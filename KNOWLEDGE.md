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

### ④ 实测发现（DeepSeek v4-flash / Anthropic 兼容端点；教师预跑 2026-09-06 + 用户实证补记见文末）
- 小菜单对照组（天气+时间+出口，问句全域内）：分工放"不写 system / 写 system / 摊进 desc"三处，**行为完全一致且全对**（写诗 end_turn 不碰工具、时间不乱套 report、混合请求并行点单）——flash 太乖，此档看不出分工差异。
- 决定性档在**菜单含万能搜索工具 + 域外问句**（三镜唯一变量 = 边界写没写进 system）：
  - 镜1 裸奔无 system → 币价调 `search_web` 去搜（能力外泄成通用助手）；珠峰凭记忆照答 8848.86。
  - 镜2 system 声明"专用助手只做天气/时间" → 币价、珠峰**全拒**。
  - 镜3 desc 各自收窄（search 限企业内网）、不写 system → 币价**拒**（无工具归宿）、**珠峰照答 8848.86**（零工具域外 desc 看不见）。
- 结论（可复述）："所有工具自守加起来 = 有整体边界"是错觉；desc 拦得住"要调工具的域外"，拦不住"零工具的域外"。
- **实证补记（用户完成第 4 课，2026-09-06，在 code/0001 上自跑）**：
  - **挑战 B 复现**：删 system、把同一条边界只写进各工具 description（get_weather 四城限定 / report_weather"无关别调"），单问"珠穆朗玛峰有多高？"→ 模型**直接作答、零工具调用** → "desc 自守拦不住零工具域外"在用户自己循环上成立，与教师预跑镜 3 一致。
  - **挑战 A（0001 恢复 `SYSTEM_SCOPED`）三观察**：① 上海 → 先 get_weather 再 report_weather 结构化收尾（第 3 课出口结构无回归）；② 东京（白名单外）→ **全程无 `[工具请求]` 打印** → 是 system 边界抢在点单前拦截，白名单闸未上场；③ "写诗"不再写（无 system 时第 3 课实证会直接写诗）。
  - **复盘补刀（与第 2 课并置，面试可直接用）**：白名单的漏（模型真点了单）能被**更下游**的执行闸兜底；本课零工具漏**没有下游可兜** → 只能**上游** system 补。于是三层各守一个时刻：**system 管"这台 Agent 该不该接"（点单前）→ desc/schema 管"这一次调用合不合规"（调用中）→ 执行闸管"不合规就别执行"（点单后）**，不互相替代。

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

## 第 5 课 · 字是一个个蹦出来的：流式输出（streaming）· M2

### ① 一句话核心
流式 = 服务器**边生成边把 token 推给你**，用户体感 ≈ **TTFT（首字时间）**；非流式 = 服务器把整段生成完才一次性返回，用户干等的 = 生成到最后一个 token 的**总时长**。流式是 **I/O / 体验层的开关，不是新的 agent 机制**——模型照常"点单 + 说话"，agentic loop 一行不用改。反直觉实锤：**给用户看的文字能逐字蹦，但 tool_use 参数是"半个半个"到的，必须等整块收齐才能执行 → 流式省不掉"工具那一拍"**。

### ② 心智模型
- 一次生成在流式里 = **一串事件**（能默画）：`message_start → content_block_start → content_block_delta ×N → content_block_stop → message_delta（携带 stop_reason）→ message_stop`。共六种事件；delta 有三种：`text_delta` / `thinking_delta` / `input_json_delta`（各内容块类型各有各的 delta）。
- **文字能蹦、工具不行**：text 是 text_delta 一片片拼的，边蹦边看没问题；但 tool_use 的参数是 input_json_delta"半个半个"到的（`{` `"` `city` `"` `: ` `"` `北京` `"` `}`），半截 JSON 不能 json.loads / EXEC → 必须等 `content_block_stop` 收齐完整 JSON。
- **两条收流的姿势**：裸 `create(stream=True)` = 自己逐事件手工拼（引擎盖，教学看事件用）；高级助手 `messages.stream()` = 内置帮你拼——`text_stream` 只吐给用户看的 text 块（thinking / 参数已剥），`get_final_message()` 把流拼回**与非流式 response 同形状**的 message（content / stop_reason / usage 都在，`ToolUseBlock.input` 已是 dict）。
- 一句话判据：**想拿工具参数，去 `get_final_message()` 返回对象的 `block.input` 取，别去流里捡碎片。**

### ③ 要点清单
- [ ] 用户体感指标 = **TTFT（首字时间）**；流式**不改总时长**、不改模型决策 / 工具顺序 / 最终答案，只改"字什么时候送达"。
- [ ] 能默画六事件 + 三种 delta；`stop_reason` 藏在 **message_delta**（不在 message_stop）。
- [ ] input_json_delta 半路不能执行 → 等 `content_block_stop`；这就是"流式省不掉工具那一拍"的原因。
- [ ] `text_stream` 只吐给用户看的 text 块——想拿参数别找它，`get_final_message()` 的 `block.input` 才是收齐的 dict。
- [ ] 高级助手 vs 裸流：`messages.stream`（内置拼装、drop-in 替换 create）vs `create(stream=True)`（自己逐事件拼，lab 镜 2 / 3a 用）。
- [ ] end_turn 分支别把已逐字蹦过的文字**再打一遍**（切流式后原 `print("最终答案:", final)` 会二次输出——挑战 A 唯一要收拾的尾巴：删掉或只作兜底）。
- [ ] **收尾必须查 `stop_reason != "end_turn"`**：截断 / 拒答 / 内容过滤都不是"模型自己觉得写完了"。
- [ ] 流式让"截断"从**静默变可见**：非流式整包给你、少了尾巴常察觉不到；流式你能看见句子蹦到一半戛然而止。
- [ ] thinking 该不该也流式展示给用户 = **产品决策**，不是技术对错。

