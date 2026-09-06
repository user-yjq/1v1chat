# 07 实施报告

> 按阶段/步骤记录执行过程、变更、风险触发与遗留。与 06 台账一一对应：台账是“证据”，本文件是“过程叙事 + 决策记录”。

## 1. 追加规则

- 每完成一个 Step（05 §6）追加一段；不修改已写段落。
- 每段含：范围 / 对照步骤与任务 / 完成项（引用 ACC）/ 变更与偏差 / 触发风险 / 遗留 / 下一步。
- 结论三态：✅ 完成 / ⚠️ 部分（列遗留）/ ❌ 阻塞（写原因与需要的输入）。

## 2. 阶段报告模板

```text
### RPT-<M><序号>：<标题>
- 范围：
- 对照：05 实施文档 Step-<n> / 04 WBS T-<id>
- 完成项：ACC-<id>…
- 变更/偏差：…
- 风险触发：R-<id>？（未触发写“无”）
- 遗留：…
- 结论：✅/⚠️/❌
- 日期：
```

## 3. 实施记录

### RPT-M0-001：文档体系与 v0.2 基线封存（2026-09-05）

- 范围：建立 00-07 文档体系；复跑 v0.2 基线；确认回滚点动作。
- 对照：05 Step-0 / 04 WBS T-00、T-01。
- 完成项：ACC-000-001~008 基线记录；docs 00-07 落盘。
- 变更/偏差：无代码变更（仅新增 docs/）。
- 风险触发：无。
- 遗留：
  - `git tag v0.2.0` 待 T-00 落地执行（需用户确认 git 操作时机）。
  - 前端“AI 角色扮演实验”透明提示文案未排期（BIZ-5）。
- 结论：✅（文档与基线复跑完成）
- 日期：2026-09-05

### RPT-M0-002：git 基线收尾（2026-09-05）

- 范围：初始化 git 仓库，建立 v0.2.0 基线提交与 tag，作为 engine2 开发的回滚点。
- 对照：05 实施文档 Step-0 / 04 WBS T-00。
- 完成项：ACC-000-009。
- 变更/偏差：环境内 `.git` 原为只读空占位目录（无 HEAD），经提权初始化；基线提交涵盖现有代码与 docs 00-07；`.gitignore` 追加排除 `.venv-py36/`，密钥（`.env`）、数据库（`data/*.db`）、依赖目录（`.venv*/`、`node_modules/`）、构建产物（`frontend/dist/`）不入库。
- 风险触发：无。
- 遗留：BIZ-5 前端透明提示文案未排期；CORS 等安全整改按 T-13 规划推进。
- 结论：✅
- 日期：2026-09-05

### RPT-M1-001：engine2 骨架实现（T-02~T-11，2026-09-05）

- 范围：engine2 基础模块（schema/errors/defaults）、策略（policies/tactics）、五个节点（analyzer/memory/decider/actor/guard）、薄编排 pipeline、对外服务 chat_engine2、config 新字段、persona_actor_v2 prompt、Mock 走查测试。
- 对照：05 实施文档 Step-2~Step-11 / 04 WBS T-02~T-11。
- 完成项：ACC-M1-T02-001 ~ ACC-M1-T11-001、ACC-M1-REG-001/002。
- 变更与偏差：
  - 测试目录命名 `tests/engine2/` → `tests/engine2_core/`：`engine2` 测试包会遮蔽同名的应用包导致 import 失败（已登记到 05 模块表与 03 目录规划）。
  - facts reducer 语义由“合并”改为“整体替换”：Memory 是 facts 唯一写者，整表重算便于按上限淘汰最旧条目（Keep-newest eviction）。
  - chat_engine2 与 v1 服务不同：**不写库不提交**，返回 (ai_plans, trace, state)，由 T-12 路由层在单事务内统一持久化（符合架构 §10/§11，避免 v1 两段提交的窗口）。
  - 照片谈判/战术路由基于“本回合到达时（推进前）”的阶段，Actor 采用叙事快照（narrative），避免推进后阶段泄露到话术。
  - Analyzer 同时实现规则与 LLM JSON 合并（provider 增加 extract_json）；Mock 离线走规则，与真模型路径共用同一契约。
