# 0005-streaming-lab.py — 第 5 课实验：把 Agent 切成流式输出（streaming）
# 配套课件：lessons/0005-streaming.html
#
# 主线一句话：流式不改"模型的生成逻辑"，只改"你什么时候看到字"。
#   非流式 = 服务器把整段回复憋完、整包发你 → 你等的其实是"最后一个 token"的时间；
#   流式   = 服务器边生成边把 token 碎片推给你 → 用户体感的"快"是首字时间（TTFT）。
# 四镜安排：
#   镜 1  整段等 vs 逐字蹦 —— 用时长和首字延迟体会差别（重点：别比内容，模型两次会写不同诗）
#   镜 2  打开引擎盖 —— 裸 create(stream=True)，看 streaming 到底推了哪些事件
#   镜 3  高级助手 —— messages.stream() 的 text_stream（剥掉 thinking）与 get_final_message()
#   镜 4  ★ 同一份 agentic loop，只切一个 streaming 开关 —— 行为必须一致（本课 decisive）
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # Windows 控制台防乱码

import anthropic
import time

MODEL = "deepseek-v4-flash"
client = anthropic.Anthropic()

def sep(t):
    print("\n" + "=" * 14 + " " + t + " " + "=" * 14)

# ---------------------------------------------------------------- 镜 1
sep("镜 1 · 整段等 vs 逐字蹦（同一首长诗，非流式与流式各写一次）")

LONG_ASK = "请用中文写一首十二行的小诗，主题是大海，每一行都要自然出现一次“浪”。"

# 1a) 非流式：客户端真的什么也看不到，直到整段生成完
t0 = time.time()
resp = client.messages.create(model=MODEL, max_tokens=2048,
                              messages=[{"role": "user", "content": LONG_ASK}])
wall = time.time() - t0
poem1 = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
print(f"[1a 非流式] 你干等了 {wall:.2f}s，然后整首诗一次性出现（{len(poem1)} 字）。")

# 1b) 流式：一边生成一边把字推出来
t0 = time.time()
first_t = None
poem2 = []
with client.messages.stream(model=MODEL, max_tokens=2048,
                            messages=[{"role": "user", "content": LONG_ASK}]) as s:
    for chunk in s.text_stream:          # text_stream：只吐"给用户看的字"，thinking 已被剥掉
        if first_t is None:
            first_t = time.time() - t0
            print(f"[1b 流式] 首段文字在 {first_t*1000:.0f}ms 后出现，下面逐字蹦：\n")
        print(chunk, end="", flush=True)
        poem2.append(chunk)
    fin = s.get_final_message()
wall2 = time.time() - t0
print(f"\n[1b 流式] 全诗共 {wall2:.2f}s 蹦完（{sum(len(c) for c in poem2)} 字），总时长和非流式差不多。")

print("\n观察：非流式把 2.x 秒全憋成'无声等待'；流式让你在 1.x 秒就开始读。"
      "\n（两首诗内容不同是正常的——模型每次抽样都不同；流式不改生成，只改投递。）")

# ---------------------------------------------------------------- 镜 2
sep("镜 2 · 打开引擎盖：裸 create(stream=True)，看流里到底有什么事件")

print("先关掉 thinking，让事件序列干干净净（此端点默认会先吐一段思考，等下在镜 3 你会看到它）。")
stream = client.messages.create(
    model=MODEL, max_tokens=512, thinking={"type": "disabled"}, stream=True,
    messages=[{"role": "user", "content": "只回复四个字：收到收到。"}],
)
for event in stream:
    if event.type == "message_start":
        print("  message_start            ← 一条消息开始")
    elif event.type == "content_block_start":
        print(f"  content_block_start  index={event.index} 类型={event.content_block.type}")
    elif event.type == "content_block_delta":
        d = event.delta
        if getattr(d, "type", "") == "text_delta":
            print(f"  content_block_delta  index={event.index} text_delta → 一个字/词：{d.text!r}")
    elif event.type == "content_block_stop":
        print(f"  content_block_stop   index={event.index}   ← 这块内容结束了")
    elif event.type == "message_delta":
        print(f"  message_delta         stop_reason={event.delta.stop_reason}   ← 停止原因藏在这里")
    elif event.type == "message_stop":
        print("  message_stop           ← 一条消息结束")
