# 09 部署与发布手册（v0.5.0）

> 依据：01 FR/NFR、02 ADR、03 架构/§16、04 发布策略、08 生产化缺口台账。
> 目标读者：拿到本仓库后要把 demo 跑成“可上线候选”的人。

## 1. 组件与拓扑

| 组件 | 说明 | 端口 |
|------|------|------|
| `frontend` | Vue3 构建产物 + nginx：静态站点、`/api/`、`/media/` 反代到 backend | 3000 |
| `backend` | FastAPI（uvicorn，单 worker 基线；多 worker 需 Redis/PG，见 §4） | 8000 |
| PostgreSQL（可选，推荐） | 生产候选存储；启动时由 backend 自动跑 Alembic `upgrade head` | 5432 |
| Redis（可选） | 跨 worker 限流共享计数（`REDIS_URL` 配置） | 6379 |

默认 `docker-compose.yml` 即包含 backend + frontend；PG/Redis 接入方式见 §4。

## 2. 快速开始（Docker 一键）

```bash
cp .env.example .env            # 按需改 .env（见 §3 必改项）
docker compose up -d --build    # 或 make docker-up
docker compose ps               # backend healthcheck 就绪后 frontend 才起来
curl -fsS http://127.0.0.1:8000/api/health/ready   # {"status":"ok",...}
open http://127.0.0.1:3000      # 前端（/api 已反代）
```

本地裸跑：`make install && make seed && make backend`（8000）+ `make frontend`（5173）。

> 构建源与运行环境说明：
> - 两个 Dockerfile 的依赖安装走 uv（backend，装 `backend/requirements.txt` 单一源）与 npm `ci`（frontend，按 lockfile）；
>   默认国内镜像源（阿里云 PyPI/apt、npmmirror），海外/CI 可用 `docker build --build-arg PIP_INDEX_URL=... --build-arg APT_MIRROR=... --build-arg NPM_REGISTRY=... --build-arg UV_VERSION=...` 覆盖（见各 Dockerfile 头注释）。
> - `docker compose` 会读取项目根 `.env` 做变量插值；若该 `.env` 是本地裸跑用的开发值（如 `sqlite:///./1v1chat.db`、`redis://localhost`），容器会拿到容器内不可用的地址——请用 shell 环境变量覆盖（如 `DATABASE_URL=sqlite:///./data/1v1chat.db REDIS_URL= docker compose up -d`）或按 `.env.example` 配置。
> - 镜像以非 root（uid 10001）运行；`.dockerignore` 排除所有层级的 `.env`，运行期密钥一律经 compose/部署环境注入，不烧进镜像。

## 3. 部署前必改配置（对照 08 R-C1/C2/C3/C5/C6）

| 项 | 键 | 说明 |
|----|----|------|
| 运行模式 | `APP_ENV=prod` | 触发 prod fail-fast：占位 `JWT_SECRET`/空 key/`APP_DEBUG=true` 直接拒绝启动 |
| JWT 密钥 | `JWT_SECRET` | 强随机 ≥32 字符；泄漏=可伪造会话 |
| LLM Key | `DEEPSEEK_API_KEY`（可空） | 空时需 `LLM_MODE=mock`，否则 prod 启动失败 |
| CORS | `CORS_ORIGINS` | 显式白名单（如 `["https://chat.example.com"]`），禁止含 `*` |
| 管理员 | `ADMIN_BOOTSTRAP_USERNAME/PASSWORD` | 首次空表启动自动建 admin；初始化后请清空这两个环境变量 |
| 引擎 | `ENGINE_VERSION` | **v0.5.0 默认 `v2`**（engine2）；回滚设 `v1`（见 §5） |
| 合规披露 | `DISCLOSURE_ENABLED/TEXT` | 前端“对面是 AI 角色扮演实验”横幅文案/开关 |
| 静态媒体 | `MEDIA_DIR` | AI 头像/照片素材目录（compose 用 named volume） |

生产存储建议 PostgreSQL：`DATABASE_URL=postgresql+psycopg2://user:pass@host:5432/1v1chat`；
dev/演示可继续 SQLite（文件库自动 WAL）。启动即迁移（prod 分支 `run_migrations`）。

## 4. 多 worker / 多实例注意事项

- 会话写入一致性：engine2 在 PG 上用 `pg_advisory_xact_lock` 串行同一会话（R-A1）；**SQLite 只能单 worker**。
- 限流跨 worker：设置 `REDIS_URL`，登录防爆破/聊天限流自动走 Redis（不可用时降级进程内，R-A3/R-C2）。
- 指标/日志：`/api/metrics`（Prometheus 文本，进程内计数，多实例需自行抓取聚合）；日志为单行 JSON 且不含消息正文。
- 备份：每日 `pg_dump -Fc` + 30 天轮转（`scripts/backup_pg.sh`），RPO ≤24h；恢复演练见 03 §16.4。

## 5. 回滚（R-E4）

v0.5.0 默认 v2（engine2）。需要回退旧引擎时：

1. 快照数据：PG 用 `scripts/backup_pg.sh`；SQLite 直接拷贝 `data/*.db`（含 `-wal`/`-shm`）。
2. 把 `ENGINE_VERSION` 设为 `v1`（`.env` 或容器环境）并重启 backend。
3. 走查一轮：`scripts/drill_engine_rollback.py`（内存 FakeLLM，双引擎同输入对照）PASS；
   v1 回滚点仍能正常出消息与落库（v1 实现已归档 `_legacy/engine_v1/`，经 `services/chat_engine` 转发层加载，见 docs/03 §12）。

## 6. 发布 checklist（对应 08 M4.9 退出标准）

- [ ] `make lint && make test`（sqlite 全量）绿；PG 全量 `TEST_DATABASE_URL=... pytest` 绿
- [ ] `ruff check backend scripts` 0；frontend `npm run build` 通过
- [ ] 迁移：`alembic upgrade head && alembic check` 无漂移（CI Migrate 步骤已覆盖）
- [ ] 双引擎回归：`test_engine_parity.py` 通过；`drill_engine_rollback.py` PASS
- [ ] 台账回填：08 R-* 状态、06 验收记录、07 实施报告、00/04 看板
- [ ] 打 tag：`git tag -a v0.5.0 -m "v0.5.0 production candidate"` 并推送 tag（回滚点）

## 7. 上线后待补（遗留登记）

- 真实 HTTP 环境万级消息 p95 压测与看板（Prometheus+Grafana）
- 注册人机校验升级（验证码/设备指纹）；Terms/Privacy 文案法务审读
