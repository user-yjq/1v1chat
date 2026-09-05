# 1v1Chat - 人设剧本驱动的 1v1 角色聊天平台

用 Python + FastAPI + Vue3 实现的微信式 1v1 角色聊天 demo。
AI 扮演固定“人设”（如卖茶女生），通过**剧本状态机**推进聊天场景，按**人设照片策略**决定什么时候发照片；
回复由单次 LLM 调用以真人微信口吻生成，**不暴露 AI 身份、不硬推销**。

## 文档（开发前置，engine2 重构必读）

从 `docs/00-README.md` 进入整套开发文档：需求与边界、技术选型（ADR）、架构设计、工程规划、实施文档（流程/任务拆分/分步执行）、验收台账（每步测试与边界证据）、实施报告。

> 文档契约：文档先于代码；每完成一个实施步骤必须同步更新 `docs/06-acceptance-ledger.md` 与 `docs/07-implementation-report.md`，否则该步骤不算完成。

## 为什么不是 7 Agent 串链？

早期版本做过 7 Agent（画像/意图/策略/演绎/质检/复盘/记忆）串链：每轮 6-9 次 LLM 调用，慢、贵、行为漂移，
且方向是“AI 防御用户”，与“AI 主导卖茶场景”的产品目标相反。

当前架构（方案 C）：
- **决策是确定性的**：事件规则（要照片/怀疑AI/红包/想买…）+ 剧本状态机 + 照片策略都在代码/配置里
- **LLM 只负责“说人话”**：每轮最多 1 次调用，用“人设卡 + 当前阶段 + 已确认事实 + 本轮指令”生成
- 行为可复现、可控、可验收，聊到第几步由数据说了算，而不是靠模型即兴

## 预置人设（`python seed.py` 生成）

| 人设 | 场景 | 照片策略 |
|------|------|----------|
| 小雨（卖茶女生，25 杭州） | tea_seller 五阶段：认识→聊熟→聊到家→轻推荐→收尾 | friendly：聊到“聊到家”阶段才发 |
| 桃桃（23 成都，自来熟） | free_chat | instant：要就给（限量） |
| 雪儿（24 深圳，爱撒娇） | free_chat | red_packet：收到红包/转账才解锁 |
| 阿静（27 上海，高冷） | free_chat | dangle：一直吊着不给 |

每个会话都记录运行状态：当前阶段、照片已发数、收到红包数、怀疑次数等（`conversations.state` JSON），
并写入每条 AI 消息的 `agent_trace` 便于调试。

## 环境要求
- Python 3.11+
- Node.js 20+
- DeepSeek API Key（可选：没有 key 也可用 `LLM_MODE=mock` 跑通全流程）

## 快速启动

```bash
cp .env.example .env          # 填入 DEEPSEEK_API_KEY（可选）
make install                  # venv(py3.11)+pip 或 uv 均可

# 初始化数据库 + 预置人设/剧本
make seed

# 启动后端（8000）与前端（3000）
make backend
make frontend
```

访问 http://localhost:3000 ，注册后选人设开聊。

没有 API Key 时的离线模式：

```bash
cd backend && LLM_MODE=mock ../.venv/bin/uvicorn main:app --port 8000
```

管理后台（人设/剧本配置、会话记录查看）：

```bash
cd backend && python set_admin.py <你的用户名>   # 把自己设为管理员
# 登录后点击左下角“后台”
```

## 代码结构

```
backend/
  models/          # User/Persona/Scenario/Conversation/Message
  engine/          # events 事件规则 / state 会话状态与阶段机 / photo 照片策略
  llm/             # prompts 模板 + provider(DeepSeek/mock 单次生成)
  routers/         # auth / conversations / chat / personas / admin
  services/chat_engine.py  # 引擎：事件→状态/照片决策→单次生成
  seed.py          # 预置人设与剧本（幂等）
  set_admin.py     # 提权管理员
  tests/           # 22 个离线验收测试（规则/策略/状态机/引擎/剧本走查）
  _legacy/         # 旧 7-Agent 实现存档（不再使用）
frontend/          # Vue3：选人设 → 微信式聊天（图片气泡/头像/正在输入）
```

## 照片为什么是“真发的”
- `Persona.photo_assets` 是真实可访问的图片（`/media/...`，backend/media 下生成，可随时替换成真人/生成图）
- 引擎决策为“发”时，AI 消息是 `content_type=image + media_url` 的真实图片气泡，而不是模型在文字里假装发图

## 测试与代码规范

```bash
cd backend && ../.venv/bin/python -m pytest -q      # 22 passed
cd backend && ../.venv/bin/ruff check .             # 0 errors
cd frontend && npm run build                        # vue-tsc + vite 通过
```

## API 速览
- `POST /api/auth/register|login`
- `GET  /api/personas`（人设列表）
- `POST /api/conversations {persona_id}`（建会话，自动插入开场白）
- `POST /api/chat/send {conversation_id, content}`（返回 `user_message` + `ai_messages[]`，支持 image）
- `GET  /api/conversations/{id}/messages`
- `GET/POST/PUT /api/admin/personas|scenarios`、`GET /api/admin/conversations`
- `GET /media/...`（静态头像与照片）

## 当前进度与验收
见 [REPORT.md](REPORT.md)。
