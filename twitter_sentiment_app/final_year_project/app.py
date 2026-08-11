from flask import Flask, request, jsonify, render_template, session
from textblob import TextBlob
import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "supersecretkey"

# DATABASE
conn = sqlite3.connect('database.db', check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE,
    password TEXT
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT,
    sentiment TEXT,
    time TEXT,
    user TEXT
)
''')

conn.commit()

# HOME
@app.route('/')
def home():
    return render_template('index.html')

# SENTIMENT FUNCTION
def analyze_sentiment(text):
    polarity = TextBlob(text).sentiment.polarity

    if "bad" in text.lower() or "😡" in text:
        return "Negative"
    elif "good" in text.lower() or "😍" in text:
        return "Positive"

    if polarity > 0:
        return "Positive"
    elif polarity < 0:
        return "Negative"
    return "Neutral"

# ANALYZE
@app.route('/analyze', methods=['POST'])
def analyze():
    if 'user' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    text = data.get('text')

    if not text or len(text.strip()) == 0:
        return jsonify({"error": "Empty input"}), 400

    sentiment = analyze_sentiment(text)
    time = datetime.now().strftime("%Y-%m-%d %H:%M")

    cursor.execute(
        "INSERT INTO history (text, sentiment, time, user) VALUES (?, ?, ?, ?)",
        (text, sentiment, time, session['user'])
    )
    conn.commit()

    return jsonify({"sentiment": sentiment})

# HISTORY
@app.route('/history')
def history():
    if 'user' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    cursor.execute(
        "SELECT text, sentiment, time FROM history WHERE user=? ORDER BY id DESC",
        (session['user'],)
    )
    return jsonify(cursor.fetchall())

# ANALYTICS
@app.route('/analytics')
def analytics():
    if 'user' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    cursor.execute(
        "SELECT sentiment, COUNT(*) FROM history WHERE user=? GROUP BY sentiment",
        (session['user'],)
    )
    data = cursor.fetchall()

    result = {"Positive": 0, "Negative": 0, "Neutral": 0}
    for sentiment, count in data:
        result[sentiment] = count

    return jsonify(result)

# SIGNUP
@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()

    try:
        hashed = generate_password_hash(data['password'])
        cursor.execute(
            "INSERT INTO users (email, password) VALUES (?, ?)",
            (data['email'], hashed)
        )
        conn.commit()
        return jsonify({"message": "User registered"})
    except:
        return jsonify({"error": "User already exists"}), 400

# LOGIN
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()

    cursor.execute("SELECT password FROM users WHERE email=?", (data['email'],))
    user = cursor.fetchone()

    if user and check_password_hash(user[0], data['password']):
        session['user'] = data['email']
        return jsonify({"message": "Login success"})

    return jsonify({"error": "Invalid credentials"}), 401

# LOGOUT
@app.route('/logout')
def logout():
    session.clear()
    return jsonify({"message": "Logged out"})

# RUN
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000, debug=True)