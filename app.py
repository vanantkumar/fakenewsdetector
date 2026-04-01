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
st.set_page_config(page_title="Fake News Detector", layout="wide")

# -------------------- CSS --------------------
st.markdown("""
<style>

/* REMOVE STREAMLIT HEADER SPACE */
header, footer {
    visibility: hidden;
}
.block-container {
    padding-top: 0rem;
}

/* BACKGROUND IMAGE */
.stApp {
    background-image: url("https://media.gettyimages.com/id/1335171779/photo/fake-or-real.jpg?s=612x612&w=0&k=20&c=4ihkaDS1Ry0i9ev41--smxxH5ir8vWM4Q4JL93VhC_k=");
    background-size: cover;
    background-position: center;
    background-attachment: fixed;
}

/* DARK OVERLAY */
.stApp::before {
    content: "";
    position: fixed;
    top:0; left:0;
    width:100%; height:100%;
    background: rgba(0,0,0,0.65);
    z-index:0;
}

/* LEFT PANEL */
.left {
    position: relative;
    z-index: 1;
    color: white;
    padding: 120px 60px;
}

.left h1 {
    font-size: 48px;
}

.left p {
    color: #ddd;
}


/* BUTTON */
.stButton>button {
    width: 100%;
    border-radius: 6px;
    background: #2575fc;
    color: white;
}

/* MAIN CARDS */
.main-card {
    background: rgba(255,255,255,0.08);
    padding:20px;
    border-radius:15px;
    color:white;
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

    col1, col2 = st.columns([1,1])

    with col1:
        st.markdown("""
        <div class="left">
            <h1>📰 Fake News Detector</h1>
            <p>Detect fake news and real-time verification.</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="card">', unsafe_allow_html=True)

        if st.session_state["auth_mode"] == "login":
            st.markdown("### Login")

            username = st.text_input("Username")
            password = st.text_input("Password", type="password")

           if st.session_state["auth_mode"] == "login":

    st.markdown("### Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    # LOGIN BUTTON
    if st.button("Login"):
        user = c.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()

        if user and hashlib.sha256(password.encode()).hexdigest() == user[1]:
            st.session_state["user"] = username
            st.rerun()
        else:
            st.error("Invalid credentials")

    st.markdown(
        "<p style='text-align:center; color:gray;'>Don't have an account?</p>",
        unsafe_allow_html=True
    )

    # SIGNUP BUTTON
    if st.button("Signup"):
        st.session_state["auth_mode"] = "signup"
        st.rerun()

        else:
            st.markdown("### Signup")

            new_user = st.text_input("Create Username")
            new_pass = st.text_input("Create Password", type="password")
            confirm_pass = st.text_input("Confirm Password", type="password")  # ✅ NEW FIELD

            if st.button("Create Account"):
                if new_user and new_pass:
                    c.execute("INSERT INTO users VALUES (?, ?, ?)",
                              (new_user, hashlib.sha256(new_pass.encode()).hexdigest(), "user"))
                    conn.commit()
                    st.success("Account created")

            if st.button("Back to Login"):
                st.session_state["auth_mode"] = "login"
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

    st.stop()

# -------------------- GEMINI --------------------
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel(
    next(m.name for m in genai.list_models() if "generateContent" in m.supported_generation_methods)
)

# -------------------- FETCH NEWS --------------------
def fetch_real_news(query):
    try:
        url = f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}&hl=en-IN&gl=IN&ceid=IN:en"
        root = ET.fromstring(requests.get(url).content)
        return [i.find("title").text for i in root.findall(".//item")[:5]]
    except:
        return []

# -------------------- ANALYSIS --------------------
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
st.markdown("<h1 style='text-align:center;color:white;'>📰 Fake News Detector</h1>", unsafe_allow_html=True)

# -------------------- NAVIGATION --------------------
c1, c2, c3 = st.columns(3)
with c1:
    if st.button("Analyze"):
        st.session_state["page"] = "Analyze"
with c2:
    if st.button("Dashboard"):
        st.session_state["page"] = "Dashboard"
with c3:
    if st.button("History"):
        st.session_state["page"] = "History"

# -------------------- ANALYZE --------------------
if st.session_state["page"] == "Analyze":
    news = st.text_area("Enter News")

    if st.button("Run Analysis"):
        placeholder = st.empty()
        for i in range(3):
            placeholder.write("🧠 AI analyzing...")
            time.sleep(0.5)

        result = analyze_news(news)
        placeholder.empty()

        confidence = int(re.search(r'(\d+)%', result).group(1)) if re.search(r'(\d+)%', result) else 50

        if "fake" in result.lower():
            st.error("🚨 Fake News")
        elif "real" in result.lower():
            st.success("✅ Real News")
        else:
            st.info("🤔 Unverified")

        st.progress(confidence)
        st.write(result)

        c.execute("INSERT INTO history VALUES (?, ?, ?)",
                  (st.session_state["user"], news, result))
        conn.commit()

# -------------------- DASHBOARD --------------------
elif st.session_state["page"] == "Dashboard":
    rows = c.execute("SELECT * FROM history").fetchall()

    if rows:
        df = pd.DataFrame(rows, columns=["User","News","Result"])

        fake = df["Result"].str.contains("fake", case=False).sum()
        real = df["Result"].str.contains("real", case=False).sum()
        unv = df["Result"].str.contains("unverified", case=False).sum()

        st.markdown('<div class="main-card">', unsafe_allow_html=True)
        st.write("### Analytics")
        st.bar_chart({"Fake":[fake], "Real":[real], "Unverified":[unv]})
        st.markdown('</div>', unsafe_allow_html=True)

# -------------------- HISTORY --------------------
elif st.session_state["page"] == "History":
    rows = c.execute("SELECT * FROM history WHERE username=?",
                     (st.session_state["user"],)).fetchall()

    for r in rows[::-1]:
        st.markdown('<div class="main-card">', unsafe_allow_html=True)
        st.write("📰", r[1][:100])
        st.write(r[2])
        st.markdown('</div>', unsafe_allow_html=True)

# -------------------- LOGOUT --------------------
if st.button("Logout"):
    st.session_state["user"] = None
    st.rerun()
