# app.py
from flask import Flask, request, jsonify, render_template, g
import sqlite3, time, os, socket, ipaddress, hmac

DB_PATH = "./data/chat.db"
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "")

app = Flask(__name__, static_folder="static", static_url_path="/static")


def normalize_room(raw):
    room = (raw or "").strip()[:32]
    return room or "general"


def _get_server_ips():
    ips = {"127.0.0.1", "::1"}
    # Gather local interface addresses so requests from this machine to LAN IP
    # can still be recognized as local admin traffic.
    try:
        host = socket.gethostname()
        for item in socket.getaddrinfo(host, None):
            ip = item[4][0]
            ips.add(ip)
    except OSError:
        pass
    return ips


SERVER_IPS = _get_server_ips()


def is_server_local_request(req):
    remote = req.remote_addr or ""
    if not remote:
        return False
    try:
        ip = ipaddress.ip_address(remote)
        if ip.is_loopback:
            return True
    except ValueError:
        return False
    return remote in SERVER_IPS


def is_super_admin(req):
    # Option A: request comes from this server itself.
    if is_server_local_request(req):
        return True
    # Option B: remote admin caller provides shared secret token.
    if ADMIN_TOKEN:
        token = req.headers.get("X-Admin-Token", "")
        if token and hmac.compare_digest(token, ADMIN_TOKEN):
            return True
    return False

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH, check_same_thread=False)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(_):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    first = not os.path.exists(DB_PATH)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS messages(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          room TEXT NOT NULL DEFAULT 'general',
          user TEXT NOT NULL,
          content TEXT NOT NULL,
          ts INTEGER NOT NULL
        )""")
        # 轻量并发下更稳：多读单写
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.commit()

@app.get("/")
def index():
    room = normalize_room(request.args.get("room"))
    return render_template("index.html", initial_room=room)


@app.get("/<room>")
def index_room(room):
    return render_template("index.html", initial_room=normalize_room(room))

@app.post("/api/send")
def api_send():
    data = request.get_json(force=True, silent=True) or {}
    user = (data.get("user") or "anon")[:32]
    room = (data.get("room") or "general")[:32]
    content = (data.get("content") or "").strip()
    if not content:
        return jsonify({"ok": False, "error": "empty"}), 400
    ts = int(time.time())
    db = get_db()
    db.execute("INSERT INTO messages(room,user,content,ts) VALUES(?,?,?,?)",
               (room, user, content, ts))
    db.commit()
    return jsonify({"ok": True})

@app.get("/api/messages")
def api_messages():
    room = (request.args.get("room") or "general")[:32]
    since_id = int(request.args.get("since_id", "0") or 0)
    limit = max(1, min(int(request.args.get("limit", "100")), 500))
    rows = get_db().execute(
        "SELECT id,user,content,ts FROM messages WHERE room=? AND id>? "
        "ORDER BY id ASC LIMIT ?",
        (room, since_id, limit)
    ).fetchall()
    return jsonify([dict(r) for r in rows])

@app.get("/api/recent")
def api_recent():
    room = (request.args.get("room") or "general")[:32]
    limit = max(1, min(int(request.args.get("limit", "100")), 500))
    rows = get_db().execute(
        "SELECT id,user,content,ts FROM messages WHERE room=? "
        "ORDER BY id DESC LIMIT ?",
        (room, limit)
    ).fetchall()
    data = [dict(r) for r in rows][::-1]  # 时间顺序返回
    return jsonify(data)


@app.get("/api/admin/status")
def api_admin_status():
    return jsonify({"ok": True, "is_admin": is_super_admin(request)})


@app.post("/api/admin/purge")
def api_admin_purge():
    if not is_super_admin(request):
        return jsonify({"ok": False, "error": "forbidden"}), 403

    data = request.get_json(force=True, silent=True) or {}
    room = (data.get("room") or "").strip()[:32]
    db = get_db()
    if room:
        cur = db.execute("DELETE FROM messages WHERE room=?", (room,))
    else:
        cur = db.execute("DELETE FROM messages")
    db.commit()
    return jsonify({"ok": True, "deleted": cur.rowcount, "room": room or "ALL"})

if __name__ == "__main__":
    init_db()
    # 内网可见
    app.run(host="0.0.0.0", port=8902, debug=False)
