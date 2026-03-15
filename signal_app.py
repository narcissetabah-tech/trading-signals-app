import streamlit as st
import pandas as pd
import os
from threading import Thread
from flask import Flask, request, jsonify

# -----------------------------
# CONFIGURATION PAGE
# -----------------------------
st.set_page_config(
    page_title="Signal Bot Pro",
    page_icon="📊",
    layout="wide"
)

# -----------------------------
# THEMES
# -----------------------------
theme = st.sidebar.selectbox(
    "🎨 Mode d'affichage",
    ["System", "Clair", "Sombre"]
)

if theme == "Sombre":
    st.markdown("""
        <style>
        body {background-color:#0e1117;color:white;}
        </style>
    """, unsafe_allow_html=True)

if theme == "Clair":
    st.markdown("""
        <style>
        body {background-color:white;color:black;}
        </style>
    """, unsafe_allow_html=True)

# -----------------------------
# API RECEIVER (FLASK)
# -----------------------------
app = Flask(__name__)
DATA_FILE = "signals_history.csv"

@app.route('/webhook', methods=['POST'])
def webhook():

    data = request.json

    new_sig = pd.DataFrame([{
        "date": pd.Timestamp.now().strftime("%d %b %H:%M"),
        "pair": data.get("pair"),
        "sens": data.get("sens"),
        "entry": data.get("entry"),
        "sl": data.get("sl"),
        "tp": data.get("tp"),
        "rr": data.get("rr")
    }])

    if not os.path.isfile(DATA_FILE):
        new_sig.to_csv(DATA_FILE, index=False)
    else:
        new_sig.to_csv(DATA_FILE, mode='a', header=False, index=False)

    return jsonify({"status": "ok"}), 200


def run_flask():
    app.run(host="0.0.0.0", port=5000)


if 'flask_started' not in st.session_state:
    Thread(target=run_flask, daemon=True).start()
    st.session_state['flask_started'] = True

# -----------------------------
# HEADER
# -----------------------------
st.title("💎 Institutional Signal Dashboard")

st.caption("Flux de signaux trading en temps réel")

# -----------------------------
# DATA
# -----------------------------
if os.path.exists(DATA_FILE):
    df = pd.read_csv(DATA_FILE)
else:
    df = pd.DataFrame()

# -----------------------------
# STATS
# -----------------------------
if not df.empty:

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("📡 Signaux reçus", len(df))

    with col2:
        buy = len(df[df["sens"] == "BUY"])
        st.metric("📈 BUY", buy)

    with col3:
        sell = len(df[df["sens"] == "SELL"])
        st.metric("📉 SELL", sell)

st.divider()

# -----------------------------
# SIGNALS DISPLAY
# -----------------------------
st.subheader("📊 Signaux récents")

if df.empty:

    st.info("Aucun signal reçu pour le moment...")

else:

    for _, sig in df.iloc[::-1].iterrows():

        color = "#00ff9c" if sig["sens"] == "BUY" else "#ff4b4b"

        st.markdown(
            f"""
            <div style="
                border-radius:12px;
                padding:20px;
                margin-bottom:15px;
                background:#1e1e1e;
                border-left:6px solid {color};
                box-shadow:0px 2px 10px rgba(0,0,0,0.3);
            ">

            <h3>{sig['pair']} — <span style='color:{color}'>{sig['sens']}</span></h3>

            <b>Entry :</b> {sig['entry']}  
            <br>
            <b>Stop Loss :</b> {sig['sl']}  
            <br>
            <b>Take Profit :</b> {sig['tp']}  

            <br><br>

            <small>🕒 {sig['date']}</small>

            </div>
            """,
            unsafe_allow_html=True
        )

# -----------------------------
# AUTO REFRESH
# -----------------------------
st.sidebar.divider()

if st.sidebar.button("🔄 Rafraîchir"):
    st.rerun()

st.sidebar.caption("Signal Bot Pro")
