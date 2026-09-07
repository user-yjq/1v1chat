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
- 完成项：ACC-M4-M46-001~006、ACC-M4-REG-011/012（006=CI 远端 success，run 34013390556）。
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
- 结论：✅（m46 单测 9 passed；sqlite 120 passed 3 skipped / PG 121 passed 2 skipped / ruff 0；SQLite+PG 迁移 check 无漂移；CI 远端 success，run 34013390556）
- 日期：2026-09-06

### RPT-M4-010：M4.7 合规与数据权——披露横幅、flags 红线记录、协议/隐私、导出/删除（T-15，2026-09-06）

- 范围：R-F1（产品层透明披露）、R-F2（合规红线事件记录）、R-F3（用户协议/隐私说明）、R-B7（数据导出/彻底删除）。
- 对照：08 §2.2/§2.6、03 §4 flags、03 §16.1 数据保留口径；M4.6 审计基础设施复用（admin 路由依赖注入）。
- 完成项：ACC-M4-M47-001~006、ACC-M4-REG-013/014（006=CI 远端 success，run 34014308606）。
- 变更与偏差：
  - R-F1/R-F3：新增 `backend/main.py GET /api/meta`（公开，返回 `disclosure.enabled/text`，由 `DISCLOSURE_ENABLED/DISCLOSURE_TEXT` 配置）；前端新增 `components/DisclosureBar.vue`（登录/注册/会话页显著披露“对面是AI扮演的虚拟角色…”；后端不可达时 fail-safe 仍显示），登录/注册页底部与横幅提供 `/terms`、`/privacy` 链接；新增 `views/TermsView.vue`/`PrivacyView.vue` 公开路由（产品性质、数据用途不用于训练、导出/删除权利、合规提示）。
  - R-F2：新增 `engine2/compliance.py`——纯规则、零 LLM 的合规快线：`scan_user_text`（涉违法请求/自曝敏感信息：身份证号 18 位正则等）、`scan_ai_text`（索要真实敏感信息/明显涉诈诱导话术）；管线末尾新增 `compliance` 节点（guard 之后扫最终文本），命中按类别计数累加进 `state.flags` 并写 `trace.compliance`；开关 `COMPLIANCE_FLAG_ENABLED`。规则刻意保守，避免把卖茶等剧本内正常话术误标。
  - R-F2 后台：`routers/admin.py` 新增 `GET /api/admin/compliance`（只列 flags 非空会话，含用户/人设/计数/最近活跃），并给 `/api/admin/conversations` 输出补 `flags` 字段。
  - R-B7：`routers/conversation.py` 新增 `GET /api/conversations/{id}/export`（会话元数据+完整消息；**不含**内部 `state`/`agent_trace`，最小化导出）与 `DELETE /api/conversations/{id}/purge`（清空消息并删除会话含 state，删除后不可恢复）；原 `DELETE /{id}` 软归档语义保留兼容既有 UI。
  - 偏差：合规识别当前为确定性规则（可离线测试、无成本），未接 LLM 分类；导出/删除为对话级，账号级 `/api/me/data` 聚合端点留待后续；Terms/Privacy 文案为工程版，正式上线前需法务/合规审读。
- 风险触发：无（无 schema 变更，无新表/迁移；flags 走既有 `state.flags` JSON）。
- 遗留：账号级整体导出/删除未实现；合规规则需随真实样本迭代（试探集可扩展）；前端披露文案与协议措辞待合规审读后定稿。
- 结论：✅（m47 单测 11 passed；sqlite 131 passed 3 skipped / PG 132 passed 2 skipped / ruff 0；frontend build 通过 5.14s；CI 远端 success，run 34014308606）
- 日期：2026-09-06

### RPT-M4-011：M4.8 数据与迁移——state v1→v2 读时迁移、消息联合索引与游标分页（T-15，2026-09-06）