### ④ 实测发现（DeepSeek v4-flash / Anthropic 兼容端点；教师预跑 2026-09-06 + 用户实证补记见文末）
- 镜 1 同一句"写十二行诗"：非流式干等 **2.50s** 整首出现（168 字）；流式首字 **617ms** 即到、**1.99s** 蹦完（178 字）。**总耗时几乎不变** → 流式优化空窗期，不制造"更快 / 更便宜 / 更聪明"。
- 镜 2 裸流事件序列（关 thinking）：六种事件干净可复现；"收到收到"被拆成两个 `'收到'` text_delta。
- 镜 3 带工具：thinking_delta 先到（index 0）→ tool_use 的 input_json_delta 碎片拼成 `{"city": "北京"}`。**某些 run 里 thinking 与 tool_use 之间会夹一个圆场 text 块（"我来帮您查询…"），也可能没有——随机，别把"有没有圆场话"当判据**。高级助手 `text_stream` 正确剥 thinking 只给可见字。
- 镜 4 决定性：同一份 agentic loop 只切 streaming 布尔，两遍"上海天气"日志**逐字一致**（get_weather → report_weather → ✅ 结构化出口），无回归实证。
- `thinking={"type":"disabled"}` 该端点**可用**（不 400）；与第 3 课"显式 tool_choice 会 400（Thinking mode 不支持）"不矛盾——后者是该端点 thinking 模式下的参数限制。
- max_tokens=16 截断前提（挑战 B）：300 字散文蹦到"午后的"戛然而止，`stop_reason=max_tokens`，`usage.out=16`。
- **实证补记（用户完成挑战 A/B，2026-09-06，code/0001 + code/_truncate.py）**：
  - 挑战 A 手术刀改 0001 成功：唯一 API 调用点换成 `with messages.stream + text_stream 逐字打印 + get_final_message()`，agentic loop 其余一行没动；`end_turn` 分支"最终答案"兜底打印已注释（防重复打印已蹦过的字）。观察①② 对：上海工具序列 / 结构化出口与非流式成品一致（无回归）；东京 / 写诗是 system 拦截的纯文字答复，也是蹦出来的（短句蹦字感弱，最强的打字机效果在 lab 镜 1 长诗）。
  - **观察③ 答偏（本课最重要的纠正）**：用户答"因为并没有调用这个 tool"——只对"写诗"那次 run 成立（system 拦截、零工具），不是机制。正解：**循环从不读裸流参数——`s.get_final_message()` 把 input_json_delta 碎片重新拼成完整 JSON，放进返回对象 `ToolUseBlock.input`（已是 dict）；循环从 `response.content` 取 dict，根本没见过碎片 → 不用等、不用手动拼**。上海那次 get_weather 真被调、参数真的一半一半到，循环照样直接拿完整 dict 执行——把 0001 留言改回上海跑一次即可亲手确认。
  - 挑战 B：① stop_reason=max_tokens（蹦到半句就断）观察正确；② 只描述了非流式截断的结局（"直接输出文字、超出部分不显示"），漏了"扎眼在**断的过程被看见了**"——流式下截断发生在眼前，非流式整包送达、少了尾巴察觉不到；③ 待补 why：`stop_reason` 不等于 end_turn（截断 / 拒答 / 内容过滤）就不是真写完，不查会把半截话当最终答案交付；且 thinking 与正文**共享 max_tokens 预算**（第 3 课），thinking 吃光预算、正文被静默砍半时 stop_reason 同样是 max_tokens → 收尾查 stop_reason 是生产必修，看不出"写完没写完"就交付会翻车。

### ⑤ 工程陷阱与面试追问
- 面试题「非流式和流式，用户体感差在哪？」→ 空窗（憋完生成总时长再整包给）vs 首字即到（TTFT）；流式不改总时长。
- 面试题「流式会让 Agent 更快 / 更省 token / 更聪明吗？」→ 都不。只改投递层：usage、决策、工具顺序、最终答案全不变（镜 4 逐字一致为证）；工具那一拍因参数要收齐完整 JSON 反而省不掉。
- 陷阱① "以为 stream 了工具也快了"：文字能边蹦边看，工具不行（参数收不齐就不能解析、不能 EXEC）；要查天气的回合，答案永远等工具执行完、下一轮模型交回 `report_weather`。
- 陷阱② "把 text_stream 当参数通道"：text_stream 只吐给用户看的 text 块，thinking 与工具参数都被过滤；要参数去 `get_final_message()` 的 `ToolUseBlock.input` 拿现成 dict。
- 陷阱：拿"两次 run 内容不同 / 有没有圆场话"去反推流式副作用——那是抽样噪声与模型自主性（有无圆场话是随机的），不是流式改的。
- 陷阱：max_tokens 截断在非流式下是**静默**的（整包给你、尾巴丢了常无感）→ 无论流式与否，生产都要收尾查 `stop_reason != "end_turn"` 发现截断 / 拒答。
- 陷阱：切流式后 `end_turn` 分支原 `print("最终答案:", final)` 会把已逐字蹦过的文字**再打一遍**——删掉或只在没蹦过字时兜底。
- 预留钩子：thinking 要不要流式展示给用户（产品决策）；用户点停止 / 网络断了半路取消（cancellation）怎么收尾；流式输出怎么做 eval / judge。

### ⑥ 术语·厂商对照·原典
- 术语：streaming / TTFT（time to first token，首字时间）/ event（事件）/ content_block_start / content_block_delta / content_block_stop / text_delta / thinking_delta / input_json_delta / message_delta / message_stop / stop_reason / text_stream / get_final_message / SSE
- 厂商对照：Anthropic 高级助手 `messages.stream()`（内置拼流成 message，drop-in 替换非流式 create）vs 裸 `create(stream=True)`（逐事件手工拼）；OpenAI 对应 = `stream=True` / Responses API 的流式，同"边生成边发"、事件命名不同（本课不展开）。概念在两端都有一一对应——找 SDK 里"把流收成一个 message"的 helper 就是 `get_final_message` 的同类。
- 原典（必读）：Claude 官方 **Streaming Messages** 文档（platform.claude.com/docs → streaming），精读 **Events 列表**与 **SDK 用法**段（`text_stream` / `get_final_message` 这些名字全来自官方那页，能默画就是真懂）。

---

## 第 6 课 · 越聊越贵：把每次调用算成账（成本与 token）· M2（收官）

