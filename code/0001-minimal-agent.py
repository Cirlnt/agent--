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


SYSTEM_SCOPED = (
    "你是「天气与时间」专用助手，只处理查天气（仅支持：北京、上海、巴黎、纽约）与"
    "查当前时间；与天气、时间无关的请求（写作、闲聊、知识问答等）不要调用任何工具，直接告诉用户你只负责天气和时间。"
    "查天气：先 get_weather 取回真实数据，最后调用一次 report_weather 结构化收尾；查时间：调用 get_current_time 后用自然语言答复，不要套 report_weather。"
)

EXEC = {"get_weather": get_weather, "get_current_time": get_current_time}   # 名字 -> 真实函数

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
print("多轮天气助手（支持：北京/上海/巴黎/纽约 天气、当前时间；输入 exit 退出）")
while True:
    q = input("\n你: ").strip()
    if q.lower() in ("exit", "quit", "q", "退出"):
        break
    if not q:
        continue
    answer(q)