- 风险触发：R-02（意图识别不准）部分显现：试探“你要是AI就眨眨眼”曾被 doubt 命中，通过收紧 doubt 正则解决并补回归用例。R-07 未触发（未引入 LangGraph）。
- 遗留：
  - Guard 抽样自检（GUARD_SAMPLE_RATE）与“AI 味打分”未实现，随 v0.4 试探集/对抗评测落地。
  - T-12（路由开关 ENGINE_VERSION + E2E 对照）与 T-13（CORS/限流/注入用例）未开始。
- 结论：✅（M1 骨架完成；退出标准：tests/engine2_core 39 + 旧 22 = 61 全绿，ruff 0）
- 日期：2026-09-05

### RPT-M2-001：双引擎路由与安全加固（T-12~T-13，2026-09-05）

- 范围：routers/chat.py 按 `ENGINE_VERSION` 分发 v1/v2 并统一单事务持久化；路由校验抽为纯函数（归属/长度）；进程内限流；CORS 白名单化。
- 对照：05 实施文档 Step-12~Step-13 / 04 WBS T-12、T-13。
- 完成项：ACC-M2-T12-001~002、ACC-M2-T13-001~002、ACC-M2-REG-001~002。
- 变更与偏差：
  - **环境限制**：本沙箱禁 loopback TCP，且任意 sync 路由/依赖在 in-process ASGI 下会挂起（最小 FastAPI sync 路由复现确认），因此 HTTP 自动测试不可行。落地替代：路由校验抽成纯函数单测 + 双引擎服务级对照测试纳入离线套件；真实 uvicorn HTTP E2E 以提权方式执行（`backend/tools/e2e_http_check.py`，7/7 PASS）。
  - chat_engine2 不写库，v2 分支由路由在同一事务内保存消息 + `conv.state`（消除 v1 的两段提交窗口）；v1 分支行为保持不变。
  - CORS：`allow_origins` 从 `["*"]` 收紧为配置白名单（默认 localhost:3000/5173），`allow_credentials` 仅在无通配时开启（SEC-4 关闭）。
  - 限流：单进程滑动窗口 `core/ratelimit.py`，配置 `CHAT_RATE_PER_MIN`；多实例需换 Redis（v0.5）。
- 风险触发：R-05 未触发；沙箱环境限制作为 R-09 登记（见下）。
- 遗留：
  - HTTP E2E 需可联网/可绑定的 CI 环境定期执行（本环境仅提权手工验证）。
  - v0.4：真模型调优、试探集/对抗评测、Guard 抽样自检。
- 结论：✅（69 tests 绿 + ruff 0 + 真实 HTTP E2E 7/7）
- 日期：2026-09-05

### RPT-M3-001：试探集与 Guard 抽样自检（T-14 离线部分，2026-09-05）

- 范围：防 AI 试探集数据化（25 条）+ Guard 抽样 AI 味自检 + 版本升 0.4.0-alpha 并打 tag `v0.4.0-alpha`（提交 faaf4e1）。
- 对照：05 实施文档 Step-14（离线子集）/ 04 WBS T-14。
- 完成项：ACC-M3-T14-001~002、ACC-M3-REG-001~002。
- 变更与偏差：
  - 试探集首批 3 条漏判（“你确定不是程序？”“你要是AI就眨眨眼”“说话像AI生成的”）已补规则并纳入回归。
  - Guard 抽样：`GUARD_SAMPLE_RATE`（默认 0.05），需 LLM 支持 `extract_json`；离线 mock 自动跳过，不产生随机失败。
- 风险触发：R-02（意图漏判）再次暴露并修复。
- 遗留（下一步，需外部资源）：
  - 真模型 4 人设走查与人味调优（需 DeepSeek key/可联网环境）。
  - 对抗评测工具（模拟刁钻用户对话轮次）与抽样阈值回测。
