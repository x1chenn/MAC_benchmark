# 日常场景多智能体协作基准：顶层设计 v0

日期：2026-11-23。状态：设计稿，尚无代码。仓库名 MAC_benchmark 是工作名：已有两个基准叫 MAC Bench 或 MAC-Bench，正式名称需要避开。
配套文件：[SCENARIOS.md](SCENARIOS.md)（三个场景的调研与任务设计），[APPENDIX_tools.md](APPENDIX_tools.md)（agent 工具调研的原始表）。

## 0. 一页结论

1. **打包格式直接用 Harbor 的任务目录。** Harbor 是 Terminal-Bench 现在的运行框架，预集成了 40 多个 agent，其中包括 `muse-code`。任务按它的格式打包，Claude Code、Codex、Gemini CLI、Muse Code 都是一条命令接入。
2. **通用工具不由我们提供。** Harbor 的立场是工具属于 agent，环境要提供能力就用 MCP、API、CLI 或 skills。bash、读写文件由各家 harness 自带。我们提供的是两样东西：一个模拟真实平台的服务（REST 加 MCP），一个消息板。
3. **真值在世界状态里，不在对话里。** 订票、下单、理赔结案都必须通过服务接口落到数据库。验证器只读最终状态和事件日志，用程序判分。
4. **六层解耦，层间只靠七个文件契约通信。** 世界内核、领域包、接口层、运行层、评估层、发布层。换场景只动领域包，换模型只动运行层，换指标只动评估层。
5. **席位模型统一了"谁被测"。** 每个角色是一个席位，席位由被测 agent、冻结的对手模型、脚本策略或参考解之一控制。同一个任务既能当单 agent 的训练环境，也能当多 agent 的团队评测。
6. **三个场景恰好覆盖合作到对立的光谱。** 订票偏合作，购物是混合动机，理赔偏对立但有法规给出的可计算真值。

## 1. 目标与约束

| 目标 | 含义 | 由谁保证 |
|---|---|---|
| 即插即用 | 任何 Harbor 支持的 agent 一条命令跑一个任务 | Harbor 任务格式，MCP |
| 程序化真值 | 分数由确定性代码从状态和日志算出 | 规则引擎，求解器，验证器 |
| 足够真 | 数据结构和规则对照真实平台与法规，每条规则有出处 | 领域包，规则出处表 |
| 可规模化 | 生成器按种子产出任意多实例，训练集和测试集分离 | 生成器，划分方案 |
| 解耦 | 各模块可独立替换和测试 | 分层与契约 |

两个使用方式必须同时支持，模型训练和基准评测：
- **训练**：大量实例，带奖励的完整轨迹。
- **评测**：固定的留出测试集，可复现，防作弊。

## 2. 三个参考实现各给我们什么

| 参考 | 我们直接复用 | 我们借鉴做法 | 它没有而我们要补的 |
|---|---|---|---|
| Harbor / Terminal-Bench | 任务目录格式，沙箱，预集成 agent，独立验证器沙箱，`harbor lint`，ATIF 轨迹格式，MCP 声明，网络白名单 | 验收三条：说明完备、可解、不可作弊；每个任务带参考解；对抗性作弊 agent 检查 | 原生只有一个 agent（加一个模拟用户）；没有领域世界 |
| Bespoke multi-agent harness（Apache-2.0） | hub 加 N 个 agent 沙箱的团队环境，消息板（`send`/`inbox`/`history`），按角色下发工具的插件机制，模型代理和预算上限 | 关掉 CLI 自带的子代理，否则消息会绕过消息板 | 任务都是同目标的副本团队；没有私有信息不同、目标不同的角色；只接了 Codex、Claude Code、Antigravity |
| tau2-bench | 无代码复用 | 领域的内部结构：数据模型、工具、策略文档、任务、数据库终态评估；用户侧也有工具的双控设计；重复 k 次都通过的可靠性指标 | 只有一个 agent 对一个模拟用户；真值是唯一的数据库终态，不适合有多个可行解的协商 |

来源见文末。Harbor 文档原话：*"Harbor considers tools to be a component of the agent, not the environment. If the environment does provide tools, it should do so in the form of MCPs, skills, APIs, or CLIs."*

