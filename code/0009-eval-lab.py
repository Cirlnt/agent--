# 0009-eval-lab.py — 第 9 课实验：给 RAG 装一把尺子（检索评估 / eval 第一次上手）
# 配套课件：lessons/0009-retrieval-eval.html
#
# 主线一句话：上一课你已经能让 RAG 答对几道题了；但"感觉还行"不是工程。
#   本课先造一把【尺子】（手写 gold set + Hit@k / Recall@k / MRR），
#   再用这把尺子去回答上一课亲手量出来的两个悬而未决的问题：
#     ① 分数阈值到底该设在哪？  ② 追问（「那二线城市呢」）到底该不该改写？
#   顺带用同一把尺子量出：关键词 + 语义【合流】比任何单路强多少，以及为什么合流要用 RRF。
#
# 四镜安排：
#   镜 1  ★ 先有尺子：四路检索器（keyword 2-gram / semantic bge / hybrid RRF / RRF·语义加权）
#          一起上秤 → 打印逐题判定 + 汇总指标表 + 【只看各路分歧的题】。
#   镜 2  ★ 阈值不是拍脑袋：把「答案块的分数（正样本）」与「噪音的天花板（负样本）」
#          两条分布摊开 → 看 0.6 / 0.5 / 0.45 各自误杀几个、漏放几个 → 阈值只能按分布标定。
#          同时用关键词那一路自己的分布再算一遍 → 第 8 课"量纲不可跨路搬运"再实锤一次。
#   镜 3  ★ query 自不自足：5 道"追问原话"→ 三栏对照（原话 / flash 改写 / 人工自足版）的检索命中
#          → 量出"改写救回多少"，并回答"能不能赌模型自发改写"。
#   镜 4  ★ top_k 扫描：k=1..5 的 Hit@k / Recall@k 曲线 + 平均注入 token → k 该设多少。
#
# 诚实口径（第 7/8 课照搬）：检索成败用【确定性判定】——每道题标了"应命中的块"(gold)，指标算的是
#   "答案块有没有进 top-k"；模型只用在"改写 query"这一处，且我们会把它改写的结果原样打出来给你看。
#
# 跑法（必须用项目 venv，沿用第 8 课的环境，本课不用再装任何东西）：
#   agent-lab\.venv\Scripts\python.exe code\0009-eval-lab.py
import os, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")      # Windows 控制台防乱码

import anthropic
from fastembed import TextEmbedding

MODEL = "deepseek-v4-flash"
client = anthropic.Anthropic()

MODEL_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                          "..", "agent-lab", "models", "bge-small-zh-v1.5"))
DIM = 512
RRF_K = 60                   # RRF（Reciprocal Rank Fusion）的平滑常数，业界默认 60

def sep(t):
    print("\n" + "=" * 12 + " " + t + " " + "=" * 12)

def bar(x, width=28):
    return "█" * max(0, min(width, int(x * width)))

# ===============================================================
# 0) 语料：云杉科技员工手册【本课扩到 30 块】
#    ⚠ 挑战 A 第 2 步把 C12 注释掉了 → 当前实际 29 块。观察完"删块后镜 2 的噪音天花板变没变"，
#      建议把 C12 取消注释还原（下面几处"30 块"的说法也随之复原）；脚本已改成读 len(CHUNKS)，
#      所以删/还原都不会再崩。
#    C01~C08 = 上一课那 8 块，原文一字未动 → 0001 里挂着的 search_manual 仍能对上；
#    新增 C09~C30 = 22 块，故意埋进【一批互相易混的块】（年假 vs 病假 vs 调休、
#    出差住宿 vs 出差餐补 vs 出差交通、事故/限流、数据分级 vs 数据出境……）。
#    为什么要扩：8 块时 top-3 闭着眼都全中，指标永远 100% → 量不出任何差别 = 评估没意义。
# ===============================================================
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