### ① 一句话核心
Agent 烧钱 = **输出单价高 + 每一轮重读全部历史**。模型是**无状态函数**，每轮都得把【全部历史 + system + 工具说明书】重新发一遍 → 对话越长、每轮 input 越大，**越聊越贵，且贵得越来越快**。把一次调用拆成 input / output 分开计价（output 通常贵很多）、用 max_tokens 封顶单次输出的最坏账单、让每轮不变的前缀命中缓存降重复读的单价、再每轮读 usage 记账，才算"把 Agent 算成账"。

### ② 心智模型
- 一次 usage 最少看两个数：**input / output 分开计价，output 比 input 贵很多**（本端点 flash 低谷 in ¥1.5/M vs out ¥4.5/M，输出 3 倍）；缓存命中时还有 `cache_read_input_tokens`。
- **最大的坑：每一轮模型都把整段历史从头重读一遍**——不是你只把"这一轮新增的话"发过去，连工具往返都重读：第 1 次 get_weather 之后你把 tool_use 记录 + tool_result 塞进 messages，第 2 次调用把整段（含这段）从头重读。
- **读 usage 的正确口径（本课 decisive）**：在自动缓存端点上 `input_tokens` 报的是"缓存未命中、按全价算的新增部分"，不是完整 prompt；**完整 prompt = input_tokens + cache_read_input_tokens**。只盯 input_tokens（被缓存压得又小又平）会误以为"每轮没在重读历史 / 越聊不越贵"。
- 缓存原理：把**每轮都不变的前缀**（system + 工具说明书 + 长指令）存起来，下一轮命中就按超便宜的命中价算。但**缓存砍的是"重复读的单价"，砍不掉"每一轮都在读一遍"这件事本身**——新增对话（未命中部分）永远全价，随对话变长只多不少。
- max_tokens 是**单次输出的封顶**（最坏输出账单的上限），不是省钱开关：① input 那一头照旧全算（历史重读一分不少）；② **thinking 与正文共享这个预算**——给太小，thinking 先吃光，你为看不见的字付了钱还得到一次截断。
- 成本公式：cost = 新增 in×全价 + 命中 in×命中价 + out×单价。换挡（改价格常量）只把账本**线性缩放**，不改"每轮重读历史、对话越长越贵"的结构。
- **四把扳手**：① 读 usage 记账（看清账本）② max_tokens 封顶最坏输出 ③ 缓存降重复读单价 ④ **别让对话无限长**（截断 / 摘要 / clear）——只有 ④ 砍的是缓存也砍不掉的"对话变长"本身。

### ③ 要点清单
- [ ] 会读 usage：input / output / cache_read_input_tokens 各是什么；**模型每轮实际读了 = input_tokens + cache_read_input_tokens**，别把 input_tokens 单独当完整 prompt。
- [ ] 越聊越贵的机制链：无状态函数 → 每轮重读全部历史 → 对话越长每轮 input 越大 → 成本只涨不跌（镜 2 实测完整历史 445 → 553 → 667，每问 +100 左右）。
- [ ] **一个问题内部的多次调用也在涨**：一次"上海天气"≥2 次模型调用（先 get_weather 再 report_weather 收尾），第 2 次重读了第 1 次往返 → Agent 账单 = 循环内每次调用 input 的加总。"一个问题内部往返"与"对话被拉长"烧的是同一机制：**每多一次调用，就多一次整段重读**。
- [ ] max_tokens 是"单次输出账单的封顶"，不是省钱开关；thinking 与正文共享预算，给太小 = 白付钱 + 正文截断甚至 0 字可见。
- [ ] 自动缓存命中是"尽力而为"：同一前缀第一次出现时 cache_read 为 0（还没跑热），第二次起才可能命中；别把某次 cache_read=0 当成"端点不支持缓存"。
- [ ] 缓存省的是重复读的**单价**，砍不掉新增（未命中）与"对话变长"本身；只盯 input_tokens 会误以为越聊不越贵。
- [ ] 会算账：用 cost = in×单价 + out×单价 把真实 token 换成人民币，能估一个月量级（镜 4：一场 3 问对话 ≈0.66 分 vs 自动缓存 ≈0.22 分；放大 100 用户×30 问/天×30 天 ≈199 元/月 vs ≈66 元/月）。
- [ ] 明确知道砍"对话变长"的是第 4 把扳手（截断 / 摘要 / clear），**不是缓存**。

### ④ 实测发现（DeepSeek v4-flash / Anthropic 兼容端点；教师预跑 2026-09-06 + 用户实证补记见文末）
- usage 在该端点是自动缓存口径：同一请求发两次，第二次 `input_tokens=18 + cache_read_input_tokens=384 = 402`，与首跑 402 吻合 → input_tokens 只报未命中新增，重复前缀进 cache_read（DeepSeek 原生"自动上下文缓存"透传到 Anthropic 兼容端点的 usage）。命中"尽力而为"、跨脚本同前缀也命中。
- `count_tokens(messages)` 在该端点可用且返回全量（与 input+cache_read 相等，404=404），是**不受缓存干扰、看完整 prompt 到底多大**的官方真值。
- decisive 实验（看完整历史涨而非只看 input_tokens）：445 → 553 → 667 只涨不跌；cache_read 384 → 512 → 640 越滚越大（自动缓存吃掉重复前缀）；新增 in 一直很小。同问内第 2 次调用更大（工具往返被重读）。
- max_tokens 截断 + thinking 共享预算实锤：300 字散文 max_tokens=32 → usage.out=32、stop=max_tokens、可见正文 **0 个字**（thinking 吃光预算，为 32 个输出 token 付钱却一字不见）；max_tokens=2048 → end_turn、357 字。
- 成本换算（flash 低谷价：in ¥1.5/M、命中 ¥0.05/M、out ¥4.5/M）：镜 2 那场 3 问对话（新增 in 503、命中 3072、out 286，完整等效 3575）——不缓存 ≈0.66 分 vs 自动缓存 ≈0.22 分（省约 2/3）；放大 100 用户×30 问/天×30 天 → 不缓存 ≈199 元/月 vs 自动缓存 ≈66 元/月（量级感）。**缓存省的是重复读的单价，full 曲线照涨**——正好点破"缓存 ≠ 停止增长"。
- 显式 cache_control 探针：system 块发 `cache_control={"type":"ephemeral"}` **不报 400**，但 cache_creation/cache_read 不因其点亮 → 该端点缓存是自动的、cache_control 不"手动控制"。诚实口径：别假设 cache_control 一定生效，靠读 usage 确认。
- **实证补记（用户完成挑战 A/B + 收束自释，2026-09-07，code/0001 + code/0006-cost-lab.py）**：
  - 挑战 A（给 0001 装账单仪表盘）：0001 落点核对通过——只加两个价格常量 + `s.get_final_message()` 后一行账单打印，流式循环与 agent 逻辑一行未动，第 5 课成品态保持。观察①②③ 定性都对（一次"上海天气"内第 2 次调用 input 更大）；追问补点破：多出来的是"第 1 次调用后塞进 messages 的 tool_use 记录 + tool_result，第 2 次整段重读把它读进来"；"一个问题内部往返"与"对话被拉长"是同一个计数器在涨（每多一次调用就多一次整段重读，账单 = 循环内每次调用 input 的加总）。
  - 挑战 B：② 换高峰价后镜 2 曲线没变、③ clear（第 4 把扳手）砍的是缓存也砍不掉的"对话变长"——都对；**① 未重跑，理由"换挡必翻倍、跑它没信息量"——认可为看穿题眼**（价格只是把账本线性缩放 ×2：≈199→≈398、≈66→≈132，结构不随价格变）。
  - 收束自释逐空判卷：核心机制全对（usage 最小读法 / 无状态函数 / max_tokens 共享预算 / clear 扳手），两处修回课件口径——完整 input 要说字段名 `input_tokens + cache_read_input_tokens`（不是"新的+过去缓存前缀"）；缓存只把重复前缀的**单价**打折（别把"单价"说成"缓存"）；"只盯 input_tokens 误以为"的方向是"每轮没在重读历史 / 越聊不越贵"，不是"价格变低"。
  - 价格基准（2026-09-06 查证）：DeepSeek 2026-08-17 起峰谷分时计价、2026-08-23 起周末全天低谷价；flash 低谷 in ¥1.5/M、命中 ¥0.05/M、out ¥4.5/M，高峰翻倍（3.0 / 0.10 / 9.0）。课件与脚本均标"以官方为准、价格会变"。

