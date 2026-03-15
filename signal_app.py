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

try:
    # On vérifie si les secrets existent avant de tenter d'y accéder
    if "gcp" in st.secrets:
        from google.oauth2 import service_account
        gcp_creds = st.secrets["gcp"]
        creds = service_account.Credentials.from_service_account_info(gcp_creds)
        db = firestore.Client(credentials=creds, project=gcp_creds["project_id"])
    else:
        # Si aucun secret, on tente la connexion native de la VM
        db = firestore.Client(project="tradingbot-489416")
except Exception as e:
    st.error(f"Erreur de connexion à Firestore : {e}")
    db = None

COLLECTION = "signals"

@st.cache_data(ttl=60)
def get_signals():
    try:
       docs = db.collection(COLLECTION).order_by("date", direction=firestore.Query.DESCENDING).stream()
       data = [doc.to_dict() for doc in docs]
       return pd.DataFrame(data) if data else pd.DataFrame()
    except Exception as e:
        st.error(f"erreur : {e} ")
        return pd.DataFrame()
        
df = get_signals()

# -------------------------
# CONFIG PAGE
# -------------------------

st.set_page_config(
    page_title="Institutional Signal Dashboard",
    page_icon="📈",
    layout="wide"
)

st_autorefresh(interval=5000, key="refresh")

# -------------------------
# STYLE
# -------------------------

st.markdown("""
<style>

.block-container{
padding-top:2rem;
}

.metric-card{
background-color: rgba(30,30,30,0.05);
padding:20px;
border-radius:12px;
}

.signal-card{
border-radius:14px;
padding:20px;
margin-bottom:15px;
background:rgba(40,40,40,0.05);
border-left:6px solid #3b82f6;
}

.buy{
border-left:6px solid #00c853;
}

.sell{
border-left:6px solid #ff3d00;
}

</style>
""", unsafe_allow_html=True)

# -------------------------
# FLASK API
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
    
    # Sauvegarde dans Firestore
    db.collection(COLLECTION).document(trade_id).set(signal_data)
    return jsonify({"trade_id": trade_id})

def run_flask():
    app.run(host="0.0.0.0", port=5001)

if "flask_started" not in st.session_state:
    Thread(target=run_flask, daemon=True).start()
    st.session_state["flask_started"] = True

# -------------------------
# HEADER
# -------------------------

st.title("💎 Institutional Signal Dashboard")
st.caption("Live Trading Signal Monitor")

# --- LOGIQUE FIRESTORE ---

def get_signals():
    """Récupère les données depuis Firestore"""
    docs = db.collection(COLLECTION).order_by("date", direction=firestore.Query.DESCENDING).stream()
    data = [doc.to_dict() for doc in docs]
    return pd.DataFrame(data) if data else pd.DataFrame()

# -------------------------
# NOTIFICATION
# -------------------------

if not df.empty:

    last = df.iloc[-1]

    st.success(
        f"New Signal → {last['pair']} {last['sens']} | Entry {last['entry']}"
    )

# -------------------------
# STATS
# -------------------------

if not df.empty:

    total = len(df)
    wins = len(df[df["result"]=="win"])
    losses = len(df[df["result"]=="loss"])

    closed = wins + losses

    winrate = 0
    if closed > 0:
        winrate = round((wins/closed)*100,2)

    profit_r = 0

    for _, t in df.iterrows():
        if t["result"] == "win":
            rr_str = str(t["rr"])
            if ":" in rr_str:
                rr_val = float(rr_str.split(":")[1])
            else:
                rr_val = float(rr_str)
            profit_r += rr_val
        if t["result"] == "loss":
            profit_r -= 1
        
    col1,col2,col3,col4,col5 = st.columns(5)

    col1.metric("Signals", total)
    col2.metric("Wins", wins)
    col3.metric("Losses", losses)
    col4.metric("Winrate", f"{winrate}%")
    col5.metric("Profit (R)", round(profit_r,2))

st.divider()

# -------------------------
# EQUITY GRAPH
# -------------------------

if not df.empty:

    perf = df.copy()

    perf["profit"]=0

    perf.loc[perf["result"]=="win","profit"]=perf["rr"]
    perf.loc[perf["result"]=="loss","profit"]=-1

    perf["equity"]=perf["profit"].cumsum()

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=perf["date"],
            y=perf["equity"],
            mode="lines",
            line=dict(width=3)
        )
    )

    fig.update_layout(
        title="Equity Curve",
        template="plotly_dark",
        height=400
    )

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

        w = len(sub[sub["result"]=="win"])
        l = len(sub[sub["result"]=="loss"])

        c = w + l

        wr = 0
        if c>0:
            wr = round((w/c)*100,2)

        pair_stats.append([pair,w,l,wr])

    pair_df = pd.DataFrame(
        pair_stats,
        columns=["Pair","Wins","Losses","Winrate"]
    )

    st.dataframe(pair_df, use_container_width=True)

st.divider()

# -------------------------
# FILTER
# -------------------------

st.subheader("Signals")

if not df.empty:

    pairs = df["pair"].unique()

    selected = st.selectbox(
        "Filter Pair",
        ["All"] + list(pairs)
    )

    if selected != "All":
        df = df[df["pair"]==selected]

# -------------------------
# SIGNAL DISPLAY
# -------------------------

if df.empty:

    st.info("Aucun signal en base")

else:

    for _,sig in df.iloc[::-1].iterrows():

        buy = sig["sens"]=="BUY"

        card_class = "buy" if buy else "sell"

        with st.container():

            st.markdown(
                f'<div class="signal-card {card_class}">',
                unsafe_allow_html=True
            )

            col1,col2 = st.columns([3,1])

            with col1:

                direction = "🟢 BUY" if buy else "🔴 SELL"

                st.subheader(f"{sig['pair']} — {direction}")

                st.write(f"Entry : {sig['entry']}")
                st.write(f"SL : {sig['sl']}")
                st.write(f"TP : {sig['tp']}")
                st.write(f"RR : {sig['rr']}")

                if sig["result"]=="open":

                    c1,c2 = st.columns(2)

                    if c1.button("🏆 WIN", key=f"win{sig['id']}"):

                        db.collection(COLLECTION).document(sig['id']).update({"result": "win"})

                    if c2.button("❌ LOSS", key=f"loss{sig['id']}"):
                        
                       db.collection(COLLECTION).document(sig['id']).update({"result": "loss"})

                elif sig["result"]=="win":

                    st.success("WIN")

                elif sig["result"]=="loss":

                    st.error("LOSS")

                st.caption(f"Trade ID : {sig['id']}")

            with col2:

                st.caption(sig["date"])

            st.markdown("</div>", unsafe_allow_html=True)
