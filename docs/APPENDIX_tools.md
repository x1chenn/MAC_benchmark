# 附录：agent 工具调研

日期：2026-11-23。工具名取自官方文档或仓库源码。标"未核实"的条目没有在一手来源读到原文。
主文档：[DESIGN.md](DESIGN.md) 第 4 节。

## 1. Harness 内置工具

| Harness | 主要工具（原名） | MCP | 来源 |
|---|---|---|---|
| Claude Code | `Bash`；`Read`/`Edit`/`Write`；`Glob`/`Grep`（Linux、macOS 默认缺席，改走 `Bash`）；`WebFetch`/`WebSearch`；`Agent`（子代理）；`SendMessage`；任务清单类工具只在较早的模型上默认提供；`AskUserQuestion`；`Skill` | 支持 | https://code.claude.com/docs/en/tools-reference |
| Codex CLI | `exec_command` 加 `write_stdin`；`apply_patch`；`update_plan`；`view_image`；`request_user_input`；托管的 web search；多代理 `spawn_agent`/`send_message`/`wait_agent` 等。没有独立的读文件或搜索工具 | 支持 | https://github.com/openai/codex/tree/main/codex-rs/core/src/tools/handlers |
| Gemini CLI | `run_shell_command`；`read_file`/`read_many_files`/`write_file`/`replace`；`glob`/`grep_search`/`list_directory`；`google_web_search`/`web_fetch`；`write_todos`；`ask_user`；`activate_skill`；`invoke_agent` | 支持 | https://github.com/google-gemini/gemini-cli/blob/main/docs/reference/tools.md |
| OpenHands CodeAct | `execute_bash`；`execute_ipython_cell`；`str_replace_editor`；`browser`；`think`；`finish`；`task_tracker` | 支持 | https://github.com/All-Hands-AI/OpenHands/tree/0.59.0/openhands/agenthub/codeact_agent/tools |
| mini-SWE-agent | 只有 bash，不走函数调用；结束靠输出一个哨兵字符串 | 无原生支持 | https://github.com/SWE-agent/mini-swe-agent |
| Terminus 2 | 无工具调用：输出 JSON，里面是送入 tmux 的按键和 `task_complete` | 只把服务器名和地址写进提示词 | https://github.com/harbor-framework/harbor/tree/main/src/harbor/agents/terminus_2 |
| Goose | `shell`/`write`/`edit`/`tree`；`todo_write`；`delegate`；可选的记忆和电脑控制扩展 | 原生（扩展即 MCP） | https://github.com/block/goose |

## 2. 频次表：是否默认有专用工具

| 类别 | Claude Code | Codex | Gemini CLI | OpenHands | mini-SWE | Terminus 2 | Goose | 合计 |
|---|---|---|---|---|---|---|---|---|
| shell | 有 | 有 | 有 | 有 | 有 | 有 | 有 | 7/7 |
| 写或改文件 | 有 | 有 | 有 | 有 | 无 | 无 | 有 | 5/7 |
| 子代理 | 有 | 有 | 有 | 有 | 无 | 无 | 有 | 5/7 |
| 计划或 todo | 可选 | 有 | 有 | 有 | 无 | 无 | 有 | 4/7 |
| 读文件 | 有 | 无 | 有 | 有 | 无 | 无 | 无 | 3/7 |
| web 搜索 | 有 | 有 | 有 | 无 | 无 | 无 | 无 | 3/7 |
| web 抓取或浏览器 | 有 | 无 | 有 | 有 | 无 | 无 | 可选 | 3/7 |
| 问用户 | 有 | 有 | 有 | 可选 | 无 | 无 | 无 | 3/7 |
| finish 或 submit | 无 | 无 | 仅子代理 | 有 | 有 | 有 | 无 | 3/7 |
| agent 间消息 | 有 | 有 | 无 | 无 | 无 | 无 | 无 | 2/7 |
| 代码搜索 | 可选 | 无 | 有 | 可选 | 无 | 无 | 可选 | 1/7 |
| 专用代码执行 | 无 | 可选 | 无 | 有 | 无 | 无 | 可选 | 1/7 |
| 记忆或笔记 | 无 | 无 | 有 | 无 | 无 | 无 | 可选 | 1/7 |
| 领域 API | 经 MCP | 经 MCP | 经 MCP | 经 MCP | 仅提示词 | 仅提示词 | 经 MCP | 内置 0/7 |

## 3. 服务型和日常任务基准的工具数