# ===============================================================
# 0.1) gold set（评估集）：每题标注【应命中的块】——这把尺子的刻度全靠它。
#      · 绝大多数题 1 个 gold；有两题是 2~3 个 gold（答案本来就横跨几块）
#        → 这两题让 Recall@k 和 Hit@k 分开说话（Hit 只问"中没中"，Recall 问"该拿的拿全没"）。
#      · 措辞刻意做了三档：① 术语型（含 429/2FA/RTO 这种字面串，关键词占便宜）
#        ② 口语换说法型（字面几乎不重合，语义占便宜）③ 追问型（不自足，见镜 3）
# ===============================================================
QUESTIONS = [
 ("01", "429 是什么意思？",                                                  ["C05"]),
 ("02", "RTO 是多少",                                                        ["C21"]),
 ("03", "OKR 多久做一次评估",                                                ["C27"]),
 ("04", "2FA 是强制的吗",                                                    ["C07"]),
 ("05", "PR 超过多少行会被要求拆分",                                         ["C19"]),
 ("06", "试用期工资是转正后的几成",                                          ["C25"]),
 ("07", "我上周末骑单车摔伤了，去诊所缝了几针，医药费花了好几百块——公司给员工配的那份医疗补充险，能按什么比例报销吗？", ["C04"]),
 ("08", "我刚入职满两年，每年能休多少天带薪假期？",                          ["C01"]),
 ("09", "下周去上海出差住酒店，一晚最多能报多少？",                          ["C02"]),
 ("10", "刮台风那天打不到车，我打车去见客户，这笔钱能报吗？",              ["C03"]),
 ("11", "家里老人住院，我要请一段较长的假去照看，那段时间工资怎么算？",      ["C09"]),
 ("12", "我打算休婚假去度蜜月，公司给几天？",                                ["C11"]),
 ("13", "周末被叫来加班，能不能换成以后补休？",                              ["C10"]),
 ("14", "买个服务器超过多少钱要走比价流程？",                                ["C17"]),
 ("15", "我的代码要几个人点头才能合进主干？",                                ["C19"]),
 ("16", "新写的模块测试要跑到多少才算过关？",                                ["C20"]),
 ("17", "客户名单能不能直接放到境外的服务器上？",                            ["C23"]),
 ("18", "我想报个线上课程，公司能出钱吗？",                                  ["C28"]),
 ("19", "提离职要提前多久说？",                                              ["C26"]),
 ("20", "供应商的货款多久结一次？",                                          ["C30"]),
 ("21", "下周去北京出差三天，住宿和每天饭钱公司分别报多少？",                ["C02", "C13"]),
 ("22", "出差去上海，交通、住宿和餐补标准分别是什么？",                      ["C14", "C02", "C13"]),
 ("23", "我现在家里有事情，身体也有点不好，来公司两年了，想请一段时间的假，能休多久？", ["C01", "C09", "C10"]),
 ("24", "这次出差的住宿，餐补，交通怎么报销？",                              ["C02", "C13", "C14"]),
 ("25", "我可以查看客户名单吗？数据能放在境外的服务器上吗？",                ["C22", "C23"]),
 ("26", "我提的代码要合进主干，除了同事点头，还得过哪些检查？",              ["C19", "C20"]),
 ("27", "我还在试用期，转正那次的评估和平时绩效考核是一回事吗？",            ["C25", "C27"]),
]

# ---------------------------------------------------------------
# 0.2) 追问集（镜 3 专用）：只给"上一轮聊到的话题"这个上下文，追问本身不自足。
#      每条 = (上一轮的话题, 追问原话, 人工写的自足版, gold)
#      "人工自足版"= 把话题补回 query 里（"出差住宿报销 二线城市 每晚上限"）——这正是改写该产出的样子。
# ---------------------------------------------------------------
FOLLOWUPS = [
 ("出差住宿报销标准是多少？", "那要是更偏的地方呢",     "出差住宿报销 二线城市 每晚上限",   ["C02"]),
 ("住院费用能报多少？",       "那另外那部分呢",         "补充商业医疗险 门诊费用报销比例", ["C04"]),
 ("报销单要谁审批？",         "那要是再贵一点的呢",     "报销审批流 超过 5000 元 谁审批",   ["C15"]),
 ("调休最多能放多久？",       "那要是没来得及用呢",     "调休 有效期 过期怎么处理",         ["C10"]),
 ("会议室要预约吗？",         "那最早能定到什么时候",   "会议室预约 最多提前几天",         ["C29"]),
]

# ===============================================================
# 1) embedding（沿用第 8 课：本地 bge-small-zh，¥0、离线）
# ===============================================================
emb = TextEmbedding("BAAI/bge-small-zh-v1.5", specific_model_path=MODEL_DIR)
print(f"embedding 模型已加载：BAAI/bge-small-zh-v1.5（本地 CPU，{DIM} 维，¥0）")

