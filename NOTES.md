# NOTES — 教学偏好与工作区笔记

## 学习者偏好（来自首次访谈 2026-09-04）
- **语言**：中文讲解。英文术语保留原文（如 agentic loop、tool calling），这是行业通用语言，求职也用得上。
- **风格**：概念 → 动手 → 反馈。希望每课都有一个"看得见摸得着"的小成果。
- **编码水平**：Python 基础语法。写代码示范时注释要充足、一次只引入一个陌生概念。机器上 Python 3.13.5 + pip 25.1 可用。
- **目的**：求职冲刺，<3 个月，实战优先，原理为实战服务（讲原理但落到工程）。
- **厂商**：Claude + OpenAI 双线。教学用 Claude 落地示范，同时点出与 OpenAI 概念一一对应，避免厂商锁死。
- **成本敏感**：练习脚本默认用一个便宜够用的模型常量，允许切换。
- 是否愿意加入社区/社群：**尚未确认**，后续课程里再问，先不默认。

## 3 个月冲刺课程路线图（粗略，会随进度修订）
1. **M1 核心心智模型**：agentic loop、LLM 工具调用、一次调用 vs 循环（已完成：第 1 课，见 learning-records/0002）
2. **M2 工程地基**：prompt / 结构化输出 / tool calling 实战（Claude+OpenAI 双写）、流式、成本与 token（第 2 课 工具说明书 ✅、第 3 课 结构化输出 ✅、第 4 课 提示词工程（system vs description 分工）✅、第 5 课 流式 ✅、第 6 课 成本与 token ✅交付，均已实证完成回填 → **M2 六块收官 ✅**；第 6 课 KNOWLEDGE ①~⑥ + 实证补记已回填）
3. **M3 记忆与上下文**：多轮状态、长上下文、RAG 与检索评估（第 7 课 多轮状态+上下文管理 ✅ 2026-09-08；第 8 课 检索注入/RAG 上手 ✅ 2026-09-10；第 9 课 检索评估 eval 首次上手 ✅ 已交付 2026-09-10，待用户实证收束。**M3 三课收官**：管得住 → 取得回 → 量得准。第 9 课按用户选择走"**评估驱动检索调优**"主线（未装向量库依赖）：语料 8→30 块、22 题 gold set、四路检索器对比（关键词 0.73 / 语义 0.91 / 混合 0.91 / 语义加权 0.95，Hit@1）、阈值按正/负样本分布标定、追问改写让命中 2/5→5/5。真向量库（Chroma/FAISS）与持久化刻意留给 M4 之后或直接长进作品集项目 M7。**下一课：M4「手写 vs 框架」**——手写循环到此为止，看 LangGraph / Pydantic AI / OpenAI Agents SDK 封装了什么、何时该上何时别上）
4. **M4 手写 vs 框架**：先手写循环，再看 LangGraph / Pydantic AI / OpenAI Agents SDK 如何封装，何时用框架
5. **M5 连接世界**：MCP、自定义工具、技能（Skills）、多智能体编排
6. **M6 生产化**：评估（evals）、可观测性、错误处理、部署（FastAPI / Docker）
7. **M7 作品集项目**：2-3 个完整项目逐步搭建
8. **M8 面试冲刺**：题库、系统设计、模拟问答

## 教学原则提醒
- 每课一个**紧密聚焦**的成果，保持在最近发展区内（略难但够得着）。
- 多用检索练习（quiz）、间隔复习、交错练习，而非灌输。
- 复习用 **reference/ 术语表与速查**，新内容用 lessons/。
- 讲 Agent 必须落到"Anthropic 建议先从最小复杂度开始、先用原生 API 再看框架"的立场（见 Building Effective Agents）。