## 3. 顶层架构

### 3.1 六层

```
┌───────────────────────────────────────────────────────────────────┐
│ 6 发布层   数据集划分 · 版本 · 注册表 · 榜单                        │
├───────────────────────────────────────────────────────────────────┤
│ 5 评估层   验证器 → reward.json · 分析器 → 行为与协作报告            │
├───────────────────────────────────────────────────────────────────┤
│ 4 运行层   席位 · 控制器 · harness 适配 · 编排 · 轨迹                │
├───────────────────────────────────────────────────────────────────┤
│ 3 接口层   REST+OpenAPI · MCP · CLI      │   消息板                 │
├───────────────────────────────────────────────────────────────────┤
│ 2 领域包   ticketing │ shopping │ insurance                        │
│            数据模型 · 规则 · 事件 · 生成器 · 求解器 · 策略文档        │
├───────────────────────────────────────────────────────────────────┤
│ 1 世界内核 状态存储 · 逻辑时钟 · 事件队列 · 身份与权限 · 事件日志     │
└───────────────────────────────────────────────────────────────────┘
```

依赖规则：每层只依赖下面的层。评估层只读文件，不调用 agent，也不调用运行中的世界。

和你说的三个模块的对应关系：

| 你的模块 | 对应的层 | 说明 |
|---|---|---|
| Agent | 3 接口层，4 运行层 | 工具面、席位、harness 适配、轨迹 |
| Task | 1 世界内核，2 领域包，再加任务规格 | 你说的"sandbox 环境"就是内核加领域包 |
| Evaluation metric | 5 评估层 | 只消费状态、日志、求解器输出 |

### 3.2 四个核心概念

- **World**：状态、规则、时钟。状态只能被某个身份提交的动作改变。每个动作先过规则校验，再原子生效，再写入事件日志。世界里没有 LLM。
- **Seat（席位）**：场景里的一个角色，加上控制它的东西。控制器有五种：`agent`（被测的 LLM harness），`panel`（冻结的对手模型加人设），`script`（确定性策略），`oracle`（参考解），`human`。
- **Scenario（场景实例）**：世界种子，各角色的角色卡，外生事件表，终止条件，预算。
- **Verifier（验证器）**：函数，输入是最终状态、事件日志、场景实例、求解器输出，输出是 `reward.json`。

### 3.3 七个契约

模块之间只通过下面七种文件或接口通信。只要契约不变，任何一侧都可以重写。

| 契约 | 生产方 → 消费方 | 形式 |
|---|---|---|
| 世界 API | 领域包 → 接口层 | OpenAPI 规格；每个请求带角色令牌，服务端按角色鉴权 |
| 工具清单 | 接口层 → agent | 由 OpenAPI 自动生成的 MCP 工具表和 CLI |
| 消息格式 | 消息板 → 席位 | `{seq, from, to, text, ts, refs}` |
| 角色卡 | 场景 → 席位 | `card.md`（公开说明、私有信息、计分规则）加 `card.json`（机器可读的效用参数） |
| 事件日志 | 世界和消息板 → 验证器 | 只追加的 JSONL，记录动作、外生事件、消息、时钟推进 |
| 轨迹 | 席位 → 数据集 | 每个席位一份 ATIF JSON |
| 奖励 | 验证器 → Harbor | `reward.json`，带标签的多个数值 |

另有一个内部契约：求解器输出 `truth.json`（最优值、帕累托集合、参考动作序列），只进验证器镜像，永远不进 agent 容器。

### 3.4 一次试验的容器拓扑

```
一次 trial
 ├─ world      领域服务：REST、MCP、数据库、时钟、规则。无 LLM
 ├─ board      消息板（v1 可与 world 同进程）
 ├─ seat-1 … seat-N   每个席位一个容器；只装自己的角色卡和令牌
 └─ verifier   独立沙箱；trial 结束后拿到世界快照和事件日志
```

