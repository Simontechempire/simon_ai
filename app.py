import os, json, hashlib
from flask import Flask, send_from_directory, jsonify, request, session

app = Flask(__name__, static_folder="frontend")
app.secret_key = os.environ.get("SECRET_KEY", "simon-secret-123")

os.makedirs("database", exist_ok=True)
os.makedirs("uploads", exist_ok=True)
os.makedirs("downloads", exist_ok=True)

def get_users():
    p = "database/users.json"
    if not os.path.exists(p): return []
    try: return json.load(open(p))
    except: return []

def hash_pw(pw): return hashlib.sha256(pw.encode()).hexdigest()

def load_chats():
    p="database/chats.json"
    if not os.path.exists(p): return []
    try: return json.load(open(p))
    except: return []

# ===== AUTH - NO VERIFICATION =====
@app.route("/api/auth/signup", methods=["POST"])
def signup():
    data = request.get_json() or {}
    name = data.get("name","").strip()
    email = data.get("email","").strip().lower()
    password = data.get("password","")
    if not name or not email or not password:
        return jsonify({"error":"Fill all fields"}), 400
    users = get_users()
    for u in users:
        if u["email"] == email:
            return jsonify({"error":"Email already exists, please login"}), 400
    user = {"id": str(len(users)+1), "name": name, "email": email, "password": hash_pw(password)}
    users.append(user)
    json.dump(users, open("database/users.json","w"), indent=2)
    session["user"] = {"id": user["id"], "name": name, "email": email}
    return jsonify({"success": True, "user": session["user"]})

@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    email = data.get("email","").strip().lower()
    password = data.get("password","")
    for u in get_users():
        if u["email"] == email and u["password"] == hash_pw(password):
            session["user"] = {"id": u["id"], "name": u["name"], "email": email}
            return jsonify({"success": True, "user": session["user"]})
    return jsonify({"error":"Wrong email or password"}), 401

@app.route("/api/account/me")
def me():
    return jsonify({"user": session.get("user")})

@app.route("/api/auth/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"success": True})

# ===== CHAT =====
@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json() or {}
    msg = data.get("message","").strip()
    if not msg: return jsonify({"error":"Empty"}), 400
    user = session.get("user", {})
    name = user.get("name","friend")
    low = msg.lower()
    if "hello" in low or "hi" in low:
        reply = f"Hello {name}! 👋 How can I help you today?"
    elif "who are you" in low:
        reply = "I am Simon AI, your smart assistant built by Simon Tech Empire."
    elif "what can you do" in low:
        reply = "I can chat, answer questions, help with homework, write, code, and remember your chats."
    else:
        reply = f"Got it — '{msg}'. Tell me more, {name}, I dey here to help you."
    chats = load_chats()
    chats.append({"user": user.get("email","guest"), "message": msg, "reply": reply})
    json.dump(chats, open("database/chats.json","w"), indent=2)
    return jsonify({"reply": reply})

@app.route("/api/chats")
def get_chats():
    email = session.get("user",{}).get("email","guest")
    return jsonify({"chats": [c for c in load_chats() if c.get("user")==email]})

@app.route("/api/ai", methods=["POST"])
def ai():
    data = request.get_json() or {}
    return jsonify({"response": f"Simon AI thinks: {data.get('prompt','')}"})

@app.route("/api/health")
def health():
    return jsonify({"name":"SIMON AI","status":"online"})

@app.route("/")
def home():
    return send_from_directory("frontend", "index.html")

@app.route("/<path:filename>")
def frontend_files(filename):
    if filename.startswith("api/"):
        return jsonify({"error":"Not found"}), 404
    return send_from_directory("frontend", filename)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
