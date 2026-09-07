# 0007-memory-context-lab.py — 第 7 课实验：Agent 怎么记得住？（多轮状态 + 上下文管理）
# 配套课件：lessons/0007-memory-context.html
#
# 主线一句话：模型是「无状态函数」，它本身什么都不记得——Agent 能"记住"，
#   唯一原因是【你每轮把历史原样喂回去】。多轮状态 = 你代码里维护的 messages；
#   对话太长后怎么"压缩历史"，本课用三招对比：keep-all / 滑动窗口 / 滚动摘要。
#
# 三镜安排：
#   镜 1  ★ 无状态实锤（真实 agent + 工具）——同一个问题"我第一次问的是哪个城市？"，
#        带历史能答、冷启动（零历史）答不出 → 证明"记得"全靠喂进去的历史
#   镜 2  ★ 三招管长对话（固定对话回放）——三种策略吃【同一段】6 轮备忘对话：
#        (a) 管理期 prompt：全留每轮越喂越大（量出第 6 课的曲线）；窗口/摘要封顶多少
#        (b) 回忆期：同样的"最早事实"题，事实在输入里还在不在（确定性）+ 模型答对没
#   镜 3  摘要长什么样 —— 把滚动摘要压出来的那段文字打印出来，亲眼看看保住了什么
#
# 为什么镜 2 用"回放"而不是真的让模型跑一遍？
#   镜 1 已证明"靠历史才记得"。镜 2 想单独比较三种策略——就该让它们吃到【完全一样】的对话，
#   否则模型每次回答内容不同，会把"策略差异"和"回答随机性"搅在一起。对话是固定脚本，
#   策略只决定"哪几轮留下、哪几轮压成摘要再喂"，干净地隔离变量。
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # Windows 控制台防乱码

import anthropic

MODEL = "deepseek-v4-flash"
client = anthropic.Anthropic()

def sep(t):
    print("\n" + "=" * 12 + " " + t + " " + "=" * 12)

# ---------------------------------------------------------------
# 镜 1 专用：真实多轮天气 agent（工具拿"确定性温度"，跟 0001 同款）
# ---------------------------------------------------------------
WEATHER = {"北京": "晴，18°C", "上海": "多云，23°C", "巴黎": "雨，14°C", "纽约": "晴，26°C"}
SUPPORTED = list(WEATHER)

def get_weather(city):
    return WEATHER.get(city, f"暂无 {city} 的天气数据")

def get_current_time():
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

EXEC = {"get_weather": get_weather, "get_current_time": get_current_time}
TOOLS = [
    {"name": "get_weather", "description": "查询某个城市的当前天气。只支持：" + "、".join(SUPPORTED) + "。",
     "input_schema": {"type": "object", "properties": {"city": {"type": "string", "description": "城市名，如：北京"}},
                      "required": ["city"]}},
    {"name": "get_current_time", "description": "查询当前时间。", "input_schema": {"type": "object", "properties": {}}},
]
SYSTEM_W = ("你是对话助手，说话简洁。用户明确让『查XX的天气/现在几点』时，先调用 get_weather / get_current_time "
            "拿到真实数据，回答时把工具返回的天气原文复述出来（如：多云，23°C）；没让查时不要调工具。")

def agent_ask(history, question):
    """跑完一个问题（含工具往返），把一问一答追加进 history（记录层只存最终文本）。
    返回这一问的答复。"""
    working = [dict(m) for m in history] + [{"role": "user", "content": question}]
    while True:
        resp = client.messages.create(model=MODEL, max_tokens=1024,
                                      system=SYSTEM_W, tools=TOOLS, messages=working)
        if resp.stop_reason == "tool_use":
            working.append({"role": "assistant", "content": resp.content})
            results = []
            for b in resp.content:
                if b.type != "tool_use":
                    continue
                if b.name == "get_weather" and b.input.get("city") not in SUPPORTED:
                    out = f"错误：暂不支持城市 {b.input.get('city')}。支持：{'、'.join(SUPPORTED)}"
                else:
                    out = EXEC[b.name](**b.input)
                results.append({"type": "tool_result", "tool_use_id": b.id, "content": out})
            working.append({"role": "user", "content": results})
            continue
        text = "".join(b.text for b in resp.content if b.type == "text").strip()
        history.append({"role": "user", "content": question})
        history.append({"role": "assistant", "content": text})
        return text

