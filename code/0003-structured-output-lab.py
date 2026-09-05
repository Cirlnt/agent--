# structured_output_lab.py — 第 3 课实验：同一句"人话"，三种姿势让它变成"结构"
# 配套课件：lessons/0003-structured-output.html
#
# 一句话预习：程序要的是数据（dict），模型给的是文本（可能带解释、围栏、甚至被截断为空）。
# 三种姿势 = 三种"拿到 dict"的路子。你会看到：有的路子要你一遍遍剥文本（打地鼠），
# 有的路子模型交给你的时候天生就是 dict（因为它走的是"工具调用"这条机器通道）。
#
# 端点仍是 DeepSeek 的 Anthropic 兼容端点，写法与真 Anthropic 一致。
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # Windows 控制台防乱码
import json
import anthropic

MODEL = "deepseek-v4-flash"   # 想更强换成 "deepseek-v4-pro[1M]"
client = anthropic.Anthropic()

# ============================================================
# 公共素材：一句用户"人话"，我们想把它抽成结构化字段
#   {action: 动作, target: 对象, when: 时间}   去喂给下游程序
# ============================================================
S_CLEAN = "帮我查一下后天上海天气怎么样"
S_QUOTE = '记下：老板说"周六前务必回邮件"'

NAIVE_SCHEMA_HINT = ('{"action":"查天气|订票|设提醒|其它","target":"目标文本(原样抄,可含引号)",'
                     '"when":"时间词,没有给空串"}')

# ------------------------------------------------------------
# 镜 1 用：只靠嘴"求"它输出 JSON（不注册任何工具）
# ------------------------------------------------------------
SYSTEM_NAIVE = (
    "你是意图路由器。把用户的句子解析成 JSON，字段为：" + NAIVE_SCHEMA_HINT +
    "。只输出这个 JSON 对象本身，禁止 markdown 代码块，禁止任何解释或前后缀文字。"
)

# 同一个解析任务，但要求"先给用户一句人话确认再输出 JSON"——
# 真实世界里开发者经常这样顺口加一句，模型照做，输出就"不纯"了。
SYSTEM_NAIVE_TALK = (
    "你是意图路由器。用户说完一句话后，你先用一句自然语言回应确认（如：好的，已记下），"
    "然后再另起一行，把解析结果输出为 JSON：" + NAIVE_SCHEMA_HINT + "。"
)

def robust_json(text):
    """一套"尽力剥出 JSON"的解析。注意它每加一个分支，都是在打一只新地鼠。"""
    if not text.strip():
        return False, "输出为空（可能被 max_tokens 截断在思考阶段）"
    candidates = [text]                     # 候选 1：整段直接 loads
    a, b = text.find("{"), text.rfind("}")  # 候选 2：剥掉前后缀文字只留 {...}
    if a != -1 and b > a:
        candidates.append(text[a:b+1])
    for c in candidates:
        c = c.strip()
        if c.startswith("```"):             # 候选 3：剥 markdown 围栏 ```json ... ```
            c = c.strip("`").strip()
            if c.startswith("json"):
                c = c[4:].strip()
        try:
            return True, json.loads(c)
        except Exception as e:
            last_err = f"{type(e).__name__}: {e}"
    return False, last_err

def pose_naive(sentence, system, label):
    """镜 1：让模型直接输出 JSON 文本，我们再用 json.loads 解析。
    对比两种写法：直接解析整段 vs 用 robust_json 的剥除逻辑去救。"""
    print("\n" + "=" * 66)
    print(label)
    print("=" * 66)
    print(f"用户说：{sentence}")
    resp = client.messages.create(
        model=MODEL, max_tokens=4096, system=system,   # 预算给足，别让文本输出被"思考"饿死（见课件陷阱②）
        messages=[{"role": "user", "content": sentence}],
    )
    text = "".join(b.text for b in resp.content if b.type == "text")
    print(f"模型返回（文本，共 {len(text)} 字）：{text!r}")

    # 写法 1：天真地 json.loads 整段——很多人就这样写
    strict_ok, strict_data = False, None
    try:
        strict_data = json.loads(text)
        strict_ok = True
        print("直接 json.loads(整段)：✅ 成功 ->", strict_data)
    except Exception as e:
        print(f"直接 json.loads(整段)：❌ 崩了 -> {type(e).__name__}: {e}")

    # 写法 2：真崩了才动用剥除逻辑（剥围栏/剥前后缀）去救
    if strict_ok:
        print("   （这一镜剥除逻辑没派上用场。但注意：能救它全靠一堆 if 分支——")
        print("     换模型/加需求就可能冒出新形态，剥除逻辑永远在『补下一只地鼠』。）")
    else:
        ok, data = robust_json(text)
        if ok:
            print(f"上剥除逻辑救：✅ 救回来了 -> {data}")
            print("   注意：为了救它，我们得亲手写『剥围栏、剥前后缀』——这就是打地鼠：")
            print("   每换一个模型/每加一句需求，都可能冒出一只新地鼠，你就得再补一个分支。")
        else:
            print(f"上剥除逻辑救：❌ 连剥除逻辑也无能为力 -> {data}")

