from flask import Flask, request, jsonify, render_template, redirect
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
from flask_bcrypt import Bcrypt
import sqlite3
import pickle
import os
import pandas as pd

app = Flask(__name__)
app.secret_key = "secret123"

bcrypt = Bcrypt(app)

# LOGIN
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "home"

class User(UserMixin):
    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

# DATABASE
def init_db():
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            password TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# LOAD MODEL
model = None
vectorizer = None

if os.path.exists("model.pkl") and os.path.exists("vectorizer.pkl"):
    model = pickle.load(open("model.pkl","rb"))
    vectorizer = pickle.load(open("vectorizer.pkl","rb"))

# LOAD DATASET
df = None
try:
    df = pd.read_csv("training.csv", encoding="latin-1", header=None)
    df.columns = ["target","id","date","flag","user","text"]
except:
    print("Dataset not loaded")

# TRENDING LIST
TRENDING = ["elon", "modi", "virat", "trump", "taylor", "cricket", "ai"]

# FETCH
def fetch_tweets(keyword, count=5):
    if df is None:
        return ["Dataset not loaded"]

    filtered = df[df['text'].str.contains(keyword, case=False, na=False)]

    if len(filtered) == 0:
        filtered = df.sample(n=count)

    return filtered.head(count)['text'].tolist()

# ROUTES
@app.route("/")
def home():
    return render_template("login.html")

@app.route("/register_page")
def register_page():
    return render_template("register.html")

@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", trending=TRENDING)

# AUTH
@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    hashed_pw = bcrypt.generate_password_hash(password).decode("utf-8")

    conn = sqlite3.connect("users.db")
    cur = conn.cursor()

    try:
        cur.execute("INSERT INTO users(email,password) VALUES (?,?)",(email,hashed_pw))
        conn.commit()
        return jsonify({"status":"ok"})
    except:
        return jsonify({"status":"exists"})
    finally:
        conn.close()

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE email=?", (email,))
    user = cur.fetchone()
    conn.close()

    if user and bcrypt.check_password_hash(user[2], password):
        login_user(User(user[0]))
        return jsonify({"status":"ok"})

    return jsonify({"status":"fail"})

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/")

# ANALYZE
@app.route("/analyze/<keyword>")
@login_required
def analyze(keyword):
    tweets = fetch_tweets(keyword)

    results = []
    pos = 0
    neg = 0

    for t in tweets:
        if model and vectorizer:
            vec = vectorizer.transform([t])
            pred = model.predict(vec)[0]
            prob = model.predict_proba(vec).max()
        else:
            pred = 1 if "good" in t.lower() else 0
            prob = 0.8

        sentiment = "Positive" if str(pred) == "1" else "Negative"

        if sentiment == "Positive":
            pos += 1
        else:
            neg += 1

        results.append({
            "text": t,
            "sentiment": sentiment,
            "confidence": round(prob * 100, 2)
        })

    return jsonify({
        "tweets": results,
        "positive": pos,
        "negative": neg
    })

# RUN
if __name__ == "__main__":
    app.run(debug=True)