def embed_one(text):
    return next(emb.embed([text]))

def cosine(a, b):
    import numpy as np
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

index_vecs = {cid: embed_one(t) for cid, _, t in CHUNKS}
TEXT = {cid: t for cid, _, t in CHUNKS}
print(f"已建索引：{len(index_vecs)} 块 → 共 {len(index_vecs)} 个向量。评估集 {len(QUESTIONS)} 题。")

# ===============================================================
# 2) 四路检索器（都返回"全库排序"，指标才有得算）
# ===============================================================
def char_bigrams(s):
    return {s[i:i+2] for i in range(len(s) - 1)}

def kw_scores(query):
    """路 A · 关键词：问题与每块的字符 2-gram 重合率。代表"字面/BM25"这一档。"""
    qb = char_bigrams(query)
    return {cid: len(qb & char_bigrams(t)) / max(len(qb), 1) for cid, _, t in CHUNKS}

def keywords_scores(query):
    """路 E · 只看块标题（主题词）：问题与【标题】的字符 2-gram 重合率。
    ★ 与 kw_scores 唯一的差别就是把 t（全文）换成 title（标题）——用来验证"标题就够用"这个直觉。
    ★ 踩过的坑：写成 `1.0 if query in title else 0.0` 是【整句子串判断】——整句话永远不是标题的子串，
      于是 29 块全拿 0.0，rank_of 的稳定排序退化成文件顺序（每题 top-3 恒为 C01 C02 C03）。
      排序失效 ≠ 检索器差，看指标前先确认它真的在排序。"""
    qb = char_bigrams(query)
    return {cid: len(qb & char_bigrams(title)) / max(len(qb), 1) for cid, title, _ in CHUNKS}

def vec_scores(query):
    """路 B · 语义：问题也 embed 成向量 → 与每块比余弦。"""
    qv = embed_one(query)
    return {cid: cosine(qv, index_vecs[cid]) for cid, _, _ in CHUNKS}

def rank_of(scores):
    """把 {块: 分数} 排成从好到差的块号列表。"""
    return sorted(scores, key=lambda cid: scores[cid], reverse=True)

def rrf_rank(pairs, k=RRF_K):
    """RRF（Reciprocal Rank Fusion）—— 只用【名次】融合，不用分数。
    公式：某块得分 = Σ 权重_i × 1/(k + 它在第 i 路里的名次)。名次越靠前、分越高。
    ★ 为什么用名次而不是加权分数：上一课的教训——关键词的重合率和余弦是两种量纲、不可搬运，
      直接加权要先做归一化调参；RRF 干脆不看分数，量纲问题直接绕过去。生产混合检索的默认选择。
    ★ 权重 w 是【要调的旋钮】：w=1 表示两路平等；想让语义话语权更大就给它 >1 的权重。
      怎么知道该调成多少？——还是同一把尺子说了算。"""
    agg = {}
    for ranks, w in pairs:
        for i, cid in enumerate(ranks, 1):
            agg[cid] = agg.get(cid, 0.0) + w / (k + i)
    return sorted(agg, key=lambda cid: agg[cid], reverse=True)

def hybrid_rank(query, w_vec=1.0):
    """混合：关键词一路 + 语义一路，RRF 融合。w_vec = 语义那一路的权重。"""
    return rrf_rank([(rank_of(kw_scores(query)), 1.0),
                     (rank_of(vec_scores(query)), w_vec)])

RETRIEVERS = {
    "关键词 keyword ": lambda q: rank_of(kw_scores(q)),
    "语义 semantic ": lambda q: rank_of(vec_scores(q)),
    "混合 hybrid ": lambda q: hybrid_rank(q),
    "混合·语义×2 ": lambda q: hybrid_rank(q, w_vec=2.0),
    "主题词keywords ": lambda q: rank_of(keywords_scores(q)),
}

# ===============================================================
# 3) 指标：Hit@k / Recall@k / MRR
#    这三个是检索评估的"通用尺子"，任何 RAG 项目、任何向量库都通用，面试也照这三样问。
# ===============================================================
def hit_at(ranked, gold, k):
    """top-k 里有没有答案块？（有=1，没有=0）——最宽松：只要沾到就满分。"""
    return 1.0 if any(cid in gold for cid in ranked[:k]) else 0.0