# ---------------------------------------------------------------
# 镜 2/3 专用：一段固定 6 轮"出游备忘"对话（事实由我们写死、可复现）
#   两道回忆题盯最早轮里出现、后面不再重复的代号：
#     HO1251 = 最初航班号（只在第 1 轮与第 4 轮"原 HO1251"里出现）
#     881204 = 会议号（第 1 轮后从未再提）
# ---------------------------------------------------------------
ROUNDS = [   # (user, assistant)
 ("帮我存份出游备忘，回头我会抽查：①周六坐 HO1251 航班去上海（当地多云 23°C）；②周日逛巴黎美术馆（预报雨，14°C）；③下周三和客户开视频会（会议号 881204）。",
  "记好了：周六 HO1251 飞上海（多云 23°C）；周日巴黎美术馆（雨，14°C）；下周三视频会，号 881204。随时抽查。"),
 ("巴黎美术馆改到周六晚上，周日上午空出来。",
  "已改：巴黎美术馆→周六晚上；周日上午空出来了。"),
 ("周日上午加一个卢浮宫，要逛一整个上午。",
  "已加：周日上午卢浮宫。现在周日只剩下午了。"),
 ("对了，周六的航班改成 HO1252，晚一小时出发。",
  "已改：周六 HO1252（原来那班 HO1251 不坐了），晚一小时。"),
 ("我下周三开会之前想看一版提纲，先提醒我记着。",
  "记下了：下周三会前提醒你备好提纲。"),
 ("行，那按目前的样子把整份备忘念一遍，按天来。",
  "【周六】HO1252 晚一班飞上海，晚上巴黎美术馆；【周日】上午卢浮宫、下午空；【周三】下午和客户视频会，会前先看提纲。"),
]
QUIZ = [
    ("最开始那份备忘里，我周六原定坐的航班号是多少？", "HO1251"),
    ("我下周三和客户的视频会，会议号是多少？", "881204"),
]

SYSTEM_P = ("你是对话助手。用户问『之前对话里提到过的事』（航班号、会议号、原定安排等），就照你看到的"
            "对话历史回答；历史里有就说，没有就直说『历史里没有』，不要编造。")

def summarize_text(old_rounds):
    """把一段旧对话压成要点。每次做这件事 = 多花一次模型调用（它不是免费的）。
    注意：压缩器也是模型——保不保留某个细节，取决于它怎么理解 + 你的压缩指令点没点名。"""
    sys_p = ("你是对话压缩器。把下面这段旧对话压成一段简洁中文要点，供之后的模型接着这段对话用。"
             "必须保留所有数字代号（航班号 HO1251/HO1252、会议号 881204）、日期安排、以及『原来→后来改成』这类改动。"
             "只输出压缩结果，不要寒暄。")
    prompt = "\n".join(f"用户：{u}\n助手：{a}" for u, a in old_rounds)
    resp = client.messages.create(model=MODEL, max_tokens=500, thinking={"type": "disabled"},
                                  system=sys_p, messages=[{"role": "user", "content": prompt}])
    return "".join(b.text for b in resp.content if b.type == "text").strip()

def flatten(rounds):
    msgs = []
    for u, a in rounds:
        msgs += [{"role": "user", "content": u}, {"role": "assistant", "content": a}]
    return msgs

def recall(history_msgs, summary, probe):
    """记忆测验：不带工具。把【此刻会喂给模型的文本】(summary + history) 和问题发过去。
    返回 (模型回答, 实际发进去的纯文本)。"""
    sent = (summary + "\n" if summary else "") + " ".join(m["content"] for m in history_msgs if isinstance(m["content"], str))
    content = (sent + "\n\n我的问题：" + probe) if sent else probe
    resp = client.messages.create(model=MODEL, max_tokens=512, thinking={"type": "disabled"},
                                  system=SYSTEM_P, messages=[{"role": "user", "content": content}])
    text = "".join(b.text for b in resp.content if b.type == "text").strip()
    return text, sent

def count_prompt(msgs, summary=""):
    """量『这段文字喂给模型会是多大的输入』（官方 count_tokens：不受缓存影响、不产生生成）。"""
    sent = (summary + "\n" if summary else "") + " ".join(m["content"] for m in msgs if isinstance(m["content"], str))
    return client.messages.count_tokens(model=MODEL, system=SYSTEM_P,
                                        messages=[{"role": "user", "content": sent + "\n\n我的问题：？"}]).input_tokens

# ===============================================================
sep("镜 1 · ★ 无状态实锤：历史在，才记得住（真实 agent + 工具）")

h = []
r1 = agent_ask(h, "帮我查一下上海的天气")
print(f"  第 1 问「帮我查一下上海的天气」→ {r1}")
r2 = agent_ask(h, "那北京呢？")
print(f"  第 2 问「那北京呢？」→ {r2}   ← 能接上，因为输入里有第 1 问")

