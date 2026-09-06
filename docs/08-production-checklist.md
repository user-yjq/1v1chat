# 08 生产化缺口清单与加固台账（T-15 / M4 阶段一评审基线）

> 依据：01 需求与边界（§2 FR / §3 NFR / §4 分层披露 / §5 合规红线）、02 ADR、03 架构、04 WBS T-15。
> 本文档先做**缺口审计**（每项带现状证据与验收方式），再排加固顺序。任何一项实施前，须先在 01 完成相应 NFR 评审（见 §4 提案），实施后回填本表状态并在 06/07 登记。

## 1. 目标 / 范围 / 评审方式

- 目标：把 demo 升级为 **v0.5 生产候选**——可多进程部署、可回滚、可观测、符合披露合规，能力与边界不变（FR 冻结）。
- 范围：运行时可靠性、数据与迁移、网关与安全、可观测性、部署/CI/发布一致性、合规与产品披露。
- 非目标：不做新业务功能、不引入多 Agent/LangGraph/MCP/向量记忆（见 02 ADR-08/12）。
- 评审方式：逐项核对源码与配置文件（证据列文件路径）；状态图例 ⏸ 未开始 / 🚧 实施中 / ✅ 已验收（登记 06）。
- 建议实施顺序见 §3；顺序建议有依赖，不要打乱。

## 2. 缺口清单

### 2.1 运行时可靠性

| ID | 缺口 | 现状（证据） | 加固建议 | 优先级 | 状态 | 验收方式 |
|----|------|--------------|----------|--------|------|----------|
| R-A1 | 会话锁只在单进程内存内 | `backend/engine2/pipeline.py` 模块级 `_LOCKS`；多 uvicorn worker 各自持有，并发会互相覆盖 state（违反 NFR-PERF-3） | 切 PostgreSQL 后用行级锁/唯一写者 | P0 | ✅ | PG advisory xact lock（routers/chat.py）；PG 并发测试通过 |
| R-A2 | LLM 上游无熔断与预算护栏 | `llm/provider.py` 仅 tenacity 3 次指数退避；上游持续故障时每轮仍等超时再走兜底 | 加错误率熔断（阈值+半开）、按用户/全局并发与 token 预算；超限直接走降级话术 | P1 | ⏸ | 注入故障：熔断后 P95 回落、兜底率有指标 |
| R-A3 | 限流为进程内滑动窗口 | `backend/core/ratelimit.py`；多 worker 各自计数（NFR-SEC-3 在多实例下失效） | 网关层或 Redis 计数；保留本进程实现作为单机回退 | P1 | ✅ | REDIS_URL 生效（INCR+EXPIRE 61s），Redis 故障自动降级进程内 |
| R-A4 | 无任务队列/背压 | 聊天为同步 HTTP 单轮处理；长轮询/后续 WebSocket 无队列 | v0.5 先不引队列；接入 WS 或重负载时再评估（进程内 asyncio.Queue + DB 乐观锁） | P2 | ⏸ | 负载模型压测通过后评审 |

### 2.2 数据与迁移

| ID | 缺口 | 现状（证据） | 加固建议 | 优先级 | 状态 | 验收方式 |
|----|------|--------------|----------|--------|------|----------|
| R-B1 | 仍是 SQLite，未切 PostgreSQL | `backend/config.py DATABASE_URL` 默认 sqlite；02 ADR-07 明确生产候选 PG | 引入 PG 连接（连接池/重试），SQLite 仅 dev 与 CI | P0 | ✅ | 本地 PG 全量 93 tests 绿 + alembic check 一致 |
| R-B2 | 无迁移工具 | `backend/db/database.py init_db()` 用 `create_all`；schema 演进不可回滚 | 引入 Alembic：基线迁移 + 后续变更走版本迁移；容器启动跑 `upgrade head` | P0 | ✅ | 基线 0001 建 5 表；SQLite/PG upgrade+check 均无漂移 |
| R-B3 | SQLite WAL/busy_timeout 未启用，与文档不符 | 02 ADR-07 声称已启用；`backend/db/database.py` 无 PRAGMA | 开发库补 `journal_mode=WAL`+`busy_timeout`（文档与代码对齐） | P2 | ✅ | 单测断言 WAL/busy_timeout=5000 |
| R-B4 | 会话 state 迁移无版本化流程 | `engine2/schema.normalize_state` 容忍旧数据，但 schema 演进策略未定义 | 定义 state v2→v3 的迁移清单与灰度策略（旧会话可降级/迁移脚本） | P2 | ⏸ | 迁移演练记录 |
| R-B5 | 消息查询无联合索引/分页 | `models/database.Message` 仅 `sent_at` 索引；`routers/conversation.py` 用 `.limit()` 无游标 | 加 `(conversation_id, sent_at)` 联合索引；消息列表改游标分页 | P2 | ⏸ | 万级消息会话接口 p95 达标 |
| R-B6 | 无备份/恢复与数据保留策略 | 已落地 `scripts/backup_pg.sh`/`restore_pg.sh`/`drill_pg_backup_restore.sh` + 保留策略（03 §16）：pg_dump -Fc + sha256 + 30 天轮转、恢复防误覆盖同名库、演练逐表行数比对 PASS | 上线按 cron 每日备份（RPO ≤24h）；SQLite 开发库直接拷贝 data 文件 | P1 | ✅ | 演练 PASS（6 表行数一致，06 ACC-M4-B6-001） |
| R-B7 | 无用户数据导出/删除闭环 | 会话只有软归档 `status="archived"`（`routers/conversation.py`），无删除/导出 | 提供导出（JSON）与彻底删除接口，删除同时清 state/messages | P1 | ⏸ | 删除后数据不可恢复（抽查 DB） |

