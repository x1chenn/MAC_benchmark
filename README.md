# MAC_benchmark

A multi-agent coordination benchmark on daily service scenarios: flight ticketing, online shopping and auto-insurance claims. **Status: design stage, no code yet.** The design documents are in Chinese.

日常服务场景下的多智能体协作基准，覆盖订票、购物、车险理赔三个场景。目前是设计阶段，还没有代码。仓库名是工作名，正式名称待定。

## 设计要点

- 任务按 [Harbor](https://github.com/harbor-framework/harbor) 的任务目录格式打包，任何 Harbor 支持的 agent 都能一条命令运行。
- 环境提供两样东西：一个模拟真实平台的领域服务（REST 加 MCP），一个消息板。通用工具由 agent 的 harness 自带。
- 真值在世界状态里。订票、下单、结案都通过接口落库，验证器只读终态和事件日志，用程序判分。
- 每个角色是一个席位，可以由被测 agent、冻结的对手模型、脚本或参考解控制。

```
6 发布层   数据集划分 · 版本 · 注册表 · 榜单
5 评估层   验证器 → reward.json · 分析器
4 运行层   席位 · 控制器 · harness 适配 · 编排 · 轨迹
3 接口层   REST+OpenAPI · MCP · CLI · 消息板
2 领域包   ticketing │ shopping │ insurance
1 世界内核 状态存储 · 逻辑时钟 · 事件队列 · 身份与权限 · 事件日志
```

## 文档

| 文件 | 内容 |
|---|---|
| [docs/DESIGN.md](docs/DESIGN.md) | 顶层设计：分层、契约、Agent / Task / Evaluation 三个模块、验收标准、数据划分、实现顺序 |
| [docs/SCENARIOS.md](docs/SCENARIOS.md) | 三个场景：已有工作、世界模型、规则出处、接口、事件、任务族、真值算法 |
| [docs/APPENDIX_tools.md](docs/APPENDIX_tools.md) | agent 工具调研：7 个 harness 和 6 类服务型基准 |
| [docs/page/](docs/page/) | 把以上三份文件生成一个带架构图的单页：`python docs/page/build_page.py` |
