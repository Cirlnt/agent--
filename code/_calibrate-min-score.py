# _calibrate-min-score.py — 挑战 B 步骤 1：给 0001 的检索侧标定 MIN_SCORE
#
# 这不是 agent 运行时要跑的东西，而是【离线一次性分析】：产物是一个数（MIN_SCORE）。
# 所以独立成文件，不塞进 0001 —— 真实的 RAG 项目也是这么干的：
# 标定离线做，运行时只带那个数。
#
# 它干三件事（对应 0009 镜 2 但那面镜子只照了 0009）：
#   ① 正样本 = 每道题【答案块】的最高分
#   ② 负样本 = 每道题【非答案块】的最高分（噪音天花板）
#   ③ 负样本第二类 ★ = 【手册里根本没有】的问题在全库的最高分
#      —— 0009 的镜 2 没有这一类，所以它量不到"该拒答时能不能拒答"。
#         你 0001 里那个 MIN_SCORE 真正要挡的就是这一类。
#
# 跑法（必须用项目 venv）：
#   agent-lab\.venv\Scripts\python.exe code\_calibrate-min-score.py
import os, sys, ast

sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # Windows 控制台防乱码
HERE = os.path.dirname(os.path.abspath(__file__))

# ===============================================================
# 0) 复用 0001 的语料 / 索引 / cosine —— 不复制一份，避免两份语料各自漂移
#    （0001 的 REPL 已经用 __main__ 守卫包住，所以 import 它不会进交互循环）
# ===============================================================
import importlib.util
_spec = importlib.util.spec_from_file_location("agent0001",
                                               os.path.join(HERE, "0001-minimal-agent.py"))
A = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(A)

CHUNKS = A.CHUNKS
index_vecs = A.index_vecs
print(f"已从 0001 载入语料：{len(CHUNKS)} 块")

# gold set 从 0009 读，不在这里重抄一份（0009 才是它的唯一真源）
def load_questions(path):
    tree = ast.parse(open(path, encoding="utf-8").read())
    for node in tree.body:
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "QUESTIONS":
            return ast.literal_eval(node.value)
    raise SystemExit("在 0009 里没找到 QUESTIONS")

QUESTIONS = load_questions(os.path.join(HERE, "0009-eval-lab.py"))
print(f"已从 0009 载入 gold set：{len(QUESTIONS)} 题")


# ===============================================================
# 1) 0001 检索侧的【原始分数】
#    ★ 坑：别拿 0001 的检索函数（search_hybrid）来取分 —— 它内部已经套了 MIN_SCORE、
#      MIN_SCORE_KW 和 top-k 截断，那样等于"用要校准的尺子去量它自己"，
#      低于阈值的点会凭空消失，分布假得漂亮。
#      标定要的是每块都打分、一个不丢、不做任何截断。
# ===============================================================
def vec_scores(query):
    qv = A.embed_one(query)
    return {cid: A.cosine(qv, index_vecs[cid]) for cid, _, _ in CHUNKS}


# ===============================================================
# 2) 两类负样本
# ===============================================================
# (a) 手册里【有】这些主题，但问的不是它 —— 噪音天花板
# (b) ★ 手册里【根本没有】这些主题 —— 你真正要挡住的那类
ORPHANS = [
    ("O1", "公司年会抽奖规则是什么？"),
    ("O2", "团建经费每人多少？"),
    ("O3", "公司有没有健身房？"),
    ("O4", "食堂几点开饭？"),
    ("O5", "停车位怎么申请？"),
]


def distribution(questions):
    pos, neg = [], []
    for qid, q, gold in questions:
        sc = vec_scores(q)
        pos.append((qid, max(sc[c] for c in gold)))                       # 答案块的最高分
        neg.append((qid, max(v for c, v in sc.items() if c not in gold)))  # 非答案块的最高分
    return pos, neg


pos, neg = distribution(QUESTIONS)
pos.sort(key=lambda x: -x[1])
neg.sort(key=lambda x: -x[1])
orphans = sorted(((oid, max(vec_scores(q).values()), q) for oid, q in ORPHANS),
                 key=lambda x: -x[1])

THRS = [0.70, 0.65, 0.60, 0.55, 0.50, 0.45, 0.40]

# ===============================================================
# 3) 打印
# ===============================================================
print("\n" + "=" * 12 + " 0001 检索侧（bge-small-zh 语义余弦）· 两条分布 " + "=" * 12)

print(f"\n  ══ 正样本：答案块的最高分（越高越好）× {len(pos)} ══")
print(f"    {pos[0][1]:.3f}（最高·{pos[0][0]}）  …  "
      f"{pos[len(pos)//2][1]:.3f}（中位·{pos[len(pos)//2][0]}）  …  {pos[-1][1]:.3f}（最低·{pos[-1][0]}）")