- **隔离私有信息**：角色卡只存在于对应席位的容器。令牌按角色签发，世界服务按令牌决定能看什么、能做什么。旅客甲读不到旅客乙的预算，保险公司甲读不到保险公司乙的案卷。
- **令牌怎么传**：Harbor 里带凭证的 MCP 请求头目前只有 Claude Code、Codex、opencode-v2 支持。所以焦点模式不依赖请求头：world 对 `main` 容器只暴露焦点角色的端点，其余席位的控制器走 sidecar 内部的接口。团队模式下每个 agent 用自己的 Bearer 令牌，这是 Bespoke harness 的现成做法。
- **网络**：席位只能访问 world、board 和模型推理地址。没有公网。"搜索"是世界内部的接口，比如航班搜索、商品搜索、条款检索。
- **作弊面**：数据库在 world 容器里，agent 的 bash 碰不到；`truth.json` 只在验证器镜像里。

### 3.5 两种运行模式，同一份任务

| | 焦点模式 | 团队模式 |
|---|---|---|
| 被测 | 一个席位 | 所有席位，或指定的若干席位 |
| 其余席位 | `script` 或 `panel` | 无，或混入 `panel` |
| 实现 | 原生 Harbor：被测席位是 `main` 容器，其余席位的控制器跑在一个 sidecar 里 | Bespoke 团队环境：hub 加 N 个 agent 沙箱，写一个带角色的编排策略 |
| 分数 | 该席位的个体分，加联合指标 | 联合指标，加每席位个体分 |
| 用途 | 训练环境；榜单；换对手测稳健性 | 团队协作评测；自博弈数据 |
| 接入成本 | 任何 Harbor 预集成 agent 零改动 | 团队 harness 目前只接了 Codex、Claude Code、Antigravity，其余 agent 要自己适配 |

建议先做焦点模式。理由有三条：任何 Harbor 预集成 agent 都是零成本接入；对手可控，所以结果可复现；它和 tau-bench 的"agent 对模拟用户"是同一形态，而 tau-bench 是被 10 家实验室采用的形态。

### 3.6 逻辑时钟

真实等待不可复现，所以世界用逻辑时间。
- 每个动作不消耗时间，或消耗规则指定的时间。
- 当所有还在运行的席位都阻塞在 `inbox(wait)` 上时，内核把时钟跳到下一个预定事件，触发它，再唤醒相关席位。
- 没有事件可触发且所有席位都空闲或已结束时，试验结束。墙上时钟只作为安全超时。
- 外生事件有两种触发方式：到达某个逻辑时刻，或某个状态谓词成立（例如"两人都已出票之后，宣布航班延误"）。

v1 可以只实现谓词触发，接口按完整的离散事件时钟来留。

## 4. Agent 模块

### 4.1 调研结论

对 7 个 harness 和 6 类服务型基准的工具做了核对，原始表在 [APPENDIX_tools.md](APPENDIX_tools.md)。

| 发现 | 证据 |
|---|---|
| shell 是唯一所有 harness 都有的工具 | 7 个里 7 个有；mini-SWE-agent 和 Terminus 2 只有 shell |
| 内置工具在变少 | 新版 Claude Code 在 Linux 上默认去掉了专用的搜索工具，在新模型上默认不给任务清单工具 |
| 服务型基准把领域接口做成带类型的函数 | tau-bench 航空 14 个，零售 16 个；AgentDojo 旅行 28 个；每域 11 到 28 个 |
| agent 间通信都是"发消息加收件箱" | Bespoke `send`/`inbox`/`history`；Magentic Marketplace `SendMessage`/`FetchMessages`；Claude Code `SendMessage` |
| 结构化报价是消息的一种类型 | Magentic Marketplace 的消息分 `TextMessage`、`OrderProposal`、`Payment` 三种 |

### 4.2 工具面

分三组，只有后两组由我们实现。

| 组 | 工具 | 谁提供 | 数量 |
|---|---|---|---|
| 通用 | `shell`，`read_file`，`write_file` | harness 自带；裸模型用我们的参考 agent | 3 |
| 通信 | `send_message(to, text)`，`inbox(wait_seconds)`，`history(after)` | 消息板，MCP 加 REST | 3 |
| 控制 | `finish(summary)` | 消息板 | 1 |
| 领域 | 按角色下发，例如 `search_flights`、`hold_offer`、`confirm_booking` | 世界服务，MCP 加 REST | 每角色 8 到 15 |