print("事件序列就这几类。text 块由许多个 text_delta 碎片拼成。")

# ---------------------------------------------------------------- 镜 3
sep("镜 3 · 带工具时：tool_use 参数也是“半个半个”来的 + 高级助手怎么用")

TOOLS = [{
    "name": "get_weather",
    "description": "查询某个城市的当前天气。只支持：北京、上海。",
    "input_schema": {"type": "object",
                     "properties": {"city": {"type": "string", "description": "城市名，如：北京"}},
                     "required": ["city"]},
}]

# 3a) 先用裸流看一个工具调用长什么样（保留 thinking，看它排在第几块）
print("3a) 裸流 + 工具调用 —— 留意 input_json_delta（tool_use 参数的碎片）：")
stream = client.messages.create(
    model=MODEL, max_tokens=2048, tools=TOOLS, stream=True,
    messages=[{"role": "user", "content": "帮我查一下北京的天气"}],
)
partial = []
n_th = 0
for event in stream:
    if event.type == "content_block_start":
        cb = event.content_block
        if cb.type == "tool_use":
            if n_th:
                print(f"    （前导 thinking 块共 {n_th} 段增量，已折叠——思考先走完，才轮到 tool_use）")
            print(f"    content_block_start index={event.index} → tool_use name={cb.name}（参数开始流式抵达）")
    elif event.type == "content_block_delta":
        d = event.delta
        dt = getattr(d, "type", "")
        if dt == "input_json_delta":
            partial.append(d.partial_json)
            print(f"    content_block_delta index={event.index} input_json_delta 碎片：{d.partial_json!r}")
        elif dt == "thinking_delta":
            n_th += 1
            if n_th == 1:
                print("    （第一段 thinking_delta……模型的思考碎片，通常不展示给用户）")
    elif event.type == "message_delta":
        print(f"    message_delta stop_reason={event.delta.stop_reason}")
json_args = "".join(partial)
print(f"    全部 input_json_delta 拼起来 = {json_args!r}  ← 必须等 content_block_stop 收齐才能 json.loads/执行！")

# 3b) 高级助手：messages.stream() 一把抓（text_stream + get_final_message）
print("\n3b) 同一个请求，改用高级助手 messages.stream()：")
t0 = time.time()
with client.messages.stream(model=MODEL, max_tokens=2048, tools=TOOLS,
                            messages=[{"role": "user", "content": "帮我查一下北京的天气"}]) as s:
    print("    给用户看的字（thinking 已剥）:", end=" ")
    for chunk in s.text_stream:
        print(chunk, end="", flush=True)
    final = s.get_final_message()      # 把流重新拼成一个对象
print(f"\n    get_final_message() 返回 stop_reason={final.stop_reason}  (耗时 {time.time()-t0:.2f}s)")
for b in final.content:
    if getattr(b, "type", "") == "tool_use":
        print(f"    里面的 tool_use 块：name={b.name} input={b.input}  ← 已是 dict，可直接执行")
        print(f"    usage: in={final.usage.input_tokens} out={final.usage.output_tokens}  ← 也在对象上")
# 注意：final.content 里第一个是 ThinkingBlock（index=0），text_stream 自动把它过滤掉了。

# ---------------------------------------------------------------- 镜 4
sep("镜 4 · 决定性：同一份 agentic loop，只切 streaming 开关，行为必须一致")

def get_weather(city):
    table = {"北京": "晴，18°C", "上海": "多云，23°C"}
    return table.get(city, f"暂无 {city} 的天气数据")

def report_weather(city, condition):
    return f"最终答复：{city} {condition}"     # 出口工具：真实项目里这里可能只是登记/返回

