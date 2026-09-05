# 02 技术选型（ADR）

> 每个决策记录为 ADR：结论 / 理由 / 备选 / 代价。原则：**决策确定性优先，LLM 只做理解与说话；依赖能不加就不加。**

## ADR-01：Python 3.11 + FastAPI + SQLAlchemy 2（保留现状）

- 结论：沿用 `backend/` 现有栈（fastapi 0.111 / sqlalchemy 2.0.30 / pydantic 2.7 / uvicorn）。
- 理由：代码可跑、测试已绿、够用；重写框架不带来产品价值。
- 备选：重写为其他 Web 框架 → 无收益。代价：需遵守现有 ruff 与 pyproject 约束。

## ADR-02：会话状态存 DB JSON，不引 LangGraph checkpointer

- 结论：`Conversation.state` 存版本化 JSON（v2 schema，见 03），DB 即状态源。
- 理由：断点续聊=读 state 继续，天然满足 FR-10；零新增依赖。
- 备选：LangGraph checkpointer → 引入图框架税，探索期拓扑未定，易画错图。
- 代价：状态 schema 需自行版本化（`v` 字段），并发写需串行（见 03 §并发）。

## ADR-03：编排层用手写薄管线，不引 LangGraph/LangChain

- 结论：节点写纯函数 `node(ctx) -> patch`，编排是十几行顺序循环（见 03 §节点契约）。
- 理由：本项目是“有长期目标的拟人对话控制器”，不是多步工具求解；核心难点在人设/边界/评测，不在编排。旧 7-Agent 与方案 C 的教训：框架不是能力来源。
- 备选：一开始就用 LangGraph → 被否，理由见 04 风险与 03 迁移路径。
- 代价：将来拓扑复杂到 >10 分支嵌套且需要回放评测时，再包一层 StateGraph（节点原样搬，1-3 天），预留了映射形状。

## ADR-04：LLM Provider 自持 httpx（保留现状），抽象 `generate()/extract_json()`

- 结论：保留 `llm/provider.py` 的单次生成抽象；v0.3 为其增加**结构化输出**能力（analyze 用）。
- 理由：DeepSeek/OpenAI 兼容接口已打通，不重复造轮子；抽象一层便于将来换模型/加网关。
- 备选：langchain 的 model wrapper → 无必要抽象层。

## ADR-05：Analyzer 用“结构化 JSON 输出”，正则兜底

- 结论：感知节点优先用模型结构化输出（优先 function calling/JSON mode；不可用则退化正则+规则，全不可用则 mock）。
- 理由：用户输入随机，正则覆盖不了语义；但正则便宜、确定性，作为低置信度时的兜底与关键词省钱路径。
- 代价：结构化输出 schema 必须严格定稿并做 schema 校验（Pydantic），坏 JSON 走降级路径。

## ADR-06：每轮 LLM 调用 ≤ 2 次（Analyzer + Actor），决策不进模型

- 结论：硬预算 NFR-PERF-1。发不发照片、阶段推进、红包解锁均为代码策略。
- 理由：控延迟、控成本、行为可复现可测试。
- 代价：人设差异靠“配置参数 + prompt”表达，需要足够的提示词调优投入。

## ADR-07：数据库 SQLite（开发）→ PostgreSQL（生产候选）

- 结论：v0.3 继续 SQLite（现有 `data/1v1chat.db`），启用 WAL + busy_timeout；生产化（v0.5）切 PostgreSQL 并引入 Alembic 迁移。
- 理由：demo 单机足够；`DATABASE_URL` 已是配置项，切换成本低。
- 代价：多进程部署前必须完成切库，SQLite 不适合多 worker 写并发。

## ADR-08：不用 Redis / Chroma / 向量记忆

- 结论：记忆用 facts JSON（FR-09）；会话队列 v0.5 再评估（优先进程内任务 + DB 乐观锁，其次 Redis）。
- 理由：demo 数据量小；`.env` 里的 REDIS_URL/CHROMA 等键为历史残留，v0.3 清理无用配置避免误导。

## ADR-09：前端保留 Vue3，API 契约不变

- 结论：v0.3 不改前端；`/api/chat/send` 的 `ChatResponse`、消息结构、`agent_trace` 字段保持兼容。
- 理由：重构范围只到 engine 层；前端改动是另一笔账。
- 备选：重写前端 → 无收益。

## ADR-10：可观测走“trace 结构 + 适配器接口”，Langfuse 留待 v0.5

- 结论：engine2 输出结构化 trace JSON 落库（agent_trace）；预留 `tracing/` 适配器接口；`.env` 已有 `LANGFUSE_*`，v0.5 再启用。
- 理由：先有数据再上平台；避免 demo 阶段引入外部依赖与网络失败点。

## ADR-11：测试用 pytest + pytest-asyncio + ruff（保留），新增 tests/engine2_core/

- 结论：沿用现有测试栈；旧测试冻结不动，新测试进 `tests/engine2_core/`（目录名避开与 engine2 应用包同名遮蔽）。
- 理由：回归门槛 NFR-TEST-2 依赖稳定测试基建。

## ADR-12：运行时不用 ReAct / Multi-Agent / MCP / Skills

- 结论：
  - ReAct：不需要。本问题每轮至多“分析→决策→说话”，无多步工具推理。
  - Function calling：Analyzer/Actor 需要时用“模型输出结构化动作”，但动作必须白名单 + 策略把关，不放开自由调工具。
  - Multi-Agent：运行时不用（一个会话只有一个人，多角色一致性差）；离线对抗评测用一个模拟用户模型即可（见 04 评测件）。
  - MCP/Skills：运行时不需要（工具全在进程内）；它们服务于异构工具生态/编码型 agent，与本产品形态不同。
- 理由：控制层越多确定性越好；任何“agent 化”倾向都引入行为漂移与 AI 味。

## 技术栈矩阵（落地目标）

| 层 | 选型 | 来源 |
|----|------|------|
| Web | FastAPI 0.111 + uvicorn | 保留 |
| ORM | SQLAlchemy 2.0.30 | 保留 |
| 数据 | SQLite（dev）/ PostgreSQL（v0.5） | 保留/规划 |
| Schema | pydantic 2.7 | 保留 |
| LLM HTTP | httpx 0.27 + tenacity | 保留 |
| 认证 | python-jose + bcrypt（JWT） | 保留 |
| 编排 | 自研薄管线（engine2） | 新增 |
| 结构化输出 | OpenAI 兼容 function calling / JSON mode，正则兜底 | 新增能力 |
| 观测 | trace JSON + 适配器接口（Langfuse v0.5） | 规划 |
| 测试 | pytest 8 + pytest-asyncio + ruff 0.4 | 保留 |
| 前端 | Vue3 + axios + Vite | 保留 |

## 明确不引入（当前版本）

`langgraph`、`langchain`、`chromadb`、`redis`（运行时）、`openai` SDK（httpx 已够）、MCP server、任何多 Agent 框架。