def recall_at(ranked, gold, k):
    """top-k 把"该拿的块"拿全了几成？——多 gold 的题只有它能照出差距。"""
    return len(set(ranked[:k]) & set(gold)) / len(gold)

def rr(ranked, gold):
    """Reciprocal Rank：第一个答案块排在第几 → 取倒数（第 1 名=1.0，第 3 名≈0.33，没捞到=0）。"""
    for i, cid in enumerate(ranked, 1):
        if cid in gold:
            return 1.0 / i
    return 0.0

def evaluate(fn, questions, k_hit=3, k_rec=3, k_mrr=5):
    rows = []
    for qid, q, gold in questions:
        ranked = fn(q)
        rows.append({"qid": qid, "q": q, "gold": gold, "ranked": ranked,
                     "hit1": hit_at(ranked, gold, 1), "hit3": hit_at(ranked, gold, k_hit),
                     "rec3": recall_at(ranked, gold, k_rec), "rr": rr(ranked[:k_mrr], gold)})
    n = len(rows)
    return rows, {"Hit@1": sum(r["hit1"] for r in rows) / n,
                  "Hit@3": sum(r["hit3"] for r in rows) / n,
                  "Recall@3": sum(r["rec3"] for r in rows) / n,
                  "MRR@5": sum(r["rr"] for r in rows) / n}

# ===============================================================
sep("镜 1 · ★ 先有尺子：四路检索器一起上秤")
print("""
  先说清楚"评估"是什么：不是让模型自评、也不是看着答案"感觉还行"——
  是你自己写一份【评估集】（一批题 + 每题该命中哪块），再算几个【客观指标】。
  有了尺子，后面每一次调参（换检索器、设阈值、改 k）才叫"改进了"，否则只是"感觉变了"。

  尺子上的三个刻度（通用，记下来）：
    Hit@1  ：top-1 里有没有答案块 —— 用户点进来第一眼看到的对不对
    Hit@3  ：top-3 里有没有        —— 注入进 prompt 的那几块里对不对
    Recall@3：该拿的块拿全了几成    —— 多块答案（出差三件事）专用
    MRR@5  ：第一个答案块排名倒数   —— 排第 1 得 1 分、排第 3 得 0.33、没进 top-5 得 0 分
""")

evals = {}
for name, fn in RETRIEVERS.items():
    rows, agg = evaluate(fn, QUESTIONS)
    evals[name] = (rows, agg)

print(f"  {len(QUESTIONS)} 道题，每题标了应命中块（gold）。逐题 top-1：")
heads = ["关键词", "语义", "混合", "混·语×2"]
print(f"    {'#':3} {'gold':15} " + " ".join(f"{h:9}" for h in heads) + " 问题")
for i, (qid, q, gold) in enumerate(QUESTIONS):
    marks = []
    for name in RETRIEVERS:
        top1 = evals[name][0][i]["ranked"][0]
        marks.append(("✅" if top1 in gold else "❌") + top1)
    g = ",".join(gold)
    print(f"    {qid:3} {g:15} " + " ".join(f"{m:9}" for m in marks) + f" {q[:30]}")

print("\n  ── 汇总指标（这才是「感觉」的替代品）──")
print(f"    {'检索器':16} {'Hit@1':>8} {'Hit@3':>8} {'Recall@3':>9} {'MRR@5':>8}")
for name, (rows, agg) in evals.items():
    print(f"    {name:16} {agg['Hit@1']:>8.2f} {agg['Hit@3']:>8.2f} {agg['Recall@3']:>9.2f} {agg['MRR@5']:>8.2f}")

kw_agg, se_agg, hy_agg, hw_agg = (evals["关键词 keyword "][1], evals["语义 semantic "][1],
                                  evals["混合 hybrid "][1], evals["混合·语义×2 "][1])
print(f"\n  ├ 关键词 vs 语义：Hit@1 {kw_agg['Hit@1']:.2f} → {se_agg['Hit@1']:.2f}"
      f"（照第 8 课预期：换说法那几题关键词会掉）")
print(f"  ├ 语义 vs 混合  ：Hit@3 {se_agg['Hit@3']:.2f} → {hy_agg['Hit@3']:.2f}，"
      f"Recall@3 {se_agg['Recall@3']:.2f} → {hy_agg['Recall@3']:.2f}")
