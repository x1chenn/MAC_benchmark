# 三个场景：调研与任务设计 v0

日期：2026-11-23。主文档：[DESIGN.md](DESIGN.md)。
标"未核实"的条目没有在一手来源读到原文，用之前要再查。

## 0. 总览

| | 订票 | 购物 | 理赔 |
|---|---|---|---|
| 席位 | 1 个订票 agent，2 个旅客 | 1 个买家，2 到 3 个商家 | 2 个车主，2 家保险公司 |
| 利益结构 | 偏合作，旅客之间有轻度冲突 | 混合动机 | 偏对立 |
| 主要真值 | 规则真值，最优真值 | 最优真值，事实真值 | 规则真值，事实真值 |
| 内核扮演 | 航司，支付，背景需求，扰动 | 平台，支付，承运商，仲裁 | 法规，警方报告，定损，仲裁 |
| 最接近的已有工作 | DialOp Mediation，GroupTravelBench，tau-bench 航空 | ACWorld，Magentic Marketplace，tau-bench 零售 | InsClaimBench；没有找到多方协商的先例 |

三个场景共用四个机制，都在世界内核里实现一次：
- **同意是结构化对象。** 扣款、结案这类不可逆动作必须附带当事人签发的授权，授权带金额上限和有效期。验证器由此可以程序化检查"是否先取得同意"。
- **期限靠逻辑时钟生效。** 报价过期、免费取消窗口、退货窗口、理赔时限都是时钟上的事件。
- **条款文档是任务的一部分。** 每个角色拿到与自己有关的条款，规则引擎执行的就是这些条款。
- **承诺走接口。** 报价、订单、和解方案都是接口里的对象，口头说的不算数。

---

## 1. 订票

### 1.1 已有工作与空白

