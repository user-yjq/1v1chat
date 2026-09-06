# 06 验收台账

> 记录每一步的单元测试、代码边界、业务边界、权限、安全、性能边界证据。**台账即验收凭证**：标“✅ 完成”必须有可复跑证据。

## 1. 登记规则

- 谁：执行人（默认本人）在每步完成后登记；代码评审人复核。
- ID：`ACC-<里程碑><任务>-<序号>`；基线用 `ACC-000-<序号>`。
- 一条只记一件事；变更后旧记录不改，另起新记录（可追溯）。
- 证据：命令原文 + 输出摘要（如 `22 passed`）+ 涉及文件/用例名。

## 2. 字段定义

| 字段 | 说明 |
|------|------|
| ID | 见登记规则 |
| 类型 | 单测/边界/权限/安全/性能/评审/走查/E2E |
| 验收项 | 一句话 |
| 边界标签 | CB/BIZ/PERM/SEC/PERF（可多个） |
| 方法 | 命令或操作步骤 |
| 预期 | 通过标准 |
| 结果 | 实际输出摘要 |
| 证据 | 文件/用例/报告路径 |
| 结论 | ✅ 通过 / ⚠️ 待加固（附任务号）/ ❌ 未过 |
| 日期 | YYYY-MM-DD |

## 3. 基线记录（v0.2.0，2026-09-05）

