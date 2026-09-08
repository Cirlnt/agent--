# 0008-rag-lab.py — 第 8 课实验：检索注入 / RAG 上手
# 配套课件：lessons/0008-rag-intro.html
#
# 主线一句话：模型是「无状态函数」，没背过我们公司的政策；RAG 能答对，不是模型变聪明了，
#   而是你在提问前把【答案所在的那几段原文】检索出来、塞进了这次的 prompt（开卷考试：先翻书再答卷）。
#   步骤：切块 → 每块算向量(embedding) → 提问时把问题也变向量 → 取最相似的 top-k 原文 → 拼进 prompt 作答。
#
# 为什么 DeepSeek 没有、我们要另配 embedding？
#   DeepSeek 官方 API 至今没有 embeddings 端点（2026 实测，api.deepseek.com/embeddings 404）。
#   这是业内共识：用 DeepSeek 做 RAG = 对话走 DeepSeek、向量另配来源。本课向量来源 = 本地 bge 小模型
#   （fastembed + BAAI/bge-small-zh-v1.5，ONNX CPU 跑）→ 零账号、零费用、断网可重跑。
#
# 三镜安排：
#   镜 1  ★ 检索注入才答得出（闭卷会编）——同一道手册题：A 零注入(模型裸答) vs B 注入检索 top-1 原文
#          vs C 把 8 块全塞进去 → 比"答对没"和"喂了多少 token"。
#          题选「紧急发版」：真值=须经 CTO 书面批准 + 发布后 24h 内复盘会，是公司特有流程 → 闭卷猜不中。
#   镜 2  ★ 关键词检索 vs 语义(embedding)检索——用「补充医疗险」同一件事问两遍：
#          照手册原话问（两路都中）vs 换说法问（关键词分掉到 0.11 < 下限 → 断；embedding 仍 0.67 → 中）
#          决定性 = 检索器打分：关键词换说法就没把握，语义靠"意思"兜住。
#   镜 3  偷看内部 + 算账——8 块 chunk 清单、某题的 top-3 相似度条形、三种喂法的 input token 对比
#
# 诚实口径（第 7 课照搬）：检索成败用【确定性判定】——每题标注"应命中的 chunk_id"，
#   打印 top-1 命没命中；模型回答只当佐证，不作唯一证据。
import os, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")      # Windows 控制台防乱码

import anthropic
from fastembed import TextEmbedding

MODEL = "deepseek-v4-flash"
client = anthropic.Anthropic()

# embedding 模型目录 = 课程自带的本地 bge 小模型（agent-lab/models/，git 忽略），
# 完全离线加载，不联网、不花钱。想自己重建/换机器：见代码末尾"附录"。
MODEL_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                          "..", "agent-lab", "models", "bge-small-zh-v1.5"))

TOP_K = 3                    # 镜 3 用：每次注入几块（★ 挑战 B 就改这一个数：1 或 8）
KW_HIT_FLOOR = 0.15          # 关键词检索命中下限：重合度低于它 = 判"没检索到那一页"（防拿噪音当答案）

def sep(t):
    print("\n" + "=" * 12 + " " + t + " " + "=" * 12)

# ---------------------------------------------------------------
# 0) 虚构语料：云杉科技员工手册（模型绝不可能背过 → 检索才答得出）
#    每块 = 一个自洽的主题段落，含具体数字/规则，块与块之间语义分开。
# ---------------------------------------------------------------
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

# 题集 = (代号, 问题, 应命中哪一块)。每题标了"唯一事实来源"chunk → 检索判定用。
#   Q1 紧急发版 → C06（公司特有流程，模型闭卷猜不出 → 镜 1 的 decisive）
#   Q2 骑车看伤 → C04（换说法：几乎不与 C04 字面重合 → 镜 2 的 decisive）
#   Q3 API 限流 → C05（照手册原话问：关键词也够用 → 镜 2 对照组之一）
#   Q4 医疗险"照原话问"→ C04（镜 2 对照组的另一半，跟 Q2 是同一件事）
QUESTIONS = {
 "Q1": ("我负责的下单接口线上出了高危 bug，想在周四的发布窗口之外立刻发一版紧急修复——"
        "公司流程允许吗？要过哪道批准？", "C06"),
 "Q2": ("我上周末骑单车摔伤了，去诊所缝了几针，医药费花了好几百块——公司给员工配的那份医疗补充险，"
        "这种能按什么比例报销吗？", "C04"),
 "Q3": ("云杉控制台的开放接口我调太快被限流了，一分钟到底允许几次？", "C05"),
 "Q4": ("员工补充商业医疗险的门诊费用报销比例是多少？", "C04"),   # 照手册原话问 → 对照组
}
GROUND = {k: v[1] for k, v in QUESTIONS.items()}

