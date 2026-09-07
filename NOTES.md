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
3. **M3 记忆与上下文**：多轮状态、长上下文、向量库与 RAG 基础（第 7 课 多轮状态+上下文管理 已交付 2026-09-07，实证回填待用户完成；下一课 检索注入/RAG 上手）
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

## 环境现实（2026-09-05 实测确认）
- **用户的真实 API 通道 = DeepSeek 官方 Anthropic 兼容端点**，不是直连 Anthropic：
  - `ANTHROPIC_BASE_URL = https://api.deepseek.com/anthropic`
  - `ANTHROPIC_AUTH_TOKEN` = DeepSeek 平台 `sk-` key（35 位）
  - 可用模型：`deepseek-v4-flash`（便宜/快，Haiku 档）、`deepseek-v4-pro[1M]`（强档）
- 实测结论：`anthropic` SDK 1.4.0 在这个端点上**工具调用（tool_use → tool_result 闭环）完全可用**，还会返回 thinking 块。
- 教学影响：概念课仍以 Claude/OpenAI 为讲解主线（求职面试知识），但**一切"动手跑"的代码都跑在 DeepSeek 上**。SDK 写法不变 → 这正是"厂商无关"教学的好例子。`code/0001-minimal-agent.py` 已适配（MODEL=flash、max_tokens=4096、加了 Windows 控制台 utf-8 reconfigure）。
- 提醒：这些 env var 只在配了 Claude Code 的环境里可见；用户新开终端跑脚本可能读不到，届时引导他手动 set（值可从本会话 env 复制，或 platform.deepseek.com）。