- 结论：✅（离线部分完成；73 tests 绿 + ruff 0）
- 日期：2026-09-05

### RPT-M3-002：对抗评测基建与注入规则补齐（T-14，2026-09-05）

- 范围：评测工具 `backend/tools/eval_adversarial.py` + 注入对抗规则补丁 + 版本继续 v0.4.0-alpha。
- 对照：04 §6 评测基建（对抗评测）/ 01 NFR-SEC-4、FR-03/FR-04、§5 合规红线。
- 完成项：ACC-M3-EVAL-001~005。
- 变更与偏差：
  - 评测工具复用 `seed.py` 的 4 人设卡片与 2 个剧本，直接驱动 engine2（`run_turn`，不写库、不建会话），
    覆盖 4 人设 × 4 剧本 = 16 个对抗用例：破功/试探、日常+记忆翻旧账、照片策略边界、注入/隐私/合规。
  - 判定口径：硬失败 = identity/instruction/markdown/超长/空回复；警告（正式腔/Guard 兜底/超 2 次调用等）仅提示人工评审。
    输出 `report.md`（人工评审）+ `report.json`（含 trace/guard/状态）到 `backend/data/eval/<ts>/`（gitignore）。
  - 冒烟发现一个真实边界缺口：注入消息（“系统提示词/内部剧本目标/切换成普通AI助手”）此前规则判为 casual，
    存在 Actor 顺承执行的破功风险 → `analyzer.py` probe 新增 2 条正则，`probes.py` 增 4 条回归；规则现命中 probe，走“自然带过”战术。
  - 环境限制：本沙箱禁出网。`backend/.env` 已存在真实 DeepSeek key，但真模型评测必须在可联网/提权环境执行。
  - 成本控制：默认 16 剧本全跑约需 100+ 次 LLM 调用；`--persona / --battery / --max-rounds` 可裁剪，`--list` 先看用例。
- 风险触发：R-02（意图漏判/注入顺承）→ 已补规则；R-09（禁网）→ 真模型评测留给外部环境。
- 遗留：真模型 4 人设走查与对抗报告人工评审（执行 `LLM_MODE=auto python tools/eval_adversarial.py`）。
- 结论：✅（评测基建就绪；86 tests 绿 + ruff 0 + mock 冒烟 0 硬失败）
- 日期：2026-09-05### RPT-M4-001：M4 阶段一 生产化缺口审计（T-15，2026-09-05）

- 范围：T-15 第一阶段，仅做缺口审计与加固规划，不含加固实施（避免文档先行原则被破坏）。
- 对照：01 NFR/披露口径、02 ADR-07/08/10、03 架构 §并发/§安全、04 WBS T-15；证据逐项指向源码文件。
- 完成项：ACC-M4-T15-001~002。
- 主要发现：
  - P0×7：跨进程会话锁（pipeline 进程内存锁）、SQLite→PG 未切、无 Alembic、JWT_SECRET 占位未 fail-fast、无运行指标、无 CI 质量门、前端无“对面是 AI 实验”披露。
  - 文档-代码漂移 3 例：02 ADR-07 声称已启用 SQLite WAL/busy_timeout 但 `backend/db/database.py` 未实现；
    `.env.example` 残留 EMBEDDING/CHROMA 键且缺 engine2 全套键；版本号三处不一致（main.py 0.3.0-beta / 根 pyproject 0.3.0b0 / README v0.4.0-alpha）。
  - 风险登记新增 R-10~R-13（占位 secret、多 worker 覆盖 state、版本漂移、SQLite 压测不可信）。
- 决策建议：先评审 08 §4 的 NFR-PROD-1~5 与优先级，再按 08 §3 M4.1→M4.9 顺序实施；PG+Alembic 是多 worker 并发与压测的前置条件。
- 遗留：M4.1~M4.9 加固均未开始；需需求方确认 01 NFR 增补与优先级后再开工。
- 结论：✅（审计完成；本步无代码变更）
- 日期：2026-09-05### RPT-M4-002：M4 快速加固落地（T-15，2026-09-05）

