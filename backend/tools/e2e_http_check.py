# ruff: noqa
import os, socket, subprocess, sys, time
sys.path.insert(0, "/opt/1v1chat/backend")
import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

BASE = "/opt/1v1chat/backend"
PY = "/opt/1v1chat/.venv/bin/python"

STAGES = [
    {"key": "greet", "label": "刚认识", "min_turns": 1, "objective": "热络", "advance_on": []},
    {"key": "trust", "label": "聊熟了", "min_turns": 1, "objective": "交心", "advance_on": []},
    {"key": "reveal", "label": "聊到家里", "min_turns": 99, "objective": "引茶", "advance_on": ["buy_intent"]},
    {"key": "pitch", "label": "轻推荐", "min_turns": 99, "objective": "推荐", "advance_on": ["buy_intent"]},
    {"key": "deal", "label": "收尾", "min_turns": 99, "objective": "收尾", "advance_on": []},
]

def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p

def start(version, rate=100, tag="main"):
    db = f"/tmp/e2e_{tag}_{version}.db"
    if os.path.exists(db): os.remove(db)
    port = free_port()
    env = os.environ.copy()
    env.update({"DATABASE_URL": f"sqlite:///{db}", "LLM_MODE": "mock",
                "ENGINE_VERSION": version, "CHAT_RATE_PER_MIN": str(rate)})
    proc = subprocess.Popen([PY, "-m", "uvicorn", "main:app", "--host", "127.0.0.1",
                             "--port", str(port)], cwd=BASE, env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    client = httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=10)
    for _ in range(40):
        try:
            if client.get("/api/health").status_code == 200:
                return db, client, proc
        except Exception:
            time.sleep(0.5)
    raise RuntimeError("server boot timeout")

def seed(dbpath):
    engine = create_engine(f"sqlite:///{dbpath}")
    from models.database import Persona, Scenario
    S = sessionmaker(bind=engine)
    s = S()
    sc = Scenario(slug="tea_e2e", name="卖茶", goal="自然引出外公家的茶", stages=STAGES)
    s.add(sc); s.flush()
    p = Persona(name="小雨", photo_assets=["/media/tea/photo1.jpg"],
                photo_policy={"mode": "friendly", "need_stage_keys": ["reveal", "pitch", "deal"],
                              "max_photos": 2, "caption_template": "看～"}, scenario_id=sc.id)
    s.add(p); s.commit(); pid = p.id; s.close(); return pid

def register(client, name):
    r = client.post("/api/auth/register", json={"username": name, "password": "pw123456", "nickname": name})
    assert r.status_code == 200, r.text
    d = r.json()
    return d["access_token"], d["user"]["id"]

def snap(client, headers, cid):
    r = client.get(f"/api/conversations/{cid}", headers=headers)
    assert r.status_code == 200, r.text
    st = r.json()["state"]
    if "stage_idx" in st:
        return (st["stage_idx"], st["photos_sent"], st["red_packets"])
    return (st["stage"]["idx"], st["photos"]["sent"], st["economy"]["red_packets"])

def run_flow(client, headers, persona_id):
    r = client.post("/api/conversations", json={"persona_id": persona_id}, headers=headers)
    assert r.status_code == 201, r.text
    cid = r.json()["id"]
    msgs = ["哈喽 加个好友", "发张照片看看嘛", "发张照片看看你长啥样",
            "你老家是种茶的呀？茶叶多少钱一斤"]
    out = []
    for m in msgs:
        r = client.post("/api/chat/send", json={"conversation_id": cid, "content": m}, headers=headers)
        assert r.status_code == 200, (m, r.text)
        body = r.json()
        if "长啥样" in m:
            assert any(x["content_type"] == "image" for x in body["ai_messages"]), "应发真实图片"
        out.append(snap(client, headers, cid))
    return out

results = {"ok": [], "fail": []}
def check(name, cond, extra=""):
    (results["ok"] if cond else results["fail"]).append(name)
    print(("PASS " if cond else "FAIL ") + name + (" " + extra if extra else ""), flush=True)

# A) v2 全流程 + 安全边界
db_v2, c2, p2 = start("v2", tag="main")
try:
    pid = seed(db_v2)
    tok_a, _ = register(c2, "user_v2a")
    tok_b, _ = register(c2, "user_v2b")
    ha, hb = {"Authorization": f"Bearer {tok_a}"}, {"Authorization": f"Bearer {tok_b}"}
    flow2 = run_flow(c2, ha, pid)
    check("v2 flow", flow2 == [(1, 0, 0), (2, 0, 0), (2, 1, 0), (3, 1, 0)], str(flow2))

    r = c2.post("/api/conversations", json={"persona_id": pid}, headers=ha)
    cid = r.json()["id"]
    check("owner 404", c2.post("/api/chat/send", json={"conversation_id": cid, "content": "hi"}, headers=hb).status_code == 404)
    check("msg len 400", c2.post("/api/chat/send", json={"conversation_id": cid, "content": "长" * 3000}, headers=ha).status_code == 400)
    check("admin 403", c2.get("/api/admin/personas", headers=ha).status_code == 403)
    evil = c2.get("/api/health", headers={"Origin": "http://evil.example"})
    check("cors block evil", evil.headers.get("access-control-allow-origin") != "http://evil.example")
finally:
    p2.terminate(); p2.wait(); c2.close()

# B) v1 对照与回滚
db_v1, c1, p1 = start("v1", tag="main")
try:
    pid = seed(db_v1)
    tok, _ = register(c1, "user_v1a")
    h = {"Authorization": f"Bearer {tok}"}
    flow1 = run_flow(c1, h, pid)
    check("v1==v2 parity", flow1 == flow2, f"v1={flow1} v2={flow2}")
finally:
    p1.terminate(); p1.wait(); c1.close()

# C) 限流 HTTP 429
db_r, cr, pr = start("v2", rate=3, tag="rate")
try:
    pid = seed(db_r)
    tok, _ = register(cr, "user_rate")
    h = {"Authorization": f"Bearer {tok}"}
    r = cr.post("/api/conversations", json={"persona_id": pid}, headers=h)
    cid = r.json()["id"]
    codes = [cr.post("/api/chat/send", json={"conversation_id": cid, "content": f"m{i}"}, headers=h).status_code for i in range(4)]
    check("rate 429", codes == [200, 200, 200, 429], str(codes))
finally:
    pr.terminate(); pr.wait(); cr.close()

for db in ("/tmp/e2e_main_v2.db", "/tmp/e2e_main_v1.db", "/tmp/e2e_rate_v2.db"):
    if os.path.exists(db): os.remove(db)

print(f"SUMMARY ok={len(results['ok'])} fail={len(results['fail'])}")
sys.exit(1 if results["fail"] else 0)
