# minimal_agent.py — 最小的"智能体"：一个会查天气的循环
# 配套课件：lessons/0001-the-agentic-loop.html
#
# 你的账号实际走的是 DeepSeek 的 Anthropic 兼容端点：
#   ANTHROPIC_BASE_URL  = https://api.deepseek.com/anthropic
#   ANTHROPIC_AUTH_TOKEN = 你在 platform.deepseek.com 建的 sk- key
# anthropic SDK 会自动读这两个环境变量，所以代码写法与调用真 Anthropic 完全一致。
#
# ★ 运行方式（必须用项目自带的 venv，否则报 No module named 'fastembed'）：
#   cd D:\agent学习
#   .\agent-lab\.venv\Scripts\python.exe code\0001-minimal-agent.py
import os
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # Windows 控制台防止符号乱码崩溃

import anthropic
from fastembed import TextEmbedding

# 你机器上可用的模型（对应本会话 Claude Code 的配置）：
#   便宜/快： deepseek-v4-flash     更强： deepseek-v4-pro[1M]
MODEL = "deepseek-v4-flash"

client = anthropic.Anthropic()   # 自动读 ANTHROPIC_BASE_URL + ANTHROPIC_AUTH_TOKEN

MODEL_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                          "..", "agent-lab", "models", "bge-small-zh-v1.5"))

emb = TextEmbedding("BAAI/bge-small-zh-v1.5", specific_model_path=MODEL_DIR)
DIM = 512

INPUT_PRICE_PER_M  = 1.5    # 元 / 百万 tokens：deepseek-v4-flash 低谷价（缓存未命中输入）
OUTPUT_PRICE_PER_M = 4.5    # 元 / 百万 tokens：deepseek-v4-flash 低谷价（输出）

SUPPORTED = ["北京", "上海", "巴黎", "纽约"]

# --- 1) 工具的真实执行代码：在你这里，不在模型那里 ---
def get_weather(city: str) -> str:
    """查询某城市当前天气（教学用假数据，真实场景换成调天气 API）"""
    table = {"北京": "晴，18°C", "上海": "多云，23°C",
             "巴黎": "雨，14°C",  "纽约": "晴，26°C"}
    return table.get(city, f"暂无 {city} 的天气数据")

def get_current_time() -> str:
    """查询当前时间（教学用假数据，真实场景换成调时间 API）"""
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def embed_one(text):
    return next(emb.embed([text]))

def cosine(a, b):
    import numpy as np
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


