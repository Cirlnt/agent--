# Agent 开发（AI 应用工程师）资源清单

> 规则：只收高可信来源，逐条标注用途。本清单 2026-09-04 经检索核实，**2026-09-10 对全部外部链接做了一次可达性实测（见文末"可达性实测"节）**。知识不靠记忆猜，讲课引用一律回溯到这些链接。

## Knowledge

- [Anthropic 工程博客：*Building Effective Agents*](https://www.anthropic.com/engineering/building-effective-agents)
  Agent 开发最重要的入门必读（2024-12-19）。核心：workflows（代码定路径）vs agents（模型自己定路径）；五类基础模式（prompt chaining / routing / parallelization / orchestrator-workers / evaluator-optimizer）；以及"先上最简单方案、用评估证明确有需要再升级"的原则。**用于**：任何"什么是 agent、该不该上 agent、架构模式"的讲解。2026-09-10 curl 实测 200。
- [Anthropic 工程博客：*Demystifying evals for AI agents*](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)
  **评估主题最权威的一手文**（2026-01-09）。eval = 给 AI 输入 + 用评分逻辑测输出；难点在单轮 → 多轮 → agentic 的迁移（多轮工具调用、改状态，误差累积放大）。结构：The structure of an evaluation / Why build evaluations? / How to evaluate AI agents / Going from zero to one: a roadmap / **Appendix: Eval frameworks**。**用于**：第 9 课（检索评估）的上一层钩子、M6 生产化模块的核心原典、面试"你怎么知道你的 RAG 是好的"的答法依据。2026-09-10 curl 实测 200。
- [Anthropic 工程博客：*Introducing Contextual Retrieval*](https://www.anthropic.com/engineering/contextual-retrieval)
  RAG 检索质量改进（2024-09-19）：Contextual Embeddings + Contextual BM25，官方称单加前缀把失败检索降 **49%**、再加 rerank 降 **67%**（2026-09-10 curl 直抓原文核实）。**用于**：第 8、9 课（"embedding 会漏精确串 → 需与 BM25 双轨合流"就是第 9 课镜 1 题 02 的现场证据）。
- [Anthropic 工程博客：*Effective context engineering for AI agents*](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
  把上下文当**稀缺的注意力预算**来管（2025-09-29）：四策略 write long / read selective / divide & conquer / summarize。**用于**：第 7 课（长对话三招是它 compaction 的工程化子集）、第 8 课（read selective = 检索注入）。2026-09-10 curl 实测 200。
- [Anthropic：*Building Effective Agents* 开源译文版](https://github.com/machinedge/building-effective-agents/blob/main/building-effective-agents.md)
  同上内容的可检索 Markdown 版。**用于**：引用原文段落、做精读。

- [Claude Agent SDK 文档（Anthropic 官方）](https://code.claude.com/docs/en/agent-sdk)
  `claude-agent-sdk`（Python/TS）：`query()` API，SDK 替你跑通整个 agent loop，内置 Read/Write/Bash/Grep/WebSearch 等工具、hooks、MCP、session 续接。**用于**：讲"轮子已造好"的成熟 agent 载体；区分"手写 loop / SDK / 框架"三层。
- [Anthropic Python SDK 工具调用 / 智能体循环（含在 claude-api 技能内）](https://github.com/anthropics/anthropic-sdk-python)
  手写 `while stop_reason == "tool_use"` 循环、`@beta_tool` 工具运行器、tool_result 结构、并行工具调用。**用于**：M1/M2 手写 loop 的代码依据。课件代码以此为准。
- [OpenAI Agents SDK（官方，Python/TS）](https://openai.github.io/openai-agents-python/)
  OpenAI 版 agent 框架：Agent（Instructions/Model/Tools）、`@function_tool` 自动由类型注解生成 schema、agents-as-tools 与 handoffs 两种编排模式。**用于**：双厂商对照，建立"同概念不同命名"的地图。
- [OpenAI 官方快速开始 / 指南](https://developers.openai.com/api/docs/guides/agents/quickstart)
  OpenAI API 层 agent 起手式与 function calling 说明。**用于**：OpenAI 侧代码示范。
- [OpenAI 官方：*Evaluation best practices*](https://developers.openai.com/api/docs/guides/evaluation-best-practices)
  按"不确定性来源"分层建评估：输入层评指令遵循、输出层评功能正确性、Agent 层评**工具选择与参数抽取**、多智能体层评 handoff/转交准确率。**用于**：M6 评估模块的 OpenAI 侧对照（Anthropic 侧见《Demystifying evals for AI agents》）。注：该站对自动化抓取返 403，浏览器可正常打开。

- [Model Context Protocol 官方文档](https://modelcontextprotocol.io/)
  MCP = 让 AI 工具标准化的协议（"AI 世界的 USB-C"）。tool 的定义、`tools/list` / `tools/call`、安全要求（human-in-the-loop、输入校验）。**用于**：M5 连接世界模块的核心资料。
- [Pydantic AI 官方文档](https://pydantic.dev/docs/ai/overview/)
  生产级 Python agent 框架，类型安全 + 依赖注入 + 结构化输出，天然多厂商（OpenAI/Anthropic 等一行切换）。**用于**：M4 框架对比课；工程化做派参考。
- [Pydantic 官方实战文章：*How to build a production agentic app*](https://pydantic.dev/articles/building-agentic-application)
  用 Pydantic AI 搭一个生产级 agent 应用的分步文章（含测试/可观测）。**用于**：M6/M7 把 demo 变系统的范本。

- [AI Agent Engineer Handbook（harrisliangsu，GitHub）](https://github.com/harrisliangsu/ai-agent-engineer-handbook)
  中文。用 Prompt → Context → Agent → Harness 四层组织知识，含中外大厂真实 JD 拆解 + 86 道面试题。**用于**：M8 面试冲刺的题库与 JD 对照。（社区维护，非官方，作参考不作真理。）
- [awesome-agent-dev 路线图（summerjava，GitHub，中文）](https://raw.githubusercontent.com/summerjava/Awesome_Agent_Dev/main/README.md)
  一份中文 Agent 开发学习路线索引。**用于**：补漏、找主题聚合资料。
- [DataWhale 开源（中文，组队学习社区）](https://github.com/datawhalechina)
  Hello Agents / All in RAG 等开源中文教程与社区学习。**用于**：中文系统课程备选（若用户偏好集体学习节奏）。

## Wisdom (Communities)

> 社群价值 = 拿自己的真项目去被真实世界检验。用户尚未表态是否愿意加入，先列出来，逐课再确认。

- [Anthropic 开发者社区论坛（官方）](https://forum.anthropic.com/)
  官方问答。**用于**：Claude API/SDK 用法求助、看官方员工回答。
- [OpenAI Developer Forum](https://community.openai.com/)
  OpenAI 生态问答与反馈。**用于**：OpenAI SDK / function calling 排错。
- [r/AI_Agents (Reddit)](https://www.reddit.com/r/AI_Agents/)
  Agent 开发讨论。**用于**：看业界真实踩坑、方案取舍。（信噪比中等，慎用。）
- 中文语境：**掘金 / 知乎**（AI 应用开发、Agent 话题）
  中文经验贴多，但质量参差。**用于**：求职向的国内行情与 JD 情报，识别有实战作者再深读。
- LangChain / LlamaIndex Discord 及 GitHub Discussions
  **用于**：M4 框架选型期的实拍排错。

## 可达性实测（2026-09-10，本机 curl 逐条核过）

> 起因：第 9 课要引用 eval 原典，而 Claude Code 的 WebFetch 在本机**对所有域名都返回** "Unable to verify if domain … is safe to fetch"（是工具被网络策略整体拦，不是站点问题）。改用 `curl -L -A "<浏览器 UA>"` 才拿到真实状态码。**结论按"能直连 / 被拦截 / 未判明"三分，不把'被拦'当成'不存在'。**

| 资源 | 状态 | 备注 |
|---|---|---|
| `www.anthropic.com/engineering/*`（四篇工程博客 + `/pricing`） | ✅ 可直连（200） | **本清单里最稳的一档**，讲课优先压这里 |
| `docs.ragas.io`（含 `/en/stable/concepts/metrics/available_metrics/`） | ✅ 可直连（200） | 入口 `/` 会 301 到 `/en/stable/` |
| `github.com`（如 BEIR 仓库） | ⚠ 时通时断（多次 connection reset，偶发 200） | 给学员时附一句"打不开就跳过" |
| `platform.claude.com/docs/...`（Anthropic API 文档，旧别名 `docs.claude.com` / `docs.anthropic.com`） | ❌ **地区封锁**（307 → `app-unavailable-in-region`） | 控制实验：**编造的不存在路径表现完全一样** → 闸门拦在路由之前，**无法判断页面是否存在**，也**不能**据此说 URL 有效。需人工在能访问的网络下逐条核对 |
| `developers.openai.com` / `platform.openai.com` 文档 | ❌ 403 反爬（`X-Vercel-Mitigated: deny` / Cloudflare bot management） | **URL 本身有效**，浏览器打开正常；只是自动化抓取被拦。不要因 403 改链接 |
| `github.com/beir-cellar/beir` | ✅ 存在（曾抓到 200） | 论文走 OpenReview |

**两个结构性事实（来自 302 响应头本身，不依赖页面内容）**：
1. Anthropic API 文档的**规范主机名已是 `platform.claude.com`**，`docs.claude.com` / `docs.anthropic.com` 只是转发别名（本仓课件已统一用规范形式，无需改）。
2. **路径格式变过**：`docs.claude.com/en/docs/<section>/<page>` → `platform.claude.com/docs/en/<section>/<page>`（语言码从 `docs` 前移到 `docs` 后）。引用旧格式会多一跳 302。
3. OpenAI **Cookbook 已迁站**：`cookbook.openai.com/*` → `developers.openai.com/cookbook/*`。本清单若有旧 cookbook 链接应换新域名。

**据此定的引用方针**：课件"必读原典"只压**可直连**的那一档（Anthropic 工程博客 + Ragas + 本仓自产实验）；被地区封锁/反爬的文档仅作"延伸对照"，并**明写网络提示**，不让学员对着打不开的链接干瞪眼。

## Gaps（缺的高可信资源，驱动后续检索）
- ~~**评估（eval）体系的一手实操范本**~~ → **已部分关闭（2026-09-10）**：一手原典已补齐（Anthropic《Demystifying evals for AI agents》+ [Ragas 指标清单](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/)），**且本仓自己产出了一套可照着做的端到端范本**——`code/0009-eval-lab.py` + `lessons/0009-retrieval-eval.html`（22 题 gold set、Hit@1/Hit@k/Recall@k/MRR、阈值正负样本标定、query 自足性、top_k 扫描）+ `reference/m2-m3-review.html` 里的自测卷。<br>**仍未关闭的部分**：带 faithfulness / response relevancy 的**生成端**评估（本仓只量了检索端，属 M6 正题）、以及"评估怎么进 CI 做成回归门禁"的工程范例。
- **可观测性与成本核算**的实操范例（真实生产 trace / token 账单）。
- **模拟面试 / 真实 JD 到 offer 的过程复盘**：Handbook 有题库但缺"如何把项目讲成面试亮点"的方法论。
- 国内厂（通义/豆包/Kimi/DeepSeek）**一手 API 文档对照**：若求职目标是国内岗，M2 后可能需要补。（当前主线 Claude+OpenAI，先不急。）