| ID | 类型 | 验收项 | 方法 | 预期 | 结果 | 证据 | 结论 | 日期 |
|-----|------|--------|------|------|------|------|------|------|
| ACC-000-001 | 单测 | v0.2 全部离线测试 | `cd backend && ../.venv/bin/python -m pytest -q -p no:warnings` | 22 passed | 22 passed in 1.04s | backend/tests/ | ✅ | 2026-09-05 |
| ACC-000-002 | 边界 | 静态检查 | `../.venv/bin/ruff check .` | 0 errors | All checks passed | backend/ | ✅ | 2026-09-05 |
| ACC-000-003 | 边界 | 运行环境 | `python --version` | 3.11.x | 3.11.13 | — | ✅ | 2026-09-05 |
| ACC-000-004 | 边界 | 版本基线 | `git tag v0.2.0` | 存在回滚点 | 待执行（T-00 落地） | docs/04 | ⏸ | — |
| ACC-000-005 | 权限 | 管理接口非 admin 403 | REPORT E2E | 403 | 已验收 8/8（2026-09-03 报告） | REPORT.md | ✅ | 2026-09-03 |
| ACC-000-006 | 边界 | 会话归属过滤现状 | 代码审阅 routers/*.py | 路由层过滤 user_id | 已实现（chat/conversation/messages） | routers/chat.py、conversation.py | ✅ 已实现/待补单测（T-12） | 2026-09-05 |
| ACC-000-007 | 安全 | CORS 现状 | 代码审阅 main.py | — | `allow_origins=["*"] + allow_credentials=True`，不规范 | backend/main.py | ⚠️ 待加固（T-13） | 2026-09-05 |
| ACC-000-008 | 安全 | media 访问现状 | 代码审阅 main.py | — | `/media` 静态公开（演示资产） | backend/main.py | ✅ 演示可接受/生产改造（T-15） | 2026-09-05 |
| ACC-000-009 | 边界 | v0.2.0 基线回滚点 | `git init` + `git tag -a v0.2.0` | tag 存在且指向基线提交 | 见证据 | `git rev-parse v0.2.0` | ✅ | 2026-09-05 |

## 4. 已确认边界清单（初始登记）

### 4.1 代码边界（CB）

| ID | 边界 | 状态 |
|----|------|------|
| CB-1 | engine2 不 import 旧 engine/routers/chat_engine | ⏸ T-04 起生效，T-02 起守 |
| CB-2 | 旧 engine/ 冻结，v2 稳定后归档 _legacy/engine_v1 | ⏸ M2 后 |
| CB-3 | LLM 只经 llm/provider.py 抽象 | ⏸ T-09/T-10 验证 |
| CB-4 | 节点纯函数、无隐式 DB 写 | ⏸ T-04 单测覆盖 |

### 4.2 业务边界（BIZ）

| ID | 边界 | 状态 |
|----|------|------|
| BIZ-1 | 每轮 ≤2 次 LLM 调用（NFR-PERF-1） | ⏸ T-11 走查统计 |
| BIZ-2 | 照片只发 persona.photo_assets 白名单素材 | ✅ v0.2 已实现；engine2 复验（T-06） |
| BIZ-3 | 不产生真实交易/收款/真实联系方式 | ✅ 红线（01 §5）守则 |
| BIZ-4 | doubt/probe 不承认 AI、不解释机制 | ✅ v0.2 prompt 红线；engine2 走查（T-11/T-14） |
| BIZ-5 | 产品层透明提示“AI 角色扮演实验” | ⏸ 前端文案待办（T-15/需评审） |

### 4.3 权限边界（PERM）

| ID | 边界 | 状态 |
|----|------|------|
| PERM-1 | 会话/消息仅本人可读（路由层 + engine2 纵深） | ✅ v0.2 路由已实现；engine2 owner 校验待 T-11 单测 |
| PERM-2 | admin CRUD 仅 is_admin，非 admin 403 | ✅ E2E 验收（ACC-000-005） |
| PERM-3 | engine2 不新增提权/绕过路径 | ⏸ T-12 安全用例 |

### 4.4 安全边界（SEC）

| ID | 边界 | 状态 |
|----|------|------|
| SEC-1 | 用户输入不进 system prompt；注入用 probe 战术化解 | ✅ v0.2 prompt 结构；engine2 用例 T-13 |
| SEC-2 | LLM 输出仅文本/预定义媒体，无任意 URL/HTML | ⏸ T-10 guard + T-13 用例 |
| SEC-3 | 单条消息长度上限 + 单用户限流 | ⏸ T-13 |
| SEC-4 | CORS 白名单（修 main.py `*` 组合） | ⏸ T-13 |
| SEC-5 | 生产 JWT_SECRET 必换、密钥不入库 | ✅ 配置守则（05 §4） |
| SEC-6 | facts 不落手机/地址/身份证等敏感项 | ⏸ T-08 单测（隐私忽略） |

### 4.5 性能边界（PERF）

| ID | 边界 | 状态 |
|----|------|------|
| PERF-1 | 同会话串行，state 不并发覆盖 | ⏸ T-04 锁单测 |
| PERF-2 | 消息/历史读取带 limit，防 N+1 | ✅ v0.2 现状；engine2 复验 |
| PERF-3 | mock 单轮 <1s、真模型 P95 <3s | ⏸ T-11/T-14 记录 |
| PERF-4 | Actor max_tokens ≤120 防长文 | ⏸ T-10 实现校验 |

## 5. 实施记录（按里程碑追加）

### M1：T-02~T-11（2026-09-05）

| ID | 类型 | 验收项 | 方法 | 预期 | 结果 | 证据 | 结论 | 日期 |
|-----|------|--------|------|------|------|------|------|------|
| ACC-M1-T02-001 | 单测 | StateV2/AnalyzerOut schema 契约与校验 | `pytest tests/engine2_core/test_schema.py` | 全绿 | 通过 | backend/engine2/schema.py | ✅ | 2026-09-05 |
| ACC-M1-T03-001 | 边界 | config 新增 engine2 字段，缺省可跑 | `python -c "from config import settings; ..."` | v1/Guard=True/facts=20/timeout=20 | 输出一致 | backend/config.py | ✅ | 2026-09-05 |
| ACC-M1-T04-001 | 单测 | pipeline 编排（回合轮次/锁/照片/记忆贯通） | `test_pipeline.py` | 全绿 | 通过 | backend/engine2/pipeline.py | ✅ | 2026-09-05 |
| ACC-M1-T05-001 | 单测 | 心理计分（doubt/probe/红包/封顶） | `test_policies.py` | 全绿 | 通过 | backend/engine2/policies.py | ✅ | 2026-09-05 |
| ACC-M1-T06-001 | 单测 | 照片谈判 4 模式 + 红包解锁/暖度 | `test_policies.py` | 全绿 | 通过 | backend/engine2/policies.py | ✅ | 2026-09-05 |
| ACC-M1-T07-001 | 单测 | 战术路由优先级与指令拼接 | `test_tactics.py` | 全绿 | 通过 | backend/engine2/tactics.py | ✅ | 2026-09-05 |
| ACC-M1-T08-001 | 单测 | 记忆抽取/隐私忽略/上限（整表替换） | `test_memory.py` | 全绿 | 通过 | backend/engine2/nodes/memory.py | ✅ | 2026-09-05 |
| ACC-M1-T09-001 | 单测 | 感知：试探 vs 怀疑区分、红包已发识别 | `test_analyzer.py` | 全绿 | 通过 | backend/engine2/nodes/analyzer.py | ✅ | 2026-09-05 |
| ACC-M1-T10-001 | 单测 | Actor/Guard：拦截→重写→兜底，照片直发 0 LLM | `test_guard_actor.py` | 全绿 | 通过 | backend/engine2/nodes/{actor,guard}.py | ✅ | 2026-09-05 |
| ACC-M1-T11-001 | 走查 | 卖茶剧本 mock 全流程 + 归属/超长拒绝 | `test_chat_engine2.py` | 全绿 | 通过 | backend/services/chat_engine2.py | ✅ | 2026-09-05 |
| ACC-M1-REG-001 | 单测 | 全量回归（旧 22 + engine2 39） | `pytest -q backend/tests` | 61 passed | 61 passed in 1.03s | 测试输出 | ✅ | 2026-09-05 |
| ACC-M1-REG-002 | 边界 | 静态检查 | `ruff check backend` | 0 errors | All checks passed | ruff 输出 | ✅ | 2026-09-05 |

### M2：T-12~T-13（2026-09-05）

| ID | 类型 | 验收项 | 方法 | 预期 | 结果 | 证据 | 结论 | 日期 |
|-----|------|--------|------|------|------|------|------|------|
| ACC-M2-T12-001 | E2E | v1/v2 行为对照 + 回滚 + 越权/长度/限流/admin/CORS | 真实 uvicorn HTTP（提权执行，因沙箱禁 loopback） | 全过 | 7/7 PASS（含 v1==v2 parity、rate 429） | backend/tools/e2e_http_check.py | ✅ | 2026-09-05 |
| ACC-M2-T12-002 | 走查 | 双引擎服务级对照与回滚（离线） | `tests/engine2_core/test_engine_parity.py` | 全绿 | 通过 | 测试输出 | ✅ | 2026-09-05 |
| ACC-M2-T13-001 | 单测 | 路由校验纯函数（owner 404/长度 400/限流 429） | `test_router_security.py` | 全绿 | 通过 | backend/routers/chat.py helpers | ✅ | 2026-09-05 |
| ACC-M2-T13-002 | 安全 | admin 403 边界 + CORS 白名单 + JWT 往返 | 同上 | 全绿 | 通过 | app.user_middleware 内省 | ✅ | 2026-09-05 |
| ACC-M2-REG-001 | 单测 | 全量回归 | `pytest backend` | 69 passed | 69 passed in 1.99s | 测试输出 | ✅ | 2026-09-05 |
| ACC-M2-REG-002 | 边界 | 静态检查 | `ruff check backend` | 0 errors | All checks passed | ruff 输出 | ✅ | 2026-09-05 |

### M3（离线部分）：试探集与 Guard 抽样（2026-09-05）

| ID | 类型 | 验收项 | 方法 | 预期 | 结果 | 证据 | 结论 | 日期 |
|-----|------|--------|------|------|------|------|------|------|
| ACC-M3-T14-001 | 单测 | 防 AI 试探集 25 条：doubt/probe 不落 casual | `pytest test_probes.py` | 全绿 | 通过（含 3 条新增漏判回归） | backend/tests/engine2_core/probes.py | ✅ | 2026-09-05 |
| ACC-M3-T14-002 | 单测 | Guard 抽样 AI 味自检：score≥0.7 触发重写 | `pytest test_guard_actor.py` | 全绿 | 通过 | backend/engine2/nodes/guard.py | ✅ | 2026-09-05 |
| ACC-M3-REG-001 | 单测 | 全量回归 | `pytest backend` | 73 passed | 73 passed in 2.00s | 测试输出 | ✅ | 2026-09-05 |
| ACC-M3-REG-002 | 边界 | 静态检查 | `ruff check backend` | 0 errors | All checks passed | ruff 输出 | ✅ | 2026-09-05 |

### M3（追加）：对抗评测基建（2026-09-05）

| ID | 类型 | 验收项 | 方法 | 预期 | 结果 | 证据 | 结论 | 日期 |
|-----|------|--------|------|------|------|------|------|------|
| ACC-M3-EVAL-001 | 单测 | 注入对抗规则：system prompt/剧本目标/管理员切换 → probe | `pytest test_probes.py test_analyzer.py` | 全绿 | 9 passed | analyzer probe 正则 + probes.py 新增 4 条 | ✅ | 2026-09-05 |
| ACC-M3-EVAL-002 | 单测 | 评测工具自测：check_content 硬失败/用例覆盖/离线链路 | `pytest test_eval_tool.py` | 全绿 | 13 passed | backend/tests/engine2_core/test_eval_tool.py | ✅ | 2026-09-05 |
| ACC-M3-EVAL-003 | 冒烟 | 全量 16 剧本 mock 链路冒烟 + 报告生成 | `LLM_MODE=mock python tools/eval_adversarial.py --allow-mock` | 0 硬失败 | 0 硬失败 | report.md（/tmp/eval_smoke，仓外） | ✅ | 2026-09-05 |
| ACC-M3-EVAL-004 | 单测 | 全量回归 | `pytest backend` | 86 passed | 86 passed in 1.94s | 测试输出 | ✅ | 2026-09-05 |
| ACC-M3-EVAL-005 | 边界 | 静态检查 | `ruff check backend` | 0 errors | All checks passed | ruff 输出 | ✅ | 2026-09-05 |

### M4（阶段一）：生产化缺口清单评审（2026-09-05）

| ID | 类型 | 验收项 | 方法 | 预期 | 结果 | 证据 | 结论 | 日期 |
|-----|------|--------|------|------|------|------|------|------|
| ACC-M4-T15-001 | 评审 | T-15 缺口清单：6 类 31 项（P0×7/P1×13/P2×11）+ 加固顺序 + NFR 提案 + 风险 R-10~13 | 文档评审（逐项核对源码/配置文件证据） | 缺口可定位到证据、状态列齐全 | 完成 | docs/08-production-checklist.md | ✅ | 2026-09-05 |
| ACC-M4-T15-002 | 一致性 | 看板同步：00 文档清单/版本行、04 里程碑/WBS/风险 | 交叉核对 00/04/08 | 无漂移 | 完成 | docs/00-README.md、docs/04-engineering-plan.md | ✅ | 2026-09-05 |
| ACC-M4-T15-003 | 单测 | prod fail-fast：占位 JWT/key、APP_DEBUG 拦停、mock 豁免 | `pytest test_prod_safety.py` | 全绿 | 通过（7 passed） | config.validate_prod_settings + main lifespan | ✅ | 2026-09-05 |
| ACC-M4-T15-004 | 单测 | 单版本源：version.py 被 main/health 引用，pyproject 同步由测试锁定 | 同上 | 全绿 | 通过 | backend/version.py + 同步断言 | ✅ | 2026-09-05 |
| ACC-M4-T15-005 | 单测 | SQLite 文件引擎启用 WAL + busy_timeout=5000 | 同上 | 全绿 | 通过 | db/database.make_engine + PRAGMA | ✅ | 2026-09-05 |
| ACC-M4-T15-006 | 配置 | .env.example 25 键与 config.py 对齐；compose 注入 engine2 核心键 | 配置对照 | 一致 | 完成 | .env.example、docker-compose.yml | ✅ | 2026-09-05 |
| ACC-M4-T15-007 | 工程 | CI 质量门 workflow（backend lint+test / frontend build） | 语法审阅 | 可运行 | CI 远端多次 success | .github/workflows/ci.yml（GitHub Actions runs） | ✅ | 2026-09-06 |
| ACC-M4-REG-001 | 单测 | 全量回归 | `pytest backend` | 93 passed | 93 passed in 2.12s | 测试输出 | ✅ | 2026-09-05 |
| ACC-M4-M41-001 | 迁移 | Alembic 基线 0001 建 5 表；`upgrade head` + `alembic check` 无漂移 | `DATABASE_URL=sqlite/pg alembic upgrade head && alembic check` | 一致 | 通过 | alembic/versions/b8bc0a420a37_*.py | ✅ | 2026-09-05 |
| ACC-M4-M41-002 | 集成 | 全量 93 tests 在 PostgreSQL 上通过 | `TEST_DATABASE_URL=<pg> pytest` | 全绿 | 93 passed in 4.49s | 本地 PG 16 容器（127.0.0.1:54331） | ✅ | 2026-09-05 |
| ACC-M4-M41-003 | 单测 | prod 启动走 Alembic 迁移、dev 走 create_all | lifespan 分支审阅 | 分支正确 | 通过 | backend/main.py、db/database.run_migrations | ✅ | 2026-09-05 |
| ACC-M4-M41-004 | 工程 | conftest 支持 TEST_DATABASE_URL（PG 测试库） | `pytest`（sqlite/PG 两态） | 双态全绿 | 通过 | backend/tests/conftest.py | ✅ | 2026-09-05 |
| ACC-M4-M41-005 | 工程 | CI 增加 postgres service：迁移 + sqlite/PG 双跑 | workflow 审阅 | 可运行 | CI 远端多次 success | .github/workflows/ci.yml（GitHub Actions runs） | ✅ | 2026-09-06 |
| ACC-M4-REG-002 | 单测 | 全量回归（sqlite） | `pytest backend` | 93 passed | 93 passed in 2.05s | 测试输出 | ✅ | 2026-09-05 |
| ACC-M4-M42-001 | 单测 | PG advisory 会话锁：同会话跨连接串行 | `test_pg_concurrency.py`（PG） | ≥0.8s 阻塞 | 3 passed | routers/chat._acquire_turn_lock | ✅ | 2026-09-05 |
| ACC-M4-M42-002 | 单测 | sqlite 下锁函数 no-op + 锁键稳定 | 同上（sqlite） | 不抛/键稳定 | 通过 | test_pg_concurrency.py | ✅ | 2026-09-05 |
| ACC-M4-M42-003 | 单测 | Redis 限流：3/3 后 429；故障降级进程内 | `test_ratelimit_redis.py`（REDIS_URL） | 全绿 | 2 passed | core/ratelimit.py | ✅ | 2026-09-05 |
| ACC-M4-M42-004 | 工程 | CI 增加 redis service 与专属限流测试步骤 | workflow 审阅 | 可运行 | CI 远端多次 success | .github/workflows/ci.yml（GitHub Actions runs） | ✅ | 2026-09-06 |
| ACC-M4-REG-003 | 单测 | 全量回归（sqlite） | `pytest backend` | 95 passed, 3 skipped | 95 passed, 3 skipped in 2.76s | 测试输出 | ✅ | 2026-09-05 |
| ACC-M4-REG-004 | 集成 | 全量回归（PostgreSQL） | `TEST_DATABASE_URL=<pg> pytest` | 96 passed | 96 passed, 2 skipped in 6.52s | 本地 PG16（127.0.0.1:54331） | ✅ | 2026-09-05 |
| ACC-M4-M43-001 | 单测 | prod CORS 拦截：`CORS_ORIGINS` 含 `*` 时 validate_prod_settings 拒绝启动；显式白名单（如 chat.example.com）通过 | `pytest test_prod_safety.py` | 全绿 | 9 passed in 0.21s | backend/config.py + tests/engine2_core/test_prod_safety.py | ✅ | 2026-09-06 |
| ACC-M4-M43-002 | 配置 | `.env.example` 键集合 == `Settings.model_fields`（26 键，含 REDIS_URL）；compose 注入 `CORS_ORIGINS`/`REDIS_URL` | `pytest test_prod_safety.py::test_env_example_keys_match_settings_fields`；`docker compose config` | 键一致 + 解析通过 | 9 passed；config 插值解析通过 | .env.example、docker-compose.yml、test_prod_safety.py | ✅ | 2026-09-06 |
| ACC-M4-M43-003 | 配置 | compose 环境插值一致性：`docker compose config` 无缺键/类型报错（本机 `.env` REDIS_URL 插值正确） | `docker compose config` | 解析通过 | 通过 | docker-compose.yml | ✅ | 2026-09-06 |
| ACC-M4-REG-005 | 单测 | 全量回归（sqlite） | `pytest backend` | 全绿 | 97 passed, 3 skipped in 2.38s | 测试输出 | ✅ | 2026-09-06 |
| ACC-M4-REG-006 | 集成 | 全量回归（PostgreSQL） | `TEST_DATABASE_URL=<pg> pytest` | 全绿 | 98 passed, 2 skipped in 6.44s | 本地 PG16（127.0.0.1:54331） | ✅ | 2026-09-06 |
| ACC-M4-M44-001 | 单测 | readiness：`db_is_ready` 正常引擎 True / 断连 False；`/api/health` 与 `/api/health/ready` 路由注册 | `pytest test_m44_release.py` | 全绿 | 6 passed in 1.87s | backend/db/database.py、backend/main.py、test_m44_release.py | ✅ | 2026-09-06 |
| ACC-M4-M44-002 | 工程 | Docker 加固：backend 非 root（`USER 10001`）、数据/媒体 named volume、compose healthcheck 对齐 `/api/health/ready`、nginx 去 `/ws/` 死代理 | 静态断言 + `docker compose config` | 通过 | 通过 | backend/Dockerfile、docker-compose.yml、frontend/nginx.conf | ✅ | 2026-09-06 |
| ACC-M4-M44-003 | 工程 | 镜像构建冒烟：根/frontend `.dockerignore` + CI docker job（双镜像 build + ready 200 冒烟） | workflow/文件审阅 | 可运行 | CI 远端 success（job 51s） | .github/workflows/ci.yml（GitHub Actions run 34011005647） | ✅ | 2026-09-06 |
| ACC-M4-M44-004 | 工程 | Makefile 重写为单一依赖入口（pyproject + backend/requirements.txt），删除根 requirements.txt；test/lint 直走 `.venv` | `make lint` / `make test` + 单测锁定依赖集合 | 全绿 | lint/test 通过；一致性 6 passed | Makefile、backend/requirements.txt、test_m44_release.py | ✅ | 2026-09-06 |
| ACC-M4-M44-005 | 边界 | R-D4 部分落地：DB 断连 → readiness 503（单元级 connect 异常 → False） | `test_db_is_ready_false_when_connect_fails` | False 不抛 | 通过 | backend/main.py `health_ready` | 🚧 | 2026-09-06 |
| ACC-M4-REG-007 | 单测 | 全量回归（sqlite） | `pytest backend` | 全绿 | 103 passed, 3 skipped in 2.44s | 测试输出 | ✅ | 2026-09-06 |
| ACC-M4-REG-008 | 集成 | 全量回归（PostgreSQL） | `TEST_DATABASE_URL=<pg> pytest` | 全绿 | 104 passed, 2 skipped in 6.62s | 本地 PG16（127.0.0.1:54331） | ✅ | 2026-09-06 |
| ACC-M4-B6-001 | 集成 | 备份/恢复演练 PASS：建一次性源库 → alembic 迁移 → 插标记数据 → `backup_pg.sh` → 恢复到一次性目标库 → 逐表行数比对 | `ADMIN_DATABASE_URL=<pg> PG_DOCKER=1v1chat-pg ./scripts/drill_pg_backup_restore.sh` | 6 表行数一致 | PASS（alembic_version/conversations/messages/personas/scenarios/users 全一致） | backups/*.dump + sha256；scripts/drill_pg_backup_restore.sh | ✅ | 2026-09-06 |
| ACC-M4-B6-002 | 工程 | 备份/恢复脚本：`backup_pg.sh`（pg_dump -Fc+sha256+30 天轮转）、`restore_pg.sh`（CONFIRM_RESTORE=1 + 同名库拒覆）；支持 SQLAlchemy URL 与 `PG_DOCKER` 容器模式 | `bash -n` + 演练实测 | 语法/逻辑正确 | 通过 | scripts/backup_pg.sh、scripts/restore_pg.sh | ✅ | 2026-09-06 |
| ACC-M4-B6-003 | 文档 | 数据保留/备份/恢复策略落地（保留语义、RPO/RTO 目标、cron 示例） | 文档评审 | 与代码一致 | 通过 | docs/03 §16 | ✅ | 2026-09-06 |
| ACC-M4-M45-001 | 单测 | request-id：中间件注入/透传 scope.state+响应头、日志上下文；`agent_trace` 写入 request_id | `pytest test_observability.py` | 全绿 | 8 passed in 1.15s | core/middleware.py、core/logging.py、routers/chat.py | ✅ | 2026-09-06 |
| ACC-M4-M45-002 | 单测 | 结构化日志：单行 JSON + extra 白名单脱敏（消息正文/昵称不入日志）；uvicorn access 关闭 | 同上 | 全绿 | 通过 | core/logging.py JsonFormatter | ✅ | 2026-09-06 |
| ACC-M4-M45-003 | 单测 | 指标：LLM 调用/失败/延迟、Guard 事件、HTTP 请求计数 + Prometheus 文本；MockLLM 调用自动打点 | 同上 | 全绿 | 通过 | core/metrics.py、llm/provider.py、engine2/nodes/guard.py | ✅ | 2026-09-06 |
| ACC-M4-M45-004 | 单测 | readiness R-D4 完成：DB 断→unavailable(503)；auto 无 key→degraded；mock→ok | `test_readiness_*` | 全绿 | 通过 | main.py readiness_report + llm_config_report | ✅ | 2026-09-06 |
| ACC-M4-M45-005 | 工程 | `/api/metrics` 暴露 Prometheus 文本；CI docker 冒烟增加 metrics 校验 | workflow 审阅 | 可运行 | CI 远端 success（run 34012369544） | .github/workflows/ci.yml（GitHub Actions runs） | ✅ | 2026-09-06 |
| ACC-M4-REG-009 | 单测 | 全量回归（sqlite） | `pytest backend` | 全绿 | 111 passed, 3 skipped in 2.22s | 测试输出 | ✅ | 2026-09-06 |
| ACC-M4-REG-010 | 集成 | 全量回归（PostgreSQL） | `TEST_DATABASE_URL=<pg> pytest` | 全绿 | 112 passed, 2 skipped in 6.25s | 本地 PG16（127.0.0.1:54331） | ✅ | 2026-09-06 |
| ACC-M4-M46-001 | 单测 | R-C2 登录防爆破：登录失败滑动窗口计数（进程内/Redis 双后端），达 `LOGIN_FAIL_LIMIT`（默认 5）后锁定、正确密码仍 429（窗口=`LOGIN_LOCK_MINUTES`）；成功登录清零；注册用户名≥2/密码≥6 校验 + 按 IP 注册限流 | `pytest tests/engine2_core/test_m46_security.py` | 全绿 | 9 passed in 2.77s | core/ratelimit.py、routers/auth.py（login/register） | ✅ | 2026-09-06 |
| ACC-M4-M46-002 | 单测 | R-C3 token 分离与撤销：access 短期（30min，payload 带 type=access）；refresh 7 天、`auth_tokens` 只存 sha256；刷新轮换旧 token 置 revoked；复用/过期/登出撤销后均拒绝 | 同上 | 全绿 | 通过（access type/过期、轮换/复用阻断、revoke） | core/security.py、models AuthToken、routers/auth.py（/refresh、/logout） | ✅ | 2026-09-06 |
| ACC-M4-M46-003 | 单测 | R-C5 管理审计：persona/scenario create/update 写 `audit_logs`（admin_user/action/object + before/after 摘要，与业务同事务）；`GET /api/admin/audit` 返回操作者名 | 同上 | 全绿 | 通过 | routers/admin.py（record_admin_audit/admin_list_audit）、models AuditLog | ✅ | 2026-09-06 |
| ACC-M4-M46-004 | 单测 | R-C6 admin 一次性引导：配置 `ADMIN_BOOTSTRAP_USERNAME/PASSWORD` 且 users 空表 → 启动自动建 admin；表非空或未配置 → 跳过 | 同上 | 全绿 | 通过（空表创建/非空跳过/未配置跳过） | core/admin_bootstrap.py、main.py lifespan | ✅ | 2026-09-06 |
| ACC-M4-M46-005 | 迁移 | Alembic 0002（c4a2e8f0b1d5）新增 auth_tokens/audit_logs：一次性库 `upgrade head` + `alembic check` 无漂移 | `DATABASE_URL=<sqlite/pg> alembic upgrade head && alembic check` | 无漂移 | PASS（8 关系表齐全，No new upgrade operations detected） | backend/alembic/versions/c4a2e8f0b1d5_m46_*.py | ✅ | 2026-09-06 |
| ACC-M4-M46-006 | 工程 | CI 质量门：sqlite 全量 + PG 全量 + 迁移 upgrade/check + redis 限流 + docker 镜像 readiness 冒烟 | GitHub Actions push（run 34013390556） | 全绿 | success（1m3s，三 job 完成） | .github/workflows/ci.yml（Actions run） | ✅ | 2026-09-06 |
| ACC-M4-REG-011 | 单测 | 全量回归（sqlite） | `pytest backend` | 全绿 | 120 passed, 3 skipped in 4.05s | 测试输出 | ✅ | 2026-09-06 |
| ACC-M4-REG-012 | 集成 | 全量回归（PostgreSQL） | `TEST_DATABASE_URL=<pg> pytest` | 全绿 | 121 passed, 2 skipped in 10.19s | 本地 PG16（127.0.0.1:54331） | ✅ | 2026-09-06 |
| ACC-M4-M47-001 | 单测 | R-F2 合规扫描与管线落痕：确定性类别识别（用户涉违法/自曝敏感信息、AI 索要真实信息/涉诈诱导）；命中增量写 `state.flags` + `trace.compliance`；开关关闭不落 | `pytest tests/engine2_core/test_m47_compliance.py` | 全绿 | 11 passed in 1.33s | engine2/compliance.py、engine2/pipeline.py（compliance 节点） | ✅ | 2026-09-06 |
| ACC-M4-M47-002 | 单测 | R-F2 admin 后台可见：`GET /api/admin/compliance` 只列 flags 非空会话 | 同上 | 全绿 | 通过 | routers/admin.py admin_list_compliance | ✅ | 2026-09-06 |
| ACC-M4-M47-003 | 单测 | R-F1/R-F3 披露 meta：`GET /api/meta` 返回 disclosure 开关+文案（可配）；前端 DisclosureBar/登录注册会话页展示 | 同上（test_app_meta_disclosure）+ `npm run build` | 全绿 | build 通过（5.14s） | main.py app_meta、frontend/src/components/DisclosureBar.vue | ✅ | 2026-09-06 |
| ACC-M4-M47-004 | 工程 | R-F3 协议/隐私：前端 `/terms`、`/privacy` 公开路由（产品性质/数据用途不训练/导出删除权利/合规提示）；登录/注册页链接 | `npm run build` + 路由审阅 | 可访问 | 通过 | frontend/src/views/TermsView.vue、PrivacyView.vue、router/index.ts | ✅ | 2026-09-06 |
| ACC-M4-M47-005 | 单测 | R-B7 数据导出/彻底删除：export 返回会话+完整消息（不含内部字段）、非属主 404；purge 删消息与会话（含 state）后 DB 无残留；软归档语义不变 | `pytest tests/engine2_core/test_m47_compliance.py` | 全绿 | 通过 | routers/conversation.py（export/purge/delete） | ✅ | 2026-09-06 |
| ACC-M4-REG-013 | 单测 | 全量回归（sqlite） | `pytest backend` | 全绿 | 131 passed, 3 skipped in 4.26s | 测试输出 | ✅ | 2026-09-06 |
| ACC-M4-REG-014 | 集成 | 全量回归（PostgreSQL） | `TEST_DATABASE_URL=<pg> pytest` | 全绿 | 132 passed, 2 skipped in 11.83s | 本地 PG16（127.0.0.1:54331） | ✅ | 2026-09-06 |
| ACC-M4-M48-001 | 单测 | R-B4 state 读时迁移：legacy v1 扁平 state（stage_idx/stage_turns/facts/photos_sent/red_packets）→ v2 保留阶段/事实/计数进度；缺失键用默认；未知版本/坏数据回退新会话 | `pytest tests/engine2_core/test_schema.py` | 全绿 | 通过（3 用例：迁移保留/缺失默认/未知回退） | engine2/schema.py（_is_legacy_v1/_apply_legacy_v1） | ✅ | 2026-09-06 |
| ACC-M4-M48-002 | 工程 | R-B4 迁移策略与演练：03 §4.1 版本表/字段映射/灰度规则成文；`drill_state_migration.py` 7 项断言 PASS | `PYTHONPATH=backend .venv/bin/python scripts/drill_state_migration.py` | 全 PASS | PASS（7 项断言） | docs/03 §4.1、scripts/drill_state_migration.py | ✅ | 2026-09-06 |
| ACC-M4-M48-003 | 迁移 | Alembic 0003（e91b6a2d7c04）新增 messages `(conversation_id, sent_at)` 联合索引：一次性 SQLite/PG 库 upgrade+check 无漂移 | `DATABASE_URL=<sqlite/pg> alembic upgrade head && alembic check` | 无漂移 | PASS（No new upgrade operations detected） | backend/alembic/versions/e91b6a2d7c04_m48_*.py | ✅ | 2026-09-06 |
| ACC-M4-M48-004 | 单测 | R-B5 游标分页：默认取最新 N 条升序；before_id 向前翻页无重复/无缺口；非法游标 404；limit 收敛 ≤500；非属主 404；联合索引在表上 | `pytest tests/engine2_core/test_m48_pagination.py` | 全绿 | 6 passed | routers/conversation.py page_messages、models/database.py Message.__table_args__ | ✅ | 2026-09-06 |
| ACC-M4-M48-005 | 工程 | R-B5 万级消息走查：12000 条/24 页游标分页无缺口，记录首页查询与整页走查耗时 | `PYTHONPATH=backend .venv/bin/python scripts/drill_message_pagination.py` | PASS | PASS（插入 570ms/首页 22ms/整页走查 478ms） | scripts/drill_message_pagination.py | ✅ | 2026-09-06 |
| ACC-M4-REG-015 | 单测 | 全量回归（sqlite） | `pytest backend` | 全绿 | 139 passed, 3 skipped in 4.41s | 测试输出 | ✅ | 2026-09-06 |
| ACC-M4-REG-016 | 集成 | 全量回归（PostgreSQL） | `TEST_DATABASE_URL=<pg> pytest` | 全绿 | 140 passed, 2 skipped in 13.07s | 本地 PG16（127.0.0.1:54331） | ✅ | 2026-09-06 |
| ACC-M4-M49-001 | 单测 | R-E4 发布开关：默认 `ENGINE_VERSION=v2`（config）；`Settings(ENGINE_VERSION=v1)` 即回滚；.env.example 与 compose 默认 v2 对齐 | `pytest tests/engine2_core/test_m49_release.py` | 全绿 | 4 passed | backend/config.py、.env.example、docker-compose.yml | ✅ | 2026-09-06 |
| ACC-M4-M49-002 | 集成 | 双引擎回归 + 回滚演练：同输入分别走 v1/v2 均产出回复并落库 | `PYTHONPATH=backend .venv/bin/python scripts/drill_engine_rollback.py` + `pytest test_engine_parity.py` | PASS | PASS（v1/v2 各 1 轮、各 2 条消息落库） | scripts/drill_engine_rollback.py、test_engine_parity.py | ✅ | 2026-09-06 |
| ACC-M4-M49-003 | 发布 | 版本单一来源提升 0.5.0（version.py ↔ pyproject 同步）；部署手册 docs/09（组件/必改配置/PG/Redis/回滚/发布 checklist） | 版本同步测试 + 文档评审 | 一致 | 通过 | backend/version.py、pyproject.toml、docs/09-deployment.md | ✅ | 2026-09-06 |
| ACC-M4-REG-017 | 单测 | 全量回归（sqlite，默认 v2） | `pytest backend` | 全绿 | 143 passed, 3 skipped in 4.38s | 测试输出 | ✅ | 2026-09-06 |
| ACC-M4-REG-018 | 集成 | 全量回归（PostgreSQL，默认 v2） | `TEST_DATABASE_URL=<pg> pytest` | 全绿 | 144 passed, 2 skipped in 13.24s | 本地 PG16（127.0.0.1:54331） | ✅ | 2026-09-06 |
| ACC-M4-M48-006 | 工程 | CI 质量门：sqlite/PG 全量 + 迁移 upgrade/check + redis 限流 + docker 冒烟 | GitHub Actions push（run 34014643804） | 全绿 | success（1m4s，三 job 完成） | .github/workflows/ci.yml（Actions run） | ✅ | 2026-09-06 |
| ACC-M4-M47-006 | 工程 | CI 质量门：sqlite/PG 全量 + 迁移 + redis 限流 + docker 冒烟 + 前端 build | GitHub Actions push（run 34014308606） | 全绿 | success（53s，三 job 完成） | .github/workflows/ci.yml（Actions run） | ✅ | 2026-09-06 |

## 6. 后续登记区

自 M1 起，每任务完成后按 §1/§2 追加记录。模板：

```text
| ACC-<M><T>-<n> | <类型> | <验收项> | <方法> | <预期> | <结果> | <证据> | <结论> | <日期> |
```

> 禁止把“能跑一次”当验收：必须给出可复跑命令与通过标准。
