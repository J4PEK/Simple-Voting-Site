from flask import Flask, request, send_from_directory, jsonify, redirect, url_for, session
import sqlite3

app = Flask(__name__)
app.secret_key = "super_secret_key_123"   # change this to something random

DB = "votes.db"

ADMIN_USER = "admin"
ADMIN_PASS = "telewizor"


# ----------------------
# DATABASE INITIALIZATION
# ----------------------
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    # table for vote counts
    c.execute("""
        CREATE TABLE IF NOT EXISTS votes (
            photo_id INTEGER PRIMARY KEY,
            count INTEGER DEFAULT 0
        )
    """)

    # table for IPs that already voted
    c.execute("""
        CREATE TABLE IF NOT EXISTS voted_ips (
            ip TEXT PRIMARY KEY
        )
    """)

    conn.commit()
    conn.close()


init_db()


# ----------------------
# MAIN PAGE
# ----------------------
@app.route("/")
def index():
    return send_from_directory(".", "index.html")


# ----------------------
# SERVE IMAGES
# ----------------------
@app.route("/static/media/<path:filename>")
def media(filename):
    return send_from_directory("static/media", filename)


# ----------------------
# VOTING
# ----------------------
@app.route("/vote", methods=["POST"])
def vote():
    ip = request.remote_addr
    data = request.json
    photo_id = data.get("photo_id")

    if photo_id is None:
        return "Invalid vote", 400

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    # check if IP already voted
    c.execute("SELECT ip FROM voted_ips WHERE ip = ?", (ip,))
    if c.fetchone():
        conn.close()
        return "Już oddałeś głos!"

    # save IP
    c.execute("INSERT INTO voted_ips (ip) VALUES (?)", (ip,))

    # update vote count
    c.execute("""
        INSERT INTO votes (photo_id, count)
        VALUES (?, 1)
        ON CONFLICT(photo_id)
        DO UPDATE SET count = count + 1
    """, (photo_id,))

    conn.commit()
    conn.close()
    return "Dziękujemy za głos!"



@app.route("/results")
def results():

    if not session.get("logged_in"):
        return redirect("/login")

    return send_from_directory(".", "results.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = request.form.get("username")
        password = request.form.get("password")

        if user == ADMIN_USER and password == ADMIN_PASS:
            session["logged_in"] = True
            return redirect("/results")

        return "Wrong username or password"

    return """
    <h2>Admin Login</h2>
    <form method="POST">
        <input name="username" placeholder="Username"><br><br>
        <input name="password" type="password" placeholder="Password"><br><br>
        <button type="submit">Login</button>
    </form>
    """

@app.route("/results_data")
def results_data():

    if not session.get("logged_in"):
        return "Unauthorized", 403

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT photo_id, count FROM votes ORDER BY count DESC")
    rows = c.fetchall()

    conn.close()

    results = []
    for r in rows:
        results.append({
            "photo_id": r[0],
            "votes": r[1]
        })

    return jsonify(results)
# ----------------------
# RUN SERVER
# ----------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
