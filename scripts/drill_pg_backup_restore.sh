#!/usr/bin/env bash
# R-B6：PG 备份/恢复演练（可重复执行）。
# 流程：建演练源库 → alembic 迁移 → 插入标记数据 → 备份 → 恢复到新库 → 逐表行数比对 → 清理。
#
# 用法（本机有同 major pg 客户端）：
#   ADMIN_DATABASE_URL=postgresql://postgres:postgres@host:5432/postgres \
#   ./scripts/drill_pg_backup_restore.sh
# 用法（客户端版本不匹配时，用 PG 容器内工具）：
#   ADMIN_DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:54331/postgres \
#   PG_DOCKER=1v1chat-pg ./scripts/drill_pg_backup_restore.sh
set -euo pipefail

REPO_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
ADMIN_URL="${ADMIN_DATABASE_URL:?需要 ADMIN_DATABASE_URL（具备 CREATE DATABASE 权限的超级用户）}"

TS=$(date +%Y%m%d_%H%M%S)
SRC="1v1chat_drill_src_${TS}"
DST="1v1chat_drill_restore_${TS}"
HOST_BASE=$(printf '%s' "$ADMIN_URL" | sed -E 's#/[^/]*$#/#')
SRC_HOST_URL="${HOST_BASE}${SRC}"   # host 侧 URL（alembic 等从本机连）
DST_HOST_URL="${HOST_BASE}${DST}"
BACKUP_DIR="${BACKUP_DIR:-$REPO_DIR/backups}"
MARK_USER="drill_user_${TS}"

# pg 命令执行器与容器内 URL（同 backup/restore 脚本逻辑）
if [ -n "${PG_DOCKER:-}" ]; then
  pg_tool() { docker exec -i "$PG_DOCKER" "$@"; }
  ADMIN_INT="postgresql://$(printf '%s' "$ADMIN_URL" | sed -E 's#^[a-z0-9+]+://([^@/]+)@.*#\1#')@127.0.0.1:5432/postgres"
  INT_BASE="postgresql://$(printf '%s' "$ADMIN_URL" | sed -E 's#^[a-z0-9+]+://([^@/]+)@.*#\1#')@127.0.0.1:5432/"
else
  for t in psql pg_dump pg_restore; do
    command -v "$t" >/dev/null 2>&1 || { echo "✗ 未找到 $t（安装同 major 客户端或设 PG_DOCKER）" >&2; exit 1; }
  done
  pg_tool() { "$@"; }
  ADMIN_INT="$ADMIN_URL"
  INT_BASE="$HOST_BASE"
fi
ADMIN_TOOL_URL="$ADMIN_INT"
SRC_TOOL_URL="${INT_BASE}${SRC}"
DST_TOOL_URL="${INT_BASE}${DST}"

cleanup() {
  pg_tool psql "$ADMIN_TOOL_URL" -q -c "DROP DATABASE IF EXISTS \"$DST\"" 2>/dev/null || true
  pg_tool psql "$ADMIN_TOOL_URL" -q -c "DROP DATABASE IF EXISTS \"$SRC\"" 2>/dev/null || true
}
trap cleanup EXIT

echo "== 1/6 建演练库 =="
pg_tool psql "$ADMIN_TOOL_URL" -q -v ON_ERROR_STOP=1 -c "DROP DATABASE IF EXISTS \"$SRC\""
pg_tool psql "$ADMIN_TOOL_URL" -q -v ON_ERROR_STOP=1 -c "DROP DATABASE IF EXISTS \"$DST\""
pg_tool psql "$ADMIN_TOOL_URL" -q -v ON_ERROR_STOP=1 -c "CREATE DATABASE \"$SRC\""
pg_tool psql "$ADMIN_TOOL_URL" -q -v ON_ERROR_STOP=1 -c "CREATE DATABASE \"$DST\""

echo "== 2/6 alembic 迁移源库（host 侧执行） =="
(
  cd "$REPO_DIR/backend"
  DATABASE_URL="$SRC_HOST_URL" ../.venv/bin/python -m alembic upgrade head >/dev/null
)

echo "== 3/6 插入标记数据 =="
pg_tool psql "$SRC_TOOL_URL" -q -v ON_ERROR_STOP=1 <<SQL
INSERT INTO scenarios (id, slug, name, goal) VALUES (900001, 'drill_${TS}', '备份演练剧本', '验证备份恢复');
INSERT INTO personas (id, name, scenario_id, photo_policy, photo_assets)
  VALUES (900001, '演练小助手', 900001, '{"mode":"instant"}'::json, '[]'::json);
INSERT INTO users (id, username, password_hash, nickname) VALUES (900001, '${MARK_USER}', 'x', '演练用户');
INSERT INTO conversations (id, user_id, title, persona_id, scenario_id, state)
  VALUES (900001, 900001, '演练会话', 900001, 900001, '{}'::json);
INSERT INTO messages (id, conversation_id, sender_type, content) VALUES (900001, 900001, 'user', '备份演练标记消息');
INSERT INTO messages (id, conversation_id, sender_type, content) VALUES (900002, 900001, 'ai', '已收到（演练数据）');
SELECT setval(pg_get_serial_sequence('scenarios','id'), 900002);
SELECT setval(pg_get_serial_sequence('personas','id'), 900002);
SELECT setval(pg_get_serial_sequence('users','id'), 900002);
SELECT setval(pg_get_serial_sequence('conversations','id'), 900002);
SELECT setval(pg_get_serial_sequence('messages','id'), 900003);
SQL

echo "== 4/6 备份源库 =="
export DATABASE_URL="$SRC_HOST_URL"
export BACKUP_DIR="$BACKUP_DIR"
export PG_DOCKER="${PG_DOCKER:-}"
"$REPO_DIR/scripts/backup_pg.sh"
DUMP=$(ls -t "$BACKUP_DIR"/"${SRC}"_*.dump | head -1)

echo "== 5/6 恢复到目标库 =="
export BACKUP_FILE="$DUMP"
export DATABASE_URL="$DST_HOST_URL"
export CONFIRM_RESTORE=1
export SOURCE_DATABASE_URL="$SRC_HOST_URL"
"$REPO_DIR/scripts/restore_pg.sh"

echo "== 6/6 逐表行数比对 =="
FAIL=0
TABLES=$(pg_tool psql "$SRC_TOOL_URL" -tAc \
  "SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name")
for t in $TABLES; do
  S=$(pg_tool psql "$SRC_TOOL_URL" -tAc "SELECT count(*) FROM \"$t\"")
  D=$(pg_tool psql "$DST_TOOL_URL" -tAc "SELECT count(*) FROM \"$t\"")
  if [ "$S" = "$D" ]; then
    printf '  ✓ %-22s src=%-4s dst=%s\n' "$t" "$S" "$D"
  else
    printf '  ✗ %-22s src=%s dst=%s\n' "$t" "$S" "$D"
    FAIL=1
  fi
done

echo "备份产物：${DUMP}"
echo "演练源库：${SRC} / 恢复库：${DST}（已清理）"
if [ "$FAIL" = "0" ]; then
  echo "结论：PASS（备份→恢复后逐表行数一致）"
else
  echo "结论：FAIL" >&2
  exit 1
fi