所以你说的"5 到 10 个工具"落在固定的 7 个上，领域工具另算，并且每个角色看到的领域工具不同。

明确不给的两样：
- **联网搜索和抓取**：沙箱断网。Harbor 可以关掉 agent 自带的 web 工具。
- **自带的子代理**：Bespoke 首次试跑时，领队用了 Codex 内置的子代理，消息没有经过消息板。团队模式下必须关掉。

领域动作有两个通道，对应两类 agent：
- **MCP**：在 `task.toml` 里声明 `[[environment.mcp_servers]]`，Harbor 自动注册给支持 MCP 的 agent。
- **REST 加 CLI**：只有 bash 的 agent 用 `curl` 或我们给的命令行工具。两个通道后面是同一个服务、同一套鉴权。

结构化承诺走领域接口，不走自由文本。例如商家的报价必须调用 `propose_order` 才算数，口头说的价格不算。这样验证器不需要理解自然语言就能判定成交内容。

### 4.3 席位与控制器

```
Seat = { role, controller, model?, harness?, persona? }
controller ∈ { agent, panel, script, oracle, human }
```

- `script` 是确定性的，用于官方测试集的对手，保证可复现。
- `panel` 是冻结版本的模型加人设，用于稳健性测试：同一个被测 agent 对一组不同对手。
- `oracle` 是每个任务必须自带的参考解，等价于 Terminal-Bench 的 `solution/solve.sh`。所有席位都用 `oracle` 时必须拿满分。

### 4.4 接入 SOTA 模型的两条路

| 模型形态 | 接法 |
|---|---|
| 有自己的 CLI harness（Claude Code，Codex，Gemini CLI，Muse Code） | Harbor 预集成 agent，`harbor run -a <agent> -m <model> -p <task>` |
| 只有 API | 我们的参考 agent：一个最小循环，带上表的 7 个固定工具，领域工具从 MCP 读取 |

参考 agent 要尽量薄。Terminal-Bench 的参考 agent Terminus 2 只有一个 tmux 会话，目的就是让分数反映模型而不是脚手架。

各 agent 对 MCP 的支持并不一致，这是一个待实测项。例如 Codex 要求 `streamable-http`；Harbor 里 Muse Code 的集成源码 `src/harbor/agents/installed/muse_code.py` 支持 `streamable-http` 和 `stdio`，遇到 `sse` 会报错，而文档的能力表里 MCP 一栏还没有列出它。所以两条约束：我们的 MCP 服务器一律用 `streamable-http`；M0 阶段对每个要支持的 agent 实际跑一次，确认工具确实注册成功。

### 4.5 轨迹

每个席位输出一份 ATIF 轨迹（Harbor 的统一格式，记录消息、推理、工具调用、观察、用量）。一次试验的完整数据包：

```
episode/
  scenario.json          场景实例
  seats/<role>/trajectory.json
  events.jsonl           世界和消息板的全局事件日志
  final_state.json       世界终态
  reward.json            验证器输出
```

这个数据包就是一个训练单元。

## 5. Task 模块

三个场景的世界模型、角色、接口、事件、任务族、真值算法在 [SCENARIOS.md](SCENARIOS.md)。这里只定结构。

### 5.1 领域包的目录

```
domains/<name>/
  schema.py      实体（pydantic）
  rules.py       规则即代码：前置条件校验，费用、退款、赔付的计算
  service.py     REST 端点，按角色分组
  tools.yaml     角色 → 工具表；MCP 清单由它生成
  events.py      外生事件类型及其对状态的影响
  generator.py   种子和难度旋钮 → world.json 和 scenario.json
  solver.py      真值：最优值、帕累托集合、参考动作序列
  policies/      发给 agent 的条款文档
  personas/      脚本对手和 panel 对手的定义
  RULES.md       规则出处表：每条规则对应哪条真实法规或平台条款
  tests/         规则单测；求解器对暴力枚举；不变量
```

### 5.2 任务实例的目录（Harbor 格式，由导出脚本生成）

