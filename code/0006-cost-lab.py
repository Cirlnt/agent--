# 0006-cost-lab.py — 第 6 课实验：把每次调用算成账（成本与 token）
# 配套课件：lessons/0006-cost-tokens.html
#
# 主线一句话：Agent 烧钱的大头不是"输出贵"，而是——
#   多轮对话/agentic loop 里，每一轮都把整段历史重新发给模型一次。
#   → 输入 token 随轮次线性膨胀：越聊越贵，而且贵得越来越快。
# 四镜安排：
#   镜 1  读 usage —— 一次调用的账单长什么样（input / output / 有没有 cache 字段）
#   镜 2  ★ 多轮 input 膨胀 —— 同一个 agent 连续答几个问题，盯每轮 input_tokens 怎么涨（本课 decisive）
#   镜 3  max_tokens 封顶 —— 同一句话给大/给小的 max_tokens，看 output 账单和 stop_reason 差在哪
#   镜 4  成本换算 —— 把 token 数套价格算成人民币，估算"一个 agent 一个月到底烧多少钱"
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # Windows 控制台防乱码

import anthropic
import time

MODEL = "deepseek-v4-flash"
client = anthropic.Anthropic()

# ---------------------------------------------------------------
# ★ 价格（元 / 百万 tokens）——这是"练手用的常量"，真实价格会变，以官方定价页为准。
#   deepseek-v4-flash 自 2026-08-17 起峰谷分时计价；周六/周日全天按低谷价。
#   （今天若是周末，脚本自动提示你按低谷价看。想换价格，改下面三行即可。）
# ---------------------------------------------------------------
import datetime as _dt
_IS_WEEKEND = _dt.date.today().weekday() >= 5
INPUT_PRICE_PER_M   = 1.5      # 缓存未命中输入（低谷 1.5 / 高峰 3.0）
OUTPUT_PRICE_PER_M  = 4.5      # 输出（低谷 4.5 / 高峰 9.0）
CACHE_HIT_PER_M     = 0.05     # 缓存命中输入（低谷 0.05 / 高峰 0.10）——本课概念对照用
if _IS_WEEKEND:
    print(f"[价格基准] 今天是周{'六' if _dt.date.today().weekday()==5 else '日'}，DeepSeek 全天按低谷价："
          f"输入 ¥{INPUT_PRICE_PER_M}/M、输出 ¥{OUTPUT_PRICE_PER_M}/M、缓存命中输入 ¥{CACHE_HIT_PER_M}/M")
else:
    print(f"[价格基准] 工作日注意：现在是高峰还是低谷时段决定你按哪档价（本脚本固定用低谷价练手，真实账单查官方）")

def cost(in_tok, out_tok):
    """把一次调用的 input/output token 换成人民币（元）。"""
    return in_tok / 1_000_000 * INPUT_PRICE_PER_M + out_tok / 1_000_000 * OUTPUT_PRICE_PER_M

def fen(yuan):
    """元 → 分，取两位小数给人类读。"""
    return f"{yuan*100:.2f} 分"

def show_usage(tag, usage):
    """打印一次 usage 的账单，诚实显示这个端点到底返回了哪些字段。"""
    parts = [f"in={usage.input_tokens}", f"out={usage.output_tokens}"]
    # cache 字段是"可选"的：有的端点返回、有的不返回。用 getattr 探，别假设。
    if getattr(usage, "cache_read_input_tokens", None) is not None:
        parts.append(f"cache_read={usage.cache_read_input_tokens}")
    if getattr(usage, "cache_creation_input_tokens", None) is not None:
        parts.append(f"cache_creation={usage.cache_creation_input_tokens}")
    if getattr(usage, "cache_creation_output_tokens", None) is not None:
        parts.append(f"cache_creation_out={usage.cache_creation_output_tokens}")
    print(f"    {tag} → usage({', '.join(parts)})  账单≈{fen(cost(usage.input_tokens, usage.output_tokens))}")

def sep(t):
    print("\n" + "=" * 14 + " " + t + " " + "=" * 14)

# ---------------------------------------------------------------- 镜 1
sep("镜 1 · 读 usage：一次调用的账单长什么样")

# 1a) 短输入、长输出：写一首长诗，output 会是账单大头
t0 = time.time()
resp = client.messages.create(model=MODEL, max_tokens=2048,
                              messages=[{"role": "user", "content": "用中文写一首八行的小诗，主题是深夜加班，每行出现一次“咖啡”。"}])
u1 = resp.usage
show_usage(f"1a 短输入长输出（写诗，{time.time()-t0:.1f}s）", u1)
print("    观察：in 和 out 谁大？cache_* 字段这次有没有亮？——注意：自动缓存命中是『尽力而为』，")
print("    同一前缀没跑热时 cache_read 就是 0，跑热后第二次起才会亮。别把 cache_read=0 当『端点不支持』。")

