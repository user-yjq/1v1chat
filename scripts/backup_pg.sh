#!/usr/bin/env bash
# R-B6：PostgreSQL 逻辑备份（pg_dump -Fc）+ sha256 + 按天轮转。
#
# 用法：
#   DATABASE_URL=postgresql://user:pass@host:5432/db \
#   [BACKUP_DIR=./backups] [RETAIN_DAYS=30] [PG_DOCKER=<容器名>] ./scripts/backup_pg.sh
#
# 说明：
#   - 接受 SQLAlchemy 风格 URL（postgresql+psycopg2:// 自动转 postgresql://）；
#   - 本机 pg_dump 需与服务器同 major；否则设 PG_DOCKER=<PG 容器名> 走容器内客户端。
set -euo pipefail

DATABASE_URL="${DATABASE_URL:-}"
RETAIN_DAYS="${RETAIN_DAYS:-30}"
BACKUP_DIR="${BACKUP_DIR:-$(pwd)/backups}"

if [ -z "$DATABASE_URL" ]; then
  echo "✗ 需要 DATABASE_URL" >&2
  exit 1
fi

# pg 命令执行器：PG_DOCKER 模式下经 docker exec -i 在容器内执行
if [ -n "${PG_DOCKER:-}" ]; then
  pg_tool() { docker exec -i "$PG_DOCKER" "$@"; }
else
  command -v pg_dump >/dev/null 2>&1 || { echo "✗ 未找到 pg_dump（安装同 major 客户端或设 PG_DOCKER）" >&2; exit 1; }
  pg_tool() { "$@"; }
fi

# 本机库 URL -> libpq URL -> 容器内可见 URL
LIBPQ_URL=$(printf '%s' "$DATABASE_URL" \
  | sed -e 's/^postgresql+psycopg2:/postgresql:/' -e 's/^postgresql+psycopg:/postgresql:/')
DB_NAME=$(printf '%s' "$LIBPQ_URL" | sed -E 's#^[^:]+://[^/]+/([^?/]*).*#\1#')
TOOL_URL="$LIBPQ_URL"
if [ -n "${PG_DOCKER:-}" ]; then
  AUTH=$(printf '%s' "$LIBPQ_URL" | sed -E 's#^[a-z0-9+]+://([^@/]+)@.*#\1#')
  TOOL_URL="postgresql://${AUTH}@127.0.0.1:5432/${DB_NAME}"
fi

mkdir -p "$BACKUP_DIR"
TS=$(date +%Y%m%d_%H%M%S)
DUMP="${BACKUP_DIR}/${DB_NAME}_${TS}.dump"

echo "→ pg_dump -Fc ${DB_NAME} → ${DUMP}"
pg_tool pg_dump "$TOOL_URL" -Fc > "$DUMP"
sha256sum "$DUMP" | awk '{print $1}' > "${DUMP}.sha256"
echo "✓ 备份完成：${DUMP}"
echo "✓ sha256：$(cat "${DUMP}.sha256")"

# 轮转：仅保留 RETAIN_DAYS 天内的本库备份
find "$BACKUP_DIR" -maxdepth 1 -name "${DB_NAME}_*.dump" -mtime "+${RETAIN_DAYS}" -delete -print
find "$BACKUP_DIR" -maxdepth 1 -name "${DB_NAME}_*.dump.sha256" -mtime "+${RETAIN_DAYS}" -delete -print
echo "✓ 轮转完成：保留 ${RETAIN_DAYS} 天内的 ${DB_NAME} 备份"