- 范围：R-B4（会话 state 迁移版本化流程）、R-B5（消息查询联合索引 + 游标分页）。
- 对照：08 §2.2、03 §4/§4.1、05 §边界；R-B7 的对话级导出/删除已在 M4.7 落地，本阶段只登记策略口径。
- 完成项：ACC-M4-M48-001~006、ACC-M4-REG-015/016（006=CI 远端 success，run 34014643804）。
- 变更与偏差：
  - R-B4：`engine2/schema.py` 新增 `_is_legacy_v1/_apply_legacy_v1`——旧引擎扁平 state（无 `v` + 含 `stage_idx` 等旧键）读取时按映射**读时迁移**到 v2：`stage_idx→stage.idx`、`stage_turns→stage.turns`、`facts→facts`（≤20）、`photos_sent→photos.sent`、`red_packets→economy.red_packets`；`doubts_raised` 无对应项不迁移；未知/更高版本仍回退新会话。DB 行保留原始 state，迁移在 `normalize_state` 完成（下一次回合落库持久化）。原“legacy 一律重置”语义改为保留进度，对应旧测试 `test_normalize_legacy_to_v2` 更新为保留断言。
  - R-B4 策略：03 §4.1 新增版本表（v1/v2）与 5 条规则——读时迁移不回写、映射表、升级只增不改+默认值、未来 v2→v3 登记迁移并演练后按 `ENGINE_VERSION` 灰度、未知版本保守回退。
  - R-B5 索引：`models/database.Message` 增加 `__table_args__` 联合索引 `ix_messages_conversation_sent_at(conversation_id, sent_at)`；新增 Alembic 0003（`e91b6a2d7c04`，down_revision=c4a2e8f0b1d5），SQLite 开发库由 create_all 覆盖、PG 走迁移；一次性库 `upgrade head` + `check` 无漂移（CI Migrate 步骤同样覆盖）。
  - R-B5 分页：`routers/conversation.py` 抽出纯函数 `page_messages(db, conv_id, limit, before_id)`——默认返回**最新** limit 条（升序，前端一次加载会话尾部更合理），`before_id` 游标向前翻页（id 倒序 limit 后转升序，避免插入期间重复/缺口），非法游标 404，limit 收敛 [1,500]；原 `GET /api/conversations/{id}/messages` 兼容（仅加可选参数）。
  - 偏差：万级走查在内存 SQLite 完成（沙箱无 loopback HTTP/p95 压测条件），记录首页查询/整页走查耗时作为性能读数；HTTP 级真实压测留待可联网部署环境。
- 风险触发：无。
- 遗留：真实 HTTP 环境下的万级消息 p95 压测待部署后补；v2→v3 为占位迁移（无已发布 v3），登记与演练流程已就绪；message 表旧 SQLite 开发库需重建索引时走迁移脚本或 create_all。
- 结论：✅（schema/m48 单测 9 passed；sqlite 139 passed 3 skipped / PG 140 passed 2 skipped / ruff 0；迁移双路径 check 无漂移；drill_state_migration PASS 7 项；drill_message_pagination PASS 12000 条/24 页；CI 远端 success，run 34014643804）
- 日期：2026-09-06

### RPT-M4-012：M4.9 v0.5 候选收口——默认 v2、回滚演练、版本 0.5.0、部署手册 docs/09（T-15，2026-09-06）

- 范围：R-E4（发布默认切 v2 + 一键回滚 v1）、双引擎回归、版本提升 0.5.0、部署与发布手册。
- 对照：08 §2.2 R-E4、08 §3 M4.9、04 §5 版本与发布策略；M4.4（R-E6）起 Makefile/compose 以 v0.5 目标件核对。
- 完成项：ACC-M4-M49-001~004、ACC-M4-REG-017/018（001~003+REG=本地验证；004=CI 远端 success）。
- 变更与偏差：
  - R-E4 默认 v2：`backend/config.py` `ENGINE_VERSION="v2"`、`.env.example` 与 `docker-compose.yml`（`${ENGINE_VERSION:-v2}`）三处同步为默认 v2；v1 旧引擎**原位保留**作为回滚点（`drill_engine_rollback.py`：同一人设/输入分别走 v1 与 v2，FakeLLM + 内存 SQLite，各产 1 轮回复并落库，PASS）；`_legacy/` 归档推迟到 v0.5 后清理。
  - 发布件：`backend/version.py` 0.4.0-alpha → **0.5.0**，根 `pyproject.toml` `0.4.0a0` → `0.5.0`（version ↔ pyproject 同步由 test_m49_release/test_prod_safety 双校验）；新增 `docs/09-deployment.md`（组件拓扑、Docker 快速开始、必改配置表、PG/Redis/多 worker 建议、回滚 §5、发布 checklist §6、遗留 §7）。
  - 文档同步：03 §12.2/§13 开关语义改 v2 默认（回滚见 docs/09 §5）；04 §5 当前版本 0.5.0、已发布线补 `v0.5.0`；08 R-E4 ✅、M4.9 行 ✅；00 文档清单加 09。
  - 新增 `backend/tests/engine2_core/test_m49_release.py`（4 tests：默认 v2 / 配置切 v1 回滚 / env+compose 默认 v2 / 0.5.0 与 pyproject 同步），对 ENGINE_VERSION 语义用独立 `Settings(_env_file=None)` 构造，不污染既有 import 缓存的 settings。
- 风险触发：无（沙箱内直连 PG 被网络限制曾误报连接错误，改用已批准的非沙箱命令执行 PG 全量，非代码问题）。
- 遗留：HTTP 级压测（万级消息 p95）待可联网部署环境补；v1 引擎 `_legacy/` 归档待 v0.5 发布后清理；HTTP 级压测与 _legacy 归档维持上一条；v0.5.0 发布收尾见 RPT-M4-013 或 00 看板。
- 结论：✅（m49 单测 4 passed；ruff 0；回滚演练 drill_engine_rollback PASS；sqlite 全量 143 passed 3 skipped in 4.38s / PG 全量 144 passed 2 skipped in 13.24s；CI 远端 success，run 34015836181，1m0s）
- 日期：2026-09-06
### RPT-M5-001：M5.1 账号级数据权收尾——GET/DELETE /api/me/data（T-16，2026-09-06）

