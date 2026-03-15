import streamlit as st
import pandas as pd
import os
import uuid
import json
from threading import Thread
from flask import Flask, request, jsonify
from streamlit_autorefresh import st_autorefresh
from google.cloud import firestore
from google.oauth2 import service_account
import plotly.graph_objects as go

# -------------------------
# CONFIG PAGE & STYLE (NETTOYAGE MOBILE)
# -------------------------
st.set_page_config(
    page_title="Institutional Signal Dashboard",
    page_icon="📈",
    layout="wide"
)

# Masquer les menus de développement (Bouton Arrêt, etc.)
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display:none;}
    .block-container{ padding-top:2rem; }
    .metric-card{ background-color: rgba(30,30,30,0.05); padding:20px; border-radius:12px; }
    .signal-card{ border-radius:14px; padding:20px; margin-bottom:15px; background:rgba(40,40,40,0.05); border-left:6px solid #3b82f6; }
    .buy{ border-left:6px solid #00c853; }
    .sell{ border-left:6px solid #ff3d00; }
    </style>
    """, unsafe_allow_html=True)

st_autorefresh(interval=5000, key="refresh")

# -------------------------
# CONNEXION FIRESTORE
# -------------------------
try:
    if "gcp" in st.secrets:
        gcp_creds = st.secrets["gcp"]
        creds = service_account.Credentials.from_service_account_info(gcp_creds)
        db = firestore.Client(credentials=creds, project=gcp_creds["project_id"])
    else:
        db = firestore.Client(project="tradingbot-489416")
except Exception as e:
    st.error(f"Erreur de connexion à Firestore : {e}")
    db = None

COLLECTION = "signals"

# -------------------------
# LOGIQUE DE CALCUL (ROBUSTE)
# -------------------------
def calculate_metrics(df):
    """Calcule les wins, losses et profit R sans erreurs de format"""
    profit_r = 0.0
    wins = 0
    losses = 0
    
    for _, t in df.iterrows():
        res = str(t.get("result", "")).lower()
        rr_raw = str(t.get("rr", "0")) 
        try:
            # Gère les formats '1:2.0', 'RE:2.0' ou '2.0'
            rr_val = float(rr_raw.split(":")[-1]) if ":" in rr_raw else float(rr_raw)
        except:
            rr_val = 0.0

        if res == "win":
            profit_r += rr_val
            wins += 1
        elif res == "loss":
            profit_r -= 1.0
            losses += 1     
    return wins, losses, round(profit_r, 2)

@st.cache_data(ttl=5)
def get_signals():
    try:
        docs = db.collection(COLLECTION).order_by("date", direction=firestore.Query.DESCENDING).stream()
        data = [doc.to_dict() for doc in docs]
        return pd.DataFrame(data) if data else pd.DataFrame()
    except Exception as e:
        return pd.DataFrame()

df = get_signals()

# -------------------------
# FLASK API (GARDÉ POUR TA VM)
# -------------------------
app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    trade_id = str(uuid.uuid4())
    signal_data = {
        "id": trade_id,
        "date": firestore.SERVER_TIMESTAMP,
        "pair": data.get("pair"),
        "sens": data.get("sens"),
        "entry": data.get("entry"),
        "sl": data.get("sl"),
        "tp": data.get("tp"),
        "rr": data.get("rr"),
        "result": "open"
    }
    db.collection(COLLECTION).document(trade_id).set(signal_data)
    return jsonify({"trade_id": trade_id})

def run_flask():
    app.run(host="0.0.0.0", port=5001)

if "flask_started" not in st.session_state:
    Thread(target=run_flask, daemon=True).start()
    st.session_state["flask_started"] = True

# -------------------------
# INTERFACE UTILISATEUR
# -------------------------
st.title("💎 Institutional Signal Dashboard")
st.caption("Live Trading Signal Monitor")

if not df.empty:
    # Notification dernier signal
    last = df.iloc[0] # iloc[0] car trié par date DESC
    st.success(f"New Signal → {last['pair']} {last['sens']} | Entry {last['entry']}")

    # Calcul des stats
    wins, losses, profit_r = calculate_metrics(df)
    total = len(df)
    winrate = round((wins / (wins + losses)) * 100, 1) if (wins + losses) > 0 else 0
        
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Signals", total)
    col2.metric("Wins", wins)
    col3.metric("Losses", losses)
    col4.metric("Winrate", f"{winrate}%")
    col5.metric("Profit (R)", profit_r)

st.divider()

# -------------------------
# EQUITY GRAPH (CORRIGÉ)
# -------------------------
if not df.empty:
    perf = df.copy()
    # Nettoyage RR pour le calcul cumulatif
    perf["rr_num"] = pd.to_numeric(perf["rr"].astype(str).str.replace(r'.*:', '', regex=True), errors='coerce').fillna(0)
    
    perf["profit"] = 0.0
    perf.loc[perf["result"] == "win", "profit"] = perf["rr_num"]
    perf.loc[perf["result"] == "loss", "profit"] = -1.0
    
    # Inverser pour que le graphe soit chronologique (bas vers haut)
    perf = perf.iloc[::-1]
    perf["equity"] = perf["profit"].cumsum()

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=perf["date"], y=perf["equity"], mode="lines+markers", line=dict(color='#3b82f6', width=3)))
    fig.update_layout(title="Equity Curve (Cumulative R)", template="plotly_dark", height=400)
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# -------------------------
# PAIR STATS
# -------------------------
if not df.empty:
    st.subheader("Pair Statistics")
    pair_stats = []
    for pair in df["pair"].unique():
        sub = df[df["pair"]==pair]
        w, l, p = calculate_metrics(sub)
        wr = round((w/(w+l))*100, 2) if (w+l) > 0 else 0
        pair_stats.append([pair, w, l, wr, p])

    pair_df = pd.DataFrame(pair_stats, columns=["Pair", "Wins", "Losses", "Winrate %", "Profit R"])
    st.dataframe(pair_df, use_container_width=True, hide_index=True)

st.divider()

# -------------------------
# FILTRES ET AFFICHAGE SIGNAUX
# -------------------------
st.subheader("Signals")
if not df.empty:
    pairs = ["All"] + list(df["pair"].unique())
    selected = st.selectbox("Filter Pair", pairs)
    display_df = df if selected == "All" else df[df["pair"]==selected]

    if display_df.empty:
        st.info("Aucun signal correspondant")
    else:
        for _, sig in display_df.iterrows():
            buy = sig["sens"] == "BUY"
            card_class = "buy" if buy else "sell"
            
            st.markdown(f'<div class="signal-card {card_class}">', unsafe_allow_html=True)
            c1, c2 = st.columns([3, 1])
            
            with c1:
                direction = "🟢 BUY" if buy else "🔴 SELL"
                st.subheader(f"{sig['pair']} — {direction}")
                st.write(f"**Entry:** {sig['entry']} | **SL:** {sig['sl']} | **TP:** {sig['tp']} | **RR:** {sig['rr']}")

                if sig["result"] == "open":
                    b1, b2 = st.columns(2)
                    if b1.button("🏆 WIN", key=f"win_{sig['id']}"):
                        db.collection(COLLECTION).document(sig['id']).update({"result": "win"})
                        st.rerun()
                    if b2.button("❌ LOSS", key=f"loss_{sig['id']}"):
                        db.collection(COLLECTION).document(sig['id']).update({"result": "loss"})
                        st.rerun()
                else:
                    status_color = "green" if sig["result"] == "win" else "red"
                    st.markdown(f"**Status:** :{status_color}[{sig['result'].upper()}]")
                
                st.caption(f"ID: {sig['id']}")
            
            with c2:
                st.caption(f"Date: {sig['date']}")
            
            st.markdown("</div>", unsafe_allow_html=True)
else:
    st.info("Aucun signal en base")