print(f"  │   ★ 注意混合在 Hit@1 上并没有赢（{se_agg['Hit@1']:.2f} → {hy_agg['Hit@1']:.2f}）："
      f"RRF 会把某一路的错答案也一起顶上来。")
print(f"  │     但真正决定【注入哪几块给模型】的是 Hit@3 / Recall@3 —— 那一栏混合全胜。"
      f"合流治的是【漏】，不是【排第一】。")
print(f"  └ 融合权重也能调：给语义 ×2 后 Hit@1 {hy_agg['Hit@1']:.2f} → {hw_agg['Hit@1']:.2f}"
      f"（怎么知道该给多少？还是这把尺子说了算）。")
print(f"    结论：两路是【互补】不是【替代】——语义兜换说法，关键词兜术语串（429/2FA/RTO 这种）。")

print("\n  ── 只看各路分歧的题（尺子最值钱的地方：把所有争论收敛到几行）──")
n_div = 0
for i, (qid, q, gold) in enumerate(QUESTIONS):
    tops = [evals[n][0][i]["ranked"][0] for n in RETRIEVERS]
    if len(set(tops)) == 1:
        continue
    n_div += 1
    print(f"    {qid}  {q[:40]}")
    print(f"        gold={','.join(gold)}")
    for name in RETRIEVERS:
        r = evals[name][0][i]
        top3 = " ".join((("✅" if c in gold else "  ") + c) for c in r["ranked"][:3])
        print(f"        {name} top-3: {top3}")
print(f"    → {n_div} 道题上各路给出了不同答案；剩下 {len(QUESTIONS)-n_div} 道各路一致（这些题对选型没信息量）。")
print("    ★ 教学点：评估集不是每题都有用——真正推动决策的是【分歧题】。你的题集里分歧题越多，尺子越灵敏。")

# ===============================================================
sep("镜 2 · ★ 阈值不是拍脑袋：把两条分数分布摊开看")
print("""
  上一课你给检索加了分数下限（MIN_SCORE=0.6），当场的疑问是"0.6 这个数凭什么"。
  定量做法只有一条：把【正样本】和【负样本】的分数分布都画出来，看它们分不分得开。

    正样本分数 = 这道题里【答案块】拿到的最高分（希望它高）
    负样本分数 = 这道题里【非答案块】拿到的最高分（也就是"噪音的天花板"，希望它低）

  阈值该卡在哪：既要高于大多数噪音，又不能高过正样本 —— 两者的重叠区就是你的"不确定地带"。
""")

def distribution(score_fn, questions):
    pos, neg = [], []
    for qid, q, gold in questions:
        sc = score_fn(q)
        pos.append((qid, max(sc[c] for c in gold)))
        neg.append((qid, max(v for c, v in sc.items() if c not in gold)))
    return pos, neg

for label, score_fn, cands in [
    ("语义 · 余弦（0~1）", vec_scores, [0.70, 0.60, 0.50, 0.45, 0.40]),
    ("关键词 · 2-gram 重合率（0~1）", kw_scores, [0.30, 0.20, 0.15, 0.10, 0.05]),
]:
    pos, neg = distribution(score_fn, QUESTIONS)
    pos.sort(key=lambda x: -x[1]); neg.sort(key=lambda x: -x[1])
    print(f"\n  ══ {label} ══")
    print(f"    正样本（答案块的最高分，越高越好）× {len(pos)}：")
    print(f"      {pos[0][1]:.3f}（最高·{pos[0][0]}） … {pos[len(pos)//2][1]:.3f}（中位·{pos[len(pos)//2][0]}） … "
          f"{pos[-1][1]:.3f}（最低·{pos[-1][0]}）")
    print(f"    负样本（噪音天花板，越低越好）× {len(neg)}：")
    print(f"      {neg[0][1]:.3f}（最高·{neg[0][0]}） … {neg[len(neg)//2][1]:.3f}（中位·{neg[len(neg)//2][0]}） … "
          f"{neg[-1][1]:.3f}（最低·{neg[-1][0]}）")
    pos_min = min(p[1] for p in pos)
    neg_max = max(n[1] for n in neg)
    if pos_min > neg_max:
        print(f"    ✅ 两条分布【分得开】：噪音最高 {neg_max:.3f} < 答案最低 {pos_min:.3f}"
              f" → 落在 ({neg_max:.3f}, {pos_min:.3f}) 空隙里的任何阈值都一样好，挑哪个都行。")
    else:
        print(f"    ⚠ 两条分布【重叠】：噪音最高 {neg_max:.3f} > 答案最低 {pos_min:.3f}"
              f" → 重叠区 [{pos_min:.3f}, {neg_max:.3f}] 里的阈值必然两头不讨好（见下表）。")
    print(f"    {'阈值':>8} {'误杀(正样本被滤)':>18} {'漏放(噪音当答案)':>18}  说明")
    for thr in cands:
        miss = [p[0] for p in pos if p[1] < thr]
        leak = [n[0] for n in neg if n[1] >= thr]
        note = "← 现状" if (label.startswith("语义") and thr == 0.60) or (label.startswith("关键词") and thr == 0.15) else ""
        print(f"    {thr:>8.2f} {len(miss):>10} ({len(miss)/len(pos):>4.0%}) {len(leak):>13} ({len(leak)/len(neg):>4.0%})  {note}")
    if label.startswith("语义"):
        cur = [p for p in pos if p[1] < 0.60]
        print(f"    → 上一课的 0.6 在这批数据上会【误杀 {len(cur)} 道题】"
              f"（{'、'.join(q for q, _ in cur) if cur else '无'}）；降到 0.45 则误杀 {len([p for p in pos if p[1] < 0.45])} 道。")
    else:
        print(f"    → 关键词路的最优区间和余弦路完全不同（差着一个量级）——"
              f"这就是第 8 课那条『量纲不可跨路搬运』的定量版。")