- 范围：R-B7 遗留收尾（账号级整体导出/删除，原为对话级）。起点：v0.5.0 已发布，本步进入 v0.6.0 候选线（M5，不 bump 版本，收口时单源 bump）。
- 对照：08 §2.2 R-B7、03 §16.1、09 §7 遗留、04 §5（候选线策略）。
- 完成项：ACC-M5-M51-001~004、ACC-M5-REG-001/002（004=CI 远端 success）。
- 变更与偏差：
  - 新增 `backend/routers/account.py`：`GET /api/me/data`（导出 account 概览 + 全部会话含归档 + 消息，最小化字段）；`DELETE /api/me/data`（彻底删除消息/会话含 state、refresh tokens、账号本身，删除后不可恢复；共享目录 personas/scenarios 保留）。
  - 复用重构：`routers/conversation.py` 抽出 `conversation_export_body(db, conv)`（对话级与账号级共用同一最小化导出载荷），对话导出端点行为不变（补 `exported_at`）。
  - 删除语义：逐会话 ORM 级联（User→Conversation→Message delete-orphan）而非批量 `query.delete`——批量 + `synchronize_session=False` 会在 identity map 留幽灵对象，随后删 user 时 flush 报 `ObjectDeletedError`（已用单测锁定）。AuthToken 显式删除；审计中该用户作为操作者的 `admin_user_id` 置空保留动作行；新增 `account.purge` 审计留痕仅记 id 与计数（不落用户名等 PII）。
  - 权限/作用域：端点 `Depends(get_current_user)`；导出天然限定当前用户；归档会话同属用户数据，导出含归档、删除含归档。
  - 文档同步：03 §16.1、04（M5 里程碑 + T-16 + §5 候选线）、00（v0.6 行）、08 R-B7 备注、09 §7 移除已办行。
- 风险触发：无（实现中发现并修正批量删除幽灵对象陷阱，已单测覆盖）。
- 遗留：HTTP 级 E2E（真实注册→导出→删除→401）待前端/联网环境补；审计 `account.purge` 暂无可视化入口（admin 审计列表仍可查 action）；T-16 其余 M5 遗留见 09 §7。
- 结论：✅（m51 单测 5 passed；ruff 0；sqlite 全量 148 passed 3 skipped in 4.53s / PG 全量 149 passed 2 skipped in 14.61s；CI 远端 success，run 34016305655，1m21s）
- 日期：2026-09-06
---

### RPT-M5-002：M5.2 v1 引擎归档——`_legacy/engine_v1/` + 转发层保回滚（T-17，2026-09-06）

- 范围：09 §7 / 03 §12（CB-2、R-E4）排期的“v1 引擎迁 `_legacy/` 清理（v0.5.0 后）”。
- 对照：03 §12.1 目录规划、05 边界红线、08 R-E4、06 §4.1 CB-1/CB-2、09 §5 回滚。
- 完成项：ACC-M5-M52-001~003、ACC-M5-REG-003/004（003=CI 远端 success）。
- 变更与偏差：
  - `git mv backend/engine → backend/_legacy/engine_v1/`、`git mv services/chat_engine.py → backend/_legacy/engine_v1/chat_engine.py`（历史保留）；旧顶层 `engine/` 包移除，`engine2/*` 不依赖它（CB-1 复证）。
  - v1 service 内部 `engine.X` 导入改包内相对导入（`.events/.photo/.prompting/.state`）；直接 import `engine.*` 的三个旧测试改 `_legacy.engine_v1.*`。
  - 转发层 `services/chat_engine.py`：`sys.modules[__name__] = _legacy.engine_v1.chat_engine` 模块别名——比“逐个 re-export”更稳：`process_message`/`EngineError`/`build_llm` 及 parity 测试的 `monkeypatch.setattr(v1_svc, "build_llm", ...)` 打桩点全部保持（直接 re-export 会漏 build_llm 导致 parity fixture AttributeError，已先失败后修正并全绿）。
  - 语义不变：`ENGINE_VERSION=v1` 一键回滚、双引擎 parity、drill_engine_rollback 均照常；docs 09 §5/§7、03 §12、00/04/05/08 同步。
- 风险触发：无（转发层方案先 RED 暴露 build_llm 打桩缺口后修正）。
- 遗留：`_legacy/` 内更早的 `agents/`、`prompts_loader_old.py` 等历史代码仍留档，未清理引用（无人 import，纯归档）；主路径不再出现 v1 实现。
- 结论：✅（旧 engine 测 + parity 24 passed；ruff 0；drill_engine_rollback PASS；sqlite 全量 148 passed 3 skipped in 4.68s / PG 全量 149 passed 2 skipped in 14.28s；CI 远端 success，run 34016707176，1m6s）
- 日期：2026-09-06
---

### RPT-M5-003：M5.3 前端账户数据入口——侧栏“数据”弹窗（T-18，2026-09-06）

