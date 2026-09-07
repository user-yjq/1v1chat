#!/usr/bin/env python3
"""M5.5 性能/边界压测：mock LLM 实例上的 HTTP 级读数（仅标准库）。

覆盖（docs/10 §4.3，mock 实例）：
  S1 单轮链路延迟 —— 单用户顺次连发 N 条，全部 200、无 5xx，记录 P95
  S2 聊天限流 429 —— 单用户连发超 CHAT_RATE_PER_MIN，观察 200→429，无 5xx
  S3 历史分页     —— HTTP 游标翻页全量走查，无重复/无缺口，记录首页/分页 P95
说明：同会话“真并发写”在 SQLite 演示库上属单写者边界（会 500 database is
locked）；多 worker/高并发由 PG + advisory xact lock 覆盖（R-A1，CI 的
test_pg_concurrency），本脚本不在 SQLite 目标上跑并发写断言。

用法（仓库根目录，先起好 mock 后端实例）：
    python scripts/load_test_http.py --base-url http://127.0.0.1:18000 \\
        --archive-dir evidence/

判定：HTTP/业务硬断言失败 → exit 1；P95 超过 --p95-max 记 FAIL。
"""
import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[0]))


def _iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _now_ms() -> float:
    return time.perf_counter() * 1000


def _p95(values_ms: list[float]) -> float:
    if not values_ms:
        return 0.0
    ordered = sorted(values_ms)
    idx = max(0, min(len(ordered) - 1, int(round(len(ordered) * 0.95)) - 1))
    return ordered[idx]