print(f"\n  ══ 负样本 (a)：非答案块的最高分，即「噪音天花板」（越低越好）× {len(neg)} ══")
print(f"    {neg[0][1]:.3f}（最高·{neg[0][0]}）  …  "
      f"{neg[len(neg)//2][1]:.3f}（中位·{neg[len(neg)//2][0]}）  …  {neg[-1][1]:.3f}（最低·{neg[-1][0]}）")

print(f"\n  ══ 负样本 (b) ★：手册里【根本没有】的问题，全库最高分 × {len(orphans)} ══")
for oid, s, q in orphans:
    print(f"    {s:.3f}   {oid}  {q}")

pos_min, neg_max, orph_max = min(p[1] for p in pos), max(n[1] for n in neg), orphans[0][1]

print("\n  ── 三条线放在一起看 ──")
print(f"    答案最低（正样本下界）  {pos_min:.3f}")
print(f"    噪音最高（负样本上界）  {neg_max:.3f}")
print(f"    孤儿最高（该拒答的）    {orph_max:.3f}  ← 这一条 0009 镜 2 量不到")
if pos_min > max(neg_max, orph_max):
    print("    ✅ 分得开：落在空隙里的阈值都行")
else:
    print(f"    ⚠ 重叠：想同时挡住「噪音」和「孤儿」，得卡到 {max(neg_max, orph_max):.3f} 以上，"
          f"但那样会误杀正样本里 {sum(1 for p in pos if p[1] < max(neg_max, orph_max))} 道题")

print(f"\n  {'阈值':>6} {'误杀(正样本被滤)':>18} {'漏放(噪音)':>14} {'漏放(孤儿)':>14}  说明")
for thr in THRS:
    miss = [p[0] for p in pos if p[1] < thr]
    leak = [n[0] for n in neg if n[1] >= thr]
    oleak = [o[0] for o in orphans if o[1] >= thr]
    note = "← 8 块时代拍下的 0.6" if thr == 0.60 else ""
    print(f"    {thr:>6.2f} {len(miss):>10} ({len(miss)/len(pos):>4.0%}) "
          f"{len(leak):>8} ({len(leak)/len(neg):>4.0%}) "
          f"{len(oleak):>8} ({len(oleak)/len(orphans):>4.0%})  {note}")

# ===============================================================
# 4) 挑战 B 步骤 2 要观察的：块数 8 → 30，到底什么变了、什么没变
#    ★ 用【8 块时代那句原话】做对照，别拿措辞不同的另一句来比（比出来的是假的）
# ===============================================================
print("\n" + "=" * 12 + " 步骤 2：块数 8 → 30，什么变了、什么没变 " + "=" * 12)

LEGACY = {c for c, _, _ in CHUNKS if c in {f"C{i:02d}" for i in range(1, 9)}}   # 原 8 块

print("\n  ── (1) 同一道题、同一块：余弦会不会因为库里块多了而变？ ──")
print("     （0001 里 :59 记的 8 块时代原话 =「我下周出差去上海，住酒店一晚公司最多能报销多少？」0.731）")
for _qid, q, gold in [("第8课原话", "我下周出差去上海，住酒店一晚公司最多能报销多少？", "C02"),
                      ("0009 另一句", "下周去上海出差住酒店，一晚最多能报多少？", "C02")]:
    sc = vec_scores(q)
    rank = sorted(sc, key=lambda c: -sc[c])
    print(f"    {_qid:10} 「{q[:22]}…」 → 该块分={sc[gold]:.3f}  top-1={rank[0]}({sc[rank[0]]:.3f})  名次={rank.index(gold)+1}")

print("\n  ── (2) ★ 噪音天花板：只在前 8 块里挑 vs 在全部 30 块里挑 ──")
print("     （挑战 A 步骤 2 问的「负样本最高分有没有跟着变」，就是这一栏）")
up = 0
for qid, q, gold in QUESTIONS:
    sc = vec_scores(q)
    n8 = max(v for c, v in sc.items() if c not in gold and c in LEGACY)
    n30 = max(v for c, v in sc.items() if c not in gold)
    if n30 > n8 + 1e-9:
        up += 1
    print(f"    {qid}  8块内噪音={n8:.3f}   30块内噪音={n30:.3f}   {'↑ 涨了' if n30 > n8 + 1e-9 else '持平'}")
print(f"    → {up}/{len(QUESTIONS)} 道题的噪音天花板【涨了】；没涨的那些本来就是持平或更高。")

print("\n  ⚠ MIN_SCORE 定多少 —— 不看这张表也能定，那叫拍脑袋；看了表还得说清"
      "\n     「更怕误杀还是更怕漏放」，那才叫标定。这个数归你定。")