print("""
  ★ 结论（阈值怎么定，标准答法）：
    ① 阈值不是一个"正确答案"，是你按自己的数据分布做的【取舍】：卡高 = 宁可答不出的多、编的少；
       卡低 = 答得出的多、噪音也多。往哪偏，取决于你的场景更怕哪种错。
    ② 先画分布（本镜就三步：算正样本、算负样本、看重叠），再选数——永远别从别的项目抄一个阈值。
    ③ 两路分布没法用同一个数：余弦天生挤在 0.3~0.8，2-gram 重合率一大片是 0。
    ④ 分布重叠严重时，单靠阈值救不了 —— 该做的是提升检索质量（合流/rerank/换 embed 模型），
       阈值只是最后一道保险，不是主力。
""")

# ===============================================================
sep("镜 3 · ★ query 自不自足：追问原话 vs 改写")
print("""
  上一课第二个悬案：追问「那二线城市呢」该不该改写？本镜用尺子量。
  三栏对照，都用同一把尺子：
    A 原话（不自足）  —— 用户随口甩出来的、脱离开上下文根本不知所云的查询
    B flash 改写      —— 让对话模型看着"上一轮话题"，把追问改写成自足查询（真调模型，原样打印）
    C 人工自足版      —— 人写出来的"标准答案长什么样"，作为改写质量的上限参照
""")

SYS_REWRITE = ("你在帮我做检索查询改写。我会给你一段对话的上一轮话题，以及用户的追问。"
               "请把追问改写成一条【自足】的检索查询：补全被省略的主语和主题，"
               "使其脱离对话上下文也能独立被检索到。只输出查询本身，不要解释、不要引号。")

def rewrite_query(topic, followup):
    resp = client.messages.create(model=MODEL, max_tokens=120, thinking={"type": "disabled"},
                                  system=SYS_REWRITE,
                                  messages=[{"role": "user", "content":
                                             f"上一轮话题：{topic}\n用户追问：{followup}"}])
    return "".join(b.text for b in resp.content if b.type == "text").strip()

print(f"    {'上一轮话题':18} {'追问原话':16} {'A 原话 top-1':16} {'B flash 改写':30} {'B top-1':10}")
print("    " + "-" * 100)
stat = {"A": 0, "B": 0, "C": 0}
for topic, followup, manual, gold in FOLLOWUPS:
    a_rank = hybrid_rank(followup)
    a_ok = a_rank[0] in gold
    rw = rewrite_query(topic, followup)
    b_rank = hybrid_rank(rw)
    b_ok = b_rank[0] in gold
    c_rank = hybrid_rank(manual)
    c_ok = c_rank[0] in gold
    stat["A"] += a_ok; stat["B"] += b_ok; stat["C"] += c_ok
    amark = f"{'✅' if a_ok else '❌'} {a_rank[0]}"
    bmark = f"{'✅' if b_ok else '❌'} {b_rank[0]}"
    print(f"    {topic:18} {followup:16} {amark:16} {rw[:28]:30} {bmark:10}")
    print(f"        ↑ 改写{'救回' if b_ok and not a_ok else ('弄丢' if a_ok and not b_ok else '无变化')}"
          f"（gold={'/'.join(gold)}）｜ 人工自足版「{manual}」→ {'✅' if c_ok else '❌'} {c_rank[0]}")

