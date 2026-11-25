import os, json, hashlib, random, smtplib, time
from flask import Flask, send_from_directory, jsonify, request, session
from email.mime.text import MIMEText

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

def send_email(to_email, code):
    sender = os.environ.get("EMAIL_USER")
    password = os.environ.get("EMAIL_PASS")
    if not sender or not password:
        print("EMAIL_USER / EMAIL_PASS missing")
        return False
    msg = MIMEText(f"Your Simon AI verification code is: {code}\n\nDo not share it.")
    msg["Subject"] = "Simon AI - Your Verification Code"
    msg["From"] = sender
    msg["To"] = to_email
    try:
        s = smtplib.SMTP("smtp.gmail.com", 587)
        s.starttls(); s.login(sender, password)
        s.sendmail(sender, to_email, msg.as_string()); s.quit()
        return True
    except Exception as e:
        print("Email error:", e)
        return False

def load_chats():
    p="database/chats.json"
    if not os.path.exists(p): return []
    try: return json.load(open(p))
    except: return []

@app.route("/api/auth/send-code", methods=["POST"])
def send_code():
    data = request.get_json() or {}
    email = data.get("email","").strip().lower()
    if not email or "@" not in email:
        return jsonify({"error":"Enter valid email"}), 400
    code = str(random.randint(100000, 999999))
    codes = {}
    if os.path.exists("database/verify.json"):
        try: codes = json.load(open("database/verify.json"))
        except: codes = {}
    codes[email] = {"code": code, "time": time.time()}
    json.dump(codes, open("database/verify.json","w"), indent=2)
    if not send_email(email, code):
        return jsonify({"error":"Could not send email. Check EMAIL_USER / EMAIL_PASS in Render"}), 500
    return jsonify({"success": True})

@app.route("/api/auth/verify", methods=["POST"])
def verify():
    data = request.get_json() or {}
    name = data.get("name","").strip()
    email = data.get("email","").strip().lower()
    password = data.get("password","")
    code = data.get("code","").strip()
    if not name or not email or not password or not code:
        return jsonify({"error":"Fill all fields + code"}), 400
    codes = {}
    if os.path.exists("database/verify.json"):
        codes = json.load(open("database/verify.json"))
    saved = codes.get(email)
    if not saved or saved["code"] != code:
        return jsonify({"error":"Wrong code"}), 400
    if time.time() - saved.get("time",0) > 600:
        return jsonify({"error":"Code expired. Send new code"}), 400
    users = get_users()
    for u in users:
        if u["email"] == email:
            session["user"] = {"id": u["id"], "name": u["name"], "email": email}
            return jsonify({"success": True, "user": session["user"]})
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

@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json() or {}
    msg = data.get("message","").strip()
    if not msg: return jsonify({"error":"Empty"}), 400
    user = session.get("user", {})
    reply = f"Simon AI: I hear you — '{msg}'. How can I help you further?"
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

@app.route("/api/memory")
def memory():
    return jsonify({"memory": load_chats()})

@app.route("/api/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"error":"No file"}), 400
    f = request.files["file"]
    f.save(os.path.join("uploads", f.filename))
    return jsonify({"success": True, "filename": f.filename})

@app.route("/api/download/<filename>")
def download(filename):
    if os.path.exists(os.path.join("downloads", filename)):
        return send_from_directory("downloads", filename, as_attachment=True)
    return jsonify({"error":"Not found"}), 404

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