### ⑤ 工程陷阱与面试追问
- 面试题「为什么 Agent 越聊越贵？」→ 先答"每一轮重读全部历史"这一层（无状态函数，历史越攒越长、每轮 input 只涨不跌），再答缓存——比只背价格表高一档。
- 面试题「把 input_tokens 当完整 prompt 对不对？」→ 不对：自动缓存端点上它是"未命中新增"，完整 prompt = input_tokens + cache_read_input_tokens；只盯它得出"越聊不越贵"是错结论。
- 陷阱① "把 max_tokens 当省钱旋钮"：它只封顶单次输出账单；input 那头的历史重读一分不少，thinking 还与正文共享预算（给太小 = 白付钱 + 截断）。
- 陷阱② "以为用了自动缓存，成本就不再随对话变长而涨"：缓存只把重复前缀的单价从全价打到命中价，新增对话永远全价、随变长只多不少 → 成本曲线照涨，只是斜率变缓。
- 陷阱③ "以为发 cache_control 就一定生效"：该端点缓存是自动的、cache_control 不"手动控制"；判断标准是读 usage 里 cache_read / cache_creation 亮没亮。
- 面试加分：把"四把扳手"按作用说全——记账 / 封顶输出 / 缓存降单价 / **别让对话无限长**；只有第四把砍的是缓存也砍不掉的"对话变长"。
- 预留钩子：对话多长该"截断 / 摘要 / 归档"才划算（M3 记忆与上下文的入口）；缓存命中率怎么在生产里监控（M6 可观测性）。

### ⑥ 术语·厂商对照·原典
- 术语：usage / input_tokens / output_tokens / cache_read_input_tokens / cache_creation_input_tokens / count_tokens / max_tokens / prompt caching（自动上下文缓存）/ 缓存命中价 / stop_reason / end_turn
- 厂商对照：Anthropic **显式** cache_control（`cache_control: {"type":"ephemeral"}` 标缓存点）vs DeepSeek **自动**上下文缓存（免配置，usage 自动出 cache_read，cache_control 不手动控制）；OpenAI 概念一一对应（usage 字段命名不同）。结构规律每家都一样：输出比输入贵、缓存命中比未命中便宜、强模型比弱模型贵。
- 原典（必读）：Claude 官方 **Counting & displaying token usage** 文档（usage 字段与 counting tokens 段——本课 input / cache_read / count_tokens 全来自这一页，能默画 usage 结构就是真懂）；**Pricing** 与 **Prompt caching** 官方页（platform.claude.com）。延伸对照：DeepSeek 官方定价与自动上下文缓存说明（platform.deepseek.com → 文档）；OpenAI 的 token 计费 / prompt caching 对应页。

---

## 第 7 课 · Agent 怎么记得住：多轮状态与上下文管理 · M3（第一课）

### ① 一句话核心
模型是**无状态函数**，本身没有记忆；Agent 能"记住"，唯一原因是**每轮把历史喂回去**——它"记得"的边界 = 你此刻喂进上下文窗口里的内容。多轮不断链 = 代码每轮把 user **和 assistant 都 append** 回 messages（漏了 assistant 那半就断片甚至 400）；对话太长会越聊越贵（第 6 课）甚至撞上下文上限 → 三招压缩历史：**截断 / 滑动窗口 / 滚动摘要**——都是取舍，不是记忆。想"记得久 + 不无限烧 + 细节不丢"，窗口/摘要都做不到，出路是**检索注入（RAG）**（下一课落地）。

### ② 心智模型
- **记忆分两层**：① 上下文窗口里的现成记忆（working / short-term）= 你发的 system + 工具 + 历史；② 长期记忆 = 你自己存出去、用时捞回来的外部存储（文件 / DB / 向量 / RAG）。**模型从不主动碰外部，一切存取都是应用代码**。
- **多轮状态不是模型的属性，是你代码的产物**：messages 列表 + "每轮把 assistant 答复也 append 回去"。断链几乎总是**只 append user、漏 assistant** → 下一轮模型没有"我说过 X"的依据（真 Anthropic 上还违反 user/assistant 严格交替 → 400）。
- **上下文窗口 = 稀缺预算**：同时被 system + 工具说明书 + 历史占着，每轮模型把整段重读（第 6 课）。对话太长撞上限 → 三招取舍：
  | 招 | 做法 | 保住 | 丢掉 | 额外代价 |
  |---|---|---|---|---|
  | 截断 truncation | 超长就砍掉最老、一次砍到装得下 | 近况 | 最早整段 | 无（最省） |
  | 滑动窗口 window | 只留最近 N 轮 | 近 N 轮 | N 轮之前全部 | 无（prompt 封顶） |
  | 滚动摘要 summary | 老的压成一段要点、留最近原文 | 要义 | 细节数字 / 原文措辞 | **每压一次 = 一次模型调用**；压缩器也是模型，保不保留看它 |