n = len(FOLLOWUPS)
print(f"\n    Hit@1 对照（{n} 道追问）：A 原话 {stat['A']}/{n} ｜ B flash 改写 {stat['B']}/{n} ｜ C 人工自足 {stat['C']}/{n}")
print("""
  ★ 结论：
    ① 不自足的 query 检索质量是"看运气"——它的向量压根不在你要的那个语义邻域里；
       补全主题（= 让它自足）之后，同一套索引、同一路检索器，命中率就能上一个台阶。
    ② 但"让模型自己改写"是【要显式做出来】的一步，不能指望它顺手发生：模型不会每轮都替你补主语。
       所以工程上二选一（或都做）：在工具描述/system 里【明确要求 query 自足】，
       或专门做【查询改写】这一环（本镜就是一个 20 行的最小实现）。
    ③ 改写同样要用尺子验收：上面 A/B/C 三栏就是最简版——改写有没有救回命中，一跑就知道。
       注意改写也可能【弄丢】原本能命中的查询（把关键词改没了），所以这一步必须进回归集。
""")

# ===============================================================
sep("镜 4 · ★ top_k 扫描：k 该设多少")
print("""
  k 是"每次往 prompt 里塞几块"。太大 → token 涨、稀释注意力；太小 → 答案块被切在 top-k 之外。
  把 k 从 1 扫到 8，同时看【指标】和【钱】——这就是"调参"该有的样子：一次只动一个旋钮，其余不动。
  最后一行的"全量塞"是第 8 课那面镜子，放在一起才知道"省下来的到底是什么"。
""")

print(f"    {'k':>3} {'Hit@1':>8} {'Hit@k':>8} {'Recall@k':>9} {'MRR@5':>8} {'平均注入 token':>16}")
SCAN_KS = (1, 2, 3, 4, 5, 8)
N_ALL = len(CHUNKS)                            # 全量塞 = 语料当前块数
TOK_KS = (1, 3, 5, 8, N_ALL)                   # 量 token 的几档；★ 这里别再写死 30——
                                               # 挑战 A 删掉 C12 后语料变 29 块，avg_tokens 返回 None，最后一行会崩
PROBE = QUESTIONS[:6]                          # 抽 6 题量 token，够看趋势且省钱

def avg_tokens(k):
    if k > len(CHUNKS):
        return None
    tot = 0
    for qid, q, gold in PROBE:
        refs = "\n".join(f"[{cid}] {TEXT[cid]}" for cid in hybrid_rank(q)[:k])
        tot += client.messages.count_tokens(model=MODEL, system="x",
                                            messages=[{"role": "user", "content": refs + "\n问题：" + q}]).input_tokens
    return tot // len(PROBE)

tok_map = {k: avg_tokens(k) for k in TOK_KS}

for k in SCAN_KS:
    rows, _ = evaluate(hybrid_rank, QUESTIONS, k_hit=k, k_rec=k, k_mrr=5)
    hit1 = sum(r["hit1"] for r in rows) / len(rows)
    hitk = sum(hit_at(r["ranked"], r["gold"], k) for r in rows) / len(rows)
    reck = sum(recall_at(r["ranked"], r["gold"], k) for r in rows) / len(rows)
    mrr = sum(r["rr"] for r in rows) / len(rows)
    tok = f"{tok_map[k]:>16}" if tok_map.get(k) else f"{'—':>16}"
    tail = "   ← 全量塞（第 8 课那面镜子）" if k == N_ALL else ("   ← 本课默认" if k == 3 else "")
    print(f"    {k:>3} {hit1:>8.2f} {hitk:>8.2f} {reck:>9.2f} {mrr:>8.2f} {tok}{tail}")
print(f"    全量塞 {N_ALL} 块：平均注入 {tok_map[N_ALL]:>3} token —— 是 k=3 的 "
      f"{tok_map[N_ALL]/tok_map[3]:.1f} 倍，而上面每一栏指标一个点都没涨。")