TOOLS_AGENT = [
    {"name": "get_weather",
     "description": "查询某城市当前天气。只支持：北京、上海。用户问其它城市别调本工具，直接说暂不支持。",
     "input_schema": {"type": "object",
                      "properties": {"city": {"type": "string", "description": "城市名，如：北京"}},
                      "required": ["city"]}},
    {"name": "report_weather",
     "description": "★出口工具★ 已查到天气、准备答复用户时，把最终结果结构化提交；提交后不要再输出自然语言。",
     "input_schema": {"type": "object",
                      "properties": {"city": {"type": "string"},
                                     "condition": {"type": "string", "description": "get_weather 拿到的天气串"}},
                      "required": ["city", "condition"]}},
]
EXEC = {"get_weather": get_weather}
SYSTEM = ("你是「天气」专用助手，只处理北京、上海两城的天气查询。查天气：先 get_weather 取真实数据，"
          "最后调用一次 report_weather 结构化收尾。与天气无关的请求不要调任何工具，直接告诉用户你只负责天气。")

def run_weather(question, streaming: bool, live_text: bool = False):
    """同一套 agentic loop，唯一区别在"怎么收这一轮的 response"。"""
    messages = [{"role": "user", "content": question}]
    log = []
    while True:
        if streaming:
            # 流式：调用签名的字段一字不差，只是外面包了 with messages.stream()
            with client.messages.stream(model=MODEL, max_tokens=2048,
                                        tools=TOOLS_AGENT, messages=messages,
                                        system=SYSTEM) as s:
                if live_text:
                    # 真·逐字往外蹦：每个可见字符一到就打印（像打字机）
                    text_parts = []
                    for chunk in s.text_stream:
                        print(chunk, end="", flush=True)
                        text_parts.append(chunk)
                else:
                    text_parts = [c for c in s.text_stream]          # 只收不显示
                response = s.get_final_message()                 # ★ 拼回和非流式一模一样的 message
            if text_parts and not live_text:
                log.append("(流式) 圆场话：" + "".join(text_parts))
        else:
            response = client.messages.create(model=MODEL, max_tokens=2048,
                                              tools=TOOLS_AGENT, messages=messages,
                                              system=SYSTEM)
            text_parts = [b.text for b in response.content if getattr(b, "type", "") == "text"]

        if response.stop_reason == "tool_use":
            if text_parts and not streaming:
                log.append("(非流式) 圆场话整段返回：" + "".join(text_parts))
            messages.append({"role": "assistant", "content": response.content})
            results = []
            exit_payload = None
            for block in response.content:
                if getattr(block, "type", "") != "tool_use":
                    continue
                log.append(f"[工具请求] {block.name}({block.input})")
                if block.name == "report_weather":
                    exit_payload = block.input
                    continue
                results.append({"type": "tool_result", "tool_use_id": block.id,
                                "content": EXEC[block.name](**block.input)})
            if exit_payload is not None:
                log.append(f"✅ 结构化出口：{exit_payload}")
                return log
            messages.append({"role": "user", "content": results})
        elif response.stop_reason == "end_turn":
            log.append("最终答案：" + "".join(text_parts))
            return log
        else:
            log.append(f"! 意外停止：{response.stop_reason}")
            return log

print("同一句「帮我查一下上海的天气」，跑两遍——一遍非流式、一遍流式（流式这遍，模型若先吐圆场话你会看见它逐字蹦出来）：")
log_a = run_weather("帮我查一下上海的天气", streaming=False)
print("\n--- 非流式那一遍（模型若说圆场话，是整段一次性返回） ---")
for line in log_a:
    print("  " + line)
log_b = run_weather("帮我查一下上海的天气", streaming=True, live_text=True)
print("\n--- 流式那一遍（上面若冒出“我来帮您查询上海的天气。”之类，就是正在逐字打字） ---")
for line in log_b:
    print("  " + line)
print("\n→ 关键判断：两遍的工具调用序列、结构化出口是否完全一致？"
      "\n  （流式不改 agent 逻辑，只改字的投递方式。能证明这一点，你就抓住了本课。）")