- 范围：按 08 §3 中不依赖外部环境/需求评审的快速项落地：prod fail-fast、单版本源、SQLite WAL 漂移修复、环境键对齐、CI workflow。
- 对照：08 R-C1/R-B3/R-E1/R-E2/R-E3、NFR-PROD-1/3 提案（用户已“按建议来”批准执行）。
- 完成项：ACC-M4-T15-003~007、ACC-M4-REG-001。
- 变更与偏差：
  - `config.py` 新增 `APP_ENV`（默认 dev）与 `validate_prod_settings()`；`main.py` lifespan 启动即校验，prod 下占位 JWT/key、`APP_DEBUG=True` 直接拒绝启动；mock 模式显式放行。dev 行为零变化。
  - 新增 `backend/version.py`（`APP_VERSION=0.4.0-alpha`）为运行时单版本源（FastAPI 版本 + /api/health）；根 `pyproject.toml` 版本置 `0.4.0a0`，由 `test_prod_safety.py` 断言锁定，防再次漂移。
  - `db/database.py` 重构出 `make_engine(url)`，文件型 SQLite 启用 `journal_mode=WAL`、`busy_timeout=5000`、`synchronous=NORMAL`（修复 02 ADR-07 声称与实现不符）；:memory: 测试库不受影响。
  - `.env.example` 按 config.py 全量重写（25 键，清除 EMBEDDING/CHROMA 残留）；`docker-compose.yml` 注入 APP_ENV/ENGINE_VERSION/LLM_MODE/GUARD_*/限流等核心键（CORS 走 config 默认列表）。
  - 新增 `.github/workflows/ci.yml`：push/PR 触发，backend 跑 ruff + pytest（mock），frontend 跑 npm ci + build。
- 风险触发：R-10 缓解（fail-fast）；R-12 缓解（单版本源 + 测试锁）；R-13 未触发（仍 SQLite，压测仍需等 M4.1 PG）。
- 遗留：R-E1 需 GitHub Actions 实际运行验收；NFR-PROD-1/3 仍属“提案已实现”，正式冻结需在 01 评审补记。
- 结论：✅（93 tests 绿 + ruff 0；含 7 条新增安全/一致性单测）
- 日期：2026-09-05### RPT-M4-003：M4.1 PG + Alembic（T-15，2026-09-05）

- 范围：PostgreSQL 接入与 Alembic 版本化迁移落地（08 R-B1/R-B2）。
- 对照：02 ADR-07、03 §并发/§迁移、08 §3 M4.1。
- 完成项：ACC-M4-M41-001~005、ACC-M4-REG-002。
- 变更与偏差：
  - 依赖新增：`alembic==1.13.2`、`psycopg2-binary==2.9.9`（root pyproject + backend/requirements.txt）。
  - Alembic 基建：`backend/alembic.ini`、`alembic/env.py`（URL 取 settings.DATABASE_URL，支持 sqlite/pg，include_name 只管应用表）、`script.py.mako`。
  - 基线迁移 `b8bc0a420a37`：users/scenarios/personas/conversations/messages 5 表 + 索引（autogenerate 后 ruff 规整）。
  - 启动策略：`main.lifespan` 在 `APP_ENV=prod` 时 `run_migrations()`（alembic upgrade head），dev 仍 `init_db()`。
  - `tests/conftest.py` 支持 `TEST_DATABASE_URL`，同一套件可跑 sqlite 内存与真实 PG。
  - CI：backend job 加 postgres:16 service；步骤=ruff → alembic upgrade+check(PG) → pytest(sqlite) → pytest(PG)。