# ===============================================================
# 检索层：关键词路 + 语义路 → RRF 合流   ★ 第 9 课挑战 B 后半程的产物
# ===============================================================
# 【为什么从"只有语义一路"改成两路合流】
#   第 9 课镜 1 已经量过：语义路有盲区——精确串（错误码、缩写）的向量压根不在附近。
#   本文件自己的证据：0.6 那道闸门误杀的 8 道题（429/RTO/2FA/比价/代码评审/覆盖率/
#   学习基金/代码合入）**全是术语型、精确串型**，正是镜 1 里题 02（RTO）那一类：
#   语义路 top-3 连 C21 都没进，关键词路排第 2，合流把它救回第 1。
#   ⇒ 这 8 道题退化成"诚实拒绝"，**不是阈值的锅，是没有合流的锅**。
#     按本课自己的规矩：分布分不开时该做的是【提升检索质量】，不是继续试数字
#     —— 把 0.6 往下调只会让噪音漏放从 15% 涨到 59%（见 _calibrate 的阈值表）。
#
# 【★ 合流之后，闸门（阈值）挂在哪？—— 这是这一步真正要撞上的设计问题】
#   RRF 只吃名次、不吃分数，合流出来的结果是"名次"不是"分数"，
#   所以你没法再拿 0.6 去卡合流后的结果。本文件的做法：**闸门留在单路，合流只管排名**——
#     语义路：余弦低于 MIN_SCORE 的块 → 这一路不投它的名次
#     关键词路：2-gram 重合率低于 MIN_SCORE_KW 的块 → 这一路不投它的名次
#   拒答判据随之变成：**两路都没投出任何块**（=没有任何一路给出强证据）→ 当手册里没有。
#   两个闸门【量纲不同、数值也不该相同】—— 0.6 是余弦、0.15 是重合率，
#   这是"量纲不可跨路搬运"的第三次实锤。
#
# 【★ 已知限制：合流可能退化成单路，单路自己的排序毛病就没人兜了】
#   在 27 题上量过：合流把原先被 0.6 误杀的 8 题救回 3 道（01/04/18），孤儿题拒答 5/5 全对，
#   Hit@1 = 0.81（top-2 有非答案块的题 8/27）。但有一题翻车得很有教学价值：
#     题 02「RTO 是多少」→ 合流给了 C06（发布窗口），gold C21 排第 2。
#   根因【不是】合流，是关键词路的 2-gram 打分在短查询上打平、而并列由【文件顺序】断：
#     query 的 6 个 bigram = {RT, TO, "O␣", "␣是", 是多, 多少}
#       C21「…（RTO）为 2 小时」 → 命中 RT、TO       = 2/6 = 0.333
#       C06「…先经 CTO 书面批准」 → 命中 TO、O␣      = 2/6 = 0.333   ← 巧合！CTO 不是 RTO
#     rank_of 用的是稳定排序 → 并列时按 CHUNKS 的文件顺序断 → C06 在前面（它定义得更早）。
#   ⇒ 两个真伪不同的证据被打成平手，RRF 再把这个【假的名次差】放大成胜负。
#     而且语义路被 0.6 闸空后，合流退化成关键词单路，连"另一路的弱票"都没有了
#     （0009 镜 1 里同一题混合路 ✅C21 排第 1，正是因为那边不设闸、语义路的弱票进来打破了并列）。
#   怎么补？按本课自己的规矩：这是【检索质量】问题，不是阈值问题——
#     该做的是给关键词路换更强的字面匹配（分词/BM25/IDF，让"RTO"这种真词压过"CTO+空格"的巧合），
#     而不是把 0.6 往下调。注意：这题实际【答对了】——k=2 把 C21 也带进材料了，
#     所以是 Hit@1 掉了一名、效果没掉。别只看 Hit@1 就判死刑。
#
#   ---- 下面这组数是怎么来的（第 9 课挑战 B 标定，30 块语料 / 27 题 gold）----
#   标定脚本：code/_calibrate-min-score.py（离线分析，agent 运行时不跑它）
#     正样本（答案块最高分）  0.819 高 / 0.653 中位 / 0.424 低
#     负样本(a) 噪音天花板    0.699 高 / 0.561 中位 / 0.362 低
#     负样本(b) 手册里没有的    0.529 高（"停车位""食堂""健身房"这类孤儿问题）
#   三条线【重叠】→ 想同时挡住噪音得卡到 0.699，那会误杀 21/27 道题 = 光靠阈值救不了。
#   只能在重叠区里按场景取舍：本文件更怕【漏放】（噪音进 prompt → 模型拿着它编），
#   所以卡在 0.60 这一侧。代价：27 题里 8 题的正样本被语义路滤掉
#   —— 但这个"代价"现在只落在语义路上：里面相当一部分能靠关键词路救回来，
#     这正是合流值钱的地方（合流前它们只能退化成一次【诚实的拒绝】）。
#   漏放与误杀的代价不对称（编 vs 诚实说不知道），阈值也就不该对称。
#
#   ---- 两条必须记住的坑 ----
#   ① 量纲不可跨路搬运（上面已说）。
#   ② ★ 阈值会随语料扩张而失效：余弦只取决于 query 和 chunk 两个向量，所以
#      【加块不会改变已有块的分数】；但"噪音天花板"是取 max —— 候选池变大，max 只涨不跌
#      （实测 22/27 道题的噪音天花板在 8→30 块时上涨）。两条分布只会越来越重叠。
#      ⇒ 语料一扩，阈值必须重标；别指望一个数用到底。
MIN_SCORE    = 0.6     # 语义路闸门（余弦；中文短句天然在 0.27~0.5 之间飘）
MIN_SCORE_KW = 0.15    # 关键词路闸门（2-gram 重合率；没重合就是 0）——第 8 课那个数
RRF_K        = 60      # RRF 的平滑常数，业界默认 60（与 0009 同款）