## 复习日（2026-09-10 建：M2 + M3 复盘）
- 用户在第 9 课交付后主动要求"花一天再读一次原典、复习 M2+M3"，并选定形态 = **先自测 → 带问题重读 → 压成速查卡**、范围 = **3 篇硬原典精读 + 文档只做速查**。
- 交付物 `reference/m2-m3-review.html`：卷 A 概念自测 20 题（**交错出题、不标课号**，反馈里才标课号，让用户自己统计塌方）/ 卷 B 数字默写 12 题（`<details>` 折叠，先默写后对答案）/ 错题映射表（错在哪几题 → 读哪篇原典哪一节 → 回看哪个 code 的哪面镜）/ 3 篇原典带读问题（每篇 5 问，全部锚在用户已做过的项目上）/ 九课速查卡 + 面试视角六问 / 错题本与验收标准。设计记录见 `learning-records/0011`。
- 原则：**纯重读是性价比最低的复习**（fluency illusion），所以顺序是**测 → 读 → 压**，让漏洞点名该读哪篇。带读问题里 Contextual Retrieval 那几个百分比**故意留空要求用户去原文抄**（本机 WebFetch 到 anthropic.com 被网络策略拦截，不能替用户凭记忆填数）。
- 使用时机：M3 正式收束（用户完成第 9 课挑战 A/B）之后、M4 开始之前。<br>做完后据结果决定 M4 是否要先补 M2 的洞。

## 环境现实（2026-09-05 实测确认）
- **用户的真实 API 通道 = DeepSeek 官方 Anthropic 兼容端点**，不是直连 Anthropic：
  - `ANTHROPIC_BASE_URL = https://api.deepseek.com/anthropic`
  - `ANTHROPIC_AUTH_TOKEN` = DeepSeek 平台 `sk-` key（35 位）
  - 可用模型：`deepseek-v4-flash`（便宜/快，Haiku 档）、`deepseek-v4-pro[1M]`（强档）
- 实测结论：`anthropic` SDK 1.4.0 在这个端点上**工具调用（tool_use → tool_result 闭环）完全可用**，还会返回 thinking 块。
- 教学影响：概念课仍以 Claude/OpenAI 为讲解主线（求职面试知识），但**一切"动手跑"的代码都跑在 DeepSeek 上**。SDK 写法不变 → 这正是"厂商无关"教学的好例子。`code/0001-minimal-agent.py` 已适配（MODEL=flash、max_tokens=4096、加了 Windows 控制台 utf-8 reconfigure）。
- 提醒：这些 env var 只在配了 Claude Code 的环境里可见；用户新开终端跑脚本可能读不到，届时引导他手动 set（值可从本会话 env 复制，或 platform.deepseek.com）。
- **跑 embedding 脚本必须用项目 venv**：`D:\agent学习\agent-lab\.venv\Scripts\python.exe`（或先 `activate`）。全局 `D:\tool\python\python.exe`（3.13.5）装了 anthropic 但**没装 fastembed**——第 1~7 课用全局 python 照跑无事，第 8 课起一引入 embedding 就 `ModuleNotFoundError: No module named 'fastembed'`（2026-09-10 挑战 A 真实踩中）。**"前几课都能跑"不等于环境没问题**；排查时先问"你怎么跑的"，再看代码。
- 调试用管道喂中文给脚本时要加 `PYTHONIOENCODING=utf-8`：Windows 管道会按 cp936 解出**孤立代理字符**，报一个和代码无关的假错 `UnicodeEncodeError: surrogates not allowed`。
- **网络可达性（2026-09-10 逐条实测）**：Claude Code 的 **WebFetch 在本机对所有域名都被拦**（一律返回 "Unable to verify if domain … is safe to fetch"）——**这是工具被网络策略整体拦，不代表链接失效，别据此改链接**；要看真实状态码改用 `curl -L -A "<浏览器 UA>"`。可达性三分：① **可直连**——`www.anthropic.com/engineering/*`（工程博客四篇 + /pricing）、`docs.ragas.io`；② **地区封锁**——`platform.claude.com`（Anthropic API 文档，旧别名 `docs.claude.com`，307 → `app-unavailable-in-region`）；③ **反爬 403**——`developers.openai.com` / `platform.openai.com` 文档（`X-Vercel-Mitigated: deny` / Cloudflare，**浏览器打开正常**）。另：GitHub 时通时断。**结论**：课件"必读原典"优先压第①档并给网络提示，第②③档只作"延伸对照"。详见 RESOURCES.md 的"可达性实测"节。
