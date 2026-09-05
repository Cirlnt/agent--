# Agent 开发（AI 应用工程师）资源清单

> 规则：只收高可信来源，逐条标注用途。本清单 2026-09-04 经检索核实。知识不靠记忆猜，讲课引用一律回溯到这些链接。

## Knowledge

- [Anthropic 工程博客：*Building Effective Agents*](https://www.anthropic.com/engineering/building-effective-agents)
  Agent 开发最重要的入门必读（2024-12）。核心：workflows（代码定路径）vs agents（模型自己定路径）；五类基础模式（prompt chaining / routing / parallelization / orchestrator-workers / evaluator-optimizer）；以及"先上最简单方案、用评估证明确有需要再升级"的原则。**用于**：任何"什么是 agent、该不该上 agent、架构模式"的讲解。
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

## Gaps（缺的高可信资源，驱动后续检索）
- **评估（eval）体系的一手中文/英文实操课**：如何给 agent 写评估集、离线回归。目前只有文档片段，缺一套可照着做的端到端范本。
- **可观测性与成本核算**的实操范例（真实生产 trace / token 账单）。
- **模拟面试 / 真实 JD 到 offer 的过程复盘**：Handbook 有题库但缺"如何把项目讲成面试亮点"的方法论。
- 国内厂（通义/豆包/Kimi/DeepSeek）**一手 API 文档对照**：若求职目标是国内岗，M2 后可能需要补。（当前主线 Claude+OpenAI，先不急。）