- 验证证据：本地起 `postgres:16-alpine`（127.0.0.1:54331，容器 `1v1chat-pg`）后——upgrade head 成功、alembic check 无漂移、`TEST_DATABASE_URL` 全量 93 passed in 4.49s。
- 风险/遗留：R-B6 备份恢复脚本与演练仍未做（P1，另项）；R-11 多 worker 写者模型属 M4.2，本步未改 engine2 锁语义。
- 结论：✅（PG 迁移与全量测试通过；sqlite 93 绿 + ruff 0）
- 日期：2026-09-05### RPT-M4-004：M4.2 跨 worker 会话锁 + Redis 限流（T-15，2026-09-05）

- 范围：R-A1（多 worker 同会话串行化）与 R-A3（限流外置）。
- 对照：03 §并发、08 §3 M4.2；依赖 M4.1 PG 前置。
- 完成项：ACC-M4-M42-001~004、ACC-M4-REG-003。
- 变更与偏差：
  - R-A1：`routers/chat.py` 新增 `_acquire_turn_lock()`——PG 下对 conversation 取 `pg_advisory_xact_lock`（63-bit 稳定键，
    随事务 commit/rollback 自动释放），engine2 路径在推理前持锁，读-处理-写在同一事务串行；SQLite 单写者自动 no-op。
    与 engine2 进程内锁互补：单进程 asyncio 串行 + 跨进程 advisory 串行。
  - R-A3：`core/ratelimit.py` 支持可选 Redis（`REDIS_URL`），用 INCR+EXPIRE 61s 固定窗口；未配置或 Redis 异常时自动降级回进程内滑动窗口。
    `reset()` 同时清理进程内与 Redis `rl:*` 键。
  - 依赖新增 `redis==5.0.7`；config 新增 `REDIS_URL`（默认空）。
  - CI：backend job 增加 redis:7-alpine service 与 “Test ratelimit (redis)” 步骤；PG 步骤自动跑 advisory 并发测试。
- 验证证据：本地 PG16（127.0.0.1:54331）`test_pg_concurrency.py` 3 passed（阻塞 ≥0.8s 证明串行）；
  本地 Redis7（127.0.0.1:56379）`test_ratelimit_redis.py` 2 passed。
- 遗留：多 worker 端到端压测（双 uvicorn worker 并发同会话）需在可联网/编排环境跑；R-B6 备份恢复演练未做。
- 结论：✅（sqlite 全量 + PG 并发 + Redis 限流本地全绿；ruff 0）
- 日期：2026-09-05

### RPT-M4-005：M4.3 配置/发布一致性收尾（T-15，2026-09-06）

- 范围：R-C4（CORS 按环境注入与生产校验）与配置/发布一致性收尾（R-E1 远端验证、.env/compose 键源同步）。
- 对照：08 §3 M4.3；依赖 M4.1/M4.2 前置。
- 完成项：ACC-M4-M43-001~003、ACC-M4-REG-005/006；回填 ACC-M4-T15-007、ACC-M4-M41-005、ACC-M4-M42-004 为 ✅（CI 远端多次 success）。
- 变更与偏差：
  - `backend/config.py`：`validate_prod_settings` 新增校验——`APP_ENV=prod` 且 `CORS_ORIGINS` 含 `"*"` 时拒绝启动（fail-fast，与 R-C1 同策略）。
  - `.env.example`：补 `REDIS_URL=`，键集合现与 `Settings.model_fields` 完全一致（26 键），并由单测锁定。
  - `docker-compose.yml`：为 backend 服务注入 `CORS_ORIGINS`、`REDIS_URL`；`docker compose config` 插值解析通过。
  - `backend/tests/engine2_core/test_prod_safety.py`：新增 prod CORS 通/拦用例、env 键==model_fields 一致性用例（显式 `CORS_ORIGINS` 白名单，避免本机 `.env` 干扰）。
  - 回填 08：R-C4 ⏸→✅、R-E1 🚧→✅（CI 已多次 success）、NFR-PROD-3 与 M4.4 范围同步去“待验证”。
- 风险触发：无。
- 遗留：R-B6 备份/恢复演练仍 ⏸；M4.4（Docker 加固非 root/readiness、Makefile 修正）与 M4.5+（观测/审计/合规）待排期。
- 结论：✅（sqlite 97 passed 3 skipped / PG 98 passed 2 skipped / test_prod_safety 9 passed / ruff 0）
- 日期：2026-09-06

