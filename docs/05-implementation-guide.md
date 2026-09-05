# 05 实施文档（开发流程与分步执行）

> 本文把 04 的任务卡变成**可执行的分步规范**：每步有输入/动作/产出/验收命令，并定义 DoD 与边界自检。开发严格按 Step 顺序推进，每步完成后登记 06 台账并追加 07 报告。

## 1. 通用流程（每步循环）

```text
读任务卡/边界 → 写测试(红) → 最小实现(绿) → 全量回归 → 台账登记 → 报告追加 → 提交
```

任何一步卡住 >2 次尝试：停下来写问题到 07，不硬解、不绕测试。

## 2. DoD（Definition of Done）

满足全部才算完成：

1. `cd backend && ../.venv/bin/python -m pytest -q -p no:warnings` 全绿（含新增与旧测试）；
2. `../.venv/bin/ruff check .` 0 errors；
3. 新逻辑有对应单测/用例，且先红后绿可追溯；
4. 边界自检清单（§7）全过或已登记“待加固”项并带任务号；
5. 06 台账新增 ≥1 条记录（含证据）；07 报告追加执行记录；
6. 无死代码/注释掉的代码/未使用的配置残留。

## 3. Git / 提交规范

- 分支：`feat/engine2-<task>`（如 `feat/engine2-T05`），完成后合入 `main`。
- 提交信息：`<task>: <一句话>`（如 `T05: 心理计分纯函数与边界测试`）。
- `main` 只合已过 DoD 的代码；tag 只在里程碑（M0..M4）打。
- 不做：直接提交 main、提交带 .env/密钥、一条提交塞多个任务。
- M0 先打 `git tag v0.2.0` 作为回滚点（T-00 完成）。

## 4. 编码规范

- 风格：遵循 `pyproject.toml`（ruff E/F/I/B/UP/N，line-length 110）；新代码不破坏 `ruff check`。
- 类型：全部 public 函数写类型注解；Pydantic 用于 schema 校验（AnalyzerOut/StateV2）。
- 纯函数：节点/策略无隐式 IO；DB 只在 services 编排层访问；不写模块级可变状态。
- 异常：`engine2/errors.py` 定义 `Engine2Error`；节点只抛领域异常，由编排层统一转 HTTP（502）。
- 日志：模块级 `logger`，关键节点记录 `turn_id + node + ms + ok`；禁止 print 残留。
- 配置：一律走 `settings`；新增项进 03 §12.2；密钥不入代码/测试。
- 注释：中文注释说明“为什么”；接口说明用 docstring；不写废话注释。

## 5. 模块拆分与职责表

| 模块/文件 | 职责 | 依赖方向 | 测试文件 |
|-----------|------|----------|----------|
| `engine2/schema.py` | TurnContext/StatePatch/StateV2/AnalyzerOut | models, pydantic | `tests/engine2/test_schema.py` |
| `engine2/errors.py` | 异常层级 | 无 | 随用随测 |
| `engine2/pipeline.py` | 锁/顺序/超时/降级/patch 合并 | schema, nodes | `test_pipeline.py` |
| `engine2/policies.py` | 心理计分/照片谈判/阶段机 | schema | `test_policies.py` |
| `engine2/tactics.py` | 战术注册表（指令/动作白名单） | schema | `test_tactics.py` |
| `engine2/nodes/analyzer.py` | 结构输出 + 正则降级 | schema, llm, policies | `test_analyzer.py` |
| `engine2/nodes/memory.py` | facts 抽取/裁剪/隐私忽略 | schema | `test_memory.py` |
| `engine2/nodes/decider.py` | 计分更新 + 路由 | schema, policies, tactics | `test_decider.py` |
| `engine2/nodes/actor.py` | persona_actor_v2 生成 | schema, llm | `test_actor.py` |
| `engine2/nodes/guard.py` | 黑名单/重写/抽样/合规快线 | schema, llm | `test_guard.py` |
| `services/chat_engine2.py` | 对外编排服务（签名对齐 v1） | engine2, db | `test_chat_engine2.py` |
| `routers/chat.py` | 按 ENGINE_VERSION 分发（v0.3 末期改） | services | E2E |