# ------------------------------------------------------------
# 镜 2 / 镜 3 用：一个"输出工具"。模型想"把答案交给你"就必须调用它，
# 你从 block.input 拿到的天生就是 dict（不用 json.loads）。
# ------------------------------------------------------------
OUT_TOOL = {
    "name": "submit_request",
    "description": "当用户给出一句自然语言的请求时，调用本工具把它结构化地提交出来"
                   "（抽取：动作 / 对象 / 时间）。target 要原样抄用户原话里的关键短语，"
                   "可能含引号与标点；when 抄时间词，用户没提就给空字符串。"
                   "把抽取结果通过本工具返回，不要直接回话。",
    "input_schema": {
        "type": "object",
        "additionalProperties": False,   # 声明"不欢迎多余字段"（端点未必替你真拦，见课件）
        "properties": {
            "action": {"type": "string", "enum": ["查天气", "订票", "设提醒", "其它"]},
            "target": {"type": "string", "description": "对象/关键短语，原样抄，可含引号"},
            "when":   {"type": "string", "description": "时间词，没提给空串"},
        },
        "required": ["action", "target", "when"],
    },
}

def pose_tool(sentence, label, tool_choice=None):
    """镜 2/3：走"输出工具"通道。tool_choice 传入则尝试让模型必须用工具。"""
    print("\n" + "=" * 66)
    print(label)
    print("=" * 66)
    print(f"用户说：{sentence}")
    kwargs = dict(model=MODEL, max_tokens=4096, tools=[OUT_TOOL],
                  messages=[{"role": "user", "content": sentence}])
    if tool_choice is not None:
        kwargs["tool_choice"] = tool_choice
    resp = client.messages.create(**kwargs)
    print(f"stop_reason = {resp.stop_reason}")
    for b in resp.content:
        if b.type == "tool_use":
            print(f"✳ 模型调用 {b.name}，block.input 的类型 = {type(b.input).__name__}")
            print(f"   block.input = {b.input}")
            print(f"   注意 target 里的引号原样保留：{b.input.get('target')!r}")
            print("   → 我们全程没有调用 json.loads——因为它交给我们时就已经是 dict")
        elif b.type == "text" and b.text.strip():
            print(f"✍ 模型直接回话（没走工具出口）：{b.text.strip()}")
    return resp

def force_named_choice():
    """小实验：指名强制 tool_choice {type:'tool', name} 在本端点会怎样？
    结论已实测：DeepSeek 兼容端点会 400 拒绝（thinking 模式不支持）。
    这就是"厂商差异要实测、别照搬文档假设"。"""
    print("\n" + "=" * 66)
    print("小实验 · tool_choice = {type:'tool', name:...}（指名强制，Anthropic 支持）")
    print("=" * 66)
    try:
        client.messages.create(
            model=MODEL, max_tokens=512, tools=[OUT_TOOL],
            tool_choice={"type": "tool", "name": "submit_request"},
            messages=[{"role": "user", "content": "查天气"},
                      {"role": "assistant", "content": "查天气，走工具"},
                      {"role": "user", "content": "帮我把这记下来"}],
        )
        print("（居然没报错）")
    except Exception as e:
        print(f"端点返回：{e}")

if __name__ == "__main__":
    # ---------- 镜 1：裸 JSON，靠解析 ----------
    pose_naive(S_CLEAN, SYSTEM_NAIVE,
               "镜 1a · 纯 JSON：干干净净的一句话，模型有时直接给你一份干净 JSON")
    pose_naive(S_QUOTE, SYSTEM_NAIVE,
               "镜 1b · 内容含引号：target 要带 \" 引号，转义做不做全靠模型守规矩")
    pose_naive(S_CLEAN, SYSTEM_NAIVE_TALK,
               "镜 1c · 你顺嘴要了句人话确认：输出立刻『不纯』，直接 json.loads 就崩")

    # ---------- 镜 2：工具即输出（不强制，看模型会不会自觉走） ----------
    pose_tool(S_QUOTE, "镜 2 · 工具即输出：把「结构」定义成一个输出工具，让模型调用它来交答案")

    # ---------- 镜 3：加锁（tool_choice 尽量让「必须走工具」） ----------
    pose_tool(S_QUOTE, "镜 3 · tool_choice={'type':'any'}：让这一轮必须走工具",
              tool_choice={"type": "any"})

    # ---------- 小实验：指名强制在本端点的真实反应 ----------
    force_named_choice()