# ---------------------------------------------------------------
# 1) embedding：把文字变成向量（本地 bge-small-zh，512 维，¥0）
#    注意：embedding 模型的输出是"数字向量"，不是文字；它是另一类模型，不是对话模型。
# ---------------------------------------------------------------
emb = TextEmbedding("BAAI/bge-small-zh-v1.5", specific_model_path=MODEL_DIR)
DIM = 512
print(f"embedding 模型已加载：BAAI/bge-small-zh-v1.5（本地 CPU，维度 {DIM}，¥0）")

def embed_one(text):
    return next(emb.embed([text]))

def cosine(a, b):
    import numpy as np
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

# 2) 自建最小"向量库"：把 8 块各算一个向量，存成一张 (id, 文本, 向量) 的表
index_vecs = {cid: embed_one(t) for cid, _, t in CHUNKS}
print(f"已建索引：{len(index_vecs)} 块 → 每块一个 {DIM} 维向量。" + "  （所谓向量库 = 这张表 + 余弦排序）")

def search_semantic(query, k=3):
    """语义检索：问题也变向量 → 与 8 块比余弦 → 返回最像的 top-k 块。"""
    qv = embed_one(query)
    scored = sorted(((cosine(qv, index_vecs[cid]), cid, t) for cid, _, t in CHUNKS),
                    reverse=True)
    return scored[:k]

def char_bigrams(s):
    return {s[i:i+2] for i in range(len(s) - 1)}

def search_keyword(query, k=3):
    """字面检索（对照组）：数问题与每块【共有的字符 2-gram 数量】。朴素、但代表"关键词匹配"这一档。"""
    qb = char_bigrams(query)
    scored = sorted(((len(qb & char_bigrams(t)) / max(len(qb), 1), cid, t) for cid, _, t in CHUNKS),
                    reverse=True)
    return scored[:k]

# ---------------------------------------------------------------
# 3) 作答：把检索到的原文注入 prompt，让 flash"开卷"回答
# ---------------------------------------------------------------
SYS_GROUNDED = ("你是「云杉科技」员工助手。请只依据下面的【参考资料】回答问题："
                "资料里有的数字与规则，照资料原文回答；资料里没有，就明确说『手册资料里没有』，不要编。")
SYS_GENERIC  = "你是「云杉科技」的员工助手，请简洁回答员工的问题。"

def ask(question, references="", sys_p=SYS_GROUNDED):
    """references = 注入的原文（可空）。返回模型回答文本。"""
    content = (references + "\n\n问题：" + question) if references else question
    resp = client.messages.create(model=MODEL, max_tokens=400,
                                  thinking={"type": "disabled"},
                                  system=sys_p,
                                  messages=[{"role": "user", "content": content}])
    return "".join(b.text for b in resp.content if b.type == "text").strip()

def in_tokens(question, references="", sys_p=SYS_GROUNDED):
    """量『这种喂法会让模型读到多少 input token』（count_tokens，第 6 课口径，不产生生成）。"""
    content = (references + "\n\n问题：" + question) if references else question
    return client.messages.count_tokens(model=MODEL, system=sys_p,
                                        messages=[{"role": "user", "content": content}]).input_tokens

# ===============================================================
sep("镜 1 · ★ 检索注入才答得出：闭卷会编，开卷照抄")

Q1, Q1_CHUNK = QUESTIONS["Q1"]
ref_top1 = search_semantic(Q1, k=1)[0]                    # 语义检索 top-1
ref_all  = "\n".join(f"[{cid}] {t}" for cid, _, t in CHUNKS)

