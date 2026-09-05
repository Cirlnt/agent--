# 第 2 课交付：工具的说明书（description 与 schema）+ 一处实测发现

2026-09-05。用户完成第 1 课后报到，按 lessons/0001 页脚预告与 NOTES 路线图，交付 **M2 第 2 课** `lessons/0002-the-tool-spec.html` 与实验脚本 `code/0002-tool-spec-lab.py`（同一 get_weather 函数、三种 TOOLS 说明书 BAD / GOOD_DESC / ENUM，同问"东京天气"，观测点单变化）。

**实测发现（教师先跑验证，重要）**：deepseek-v4-flash 这个模型相当守规矩——只要 description 透露"仅支持北京/上海/巴黎/纽约"或 schema 里有 enum，它就会礼貌拒绝东京；**只有"裸奔"说明书（无范围信息）它才乱点 `get_weather({'city':'东京'})`**。进一步探测（裸奔 desc+enum、混合城市提问"北京和东京都查"）均未出现"就近偷换成合法城市"的幻觉。结论：镜 2 与镜 3 在本端点**肉眼难分高下**。

**由此定的教学口径（已在课程里诚实化）**：
- 不硬凑镜 2/镜 3 差异。把 decisive 对比定位在 镜1(盲) vs 镜2(知情)；enum 的价值定位为"传参通道层的机械约束 + 换模型/回归时的保险 + 合法取值文档"，而非"今天这模型会乱来"。
- "绝对保证"不讲成 schema 自带：真 Anthropic 的 `strict:true`（GA，需 additionalProperties:false+required）在 DeepSeek 兼容端点**未验证**，课程只提开关不依赖。
- 硬兜底落到**执行前校验**（挑战 B 改循环，加白名单闸门）——厂商无关、永远成立。三道防线 = description 劝退 → schema 锁 → 执行前校验。

**ZPD 判断 / 对后续课的预测**：
- 用户在挑战 B 若能把"把校验放在自己这边，比祈祷模型守规矩强在哪 / 换笨模型哪层兜底"讲清，即算吃透"契约不靠祈祷"。若只会照抄白名单代码而答不上"为什么"，下次课（结构化输出）前需再点一次执行边界。
- 第 2 课正文已埋两处 M2 后续钩子：`additionalProperties:false` 与 system prompt vs description 的决策分工 → 留给结构化输出 / prompt 课。

**待办（用户完成第 2 课后回填）**：跑通三镜头 + 挑战 A/B 的实证；核对 code/0002 是否被用户改过。第 2 课完成时把本记录标注完成。