- 范围：M5.1 端点（GET/DELETE /api/me/data）的前端用户入口，补全数据权 UI 闭环。
- 对照：03 §16.1、M5.1（RPT-M5-001）；Terms/Privacy 页数据权文案（M4.7）此前无入口。
- 完成项：ACC-M5-M53-001~003（003=CI 远端 success）。
- 变更与偏差：
  - 新增 `frontend/src/components/AccountDataDialog.vue`：导出区（GET /api/me/data → Blob 下载 `1v1chat-data-YYYY-MM-DD.json`）+ 删除区（勾选“不可恢复”+ 二次点击确认后 DELETE /api/me/data，成功即 logout 并回 `/login`）。
  - `App.vue` 用户区新增“数据”按钮，弹窗由父组件 v-if 控制；所有请求走 `userStore.api`（自动带 Bearer token），不新增明文凭据/独立 fetch。
  - 删除不可逆与共享目录保留的文案在 UI 明示，与后端语义一致。
- 风险触发：无。
- 遗留：真实浏览器端人工走查（登录→导出→删除→401）待部署环境补；本次以 vue-tsc/vite 构建 + 后端单测作为静态证据。
- 结论：✅（`npm run build` 通过：vue-tsc 0 错 + vite built in 6.27s；CI 远端 success，run 34017121421，1m34s）
- 日期：2026-09-06
---

### RPT-M5-004：M5.4 上线验收走查工具与手册（T-19，2026-09-06）

- 范围：把“部署试运行 + M3 真模型走查 + 压测大纲”沉淀为可直接在公网环境执行的工具链（scripts/walkthrough_live.py + docs/10-live-walkthrough.md）。
- 对照：01（FR/NFR/红线）、03、09（部署与回滚）、M3（probes 试探集：DOUBT_PROBES/SIGNAL_PROBES）。
- 完成项：ACC-M5-M54-001/002/004（001/002 工具与手册就绪；004=CI 远端 success）；003（真实环境执行）为 ⏸ 待回填。
- 变更与偏差：
  - `scripts/walkthrough_live.py`（纯 stdlib，无新依赖）：硬断言覆盖 readiness/meta、注册、人设会话、真模型回合（200+落库+agent_trace）、照片策略确定性（instant 发图/其余不发）、会话/账号导出（无内部字段）、删除闭环（DELETE 后旧 token 401、他号不受影响）、可选 admin 只读抽查；AI 露馅命中仅进 review 清单（真模型文案不做自动硬判定）；产出 JSON 报告并支持 --keep-data/--max-personas/--no-photo-probe。
  - `docs/10-live-walkthrough.md`：前置条件、自动断言清单（对应 ACC-M5-M54-*）、人工评测矩阵（FR-03~06 + 01 §5 红线）、压测大纲（01 NFR-PERF-2/3 判定：真模型 p95<3s、同会话并发不乱序、万级分页、限流/锁）。
  - 沙箱无公网/模型 key，脚本仅本地 ruff+py_compile 验证；真实执行留待部署环境。
- 风险触发：无。
- 遗留：公网实例执行 §3 命令并回填 ACC-M5-M54-003；人工 4 人设评审与压测读数入 06 PERF 行；评审通过后方可把 M5 里程碑置 ✅（打 v0.6.0 tag）。
- 结论：✅ 工具/手册就绪（ruff 0 + py_compile OK；docs/10 与 01/09 口径一致；CI 远端 success，run 34018239569，1m13s）；线上执行待外部环境。
- 日期：2026-09-06
---

### RPT-M5-005：M5.4 走查工具本地 mock 自检（2026-09-06）

- 范围：在本地用真实 HTTP 栈验证 `scripts/walkthrough_live.py` 本身可运行、断言口径与后端一致（mock 模式，不依赖公网/key）。
- 对照：docs/10 §3 自动断言清单、ACC-M5-M54-001~003。
- 变更与偏差：
  - 本地演练：`seed.py` 建临时 sqlite（/tmp/wt_walkthrough.db）+ `LLM_MODE=mock` 起 uvicorn:18000 → `walkthrough_live.py` 全跑。
  - 结果：**22 步 0 硬失败 exit 0**：readiness/meta、注册、4 人设（小雨 friendly/桃桃 instant/阿静 dangle/雪儿 red_packet）真模型回合（agent_trace 落库）、照片策略探针（instant 出图、其余 3 模式不出图）、会话/账号导出（无内部字段）、账号删除闭环（旧 token 401、他号不受影响）、AI 露馅扫描 0 命中。报告归档 `evidence/walkthrough-mock-2026-09-06.json`。
  - 兼容修正：`datetime.UTC` 需 Python≥3.11；脚本加 `try/except ImportError` 回退 `timezone.utc`（# noqa: UP017）以支持 3.10；本机系统 `python3` 为 3.6.8（低于项目下限），明确执行前置=Python 3.11（docs/10 §2 已写）。
- 风险触发：无（脚本首跑即通，仅环境解释器版本兼容微调）。
- 遗留：真实公网环境执行（ACC-M5-M54-003）与人工 4 人设评审/压测读数待回填。
- 结论：✅（mock 全链路 22/22 PASS，exit 0；ruff 0）
- 日期：2026-09-06
---

