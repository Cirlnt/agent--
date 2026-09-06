# 第 5 课交付：字是一个个蹦出来的（streaming 流式输出）+ 教师预跑实证

2026-09-06。用户上完第 4 课后报到，按 lessons/0004 页脚预告（"下一课：M2 · 流式输出…… thinking / max_tokens / 首 token 延迟都从第 3 课埋过线"），交付 **M2 第 5 课** `lessons/0005-streaming.html` 与实验脚本 `code/0005-streaming-lab.py`。主题与用户确认：先讲流式，"成本与 token"留作 M2 收官第 6 课。

**本课核心心智（教学定调）**：把"agentic loop 里怎么收 response"从非流式扩展到流式。一句话核心：**流式是 I/O / 体验层的开关，不是新的 agent 机制**——模型照常"点单 + 说话"，流式只改"字什么时候到你屏幕"。用户体感 ≈ **TTFT（首字时间）**而非生成总时长。对工具 Agent 最反直觉的一点（本课实锤）：**给用户看的文字能逐字蹦，但 tool_use 参数是 input_json_delta"半个半个"到的，必须等 content_block_stop 收齐整段 JSON 才能 EXEC → 流式省不掉"工具那一拍"**。SDK 高级助手 `messages.stream()` + `get_final_message()` 返回与非流式 response **同形状对象** → 0001 的 agentic loop 逻辑一行不改即可切流式。

**教师预跑验证（DeepSeek v4-flash / Anthropic 兼容端点，结论全部诚实化进课件）**：
1. **镜 1（整段等 vs 逐字蹦）**：同一句"写十二行、每行有'浪'的小诗"，非流式 `client.messages.create` 干等 **2.50s** 后整首一次性出现（168 字）；流式 `messages.stream` 首段可见文字 **617ms** 即到、**1.99s** 蹦完（178 字）。**总耗时几乎不变** → 诚实口径：流式改"空窗期"，不改"总时长"。两首诗内容不同是抽样噪声，课件已提醒"别比内容"。
2. **镜 2（裸 create(stream=True) 事件序列）**：关掉 thinking 后序列干净可复现——`message_start → content_block_start(text,index0) → content_block_delta(text_delta)×N → content_block_stop → message_delta(stop_reason=end_turn) → message_stop`。"收到收到"被拆成两个 `'收到'` 碎片。
3. **镜 3（工具参数碎片）**：默认 thinking 开时，带工具请求事件为 thinking 块先到（index 0，约 19–24 段 thinking_delta）→ tool_use 块（index 1 或 2）`input_json_delta` 碎片 `{` `"` `city` `"` `: ` `"` `北京` `"` `}` 拼成 `{"city": "北京"}`。**某些 run 里 thinking 与 tool_use 之间还会夹一个 text 块**（如"我来帮您查询北京的天气。"，模型先圆场再点单），也可能没有 text 块直接点单——**随机，别把"有没有圆场话"当判据**。`messages.stream()` 的 `text_stream` 正确剥掉 thinking 只给可见字；`get_final_message()` 返回对象带 `stop_reason=tool_use`、`ToolUseBlock.input={'city':'北京'}`（已是 dict）、`usage` 齐备 → drop-in 成立。
4. **镜 4（决定性，streaming 开关）**：同一份 run_weather(agentic loop) 只切 `streaming` 布尔，两遍"上海天气"日志**逐字一致**：`get_weather({'city':'上海'}) → report_weather({...}) → ✅ 结构化出口`，两遍都没有圆场话（此模型上海问句直接点单）。行为无回归实证成立。
5. **thinking 显式开关**：`thinking={"type":"disabled"}` 在该端点**可用**（不 400），返回只含 ParsedTextBlock、首字 ~0.6s。与第 3 课记录"显式 tool_choice 会 400（Thinking mode does not support this tool_choice）"并不矛盾——是本端点对 thinking 模式下某参数的限制，流式 + 工具在默认 thinking 下正常。课件诚实框：flash 默认常先吐 thinking，首字 0.6–1.3s 波动。
6. **挑战 B 前提（max_tokens 截断）**：`max_tokens=16` + thinking disabled 写 300 字散文 → 文字蹦到"午后的"戛然而止，`stop_reason=max_tokens`，`usage.out=16`。"蹦一半就断"可见性实锤。