def char_bigrams(s):
    """切成相邻两字的集合（"年假几天" → {年假, 假几, 几天}）。字面重合率就是拿它算的。"""
    return {s[i:i+2] for i in range(len(s) - 1)}

def kw_scores(query):
    """关键词路的【原始分数】：问题与每块的字符 2-gram 重合率。全库都打分、不截断、不卡阈值。
    ★ 为什么不直接复用"打分+卡阈值+截断"的检索函数：那等于用待校准的尺子量它自己，
      低于阈值的点会凭空消失，分布假得漂亮（_calibrate-min-score.py 里踩过这个坑）。"""
    qb = char_bigrams(query)
    return {cid: len(qb & char_bigrams(t)) / max(len(qb), 1) for cid, _, t in CHUNKS}

def vec_scores(query):
    """语义路的【原始分数】：问题也变向量 → 与库里每一块比余弦。同样全库打分、不截断。"""
    qv = embed_one(query)
    return {cid: cosine(qv, index_vecs[cid]) for cid, _, _ in CHUNKS}

def rank_of(scores, min_score):
    """把 {块: 分数} 排成"从好到差的块号"列表；低于该路闸门的块【不参与排名】= 这一路没投它。
    这就是"闸门留在单路"的落地：分数在各自路上被卡，名次才是合流的输入。"""
    return sorted((cid for cid, s in scores.items() if s >= min_score),
                  key=lambda cid: -scores[cid])

def rrf_rank(pairs, k=RRF_K):
    """RRF（Reciprocal Rank Fusion）—— 只用【名次】融合，不用分数。
    某块得分 = Σ 权重_i × 1/(k + 它在第 i 路里的名次)。名次越靠前、分越高。
    ★ 为什么用名次而不是加权分数：关键词的重合率和余弦是两种量纲，直接加权求和要先归一化、
      还得调参；RRF 干脆不看分数，"量纲不可跨路搬运"这个坑直接绕过去。生产混合检索的默认选择。
    ★ 但它【只治漏、不治排第一】：某一路的错答案也会被一起顶上来（第 9 课实测抓过两例）。"""
    agg = {}
    for ranks, w in pairs:
        for i, cid in enumerate(ranks, 1):
            agg[cid] = agg.get(cid, 0.0) + w / (k + i)
    return sorted(agg, key=lambda cid: -agg[cid])

def search_hybrid(query, k=2):
    """两路合流 → 返回 top-k 的 [(块号, 全文), ...]；两路都被闸门卡空时返回 []（= 该拒答）。"""
    order = rrf_rank([(rank_of(kw_scores(query),  MIN_SCORE_KW), 1.0),
                      (rank_of(vec_scores(query), MIN_SCORE),    1.0)])
    text = {cid: t for cid, _, t in CHUNKS}
    return [(cid, text[cid]) for cid in order[:k]]

