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

/* Background Image */
.stApp {
    background-image: url("https://t3.ftcdn.net/jpg/17/99/92/42/360_F_1799924294_c6IkNOhxt7Vv6SYasT9xcTHxhdswWYZ9.jpg");
    background-size: cover;
    background-position: center;
    background-attachment: fixed;
}

/* Dark overlay */
.stApp::before {
    content: "";
    position: fixed;
    top: 0; left: 0;
    width: 100%; height: 100%;
    background: rgba(0,0,0,0.65);
    z-index: 0;
}

/* Login Box */
.login-box {
    position: relative;
    z-index: 1;
    background: rgba(0,0,0,0.75);
    padding: 40px;
    border-radius: 15px;
    width: 350px;
    margin: auto;
    margin-top: 120px;
    text-align: center;
    backdrop-filter: blur(8px);
}

/* Title */
.login-title {
    font-size: 30px;
    font-weight: bold;
    color: #facc15;
}

/* Subtitle */
.login-sub {
    color: #ccc;
    margin-bottom: 20px;
}

/* Inputs */
.stTextInput>div>div>input {
    background-color: #111;
    color: white;
    border-radius: 8px;
}

/* Buttons */
.stButton>button {
    background: linear-gradient(90deg,#facc15,#f97316);
    color: black;
    border-radius: 8px;
    font-weight: bold;
}

/* Cards */
.card {
    background: rgba(255,255,255,0.05);
    backdrop-filter: blur(12px);
    border-radius:15px;
    padding:20px;
    margin-top:15px;
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

    st.markdown("""
    <div class="login-box">
        <div class="login-title">🕵️ Investigator Login</div>
        <div class="login-sub">Access the truth engine</div>
    """, unsafe_allow_html=True)

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    col1, col2 = st.columns(2)

    with col1:
        login_btn = st.button("Login")

    with col2:
        signup_btn = st.button("Signup")

    if login_btn:
        user = c.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        if user and hashlib.sha256(password.encode()).hexdigest() == user[1]:
            st.session_state["user"] = username
            st.rerun()
        else:
            st.error("Invalid credentials")

    if signup_btn:
        if username and password:
            c.execute("INSERT INTO users VALUES (?, ?, ?)",
                      (username, hashlib.sha256(password.encode()).hexdigest(), "user"))
            conn.commit()
            st.success("Account created! Now login.")

    st.markdown("</div>", unsafe_allow_html=True)
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
st.markdown("<h1 style='text-align:center;color:#facc15;'>🕵️ AI Fake News Investigator</h1>", unsafe_allow_html=True)

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
        with st.spinner("🧠 Investigating..."):
            progress = st.progress(0)
            for i in range(100):
                time.sleep(0.01)
                progress.progress(i+1)

            result = analyze_news(news)

        confidence = int(re.search(r'(\d+)%', result).group(1)) if re.search(r'(\d+)%', result) else 50

        if "fake" in result.lower():
            st.error("🚨 FAKE NEWS")
        elif "real" in result.lower():
            st.success("✅ REAL NEWS")
        else:
            st.info("🤔 UNVERIFIED")

        st.metric("Confidence", f"{confidence}%")
        st.progress(confidence)

        st.markdown(f"<div class='card'>{result}</div>", unsafe_allow_html=True)

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