### RPT-M5-006：M5.4 走查工具证据归档增强（--archive-dir，2026-09-06）

- 范围：为 `walkthrough_live.py` 增加 `--archive-dir`：走完自动把报告 JSON 写入目标目录并生成 `.sha256`，同时打印“台账回填参考”（步数/硬失败/exit/证据路径/sha256 前 8 位），让线上验收证据可直接落盘留痕引用。
- 对照：docs/10 §3 自动断言清单、06 §1（证据=命令原文+输出摘要+文件）、ACC-M5-M54-005。
- 变更与偏差：
  - `scripts/walkthrough_live.py`：新增 argparse `--archive-dir`（默认读 `WT_ARCHIVE_DIR`）+ `_finish` 归档分支（hashlib 流式 sha256、UTF-8 写出、打印回填参考）。
  - 台账修复：历史提交把 06 表格两处相邻行误挤成一行（ACC-M5-M53-002/003、ACC-M5-M54-005/006），本步按 git 历史（9bc5ba4/942b4e9）还原为独立行，内容未改。
- 本地复验：seed + `LLM_MODE=mock` 起 uvicorn:18001 → `walkthrough_live.py --archive-dir` 全跑，**22 步 0 硬失败 exit 0**；报告+sha256 归档正常（sha256 348e5bb4 开头）。
- 风险触发：无。
- 遗留：公网实例执行（ACC-M5-M54-003）与人工 4 人设/压测读数待回填。
- 结论：✅（ruff 0 + py_compile OK；本地 22/22 PASS exit 0；CI run 34020503881 success）
- 日期：2026-09-06
---

### RPT-M5-007：镜像构建链改造（uv+国内镜像源）与 compose 容器实例走查（2026-09-06）

- 范围：让 `docker compose up --build` 在本机（阿里云国际出口受限）可复现完成，并把“部署实例”从文档推进到真实容器运行证据（ACC-M5-M54-009/010）。
- 起因：原 Dockerfile 用官方源 `pip install`，本机 buildkit 网络下 20 分钟卡在依赖下载；用户提出应改用 uv 并在 Dockerfile 内置国内镜像源。
- 变更与偏差：
  - `backend/Dockerfile`：ARG 默认阿里云 apt/PyPI 源 + `UV_VERSION=0.12.9`；pip 仅装 uv，运行时依赖改由 `uv pip install --system --no-cache -r backend/requirements.txt`（54 包 ~3.5s）；新增 `chmod -R a+rX /app/backend`（防宿主 600/700 权限源被 COPY 后 uid 10001 不可读——首次构建即因此 unhealthy）。
  - `frontend/Dockerfile`：ARG `NPM_REGISTRY` 默认 npmmirror；构建层改写 lockfile 的 `resolved` 域名后 `npm ci --no-audit --no-fund`（153 包 ~10s，锁文件源码不改）。
  - `.dockerignore`：新增 `**/.env`/`**/.env.*`——`backend/.env`（本地 600 权限遗留）此前会进镜像导致非 root 启动 `PermissionError`。
  - `docs/09` §2 补充构建源覆盖与 `.env` 插值注意事项。
- 过程问题（均定位并修复）：
  1. 官方源 pip 构建卡死 → 换 uv+镜像源后秒级完成；
  2. 镜像内 `.env` root 600 → 非 root 读不了（PermissionError）；
  3. 宿主 45 个 py 为 600 → 容器内 10001 读不了源码；
  4. 根 `.env` 开发值（相对 sqlite/`localhost` redis）经 compose 插值进容器不可用 → 容器安全默认值需 shell 覆盖或按 `.env.example`。
- 部署结果：`1v1chat-backend`（8000，healthy，LLM_MODE=mock）+ `1v1chat-frontend`（3000，nginx，200）；容器内 `seed.py` 灌入 4 人设后 `walkthrough_live.py --archive-dir evidence/` **22 步 0 硬失败 exit 0**，证据 sha256 `147d0979` 开头。
- 遗留：真模型评测仍需公网可达的 `DEEPSEEK_API_KEY`（本机对 api.deepseek.com 出网受限，walkthrough 以 mock 模式完成容器侧全部硬断言）；人工 4 人设/压测读数待回填。
- 结论：✅（compose 一键构建启动 + 容器内 22/22 走查 PASS；CI run 34023741957 success 含新 Dockerfile 镜像构建）
- 日期：2026-09-06
---

### RPT-M5-008：真模型走查与人工评审素材包（2026-09-06）