```
tasks/<domain>/<task-id>/
  task.toml                    元数据，超时，资源，MCP 声明，网络白名单
  instruction.md               焦点席位的任务说明
  environment/
    docker-compose.yaml        world，board，counterparts
    world/world.json           初始世界
    world/scenario.json        席位，事件表，终止条件
  roles/<role>/card.md         每个角色的角色卡
  solution/solve.sh            参考解：驱动 oracle 控制器
  tests/
    Dockerfile                 独立验证器镜像
    test.sh                    运行 verify.py，写 reward.json
    truth.json                 求解器输出，只在此镜像内
```

### 5.3 三类真值

"环境能给出真值解"在多方交互里有三种不同含义，每个场景侧重不同。

| 真值类型 | 含义 | 谁计算 | 订票 | 购物 | 理赔 |
|---|---|---|---|---|---|
| 规则真值 | 某个动作是否允许，应收应付多少 | 规则引擎 | 主 | 辅 | 主 |
| 最优真值 | 给定世界，某席位或全体能达到的最好结果 | 求解器 | 主 | 主 | 辅 |
| 事实真值 | 世界里隐藏的真实情况，对照各方的声称 | 生成器 | 辅 | 主 | 主 |

### 5.4 角色卡必须写明计分规则

Terminal-Bench 的验收第一条是说明完备：凡是被评分的要求都必须写在说明里。对我们意味着偏好不能只用形容词。角色卡要给出可计算的效用，例如：

> 预算上限 420 美元。必须在周五 18:00 前到达。每多一次中转扣 30 分。两人邻座加 40 分。总花费每省 1 美元加 1 分。

这样求解器和 agent 面对的是同一个目标，分数才有意义。

### 5.5 跨场景共用的难度轴

三个场景用同一组旋钮描述任务，结果才能横向比较。

| 轴 | 取值 |
|---|---|
| 利益结构 | 一致，混合，对立 |
| 信息 | 对称，私有信息不同，证据分散在各方 |
| 稀缺 | 无，资源只够一方 |
| 外生事件 | 无，中途发生（延误、缺货、新证据） |
| 规则压力 | 无，有人要求做规则不允许的事 |
| 对手类型 | 脚本，panel 人设，同模型自博弈 |

## 6. Evaluation 模块

### 6.1 四层指标

| 层 | 问题 | 例子 | 计算方式 |
|---|---|---|---|
| 0 有效性 | 试验是否合规完成 | 无违规动作，无超权限调用，在预算内结束 | 程序 |
| 1 结果 | 目标达成了多少 | 成功与否；归一化效用；联合效率；公平性；结算误差 | 程序，对照 `truth.json` |
| 2 协作过程 | 怎么达成的 | 消息数；重复或冲突的动作；关键私有信息在提交前是否被传达；事件后的恢复用时；不可逆动作前是否取得同意 | 程序，读事件日志 |
| 3 行为 | 表现出什么倾向 | 陈述与自己私有事实不符的比例；让步模式；对违规请求的顺从 | 能结构化的用程序，其余用带量表的评审模型，先验证再上榜 |

### 6.2 头条数字

- `success`：0 或 1。第 0 层通过，且硬目标全部满足。
- `score`：0 到 1。`(u − u_0) / (u* − u_0)`，其中 `u_0` 是什么都不做的结果，`u*` 是求解器最优。
- `pass^k`：同一任务跑 k 次全部成功的比例，沿用 tau-bench。
- 混合动机任务另报：联合效率（实现的总剩余占最大总剩余的比例），以及个体分。

第 3 层只报告，不进头条，直到评审模型和人工标注的一致性达标。

### 6.3 `reward.json` 示例

```json
{
  "success": 1,
  "score": 0.82,
  "valid": 1,
  "policy_violations": 0,
  "joint_efficiency": 0.91,
  "fairness_gap": 0.07,
  "messages": 14,
  "redundant_actions": 2,
  "private_facts_shared": 0.75,
  "recovery_steps": 6
}
```

## 7. 验收标准

对照 Terminal-Bench 的做法，每个任务入库前要过下面的检查。前七条可以全自动。

