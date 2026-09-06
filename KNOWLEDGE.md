# KNOWLEDGE — 课程知识总表（随课程滚动积累）

> 用途：复习与面试冲刺。**每完成一课**，把该课"可带走的知识"浓缩成一节追加到本文件。
> 每课固定按六类分类（新课程照抄模板）：
> ① 一句话核心 ｜ ② 心智模型 ｜ ③ 要点清单（逐条能自测）｜ ④ 实测发现 ｜ ⑤ 工程陷阱与面试追问 ｜ ⑥ 术语·厂商对照·原典
> 原则：只收"讲得清、能自测"的硬知识；概念用中文，英文术语保留原词（行业通用语）。

---

## 第 1 课 · Agent 的最小闭环（agentic loop）· M1

### ① 一句话核心
Agent = **一个在循环里自主决定调用工具干活的大模型**（Anthropic：*an LLM using tools to perform a task in a loop*）。它比一次 API 调用只多三样东西：**工具清单、可续历史、循环**。

### ② 心智模型
- 一次 LLM 调用 = **无状态函数**：文本进、文本出；没有记忆、不会主动、不能动手。
- **Agentic loop**（必须能默画）：
  ```
  发消息(历史 + 工具清单) → 模型返回?
     tool_use → 你执行它点名的工具
              → 把 tool_result(带 tool_use_id) 喂回 → 再来一轮
     end_turn → 纯文字 = 最终答案 → 输出、停
  ```
- ReAct = Agentic loop 的思想名（Reason→Act→Observation）；loop 是它的**工程实现**。面试能主动说出这层关系很加分。

### ③ 要点清单
- [ ] Agent 的判据：模型**在循环里自主决定**调哪个工具（调强模型、提示词细、能存多轮，都不是判据）。
- [ ] **谁执行工具**：模型从不执行。它只返回 `tool_use`"点单"（工具名 + 参数）；真正跑的是你注册的 Python 函数 `EXEC[name](**block.input)`。← 本课纠正过的最大误区
- [ ] 模型职责只有两件：**决策**（调不调 / 调哪个 / 传什么参）+ **生成最终文字**。
- [ ] 闭环三要素：`tool_result` 放 **user 角色**消息里；`tool_use_id` 必须对上模型给的 `block.id`；漏一个循环就断。
- [ ] **并行工具**：一次 `response.content` 可含多个 `tool_use` 块，循环遍历执行 = 一次请求省多轮往返。
- [ ] Workflow vs Agent（Anthropic 建议）：Workflow = 路径代码写死、LLM 只填空；Agent = 路径模型自己定。**能用简单方案就别上 Agent**（复杂度的代价：延迟、token、难调试）。

### ④ 实测发现（DeepSeek v4-flash / Anthropic 兼容端点）
- 单条 assistant 消息内会**并行**请求多个工具 → 遍历 content 的循环天然支持并行。
- 端点宽容、能收两条连续 user 消息；但**真 Anthropic 强制 user/assistant 严格交替**，两条连续 user 会 400 → 想写厂商无关代码，就把多个需求塞进**一条消息**。

### ⑤ 工程陷阱与面试追问
- 面试题「什么是 Agent？和一次 API 调用什么区别？」→ 答：循环里的 LLM + 工具，路径由模型自己定。
- 面试题「工具的副作用谁执行？」→ 调用方代码。**安全边界就在这里**：别把"能执行任意代码"的权力交到模型手里。
- 手写这个循环，就是 OpenAI Agents SDK / Claude Agent SDK 内部帮你封装的东西 → 先手写、再拥抱框架，顺序别反。

### ⑥ 术语·厂商对照·原典
- 术语：LLM call / Agent / agentic loop / ReAct / tool_use / tool_result / end_turn / stop_reason / parallel tool calls（查 reference/glossary-core-terms.html）
- 原典（必读）：Anthropic《Building Effective Agents》——精读 **Workflows vs. Agents** + 五个模式的名字。