# 1b) 把"模型能看到的东西"整个摆出来：system + tools 说明，算一次"纯输入"账单
TOOLS = [{
    "name": "get_weather",
    "description": "查询某个城市的当前天气。只支持：北京、上海、巴黎、纽约。若用户问其它城市，本工具没有数据，不要调用，直接告诉用户暂不支持。",
    "input_schema": {"type": "object",
                     "properties": {"city": {"type": "string", "description": "城市名，如：北京"}},
                     "required": ["city"]},
}]
SYSTEM = "你是「天气」专用助手，只处理北京、上海、巴黎、纽约四城的天气查询。查天气先调用 get_weather；与天气无关的请求不要调用工具，直接告诉用户你只负责天气。"
resp2 = client.messages.create(model=MODEL, max_tokens=512, system=SYSTEM, tools=TOOLS,
                               messages=[{"role": "user", "content": "上海天气怎么样"}])
u2 = resp2.usage
show_usage("1b 带 system+tools 的小请求", u2)
print("    观察：system + 工具说明书（你写的那些字）+ 问题，全都要算 input token——而且它们每次都重发。")
print("    （同一前缀在 1a/1b 间跑热的话，第二次起 cache_read 会亮——这正是镜 2/镜 4 要讲的东西。）")

# ---------------------------------------------------------------- 镜 2
sep("镜 2 · ★ 越聊越贵：每一轮，模型都把整段历史重读一遍（本课 decisive）")
print("同一个 agent 连续答 3 个问题，历史全程保留。模型是『无状态函数』——它不记得上一个请求，")
print("所以你每一轮都得把【全部历史 + system + 工具说明书】重新发一遍。下面两个数是证据：")
print("  · full      = 你这一轮实际发出的完整 prompt（count_tokens 实测）——它只涨不跌，因为没有捷径")
print("  · in/cache_read = 端点账单怎么拆它（重复前缀命中自动缓存=超便宜，新增部分才按全价 input 计）")
print("先感受一句：这个端点会自动缓存重复前缀，所以『越聊越贵』里的 in 会被打折——但打折的是单价，")
print("不是『每一轮都在读越来越长的历史』这件事本身。你盯着 full 看，它永远在涨。")

TOOLS_W = [dict(t) for t in TOOLS]   # 复用镜 1 的 get_weather（四城）
def get_weather(city):
    table = {"北京": "晴，18°C", "上海": "多云，23°C", "巴黎": "雨，14°C", "纽约": "晴，26°C"}
    return table.get(city, f"暂无 {city} 的天气数据")
EXEC_W = {"get_weather": get_weather}
SYSTEM_W = SYSTEM                     # 与镜 1 同款「天气专用助手」

def full_tokens(messages):
    """count_tokens = 官方口径：把这段 messages（+system+tools）完整数一遍，是多少 input token。"""
    return client.messages.count_tokens(model=MODEL, system=SYSTEM_W, tools=TOOLS_W,
                                        messages=messages).input_tokens

def read_total(usage):
    """端点报的『本次模型实际读到的 input』= 新增部分(in) + 命中缓存的重复前缀(cache_read)。"""
    return (usage.input_tokens or 0) + (usage.cache_read_input_tokens or 0)

questions = ["帮我查一下上海的天气", "那北京呢", "巴黎冷不冷"]
messages = []
SUM_NEW_IN = SUM_HIT = SUM_OUT = 0      # 整场对话的账单累加器（供镜 4 换算成钱）
for qn, q in enumerate(questions, 1):
    messages.append({"role": "user", "content": q})
    fc = full_tokens(messages)
    print(f"\n第 {qn} 问「{q}」——此刻整段历史 = {fc} tokens")
    while True:
        resp = client.messages.create(model=MODEL, max_tokens=512, tools=TOOLS_W,
                                      messages=messages, system=SYSTEM_W)
        u = resp.usage
        hit = u.cache_read_input_tokens or 0
        SUM_NEW_IN += u.input_tokens; SUM_HIT += hit; SUM_OUT += u.output_tokens
        print(f"    模型调用：完整prompt(full)≈{read_total(u):<4} = 新增in {u.input_tokens:<4} + 缓存命中 {hit:<4}"
              f"   stop={resp.stop_reason}")
        if resp.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": resp.content})
            results = []
            for block in resp.content:
                if block.type == "tool_use":
                    results.append({"type": "tool_result", "tool_use_id": block.id,
                                    "content": EXEC_W[block.name](**block.input)})
            messages.append({"role": "user", "content": results})
            continue
        messages.append({"role": "assistant", "content": resp.content})   # 真实对话会把最终答复也存进历史
        break

print(f"\n★ 判读（越聊越贵的三层）")
print(f"  ① 每个『模型调用』的 full 都≈此刻整段历史——模型每一轮都把全部历史重读一遍，一次都不少。")
print(f"  ② full 一路涨：第 1 问时整段历史最小，到第 3 问已变大——对话越长，每一轮要付的 input 越多。")
print(f"  ③ 端点把重复前缀放进 cache_read（命中自动缓存，单价≈免费）；新增部分才按全价 input 计。")
print(f"     打折的是『重复读的单价』；『每一轮都在读越来越长的历史』这件事本身，没有任何端点能省掉。")
print(f"     在不开缓存的厂商/端点（如 Anthropic 不带 cache_control），② 的每一分都要按全价付。")

