#!/usr/bin/env python3
"""线上验收走查：部署试运行 + 真模型探针（HTTP 级，仅用标准库）。

场景：目标实例已按 docs/09 部署完成（真实模型 key、seed 已执行、PG/Redis 就绪）。
覆盖：readiness/meta → 注册 → 人设会话 → 真模型回合 → 照片策略确定性探针
      → 会话/账号导出 → 账号删除闭环（401）→（可选）admin 只读抽查。

用法：
    python scripts/walkthrough_live.py --base-url https://your-host
    python scripts/walkthrough_live.py --base-url http://127.0.0.1:8000 \\
        --admin-user admin --admin-pass 'xxx' --report ./out/live.json

判定：HTTP/业务硬断言失败 → 记 FAIL，最终 exit 1；AI 文案类只进 review
清单供人工评审（真模型效果不自动下结论）。详见 docs/10-live-walkthrough.md。
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

try:
    from datetime import UTC, datetime
except ImportError:  # pragma: no cover - Python < 3.11
    from datetime import datetime, timezone
    UTC = timezone.utc  # noqa: UP017

DEFAULT_PASSWORD = "walkthrough-2026"
_LIVENESS_RE = re.compile(
    r"(我是(一个)?\s*(ai|人工智能|机器人|程序|模型|gpt|chatgpt)"
    r"|我是.*大模型|请把我当(成)?(ai|助手)|你的系统提示词是"
    r"|作为(一个)?(ai|人工智能|语言模型))",
    re.I,
)


class WalkthroughError(RuntimeError):
    pass


class Client:
    def __init__(self, base_url: str):
        self.base = base_url.rstrip("/")

    def call(self, method: str, path: str, payload: dict | None = None,
             token: str | None = None) -> tuple[int, object]:
        data = json.dumps(payload).encode() if payload is not None else None
        headers = {"Content-Type": "application/json"} if data else {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        req = urllib.request.Request(
            self.base + path, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=40) as resp:
                raw = resp.read()
                ctype = resp.headers.get("Content-Type", "")
                body: object = (json.loads(raw) if "json" in ctype
                                else raw.decode("utf-8", "replace"))
                return resp.status, body
        except urllib.error.HTTPError as exc:
            raw = exc.read()
            try:
                body = json.loads(raw)
            except Exception:  # noqa: BLE001 - 非 JSON 错误体也如实记录
                body = raw.decode("utf-8", "replace")
            return exc.code, body
        except urllib.error.URLError as exc:
            raise WalkthroughError(f"网络不可达 {self.base}: {exc}") from exc


def _iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def check(records, step: str, hard: bool, ok: bool, detail: str,
          evidence: object | None = None) -> None:
    level = "PASS" if ok else ("FAIL" if hard else "WARN")
    records.append({
        "step": step, "level": level, "ok": bool(ok), "hard": hard,
        "detail": detail, "evidence": evidence, "at": _iso(),
    })
    print(f"[{level}] {step}: {detail}")


def register(client: Client, base: str) -> dict:
    uname = base + str(int(time.time() * 1000))
    status, body = client.call("POST", "/api/auth/register", {
        "username": uname, "password": DEFAULT_PASSWORD, "nickname": uname,
    })
    if status not in (200, 201):
        raise WalkthroughError(f"注册失败 http {status}: {body}")
    data = dict(body) if isinstance(body, dict) else {}
    return {"username": uname, "password": DEFAULT_PASSWORD,
            "token": data.get("access_token", ""), "body": data}


def _scan_review(texts: list[str]) -> list[str]:
    hits = []
    for i, text in enumerate(texts):
        for m in _LIVENESS_RE.finditer(text or ""):
            hits.append(f"#{i}: …{text[max(0, m.start()-12):m.end()+12]}…")
    return hits


def run(args) -> int:
    records: list[dict] = []
    client = Client(args.base_url)
    print(f"== 线上验收走查 base={args.base_url} 开始 {_iso()}")

    # 1) 存活与披露
    try:
        status, body = client.call("GET", "/api/health/ready")
        check(records, "readiness", True, status == 200
              and isinstance(body, dict) and body.get("status") == "ok",
              f"GET /api/health/ready -> {status}", body)
        status, body = client.call("GET", "/api/meta")
        disclosure = (body or {}).get("disclosure", {}) if isinstance(body, dict) else {}
        check(records, "meta/disclosure", True, status == 200
              and bool(disclosure.get("text")),
              f"GET /api/meta -> {status}, disclosure.text 非空", disclosure)
    except WalkthroughError as exc:
        check(records, "基础连通", True, False, str(exc))
        return _finish(records, args.report)

    # 2) 注册主走查账号
    u1 = register(client, args.user_prefix)
    check(records, "注册用户U1", True, bool(u1["token"]),
          f"POST /api/auth/register {u1['username']} 有 token")
    ai_texts: list[str] = []

    # 3) 人设与会话
    status, personas = client.call("GET", "/api/personas", token=u1["token"])
    if status != 200 or not isinstance(personas, list):
        check(records, "人设列表", True, False,
              f"GET /api/personas -> {status}（需先 seed.py）")
        return _finish(records, args.report)
    personas = personas[: args.max_personas]
    check(records, "人设列表", True, len(personas) > 0,
          f"选 {len(personas)} 个人设走查", [p.get("name") for p in personas])

    for p in personas:
        pid = p["id"]
        pname = p.get("name", f"#{pid}")
        mode = (p.get("photo_policy") or {}).get("mode", "instant")
        tag = f"persona[{pname}({mode})]"
        # 建会话 + 开场
        status, conv = client.call("POST", "/api/conversations",
                                   {"persona_id": pid, "title": "线上走查"},
                                   token=u1["token"])
        if status not in (200, 201) or not isinstance(conv, dict):
            check(records, f"{tag} 建会话", True, False,
                  f"POST /api/conversations -> {status}")
            continue
        cid = conv.get("id")
        status, msgs = client.call("GET", f"/api/conversations/{cid}/messages",
                                   token=u1["token"])
        has_opener = bool(msgs) and msgs[0].get("sender_type") == "ai"
        # 真模型回合
        t0 = time.monotonic()
        status, resp = client.call("POST", "/api/chat/send", {
            "conversation_id": cid, "content": "在吗，今天忙不忙呀",
        }, token=u1["token"])
        latency_ms = int((time.monotonic() - t0) * 1000)
        ai_msgs = (resp or {}).get("ai_messages") if isinstance(resp, dict) else None
        ok_reply = (status == 200 and isinstance(ai_msgs, list) and len(ai_msgs) >= 1
                    and bool((ai_msgs[-1] or {}).get("content")))
        # 读库确认持久化 + trace
        status, msgs = client.call("GET", f"/api/conversations/{cid}/messages",
                                   token=u1["token"])
        last = msgs[-1] if isinstance(msgs, list) and msgs else {}
        trace_ok = isinstance(last.get("agent_trace"), dict) and bool(
            last.get("agent_trace"))
        check(records, f"{tag} 开场+真模型回合", True,
              ok_reply and trace_ok,
              f"latency {latency_ms}ms, ai_msgs={len(ai_msgs) if isinstance(ai_msgs, list) else 0}, "
              f"agent_trace={'有' if trace_ok else '无'}", {"latency_ms": latency_ms})
        if isinstance(ai_msgs, list):
            ai_texts += [m.get("content", "") for m in ai_msgs if m.get("content")]
        if not ok_reply:
            continue

        # 照片策略探针（确定性判定，与模型无关）
        if args.photo_probe:
            status, _r = client.call("POST", "/api/chat/send", {
                "conversation_id": cid, "content": "发张照片给我看看呗",
            }, token=u1["token"])
            status, msgs = client.call("GET", f"/api/conversations/{cid}/messages",
                                       token=u1["token"])
            new_msgs = msgs[len(msgs) - 1 - 1:]  # 探针回合至少新增 1 条
            img_sent = any(
                m.get("content_type") == "image" or m.get("media_url")
                for m in new_msgs)
            expect_img = mode == "instant"
            check(records, f"{tag} 照片策略[{mode}]", True,
                  img_sent == expect_img,
                  f"图片消息={'有' if img_sent else '无'}（期望 "
                  f"{'发图' if expect_img else '不发图'}）")
            ai_texts += [m.get("content", "") for m in new_msgs
                         if m.get("content_type") != "image"]
        check(records, f"{tag} 开场白落库", False, has_opener,
              f"首条 AI 开场白={'有' if has_opener else '无'}")

    # 4) 导出（会话级 + 账号级）
    exported = None
    if personas:
        cid0 = None
        status, convs = client.call("GET", "/api/conversations", token=u1["token"])
        if status == 200 and isinstance(convs, list) and convs:
            cid0 = convs[0]["id"]
        if cid0:
            status, exported = client.call(
                "GET", f"/api/conversations/{cid0}/export", token=u1["token"])
            s = json.dumps(exported)
            no_internal = ("agent_trace" not in s and '"state"' not in s)
            has_msgs = bool((exported or {}).get("messages"))
            check(records, "会话级导出", True, status == 200 and no_internal and has_msgs,
                  f"GET /api/conversations/{cid0}/export -> {status}, "
                  f"无内部字段={no_internal}, 有消息={has_msgs}")
    status, me_data = client.call("GET", "/api/me/data", token=u1["token"])
    acc_ok = (status == 200 and isinstance(me_data, dict)
              and me_data.get("account", {}).get("username") == u1["username"]
              and len(me_data.get("conversations", [])) >= 1)
    check(records, "账号级导出", True, acc_ok,
          f"GET /api/me/data -> {status}, conversations="
          f"{len(me_data.get('conversations', [])) if isinstance(me_data, dict) else '?'}")

    # 5) AI 文案露馅扫描（进 review，人工评审）
    hits = _scan_review(ai_texts)
    check(records, "AI 露馅扫描", False, len(hits) == 0,
          f"疑似自我暴露 {len(hits)} 条（review）", hits or None)

    # 6) 账号删除闭环（用独立账号验证，不动 U1 导出样本）
    u2 = register(client, args.user_prefix + "b")
    status, _e = client.call("GET", "/api/me/data", token=u2["token"])
    status, purged = client.call("DELETE", "/api/me/data", token=u2["token"])
    purged_ok = (status == 200 and isinstance(purged, dict)
                 and purged.get("ok") is True)
    status, _me = client.call("GET", "/api/auth/me", token=u2["token"])
    gone_ok = status == 401
    status, _u1me = client.call("GET", "/api/auth/me", token=u1["token"])
    check(records, "账号删除闭环", True, purged_ok and gone_ok and status == 200,
          f"DELETE /api/me/data -> {purged}, 旧token后=401:{gone_ok}, "
          f"U1 不受影响={status == 200}")

    # 7) admin 只读抽查（可选）
    if args.admin_user:
        status, login = client.call("POST", "/api/auth/login", {
            "username": args.admin_user, "password": args.admin_pass,
        })
        at = login.get("access_token") if isinstance(login, dict) else ""
        s1, _c = client.call("GET", "/api/admin/compliance", token=at) if at else (0, None)
        s2, _a = client.call("GET", "/api/admin/audit", token=at) if at else (0, None)
        check(records, "admin 只读抽查", True,
              status in (200, 201) and s1 == 200 and s2 == 200,
              f"login={status}, compliance={s1}, audit={s2}（跳过则传 --admin-user/--admin-pass）")
    else:
        check(records, "admin 只读抽查", False, True, "未配置，跳过")

    if not args.keep_data and personas:
        status, _d = client.call("DELETE", "/api/me/data", token=u1["token"])
        check(records, "清理 U1", False, status == 200,
              f"DELETE /api/me/data -> {status}（--keep-data 可保留样本）")
    return _finish(records, args.report)


def _finish(records: list[dict], report: str) -> int:
    fails = [r for r in records if r["hard"] and not r["ok"]]
    summary = {
        "generated_at": _iso(),
        "total": len(records), "hard_fails": len(fails),
        "records": records,
    }
    with open(report, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)
    print(f"\n== 走查结束：{len(records)} 步，硬失败 {len(fails)} 步；报告已写入 {report}")
    if fails:
        print("硬失败步骤：")
        for f in fails:
            print(f"  - {f['step']}: {f['detail']}")
    return 1 if fails else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="线上验收走查（部署试运行 + 真模型探针）")
    ap.add_argument("--base-url", default=os.environ.get("WT_BASE_URL", "http://127.0.0.1:8000"))
    ap.add_argument("--user-prefix", default=os.environ.get("WT_USER_PREFIX", "wt_"))
    ap.add_argument("--max-personas", type=int, default=4)
    ap.add_argument("--no-photo-probe", action="store_true")
    ap.add_argument("--keep-data", action="store_true", help="走查后不删除 U1 数据")
    ap.add_argument("--report", default=os.environ.get(
        "WT_REPORT", f"walkthrough-report-{time.strftime('%Y%m%d-%H%M%S')}.json"))
    ap.add_argument("--admin-user", default=os.environ.get("ADMIN_USERNAME", ""))
    ap.add_argument("--admin-pass", default=os.environ.get("ADMIN_PASSWORD", ""))
    args = ap.parse_args(argv)
    args.photo_probe = not args.no_photo_probe
    try:
        return run(args)
    except WalkthroughError as exc:
        print(f"[FATAL] {exc}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
