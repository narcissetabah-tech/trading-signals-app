import streamlit as st
import pandas as pd
import os
import uuid
import plotly.graph_objects as go

# -------------------------
# CONFIG PAGE
# -------------------------

st.set_page_config(
    page_title="Institutional Signal Dashboard",
    page_icon="📈",
    layout="wide"
)

DATA_FILE = "signals_history.csv"

# -------------------------
# STYLE
# -------------------------

st.markdown("""
<style>
.block-container{padding-top:2rem;}
.signal-card{border-radius:14px;padding:20px;margin-bottom:15px;background:rgba(40,40,40,0.05);}
.buy{border-left:6px solid #00c853;}
.sell{border-left:6px solid #ff3d00;}
</style>
""", unsafe_allow_html=True)

# -------------------------
# LOAD DATA
# -------------------------

if os.path.exists(DATA_FILE):
    df = pd.read_csv(DATA_FILE)
    df["date"] = pd.to_datetime(df["date"])
else:
    df = pd.DataFrame()

# -------------------------
# HEADER
# -------------------------

st.title("💎 Institutional Signal Dashboard")
st.caption("Live Trading Signal Monitor")

# -------------------------
# FORMULAIRE AJOUT SIGNAL
# -------------------------

with st.form("new_signal_form"):
    st.subheader("Add New Signal")
    pair = st.text_input("Pair")
    sens = st.selectbox("Sens", ["BUY", "SELL"])
    entry = st.number_input("Entry", value=0.0)
    sl = st.number_input("SL", value=0.0)
    tp = st.number_input("TP", value=0.0)
    rr = st.number_input("RR", value=0.0)
    submitted = st.form_submit_button("Add Signal")
    if submitted:
        new_id = str(uuid.uuid4())
        new_row = pd.DataFrame([{
            "id": new_id,
            "date": pd.Timestamp.now(),
            "pair": pair,
            "sens": sens,
            "entry": entry,
            "sl": sl,
            "tp": tp,
            "rr": rr,
            "result": "open"
        }])
        if os.path.exists(DATA_FILE):
            new_row.to_csv(DATA_FILE, mode="a", header=False, index=False)
        else:
            new_row.to_csv(DATA_FILE, index=False)
        st.success(f"Signal {pair} added!")

st.divider()

# -------------------------
# NOTIFICATION DU DERNIER SIGNAL
# -------------------------

if not df.empty:
    last = df.iloc[-1]
    st.success(f"Last Signal → {last['pair']} {last['sens']} | Entry {last['entry']}")

# -------------------------
# STATISTIQUES
# -------------------------

if not df.empty:
    total = len(df)
    wins = len(df[df["result"]=="win"])
    losses = len(df[df["result"]=="loss"])
    closed = wins + losses
    winrate = round((wins/closed)*100,2) if closed>0 else 0
    profit_r = sum(df.apply(lambda t: float(t["rr"]) if t["result"]=="win" else -1 if t["result"]=="loss" else 0, axis=1))

    col1,col2,col3,col4,col5 = st.columns(5)
    col1.metric("Signals", total)
    col2.metric("Wins", wins)
    col3.metric("Losses", losses)
    col4.metric("Winrate", f"{winrate}%")
    col5.metric("Profit (R)", round(profit_r,2))

st.divider()

# -------------------------
# EQUITY CURVE
# -------------------------

if not df.empty:
    perf = df.copy()
    perf["profit"] = perf.apply(lambda t: float(t["rr"]) if t["result"]=="win" else -1 if t["result"]=="loss" else 0, axis=1)
    perf["equity"] = perf["profit"].cumsum()

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=perf["date"], y=perf["equity"], mode="lines", line=dict(width=3)))
    fig.update_layout(title="Equity Curve", template="plotly_dark", height=400)
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# -------------------------
# STATISTIQUES PAR PAIRE
# -------------------------

if not df.empty:
    st.subheader("Pair Statistics")
    pair_stats = []
    for pair_name in df["pair"].unique():
        sub = df[df["pair"]==pair_name]
        w = len(sub[sub["result"]=="win"])
        l = len(sub[sub["result"]=="loss"])
        c = w+l
        wr = round((w/c)*100,2) if c>0 else 0
        pair_stats.append([pair_name,w,l,wr])
    st.dataframe(pd.DataFrame(pair_stats, columns=["Pair","Wins","Losses","Winrate"]), use_container_width=True)

st.divider()

# -------------------------
# FILTRE PAR PAIRE
# -------------------------

st.subheader("Signals")
if not df.empty:
    pairs = df["pair"].unique()
    selected = st.selectbox("Filter Pair", ["All"]+list(pairs))
    if selected!="All":
        df = df[df["pair"]==selected]

# -------------------------
# AFFICHAGE DES SIGNALS
# -------------------------

if df.empty:
    st.info("No signals received yet")
else:
    for _, sig in df.iloc[::-1].iterrows():
        buy = sig["sens"]=="BUY"
        card_class = "buy" if buy else "sell"

        with st.container():
            st.markdown(f'<div class="signal-card {card_class}">', unsafe_allow_html=True)
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
                        df_full = pd.read_csv(DATA_FILE)
                        df_full.loc[df_full["id"]==sig["id"],"result"]="win"
                        df_full.to_csv(DATA_FILE,index=False)
                        st.experimental_rerun()
                    if c2.button("❌ LOSS", key=f"loss{sig['id']}"):
                        df_full = pd.read_csv(DATA_FILE)
                        df_full.loc[df_full["id"]==sig["id"],"result"]="loss"
                        df_full.to_csv(DATA_FILE,index=False)
                        st.experimental_rerun()
                elif sig["result"]=="win":
                    st.success("WIN")
                elif sig["result"]=="loss":
                    st.error("LOSS")
                st.caption(f"Trade ID : {sig['id']}")
            with col2:
                st.caption(sig["date"])
            st.markdown("</div>", unsafe_allow_html=True)
