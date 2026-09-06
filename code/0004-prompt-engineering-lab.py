# prompt_engineering_lab.py — 第 4 课实验：同样的话，放在 system 还是放进工具 description？
# 配套课件：lessons/0004-prompt-engineering.html
#
# 一句话预习：模型每轮看到的"说明"，分三层——system prompt（整台 Agent 的全局章程）、
# 每个工具的 description（单工具的使用说明）、input_schema（参数合同）。同一条规矩，
# 该放哪层，判据只有一句话：它管"一个工具"，还是管"整台 Agent / 工具之间"？
#
# 本实验想让"分工"这个抽象东西看得见：同一组工具，只改"规矩放哪"，模型的
# "点单 / 开口答 / 拒绝"行为就会不一样。测试里埋了一颗雷：工具菜单里放了一个
# "万能"的联网搜索工具——它是故意来逼你回答"边界到底谁来守"的。
#
# 端点仍是 DeepSeek 的 Anthropic 兼容端点，写法与真 Anthropic 一致。
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # Windows 控制台防乱码

import anthropic

MODEL = "deepseek-v4-flash"   # 想更强换成 "deepseek-v4-pro[1M]"
client = anthropic.Anthropic()

# ============================================================
# 公共素材：四个工具（天气 / 时间 / ★万能搜索★ / 天气出口）
#   注意两个真工具 + 出口工具在第 3 课就见过；search_web 是本课新加的"雷"。
#   它描述成"能联网搜任何信息"——先猜：不给这台 Agent 立规矩，它会拿它干嘛？
# ============================================================
SUPPORTED = ["北京", "上海", "巴黎", "纽约"]

TOOL_WEATHER = {
    "name": "get_weather",
    "description": "查询某城市的当前天气。仅支持：北京、上海、巴黎、纽约。"
                   "若用户问其它城市，本工具没有数据，不要调用，直接告诉用户暂不支持。"
                   "返回形如：晴，18°C。",
    "input_schema": {"type": "object",
                     "properties": {"city": {"type": "string",
                                             "description": "城市名，取值限于：北京/上海/巴黎/纽约"}},
                     "required": ["city"]},
}

TOOL_TIME = {
    "name": "get_current_time",
    "description": "查询当前时间。当用户问时间时使用。",
    "input_schema": {"type": "object", "properties": {}},
}

# report_weather：第 3 课的"出口工具"，只管"查到天气后结构化收尾"（原版，没写边界）
TOOL_REPORT = {
    "name": "report_weather",
    "description": "★最终出口★ 已经查到天气、准备答复用户时，必须调用本工具把最终结果"
                   "以结构化字段提交；提交后不要再输出任何自然语言总结。",
    "input_schema": {"type": "object",
                     "properties": {
                         "city": {"type": "string"},
                         "condition": {"type": "string",
                                       "description": "从 get_weather 拿到的天气串，形如：多云，23°C"},
                     },
                     "required": ["city", "condition"]},
}

# search_web 有两种"说明书"（镜 1/2 vs 镜 3 用不同那份）：
SEARCH_BROAD = ("联网搜索最新信息。当你需要回答超出自身知识范围的问题、"
                "或需要实时/最新数据时使用。")   # 万能版：什么都能搜
SEARCH_NARROW = ("搜索【企业内部知识库】（仅含公司内部政策与产品手册）。"
                 "仅当用户明确在问公司内部文档内容时使用。")   # 收窄版：只许搜内部库

def make_search(desc):
    return {"name": "search_web", "description": desc,
            "input_schema": {"type": "object",
                             "properties": {"query": {"type": "string",
                                                       "description": "搜索关键词"}},
                             "required": ["query"]}}

# ============================================================
# 镜 2 用：顶层 system 章程（整台 Agent 的定位 + 边界）
# ============================================================
SYSTEM_SCOPED = (
    "你是「天气与时间」专用助手，只做两件事：查北京/上海/巴黎/纽约的当前天气、查当前时间。"
    "除此之外的一切请求（包括知识问答、写作、搜索任意信息）都超出你的职责："
    "直接告诉用户你只负责天气和时间，不要调用任何工具。"
)

# ============================================================
# 测试问句包（都刻意不在"天气/时间"域里，或刚好踩在边界上）
#   q_weather 对照组：域内，三镜都应正常调 get_weather
#   q_btc      域外但"需要实时/外部信息" → 有个万能搜索工具时最容易被拉去搜
#   q_everest  域外但"零工具就能答"（模型自己知道 8848）→ 最考验"顶层边界"的一题
# ============================================================
BATTERY = [
    ("q_weather · 域内天气（对照组）", "帮我查一下上海现在的天气"),
    ("q_btc     · 域外：比特币实时价", "今天比特币价格是多少？"),
    ("q_everest · 域外：珠峰有多高（零工具可答）", "珠穆朗玛峰有多高？"),
]

def run_one(tag, question, tools, system=None):
    """发一次请求，打印模型这轮"点单 / 开口 / 停"的行为。"""
    print("\n" + "=" * 62)
    print(tag)
    print("=" * 62)
    print(f"用户问：{question}")
    kwargs = dict(model=MODEL, max_tokens=1024, tools=tools,
                  messages=[{"role": "user", "content": question}])
    if system:
        kwargs["system"] = system
    resp = client.messages.create(**kwargs)
    print(f"stop_reason = {resp.stop_reason}")
    for b in resp.content:
        if b.type == "tool_use":
            print(f"✳ 模型想调用：{b.name}({b.input})")
        elif b.type == "text" and b.text.strip():
            print(f"✍ 模型直接说话：{b.text.strip()[:70]}")

def run_mirror(title, tools, system=None):
    print("\n" + "#" * 62)
    print("# " + title)
    print("#" * 62)
    for tag, q in BATTERY:
        run_one(tag, q, tools, system)

if __name__ == "__main__":
    # ---------- 镜 1：裸奔。没有 system，search_web 是万能版 ----------
    run_mirror("镜 1 · 无 system：模型默认自己是『通用助手』（search_web=万能）",
               [TOOL_WEATHER, TOOL_TIME, TOOL_REPORT, make_search(SEARCH_BROAD)])

    # ---------- 镜 2：同一组工具，只加一份 system 章程 ----------
    run_mirror("镜 2 · 同一工具集 + system 顶层定位『只做天气/时间』",
               [TOOL_WEATHER, TOOL_TIME, TOOL_REPORT, make_search(SEARCH_BROAD)],
               system=SYSTEM_SCOPED)

    # ---------- 镜 3：不写 system，把"边界"摊进每个工具的 description ----------
    run_mirror("镜 3 · 无 system：只把边界写进各工具 desc（search_web=收窄成企业内网）",
               [TOOL_WEATHER, TOOL_TIME, TOOL_REPORT, make_search(SEARCH_NARROW)])