CHUNKS = [
 ("C01", "年假", "云杉科技的带薪年假：入职满 1 年 10 个工作日，满 3 年 15 个工作日，满 5 年 20 个工作日。"
             "年假必须在当年用完，最多结转 5 天到下一年，超过部分作废。"),
 ("C02", "出差住宿报销", "出差住宿报销：一线城市（北上广深）每晚上限 600 元，二线及以下城市每晚上限 400 元；"
             "超出部分自理。报销需在差旅系统填单并附发票，出差结束 48 小时内补全票据。"),
 ("C03", "市内交通报销", "市内交通报销：地铁、公交全额报销；打车仅限两种情况——晚上 22 点后，或恶劣天气"
             "（台风、暴雨、大雪），打车需在报销单备注原因。日常通勤的地铁费不报销。"),
 ("C04", "补充商业医疗险", "员工补充商业医疗险：门诊费用报销 80%，每人每年报销上限 5000 元；住院报销 90%。"
             "牙科与生育相关费用不在此险内，走公司另配的专项险。"),
 ("C05", "开放 API 限流", "云杉控制台开放 API 限流：每分钟最多 120 次请求；超限返回 HTTP 429，响应头带 "
             "Retry-After（单位秒）。生产环境核心下单接口不可用超过 15 分钟即定义为 P0 生产事故。"),
 ("C06", "发布窗口", "上线发布窗口：每周四 20:00–22:00。紧急修复可申请豁免，但须先经 CTO 书面批准，"
             "并在发布后 24 小时内补开复盘会。"),
 ("C07", "账号安全", "账号安全：全员强制两步验证（2FA）；密码每 90 天轮换一次；向外部发送含敏感数据的文件"
             "必须加密加密码水印，并登记在外发台账。"),
 ("C08", "远程办公", "远程办公：每周三为全员可远程日；远程需提前一天在内部系统登记；各办公室工位按需预约，"
             "上海办公室共 120 个工位。"),
 ("C09", "病假", "病假：连续请假超过 2 天须提交二级甲等以上医院开具的证明。病假期间工资按本人日薪的 80% 计发，"
             "全年累计病假不超过 30 天，超过部分按事假处理。"),
 ("C10", "调休", "调休：周末或法定节假日被安排加班的，可申请 1:1 折算调休，调休假期自生成之日起 3 个月内有效，"
             "过期作废，不可折算现金。调休申请需直属主管在系统里审批。"),
 ("C11", "婚假产假陪产假", "婚假、产假与陪产假：员工结婚享婚假 10 个自然日；女员工产假 158 天；"
             "男员工陪产假 15 天。假期须提前在 HR 系统提交申请并附证明文件。"),
 ("C12", "加班餐补与夜间打车", "加班补贴：工作日加班到 20:00 之后可申报晚餐补贴 30 元；加班到 21:00 之后"
             "可报销回家打车费，凭行程单报销，与市内交通报销分开计提。"),
 ("C13", "出差餐补", "出差餐补：出差期间按自然日发放餐补，一线城市每天 120 元，其他城市每天 100 元，"
             "当天来回的按半天 50 元计。餐补随当月工资发放，无需发票。"),
 ("C14", "出差交通工具标准", "出差交通工具标准：3 小时以内行程一律选择高铁二等座；超过 3 小时可乘飞机经济舱，"
             "需提前 7 天订票；单程超过 800 元须部门总监批准。市内往返车站机场可打出租车。"),
 ("C15", "报销审批流", "报销审批流：单笔金额 2000 元以内由直属主管审批；2000 元以上至 5000 元需部门总监加签；"
             "超过 5000 元的报销单还须财务负责人复核。审批链在差旅系统内自动流转。"),
 ("C16", "发票要求", "发票要求：所有报销凭证必须是开给公司的增值税发票，抬头与税号需与营业执照一致；"
             "电子发票须提交 PDF 原件，截图与照片一律退回。个人抬头发票不予报销。"),
 ("C17", "采购与比价", "采购与比价：单笔采购金额超过 2000 元须取得三家供应商报价并留存比价记录；"
             "超过 10000 元必须签订书面合同并经法务审阅。办公用品的零星采购不受此限。"),
 ("C18", "云资源使用规范", "云资源使用规范：开发与测试环境的云主机在下班后自动关机，次日上班自动开机；"
             "生产环境的任何变更必须先提工单并由值班工程师复核，禁止直接登录生产机器改配置。"),
 ("C19", "代码评审", "代码评审：所有合并请求（PR）至少需要 1 名同事 approve；核心交易服务需要 2 人 approve。"
             "单个 PR 的改动超过 400 行会被要求拆分后再评审。"),
 ("C20", "测试覆盖率门禁", "测试覆盖率门禁：核心服务的行覆盖率不得低于 80%，新提交的代码覆盖率不得低于 70%；"
             "流水线覆盖率检查不通过会直接阻断合并，不允许人工跳过。"),
 ("C21", "数据备份与恢复", "数据备份与恢复：生产数据库每日凌晨做一次全量备份，备份文件保留 30 天；"
             "关键业务的恢复时间目标（RTO）为 2 小时，恢复点目标（RPO）为 15 分钟。"),
 ("C22", "数据分级", "数据分级：公司数据分为公开、内部、机密、绝密四级。客户名单与合同属机密级，"
             "仅有明确授权的人员可访问，且下载行为会被审计记录。"),
 ("C23", "数据出境", "数据出境：任何机密级及以上的数据不得传输至境外服务器或境外第三方；"
             "确有跨境业务需要的，须同时取得法务与安全部门的书面批准，并做脱敏处理。"),
 ("C24", "入职流程", "入职流程：候选人通过面试后需完成背景调查，提交身份证、学历证明与离职证明；"
             "所有新员工入职当天完成账号开通与安全培训，试用期为 6 个月。"),
 ("C25", "试用期与转正", "试用期与转正：试用期内工资按转正后的 90% 发放；试用期满前一个月由主管发起转正评估，"
             "需提交转正答辩材料，评估不通过可延长一次，最长不超过 3 个月。"),
 ("C26", "离职流程", "离职流程：员工主动离职须提前 30 天提交书面申请；离职前完成工作交接清单、归还门卡与电脑设备；"
             "核心技术岗位签署竞业限制协议，限制期为 12 个月。"),
 ("C27", "绩效考核", "绩效考核：目标按季度设定（OKR），每半年做一次正式绩效评估，评估结果分 A/B/C 三档；"
             "连续两次评为 C 的员工进入为期一个季度的改进计划。"),
 ("C28", "学习基金", "学习基金：每位员工每年有 5000 元的学习基金，可用于购买书籍、报名线上课程或参加行业会议；"
             "使用前需在系统提交申请并说明用途，入职满 1 年的员工方可使用。"),
 ("C29", "会议室预约", "会议室预约：会议室最多可提前 14 天预约，单次预约时长不超过 4 小时；"
             "预约开始后 15 分钟内无人签到，系统自动释放该会议室。"),
 ("C30", "供应商付款", "供应商付款：常规供应商结算周期为月结 30 天，付款前须完成验收单与发票核对；"
             "付款金额超过 50 万元的需 CFO 审批。"),
]

