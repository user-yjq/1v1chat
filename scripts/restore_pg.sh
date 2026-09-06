#!/usr/bin/env bash
# R-B6：从 pg_dump -Fc 备份恢复到目标 PostgreSQL 库。
#
# 用法：
#   BACKUP_FILE=<file.dump> DATABASE_URL=<目标库 URL> CONFIRM_RESTORE=1 \
#   [SOURCE_DATABASE_URL=<备份源库 URL>] [FORCE_RESTORE=1] [PG_DOCKER=<容器名>] \
#   ./scripts/restore_pg.sh
#
# 安全约束：
#   - 必须显式 CONFIRM_RESTORE=1 才会执行；
#   - 提供 SOURCE_DATABASE_URL 且目标库名与源库同名时拒绝（除非 FORCE_RESTORE=1），
#     防止把备份误恢复到源库造成覆盖。
set -euo pipefail

BACKUP_FILE="${BACKUP_FILE:-${1:-}}"
DATABASE_URL="${DATABASE_URL:-}"
CONFIRM_RESTORE="${CONFIRM_RESTORE:-0}"
SOURCE_DATABASE_URL="${SOURCE_DATABASE_URL:-}"
FORCE_RESTORE="${FORCE_RESTORE:-0}"

if [ ! -f "$BACKUP_FILE" ]; then
  echo "✗ 备份文件不存在：$BACKUP_FILE" >&2
  exit 1
fi
if [ -z "$DATABASE_URL" ]; then
  echo "✗ 需要 DATABASE_URL（目标库）" >&2
  exit 1
fi
if [ "$CONFIRM_RESTORE" != "1" ]; then
  echo "✗ 恢复是覆盖性操作：请显式设置 CONFIRM_RESTORE=1" >&2
  exit 2
fi

if [ -n "${PG_DOCKER:-}" ]; then
  pg_tool() { docker exec -i "$PG_DOCKER" "$@"; }
else
  command -v pg_restore >/dev/null 2>&1 || { echo "✗ 未找到 pg_restore（安装同 major 客户端或设 PG_DOCKER）" >&2; exit 1; }
  pg_tool() { "$@"; }
fi

LIBPQ_URL=$(printf '%s' "$DATABASE_URL" \
  | sed -e 's/^postgresql+psycopg2:/postgresql:/' -e 's/^postgresql+psycopg:/postgresql:/')
DB_NAME=$(printf '%s' "$LIBPQ_URL" | sed -E 's#^[^:]+://[^/]+/([^?/]*).*#\1#')
TOOL_URL="$LIBPQ_URL"
if [ -n "${PG_DOCKER:-}" ]; then
  AUTH=$(printf '%s' "$LIBPQ_URL" | sed -E 's#^[a-z0-9+]+://([^@/]+)@.*#\1#')
  TOOL_URL="postgresql://${AUTH}@127.0.0.1:5432/${DB_NAME}"
fi

if [ -n "$SOURCE_DATABASE_URL" ]; then
  SRC_LIBPQ=$(printf '%s' "$SOURCE_DATABASE_URL" \
    | sed -e 's/^postgresql+psycopg2:/postgresql:/' -e 's/^postgresql+psycopg:/postgresql:/')
  SRC_DB=$(printf '%s' "$SRC_LIBPQ" | sed -E 's#^[^:]+://[^/]+/([^?/]*).*#\1#')
  if [ "$DB_NAME" = "$SRC_DB" ] && [ "$FORCE_RESTORE" != "1" ]; then
    echo "✗ 目标库（${DB_NAME}）与备份源库同名，拒绝覆盖；确需恢复请设 FORCE_RESTORE=1" >&2
    exit 2
  fi
fi

echo "→ pg_restore --clean → ${DB_NAME}（${BACKUP_FILE}）"
pg_tool pg_restore --dbname="$TOOL_URL" --clean --if-exists --no-owner --no-privileges \
  --exit-on-error < "$BACKUP_FILE"
echo "✓ 恢复完成：${DB_NAME}"

# 冒烟验证：应用表存在且可读
if [ -n "${PG_DOCKER:-}" ] || command -v psql >/dev/null 2>&1; then
  COUNT=$(pg_tool psql "$TOOL_URL" -tAc "SELECT count(*) FROM users" 2>/dev/null || echo "N/A")
  echo "✓ 验证 users 行数：${COUNT}"
fi
