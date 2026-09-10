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


# ★ 挑战A 实验：检索分数下限（钉死边界用）。设 0.0 = 关掉下限，回到挑战A 成品态。
#   为什么是 0.6 而不是第8课关键词路的 0.15：那是"字面重合率"(没重合=0)，这是"语义余弦"
#   (中文短句天然就在 0.27~0.5 之间飘)——两种量纲，阈值不可跨路搬运。
#   本机实测：命中的问题 top-1=0.731，手册里没有的问题 top-1=0.494/0.430。
MIN_SCORE = 0.6

def search_semantic(query, k=3, min_score=None):
    """语义检索：问题也变向量 → 与 8 块比余弦 → 返回最像的 top-k 块。
    索引 index_vecs 在模块加载时建一次（见下方 CHUNKS 之后），这里只做"查询"。
    min_score：低于此分的块直接不要（防拿噪音当答案）。"""
    if min_score is None:
        min_score = MIN_SCORE
    qv = embed_one(query)
    scored = sorted(((cosine(qv, index_vecs[cid]), cid, t) for cid, _, t in CHUNKS),
                    reverse=True)
    return [r for r in scored[:k] if r[0] >= min_score]

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
]

# 离线建一次索引：8 块 → 8 个向量。这就是"向量库"的最小形态（一张表 + 余弦排序）。
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
    """查手册：转向量 → top-2 → 拼成给模型的材料。低于 MIN_SCORE 就当没查到。
    形参必须叫 query：执行处是 EXEC[name](**block.input)，键名来自 schema 的 properties。"""
    hits = search_semantic(query, k=2)
    if not hits:
        # 关键：检索为空时给模型一句【明确的话】，不要甩空串——
        # 空串会让模型自由发挥（这正是"检索=空时它会编"的现场）。
        return (f"（手册检索：「{query}」没有找到相关内容，最高相似度低于下限 "
                f"{MIN_SCORE}。请如实告诉用户手册资料里没有，不要推测。）")
    return "\n".join(f"[{c}]\n{t}" for _, c, t in hits)

EXEC = {"get_weather": get_weather, "get_current_time": get_current_time,
        "search_manual": search_manual}   # 名字 -> 真实函数

# --- 3) 对话历史从这里开始（★ 多轮版） ---
# 只改两处：(1) 每轮把模型答复【记回 messages】(2) 外层循环读输入（REPL）
messages = []          # 记录层：一问一答的纯文本（成对），工具往返不常驻

def answer(user_text: str):
    """处理用户一句话。agentic loop 在局部 working 跑完；结束只把问/答文本写回 messages。"""
    working = list(messages) + [{"role": "user", "content": user_text}]
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
print("多轮助手（北京/上海/巴黎/纽约 天气、当前时间、云杉员工手册政策查询；输入 exit 退出）")
while True:
    q = input("\n你: ").strip()
    if q.lower() in ("exit", "quit", "q", "退出"):
        break
    if not q:
        continue
    answer(q)