- **三招都不是"记忆"，都是"取舍"**：截断/窗口把整段最早丢掉、摘要把细节压缩掉。想"记得久 + 不烧钱 + 细节不丢"，靠窗口/摘要都不行 → 出路是**检索注入**：把历史/知识存到外部、每轮只把最相关的几段检索进来喂。本课只立心智，下一课落地。
- 与第 6 课接缝：窗口/摘要砍的是"**别老读那么长的历史**"（第 6 课第 4 把扳手）；缓存砍的是"重复读的**单价**"。两者不互斥、各管一段——别拿缓存当"能无限留长对话"的救兵。

### ③ 要点清单
- [ ] 能一句话讲清：模型无记忆；"记得" = 那段历史还在你喂进去的输入里。验证法：同一道回忆题，**带历史 vs 冷启动（零历史）**——冷启动只能承认不知道 / 追问。
- [ ] 把"答一句就退出"改成真·多轮，agentic loop 几乎不动，只加两层：**外层读输入的死循环** + **每轮把 assistant 最终答复 append 回 messages**。
- [ ] 漏 append assistant（只存 user）→ 断片；**把半截 tool_use 留进历史 → 下一轮 400**。工程写法：历史只存"一问一答的纯文本对"，agentic loop 的工具往返放局部 working、不入档（0001 落点）。
- [ ] 三招名字要脱口而出：**截断 truncation / 滑动窗口 window / 滚动摘要 summary**；各自丢什么、多付什么（截断丢最早·免费 / 窗口丢 N 轮前全部·免费封顶 / 摘要丢细节·多付一次摘要调用）。
- [ ] **摘要保住多少不保证**：压缩器也是模型——某细节保不保留 = 你的压缩指令点没点名 + 它怎么理解。实证：指令点名保留的航班号/会议号都在摘要里；没点名的可能丢。
- [ ] 想"记得久 + 不无限烧 + 细节不丢"：窗口/摘要都做不到 → 检索注入（RAG）。窗口/摘要解决的是"别无限长"，不是"记忆完整"。

### ④ 实测发现（DeepSeek v4-flash / Anthropic 兼容端点；教师预跑 2026-09-07 + 用户实证补记见文末）
- **镜 1 · 无状态 decisive**（真实天气 agent + 工具）：连问 上海天气 → "那北京呢？"（能接上、调用 get_weather(北京)）→ 回忆题"我第一次问的哪个城市？"答 **上海**、输入含'上海'=True；**冷启动同题 → "历史里没有提到过任何城市的天气信息……无法回答"**、输入含'上海'=False。确定性 has_fact + 模型回答双轨一致 → **记得 = 事实还在你喂的输入里**。
- **镜 2 · 三招管长对话**（固定 6 轮"出游备忘"回放，A/B/C 吃同一段对话；回忆题走**无工具纯召回**，防"现查工具"掩盖失忆）：
  - A 全留：每轮喂的 prompt **236→264→295→332→363→423** 只涨不跌（第 6 课曲线照搬）；两道最早事实题 ✅✅。
  - B 窗口(最近 2 轮)：prompt **封顶 ≈229**；两题 **❌❌**——航班号题**答成后来的 HO1252（拿新值顶替原值，最值钱的翻车现场）**、会议号题诚实答"历史里没有记录"。
  - C 滚动摘要：老 5 轮压成一句（**多花 1 次压缩调用**），prompt 封顶 ≈302；两题 ✅✅（指令点名保留的 HO1251→HO1252、881204、周日改周六晚都在）。
- **摘要原文可见"压缩器自作主张"**：保住什么 = 压缩指令点没点名（压缩器也是模型）——这个诚实口径是镜 3 的落点。
- 实现取舍（写进课件诚实提醒）：镜 2 用**固定回放**而非真生成，把"策略差异"与"回答随机性"解耦；"事实在输入里"用确定性 has_fact 检查，模型回答只当佐证。第一版真生成实验失败（模型可"现查工具"掩盖失忆、还会绕开工具自编温度污染确定性事实），故改回放。
- **实证补记（用户完成三镜 + 挑战 A/B + 收束自释，2026-09-08）**：
  - 挑战 A（0001 真·多轮 REPL）：工作区 0001 改动为物证——已从"答一句就退出"改成 REPL：外层 input 死循环 + `answer()` 用局部 working 跑 agentic loop（工具往返不入档），每轮把「user 提问 / assistant 最终答复纯文本」append 回 messages（end_turn 分支补上 append；出口工具那路把结构化答案转成文本记回，防未闭合 tool_use 导致下一问 400）。自检四连问（上海 → 北京呢 → 现在几点 → "我第一次先查了哪个城市"）能对上、账单每轮 input 只涨不跌 = 通过，既保留第 5/6 课成品态又真跨轮记住。
  - 挑战 B（量 tradeoff）：把 0007 窗口的 `KEEP` 从 2 调大 → 最早事实题从 ❌ 转 ✅、管理期 prompt 从封顶 ≈229 随 KEEP 抬高、涨回接近全留 → 亲手量出"记忆完整度是用 token 买来的"。口答：滚动摘要比滑动窗口多花的钱 = 多付压缩器那**一次模型调用**，买到的是"窗口外老历史的要义"还留在输入里、能答上。
  - 收束自释逐空判卷（判卷基准见 0008-lesson-7-designed.md 核心概念表）：**核心全对**——一句话核心答得锋利（"记得的边界 = message 里的内容"）、漏 append assistant → 断片、三招共同代价是丢信息、摘要多付一次压缩调用且"原先 message 保住多少要看压缩器"、出路指向长期记忆 RAG。**修回/补点三处**：① 第一招术语漏了名字 = **截断 truncation**（被追问"截断 vs 窗口"可答：长度触发砍一次 vs 轮数触发恒定裁，两者都丢最早整段——共同点比区别重要）；② "把 message **原样**喂回"只在裸多轮成立，上窗口/摘要后喂的是"历史的一个视图"；③ 补"两层记忆"分法：working memory = 上下文窗口 vs 长期 = 外部存储，模型从不主动碰，存取全是应用代码。

