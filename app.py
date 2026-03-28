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
/* Split screen */
.login-container {
    display: flex;
    height: 100vh;
}
.left-panel {
    width: 50%;
    background: repeating-linear-gradient(
        135deg, #111 0px, #111 40px, #fff 40px, #fff 80px
    );
}
.right-panel {
    width: 50%;
    background: #f9fafb;
    display: flex;
    justify-content: center;
    align-items: center;
}
.login-box {
    width: 70%;
}

/* App background */
body {
    background: radial-gradient(circle at top, #1a1a2e, #0f172a, #020617);
}

/* Cards */
.card {
    background: rgba(255,255,255,0.05);
    backdrop-filter: blur(12px);
    border-radius:15px;
    padding:20px;
    margin-top:15px;
}

/* Buttons */
.stButton>button {
    border-radius:10px;
    background: linear-gradient(90deg,#facc15,#f97316);
    color:black;
    font-weight:bold;
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
    <div class="login-container">
        <div class="left-panel"></div>
        <div class="right-panel">
            <div class="login-box">
                <h2>🕵️ Investigator</h2>
                <p>Welcome back!</p>
    """, unsafe_allow_html=True)

    username = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Sign in"):
        user = c.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        if user and hashlib.sha256(password.encode()).hexdigest() == user[1]:
            st.session_state["user"] = username
            st.rerun()
        else:
            st.error("Invalid credentials")

    st.markdown("</div></div></div>", unsafe_allow_html=True)
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
st.markdown("<h1 style='text-align:center;'>🕵️ AI Fake News Investigator</h1>", unsafe_allow_html=True)

# -------------------- NAV --------------------
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("🧠 Analyze"):
        st.session_state.page = "Analyze"
with col2:
    if st.button("📊 Dashboard"):
        st.session_state.page = "Dashboard"
with col3:
    if st.button("📜 History"):
        st.session_state.page = "History"

page = st.session_state.page

# -------------------- ANALYZE PAGE --------------------
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

        c1, c2, c3 = st.columns(3)

        c1.markdown(f"<div class='card'>🚨 Fake<br><h2>{fake}</h2></div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='card'>✅ Real<br><h2>{real}</h2></div>", unsafe_allow_html=True)
        c3.markdown(f"<div class='card'>🤔 Unverified<br><h2>{unv}</h2></div>", unsafe_allow_html=True)

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