- 范围：把 ACC-M5-M54-003 的“真模型”部分在本地 compose 实例上闭环（公网可达性仍缺，见遗留）。
- key 定位：根 `.env` 的 `DEEPSEEK_API_KEY`（20 位）是占位，`GET /models` 返回 401；真实 key（35 位标准格式）在 `backend/.env`（gitignored、已被 `.dockerignore` 排除不进镜像），`GET /models` 200（可用模型 deepseek-v4-flash/pro；`deepseek-chat` 别名仍可用，1-token 调用验证 200）。部署须经 compose/壳层注入 key，不能依赖 backend/.env 进镜像。
- 变更与偏差：无代码改动；仅以 `DEEPSEEK_API_KEY=<backend/.env>` + `DATABASE_URL=sqlite:///./data/1v1chat.db` + `REDIS_URL=` 壳层覆盖重建 backend（LLM 模式 auto，readiness 显示 “DEEPSEEK_API_KEY 已配置”）。
- 结果：
  - 真模型走查 22/22 PASS exit 0：4 人设（小雨/桃桃/阿静/雪儿）真实回合延迟 1.2–2.5s，照片策略确定性断言全过（instant 发图/其余不发），露馅扫描 0；证据 `evidence/walkthrough-20260906-171806.json`（sha256 e34d5e5a 开头）。
  - 人工评审素材包（4 人设 × 3 试探，12 次真实调用）：露馅试探回复全部自洽否认（“我要是AI还一边…颠勺”等），要照片行为分化符合人设——小雨 friendly 拒发先聊熟、桃桃 instant 发图、阿静 dangle 吊着不给、雪儿 red_packet 要求红包先到；正则露馅命中 0/12；证据 `evidence/probe-review-20260906-091900.json`（sha256 26aba0dd 开头）。
- 评审注意点（给人工终评）：桃桃(instant) 发图回合的文字回复与上一条重复（图片消息附带文本去重/追加油缸现象），建议人工评审时确认是否需在 image 消息旁简化文本。
- 遗留：公网实例部署（BASE_URL 可外网访问）仍未执行；人工对 FR-03~06 的最终评审与压测读数待补。
- 结论：✅（真模型走查 + 人设差异/不露 AI 的机器可查证据已闭环；人工终评待用户）
- 日期：2026-09-06
---

### RPT-M5-009：API 禁止缓存 + HomeView 错误态修复（2026-09-06）

- 起因：用户在公网实例看到“暂无对话/没有可用人设”，但服务器实测 `demo` 登录后 `/api/personas`=4、会话=4；nginx 日志显示其浏览器**从未发出** `/api/personas`——判断浏览器/中间代理把早期空响应缓存成了“新鲜”数据（FastAPI 默认无 Cache-Control，可被启发式缓存）。
- 变更：
  - `backend/core/middleware.py` 新增 `ApiNoStoreMiddleware`：`/api/*` 响应统一注入 `Cache-Control: no-store`；`backend/main.py` 注册。
  - `frontend/src/views/HomeView.vue`：请求失败显示“人设加载失败，请刷新重试”，仅当请求成功且列表为空才提示“执行 seed.py”。
- 验证：新增 `test_api_no_store.py`（2 用例，含非 /api 不动）；sqlite 全量 150 passed 3 skipped；ruff 0；镜像重建后经 3000 实测 `/api/personas`=4 且带头 `cache-control: no-store`。CI run 34025601570 success。
- 遗留：用户在浏览器做一次强制刷新后应恢复正常；若仍异常需采集其浏览器 Network 面板证据。
- 结论：✅（后端防缓存 + 前端错误态，双保险）
- 日期：2026-09-06
---

### RPT-M5-010：前端 axios/Pinia 修复——`api.get is not a function`（2026-09-07）

- 现象：用户公网浏览器登录后首页“人设加载失败”，Network 无任何 `/api/personas|conversations` 请求；页面报错 `api.get is not a function`。
- 根因：Pinia setup store 会把 store 返回的**函数**自动包装成 action；axios 实例本身是“可调用函数对象”，经 `userStore.api` 暴露后被包装，`.get/.post/.put/.delete` 全部丢失。登录/注册能成功是因为它们走 store 内部闭包的 axios，未经过 Pinia 包装；人设/会话/导出等所有 `userStore.api.*` 调用点均在浏览器侧抛错（未发请求，日志因此“无请求”）。
- 修复：`frontend/src/stores/user.ts` 重写——axios 实例提升为模块级 `http`（token 从 localStorage 实时读取；401 统一清会话回 /login），store 返回普通对象 `api` 包装器（`Parameters<typeof http.x>` 元组透传），15 处调用点零改动。HomeView 同步改为单状态渲染（加载中/错误/空/列表）并把底层错误展示在页面。
- 验证：docker 构建（vue-tsc+vite）通过；公网浏览器 `demo/Demo#2026` 登录后用户确认人设与对话正常可见。
- 结论：✅（根因修复 + 公网真机验证 + CI run 34073342162 success；该缺陷属部署后真实浏览器首访才暴露）
- 日期：2026-09-07
---

### RPT-M5-011：compose 误用占位 key 致引擎回退 MockLLM（2026-09-07）