| # | 检查 | 通过条件 |
|---|---|---|
| 1 | 可解 | 所有席位用 `oracle` 时 `success = 1` |
| 2 | 无白给分 | 空 agent 和随机 agent 的 `success = 0` |
| 3 | 确定性 | 按事件日志重放，终态哈希一致 |
| 4 | 求解器正确 | 小规模实例上与暴力枚举一致 |
| 5 | 静态检查 | `harbor lint` 无告警；镜像和依赖钉版本 |
| 6 | 隔离 | 作弊 agent 试图读他人令牌、调他人接口、找 `truth.json`，全部失败 |
| 7 | 独立验证器 | 验证在单独沙箱里进行 |
| 8 | 说明完备 | 评分用到的每个量都能在角色卡或条款文档里找到；人工或模型按清单审 |
| 9 | 规则有出处 | `RULES.md` 里每条规则对应真实法规或平台条款 |
| 10 | 对手敏感性 | 同一任务换 k 个对手的分数分布随任务一起发布 |
| 11 | 防污染 | 每个文件带 canary 字符串；测试集的种子和模板不公开 |

## 8. 数据与划分

| 划分 | 内容 | 是否公开 |
|---|---|---|
| train | 大量种子，全部公开的任务族 | 公开 |
| dev | 少量种子，同分布 | 公开 |
| test-seed | 留出的种子，任务族与 train 相同 | 任务公开，`truth.json` 不公开 |
| test-family | 留出的任务族，例如某一类外生事件从不在 train 里出现 | 不公开 |
| test-world | 留出的世界，例如另一组机场和航司、另一套州法规 | 不公开 |

三个测试划分分别回答三个问题：记住了没有，学到的是这一类事件还是协作本身，换一个世界还行不行。

## 9. 实现顺序

| 阶段 | 内容 | 完成的标志 |
|---|---|---|
| M0 | 内核，消息板，参考 agent，一个玩具领域 | 玩具任务在 Harbor 里用 `oracle` 和至少两个真实 agent 各跑通一次 |
| M1 | 订票领域：数据模型，规则，生成器，求解器，一个任务族，脚本旅客 | 第 7 节的 1 到 7 条全自动通过 |
| M2 | 订票补全任务族；质量流水线；首批基线 | 约 50 个测试任务，三个以上模型的结果 |
| M3 | 购物领域 | 同 M1、M2 的标志 |
| M4 | 理赔领域 | 同上 |
| M5 | 团队模式，panel 对手 | 同一任务在两种模式下都能跑 |
| M6 | 数据发布，论文 | train 和 test 划分，榜单 |

先把一个领域纵向做穿，再横向铺开。内核和契约的问题只有在一个完整任务跑通时才会暴露。

## 10. 需要你定的事

1. **主模式**：建议焦点模式先行，团队模式放在 M5。
2. **订票里谁是被测席位**：订票 agent，还是代表旅客的助理 agent。两者训练的是不同能力，前者是服务方，后者是个人助理。建议两个都支持，官方测试集先以订票 agent 为焦点。
3. **官方测试集的对手**：建议用脚本对手保证可复现，panel 对手作为稳健性附表。
4. **法规管辖**：建议订票用美国交通部规则，欧盟 261 作为可选规则集；理赔用加州规则，过失制度做成开关，之后加得州和马里兰。中国规则可以作为单独的领域包，要不要做由你定。
5. **是否在 Bespoke 的 harness 上做团队模式**：它省掉沙箱编排、消息板、模型代理三块工作，代价是依赖它钉死的 Harbor 版本，并要自己适配它尚未支持的 agent。
6. **项目名**。

## 来源

- [Harbor 仓库](https://github.com/harbor-framework/harbor)，文档目录 `docs-mintlify/`：任务总览、`task.toml` 字段、多容器、验证器、独立验证器、模拟用户、ATIF、预集成 agent、reward hacking 一文
- [Terminal-Bench 论文](https://arxiv.org/abs/2601.11868)
- [Bespoke multi-agent-coordination-bench](https://github.com/bespokelabsai/multi-agent-coordination-bench)，`harness/docs/architecture.md`，`harness/docs/board.md`
- [tau2-bench 仓库](https://github.com/sierra-research/tau2-bench)，`src/tau2/domains/README.md`
- [Magentic Marketplace 协议](https://github.com/microsoft/multi-agent-marketplace/blob/main/docs/concepts/marketplace-protocol.md)