print(f"  问题：{Q1}")
print(f"  （真值只在 C{Q1_CHUNK[1]} 里：须经 CTO 书面批准 + 发布后 24h 内补复盘会 —— 公司特有流程）")
print(f"  语义检索 top-1 捞到 → {ref_top1[1]}（应命中 {Q1_CHUNK}）｜原文：{ref_top1[2]}\n")

for mode, references, sys_p in [
    ("A 零注入（闭卷，模型裸答）", "", SYS_GENERIC),
    ("B 注入 top-1 原文（开卷）", f"[{ref_top1[1]}] {ref_top1[2]}", SYS_GROUNDED),
    ("C 把 8 块全塞进去（整本给）", ref_all, SYS_GROUNDED),
]:
    ans = ask(Q1, references, sys_p)
    print(f"  {mode:20} 喂入={in_tokens(Q1, references, sys_p):5} token")
    print(f"       模型答：{ans}")
    if mode.startswith("A"):
        print(f"       ↑ 闭卷：模型从没背过手册 → 答案是它凭'常识'编的流程。"
              f" 含『CTO』：{'CTO' in ans} ｜ 含『复盘』：{'复盘' in ans}  ← 期望两个 False（编不出来）")
    elif mode.startswith("B"):
        print(f"       ↑ 把检索 top-1 那段原文塞进去后：含『CTO』：{'CTO' in ans} ｜ 含『复盘』：{'复盘' in ans}  ← 决定性：期望两个 True（照抄）")
    else:
        print(f"       ↑ 8 块全文都喂：也能答对，但 token 是 B 的几倍 → 见镜 3 账。")

print("\n  一句话：模型没换、也没背书——A 答不出是因为这次请求里【没有那段原文】；B 答对是检索把那段原文送了进来。")

# ===============================================================
sep("镜 2 · ★ 关键词 vs 语义：同一件事，换一种说法就分高下")

print("  关键词检索不是没用，它只是『只认字面』。用【补充医疗险】同一件事问两遍来演：")

def show_both(q, label, expect):
    kw1 = search_keyword(q, k=1)[0]
    se1 = search_semantic(q, k=1)[0]
    print(f"\n  {label}\n     问：{q}")
    if kw1[0] >= KW_HIT_FLOOR and kw1[1] == expect:
        kw_tag = f"✅ 重合度 {kw1[0]:.3f} ≥ 下限 {KW_HIT_FLOOR}，字面撞上了，命中 {expect}"
    elif kw1[0] < KW_HIT_FLOOR:
        note = f"（虽然排第一的是 {kw1[1]}，但分低到跟噪音差不多 —— 真实检索器会按下限滤掉，等于没捞到）" if kw1[1] == expect else ""
        kw_tag = f"❌ 重合度 {kw1[0]:.3f} < 下限 {KW_HIT_FLOOR} → 判『没检索到那一页』{note}"
    else:
        kw_tag = f"❌ 重合度够高，但捞到的是 {kw1[1]}（应命中 {expect}）= 捞到错页"
    print(f"     关键词 top-1：{kw1[1]}  {kw_tag}")
    se_tag = f"✅ 余弦 {se1[0]:.3f}，捞对 {expect}" if se1[1] == expect else f"❌ 捞错（{se1[1]}，应命中 {expect}）"
    print(f"     语义   top-1：{se1[1]}  {se_tag}")
    return kw1, se1

Q4, Q4_CHUNK = QUESTIONS["Q4"]      # 对照组：照手册原话问
kw_a, se_a = show_both(Q4, "题 A · 照手册原话问（对照组）", Q4_CHUNK)
Q2, Q2_CHUNK = QUESTIONS["Q2"]      # 换说法：跟 Q4 同一件事
kw_b, se_b = show_both(Q2, "题 B · 换说法问（同一件事，不背条款名）", Q2_CHUNK)

print(f"\n  ↑ 同一个『医疗险』话题：关键词打分从 {kw_a[0]:.2f}（照原话）掉到 {kw_b[0]:.2f}（换说法）→ 断了；"
      f"语义余弦 {se_a[0]:.2f} → {se_b[0]:.2f}，几乎没动。")