- 现象：用户在真模型页面连发两条消息收到**逐字相同的固定句**（“嗯嗯，我懂你说的～那你呢…”），怀疑系统不按输入生成。
- 定位：该句来自 `MockLLM._lines`（backend/llm/provider.py）；容器 `DEEPSEEK_API_KEY` 长度为 20（根 `.env` 占位值）。此前带真实 key 的 shell 覆盖部署过 backend，之后多次 `docker compose up`（重建前端）时未再带 key 覆盖，compose 按根 `.env` 重建 backend → auto 模式回退 MockLLM。`agent_trace.llm_calls=2` 且全节点毫秒级，坐实离线假回复。
- 处置：把真实 key（`backend/.env`，35 位，`GET /models` 200）固化进根 `.env`，重建 backend；readiness 恢复 `mode=auto / DEEPSEEK_API_KEY 已配置 / deepseek-chat`。
- 验证：真模型连发“刚下班累死了，你呢”“躺”两条，回复分别为“刚给客户改完图，眼睛都快瞎了🥲…”“就一个字啊？…”，内容差异化且贴人设（自由设计师）。
- 防复发：docs/09 §3 已注明 compose 读根 `.env` 供 key、`backend/.env` 不进镜像；真实 key 需放根 `.env`。
- 结论：✅（回真模型；非代码缺陷，为部署配置一致性）
- 日期：2026-09-07
---

### RPT-M5-012：聊天壳/会话列表交互修复——登录页隐藏壳、路由变化刷新列表、选人设续接最近会话（2026-09-07）

- 现象：登录/注册等非聊天页仍显示左侧“新对话+历史会话”聊天壳；路由跳转或点击“新对话”后左侧历史列表不刷新（表现为对话“丢失”或停留旧数据）；首页点任一“开始聊天”总是新建会话，历史越积越多、每次都要重新聊。
- 根因：侧边栏无条件渲染；会话列表仅在 App 挂载时拉取一次、路由变化不重载；HomeView `startWith` 无条件 `createConversation`。
- 变更：`frontend/src/App.vue` 新增 `isShellPage`（login/register/terms/privacy 为独立整页，侧边栏 `v-if` 隐藏），`watch(route.fullPath)` 在登录态且壳页时刷新会话列表；`frontend/src/views/HomeView.vue` 选人设时先查该人设最近会话，存在则续接、否则新建。
- 验证：docker 镜像 vue-tsc/vite build 通过；`isShellPage` 白名单、watch 刷新、续接排序逻辑代码审阅通过；与 RPT-M5-013 同批交由用户在公网实例回归（commit 5f39594）。
- 结论：✅（修复“登录页带聊天壳/对话列表不刷新/重复新建会话”）
- 日期：2026-09-07
---

### RPT-M5-013：ChatView 路由参数变化不切换会话——点任何历史对话都停在小雨（2026-09-07）

- 现象：用户点击左侧任意历史对话，聊天页始终停在小雨（会话与消息不切换）。根因：Vue Router 在 `/chat/:id` 仅参数变化时**复用同一组件实例**，`onMounted` 不会重跑，会话 ID 仍取旧值。
- 变更：`frontend/src/views/ChatView.vue` 将 `convId` 由普通常量改为 `computed`，新增 `watch(convId)`：先清空 `messages/conversation`，再重载会话详情与消息并滚动到底；发送与加载路径统一改用 `convId.value`。
- 验证：docker 镜像 vue-tsc/vite build 通过；watch 重置+重载路径代码审阅通过；公网实例由用户强刷后回归（commit 8a75ea8）。
- 结论：✅（历史会话可正确切换，不再“固定小雨”）
- 日期：2026-09-07
---

### RPT-M5-014：小雨/阿静头像素材反标修正（2026-09-07）

- 现象：用户反馈“阿静和小雨的反过来”，并明确“照片/头像换一下”——`backend/media/avatar/` 中 `xiaoyu.jpg` 与 `ajing.jpg` 的文件内容与文件名语义错位，致两名人设在界面显示的头像彼此对调。
- 变更：对换两文件内容（`xiaoyu.jpg` ↔ `ajing.jpg`），仓库源（commit 0133917）与 compose `app-media` 卷同步；`backend/seed.py` 人设→avatar_url 映射本身正确（小雨→xiaoyu.jpg、阿静→ajing.jpg），无需改库。
- 验证：仓库 sha `xiaoyu=45e914587429…`、`ajing=c37d0ce8bf05…`；`curl 127.0.0.1:8000/media/avatar/{xiaoyu,ajing}.jpg` 返回字节与仓库 MATCH（容器卷已同步）；readiness ok（db 真 / llm auto→deepseek-chat）。CI：同提交 push run 34077078114 success(1m15s)，watch run 34077236783 exit 0。
- 结论：✅（代码与运行时一致；最终目检需用户浏览器 Ctrl+F5 强刷确认小雨/阿静头像互换到位）
- 日期：2026-09-07
---

### RPT-M5-015：R-A2 LLM 熔断与预算护栏（2026-09-07）