---

## 第 2 课 · 工具的说明书：description 与 input_schema · M2

### ① 一句话核心
模型对一个工具的**全部了解**，只在 TOOLS 里那一个字典的三个字段：**name + description + input_schema**；函数体、docstring、注释它一个字都看不到。让它"调得准、传得对"，靠雕说明书，不靠换更聪明的模型。

### ② 心智模型
- **三个字段，三种力道**：
  - `name` —— 让模型认出"该调它"。命名用"动词+名词"（`get_weather` / `send_email`）；别叫 `handle_info` 这种谁都能是它的名字。
  - `description` —— **软引导**：让模型"倾向"做对，可它是概率系统，今天守、明天换模型/换提示词可能就不守。
  - `input_schema` —— **强约束**：`type` / `required` / `enum` 把"模型能传什么"框死。
- 核心立场：**能靠 schema 锁死的，就别靠 description 劝说** —— 靠契约，不靠祈祷。
- **description 四问**（写任何工具前逐条过）：① 什么时候该用它？② 它返回什么（给样例）？③ 边界是什么（**负例**！）④ 什么时候不该用它？—— 最易漏、却最值钱的是**负例**：不支持什么 + 何时别调用。
- schema = 模型与执行代码之间的**合同**：`input_schema` 说 `city` 必填 string，你的 `def` 就得真能接一个非 None 的 string。
- **三道防线**（力道递减的兜底层）：
  | 防线 | 所在层 | 性质 | 兜住什么 |
  |---|---|---|---|
  | ① description 负例 | 提示层 | 软·概率 | 模型"愿不愿意"越界 |
  | ② input_schema（enum 等） | 传参层 | 中硬·强先验 | 越界值"发不发的出" |
  | ③ 执行前白名单校验 | 你的代码 | 硬·物理拦截 | 非法值"到不到得了函数" |

### ③ 要点清单
- [ ] 模型看不到：函数体、docstring、注释、仓库源码、前端 UI → 参数语义只能靠 `input_schema.properties` 里参数的 description 传进去（很多人只写工具级 description，漏掉参数级）。
- [ ] 好 description 负例样板：`"仅支持：北京、上海、巴黎、纽约。若用户问其它城市，本工具没有数据，不要调用，直接告诉用户暂不支持。返回形如：晴，18°C。"`
- [ ] 合同对不齐的最隐蔽错法：**不报 400，运行时才 TypeError / 静默变行为**（schema 说必填、函数却 `city=None` 容忍 None → 悄悄崩）。
- [ ] 白名单闸门模式（执行前验单，不合规当"工具报错"喂回，让模型自己读边界）：
  ```python
  SUPPORTED = list(table)          # 单一事实来源：真相当真值只写一处
  if block.name == "get_weather" and block.input.get("city") not in SUPPORTED:
      output = f"错误：暂不支持城市 {city}。支持：{'、'.join(SUPPORTED)}"   # 喂人话，别喂 Python list 字面量
  else:
      output = EXEC[block.name](**block.input)
  ```
- [ ] **谁在说话，随说明书变**（实证）：裸奔说明书下，拒绝来自你闸门的报错文字；守规矩说明书下，拒绝是**模型自己写**的文字。模型的信息源 = TOOLS 三样 + 你喂回的 tool_result。

### ④ 实测发现（DeepSeek v4-flash）
- flash **相当守规矩**：description 写明"仅支持四城"，镜 2 就学会拒绝；镜 2（好 description）与镜 3（enum）输出肉眼难分高下。
- 结论：决定性的对比在 **镜 1（裸奔，自信乱点东京）vs 镜 2（知情，礼貌拒绝）**；enum 的价值不在"今天这模型会不会乱来"，而在**换模型 / 回归测试时的保险 + 充当合法取值文档**。
- 未验证项：Anthropic `strict:true` 在 DeepSeek 兼容端点是否可用——课程只当"有这么个开关"提及，不依赖。