### 2.3 网关与安全

| ID | 缺口 | 现状（证据） | 加固建议 | 优先级 | 状态 | 验收方式 |
|----|------|--------------|----------|--------|------|----------|
| R-C1 | JWT_SECRET 等生产敏感默认值未拦截 | `backend/config.py` 默认 `change-me`；`docker-compose.yml` 默认 `change-me` | 启动 fail-fast：`APP_ENV=prod` 时检测占位 secret/空 key 直接拒绝启动 | P0 | ✅ | 单测：占位 secret 被拦（test_prod_safety.py） |
| R-C2 | 登录/注册无防爆破 | `backend/routers/auth.py` 无限流/锁定 | 登录失败限流 + 账户临时锁定；注册接口人机校验（阶段量级） | P1 | ⏸ | 暴力尝试被 429/锁定 |
| R-C3 | JWT 无刷新/撤销 | `core/security.py` 仅签发 HS256 access token | 短期 access + refresh（可撤销白名单）；或改 httpOnly cookie 会话 | P2 | ⏸ | 退出后旧 token 失效 |
| R-C4 | CORS/同源策略需按环境注入 | CORS 白名单已配置化（T-13），但生产同源（nginx 反代）时需验证无 `*` 且无多余源 | compose/CI 显式注入 `CORS_ORIGINS`；提供环境校验测试 | P1 | ✅ | prod 含 `*` 即拦（test_prod_safety.py 9 passed）+ compose 注入验证（M4.3） |
| R-C5 | 管理动作无审计日志 | `backend/routers/admin.py` 直接读写 persona/scenario，无操作者与变更记录 | 后台写操作统一记审计（admin_user/动作/对象/前后摘要/时间） | P1 | ⏸ | 审计表有记录，后台可查 |
| R-C6 | 管理员引导仅靠脚本 | `backend/set_admin.py` 需人工执行，无法在容器内安全初始化 | 支持 `ADMIN_BOOTSTRAP_USERNAME/PASSWORD` 一次性引导（仅空表时生效） | P2 | ⏸ | 容器启动后可登录 admin |
| R-C7 | /media 全公开静态，无内容策略 | `backend/main.py` mount StaticFiles；素材白名单已满足 NFR-DATA-1，但目录内文件全部公开 | 维持白名单资产公开；若未来引入用户上传，改对象存储 + 签名 URL | P2 | ⏸ | 安全评审通过 |

### 2.4 可观测性

| ID | 缺口 | 现状（证据） | 加固建议 | 优先级 | 状态 | 验收方式 |
|----|------|--------------|----------|--------|------|----------|
| R-D1 | trace 有落库但无请求关联与汇聚 | `ObservabilityMiddleware` 注入/透传 `X-Request-Id`（scope.state + 响应头）；`routers/chat.py` 把 request_id 写入 `agent_trace`；日志同 id | 前端可透传 X-Request-Id 打通 前端→后端→LLM 链路 | P1 | ✅ | 单测：scope/响应头/上下文一致（test_observability.py） |
| R-D2 | 无运行指标 | `core/metrics.py` 进程内计数（LLM 调用/失败/延迟、Guard blocked/rewrote/fallback/sampled、HTTP 请求/耗时）+ `/api/metrics`（Prometheus 文本，无新依赖）；多 worker 各进程独立 | 如需跨进程聚合接 Prometheus 抓取多实例 | P0 | ✅ | 单测 render 断言 + CI docker smoke 校验 metrics 文本 |
| R-D3 | 无结构化日志/脱敏 | `core/logging.py`：应用 logger 单行 JSON（time/level/logger/message/request_id + extra 白名单）；uvicorn access 关闭防重复；**日志不含消息正文** | 内容字段一律不入日志；错误栈带 request_id | P1 | ✅ | 单测：白名单外字段不出现（test_observability.py） |
| R-D4 | 健康检查不查 DB/LLM 依赖 | liveness `/api/health` 与 readiness `/api/health/ready` 拆分：readiness=DB `SELECT 1`（硬条件）+ LLM 上游**配置**探测（mock/真实 key，不发网络） | DB 断→503 unavailable；LLM 未配真实 key→200 degraded | P2 | ✅ | 单测：db down→unavailable；auto 无 key→degraded；CI docker smoke ready 200 |