print(f"    （token 一栏 = 6 道题的平均值，含注入原文 + 问题；本地 embedding ¥0，只有这部分走付费模型。）")
print(f"""
  ★ 结论：k 的收益是【边际递减】的——Hit@k 到 k=2 就满了、Recall@k 到 k=3 也满了；
    再往后 5、8、{N_ALL} 一路加上去，指标纹丝不动，token 却从 {tok_map[3]} 涨到 {tok_map[N_ALL]}（{tok_map[N_ALL]/tok_map[3]:.1f} 倍）。
    所以"k 设多少"的答案不是"越大越好"，是"指标曲线的拐点 + 你的 token 预算"的交点。
    另外注意：这里涨的是 Hit@k（"答案块进没进"），它不等于"模型最终答对了"——
    要量最终答案对不对，得把生成那一步也纳入评估（下一层，M6 的 eval）。
""")

# ===============================================================
sep("收束 · 本课你手里多了什么")
print(f"""
  1. 一把尺子：{len(QUESTIONS)} 题 gold set + Hit@1/Hit@3/Recall@k/MRR@5 —— 20 行代码，任何 RAG 项目都能复用。
  2. 四路的定量结论（Hit@1 / Hit@3 / Recall@3）：
       关键词 {kw_agg['Hit@1']:.2f} / {kw_agg['Hit@3']:.2f} / {kw_agg['Recall@3']:.2f}   字面那一路，术语串稳、换说法就崩
       语义   {se_agg['Hit@1']:.2f} / {se_agg['Hit@3']:.2f} / {se_agg['Recall@3']:.2f}   主力，但会漏"精确串"（RTO 那题它连 top-3 都没进）
       混合   {hy_agg['Hit@1']:.2f} / {hy_agg['Hit@3']:.2f} / {hy_agg['Recall@3']:.2f}   RRF 融合，没漏过一块
       语义×2 {hw_agg['Hit@1']:.2f} / {hw_agg['Hit@3']:.2f} / {hw_agg['Recall@3']:.2f}   同一个 RRF 只改权重 → 又是一个可以量的旋钮
     → 互补 > 单路；RRF 只吃名次、不吃分数，顺手绕掉上一课那个"量纲不可搬运"的坑。
  3. 阈值怎么定：画正/负样本两条分布 → 看重叠区 → 按场景取舍。抄别人项目的阈值 = 没做标定。
     （上一课那个 0.6 拿到 {N_ALL} 块语料上，正样本误杀率见镜 2 —— 语料一变，阈值就得重标。）
  4. 追问必须自足：A 原话 {stat['A']}/{n}、B 模型改写 {stat['B']}/{n}、C 人工自足 {stat['C']}/{n}
     → 改写这步要显式做出来，而且要用同一把尺子验收（它也会弄丢东西）。
  5. k 设多少：看曲线拐点（本批数据 k=3 就平了），全量塞的 token 见镜 4 最后一行。

  诚实提醒（一定要会说的话）：这把尺子有误差，读数字前先看清三件事——
    ① 题是【我出的】、语料也是我写的，出得太顺手 → 指标偏乐观：真实语料的检索比你看到的难。
    ② 分辨率：{len(QUESTIONS)} 道题上，名次差一名 = {1/len(QUESTIONS):.1%}。所以上面语义 {se_agg['Hit@1']:.2f} 与混合 {hy_agg['Hit@1']:.2f}
       之间只差【一道题】——这个量级的差距【不足以】下结论；要大到超过一两道题的噪音才值得信。
    ③ 同一个评估集反复用来调参，调久了就会【过拟合到这套题上】。
       生产做法：评估集持续扩充（把线上问过的真问题补进去）+ 留一批题不参与调参、只做验收。
""")

# ---------------------------------------------------------------
# 附录 · 这套环境怎么来的（沿用第 8 课，不用重装）
#   venv 里已有 fastembed + onnxruntime；本地模型 agent-lab/models/bge-small-zh-v1.5 已就绪。
#   跑：agent-lab\.venv\Scripts\python.exe code\0009-eval-lab.py
#   想改题集/加语料：直接改本文件顶部的 CHUNKS 与 QUESTIONS——尺子是你的，随你加刻度。
# ---------------------------------------------------------------
