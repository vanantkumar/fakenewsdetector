import streamlit as st
import requests
import sqlite3
import hashlib
import google.generativeai as genai
from datetime import datetime
import urllib.parse
from xml.etree import ElementTree as ET
import pandas as pd
import re
import time

# -------------------- CONFIG --------------------
st.set_page_config(page_title="AI Fake News Investigator", layout="wide")

# -------------------- CSS --------------------
st.markdown("""
<style>

/* Layout background */
.stApp {
    background: linear-gradient(135deg, #6a11cb, #2575fc);
}

/* Split wrapper */
.container {
    display: flex;
    height: 90vh;
}

/* Left panel */
.left {
    width: 50%;
    color: white;
    padding: 80px;
}

.left h1 {
    font-size: 40px;
}

.left p {
    color: #ddd;
}

/* Right panel */
.right {
    width: 50%;
    display: flex;
    justify-content: center;
    align-items: center;
}

/* Card */
.card {
    background: white;
    padding: 35px;
    border-radius: 12px;
    width: 350px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.2);
}

/* Input */
.stTextInput>div>div>input {
    border-radius: 6px;
}

/* Button */
.stButton>button {
    width: 100%;
    background: #2575fc;
    color: white;
    border-radius: 6px;
}

/* Main app card */
.main-card {
    background: rgba(255,255,255,0.08);
    padding:20px;
    border-radius:15px;
}

</style>
""", unsafe_allow_html=True)

# -------------------- DATABASE --------------------
conn = sqlite3.connect("app.db", check_same_thread=False)
c = conn.cursor()

c.execute("CREATE TABLE IF NOT EXISTS users (username TEXT, password TEXT, role TEXT)")
c.execute("CREATE TABLE IF NOT EXISTS history (username TEXT, news TEXT, result TEXT)")

if not c.execute("SELECT * FROM users WHERE username='admin'").fetchone():
    c.execute("INSERT INTO users VALUES (?, ?, ?)",
              ("admin", hashlib.sha256("admin123".encode()).hexdigest(), "admin"))
    conn.commit()

# -------------------- SESSION --------------------
if "user" not in st.session_state:
    st.session_state["user"] = None
if "page" not in st.session_state:
    st.session_state["page"] = "Analyze"

# -------------------- LOGIN --------------------
if not st.session_state["user"]:

    col1, col2 = st.columns(2)

    # LEFT PANEL
    with col1:
        st.markdown("""
        <div class="left">
            <h1>🕵️ AI Investigator</h1>
            <p>Detect fake news using AI and real-time verification.</p>
        </div>
        """, unsafe_allow_html=True)

    # RIGHT PANEL
    with col2:
        st.markdown('<div class="right"><div class="card">', unsafe_allow_html=True)

        st.markdown("### Login")

        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        if st.button("Login"):
            user = c.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
            if user and hashlib.sha256(password.encode()).hexdigest() == user[1]:
                st.session_state["user"] = username
                st.rerun()
            else:
                st.error("Invalid credentials")

        st.markdown("---")

        st.markdown("### Signup")

        new_user = st.text_input("New Username")
        new_pass = st.text_input("New Password", type="password")

        if st.button("Create Account"):
            if new_user and new_pass:
                c.execute("INSERT INTO users VALUES (?, ?, ?)",
                          (new_user, hashlib.sha256(new_pass.encode()).hexdigest(), "user"))
                conn.commit()
                st.success("Account created")

        st.markdown("</div></div>", unsafe_allow_html=True)

    st.stop()

# -------------------- GEMINI --------------------
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel(
    next(m.name for m in genai.list_models() if "generateContent" in m.supported_generation_methods)
)

# -------------------- FETCH NEWS --------------------
def fetch_real_news(q):
    try:
        url = f"https://news.google.com/rss/search?q={urllib.parse.quote(q)}&hl=en-IN&gl=IN&ceid=IN:en"
        root = ET.fromstring(requests.get(url).content)
        return [i.find("title").text for i in root.findall(".//item")[:5]]
    except:
        return []

# -------------------- ANALYZE --------------------
def analyze_news(text):
    headlines = "\n".join(fetch_real_news(text)) or "No news found"

    prompt = f"""
    Date: {datetime.now().strftime("%B %Y")}
    News: {text}
    Real Headlines:
    {headlines}

    Verdict: Real/Fake/Unverified
    Confidence: XX%
    Explanation:
    """

    return model.generate_content(prompt).text

# -------------------- MAIN APP --------------------
st.title("🕵️ AI Fake News Investigator")

col1, col2, col3 = st.columns(3)
with col1:
    if st.button("Analyze"):
        st.session_state.page = "Analyze"
with col2:
    if st.button("Dashboard"):
        st.session_state.page = "Dashboard"
with col3:
    if st.button("History"):
        st.session_state.page = "History"

# -------------------- ANALYZE --------------------
if st.session_state.page == "Analyze":

    news = st.text_area("Enter News")

    if st.button("Run Analysis"):
        placeholder = st.empty()
        for i in range(3):
            placeholder.write("🧠 Processing...")
            time.sleep(0.5)

        result = analyze_news(news)
        placeholder.empty()

        confidence = int(re.search(r'(\d+)%', result).group(1)) if re.search(r'(\d+)%', result) else 50

        st.write(result)
        st.progress(confidence)

        c.execute("INSERT INTO history VALUES (?, ?, ?)",
                  (st.session_state["user"], news, result))
        conn.commit()

# -------------------- DASHBOARD --------------------
elif st.session_state.page == "Dashboard":
    st.write("Dashboard coming...")

# -------------------- HISTORY --------------------
elif st.session_state.page == "History":
    rows = c.execute("SELECT * FROM history WHERE username=?",
                     (st.session_state["user"],)).fetchall()

    for r in rows:
        st.write(r)

# -------------------- LOGOUT --------------------
if st.button("Logout"):
    st.session_state["user"] = None
    st.rerun()