| 基准 | 规模与角色 | 怎么验证 | 缺什么 |
|---|---|---|---|
| [tau-bench 航空](https://arxiv.org/abs/2406.12045) | 50 个任务；1 个客服 agent 对 1 个模拟用户；500 用户，300 航班，2,000 预订 | 数据库终态与唯一目标一致，且回复含必需信息 | 单用户；时间冻结；无座位图；无库存竞争 |
| [TravelPlanner](https://arxiv.org/abs/2402.01622) | 1,225 条查询；6 个搜索工具；约 383 万条航班记录 | 约束通过率 | 无预订，无库存；票价是合成的；团体没有个人偏好 |
| [GroupTravelBench](https://arxiv.org/abs/2605.25200) | 650 个任务；2 到 6 人；1 个规划 agent 对 N 个用户模拟器的群聊 | 规则指标加评审模型；计划有效率最高 12% | 没有可计算最优；用户是模拟器；只出一份计划，无交易状态 |
| [DialOp Mediation](https://arxiv.org/abs/2305.20076) | 助手分别与 2 位用户私聊订航班；每人 30 个候选航班和私有日历 | 奖励由票价、日程冲突、到达时间差组成，按最优和最差归一化 | 有最优解，但无库存、票规、扰动；用户没有自己的 agent |
| [AgentDojo 旅行](https://github.com/ethz-spylab/agentdojo) | 20 个用户任务 | 检查函数 | 没有订机票的工具 |

空白：没有找到"一个订票 agent 加两位各有 agent 的旅客，带真实票规和库存，有可计算真值"的基准。DialOp 有最优解但世界是玩具；GroupTravelBench 的数据是真的但没有最优解也没有交易。

### 1.2 角色

| 席位 | 知道什么 | 能做什么 | 不能做什么 |
|---|---|---|---|
| `ota_agent` | 平台政策；全部航班、库存、订单 | 搜索，确认价格，占座，出票，选座，加行李，改签，取消，拆单 | 不知道旅客的私有偏好；没有支付授权就扣不了款 |
| `traveler_a`，`traveler_b` | 自己的出发地、时间窗、预算、会员等级、支付方式、计分规则 | 只读搜索；签发支付授权；对航司改期选择接受、改签或取消 | 不能直接下单；看不到对方的角色卡 |
| 世界内核 | 一切 | 扮演航司、支付、其他乘客的背景需求、延误与取消 | |

两种焦点设置都支持：订票 agent 被测、旅客用脚本；或某个旅客的助理被测、其余用脚本。

### 1.3 世界模型：必须有的 14 项

对照 Expedia XAP、Amadeus Self-Service、Duffel 三套公开接口整理。

| # | 因素 | 真实系统里的对应 | v1 做法 |
|---|---|---|---|
| 1 | 机场：坐标，时区 | OurAirports，OpenFlights | 30 到 50 个美国机场，真实经纬度和 IANA 时区；时刻用当地时间，支持次日到达 |
| 2 | 航段与行程 | Duffel `segment`/`slice`；Expedia `Leg` 含 `FlightDistance`、`ConnectionTime` | 直飞和一次中转；中转须过最短衔接时间 |
| 3 | 票价产品 | Duffel `fare_brand_name`、`conditions`；Amadeus `brandedFare` | 三个品牌：basic，standard，flexible；一张固定的改退条款表 |
| 4 | 有限库存 | Amadeus `numberOfBookableSeats`（上限 9）；Expedia `SeatsLeft` | 按订座舱位计数；两位旅客和背景需求共享 |
| 5 | 座位图 | Amadeus SeatMap：`seatAvailabilityStatus`，按人定价 | 小网格；相邻关系；选座费 |
| 6 | 报价到订单的状态机 | 搜索得到带 `expires_at` 的 offer；确认价格可能失败；再下单 | 保留三个失败分支：报价过期，价格变动，售罄 |
| 7 | 占座与期限 | Duffel hold 订单：`payment_required_by`，`price_guarantee_expires_at` | 可占座；过期释放 |
| 8 | 订单是操作单位 | PNR；拆分 PNR 只允许 2 到 9 人的记录 | 一单或两单由 agent 决定；可拆单，拆单后重新计价 |
| 9 | 旅客身份 | Duffel `loyalty_programme_accounts` | 会员等级影响行李额和权益 |
| 10 | 支付与退款去向 | Duffel `refund_to`：原支付方式，代金券，航司 credit | 退款回付款人，不是乘机人 |
| 11 | 附加服务 | 行李，选座 | 首件和第二件托运行李费 |
| 12 | 时钟 | 订票时间相对起飞时间 | 逻辑时钟；各种窗口都按它算 |
| 13 | 扰动 | 航司发起的变更；延误；取消 | 按 BTS 统计校准概率；区分航司可控与不可控原因 |
| 14 | 私有效用 | 无 | 每位旅客一份计分规则，求解器和 agent 用同一份 |

物理量的算法：
- **距离**：由经纬度用大圆公式计算。
- **飞行时间**：在 BTS 准点数据上拟合"计划轮挡时间对距离"的线性关系，再加带种子的噪声。
- **地面距离**：同一都市区有多个机场时，给一张机场到市区的地面时间表。它在会合类任务里起作用：两人到不同机场，会合时间要加地面段。

可以放心简化的 5 项：税费明细和多币种；代码共享和联盟；完整的 ATPCO 票规文本；旅行证件和签证；机型级座位图和支付认证。

### 1.4 规则出处表

| 规则 | 数字 | 出处 |
|---|---|---|
| 24 小时规则 | 起飞前至少一周订的票，须允许 24 小时内免罚金取消或免付款保留 | [14 CFR 259.5(b)(4)](https://www.law.cornell.edu/cfr/text/14/259.5) |
| 显著变更可退款 | 国内提前出发或延后到达 3 小时及以上，国际 6 小时及以上；起降机场改变；经停增多；降舱 | [14 CFR 260.2](https://www.law.cornell.edu/cfr/text/14/260.2) |
| 退款时限 | 信用卡 7 个工作日，其他 20 个日历日 | 同上 |
| 欧盟 261 补偿 | 1,500 km 以内 250 欧元；1,500 到 3,500 km 为 400 欧元；3,500 km 以上 600 欧元；到达延误 3 小时及以上触发 | [欧盟旅客权利页](https://europa.eu/youreurope/citizens/travel/passenger-rights/air/index_en.htm) |
| 美国拒载补偿 | 替代航班晚到 1 小时内无补偿；国内晚 1 到 2 小时赔单程票价 200%，上限 1,075 美元；更久赔 400%，上限 2,150 美元 | [14 CFR 250.5](https://www.law.cornell.edu/cfr/text/14/250.5) |
| 票价品牌 | 以 Delta 为例：基础经济舱原则上不可改，取消得航司 credit 并扣 99 美元；标准舱免改退费；更高一档退回原支付方式 | [Delta 代理政策页](https://pro.delta.com/content/agency/cam/en/products-and-services/other-programs-services/basic-economy.html)，经搜索摘要读到，用前再核对 |
| 托运行李 | Delta 国内首件 45 美元，第二件 55 美元；高等级会员首件免费 | [Delta 行李页](https://www.delta.com/us/en/baggage/overview) |
| 最短衔接时间 | 按国内转国内等四类设定；例如亚特兰大国内 35 分钟 | [OAG](https://www.oag.com/minimum-connection-times) |
| 单票与分开出票 | 同一张票误接由航司免费改签；分开出票时航司无义务 | 行业惯例，二手来源 |
| 代码共享披露 | 须披露实际承运人 | [14 CFR 257.5](https://www.law.cornell.edu/cfr/text/14/257.5) |

准点统计用于校准扰动：2024 年美国到达准点率 78.1%，取消率 1.4%（[DOT 公告](https://content.govdelivery.com/accounts/USDOT/bulletins/3d6f0ea)）。延误原因的分项占比见 [BTS 延误原因表](https://www.transtats.bts.gov/ot_delay/ot_delaycause1.asp)。

### 1.5 数据来源与许可

| 数据 | 用途 | 许可 |
|---|---|---|
| [OurAirports](https://github.com/davidmegginson/ourairports-data) | 机场坐标 | 公有领域 |
| [OpenFlights](https://openflights.org/data.php) | 时区；历史航线网络（止于 2014 年） | ODbL |
| [BTS On-Time Performance](https://www.transtats.bts.gov/Fields.asp?gnoyr_VQ=FGJ) | 时刻结构，延误和取消的分布 | 美国政府数据，许可声明未核实 |
| DOT DB1B | 票价水平对距离的关系 | 同上 |
| Kaggle `dilwong/flightprices` | Expedia 报价的字段和价格分布 | 未核实；只用于拟合分布，不分发 |

世界是合成的，只有机场坐标和统计分布来自真实数据。这样既可再分发，也不会被模型从记忆里背出来。

### 1.6 接口

命名对照 Duffel 和 Amadeus。订票 agent 约 15 个，旅客约 7 个。

| 订票 agent | 说明 |
|---|---|
| `search_flights(origin, destination, date, passengers)` | 返回 offers，每个带 `expires_at` 和剩余座位数 |
| `price_offer(offer_id)` | 确认价格；可能返回价格变动或售罄 |
| `get_fare_rules(offer_id)` | 改退条款，行李额 |
| `get_seat_map(offer_id)` | 可售状态和选座费 |
| `create_order(offer_id, passengers, type)` | `type` 为即时出票或占座 |
| `pay_order(order_id, authorization_id)` | 必须附旅客签发的支付授权 |
| `select_seats`，`add_baggage` | 附加服务 |
| `get_order(order_id)` | 订单状态，可执行的动作 |
| `request_change(order_id, …)`，`confirm_change(change_offer_id)` | 先报价后确认 |
| `quote_cancellation(order_id)`，`confirm_cancellation(quote_id)` | 返回退款金额和退款去向 |
| `split_order(order_id, passenger_ids)` | 拆单 |
| `get_flight_status(flight_id)` | 延误和取消 |
| `search_policy(query)` | 检索平台政策 |

| 旅客 | 说明 |
|---|---|
| `get_my_profile()`，`get_my_wallet()`，`get_my_calendar()` | 私有信息 |
| `search_flights(…)` | 只读 |
| `authorize_payment(order_id, max_amount, expires_at)` | 签发授权 |
| `get_my_orders()` | 自己名下的订单 |
| `respond_to_airline_change(change_id, action)` | 接受，改签，或取消 |

### 1.7 外生事件

| 事件 | 触发 | 考察什么 |
|---|---|---|
| 报价过期，价格变动 | 逻辑时刻 | 是否重新确认，是否在授权上限内 |
| 最后一张低价票被背景需求买走 | 谓词：agent 搜索后若干步未下单 | 占座的使用 |
| 航司调整时刻 | 出票之后 | 两张订单收到不同调整时的协调 |
| 延误导致误接 | 出票之后 | 两人一起改签；是否识别退款资格 |
| 航班取消 | 出票之后 | 改签与退款之间的选择 |
| 支付被拒 | 支付时 | 回问付款人 |
| 一位旅客改变计划 | 脚本旅客的人设 | 拆单；罚金由谁承担 |

### 1.8 任务族

| 族 | 内容 | 难点 | 利益 |
|---|---|---|---|
| T1 同行 | 同一出发地，两人一起订 | 两份预算和时间窗；邻座 | 一致 |
| T2 会合 | 不同出发地，同一目的地 | 到达时间差；多机场都市区的地面段；时区 | 一致 |
| T3 稀缺 | 低价舱只剩一张，或只剩一对邻座 | 谁拿便宜票；是否如实告知双方 | 混合 |
| T4 占座与期限 | 一位旅客要晚些才能确认 | 占座，报价过期，24 小时规则 | 一致 |
| T5 扰动 | 延误或取消 | 重新求最优；退款和补偿资格；单票与分票的差别 | 一致 |
| T6 部分变更 | 一人取消或改期 | 拆单；退款回付款人；罚金分担 | 混合 |
| T7 规则压力 | 旅客要求规则不允许的事，或要求动另一个人的订单 | 拒绝；取得当事人同意 | 对立 |

### 1.9 真值怎么算

- **规则真值**：规则引擎直接给出每个动作是否允许，以及费用、退款、补偿的金额。
- **最优真值**：枚举。每位旅客的候选行程是直飞加一次中转，乘以三个票价品牌，量级是几十到几百；两人的组合再加上共享库存和邻座约束，仍然可以穷举。目标是两人效用之和，同时报告两人效用的差距。
- **扰动后的最优**：从事件发生后的实际状态重新求解，已付的钱和改退规则都算进去。得分是最终结果相对这个新最优的比例，称为恢复得分。
- **事实真值**：旅客助理被测时，把它在消息里对预算和时间的陈述与角色卡对照，得到不实陈述的比例。

---

## 2. 购物

### 2.1 已有工作与空白

| 基准 | 角色，被测方 | 规模 | 怎么验证 | 缺什么 |
|---|---|---|---|---|
| [tau-bench 零售](https://arxiv.org/abs/2406.12045) | 被测：客服 agent；用户是模拟器 | 115 个任务 | 数据库终态 | 无商家竞争，无支付和物流动态 |
| [Magentic Marketplace](https://arxiv.org/abs/2510.25779) | 顾客 agent 对商家 agent | 100 个顾客对 300 个商家 | 效用对照最优商家 | 静态市场；无售后 |
| [Automated but Risky Game](https://arxiv.org/abs/2506.00073) | 买家模型对卖家模型，9 个模型两两对打 | 100 个真实商品 | 价格指标和异常率 | 只有议价 |
| [AgenticPay](https://arxiv.org/abs/2602.06008) | 两侧都是模型；从双边议价到多对多竞争共 8 种市场拓扑 | 160 个多模态任务，4 个业务场景 | 基于效用的协议质量和联合福利 | 止于达成协议，无履约和售后 |
| [ACES](https://arxiv.org/abs/2508.02630) | 买家视觉 agent | 8 个品类 | 唯一占优选项 | 一次性选择 |
| [Vending-Bench Arena](https://andonlabs.com/evals/vending-bench-arena) | 3 到 5 个经营者竞争 | 每轮 4 次运行 | 个体余额 | 无买方 agent |
| [ACWorld](https://arxiv.org/abs/2608.02441) | 买家 agent 和商家 agent 独立受控；平台用规则协议在每个动作生效前校验 | 200 加 60 个任务；约 78.5 万个挂牌 | 过程记录加终态 | 最接近的竞品，动手前必须精读 |

已有工作的四个发现，都应该能在我们的环境里复现。均取自各论文的摘要：
- 所有模型都有严重的首个报价偏差，响应快的商家相对质量好的商家有 10 到 30 倍优势（Magentic Marketplace）。
- 只有在理想的检索条件下才接近最优福利，规模变大后表现急剧下降（Magentic Marketplace）。
- 不同模型为用户争到的结果差距显著，并且会出现超预算、接受不合理成交这类异常（Risky Game）。
- 只看终态会漏掉过程中的错误（ACWorld）。

空白：没有找到同时具备这四点的基准：两侧都是模型，完整的售后链，可计算的真值，多个买家。

### 2.2 角色怎么分

| 方案 | 先例 | 能测什么 | 代价 |
|---|---|---|---|
| 1 买家对 1 卖家 | Risky Game，AgenticPay | 议价，约束违规，剩余分割 | 没有搜索和竞争 |
| 1 买家对 N 个竞争卖家 | Magentic，ACES | 比价，首个报价偏差，抗操纵，相对最优的损失 | 卖家用模型时方差大 |
| N 买家抢稀缺库存 | Market-Bench | 分配效率，公平，合谋 | 最优解要靠机制来定义 |
| 同一委托人的多个买家（家庭预算，团购） | 未找到先例 | 协调，预算分摊，避免重复购买 | 要定义联合效用 |
| 加一个平台或仲裁角色 | ACWorld，tau-bench | 政策遵循，纠纷裁决 | 仲裁用模型的话真值变软 |

**建议的第一版**：1 个买家加 3 个互相竞争的商家。平台、支付、承运商、仲裁都由内核用确定性规则扮演。

| 席位 | 知道什么 | 能做什么 |
|---|---|---|
| `buyer` | 委托人的需求、预算、截止日、计分规则；支付授权的约束 | 搜索，询问，加购，结账，追踪，申请退换，升级纠纷 |
| `merchant_1..3` | 自己的成本、底价、库存、促销权限、退货政策 | 回答询问，发结构化报价，发货，处理退换申请 |
| 世界内核 | 商品的真实属性，物流的真实结果 | 执行底价、库存、促销规则；裁决纠纷 |

关键做法是**内核裁决，模型表述**：商家的底价、库存、叠券规则由内核强制，模型只负责对话和出价。这样商家侧的方差被压住，结果可复现。E-Commerce Bench 用的就是这个办法。

多买家放到第二版，它是目前没有先例的卖点。

### 2.3 世界模型：必须有的 15 项

| # | 因素 | 真实系统里的对应 |
|---|---|---|
| 1 | 变体级商品目录，属性有真值 | schema.org `Product`，`ProductGroup`，`sku` |
| 2 | 库存，加购不等于锁货 | schema.org `availability`；ACP `out_of_stock` |
| 3 | 价格随时间变，报价有有效期 | `priceValidUntil`；UCP 结账会话默认 6 小时过期 |
| 4 | 到手价：商品减折扣，加运费、税、费用 | ACP `Total` 的类型 |
| 5 | 促销规则：计算顺序，叠加上限，门槛，过期 | Shopify：每单最多 5 个商品或订单折扣码加 1 个运费码 |
| 6 | 履约选项与时效，带随机迟到、丢件、拆单 | ACP `Fulfillment` 状态和事件 |
| 7 | 授权与扣款分离；带约束的支付令牌 | Stripe PaymentIntent；AP2 `payment.amount_range`、`payment.allowed_payees` |
| 8 | 订单和履约状态机，加通知 | ACP `Order`；Shopify 的四条并行状态 |
| 9 | 退换政策：窗口，费用，成色，退款时限 | schema.org `MerchantReturnPolicy` |
| 10 | 纠纷升级链：卖家，平台担保，拒付，每级有期限 | eBay 退款保障；Stripe 争议流程 |
| 11 | 卖家异质性与声誉 | 评分，评论，各自的政策 |
| 12 | 信息不对称与对抗内容 | 赞助标签，夸大宣传，假评论，页面里的注入 |
| 13 | 委托人授权与回问 | ACP `requires_escalation`；AP2 的两种授权模式 |
| 14 | 身份与权限，审计日志 | AP2 的收据作为纠纷证据 |
| 15 | 全局时钟 | 各种窗口和期限 |

可以放心简化的 5 项：税（按目的地一个税率）；支付网络与密码学；物流（一个承运商加带种子的分布）；多币种和跨境；搜索排序和广告竞价（只保留一个赞助标记）。

### 2.4 可以直接照搬的真实协议对象

2026 年的协议名称有变化，设计时以当前版本为准。

| 协议 | 现状 | 我们照搬什么 |
|---|---|---|
| [ACP](https://github.com/agentic-commerce-protocol/agentic-commerce-protocol)（OpenAI 与 Stripe） | 规范版本 2026-04-17 | 结账会话的状态枚举；警告码和错误码：`price_change`、`low_stock`、`shipping_delay`、`expiring_promotion`、`discount_code_combination_disallowed`、`out_of_stock`、`payment_declined`；售后对象的类型：`refund`、`return`、`exchange`、`dispute` |
| [AP2](https://github.com/google-agentic-commerce/AP2)（Google） | v0.2，2026-04-28 | 支付授权的约束字段：金额范围，预算，允许的收款方，有效期；有人在场和无人在场两种模式 |
| [UCP](https://ucp.dev/)（Google、Shopify 等） | 2026 年发布 | 目录、购物车、结账、订单四组能力；消息严重度：可恢复，需买家输入，需买家复核，不可恢复 |

一个核实结果：AP2 早期版本里的 Intent Mandate 和 Cart Mandate 在 v0.2 里已经改名（早期版本文档本次未打开，未核实）。OpenAI 的 Instant Checkout 在 2026 年 3 月收缩一事只有二手报道。

### 2.5 规则与数字

| 事项 | 数字 | 出处 |
|---|---|---|
| 叠券上限 | 每单 5 个商品或订单折扣码，加 1 个运费码 | [Shopify](https://help.shopify.com/en/manual/discounts/discount-combinations) |
| 授权有效期 | 线上卡授权一般 7 天 | [Stripe](https://docs.stripe.com/payments/place-a-hold-on-a-payment-method) |
| 未收到货 | 预计送达日后 30 天内报告；卖家 3 个工作日内回应，否则平台介入 | [eBay 退款保障](https://www.ebay.com/help/policies/ebay-money-back-guarantee-policy/ebay-money-back-guarantee-policy?id=4210) |
| 货不对板 | 送达后 30 天内申请；卖家收到退货后 2 个工作日内退款 | 同上 |
| 欧盟退货 | 14 天无理由；法定保修至少 2 年 | [欧盟消费者页](https://europa.eu/youreurope/citizens/consumers/shopping/returns/index_en.htm) |
| 拒付 | 持卡人通常有 120 天；商家 7 到 21 天举证 | [Stripe 争议流程](https://docs.stripe.com/disputes/how-disputes-work) |
| 退货率 | 2025 年线上退货率 19.3%；9% 的退货是欺诈 | [NRF](https://nrf.com/media-center/press-releases/consumers-expected-to-return-nearly-850-billion-in-merchandise-in-2025) |
| 假评论 | FTC 规则 2024-10-21 生效，涵盖 AI 生成的评论 | [FTC](https://www.ftc.gov/news-events/news/press-releases/2024/08/federal-trade-commission-announces-final-rule-banning-fake-reviews-testimonials) |

Amazon 的 30 天退货窗口和 A-to-z 担保的 90 天期限只读到搜索摘要，未核实。

### 2.6 数据来源与许可

| 数据 | 用途 | 许可 |
|---|---|---|
| [Amazon Berkeley Objects](https://amazon-berkeley-objects.s3.amazonaws.com/index.html) | 商品和属性 | CC BY 4.0 |
| [Amazon ESCI](https://github.com/amazon-science/esci-data) | 替代品和互补品关系 | Apache-2.0 |
| [Open Food Facts](https://world.openfoodfacts.org/data) | 食品属性 | ODbL |
| [Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) | 履约时效和延迟的分布 | CC BY-NC-SA；只拟合参数，不分发 |
| Amazon Reviews 2023 | 不建议直接用 | 数据卡没有声明许可 |

### 2.7 接口

| 买家 | 商家 |
|---|---|
| `search_catalog`，`get_product`，`get_reviews`，`get_merchant_profile` | `get_inventory`，`get_cost_and_floor`（私有） |
| `create_cart`，`update_cart`，`apply_discount_code` | `propose_order(items, total, expires_at)` |
| `create_checkout`，`select_fulfillment`，`complete_checkout(payment_token)` | `set_promotion`（在权限内） |
| `get_order`，`track_shipment` | `ship_order` |
| `request_return`，`request_refund`，`request_exchange` | `respond_to_return(approve 或 deny, reason)`，`issue_refund` |
| `escalate_dispute` | `get_policy` |
| `ask_principal(question)` | |

`ask_principal` 对应真实协议里的升级状态：超出授权时必须回问委托人。委托人在 v1 里是脚本。

### 2.8 外生事件

| 事件 | 对应的真实错误码或规则 |
|---|---|
| 结账时缺货 | ACP `out_of_stock` |
| 结账前变价 | ACP `price_change` |
| 促销即将过期，券不能叠加 | ACP `expiring_promotion`，`discount_code_combination_disallowed` |
| 支付超出授权上限 | AP2 的金额约束；ACP `payment_declined` |
| 迟到，丢件，拆单 | ACP 履约事件 `failed_attempt`，`undeliverable` |
| 损坏，货不对板 | 平台担保规则 |
| 退货窗口将到期 | 商家政策 |
| 假评论，赞助标签，页面或消息里的注入 | Magentic 和 ACES 测过的条件 |

### 2.9 任务族

| 族 | 内容 | 利益 |
|---|---|---|
| S1 到手价最优 | 跨商家比较，含叠券、运费门槛、税 | 买家对规则 |
| S2 询问隐藏属性 | 兼容性等信息只有问商家才知道；商家可能夸大 | 混合，事实真值 |
| S3 议价与组合报价 | 商家有底价和促销权限；买家有预算和别的选择 | 混合 |
| S4 结账事件 | 缺货，变价，超授权 | 买家对规则，需回问委托人 |
| S5 售后 | 迟到、丢件、损坏、货不对板；退换；升级到平台 | 对立，规则真值 |
| S6 对抗内容 | 假评论，赞助，注入 | 对立 |
| S7 多买家（第二版） | 家庭共享预算；抢稀缺库存 | 混合 |

### 2.10 真值怎么算

- **买家的最优**：枚举商家、变体、促销组合、履约选项，求最高的到手效用。效用等于商品价值减到手价减超期惩罚，硬约束是预算和授权范围。
- **议价的参照**：两个界。上界是以最优商家的底价成交；对脚本商家还能算出按其让步规则可达的最好结果。得分在"不买"和上界之间归一化。
- **联合效率**：成交是否发生在总剩余最大的那一对买卖双方之间。
- **售后的规则真值**：给定真实发生的事（是否损坏，是否迟到）和适用的政策，规则引擎算出应得的补救。买家得分是实际拿到的补救除以应得的补救。商家被测时反过来查：有没有错误拒绝，有没有超出政策多退。
- **事实真值**：商家在消息里对商品的陈述与真实属性对照。

---

## 3. 理赔

### 3.1 已有工作与空白

| 基准或数据 | 内容 | 缺什么 |
|---|---|---|
| [InsClaimBench](https://arxiv.org/abs/2610.09671) | 3,780 个理赔案例，覆盖车险、财产险、健康险；86,656 条原子规则判断；从规则到模块到赔付决定到金额的链条 | 单个模型裁决一份完整案卷；没有对立的各方 |
| [INS-MMBench](https://arxiv.org/abs/2406.09105) | 保险图像选择题 | 单轮感知 |
| [InsQABench](https://arxiv.org/abs/2501.10943) | 中文保险问答 | 只有问答 |
| [UNDERWRITE](https://arxiv.org/abs/2602.00456) | 多轮核保 agent，带模拟用户 | 核保，不是理赔；单 agent |
| [CRMArena-Pro](https://arxiv.org/abs/2505.18878) | 19 类客户关系任务 | 无对立利益 |
| [NegotiationArena](https://arxiv.org/abs/2402.05863) 等 | 抽象收益的议价 | 没有法规和工具 |
| [AgentMediation](https://arxiv.org/abs/2509.06586) 等 | 民事纠纷调解的模拟 | 没有保险公司，没有可计算的结算额 |
| [NHTSA CRSS](https://www.nhtsa.gov/crash-data-systems/crash-report-sampling-system) | 警方事故报告抽样，约 120 个编码字段 | 没有责任比例和理赔；适合做事故类型的先验 |

空白：没有找到"对立的保险公司和车主在法规之下协商一起理赔"的基准。InsClaimBench 证明了金额真值可以由规则算出，但它是单模型判卷。

### 3.2 角色

| 席位 | 目标 | 知道什么 |
|---|---|---|
| `driver_a`（主要责任方） | 自付最少：免赔额，超出限额的部分，次年加费 | 自己的保单；自己持有的证据 |
| `driver_b`（次要或无责方） | 尽快拿到足额赔付；自付最少 | 自己的保单；自己持有的证据，例如行车记录仪 |
| `adjuster_a`，`adjuster_b` | 本公司净支出最少，同时不违反行为规则，并对自己的被保险人尽义务 | 本公司的案卷和保单；对方只给了什么就知道什么 |
| 世界内核 | | 事故的真实经过；扮演警方、定损、租车、仲裁、监管时钟 |

每位车主同时有两重身份：对自己的保险公司是被保险人，对对方的保险公司是索赔人。这是理赔场景结构上最有意思的地方：`driver_b` 和 `adjuster_b` 多数时候利益一致，但在免赔额返还上利益相反。

### 3.3 真实流程

1. **报案**：字段对照 ACORD 2 车险出险通知，包括时间地点、警方报告号、违章、保单与限额、车辆与驾驶人、对方车辆与保险公司、伤者、证人。
2. **核实承保**：保单是否有效，有哪些险种，限额和免赔额。
3. **调查与定责**：陈述，警方报告，照片，交通法。由保险公司定，监管机构不裁定责任。
4. **定损**：维修估价；全损判断；实际现金价值。
5. **两条索赔路线**：走自己的碰撞险，快，但先扣免赔额，再由自己的保险公司向对方追偿；或直接向对方保险公司索赔，无免赔额，但按自己的责任比例扣减。
6. **追偿**：保险公司之间的代位求偿，追回的钱要按比例返还被保险人的免赔额。
7. **仲裁**：两家谈不拢时提交行业仲裁。仲裁员按事故发生地的法律给每一方定责任百分比，裁决是终局的，30 天内支付。
8. **结案**：支付，记录。

### 3.4 规则出处表

| 规则 | 内容 | 出处 |
|---|---|---|
| 过失制度 | 纯比较过失 10 个州，含加州；修正比较过失 51% 门槛 25 个州，含得州；50% 门槛 10 个州，含佐治亚；纯共同过失 4 个州加华盛顿特区，含马里兰 | [MWL 各州对照表](https://www.mwl-law.com/wp-content/uploads/2018/02/CONTRIBUTORY-NEGLIGENCE-COMPARATIVE-FAULT-LAWS-CHART-3.pdf)，律所汇编，带各州法条引用 |
| 定责推定（加州） | 合法停放、被追尾且无违章定罪、对方有违章定罪，推定无责；"主要责任"指 51% 及以上 | [10 CCR 2632.13](https://www.law.cornell.edu/regulations/california/10-CCR-2632.13) |
| 最低限额 | 加州 30/60/15（2025 年起），得州 30/60/25 | [加州保险局公告](https://www.insurance.ca.gov/0250-insurers/0300-insurers/0200-bulletins/bulletin-notices-commiss-opinion/upload/bulletin-2023-1-re-sb-1107-final-003.pdf)，[得州保险局指南](https://www.tdi.texas.gov/pubs/consumer/cb020.html) |
| 时限（加州） | 15 天内确认收到；40 天内接受或拒绝；30 天内支付 | [10 CCR 2695.5](https://www.law.cornell.edu/regulations/california/10-CCR-2695.5)，[2695.7](https://www.law.cornell.edu/regulations/california/10-CCR-2695.7) |
| 免赔额返还 | 追偿请求必须包含被保险人的免赔额，追回款按比例分享 | 10 CCR 2695.7(q) |
| 全损与估值（加州） | 按可比车辆的成本加税费估值；可比车辆须在本地 90 天内可得；扣减须逐项列明 | [10 CCR 2695.8](https://www.law.cornell.edu/regulations/california/10-CCR-2695.8) |
| 全损判定 | 维修费加残值不低于实际现金价值；各州另有百分比门槛，得州 100%，佛州 80%，多州 75% | [MWL 全损门槛表](https://www.mwl-law.com/wp-content/uploads/2018/02/AUTOMOBILE-TOTAL-LOSS-THRESHOLDS-3.pdf) |
| 行为规则 | 不得给出不合理的低报价；责任清楚时不得引导第三方索赔人去用自己的保单；拒赔须说明理由 | 10 CCR 2695.7(g)，2695.8(d)；[NAIC 示范法 900](https://content.naic.org/sites/default/files/model-law-900.pdf) |
| 和解义务 | 无理拒绝限额内的和解要求，保险公司可能要承担超出限额的全部判决 | [Crisci 案](https://scocal.stanford.edu/opinion/crisci-v-security-ins-co-30069) |
| 行业仲裁 | 签约公司的车损追偿在每项 10 万美元以内必须仲裁；裁决终局；30 天内支付并含免赔额份额 | [Arbitration Forums 参考指南](https://home.arbfile.org/getmedia/1ae0b5d0-d3f7-464f-ba98-a0d7d0154015/ReferenceGuide.pdf) |
| 欺诈迹象 | 深夜偏僻路段；多名乘客症状相同；口径一致得像背过；突然刹停 | [NICB](https://www.nicb.org/sites/files/2019-06/Scene_Indicators_for_Law_Enforcement.pdf) |

### 3.5 真值怎么算

记责任比例 `f_A + f_B = 1`，损失 `D_i`，对方的财产损失责任限额 `L_j`，碰撞险免赔额 `d_i`。一方自己的责任为 `f` 时，可获赔的比例 `ρ(f)`：

| 制度 | `ρ(f)` |
|---|---|
| 纯比较过失 | `1 − f` |
| 51% 门槛 | `f ≤ 0.5` 时为 `1 − f`，否则 0 |
| 50% 门槛 | `f < 0.5` 时为 `1 − f`，否则 0 |
| 共同过失 | `f = 0` 时为 1，否则 0 |

公式（由上表规则推导，不是某一份官方算例）：
- 向对方索赔的应得额：`T_i = ρ(f_i) · D_i`。对方保险公司付 `min(T_i, L_j)`，超出部分由对方车主自付。
- 走自己碰撞险的赔付：`C_i = min(维修费, 实际现金价值) − d_i`。
- 追偿：请求额 `S_i = C_i + d_i`，追回 `R_i = min(ρ(f_i) · S_i, L_j)`。
- 免赔额返还：`d_i · R_i / S_i`。

算例：B 的损失 10,000 美元，A 的损失 6,000 美元，免赔额各 500 美元。

| 制度 | A 八成责任：B 获赔，A 获赔 | 各五成：B 获赔，A 获赔 |
|---|---|---|
| 纯比较过失（加州） | 8,000，1,200 | 5,000，3,000 |
| 51% 门槛（得州） | 8,000，0 | 5,000，3,000 |
| 50% 门槛（佐治亚） | 8,000，0 | 0，0 |
| 共同过失（马里兰） | 0，0 | 0，0 |

同一起事故在四种制度下的结果完全不同，五成责任处有悬崖。这本身就是一个任务族。

路线冲突的算例（加州，A 八成责任）：
- B 走碰撞险：先拿到 9,500；保险公司 B 追回 8,000；B 的免赔额返还 400；B 最终自付 100。
- B 只向对方索赔：拿到 8,000；自付 2,000。
- 两条路线对 B 差 1,900 美元，对保险公司 B 则相反。
- 两人都走碰撞险时，四方的净支出是保险公司 A 12,400、保险公司 B 3,100、车主 A 400、车主 B 100，合计 16,000 美元，等于两车损失之和。这个守恒关系可以作为规则引擎的单元测试。

真值分三层：
- **事实真值**：生成器写下事故的真实经过，以及由它决定的法定责任比例 `f*`。
- **全信息应得额**：按 `f*` 和上面的公式算出每一方应得和应付的金额。
- **仲裁结果**：仲裁由内核用规则扮演，只看各方实际提交的证据。给定提交了哪些证据，裁决是确定的。它是协商破裂时的结果，也就确定了每一方的谈判底线。

### 3.6 世界模型：必须有的 15 项

1. 隐藏的事故真实经过，以及按持有人分配的证据（行车记录仪，证人，照片，警方报告）。
2. 责任比例和可切换的 `ρ(f)`。
3. 保单记录：险种，分项限额，免赔额，是否有效。
4. 分类的损失台账，估价带噪声。
5. 全损判断和实际现金价值估值。
6. 两条索赔路线，收益不同。
7. 追偿的请求与回应，免赔额按比例返还。
8. 有约束力的仲裁作为谈不拢的结果，带费用和 30 天支付规则。
9. 法定时钟：确认，决定，支付。
10. 行为规则：不得低报价，拒赔须书面说明理由，估价须披露。
11. 限额与超额风险，以及和解义务。
12. 委托代理结构：保险公司看成本，被保险人看自付和加费。
13. 配合义务：对自己的保险公司有，对对方的没有。
14. 租车和停车费按天累计。
15. 案卷：准备金，支付，备注，欺诈标记，可供审计。

可以放心简化的 5 项：估价明细压成几行，最多一次补充定损；人伤只保留固定的医疗账单，不做精神损害和律师；警方和仲裁用规则扮演，不做诉讼；保费评级换成固定加费；只有两辆车，不做乘客和未保险驾驶人险。

数据模型对照行业系统：案卷结构参照 Guidewire ClaimCenter 的索赔、风险暴露、事故、准备金、支付、追偿；报案字段参照 ACORD 2。

### 3.7 管辖的选择

建议 v1 用加州规则，`ρ(f)` 做成开关。

| 理由 | 说明 |
|---|---|
| 赔付对责任比例是线性的 | 纯比较过失下双方都有有效的索赔，评分没有悬崖 |
| 义务可以机器检查 | 加州公平理赔条例给出 15、40、30 天的时限，免赔额按比例返还，全损估值方法，禁止引导 |
| 车损跟着过错走 | 加州不是无过错州 |

之后加得州（51% 门槛）作为第一个变体，再加马里兰（共同过失）。

中国规则可以作为单独的领域包：交警把责任定为全部、主要、同等、次要、无责五档，商业险示范条款在没有约定时按 70%、50%、30% 执行，交强险先在限额内赔付（财产损失有责限额 2,000 元）。责任由公权力给定之后，协商的重心会从定责转到定损和程序。来源：[银保监会 2020 年通知](https://www.gov.cn/zhengce/zhengceku/2020-09/04/content_5540321.htm)，示范条款取自保险公司公开的副本。

### 3.8 接口

| 车主 | 理赔员 |
|---|---|
| `get_my_policy()`，`get_my_evidence()` | `get_claim_file(claim_id)`，`verify_coverage(policy_id)` |
| `file_claim(carrier, fnol)` | `request_police_report()`，`request_statement(party)` |
| `submit_statement(claim_id, text)` | `get_estimate(vehicle)`，`lookup_prior_claims(party)` |
| `share_evidence(item_id, to)` | `set_liability(shares, reasons)`，`set_reserve(amount)` |
| `get_claim_status(claim_id)` | `make_offer(claim_id, amount, basis)`，`deny_claim(claim_id, reason)` |
| `respond_to_offer(offer_id, accept 或 reject 或 counter)` | `issue_payment(claim_id, amount)` |
| `rent_car()`，`return_car()` | `send_subrogation_demand(amount, evidence)`，`respond_to_demand(…)` |
| `request_appraisal(claim_id)` | `file_arbitration(evidence)`，`flag_fraud(claim_id, reason)` |
| | `search_regulations(query)` |

### 3.9 外生事件

| 事件 | 考察什么 |
|---|---|
| 警方报告在若干天后才出 | 在信息不全时先定准备金，之后更新 |
| 拆检发现隐藏损伤，估价上调 | 补充定损；是否越过全损线 |
| 证人陈述或行车记录仪在中途出现 | 是否据此修改定责 |
| 租车费按天累计 | 拖延的代价由谁承担 |
| 法定时限到期 | 是否按时确认、决定、支付 |
| 仲裁裁决 | 是否按期支付并返还免赔额份额 |

### 3.10 任务族

| 族 | 内容 | 利益 |
|---|---|---|
| I1 责任清楚 | 追尾；考流程、时限、金额、免赔额返还 | 一致 |
| I2 责任有争议，证据分散 | 两家理赔员协商责任比例；仲裁兜底 | 对立 |
| I3 路线选择 | `driver_b` 选碰撞险还是向对方索赔；`adjuster_b` 的建议是否对被保险人有利 | 混合 |
| I4 全损 | 估值争议，可比车辆，逐项扣减 | 对立 |
| I5 超限额 | 损失高于对方的责任限额；和解义务；A 的超额自付 | 混合 |
| I6 制度切换 | 同一事故分别在加州、得州、马里兰规则下处理 | 对立 |
| I7 夸大与欺诈 | 一方有动机把旧伤算进来；理赔员查既往理赔并标记 | 对立，事实真值 |
| I8 拖延 | 租车费在累计；谁在拖 | 混合 |

### 3.11 这个场景特有的指标

| 指标 | 定义 |
|---|---|
| 结算误差 | 每一方实际收付与全信息应得额之差的绝对值 |
| 时限合规 | 法定时限内完成的比例 |
| 行为违规数 | 低报价、无理由拒赔、不当引导的次数；低报价按"报价低于应得额的某个比例且责任清楚"判定 |
| 漏损 | 仲裁费，以及拖延造成的租车费 |
| 不实陈述 | 各方在陈述里说的与事故真实经过不符的比例 |
| 对被保险人的忠实 | 理赔员是否返还了应返还的免赔额，是否在限额内合理和解 |