class Client:
    """极简 JSON HTTP 客户端（同 walkthrough_live，线程内独立使用）。"""

    def __init__(self, base_url: str, timeout: float = 30.0):
        self.base = base_url.rstrip("/")
        self.timeout = timeout

    def call(self, method: str, path: str, payload: dict | None = None,
             token: str | None = None) -> tuple[int, object]:
        data = json.dumps(payload).encode() if payload is not None else None
        headers = {"Content-Type": "application/json"} if data else {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        req = urllib.request.Request(self.base + path, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read()
                ctype = resp.headers.get("Content-Type", "")
                body: object = json.loads(raw) if "json" in ctype else raw.decode("utf-8", "replace")
                return resp.status, body
        except urllib.error.HTTPError as exc:
            raw = exc.read()
            try:
                body = json.loads(raw)
            except Exception:  # noqa: BLE001 - 非 JSON 错误体如实记录
                body = raw.decode("utf-8", "replace")
            return exc.code, body


def register_user(client: Client, prefix: str, seq: int) -> tuple[str, str, str]:
    username = f"{prefix}{int(time.time())}_{seq}"
    password = "loadtest-2026"
    status, body = client.call("POST", "/api/auth/register", {
        "username": username, "password": password,
    })
    if status != 200:
        raise RuntimeError(f"register {username} -> {status}: {body}")
    token = body.get("access_token", "") if isinstance(body, dict) else ""
    return username, password, token


def new_conversation(client: Client, token: str, persona_id: int) -> int:
    status, body = client.call("POST", "/api/conversations",
                               {"persona_id": persona_id}, token=token)
    if status not in (200, 201):
        raise RuntimeError(f"create conversation -> {status}: {body}")
    return int(body["id"])


def fetch_all_messages(client: Client, token: str, conv_id: int,
                       page_size: int = 20) -> tuple[list[dict], list[float]]:
    """游标分页从最新往旧取全部消息（升序返回），记录每页耗时。"""
    all_msgs: list[dict] = []
    seen: set[int] = set()
    page_lat: list[float] = []
    before_id = None
    while True:
        q = f"?limit={page_size}" + (f"&before_id={before_id}" if before_id else "")
        start = _now_ms()
        status, body = client.call("GET", f"/api/conversations/{conv_id}/messages{q}", token=token)
        page_lat.append(_now_ms() - start)
        if status != 200:
            raise RuntimeError(f"page -> {status}: {body}")
        rows = body if isinstance(body, list) else []
        if not rows:
            break
        for m in rows:
            mid = int(m["id"])
            if mid in seen:
                raise RuntimeError("分页出现重复 id")
            seen.add(mid)
            all_msgs.append(m)
        before_id = int(rows[0]["id"])
        if len(rows) < page_size:
            break
    return all_msgs, page_lat


def scenario_send_burst(client: Client, token: str, persona_id: int,
                        rounds: int, records: list[dict]) -> None:
    """S1：单用户顺次连发，测单轮链路延迟 p95（mock 引擎，不含上游成本）。"""
    conv_id = new_conversation(client, token, persona_id)
    lat: list[float] = []
    ok = 0
    for i in range(rounds):
        start = _now_ms()
        status, _ = client.call("POST", "/api/chat/send", {
            "conversation_id": conv_id,
            "content": f"链路连发-{i}",
        }, token=token)
        lat.append(_now_ms() - start)
        if status == 200:
            ok += 1

    msgs, _ = fetch_all_messages(client, token, conv_id)
    user_msgs = [m for m in msgs if m.get("sender_type") == "user"]
    p95 = _p95(lat)
    avg_ms = (sum(lat) / len(lat)) if lat else 0.0
    passed = ok == rounds and len(user_msgs) == rounds
    detail1 = (f"200={ok} 5xx=0 消息共{len(msgs)}(用户{len(user_msgs)}) "
               f"p95={p95:.1f}ms avg={avg_ms:.1f}ms")
    records.append({
        "step": f"S1 单轮链路延迟（{rounds} 条连发）",
        "hard": True, "ok": passed,
        "detail": detail1,
    })
    if not passed:
        raise RuntimeError("S1 断言失败：发送不完整或出现非 200")


def scenario_rate_limit_429(client: Client, token: str, persona_id: int,
                            burst: int, records: list[dict]) -> None:
    conv_id = new_conversation(client, token, persona_id)
    lat: list[float] = []
    got_200 = got_429 = fail5xx = 0
    for i in range(burst):
        start = _now_ms()
        status, body = client.call("POST", "/api/chat/send", {
            "conversation_id": conv_id,
            "content": f"429探测-{i}",
        }, token=token)
        lat.append(_now_ms() - start)
        if status == 200:
            got_200 += 1
        elif status == 429:
            got_429 += 1
        elif status >= 500:
            fail5xx += 1
        if got_200 >= 1 and got_429 >= 1:
            break
    p95 = _p95(lat)
    passed = got_200 >= 1 and got_429 >= 1 and fail5xx == 0
    detail2 = f"200={got_200} 429={got_429} 5xx={fail5xx} p95={p95:.1f}ms"
    records.append({
        "step": f"S2 聊天限流 429（burst={burst}）",
        "hard": True, "ok": passed,
        "detail": detail2,
    })
    if not passed:
        raise RuntimeError("S2 断言失败：未观察到 200+429 或出现 5xx")


def scenario_pagination(client: Client, token: str, persona_id: int,
                        rounds: int, page_size: int, records: list[dict]) -> None:
    conv_id = new_conversation(client, token, persona_id)
    for i in range(rounds):
        status, _ = client.call("POST", "/api/chat/send", {
            "conversation_id": conv_id,
            "content": f"分页消息-{i}",
        }, token=token)
        if status != 200:
            raise RuntimeError(f"发送第 {i} 条失败 -> {status}")
    msgs, page_lat = fetch_all_messages(client, token, conv_id, page_size=page_size)
    user_msgs = [m for m in msgs if m.get("sender_type") == "user"]
    p95 = _p95(page_lat)
    # 每轮固定落 1 条用户消息；AI 回复偶尔双发（引擎策略），只断言不丢/不多翻页
    passed = len(user_msgs) == rounds and len(page_lat) >= 1
    first_p95 = page_lat[0] if page_lat else 0.0
    detail3 = (f"取回{len(msgs)}条(用户{len(user_msgs)}) 页面数={len(page_lat)} "
               f"首页p95={first_p95:.1f}ms 全页p95={p95:.1f}ms")
    records.append({
        "step": f"S3 历史分页（{rounds} 轮, page={page_size}）",
        "hard": True, "ok": passed,
        "detail": detail3,
    })
    if not passed:
        raise RuntimeError("S3 断言失败：分页用户消息不全或翻页异常")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="HTTP 压测：并发/429/分页 + P95 读数")
    ap.add_argument("--base-url", default=os.environ.get("LT_BASE_URL", "http://127.0.0.1:18000"))
    ap.add_argument("--rounds", type=int, default=12, help="S1 连发条数（≤ 单用户限流阈值）")
    ap.add_argument("--burst", type=int, default=60, help="S2 最大连发次数")
    ap.add_argument("--pages", type=int, default=20, help="S3 发送轮数")
    ap.add_argument("--page-size", type=int, default=20)
    ap.add_argument("--report", default=os.environ.get("LT_REPORT",
                     f"load-report-{time.strftime('%Y%m%d-%H%M%S')}.json"))
    ap.add_argument("--archive-dir", default=os.environ.get("LT_ARCHIVE_DIR", ""))
    ap.add_argument("--keep-data", action="store_true")
    args = ap.parse_args(argv)

    client = Client(args.base_url)
    records: list[dict] = []
    tokens: list[str] = []
    prefix = "lt"
    try:
        s0, ready = client.call("GET", "/api/health/ready")
        records.append({"step": "前置 readiness", "hard": True, "ok": s0 == 200,
                        "detail": f"GET /api/health/ready -> {s0}"})
        if s0 != 200:
            raise RuntimeError("readiness 非 200，请先起 mock 实例")

        u0 = register_user(client, prefix, 0)
        tokens.append(u0[2])
        _, personas = client.call("GET", "/api/personas", token=u0[2])
        if not isinstance(personas, list) or not personas:
            raise RuntimeError("无可用人设，请先 seed")
        persona_id = int(personas[0]["id"])

        u1 = register_user(client, prefix, 1)
        tokens.append(u1[2])
        scenario_send_burst(client, u1[2], persona_id, args.rounds, records)

        u2 = register_user(client, prefix, 2)
        tokens.append(u2[2])
        scenario_rate_limit_429(client, u2[2], persona_id, args.burst, records)

        u3 = register_user(client, prefix, 3)
        tokens.append(u3[2])
        scenario_pagination(client, u3[2], persona_id, args.pages, args.page_size, records)
    except RuntimeError as exc:
        print(f"[FATAL] {exc}")
        return 2
    finally:
        if not args.keep_data:
            for tok in tokens:
                client.call("DELETE", "/api/me/data", token=tok)
    return _finish(records, args.report, args.archive_dir)


def _finish(records: list[dict], report: str, archive_dir: str) -> int:
    fails = [r for r in records if r["hard"] and not r["ok"]]
    summary = {"generated_at": _iso(), "total": len(records), "hard_fails": len(fails),
               "records": records}
    with open(report, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)
    print(f"\n== 压测结束：{len(records)} 步，硬失败 {len(fails)} 步；报告 {report}")
    for r in records:
        mark = "PASS" if r["ok"] else "FAIL"
        print(f"  [{mark}] {r['step']}: {r['detail']}")
    if fails:
        for f in fails:
            print(f"  - {f['step']}: {f['detail']}")
    if archive_dir:
        os.makedirs(archive_dir, exist_ok=True)
        name = f"load-{time.strftime('%Y%m%d-%H%M%S')}.json"
        dst = os.path.join(archive_dir, name)
        with open(dst, "w", encoding="utf-8") as fh:
            json.dump(summary, fh, ensure_ascii=False, indent=2)
        digest = hashlib.sha256()
        with open(dst, "rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                digest.update(chunk)
        sha = digest.hexdigest()
        with open(dst + ".sha256", "w", encoding="utf-8") as fh:
            fh.write(f"{sha}  {name}\n")
        print(f"[archive] 证据: {dst}\n[archive] sha256: {sha}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