### 2.5 部署 / CI / 发布一致性

| ID | 缺口 | 现状（证据） | 加固建议 | 优先级 | 状态 | 验收方式 |
|----|------|--------------|----------|--------|------|----------|
| R-E1 | 无 CI 质量门 | `.github/workflows/ci.yml` 已落地（backend lint+test、postgres/redis service、frontend build） | 每次合入：pytest 全绿 + ruff 0 + 前端 build + 镜像构建冒烟 | P0 | ✅ | CI 远端多次 `success`（sqlite/PG 双跑 + ruff 0 + frontend build） |
| R-E2 | 版本号三处漂移 | `backend/main.py` 0.3.0-beta / 根 `pyproject.toml` 0.3.0b0 / README v0.4.0-alpha | 单一版本源（`backend/version.py`），pyproject 由测试锁同步 | P1 | ✅ | 单测断言 pyproject==version.py |
| R-E3 | .env.example 与 compose 键过期/不全 | `.env.example` 残留 EMBEDDING/CHROMA；缺 engine2 全套键（ENGINE_VERSION/LLM_MODE/GUARD_*…）；compose 未注入新键 | 重写 .env.example 覆盖全部配置项；compose 显式传 ENGINE_VERSION、LLM_MODE、GUARD_* | P1 | ✅ | .env.example 25 键与 config.py 对照；compose 注入核心键 |
| R-E4 | 默认仍跑 v1 引擎 | `backend/config.py ENGINE_VERSION="v1"` | v0.5 验收后默认切 v2，v1 移 `_legacy/`（04 §发布策略） | P1 | ⏸ | 双引擎回归 + 一键回滚演练 |
| R-E5 | 镜像/容器待加固 | backend 以非 root（`USER 10001`）运行、数据/媒体走 named volume；新增 `/api/health/ready`（DB SELECT 1）并对齐 compose healthcheck；nginx 已去 `/ws/` 死代理；根/frontend `.dockerignore`；CI 新增 docker 镜像构建+readiness 冒烟 job | 保持最小镜像与只读代码目录；bind mount 需对齐 uid 10001 | P2 | ✅ | CI docker job 构建双镜像并 ready 200 冒烟（单测 test_m44_release.py） |
| R-E6 | Makefile/说明与依赖现状不符 | Makefile 已重写：移除 requirements-py310/langgraph/chromadb/chroma 残留；test/lint 直接走仓库 `.venv`；单一依赖入口=pyproject+`backend/requirements.txt`（根 requirements.txt 已删除）；compose 健康检查对齐 ready | 改动依赖先改 pyproject，再 `make lock` 同步 | P2 | ✅ | `make lint/test` 通过；单测锁定依赖集合一致 |

### 2.6 合规与产品披露

| ID | 缺口 | 现状（证据） | 加固建议 | 优先级 | 状态 | 验收方式 |
|----|------|--------------|----------|--------|------|----------|
| R-F1 | 前端无“对面是 AI 角色扮演实验”披露 | 01 §4.3 产品层透明要求；`frontend/src` 未检索到披露文案 | 登录/会话页显著提示（不得误导真实用户交易），合规开关可配 | P0 | ⏸ | UI 走查 + 合规评审 |
| R-F2 | 合规红线事件未记录 | `state.flags` 预留（03 §4）但未接入 | 命中红线/合规场景（涉违法、诱导、索要真实信息等）写 flags + trace，后台可见 | P1 | ⏸ | 触发后后台可见记录 |
| R-F3 | 隐私政策/条款缺失 | 无对外协议文本 | 提供用户协议与隐私说明（数据用途、不用于训练） | P1 | ⏸ | 文档评审 |

## 3. 建议实施顺序（阶段拆分，供 T-15 后续子任务）

依赖规则：**先数据（PG/Alembic），再并发与安全，再做观测与发布一致性，合规披露并行于 UI 工作。**