# 离线建一次索引：每块 → 一个向量。这就是"向量库"的最小形态（一张表 + 余弦排序）。
# 注意别在这里写死块数（曾经写过"8 块"）——语料一换注释就开始说谎。
index_vecs = {cid: embed_one(t) for cid, _, t in CHUNKS}

# --- 2) 把工具"说明书"给模型看：名字/说明/参数结构 ---
TOOLS = [{
    "name": "get_weather",
    "description": "查询某个城市的当前天气。当用户问天气时使用。只支持四城、别的不查(北京/上海/巴黎/纽约)。若用户问其它城市，本工具没有数据，不要调用，直接告诉用户暂不支持。",
    "input_schema": {
        "type": "object",
        "properties": {"city": {"type": "string",
                                "description": "城市名，如：北京"
                                }},
        "required": ["city"],
    },
},{
    "name": "get_current_time",
    "description": "查询当前时间。用户问时间时使用。",
    "input_schema": {
        "type": "object",
        "properties": {}}
}]

TOOLS.append({
    "name": "report_weather",
    "description": "★最终出口★ 已经查到天气、准备答复用户时，必须调用本工具把最终结果"
                    "以结构化字段提交；提交后不要再输出任何自然语言总结。只在拿到天气数据后收尾、无关别调",
    "input_schema": {
        "type": "object",
        "properties": {
            "city":      {"type": "string"},
            "condition": {"type": "string",
                             "description": "从 get_weather 拿到的天气串，形如：多云，23°C"},
        },
        "required": ["city", "condition"],
    },
})

TOOLS.append({
    "name":"search_manual",
    "description": "查询云杉科技员工手册里的公司政策/报销/医疗/发布窗口等规则；员工问这类问题先调它",
    "input_schema":{
        "type":"object",
        "properties":{
            "query":{"type":"string","description":"员工问的政策/报销/医疗/发布窗口等问题原文或关键词"}
        },
        "required":["query"]
    },
})