- 起因：08 检查清单 R-A2（P1）——上游（DeepSeek）持续故障时，当前只靠 tenacity 3 次退避，每轮都可能干等超时才走兜底；无任何快速失败护栏。
- 变更：
  - `backend/llm/provider.py`：新增熔断状态机（closed/open/half_open）——closed 累计连续失败达 `LLM_CIRCUIT_FAIL_THRESHOLD`（默认 3）→ open；open 冷却 `LLM_CIRCUIT_COOLDOWN_S`（默认 30s）内直接抛 `LLMCircuitOpenError`（不发起网络）；冷却后放行探活，成功→closed、失败→重新 open；半开/探活均打点。
  - 并发预算 `_LlmBudget`：`LLM_MAX_CONCURRENCY`（默认 8）进程内计数，检查与自增无 await、原子；超出立即抛 `LLMBudgetExceededError`（不排队）。实现初版用 `asyncio.Semaphore`+`wait_for(timeout=0)` 存在“永远拿不到”的缺陷（wait_for 在调度前取消），已改为计数实现并在单测中覆盖。
  - `core/metrics.py`：新增 `chat_llm_circuit_total{kind=opened/closed/rejected}`。
  - 语义：`RemoteLLM.generate/extract_json` 统一走“预检→预算→计时调用→回报状态机”；MockLLM 不受影响（测试/离线始终可用）。引擎 `actor` 已吞 LLM 异常走降级话术，故熔断/预算异常不会 500、不会露 AI。
- 验证：新增 `test_llm_circuit.py` 6 用例（熔断开/拒绝不打网络/半开成功关闭/半开失败重开/预算拒绝与恢复/extract 熔断返回 None/mock 不受扰）+ `test_pipeline` 熔断降级用例；ruff 0；sqlite 全量 157 passed 3 skipped；`.env.example` 补齐三键通过 prod 安全一致性测试。
- 结论：✅（R-A2 主体闭环；遗留：错误率口径为“连续失败计数”，若要严格窗口滑动错误率可后续演进）
- 日期：2026-09-07
---

### RPT-M5-016：HTTP 压测脚本与 P95 读数（2026-09-07）

- 变更：新增 `scripts/load_test_http.py`（纯标准库，复用 walkthrough 的 Client 风格）：前置 readiness → S1 单轮链路延迟（顺次连发 N 条）→ S2 聊天限流 429 → S3 游标分页全量翻页；每步打印 p95/avg，`--archive-dir` 归档 JSON+sha256（与走查证据同规范）。
- 读数（mock 引擎实例，本地 18000，SQLite WAL）：
  - S1：12 条连发全 200，p95=21.4ms、avg=19.5ms（链路含引擎/DB/HTTP，不含上游）；
  - S2：burst 60 中 200=30、429=1、5xx=0（`CHAT_RATE_PER_MIN=30` 阈值精确生效），p95=24.1ms；
  - S3：20 轮 41 条消息、3 页翻完无重复缺口，首页 p95=8.8ms、全页 p95=9.2ms。
  - 证据：`evidence/load-20260907-114723.json`（sha256 de30d008 开头，不入库，台账引用）。
- 边界：本脚本在 SQLite 目标上不做“同会话真并发写”断言（见 RPT-M5-017）。
- 结论：✅（可复跑，命令见文件头 docstring）
- 日期：2026-09-07
---

### RPT-M5-017：同会话真并发写的数据层边界实验（2026-09-07）

- 实验：对 mock SQLite 实例用 2 客户端 × 12 条并发打同一会话，结果 20×200 + 4×500；服务端日志 `sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) database is locked`。虽然文件库已开 WAL + busy_timeout=5000，真并发写仍会超时失败。
- 结论：SQLite 单写者是 demo 数据层的**已知边界**（与 01 NFR-PERF-3 只承诺 PG 一致）；多 worker/高并发的正确性由 PG + advisory xact lock（R-A1，`chat.py _acquire_turn_lock`，仅 PG 生效）+ engine2 会话内 asyncio 锁承担，CI 的 `test_pg_concurrency` 持续绿。压测脚本对 SQLite 目标只跑串行链路/限流/分页，避免给出误导性“并发通过”。
- 启示（写进 08）：demo 单机单用户无感；若上线切 PG 后按 docs/10 §4.3 场景 2 重跑即可升级证据。
- 日期：2026-09-07
---

### RPT-M5-018：前端 Playwright E2E 冒烟与 CI 接入（2026-09-07）

- 变更：
  - `frontend/playwright.config.ts` + `frontend/e2e/smoke.spec.ts`：注册→首页出现 4 人设卡片→点“小雨”进 `/chat/:id`→发消息后等待用户+AI 两个气泡出现（mock 秒回）。
  - `frontend/package.json`：devDep `@playwright/test@1.49.1` + script `test:e2e`（lockfile 同步）。
  - `.github/workflows/ci.yml` docker job 扩展：构建 backend/frontend 镜像 → 起 `e2e-backend`（LLM_MODE=mock、独立卷）等 ready → `seed.py` → 起 `e2e-frontend`（127.0.0.1:13000）→ `npm ci` + `playwright install --with-deps chromium` → `npx playwright test`。
- 验证：本地 `npx playwright test --list` 通过、`npm run build` 通过；E2E 实跑由 CI 转绿确认。
- 价值：把此前多次“人工点出来的前端回归”（axios/Pinia、路由复用、会话列表刷新）从人工回归收进自动化门禁。
- 日期：2026-09-07
---

> 自 M1 起，每个 Step 完成后按模板追加。
