# tool_spec_lab.py — 第 2 课实验：同一只"锅"，换三张"说明书"，看模型怎么变
# 配套课件：lessons/0002-the-tool-spec.html
#
# 一句话预习：get_weather 这个函数（锅）一个字都不改，变的只有 TOOLS 里
# 给模型看的那三行字（说明书），但模型的"点单"行为会跟着变。
# 这说明：description 和 input_schema，就是模型对一个工具的全部了解。
#
# 端点仍是 DeepSeek 的 Anthropic 兼容端点，写法与真 Anthropic 一致。
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # Windows 控制台防乱码

import anthropic

MODEL = "deepseek-v4-flash"   # 想更强换成 "deepseek-v4-pro[1M]"
client = anthropic.Anthropic()

# ---------- 锅：下面的函数在三个镜头里一字不变 ----------
SUPPORTED = ["北京", "上海", "巴黎", "纽约"]      # 真实"能做"的菜 = 数据表里的城市

def get_weather(city: str) -> str:
    """查询某城市当前天气（教学用假数据，真实场景换成调天气 API）"""
    table = {"北京": "晴，18°C", "上海": "多云，23°C",
             "巴黎": "雨，14°C",  "纽约": "晴，26°C"}
    return table.get(city, f"暂无 {city} 的天气数据")

# ---------- 三种"说明书"：模型眼里工具的全部 ----------
# 镜 1 · 裸奔：没有说"我只支持哪几个城市"，city 参数也没约束
SPEC_BAD = {
    "name": "get_weather",
    "description": "查询天气。用户问天气时使用。",
    "input_schema": {
        "type": "object",
        "properties": {"city": {"type": "string", "description": "城市名"}},
        "required": ["city"],
    },
}

# 镜 2 · 在 description 里写清楚边界（含"不支持时不要调用"的负例）
SPEC_GOOD_DESC = {
    "name": "get_weather",
    "description": "查询某城市的当前天气。仅支持：北京、上海、巴黎、纽约。"
                   "若用户问其它城市，本工具没有数据，不要调用，直接告诉用户暂不支持。"
                   "返回形如：晴，18°C。",
    "input_schema": {
        "type": "object",
        "properties": {"city": {"type": "string",
                                "description": "城市名，取值限于：北京/上海/巴黎/纽约"}},
        "required": ["city"],
    },
}

# 镜 3 · 在 input_schema 里用 enum 上锁：把"能传什么"直接框死
SPEC_ENUM = {
    "name": "get_weather",
    "description": "查询某城市的当前天气。若用户问支持列表之外的城市，"
                   "直接告诉用户暂不支持，不要调用本工具。",
    "input_schema": {
        "type": "object",
        "properties": {"city": {"type": "string",
                                "enum": SUPPORTED,
                                "description": "城市名"}},
        "required": ["city"],
    },
}

def ask(tools, question, label):
    """只发一次请求，看模型"点单"点了谁 / 还是直接开口回答。此处不做菜。"""
    print("\n" + "=" * 62)
    print(label)
    print("=" * 62)
    print(f"用户问：{question}")
    resp = client.messages.create(
        model=MODEL, max_tokens=512, tools=[tools],
        messages=[{"role": "user", "content": question}],
    )
    for b in resp.content:
        if b.type == "tool_use":
            print(f"✳ 模型想调用：{b.name}({b.input})")
        elif b.type == "text" and b.text.strip():
            print(f"✍ 模型直接回答：{b.text.strip()}")

QUESTION = "帮我查一下东京现在的天气。"

if __name__ == "__main__":
    ask(SPEC_BAD,      QUESTION, "镜 1 · 裸奔说明书（没写支持范围）")
    ask(SPEC_GOOD_DESC, QUESTION, "镜 2 · 只在 description 里写明边界与负例")
    ask(SPEC_ENUM,     QUESTION, "镜 3 · 在 input_schema 里用 enum 把取值锁死")