**由实测定的教学口径（诚实化）**：本课不制造"流式让 agent 更快/更便宜/更聪明"的叙事。镜 1 数字说明总时长大致不变；镜 3/镜 4 说明工具那一拍省不掉、逻辑行为不变。流式的真实收益锚定在**体验层（TTFT/空窗期）与"长纯文本输出回合的实时可见"**。判断题（课件自测 Q4）即为防"流式加速一切"误读。另一条口径：别拿"两次 run 内容/是否有圆场话不同"去反推流式副作用——那是抽样与模型自主性。

**ZPD 判断 / 对动手层的预测**：
- 挑战 A（手术刀切 0001）的 decisive 自检是观察③："get_weather 参数在流式下明明半个半个到，为什么循环不用等碎片、直接拿到完整 dict 执行？" 正解：`messages.stream` + `get_final_message()` 把流拼回完整 message，循环读的是 `block.input`（收齐后的 dict），不是事件碎片。若用户答"因为模型传得快/流式也整包给"，要点破 get_final_message 的组装职责。观察①（上海序列无回归）检验"流式不改逻辑"是否真懂；观察②（拒绝话术蹦 vs 整段）呼应体验层。
- 挑战 B（max_tokens 蹦一半就断）检验与第 3 课"thinking/max_tokens 共享预算"的并置能力：能说出"流式把截断从静默变可见、生产必须查 stop_reason"即达标。
- 潜在误区要盯：把"文字在蹦"当成"工具执行提前了"；以为流式能省 token / 让 thinking 变短；忘了收尾查 stop_reason。
- 埋的后续钩子：流式 + eval（逐 token 打分 / judge 消费流式输出）？半路取消（cancellation / 用户停止）怎么收尾？thinking 该不该流式展示给用户（产品决策）？→ 留给 M2 收官"成本与 token"课之间的空档或 M6 可观测性。

**待办（用户完成第 5 课后回填）**：跑通 lab 四镜 + 挑战 A/B 的实证与用户口头复盘；核对 code/0001（挑战 A 落点）是否被切成流式、是否保持第 4 课 SYSTEM_SCOPED + 出口结构、end_turn 分支有没有处理"已实时打印过文字"的尾巴；把 KNOWLEDGE.md 尾标推进到"第 5 课（M2）✅"并补 ①~⑥ 一节；NOTES.md 路线图 M2 剩余从"流式、成本与 token"收到只剩"成本与 token"；index.html 进度从第 5 课 → 第 6 课时再动。第 5 课完成时把本记录标注完成。

（第 5 课 ①~⑥ 尚未写入 KNOWLEDGE.md——按惯例待实证完成后与"实证补记"一并回填。）

---

## 实证回填 · 第 5 课完成（2026-09-06）

- **用户完成挑战 A（手术刀切 0001 为流式）与挑战 B（_truncate.py "蹦一半就断"）**，口头复盘已逐条核对点评：A①②（上海序列无回归、拦截答复也蹦出来）对；**A③ 答偏**（答"因为并没有调用这个 tool"，只对写诗那次 run 成立）——已点破 `s.get_final_message()` 把 input_json_delta 碎片拼回完整 dict 放进 `ToolUseBlock.input`、循环从 `response.content` 取 dict 所以从不见碎片的机制，纠正记入 KNOWLEDGE 实证补记。B①（stop_reason=max_tokens）对，B②③ 补了"断被看见 / thinking 共享预算所以要收尾查 stop_reason"的 why。
- **code/0001 落点核对通过**：唯一 API 调用点换成 `messages.stream + text_stream + get_final_message()`；SYSTEM_SCOPED 与 report_weather 出口结构保持第 4 课成品态；`end_turn` 二次打印尾巴已处理（注释掉）。默认留言恢复"帮我查一下上海现在的天气"（仓库成品态惯例）。`code/_truncate.py` 新增并留库。
- **KNOWLEDGE.md**：第 5 课 ①~⑥ + 实证补记已写入，尾标推进至"第 5 课（M2）✅"。
- **NOTES.md**：M2 路线图剩余从"流式、成本与 token"收到只剩"成本与 token"。
- **index.html** 进度未动（按待办约定，第 6 课时再推进）。
- 待办"跑通 lab 四镜"由教师预跑覆盖并诚实化进课件；用户挑战 A/B 的观察（无回归、圆场话随机、截断可见）与镜 3/4 结论互相印证，不另设阻塞。
- **本记录标注完成。** 下一课预告钩子（成本与 token；M6 收官衔接流式 eval / cancellation 已在 ZPD 段备注）。