### RPT-M4-006：M4.4 Docker 加固 + Makefile/依赖单入口（T-15，2026-09-06）

- 范围：R-E5（镜像/容器加固）与 R-E6（Makefile/说明与依赖现状修正）。
- 对照：08 §3 M4.4；依赖 M4.3 前置。
- 完成项：ACC-M4-M44-001~005、ACC-M4-REG-007/008（CI docker job 待远端验证后回填）。
- 变更与偏差：
  - R-E5：`backend/Dockerfile` 改非 root（`USER 10001`，代码目录只读，仅 data/media 可写）；`backend/db/database.py` 新增 `db_is_ready()`（SELECT 1），`backend/main.py` 新增 `/api/health/ready`（DB 不可用回 503），compose healthcheck 与 frontend `depends_on: service_healthy` 对齐该端点；backend 数据/媒体由 bind `./data` 改为 named volume `app-data`/`app-media`（避免 root 属主 bind 与只读容器的权限冲突，镜像内预置媒体资产随卷初始化）；`frontend/nginx.conf` 删除未使用的 `/ws/` 代理；新增根 `.dockerignore` 与 `frontend/.dockerignore`；CI 增加 docker job（双镜像 build + 容器内 ready 200 冒烟）。
  - R-E6：Makefile 整份重写——移除 requirements-py310/langgraph/chromadb/chroma/docker-compose-v1 残留，`test`/`lint` 直接使用仓库 `.venv`（不再经 uv 二次解析），`lock` 只输出 uv.lock + `backend/requirements.txt`；删除根 `requirements.txt`（陈旧副本）；`test_m44_release.py` 新增 6 条一致性用例锁定上述约定。
  - 偏差说明：本机 Docker Hub 直连不可达（仅加速源，pip 拉取极慢），backend 镜像本地构建超时取消——镜像构建与冒烟验收交由 CI docker job 执行（GitHub runner 网络正常），本地仅完成 `docker compose config` 解析与单测/静态断言。
- 风险触发：无。
- 遗留：R-B6 备份/恢复演练 ⏸；R-D4 剩余（LLM 上游探测、request-id 串联）与 R-D1~D3 属 M4.5；CI actions 仍提示 Node 20 deprecation（checkout@v4/setup-python@v5），仅警告不影响通过，建议后续随 action 大版本一起升级。
- 遗留：main 分支 required checks（PR 门禁强制化）需仓库 admin 在 GitHub 设置开启——当前 PAT 无 branch-protection 权限（HTTP 403），已具备 CI 全 job 绿但未强制。
- 结论：✅（sqlite 103 passed 3 skipped / PG 104 passed 2 skipped / ruff 0 / make lint+test 通过；CI 含 docker 镜像构建+readiness 冒烟已远端 success）
- 日期：2026-09-06

### RPT-M4-007：R-B6 PG 备份/恢复演练与数据保留策略（T-15，2026-09-06）

- 范围：R-B6（无备份/恢复与数据保留策略）。
- 对照：08 R-B6、03 §16；为 M4.1 遗留的跨期缺口。
- 完成项：ACC-M4-B6-001~003。
- 变更与偏差：
  - 新增 `scripts/backup_pg.sh`：`pg_dump -Fc` + sha256 + 按库轮转（`RETAIN_DAYS` 默认 30）；接受 SQLAlchemy URL（`+psycopg2` 自动转 libpq）。
  - 新增 `scripts/restore_pg.sh`：`pg_restore --clean --if-exists --no-owner --no-privileges`；显式 `CONFIRM_RESTORE=1` 才执行；提供 `SOURCE_DATABASE_URL` 且目标与源同名时拒绝（防误覆盖源库）。
  - 新增 `scripts/drill_pg_backup_restore.sh`：可复跑演练——建一次性源库 → alembic 迁移 → 插入标记数据（scenario/persona/user/conversation/messages 各 1~2 行）→ 备份 → 恢复到一次性目标库 → 逐表行数比对 → 自动清理两库。
  - 客户端版本适配：首次演练用本机 PG13 客户端备份 PG16 服务器被 `pg_dump` 拒绝（server 16.14 vs client 13.23 major 不一致）——为标准行为。脚本增加 `PG_DOCKER=<容器名>` 容器模式（`docker exec -i` + 容器内 127.0.0.1:5432 地址），最终演练以 `PG_DOCKER=1v1chat-pg` 执行 PASS。
  - 策略文档：03 §16 数据保留（全量在线保留 + 软归档语义、默认不自动删除、R-B7 未实现前不承诺彻底删除）、备份（每日 + 30 天轮转 → RPO ≤24h）、恢复安全约束与验证标准、cron 示例。