### ⑤ 工程陷阱与面试追问
- 面试题「Agent 有记忆吗？」→ 模型无状态；"记得" = 你每轮喂回去的历史，边界 = 上下文窗口里此刻的内容。想记得久：存外部 + 检索注入，不是靠把窗口开大。
- 面试题「为什么聊到一半它忘了 / 断片？」→ 分两类答：**断链** = 你少 append 了（几乎总是只 append user、漏 assistant → 甚至 400）；**健忘** = 它本来就没见过那段（窗口裁了 / 没喂 / 摘要没保住）。别赖模型。
- 陷阱① "以为摘要免费"：每压一次 = 一次模型调用，有自己的 cost；且压缩器也是模型、会自作主张，保不保留细节不保证。
- 陷阱② "以为窗口/摘要能无限压成本又不丢记忆"：窗口丢整段、摘要丢细节数字——都是**取舍不是记忆**；真"记得久又不贵"是检索注入。
- 陷阱③ "拿缓存当救兵"：缓存砍的是重复读的**单价**（第 6 课），砍不掉"对话变长要读更多"；窗口/摘要才是砍"别老读那么长历史"的。两者各管一段，不互斥。
- 面试加分：把上面三招**取舍表**默画出来 + 主动补一句"摘要每次要付一次压缩器调用、且压缩器是模型会失真"——比只背"截断窗口摘要"高一档。

### ⑥ 术语·厂商对照·原典
- 术语：stateless（无状态）/ context window / working memory vs long-term memory / multi-turn / message history / truncation / sliding window / rolling summary / REPL / context rot
- 厂商对照：多轮状态 + 上下文管理是**客户端逻辑**，Claude / OpenAI / DeepSeek 全一样（都是你维护 messages、每轮整段重发）；厂商差异只在"窗口上限多大 / 输出单价 / 有无自动缓存"（第 6 课已对照）。"上下文工程"是跨厂商的通用工程学，不是某家 SDK 特性。
- 原典（必读）：Anthropic **Effective context engineering for AI agents**（把上下文当稀缺资源，四策略 write long / read selective / divide & conquer / summarize——本课"三招" = 它的工程化子集）；Anthropic **Memory** 官方页（短期 = 上下文窗口 vs 长期 = 外部存储的两分法）。

---

## 第 8 课 · 检索注入 / RAG 上手：把"最相关几段"喂进上下文 · M3（第二课）

### ① 一句话核心
**RAG = 检索（retrieval）增强（augmented）生成（generation）**：先把资料**切块**、每块算好**向量**建索引；提问时把问题也变向量，挑出最接近的 top-k 块**原文**塞进 prompt，再让模型**只依据这些原文**作答。**模型没换、也没背过你的资料**——变的只是"这次输入里多了几段精选原文"。这就是第 7 课"记得久 + 不烧钱 + 细节不丢"的工程答案，也是 Anthropic 上下文工程里 **read selective（只读相关）** 的落地。

### ② 心智模型
- **两段式，别神化**：先检索（在资料库找几段原文）→ 再增强生成（原文 + 问题一起给模型）。真正答话的仍是那个无状态函数（第 6/7 课立）；RAG 改的是"这次喂了什么"。面试第一句答这个 = 说明你不玄。比喻：**开卷考试——先把书翻到那一页再让你看，不是让你背书**。
- **五步流水线（要能默画）**：`切块 chunking → 每块 embed 成向量 → 建索引（向量库）→ 提问时问题也 embed、取余弦最像的 top-k → 把这几块原文拼进 prompt 让模型作答`。
- **embedding 把语义变成几何**：一个 embed 模型把"文字"映射成数字向量，语义近 → 向量近，比距离用**余弦相似度**。铁律：**向量只在同一个 embed 模型内可比**——别拿两家的向量互算相似度，像别拿公里数比斤两。
- **"向量库"不神秘**：最小实现就是一张 **(文本, 向量) 的表 + 余弦排序**；Chroma / FAISS / pgvector 只是把同一件事做得更快、能持久、能上亿条。
- **检索有几档**：字面/关键词（BM25、2-gram）→ 语义（embedding，本课）→ 重排 rerank（在 top-k 里再精排，延伸）。**RAG 质量的上限 = 检索质量**：检索没捞对，后面给多强的模型都白搭。
- **注入那一下就是你早就会的拼 prompt**：经典 RAG 放 system / "参考材料"；包成工具就是挑战 A（落在 `tool_result` 里）。两者都只是"这次请求里多了几段原文"。
- **为什么不全塞**：① token 涨（第 6 课的账）；② 噪音灌入 + **稀释注意力**（context rot，第 7 课引过数据）。官方提醒：资料库很小（<20 万 token，约 500 页内）时，配提示词缓存直接全文塞可能更简单划算——**别为上 RAG 而上 RAG**。
- **切块是检索的粒度**：块太大颗粒粗、夹带噪音；太小断语境。本课用手工"主题段落"切，保持每块自洽。

### ③ 要点清单
- [ ] **五步流水线**脱口而出；能一句话说清"模型没换"。
- [ ] **闭卷会编**（decisive）：不给材料让 flash 答"我们公司紧急发版流程"，它编出一整套"合理但假"的流程。→ 答不出来不是模型笨，是**你没喂对**。
- [ ] **关键词会断、语义不断**：换一种说法问，字面重合度 0.62 → 0.11 断了；embedding 0.77 → 0.67 稳稳捞对。
- [ ] **检索=空时，模型不但答不出，还会连引用一起编**（实测它假引了一条手册里不存在的条款）——这比"答不出"危险得多。
- [ ] **提示词给边界是软的**：「只依据材料、材料没有就说不知道」能压住大部分编造，但**硬防靠 eval + 你自己校验**。
- [ ] **分数阈值/命中下限**是真实检索器防"拿噪音当答案"的常规做法；但**两路检索的量纲不同，阈值不可跨路搬运**（本课实测，见 ④）。
- [ ] 向量只在自己这个 embed 模型内可比；`embedding 模型 ≠ 对话模型`（前者输出数字，后者输出文字）。
- [ ] 对话走 DeepSeek、向量走本地 bge 是**正常架构**：DeepSeek / Anthropic 官方都没有 embeddings 端点，RAG 天生是"两家组装"。