### ⑤ 工程陷阱与面试追问（含复盘补刀）
- 面试题「怎么保证模型稳定调对工具、传对参数？」→ 老手答三层：**雕 description（含负例）→ schema 锁 → 执行前自己校验**，而不是"换个更聪明的模型"。
- **enum 不是 100% 机械锁，是"强先验"**：Anthropic 端点在 tool_use 参数到达时**不替你拒非法值**；真机械锁 = OpenAI `strict:true`（服务端强校验）或你自己 parse 层再验。三层排序严格讲：description(纯劝) < enum(强先验) < 白名单(物理拦截)。
- **三层共同盲区：域内就近偷换**。笨模型问东京、enum 里没东京，它最省力的错法是偷填一个合法的"北京" → description 与白名单全部放行（北京合法）→ 返回北京天气当东京答案。错法从"非法值"漂移成"合法值里的语义错"后，机械层全失效；对"对错"的防守只剩 description 的"没有就直说、别就近猜"负例（仍是软）+ eval 盯着。这也是 enum 常配 `unknown/other` 兜底值的原因。
  - 自检一句话：**"白名单 100% 兜住域外；域内（类型合法但选错）没有哪一层能 100% 兜住。"**（答"类型一样却出错"就是点到了这个域内语义错。）
- schema 与函数里**两份手写真相会漂移** → 单一事实来源（`SUPPORTED = list(table)`，别两处手抄四个城市）。
- 工具输出是模型直接读的：报错/返回串要格式化成人话，别把 `['北京', '上海', …]` 这种 Python 字面量喂进去。
- 预留钩子（下几课 / 面试可问）：为什么要开 `additionalProperties: false`？一个工具该拆成几个？"要不要调工具"的决策该写进 system prompt 还是 description？

### ⑥ 术语·厂商对照·原典
- 术语：tool spec / description / input_schema / JSON Schema / enum / required / 负例（negative example）/ 三道防线 / strict
- 厂商对照：Anthropic `name / description / input_schema` == OpenAI `tools[].function` 的 `name / description / parameters`（parameters 同为 JSON Schema，概念一一对应，仅命名不同）。
- 原典（必读）：Claude 官方 **Tool use** 文档（platform.claude.com → Agents and tools / Tool use），精读 "Define tools / tool schema" 段落。

---

## 第 3 课 · 让模型交出结构化数据：三种拿 JSON 的姿势 · M2

### ① 一句话核心
程序要的是**数据（dict）**，模型给的是**文本**。让模型"只输出 JSON"是把格式押在它守规矩上（软）；更稳的是**工具即输出**——定义一个输出工具、让模型用 `tool_use` 把答案"交"回来，你从 `block.input` 拿到的天生就是 dict，还被 `input_schema`（required/enum/类型）约束。**tool_use 本来就是免费的结构化输出。**

### ② 心智模型
- **两条通道，同一机制**：
  - 输入端（第 2 课）：定义 `get_weather` 的 schema → 模型把参数 city 传回 → 你 EXEC 执行、喂回结果。
  - 输出端（本课）：定义 `submit_request` 的 schema → 模型把答案（action/target/when）装进参数传回 → 你**不执行**，直接读 `block.input`。
  - 差别只在"这一单算不算副作用"由你决定；正因工具调用可无副作用，它才能当**纯数据通道**用（第 1 课"模型从不执行工具"的另一面 = 自由度来源）。
- **三条路，软→硬**：
  - 姿势① 用嘴求（prompt"只输出 JSON"）→ 输出是**文本**，要再 json.loads；格式由模型"赏"（围栏/前后缀/尾逗号/截断为空）→ 软、赌守规矩。
  - 姿势② 工具即输出 → block.input 天生 dict，机器通道编解码、schema 约束 → 硬（本课主菜）。
  - 姿势③ 服务端"强制"开关（Anthropic `tool_choice` 指名 / OpenAI `response_format`+`strict`）→ 最硬，但**端点实现各异，要实测别假设**。