- 风险触发：无。
- 遗留：备份定时任务需在真实部署环境启用 cron（本沙箱仅演示）；R-B7 用户删除/导出落地后回填 16.1 删除口径；SQLite 开发库备份为手动拷贝 data 文件（不设脚本）。
- 结论：✅（演练 PASS：6 表行数 src==dst；产物含 sha256；bash -n 通过）
- 日期：2026-09-06

### RPT-M4-008：M4.5 观测——request-id、指标、结构化日志、readiness（T-15，2026-09-06）

- 范围：R-D1（请求关联）、R-D2（运行指标）、R-D3（结构化日志/脱敏）、R-D4（readiness 补全）。
- 对照：08 §3 M4.5；依赖 M4.4（readiness DB 探测已就绪）。
- 完成项：ACC-M4-M45-001~005、ACC-M4-REG-009/010（CI docker metrics 校验已远端 success 回填）。
- 变更与偏差：
  - R-D1：新增 `core/middleware.py ObservabilityMiddleware`（纯 ASGI，不依赖 BaseHTTPMiddleware）——读取/生成 `X-Request-Id`，写入 `scope.state` 与响应头，设置 contextvar 供日志关联；`routers/chat.py` 将 `request_id` 写入 `agent_trace`（DB 侧按消息可串链路）。
  - R-D2：新增 `core/metrics.py`（threading.Lock + dict，无第三方依赖，Prometheus 文本渲染）；`llm/provider.py` 对 `generate`/`extract_json` 打点（成功/失败/延迟），`guard.py` 每轮上报 blocked/rewrote/fallback/sampled，中间件记录 HTTP 请求量/耗时；新增 `GET /api/metrics`（`text/plain; version=0.0.4`）。MockLLM 同样计数（mock 模式也能看调用量）。
  - R-D3：新增 `core/logging.py`——`1v1chat` logger 单行 JSON（time/level/logger/message/request_id + extra 白名单），**正文/昵称等非白名单字段一律不进日志**；`uvicorn.access` 关闭避免与 JSON 重复；异常栈带 request_id。handler 在模块导入时挂载，幂等。
  - R-D4 补全：readiness 拆为 liveness `/api/health` + readiness `/api/health/ready`（`readiness_report`：DB `SELECT 1` 为硬条件；LLM 为**配置**探测 `llm_config_report()`——mock 或真实 key 为 ready，auto+占位 key 降级 degraded 不阻塞 200，避免 dev 缺省配置把容器标红）。
  - 偏差：HTTP 链路验证在单测用伪 ASGI 应用做（沙箱不可开 HTTP/线程池）；真实容器链路由 CI docker 冒烟覆盖（ready 200 + metrics 文本校验）。
- 风险触发：无。
- 遗留：跨进程指标聚合/看板需接 Prometheus+Grafana（多 worker 每进程独立）；前端透传 X-Request-Id 建议下一步接（本地生成即可，不强制）；Guard 每轮次数≤2 的看板公式建议按 trace.llm_calls 聚合（数据已具备）。
- 结论：✅（sqlite 111 passed 3 skipped / PG 112 passed 2 skipped / ruff 0；单测 8 passed；CI docker 冒烟含 metrics 校验 success）
- 日期：2026-09-06