SYSTEM_SCOPED = (
    "你是「天气 · 时间 · 公司手册」三用助手，只处理三类请求：查天气（仅支持：北京、上海、巴黎、纽约）、"
    "查当前时间、查云杉科技员工手册里的公司政策（报销/医疗/年假/发布窗口/账号安全等）。"
    "这三类之外的请求（写作、闲聊、泛知识问答等）不要调用任何工具，直接告诉用户你只负责这三类。"
    "查天气：先 get_weather 取回真实数据，最后调用一次 report_weather 结构化收尾；查时间：调用 get_current_time 后用自然语言答复，不要套 report_weather。"
    "公司政策/手册类问题：先调 search_manual 拿到材料再回答；只依据材料，材料里没有就说「手册资料里没有」，绝不编造条款或数字。"
)

def search_manual(query: str) -> str:
    """查手册：关键词路 + 语义路 → RRF 合流 → top-2。两路都没投出块 = 手册里没有。
    形参必须叫 query：执行处是 EXEC[name](**block.input)，键名来自 schema 的 properties。"""
    hits = search_hybrid(query, k=2)
    if not hits:
        # 关键：检索为空时给模型一句【明确的话】，不要甩空串——
        # 空串会让模型自由发挥（这正是"检索=空时它会编"的现场）。
        return (f"（手册检索：「{query}」没有找到相关内容：关键词路重合率低于 {MIN_SCORE_KW}、"
                f"语义路余弦低于 {MIN_SCORE}，两路都没给出强证据。"
                f"请如实告诉用户手册资料里没有，不要推测。）")
    return "\n".join(f"[{c}]\n{t}" for c, t in hits)

EXEC = {"get_weather": get_weather, "get_current_time": get_current_time,
        "search_manual": search_manual}   # 名字 -> 真实函数

# --- 3) 对话历史从这里开始（★ 多轮版） ---
# 只改两处：(1) 每轮把模型答复【记回 messages】(2) 外层循环读输入（REPL）
messages = []          # 记录层：一问一答的纯文本（成对），工具往返不常驻

# ===============================================================
# ★ 第 9 课挑战 B ③：显式的一步「查询改写」（query 自足性）
# ===============================================================
# 追问（"那门诊那部分呢"）脱离上文没有主题，向量压根不在目标语义邻域里 → 检索必捞错。
# 第 8 课的教训是"赌模型自己在工具调用里改"不稳（它偶尔救回、偶尔不救），
# 所以这里把它做成【独立的一步】：进 agentic loop 之前先改写，让自足查询进入这一轮。
#
# 这一步要付两个代价，都得记住：
#   ① 它【每轮都调一次模型】= 每轮多花一次钱（省法：只在多轮、且看着像追问时才调）；
#   ② 改写本身也会【弄丢】或【理解偏】—— 0009 镜 3 抓到过一例（把"门诊"改成了"住院"，
#      只因主题词还在就照样捞对）。所以命中 ≠ 改写正确，改写质量仍要人看，
#      而且它同样得用评估集验收，不能"看着像对的"就算数。
SYS_REWRITE = ("你在帮我做检索查询改写。我会给你一段对话的上一轮话题，以及用户的追问。"
               "请把追问改写成一条【自足】的检索查询：补全被省略的主语和主题，"
               "使其脱离对话上下文也能独立被检索到。只输出查询本身，不要解释、不要引号。")

def last_topic():
    """取"上一轮话题"：优先最后一条助手答复（里面有主题词），退而用最后一条用户问题。"""
    for m in reversed(messages):
        if m["role"] == "assistant":
            return m["content"]
    return messages[-1]["content"]

def rewrite_query(topic, followup):
    """把 (上一轮话题, 追问) 交给对话模型 → 返回一条自足查询。max_tokens 给小，这是轻活。"""
    resp = client.messages.create(model=MODEL, max_tokens=120, thinking={"type": "disabled"},
                                  system=SYS_REWRITE,
                                  messages=[{"role": "user", "content":
                                             f"上一轮话题：{topic}\n用户追问：{followup}"}])
    return "".join(b.text for b in resp.content if b.type == "text").strip()

