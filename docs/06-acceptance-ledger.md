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
| ACC-M4-T15-007 | 工程 | CI 质量门 workflow（backend lint+test / frontend build） | 语法审阅 | 可运行 | 待 GitHub 远端验证 | .github/workflows/ci.yml | 🚧 | 2026-09-05 |
| ACC-M4-REG-001 | 单测 | 全量回归 | `pytest backend` | 93 passed | 93 passed in 2.12s | 测试输出 | ✅ | 2026-09-05 |

## 6. 后续登记区

自 M1 起，每任务完成后按 §1/§2 追加记录。模板：

```text
| ACC-<M><T>-<n> | <类型> | <验收项> | <方法> | <预期> | <结果> | <证据> | <结论> | <日期> |
```

> 禁止把“能跑一次”当验收：必须给出可复跑命令与通过标准。