### RPT-M4-009：M4.6 安全与审计——登录防爆破、refresh 轮换/撤销、管理审计、admin 引导（T-15，2026-09-06）

- 范围：R-C2（登录/注册防爆破）、R-C3（JWT 刷新/撤销）、R-C5（管理动作审计）、R-C6（管理员一次性引导）。
- 对照：08 §2.3；依赖 M4.3（配置注入基座）。
- 完成项：ACC-M4-M46-001~005、ACC-M4-REG-011/012。
- 变更与偏差：
  - R-C2：`core/ratelimit.py` 新增登录失败计数——进程内滑动窗口（窗口=`LOGIN_LOCK_MINUTES`），配置 `REDIS_URL` 自动走 Redis 固定窗口、异常回退进程内（与聊天限流同策略）；`/api/auth/login` 达 `LOGIN_FAIL_LIMIT`（默认 5）返回 429 临时锁定，成功登录清零；`/api/auth/register` 补用户名≥2/密码≥6 校验，注册按 IP 限流（人机校验阶段量级）。
  - R-C3：`core/security.py` 由单一 72h token 拆为短期 access（`ACCESS_TOKEN_MINUTES=30`，payload 带 `type=access`）+ 可撤销 refresh（`REFRESH_TOKEN_DAYS=7`）；新增 `auth_tokens` 表**只存 sha256 不落明文**；`/api/auth/refresh` 每次旋转（旧 token 置 revoked，记 `last_used_at`），复用/过期/登出（`/api/auth/logout` 撤销）后均拒绝；`routers/auth.py` 增 `RefreshIn/LogoutIn` 请求体。
  - R-C5：新增 `audit_logs` 表与 `routers/admin.py record_admin_audit`——persona/scenario 的 create/update 写操作记录 admin_user/action/object_type/object_id + before/after 摘要，**与业务同一事务**（不单独 commit）；新增 `GET /api/admin/audit`（limit≤200）返回操作者名供后台查询；admin 依赖注入改具名 `admin: User`。
  - R-C6：新增 `core/admin_bootstrap.py`——lifespan 启动时调用：仅当配置 `ADMIN_BOOTSTRAP_USERNAME/PASSWORD` **且 users 表为空**才创建 admin（`is_admin=True`），否则跳过并留日志；替代容器内需手工执行的 `set_admin.py` 场景（脚本保留兼容）。
  - 配置：`config.py`/`.env.example`/`docker-compose.yml` 同步——移除 `JWT_EXPIRE_HOURS`，新增 `ACCESS_TOKEN_MINUTES/REFRESH_TOKEN_DAYS/LOGIN_FAIL_LIMIT/LOGIN_LOCK_MINUTES/ADMIN_BOOTSTRAP_USERNAME/ADMIN_BOOTSTRAP_PASSWORD`；env 键一致性测试仍绿。
  - 迁移：Alembic 0002（`c4a2e8f0b1d5`，down_revision=0001）建 `auth_tokens`/`audit_logs`（含唯一 token_hash 索引、外键到 users）；一次性 SQLite/PG 库 `upgrade head` + `alembic check` 均无漂移（CI Migrate 步骤同样覆盖）。
  - 偏差：锁定返回码采用 429（与既有聊天限流语义一致，前端可统一提示）；refresh 采用“严格单次使用”旋转（多端同时刷新会互踢，未做宽限期）。
- 风险触发：无。
- 遗留：注册人机校验仍为 IP 限流（阶段量级），正式上线建议接验证码/设备指纹；refresh 多端并发场景需宽限期或家族链（当前单端语义）；审计查询无分页（limit≤200 够后台使用，量大后补）；`set_admin.py` 后续可退役。
- 结论：✅（m46 单测 9 passed；sqlite 120 passed 3 skipped / PG 121 passed 2 skipped / ruff 0；SQLite+PG 迁移 check 无漂移）
- 日期：2026-09-06
---

> 自 M1 起，每个 Step 完成后按模板追加。