| 阶段 | 内容 | 依赖 | 对应缺口 | 退出标准 |
|------|------|------|----------|----------|
| M4.1 | PG 接入 + Alembic 基线迁移 + 备份/恢复演练 | — | R-B1/B2/B6 | 全量测试 PG 绿；迁移双路径验收 |
| M4.2 | 多 worker 会话写者模型 + 限流外置 | M4.1 | R-A1/A3 | 双 worker 并发压测通过 |
| M4.3 | 敏感默认值 fail-fast + 环境配置注入 + 单版本源 | — | R-C1/C4/E2/E3 | 单测 + 配置对照表 |
| M4.4 | Docker 加固 + Makefile/依赖单入口修正（CI 质量门已随 R-E1 落地） | — | R-E5/E6（R-D4 readiness 部分） | PR 门禁 + 镜像构建冒烟（CI docker job）✅ |
| M4.5 | 观测：request-id、指标、结构化日志、readiness | M4.2 | R-D1~D4 | 看板与日志样例 ✅（/api/metrics + JSON 日志 + readiness 探测） |
| M4.6 | 管理审计 + token 刷新/撤销 + 登录防爆破 | M4.3 | R-C2/C3/C5/C6 | 安全边界用例绿 |
| M4.7 | 合规披露 UI + flags 红线记录 + 隐私条款 + 删除/导出 | — | R-F1~F3/B7 | 合规评审通过 |
| M4.8 | 数据保留策略 + 游标分页 + state 迁移策略 | M4.1 | R-B5/B4/B7 | 压测与迁移演练 |
| M4.9 | v0.5 候选收口：默认 v2、双引擎回归、回滚演练、部署文档 | 上述全部 | R-E4 及全部 | 台账+部署文档，打 v0.5 tag |

## 4. 提案新增 NFR（**未冻结**，须先评审再进 01）

| ID | 提案项 | 指标/约束 | 对应缺口 |
|----|--------|-----------|----------|
| NFR-PROD-1 | 生产配置安全 | `APP_ENV=prod` 时占位 secret/空 key 启动即失败（已实现，见 R-C1） | R-C1 |
| NFR-PROD-2 | 多进程一致性 | 同一会话消息跨 worker 仍串行、不丢不乱 | R-A1 |
| NFR-PROD-3 | 质量门 | 每次合入：pytest 全绿 + ruff 0 + 前端 build + mock E2E（workflow 已多次跑绿） | R-E1 |
| NFR-PROD-4 | 关键指标可见 | LLM 调用量/延迟/失败、Guard 拦截/兜底率、每轮次数 ≤2 可看板化 | R-D2 |
| NFR-PROD-5 | 披露与合规 | 产品层透明文案上线可见；红线事件可追踪 | R-F1/F2 |

## 5. 风险登记（同步更新 04 §风险）

| ID | 风险 | 概率/影响 | 缓解 | 触发信号 |
|----|------|-----------|------|----------|
| R-10 | 占位 JWT_SECRET/空 key 直接上线 = 可伪造会话/泄露凭据 | 低/高 | fail-fast + 配置对照表（R-C1） | prod 未设置 secret |
| R-11 | 多 worker 并发覆盖会话 state（R-A1 未修前） | 中/高 | 单 worker 部署限制 + 尽快落 PG 写者模型 | 消息乱序/状态回退 |
| R-12 | 版本号漂移导致发布误判 | 中/中 | 单版本源（R-E2） | health 与 tag 不一致 |
| R-13 | SQLite 未迁移就做多进程压测，结论不可信 | 中/中 | 压测只在 PG 上进行（M4.1 前置） | 压测数据来自 SQLite |

## 6. 状态速览

- 本表为 M4 阶段一评审基线：共 31 项缺口，其中 P0 7 项（R-A1、R-B1、R-B2、R-C1、R-D2、R-E1、R-F1）。
- 已落地：R-C1 ✅、R-B3 ✅、R-B6 ✅（备份/恢复演练 PASS + 保留策略 03 §16）、R-E1 ✅（CI 多次 success）、R-E2 ✅、R-E3 ✅；M4.1：R-B1 ✅、R-B2 ✅；M4.2：R-A1 ✅、R-A3 ✅；M4.3：R-C4 ✅；M4.4：R-E5 ✅、R-E6 ✅；M4.5：R-D1 ✅、R-D2 ✅、R-D3 ✅、R-D4 ✅。
- 实施记录：M4.1 PG+Alembic（RPT-M4-003）；M4.2 跨 worker 会话锁 + Redis 限流（RPT-M4-004）；M4.3 prod CORS 校验 + env/compose 键一致（RPT-M4-005）；M4.4 Docker 加固 + Makefile/依赖单入口（RPT-M4-006）；R-B6 PG 备份/恢复演练与保留策略（RPT-M4-007）；M4.5 观测（request-id/指标/结构化日志/readiness）（RPT-M4-008）。
- 每完成一项：回填本节状态 → 06 台账登记 → 07 实施报告追加 → 更新 00/04 看板。