# ---------------------------------------------------------------- 镜 3
sep("镜 3 · max_tokens：它是账单的“封顶”，不是省钱工具")

ASK = "请用中文写一段 300 字左右的散文《窗外的雨》"
for cap in (32, 2048):
    t0 = time.time()
    resp = client.messages.create(model=MODEL, max_tokens=cap,
                                  messages=[{"role": "user", "content": ASK}])
    text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
    show_usage(f"max_tokens={cap:<5}（{time.time()-t0:.1f}s）", resp.usage)
    print(f"    stop_reason={resp.stop_reason}  可见正文 {len(text)} 个汉字")
    if resp.usage.output_tokens >= cap:
        print("    → output_tokens 撞到上限 = 输出被截断了（第 3/5 课：收尾要查 stop_reason）")

print("    ┌ 判读一：max_tokens 是「单次输出账单的天花板」。给 32 = 最坏只烧 32 个输出 token；")
print("    │       给 2048 = 不截断，但最坏会烧到 2048 个输出 token。它封的是「最坏那一笔」，")
print("    │       不管 input 那一头（历史照旧全算）——所以它不是“调大更贵/调小更省”的省钱开关。")
print("    │ 判读二（和第 3 课连起来）：上面 max_tokens=32 那笔，可见正文常常是 0 个字——")
print("    │       output_tokens 里混着 thinking，而 thinking 与正文共享同一个预算；预算太小被 thinking 吃光，")
print("    │       你照样为那 32 个输出 token 付了钱，却一个字都没见到。max_tokens 给太小 = 白付钱 + 被截断。")

# ---------------------------------------------------------------- 镜 4
sep("镜 4 · 成本换算：一个 Agent 一个月到底烧多少钱")
print(f"用当前价格（flash 低谷：in ¥{INPUT_PRICE_PER_M}/M、out ¥{OUTPUT_PRICE_PER_M}/M、")
print(f"缓存命中 in ¥{CACHE_HIT_PER_M}/M）套镜 2 那场 3 问对话的真实 token：")

def cost_cached(new_in, hit_in, out):
    """DeepSeek 自动缓存的实际账单：新增 in 全价，命中缓存的重复前缀按超便宜的命中价。"""
    return (new_in * INPUT_PRICE_PER_M + hit_in * CACHE_HIT_PER_M + out * OUTPUT_PRICE_PER_M) / 1_000_000

full_input = SUM_NEW_IN + SUM_HIT     # 若完全不缓存，每次全量重发应计的 input
bill_nocache = cost(full_input, SUM_OUT)
bill_cached = cost_cached(SUM_NEW_IN, SUM_HIT, SUM_OUT)
print(f"  镜 2 三问对话：新增 in={SUM_NEW_IN}、命中缓存 in={SUM_HIT}、out={SUM_OUT}（模型调用多次）")
print(f"    · 完全不缓存（Anthropic 不带 cache_control 的算法）：把 {full_input} 全按全价 input 计 ≈ {fen(bill_nocache)}")
print(f"    · DeepSeek 自动缓存实际账单：重复前缀命中按 ¥{CACHE_HIT_PER_M}/M 计 ≈ {fen(bill_cached)}")
print(f"      （这就是自动缓存在账单上的样子：同一场对话，省下的都来自『重复读的历史』那份单价。）")

print("\n放大看一个真实小产品（量级感，不是报价）：")
print("  假设：每天 100 个用户 × 每人问 30 个问题 × 30 天；每题平均≈镜 2 里一题的量级")
per_q_full = full_input / len(questions)          # 平均一题要重读的完整 input
per_q_new = SUM_NEW_IN / len(questions)           # 平均一题新增的 input
per_q_out = SUM_OUT / len(questions)
print(f"  平均每题：完整重读 ≈{per_q_full:.0f} in（其中新增≈{per_q_new:.0f}）、输出≈{per_q_out:.0f}")
calls = 100 * 30 * 30        # = 用户问题数（每题内部约 2 次模型调用，账已按“每题”算齐）
full_est = per_q_full * calls
new_est = per_q_new * calls
out_est = per_q_out * calls
print(f"  用户问题数 ≈ {calls:,} 个（每题内部约 2 次模型调用）")
print(f"  完全不缓存月账单 ≈ {cost(full_est, out_est):.1f} 元（≈ {cost(full_est, out_est)*100:.0f} 分）")
print(f"  自动缓存后月账单 ≈ {cost_cached(new_est, full_est-new_est, out_est):.1f} 元")
print("  想省钱的四把扳手：① 别让对话无限长（长对话截断/摘要历史，否则每轮重读的部分越来越贵）")
print("  ② system+工具说明书这类每轮不变的前缀上缓存（DeepSeek 自动、Claude 用 cache_control）")
print("  ③ 短问题用便宜的模型档 ④ 记账：读 usage 才知道钱花哪了，别靠感觉。")