| 基准和域 | 工具数 | 说明 | 来源 |
|---|---|---|---|
| tau-bench 航空 | 14 | 11 个领域函数加 `calculate`、`think`、`transfer_to_human_agents` | https://github.com/sierra-research/tau-bench/tree/main/tau_bench/envs/airline/tools |
| tau-bench 零售 | 16 | 13 个领域函数加同样 3 个通用工具 | 同仓库 `envs/retail/tools` |
| tau2-bench 航空 | 14 | 6 读 6 写，新增 `get_flight_status`；`think` 已被注释掉 | https://github.com/sierra-research/tau2-bench/blob/main/src/tau2/domains/airline/tools.py |
| tau2-bench 电信，agent 侧 | 13 | 6 读 6 写加转人工 | 同仓库 `domains/telecom/tools.py` |
| tau2-bench 电信，用户侧 | 30 | 15 读 15 写，例如 `run_speed_test`、`toggle_airplane_mode`、`reboot_device` | 同仓库 `domains/telecom/user_tools.py` |
| AgentDojo | 银行 11，Slack 11，旅行 28，办公 24 | 旅行域没有订机票的工具，只有 `get_flight_information` | https://github.com/ethz-spylab/agentdojo/tree/main/src/agentdojo/default_suites/v1 |
| TravelPlanner | 8 | `FlightSearch`、`GoogleDistanceMatrix`、`AccommodationSearch`、`RestaurantSearch`、`AttractionSearch`、`CitySearch`、`NotebookWrite`、`Planner` | https://github.com/OSU-NLP-Group/TravelPlanner/blob/main/agents/prompts.py |
| MCP-Universe | 133 | 6 个域，11 个服务器，231 个任务 | https://arxiv.org/abs/2508.14704 |
| MCPMark | 未核实 | 5 个服务器：Notion、GitHub、Filesystem、Postgres、Playwright；127 个任务 | https://arxiv.org/abs/2509.24002 |

## 4. Agent 间通信的原语

| 系统 | 原语 | 要点 | 来源 |
|---|---|---|---|
| Bespoke multi-agent harness | `send(text, to)`，`inbox(wait_seconds, limit)`，`history(after, limit)` | 消息板是 hub 上的 MCP 服务器，每个 agent 用自己的令牌；有 REST 镜像和 CLI；`inbox` 长轮询最多 60 秒；每 agent 每秒 5 次的限流；插件可往同一个服务器加按角色可见的领域工具 | https://github.com/bespokelabsai/multi-agent-coordination-bench （`harness/docs/board.md`） |
| Magentic Marketplace | `Search`，`SendMessage`，`FetchMessages` | 消息三种类型：`TextMessage`、`OrderProposal`（含商品、总价、有效期）、`Payment` | https://github.com/microsoft/multi-agent-marketplace/blob/main/docs/concepts/marketplace-protocol.md |
| tau2-bench 双控 | 环境持有两套工具箱 | 按请求方把调用路由到 agent 工具箱或用户工具箱，两边操作同一个环境 | https://arxiv.org/abs/2506.07982 |
| Claude Code agent teams | `SendMessage`，共享任务清单 | 实验功能；消息写入邮箱文件；任务认领用文件锁 | https://code.claude.com/docs/en/agent-teams |
| Google A2A v1.0 | `SendMessage`，`GetTask`，`CancelTask` 等 | 对象是 AgentCard、Message、Task、Artifact；任务状态含 `INPUT_REQUIRED` | https://a2a-protocol.org/latest/specification/ |
| MARBLE | `new_communication_session(target_agent_id, message)` | 拓扑有星形、链、树、图 | https://github.com/MultiagentBench/MARBLE |
| CooperBench | `send_message` 加 Redis 收件箱 | 可选共享 git | https://arxiv.org/abs/2601.13295 |

## 5. Harbor 的相关能力

| 能力 | 说明 |
|---|---|
| 预集成 agent | 40 多个，含 `claude-code`、`codex`、`gemini-cli`、`muse-code`、`openhands`、`mini-swe-agent`、`terminus-2`、`oracle`、`nop` |
| 任务声明 MCP | `task.toml` 里写 `[[environment.mcp_servers]]`，支持 `stdio`、`sse`、`streamable-http`；带凭证的请求头只有 Claude Code、Codex、opencode-v2 支持；Muse Code 的集成源码不接受 `sse`；Codex 要求 `streamable-http` |
| 多容器 | `environment/docker-compose.yaml`；`main` 是保留给 agent 的容器，其余是 sidecar，按服务名访问 |
| 模拟用户 | 第二个 agent 扮演用户，经 ACP 桥接与被测 agent 对话；被测方目前支持 6 个 CLI |
| 独立验证器 | 新任务默认在单独沙箱里验证；agent 的产出通过 artifacts 传入 |
| 网络策略 | `no-network`、`allowlist`、`public`；可分 agent 阶段和验证阶段设置；可关闭 agent 自带的 web 工具 |
| 轨迹 | ATIF v1.8，JSON，记录消息、推理、工具调用、观察、用量 |
| 静态检查 | `harbor lint`：未钉版本的依赖、验证器与 agent 共享沙箱、agent 镜像里泄露了测试或参考解等 |

Bespoke 的团队 harness 是一个 Harbor 插件，启动命令形如：

```
harbor run -p <task> \
  -e multi_agent_harness:TeamEnvironment --ek n_agents=3 \
  -a multi_agent_harness:TeamAgent --ak harness=codex
```

它的编排策略类有 `roles(agents)` 和 `prompt(team, name, instruction)` 两个必填方法，所以给每个 agent 不同的角色和提示词是支持的。消息板插件可以用 `board.role(name)` 按角色决定工具可见性。

## 6. 未核实项

- Codex 哪些工具默认开启；托管 web search 的线上名称。
- Gemini CLI 记忆工具的确切名称。
- Goose 默认启用哪些扩展。
- MCPMark 每个服务器的工具数。
- Claude Code 的工具表随版本变化，以上是 2026-11-23 的版本。
