# minimal_agent.py — 最小的"智能体"：一个会查天气的循环
# 配套课件：lessons/0001-the-agentic-loop.html
#
# 你的账号实际走的是 DeepSeek 的 Anthropic 兼容端点：
#   ANTHROPIC_BASE_URL  = https://api.deepseek.com/anthropic
#   ANTHROPIC_AUTH_TOKEN = 你在 platform.deepseek.com 建的 sk- key
# anthropic SDK 会自动读这两个环境变量，所以代码写法与调用真 Anthropic 完全一致。
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # Windows 控制台防止符号乱码崩溃

import anthropic

# 你机器上可用的模型（对应本会话 Claude Code 的配置）：
#   便宜/快： deepseek-v4-flash     更强： deepseek-v4-pro[1M]
MODEL = "deepseek-v4-flash"

client = anthropic.Anthropic()   # 自动读 ANTHROPIC_BASE_URL + ANTHROPIC_AUTH_TOKEN

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

# --- 2) 把工具"说明书"给模型看：名字/说明/参数结构 ---
TOOLS = [{
    "name": "get_weather",
    "description": "查询某个城市的当前天气。当用户问天气时使用。",
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

EXEC = {"get_weather": get_weather, "get_current_time": get_current_time}   # 名字 -> 真实函数

# --- 3) 对话历史从这里开始 ---
messages = [{"role": "user", "content": "现在北京时间几点？帮我查一下巴黎现在的天气怎么样？帮我查一下深圳现在天气怎么样？"}]

# --- 4) ★ agentic loop：循环到模型给出最终文字答案为止 ---
while True:
    response = client.messages.create(
        model=MODEL, max_tokens=4096, tools=TOOLS, messages=messages,
    )

    # 情况一：模型想调工具 -> 执行它，把结果喂回去，继续循环
    if response.stop_reason == "tool_use":
        messages.append({"role": "assistant", "content": response.content})
        results = []
        for block in response.content:
            if block.type == "tool_use":
                print(f"[工具请求] 模型想调用: {block.name}({block.input})")
                if block.name == "get_weather" and block.input.get("city") not in SUPPORTED:
                    output = f"错误：暂不支持城市 {block.input.get('city')}。支持：{SUPPORTED}"
                else:
                    output = EXEC[block.name](**block.input)
                # output = EXEC[block.name](**block.input)   # <- 真正执行的是你
                results.append({"type": "tool_result",
                                "tool_use_id": block.id,   # id 必须对上
                                "content": output})
        messages.append({"role": "user", "content": results})
        continue

    # 情况二：模型给最终文字答案 -> 输出并结束
    if response.stop_reason == "end_turn":
        final = next(b.text for b in response.content if b.type == "text")
        print("最终答案:", final)
        break

    # 其它停止原因（截断/拒答等）——后续课程专门处理
    print(f"! 意外停止：{response.stop_reason}")
    break