### ④ 实测发现（DeepSeek v4-flash / Anthropic 兼容端点；教师预跑 2026-09-09 + 用户实证补记见文末）
- **镜 1 · 检索注入才答得出（决定性）**（Q=紧急发版，真值"须经 CTO 书面批准 + 发布后 24h 内补复盘会"只在 C06，公司特有流程、常识猜不中）：
  - A 零注入（132 token）：flash **凭空编出一整套 4 步假流程**（两级审批 / 拉群确认 / 次日补记录 / 抄送 VP），含『CTO』False、『复盘』False。
  - B 注入 top-1 C06（213 token）：照手册答对，含『CTO』True、『复盘』True。
  - C 全量 8 块（591 token）：也答对，但喂的 token ≈ B 的 **2.8 倍**。→ B 又准又小 = 检索注入存在的理由。
- **镜 2 · 关键词 vs 语义（决定性）**（同一件事问两遍）：
  - 照原话问：关键词重合度 **0.619** ≥ 下限 0.15 → 命中；语义 0.770 捞对。→ 关键词不是没用，是**只认字面**。
  - 换说法问（骑车摔伤去诊所缝针）：关键词顶到 C04 也只 **0.107 < 0.15 → 判无命中（检索=空）**；语义仍 **0.665** 捞对。
  - 佐证（很值得讲）：关键词路检索=空 → flash 编了段"工伤认定"理论，还**假引手册里不存在的条款**"【员工因工受伤，享受医疗补充保险待遇】"；语义路送 C04 → 照抄"门诊报销 80%、上限 5000"。
- **镜 3 · 三题语义 top-1 全命中**（C06 0.700 / C04 0.665 / C05 0.763）；token 账 **164 / 318 / 591**（零注入 → 注入 top-3 → 全量 8 块）：送"答案页+邻页"约 +150 token，再拖全量约 +270。
- **诚实口径**：检索成败用确定性 ground-truth chunk_id 判定（top-1 命没命中），模型回答只当佐证——换模型 / 换提示词会变的是措辞，"编不出 CTO/复盘"这件事是稳的。
- **实证补记（用户完成挑战 A/B + 收束判卷，2026-09-10）**：
  - **挑战 A（0001 挂 search_manual）**：三处小改全做对——TOOLS 加一项说明书、把 0008 的 `CHUNKS` + 模型加载 + `search_semantic` 搬进 0001、system 加"公司政策类先调它、只依据材料"章程。自检两问通过：出差住宿 → **600 元**；下午茶（手册没有）→ **"手册资料里没有"**，没编。
  - **踩中两个真 bug（都当场复现）**：① **形参名必须等于 schema 的 properties 名**——写成 `lambda q:` 而 schema 里是 `query` → 执行处 `EXEC[name](**block.input)` 当场 `TypeError: got an unexpected keyword argument 'query'`。通则：**工具函数的形参名 = input_schema 里的键名，两端必须字面一致**。② **脚本必须跑在项目 venv**（`agent-lab\.venv\Scripts\python.exe`）——全局 python 有 anthropic、没 fastembed，第 1~7 课跑得动，一引入 embedding 就 `ModuleNotFoundError: No module named 'fastembed'`。**"前几课都能跑"不等于环境没问题**。
  - **追加实验：给检索加分数下限（`MIN_SCORE=0.6`）**——本机实测同一批块上：
    | 送入检索的 query | top-1 余弦 | 0.6 下限 |
    |---|---|---|
    | 我下周出差去上海，住酒店一晚公司最多能报销多少？（命中） | 0.731 | ✅ 过 |
    | 公司下午茶标准是多少？（手册没有） | 0.494 | ❌ 滤 |
    | 那二线城市呢（**原话**，C02 里其实有答案） | 0.430 | ❌ 会被误杀 |
    | 出差住宿报销标准 二线城市 每晚上限（**模型自己改写**） | **0.827** | ✅ 过 |
  - **正收益**：加下限后 Q1 的第 2 块 C03 市内交通（0.564 < 0.6）在**进模型之前**就被砍——回答里那条"（补充一条可能相关的：市内交通…）"的噪音消失，**噪音灌入 = 能看见、能省 token**。
  - **➊ 量纲不可跨路搬运（本课最值钱的一条）**：0.15 是**关键词路的字面重合率**（没重合就是 0）；余弦是**语义方向**的度量，中文短句之间天然就在 **0.27~0.5** 之间飘。**把 0.15 搬到余弦上 = 永不触发 = 等于没设**。阈值必须按自己那一路的分布重新标定。
  - **➋ query rewriting 是隐性变量**：「那二线城市呢」按原话检索只有 0.430（会被 0.6 误杀），但模型**自己把它改写成了自足查询**（0.827）救回来了。所以"追问会不会被阈值误杀"**取决于送进检索的 query 长什么样**——而模型改不改写**不稳**（换模型/换提示词就可能原样甩进来）。工程结论：别把"追问答得对"赌在模型自发改写上，要么在工具描述/system 里**明确要求 query 自足、带上主题**，要么做**多轮查询改写**。哪种更好 = 下一课 eval 要量的东西。
  - **检索为空时给模型一句明确的话，别甩空串**：0001 的 `search_manual` 在下限过滤后若为空，返回"没有找到相关内容…请如实告诉用户手册资料里没有，不要推测"——**空串 = 把编造权交还给模型**（镜 2 的"检索=空 → 连引用一起编"就是现场）。
  - **挑战 B 口答判卷**：① top_k 太小 → 正确答案那块没进 top → 答不出或编；太大 → 噪音灌入 + token 涨 + 稀释注意力 ✅；② 向量库不神秘 = 一张表 + 排序 ✅；③ **维度说错，修回**：不是"上下文 vs 外部知识"——两者最终都注入**同一个** context window、都是上下文工程；真正的分界是**来源与生命周期**：窗口/摘要管"**这场对话自己产生的文本**"（随轮次膨胀，第 6/7 课的账），RAG 管"**对话开始之前就存在的外部资料**"（再大也不占对话历史的账，每次只借相关的几页）。一句话：**一个管"我们刚说了什么"，一个管"世界本来是什么"。**
  - **一个超出本课要求的观察（用户自己答出）**：检索到的原文落在 `tool_result`（工作层，用完即弃），**没进记录层**；追问时上一轮"答案文本"还在 messages 里，所以 600 这个数它记得——**断的是"原文精度"**（C02 里那句"二线 400"上一轮它没说，追问就得重新检索）。
  - **收束自释逐空判卷（2026-09-10）**：**修回 5 处，其中 4 处同型**——都是"某个词到底指谁 / 往哪个方向"没落地（比第 7 课松：上次核心全对、修回 3 处）。**①** "真正答话的还是那个**原文**" ❌ → 是**模型**（原文是材料、不会说话；这正是本课要破的神话）；"RAG 改的是这次**消息来源**" → 是**这次请求喂进去的内容（输入/prompt）**。**②** 五步的第 4 步丢内涵 → 必须背到"**提问时把「问题」也 embed 成向量**再比余弦取 top-k"（这条正是"查询向量与索引向量必须同一 embed 模型"的由来）。**③** 铁律填成"向量只在**空间**里可比"（等于没说）→ **只在同一个 embed 模型内可比**。**⑤** "贵 + **上下文吸引注意力**" ❌ 方向反 → **噪音灌入 + 稀释（摊薄）注意力**；"贵"与 context rot 两处对。**⑥** "连**数据**都敢编" → 本课决定性证据是**连引用都敢编**（假引手册里不存在的条款——最权威的假象最危险）。**答对的两处**：④ "向量库 = 一张表 + 排序（生产库优化快/持久/亿级）"一字不差；"检索质量决定 RAG 上限"题眼命中。**超预期一处**：⑥ 后半填"靠**软说明 + cosine 下限**兜底"——正是用户当天亲手在 0001 做出来的两样（system 软章程 + `MIN_SCORE=0.6`）；补一句：两者仍是工程手段，硬防线是 **eval + 输出校验**（下一课主线）。**教学动作**：对着三句自问"**答话的是谁？比相似度的前提是什么？注意力是被吸引还是被摊薄？**"