ans, sent = recall(h, "", "我第一次问的是哪个城市的天气？")
print(f"  回忆题「我第一次问的是哪个城市的天气？」→ 模型答：{ans}")
print(f"      此刻喂给模型的文本含『上海』：{'上海' in sent}  ← 事实在输入里，才答得出")

ans2, sent2 = recall([], "", "我第一次问的是哪个城市的天气？")
print(f"\n  冷启动对照（零历史直接问同一题）→ 模型答：{ans2}")
print(f"      此刻喂给模型的文本含『上海』：{'上海' in sent2}  ← 没有事实可考，只能承认不知道/追问")
print("\n  结论：模型本身无记忆；『记得』= 那轮对话的文字还在你喂进去的输入里。")

# ===============================================================
sep("镜 2 · ★ 三招管长对话：同一段 6 轮备忘，谁记得住、prompt 各多大")

KEEP = 2                                  # 滑动窗口保留几轮（★ 挑战 B 就改这一个数）
keep_msgs = flatten(ROUNDS)
win_msgs  = flatten(ROUNDS[-KEEP:])       # 只留最近 KEEP 轮
sum_text  = summarize_text(ROUNDS[:-1])   # 摘要：老 5 轮压成一句（一次模型调用）
sum_msgs  = flatten(ROUNDS[-1:])          # 摘要策略只留最近 1 轮原文

print("\n【管理期】若按该策略管理，每轮要喂的 prompt 会多大？（count_tokens 实测，第 6 课口径：每轮模型整段重读）")
grow = [count_prompt(flatten(ROUNDS[:k])) for k in range(1, len(ROUNDS) + 1)]
print(f"  A 全留：第1→6轮喂的 prompt = {grow}   ← 只涨不跌，第 6 课『越聊越贵』的曲线照搬")
print(f"  B 窗口：永远只留最近 {KEEP} 轮 → prompt 封顶 ≈ {count_prompt(win_msgs)} token（不随对话变长）")
print(f"  C 摘要：摘要({len(sum_text)}字) + 最近 1 轮 → prompt 封顶 ≈ {count_prompt(sum_msgs, sum_text)} token"
      f"（比窗口略高，因为多了那句摘要；外加每压一次付一次摘要调用）")

print("\n【回忆期】同样的两道『最早事实』题，每种策略喂进去的输入里，事实还在吗？")
summary_rows = []
for label, msgs, summary, extra in [("A 全留", keep_msgs, "", ""),
                                    ("B 窗口", win_msgs, "", ""),
                                    ("C 摘要", sum_msgs, sum_text, f"（摘要调用 +1）")]:
    marks, answers = [], []
    for probe, kw in QUIZ:
        ans, sent = recall(msgs, summary, probe)
        has, hit = kw in sent, kw in ans
        marks.append(has)
        answers.append(ans)
        tag = "✅事实在输入里" if has else "❌事实被裁掉了"
        print(f"  {label} | 题「{probe}」→ {tag}；模型答：{ans}")
    print(f"           （{label} 的真实模型调用：2 次回忆{extra}）")
    summary_rows.append((label, marks, answers))

sep("镜 3 · 三招对照总表 + 摘要长什么样")
for label, marks, answers in summary_rows:
    v = " / ".join("✅记得" if m else "❌忘了" for m in marks)
    print(f"  {label:12} 最早事实测验：{v}   模型答：{answers[0][:34]}…")
print("\n  C 滚动摘要压出来的文字（这就是那 5 轮历史在窗口外的『替身』）：")
print(f"    「{sum_text}」")

print("\n怎么读这张表：")
print("  · A 全留：两道题都记得 ✅，代价是 prompt 每轮只涨不跌——第 6 课说的『越聊越贵』，总有一会撞上下文上限。")
print("  · B 窗口：prompt 封顶、最省，但最早两轮被整段裁掉 → 航班号/会议号不在输入里，只能答错或承认『历史里没有』。")
print("  · C 摘要：prompt 也封顶（略贵：多付一次摘要调用），老历史的『要义』被搬进摘要 → 能答上。")
print("  —— 但注意摘要保住什么，取决于压缩时有没有把那串数字写进去（压缩器也是模型）。想要『记得久 + 不无限烧 + 不丢细节』，")
print("     窗口/摘要都做不到——出路是把历史/知识存到外面、每轮只把最相关的几段检索进来喂（检索注入 = RAG，下一课）。")
