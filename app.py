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

# -------------------- MODERN LOGIN CSS --------------------
st.markdown("""
<style>

/* Gradient Background */
.stApp {
    background: linear-gradient(135deg, #667eea, #764ba2);
}

/* Center wrapper */
.login-wrapper {
    display:flex;
    justify-content:center;
    align-items:center;
    height:90vh;
}

/* Login Card */
.login-card {
    width: 380px;
    padding: 35px;
    border-radius: 15px;
    background: white;
    box-shadow: 0 15px 35px rgba(0,0,0,0.2);
}

/* Title */
.login-title {
    font-size: 28px;
    font-weight: bold;
    color: #333;
}

/* Subtitle */
.login-sub {
    color: #777;
    margin-bottom: 20px;
}

/* Buttons */
.stButton>button {
    width: 100%;
    border-radius: 8px;
    background: #667eea;
    color: white;
    font-weight: bold;
}

/* Toggle text */
.toggle {
    margin-top: 15px;
    text-align: center;
    color: #555;
}

/* Main cards */
.card {
    background: rgba(255,255,255,0.08);
    padding:20px;
    border-radius:15px;
    backdrop-filter: blur(10px);
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
if "auth_mode" not in st.session_state:
    st.session_state["auth_mode"] = "login"

# -------------------- LOGIN --------------------
if not st.session_state["user"]:

    st.markdown('<div class="login-wrapper"><div class="login-card">', unsafe_allow_html=True)

    st.markdown('<div class="login-title">Welcome Back</div>', unsafe_allow_html=True)
    st.markdown('<div class="login-sub">Login to continue</div>', unsafe_allow_html=True)

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.session_state.auth_mode == "login":

        if st.button("Login"):
            user = c.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()

            if user and hashlib.sha256(password.encode()).hexdigest() == user[1]:
                st.session_state["user"] = username
                st.rerun()
            else:
                st.error("Invalid credentials")

        st.markdown('<div class="toggle">Don’t have an account?</div>', unsafe_allow_html=True)

        if st.button("Create Account"):
            st.session_state.auth_mode = "signup"
            st.rerun()

    else:

        st.markdown('<div class="login-title">Create Account</div>', unsafe_allow_html=True)

        if st.button("Sign Up"):
            if username and password:
                c.execute("INSERT INTO users VALUES (?, ?, ?)",
                          (username, hashlib.sha256(password.encode()).hexdigest(), "user"))
                conn.commit()
                st.success("Account created")

        st.markdown('<div class="toggle">Already have an account?</div>', unsafe_allow_html=True)

        if st.button("Back to Login"):
            st.session_state.auth_mode = "login"
            st.rerun()

    st.markdown('</div></div>', unsafe_allow_html=True)
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

# -------------------- HEADER --------------------
st.markdown("<h1 style='text-align:center;color:white;'>🕵️ AI Fake News Investigator</h1>", unsafe_allow_html=True)

# -------------------- NAVIGATION --------------------
c1, c2, c3 = st.columns(3)
with c1:
    if st.button("🧠 Analyze"):
        st.session_state.page = "Analyze"
with c2:
    if st.button("📊 Dashboard"):
        st.session_state.page = "Dashboard"
with c3:
    if st.button("📜 History"):
        st.session_state.page = "History"

page = st.session_state.page

# -------------------- ANALYZE --------------------
if page == "Analyze":
    news = st.text_area("Enter News", height=200)

    if st.button("Analyze"):

        # Cinematic thinking
        placeholder = st.empty()
        for i in range(4):
            placeholder.markdown(f"🧠 AI thinking{'.'*i}")
            time.sleep(0.5)

        result = analyze_news(news)
        placeholder.empty()

        confidence = int(re.search(r'(\d+)%', result).group(1)) if re.search(r'(\d+)%', result) else 50

        if "fake" in result.lower():
            st.error("🚨 FAKE NEWS")
        elif "real" in result.lower():
            st.success("✅ REAL NEWS")
        else:
            st.info("🤔 UNVERIFIED")

        st.metric("Confidence", f"{confidence}%")
        st.progress(confidence)

        # Typing effect
        display = st.empty()
        text_out = ""
        for ch in result:
            text_out += ch
            display.markdown(f"<div class='card'>{text_out}</div>", unsafe_allow_html=True)
            time.sleep(0.01)

        c.execute("INSERT INTO history VALUES (?, ?, ?)",
                  (st.session_state["user"], news, result))
        conn.commit()

# -------------------- DASHBOARD --------------------
elif page == "Dashboard":
    rows = c.execute("SELECT * FROM history").fetchall()

    if rows:
        df = pd.DataFrame(rows, columns=["User","News","Result"])

        fake = df["Result"].str.contains("fake", case=False).sum()
        real = df["Result"].str.contains("real", case=False).sum()
        unv = df["Result"].str.contains("unverified", case=False).sum()

        col1, col2, col3 = st.columns(3)

        col1.markdown(f"<div class='card'>🚨 Fake<br><h2>{fake}</h2></div>", unsafe_allow_html=True)
        col2.markdown(f"<div class='card'>✅ Real<br><h2>{real}</h2></div>", unsafe_allow_html=True)
        col3.markdown(f"<div class='card'>🤔 Unverified<br><h2>{unv}</h2></div>", unsafe_allow_html=True)

        st.bar_chart({"Fake":[fake], "Real":[real], "Unverified":[unv]})

# -------------------- HISTORY --------------------
elif page == "History":
    rows = c.execute("SELECT * FROM history WHERE username=?",
                     (st.session_state["user"],)).fetchall()

    for r in rows[::-1]:
        st.markdown(f"<div class='card'>📰 {r[1][:150]}...<br><br>{r[2]}</div>", unsafe_allow_html=True)

# -------------------- LOGOUT --------------------
if st.button("Logout"):
    st.session_state["user"] = None
    st.rerun()