边界红线：

- `engine2/*` 不 import `engine/*`、`routers/*`、`services/chat_engine.py`。
- 旧 `engine/*` 与 `chat_engine.py` **冻结**：v1 切换前不改；切 v2 稳定后整体归档 `_legacy/engine_v1/`。
- LLM 调用只经 `llm/provider.py` 抽象；节点不得直接 httpx。

## 6. 分步执行清单（对应 04 WBS）

| 步骤 | 任务 | 输入 | 动作 | 产出 | 验收命令/动作 |
|------|------|------|------|------|----------------|
| Step-0 | T-00 | v0.2 仓库 | git tag v0.2.0；复跑测试 | 回滚点 + 基线记录 | pytest 22 / ruff 0 |
| Step-1 | T-01 | docs 00-04 | 评审并定稿 | 评审记录（07） | 文档交叉一致 |
| Step-2 | T-02 | 01/03 | 写 AnalyzerOut/StateV2 与校验测试 | schema.py | `test_schema.py` 绿 |
| Step-3 | T-03 | 02 | config 加字段；mock 缺省可跑 | settings 字段 | 冒烟启动 `/api/health` |
| Step-4 | T-04 | T-02/03 | pipeline 骨架 | pipeline.py | `test_pipeline.py`（锁/超时） |
| Step-5 | T-05 | T-04 | 心理计分纯函数 | policies.py | `test_policies.py` |
| Step-6 | T-06 | T-05 | 照片谈判（4 模式+软化） | policies.py | `test_policies.py` 扩展 |
| Step-7 | T-07 | T-06 | tactics + Decider 路由 | tactics.py/nodes/decider.py | `test_decider.py` |
| Step-8 | T-08 | T-04 | Memory 抽取/裁剪 | nodes/memory.py | `test_memory.py` |
| Step-9 | T-09 | T-04 | Analyzer 正则+降级（LLM 桩） | nodes/analyzer.py | `test_analyzer.py` |
| Step-10 | T-10 | T-07/08/09 | Actor + Guard | nodes/actor.py, guard.py | mock 全链路单测 |
| Step-11 | T-11 | T-10 | chat_engine2 + 卖茶走查 | services/chat_engine2.py | `test_chat_engine2.py` + 走查 |
| Step-12 | T-12 | T-11 | 路由开关 + E2E 对照 | routers/chat.py | uvicorn E2E v1/v2 |
| Step-13 | T-13 | T-12 | 安全整改（CORS/限流/长度/注入） | routers + tests | 安全用例绿 |
| Step-14 | T-14 | T-13 | 真模型调优 + 评测 | persona_actor_v2 + 试探集 | 评测记录入 06/07 |
| Step-15 | T-15 | T-14 | 生产化清单实施 | 队列/网关/迁移/观测 | 压测与部署验收 |

## 7. 每步边界自检清单

提交前逐条过：

| 类别 | 自检问题 |
|------|----------|
| 代码边界 CB | import 方向合规？无反向依赖？无死代码？ruff/pytest 绿？ |
| 业务边界 BIZ | 只实现本 FR/NFR？没顺手改范围外（前端/语音/向量库…）？ |
| 权限边界 PERM | engine2 无提权路径；owner 校验在？admin 未绕过？ |
| 安全边界 SEC | 用户输入未进 system；输出仅文本/白名单素材；无新增密钥；CORS/限流符合？ |
| 性能边界 PERF | LLM 调用 ≤ 预算；无 N+1 查询；历史/消息读取有 limit？ |
| 回滚能力 | ENGINE_VERSION 可切回 v1？DB 可回退/可备份？ |

未满足项禁止标“完成”：要么修复，要么登记“待加固 + 任务号”到 06。

## 8. 验收登记规范

- 每步完成后 30 分钟内登记 06 台账（趁证据新鲜），再追加 07 报告。
- 证据必须可复跑：命令原文 + 输出摘要 + 文件路径。
- 一条记录只写一件事；类型从 {单测, 边界, 权限, 安全, 性能, 评审, 走查, E2E} 中选。