def _bare(s):
    """去掉空白与句末标点，只用来判断"这次改写其实等于没改"。"""
    return s.strip().strip("？?。.！!，,、 \t")

def answer(user_text: str):
    """处理用户一句话。agentic loop 在局部 working 跑完；结束只把问/答文本写回 messages。"""
    # ★ 显式的一步：多轮时先把追问改写成自足查询（第一轮没有上文，跳过）
    retrieval_query = user_text
    if messages:
        rw = rewrite_query(last_topic(), user_text)
        # 比之前先去掉空白和句末标点：不然"只差一个问号"也会被判成改写过（真踩过）
        if rw and _bare(rw) != _bare(user_text):
            retrieval_query = rw
            print(f"\n  ↪ [改写] 追问 → 自足：「{user_text}」 ⇒ 「{rw}」")
        else:
            print(f"\n  ↪ [改写] 本来就是自足查询，原样用：「{user_text}」")   # 原样打印：改写质量要人看
    # 改写只决定"这一轮模型看到什么"；记录层 messages 仍存用户原话（见下面 answer 末尾）
    working = list(messages) + [{"role": "user", "content": retrieval_query}]
    while True:
        with client.messages.stream(model=MODEL, max_tokens=4096, tools=TOOLS,
                                    messages=working, system=SYSTEM_SCOPED) as s:
            for chunk in s.text_stream:            # 逐字蹦（第 5 课）
                print(chunk, end="", flush=True)
            response = s.get_final_message()
            u = response.usage
            print(f"\n[账单] 本轮 input={u.input_tokens} 命中缓存={u.cache_read_input_tokens or 0} "
                  f"output={u.output_tokens}  ≈ {u.input_tokens/1e6*INPUT_PRICE_PER_M + u.output_tokens/1e6*OUTPUT_PRICE_PER_M:.4f} 元")

        if response.stop_reason == "tool_use":
            results, exit_payload = [], None
            for block in response.content:
                if block.type != "tool_use":
                    continue
                print(f"[工具请求] 模型想调用: {block.name}({block.input})")
                if block.name == "report_weather":
                    exit_payload = block.input          # 出口工具：答案在参数里
                    continue
                elif block.name == "get_weather" and block.input.get("city") not in SUPPORTED:
                    output = f"错误：暂不支持城市 {block.input.get('city')}。支持：{SUPPORTED}"
                else:
                    output = EXEC[block.name](**block.input)
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": output})
            if exit_payload is not None:
                print("✅ 结构化最终输出：", exit_payload)
                messages.append({"role": "user", "content": user_text})
                messages.append({"role": "assistant",
                                 "content": f"{exit_payload['city']} 当前天气：{exit_payload['condition']}"})
                return
            working.append({"role": "assistant", "content": response.content})
            working.append({"role": "user", "content": results})
            continue

        final = "".join(b.text for b in response.content if b.type == "text")
        if response.stop_reason != "end_turn":
            print(f"! 意外停止：{response.stop_reason}")
        messages.append({"role": "user", "content": user_text})   # ★ 记用户的话
        messages.append({"role": "assistant", "content": final})  # ★ 记模型的答复——漏了这句就断片
        return

# --- 4) ★ 真·多轮 REPL ---
# 用 __main__ 守卫包起来：直接跑 = 进 REPL；被别的脚本 import = 不执行。
# 这样 code/_calibrate-min-score.py 能复用本文件里的 CHUNKS / index_vecs / cosine，不用复制语料。
def main():
    print("多轮助手（北京/上海/巴黎/纽约 天气、当前时间、云杉员工手册政策查询；输入 exit 退出）")
    print("★ 手册检索＝关键词路 + 语义路 → RRF 合流；多轮追问会先做一步【查询改写】并原样打印。")
    print("  试一试：先问「住院能报多少？」，再追问「那门诊那部分呢」——看改写前后与命中的块。")
    while True:
        q = input("\n你: ").strip()
        if q.lower() in ("exit", "quit", "q", "退出"):
            break
        if not q:
            continue
        answer(q)

if __name__ == "__main__":
    main()