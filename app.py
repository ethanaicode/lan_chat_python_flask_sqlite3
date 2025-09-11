# app.py
from flask import Flask, request, jsonify, send_from_directory, g
import sqlite3, time, os

DB_PATH = "./data/chat.db"

app = Flask(__name__, static_folder="static", static_url_path="")

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

@app.route("/")
def index():
    return send_from_directory("static", "index.html")

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

if __name__ == "__main__":
    init_db()
    # 内网可见
    app.run(host="0.0.0.0", port=9000, debug=False)