# 把两种检索结果分别喂给模型（题 B）→ 看检索断了以后，生成再强也白搭
ref_kw = f"[{kw_b[1]}] {kw_b[2]}" if kw_b[0] >= KW_HIT_FLOOR else ""   # 低于下限 → 检索结果=空
ref_se = f"[{se_b[1]}] {se_b[2]}"
a_kw = ask(Q2, ref_kw)
a_se = ask(Q2, ref_se)
print(f"\n  把两路检索结果分别喂给模型（都走『只依据资料』提示词）：")
print(f"     关键词路：检索={'空' if not ref_kw else kw_b[1] + ' 原文'} → 模型答：{a_kw}")
print(f"        （含『80』：{'80' in a_kw} ← 资料没送进来，答不出那个比例）")
print(f"     语义路　：检索到 C04 原文 → 模型答：{a_se}")
print(f"        （含『80』：{'80' in a_se} ← 决定性：资料送对了，一注入就照抄）")
print("\n  一句话：检索没把对的那页送进来，模型再强也答不出『80%』——RAG 的上限 = 检索那一环。")

# ===============================================================
sep("镜 3 · 偷看内部：top-3 长什么样 + 为什么不全塞")

print("\n  【8 块 chunk】" + "　".join(f"{cid}:{name}" for cid, name, _ in CHUNKS))

for qid in ["Q1", "Q2", "Q3"]:
    q, expect = QUESTIONS[qid]
    top = search_semantic(q, k=TOP_K)
    ok = top[0][1] == expect
    print(f"\n  {qid} 应命中 {expect} ｜ 语义 top-{TOP_K}（{'✅ top-1 命中' if ok else '❌ top-1 未命中'}）：{q}")
    for i, (sim, cid, t) in enumerate(top, 1):
        bar = "█" * int(sim * 40)
        print(f"    top{i}  {cid}  余弦={sim:.3f} {bar:42} {t[:22]}…")

print("\n  【为什么不全塞？】同一道题的三种喂法，模型实际读到的 input token：")
for qid in ["Q1", "Q2", "Q3"]:
    q, _ = QUESTIONS[qid]
    t0 = in_tokens(q)                                   # 零注入
    top = search_semantic(q, k=TOP_K)
    tk = "\n".join(f"[{c}] {t}" for _, c, t in top)
    t3 = in_tokens(q, tk)                               # 注入 top-TOP_K
    t9 = in_tokens(q, ref_all)                          # 全量 8 块
    print(f"    {qid}：零注入 {t0:4} token ｜ 注入 top-{TOP_K} {t3:4} token ｜ 全量 8 块 {t9:4} token")

print("\n怎么读这张表：")
print("  · 零注入：最省，但模型没见过手册 → 只能编（镜 1 的 A 已经演过了）。")
print("  · 注入 top-k：多花 ~150 token 把『答案所在那一页』送进去 → 答得对、还不贵（镜 1 的 B：CTO/复盘会 就是这么答出的）。")
print("  · 全量塞：也能答对，但每道题都拖 8 块全文 → 又贵，长输入还稀释注意力（context rot，第 7 课数据）。")
print("  —— 检索注入 = 只喂『相关那几页』，是 Anthropic『上下文工程』里 read selective 的落地。")
print("  —— 本地 embedding ¥0；这套向量检索不依赖任何网络服务。")

# ---------------------------------------------------------------
# 附录 · 这套环境是怎么搭的（换机器 / 想自己重建时照抄）
#   1) venv 装库（清华源快）：python -m pip install fastembed onnxruntime -i https://pypi.tuna.tsinghua.edu.cn/simple
#   2) 准备本地模型目录（二选一）：
#      · 已经带在 agent-lab/models/bge-small-zh-v1.5 里了 → 什么都不用做，直接跑。
#      · 想重新下载：设 HF_ENDPOINT=https://hf-mirror.com 后跑
#        python -c "from huggingface_hub import snapshot_download; print(snapshot_download('Qdrant/bge-small-zh-v1.5'))"
#        把输出目录里的全部文件拷到 agent-lab/models/bge-small-zh-v1.5/ 即可。
#       （大陆直连 huggingface.co 不通；DeepSeek 官方无 embeddings 端点，所以向量用本地模型。）
#   注意：换过目录就把上面 MODEL_DIR 改一下。
# ---------------------------------------------------------------