- **"格式稳" ≠ "内容对"**：schema 管结构管不了语义（第 2 课域内偷换输出侧变体）；语义靠 eval。required 慎用——逼模型填一个推不出的必填字段 = 逼它幻觉。

### ③ 要点清单
- [ ] 裸 JSON 是**文本**：可能干净、可能带 ```json 围栏 / 前后缀 / 尾逗号 / 被 max_tokens 截断为空 → json.loads 崩。能解析靠它守规矩，不是你的锁。
- [ ] 出口工具用法：schema 写清 `required` / `enum` / 字段 description；模型要答复就必须调用它交答案 → `block.input` 是 dict，**全程无 json.loads**。
- [ ] 强制必走出口：Anthropic `tool_choice={type:"tool",name}`、OpenAI `response_format=json_schema`；生产兜底 = 代码查 `stop_reason=="tool_use"`，不是就走重试/报错。
- [ ] 出口工具**不加进 EXEC**：它是数据出口不是"要执行的事"；循环里发现 `block.name=="report_x"` 就打印 input 并 break。
- [ ] `additionalProperties:false` = 合同"声明"，**不是物理拦截**；模型会把多余信息塞进自由文本字段（最省力偷换）→ 真拦靠自己代码验。
- [ ] max_tokens 是文本+思考**共享预算**：给太小时 thinking 可吃光 → 空文本 + `stop_reason=max_tokens`；工具参数随 tool_use 结构返回，不抢这个文本预算。

### ④ 实测发现（DeepSeek v4-flash / Anthropic 兼容端点）
- 裸 JSON：flash **相当守规矩**——干净句、连 target 要带 ASCII 引号（`老板说"周六前务必回邮件"`）都自己转义好、直接 loads 成功；一旦让它"再给句人话确认"，输出即变 `好的，已记下。\n{...}` → 直接 loads 崩，得手写剥除（打地鼠）。
- `tool_choice={type:"tool",name}` 指名强制 → **400**："Thinking mode does not support this tool_choice"；`{type:"any"}` 可用且强制走工具（单输出工具时≈指名）。
- `additionalProperties:false` 实测不物理拦；模型不硬加 schema 外键，而是把"预算3000靠窗"整句塞进自由文本 target。
- 挑战模式（数据工具→回填→出口工具收尾）：模型在该描述下守规矩走 `report_weather` 收尾、不再给自然语言结语。
- **实证补记（用户完成第 3 课，2026-09-06）**：
  - **改循环结构的经典翻车**：把"出口工具检测"塞进同一个 if/else、并把 `results.append` 挪进 `else` 分支 → 非支持城市的报错算出来了却没 append → 空 `results` 被当 user 消息回塞 → **400 "all messages must have non-empty content"**。只测白名单内城市（上海）会完全看不出来。修法：出口工具单独 `if/continue`，真工具（含闸门报错）**无条件 append**。← "出口与真工具同框"要按此结构拆，别共用一次 append。
  - **挑战 B 8×8（裸 JSON+确认语 vs 工具即输出，全自动跑）**：镜1d 直接 `json.loads` **8/8 崩**、剥除逻辑 **8/8 救回**（每次救回都在打地鼠）；镜2 **8/8 拿到 dict、0 解析失败、0 模型直接回话**。但镜2 的失败从"解析"**漂移成"字段质量/语义"**：target 会把带引号的后半句整段漏掉（"周五开会改周六+先把方案给我"只抄前半）、when 格式不稳定（`12 点` vs `12点`）→ "格式稳≠内容对"的输出侧实锤，语义校验只能靠下游代码 + eval。

### ⑤ 工程陷阱与面试追问
- 面试题「怎么让模型稳定返回可解析的 JSON？」→ 答：工具即输出 + schema 锁 + （代码查 stop_reason/重试），不是"请输出 JSON"写三遍。
- 面试题「工具 schema 跟输出结构有什么关系？」→ 同一机制两用：输入端锁参数、输出端锁结构；答出"模型从不在 text 里手写 JSON 给我，它把结构装进 tool_use 参数交回来"最加分。
- 陷阱：裸 JSON 的解析崩盘是**运行时才知道**的意外；"服务端强制"不是跨厂商通用（端点实测 400 是常态功课）；required 滥用制造幻觉。
- 陷阱：**回归测试只跑 happy path 会让你漏掉结构性回归**。给出口工具改循环时若只问白名单内的城市，报错分支被断掉也毫无察觉；要覆盖"白名单外"这条路径（它专测闸门/报错回填逻辑）。
- 埋点：出口工具与"真工具"混在同一 TOOLS 时怎么防调错 → 留给下一课（system prompt vs description 分工 / prompt 工程）。

### ⑥ 术语·厂商对照·原典
- 术语：structured output / 工具即输出（tool-as-output, emit pattern）/ tool_use.input / tool_choice / additionalProperties / strict / response_format / 意图路由（intent routing）/ json.loads 打地鼠。
- 厂商对照：Anthropic 无独立 "JSON mode"，结构化输出 = 工具即输出 + `tool_choice`；OpenAI = `response_format:{"type":"json_schema"}`（老版 `json_object`）+ `strict:true` 服务端强校验；DeepSeek 原生 API 另有一套 JSON mode（本课端点不展开）。概念一一对应，命名/行为各不同 → 实测为准。
- 原典（必读）：Claude 官方 **Tool use** 文档 "Forcing tool use / tool schema" 段（`platform.claude.com → Tool use`）；对照 OpenAI **Structured Outputs** 文档（`response_format`+strict）。

---

## 第 4 课 · 话要放对抽屉：system prompt 与 description 的分工 · M2

### ① 一句话核心
模型每轮读**四样说明**：system（整台 Agent 的全局章程）+ 对话历史 + tools（desc/schema）+ tool_result。分工判据一句话：**只管"一个工具"的规矩 → 写进那个工具的 description/schema；管"整台 Agent、跨工具取舍、会话身份/边界"的 → 写进 system**。description 只对"这个工具该不该被调"负责，管不住"这台 Agent 该不该接这个活"——**零工具的纯知识域外请求，desc 层看不见，只有 system 顶层边界能拦**。

### ② 心智模型
- **三只抽屉**：`system` = 整台 Agent 的身份 / 职责范围 / 整体边界 / 跨工具流程纪律（每轮都在、盖住所有工具）；tool `description` = 单工具何时用 / 负例 / 返回样张（只属于那一个工具）；`input_schema` = 单工具参数合同（类型/required/enum）。
- **判断题（能默写）**：删掉 system，这条规矩还有地方放吗？没地方可放 → 它本来就是 system 的活。
- **"desc 自守 ≠ 整体边界"**：所有工具各自"别乱用我"的加总，不等于"这台 Agent 不做 X"——只要有一类请求**不需要任何工具**，加总里就永远缺它那一格。
- 工具清单决定 Agent **能**做什么；system 决定 Agent **该**做什么。只给工具不给 system = 把 Agent 形态交给模型"通用助手"默认值（能力外泄）。

### ③ 要点清单
- [ ] 分不清放哪先问作用域：这条管"一个工具"还是"多个工具/整台 Agent"？前者 desc/schema，后者 system。
- [ ] 典型 system 内容：身份 + 支持域 + 支持/不支持清单 + 跨工具顺序纪律 + "域外直接拒、别调工具"红线。
- [ ] description 的盲区（本课 decisive）：用户问的事**不需要任何工具**就能答（珠峰多高）→ 没有工具要被调 → 没有任何 desc 会出来拦 → 只有 system 那句"只做什么/其余不做"拦得住。
- [ ] 万能工具是雷：菜单挂"联网搜索"又不给定位，产品会自行扩张成"什么都能查"的通用助手。
- [ ] 跨工具流程纪律（先查后报/出口收尾）放 system 是作用域正确：只写进出口工具 desc，则 get_weather/时间工具在跑的那些回合没人记得这条。
- [ ] 诚实注：小菜单 + 域内问句，flash 无 system 也守得住顺序（出口 schema 要的 condition 只有真工具能给 = 数据结构物理锁）。分工的价值在**作用域正确 + 复杂菜单/换模型时站得住**，不在"今天放错会崩"。

### ④ 实测发现（教师预跑，DeepSeek v4-flash / 2026-09-06，用户实证待回填）
- 小菜单对照组（天气+时间+出口，问句全域内）：分工放"不写 system / 写 system / 摊进 desc"三处，**行为完全一致且全对**（写诗 end_turn 不碰工具、时间不乱套 report、混合请求并行点单）——flash 太乖，此档看不出分工差异。
- 决定性档在**菜单含万能搜索工具 + 域外问句**（三镜唯一变量 = 边界写没写进 system）：
  - 镜1 裸奔无 system → 币价调 `search_web` 去搜（能力外泄成通用助手）；珠峰凭记忆照答 8848.86。
  - 镜2 system 声明"专用助手只做天气/时间" → 币价、珠峰**全拒**。
  - 镜3 desc 各自收窄（search 限企业内网）、不写 system → 币价**拒**（无工具归宿）、**珠峰照答 8848.86**（零工具域外 desc 看不见）。
- 结论（可复述）："所有工具自守加起来 = 有整体边界"是错觉；desc 拦得住"要调工具的域外"，拦不住"零工具的域外"。

### ⑤ 工程陷阱与面试追问
- 面试题「system prompt 和工具 description 各该写什么？」→ 答作用域：单工具使用说明/负例去 description；整台 Agent 的身份、边界、跨工具流程进 system。加一句 **"description 管工具用不用，system 管 Agent 该不该接这个活"** 最加分。
- 面试题「为什么只把边界写进工具 description 不够？」→ 答：desc 各自为政、只在"有工具要被调"时触发；零工具请求没有 desc 会拦，只能靠 system 顶层边界。
- 面试题「我的 Agent 什么题外话都接 / 到处乱调工具」→ 先查有没有 system 身份边界，别只加 desc 负例；给它"你是谁/只做什么/域外拒绝"。
- 陷阱：system 是软约束不是 schema，取值仍靠 enum/白名单（第 2 课防线照旧）；system 补的是"整体该不该做"这一维。
- 与第 2 课并置自检：白名单兜得住"域外"、兜不住"域内语义错"；system/desc 同样各有覆盖盲区——**判断规则放哪，本质是判断哪一层能覆盖它**。
- 预留钩子：system 该多长才够（太长稀释 desc？）；"要不要调工具"何时交给独立 router 工具而非靠 system 写死（意图路由深水区）。

### ⑥ 术语·厂商对照·原典
- 术语：system prompt / system message / 全局章程 / 作用域（scope）/ 能力外泄 / 通用助手默认值 / 顶层定位
- 厂商对照：Anthropic `system` 顶层参数 == OpenAI `system` role message（同一概念、不同位置）；工具 name/description/schema 概念一一对应（第 2 课已记）。
- 原典（必读）：Claude 官方 **Tool use** 文档 "Define tools / best practices" 段；延伸读 Prompt engineering 总览的 "system prompts" 节（官方称 system 为"给整个对话设定规则的高层级指令"，即本课"作用域"视角出处）；OpenAI 对应 = Prompt engineering guide 的 system messages。

---

*本文件已积累：第 1 课（M1）✅ ｜ 第 2 课（M2）✅ ｜ 第 3 课（M2）✅ ｜ 第 4 课（M2）🕓 已交付·待用户实证回填。完成新课请按顶部模板追加一节。*