### ⑤ 工程陷阱与面试追问
- 面试题「RAG 是什么？」→ 第一句先破神化：**两段式 + 五步，模型没换**；真正答话的还是同一个对话模型，RAG 改的是"这次喂了什么"。
- 面试题「为什么不全塞进上下文？」→ token 涨 + 噪音稀释注意力（context rot）；**并且主动补一句官方口径**：资料很小（<20 万 token）时配缓存直接全塞可能更划算，别为上 RAG 而上 RAG——主动说这层比背"省 token"高一档。
- 陷阱① "以为向量库是神秘高深组件" → 最小实现就是 (文本,向量) 表 + 余弦 top-k。
- 陷阱② **跨 embed 模型互算相似度** → 禁止；同一模型内才可比（面试常考）。
- 陷阱③ "以为 embedding 什么都能捞对" → 换说法得换在**同一语义邻域**；需要推理 / 反问 / 跨多块的题纯检索救不了（往后的 eval 与高级检索的入口）。
- 陷阱④ "以为提示词写了'不要编'就安全" → 那是**软**边界；**检索=空时模型会连引用一起编**。硬防 = 分数下限 / eval / 输出校验。
- 陷阱⑤ **阈值量纲混用**：拿关键词路的 0.15 当余弦下限 → 永不触发；反之拿余弦的经验值当字面重合下限 → 全部误杀。**每路按自己的分布标定**。
- 陷阱⑥ 答错先查**检索给对没有**（打印 top-k 的 chunk_id + 分数），别一上来赖模型笨。

### ⑥ 术语·厂商对照·原典
- 术语：RAG / retrieval / augmented generation / embedding / vector / cosine similarity / top-k / chunking / vector store / rerank / context rot / query rewriting / BM25 / ground truth
- 厂商对照：**embedding 这一环天生跨厂商**——DeepSeek 官方 API 无 embeddings 端点（2026 实测，`api.deepseek.com/embeddings` 404），Anthropic 官方也不提供（官方推荐 Voyage 等伙伴模型 / 自托管），OpenAI 有 `text-embedding-3-small/large`。所以 RAG 本来就是"对话 LLM + embedding 服务"两家组装，不是某家的坑；本课本地 **bge-small-zh-v1.5（512 维，ONNX CPU）≈ OpenAI text-embedding-3-small 的"角色"**，且 ¥0、离线、可复现。top-k 概念跨所有向量库一致。
- 原典（必读）：Anthropic **Effective context engineering for AI agents**（精读 **read selective**——本课检索注入就是它）；Anthropic **Introducing Contextual Retrieval**（给每块加"上下文前缀"再向量化可把检索失败率降近一半；embedding 会漏精确串如错误码 → 需与 **BM25 双轨合流**；镜 2 的"关键词 2-gram 对照"正是 BM25 这一档的最小代表）；OpenAI **Text embeddings** 官方文档（embedding = 语义向量这一概念的出处）。延伸：Building Effective Agents 的"检索增强"，挑战 A 正是把 RAG 包成 agent 的一把工具。

---

*本文件已积累：第 1 课（M1）✅ ｜ 第 2 课（M2）✅ ｜ 第 3 课（M2）✅ ｜ 第 4 课（M2）✅ ｜ 第 5 课（M2）✅ ｜ 第 6 课（M2 收官）✅（2026-09-07 成本实证 + 用户挑战 A/B 完成回填）｜ 第 7 课（M3）✅（2026-09-08 实证回填：三镜 + 挑战 A/B + 收束自释判卷）｜ 第 8 课（M3）✅（2026-09-10 实证回填：三镜 + 挑战 A/B + 分数下限实验 + 收束判卷）。M2 工程地基六块、M3 前两课收官，完成新课请按顶部模板追加一节。*
