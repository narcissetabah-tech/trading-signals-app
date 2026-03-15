import streamlit as st
import pandas as pd
import os
import uuid
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

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
    try:
        df = pd.read_csv(DATA_FILE)
        df["date"] = pd.to_datetime(df["date"])
    except:
        df = pd.DataFrame()
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
with st.form("new_signal_form", clear_on_submit=True):
    st.subheader("Add New Signal")
    col_a, col_b = st.columns(2)
    pair = col_a.text_input("Pair")
    sens = col_b.selectbox("Sens", ["BUY", "SELL"])
    
    col_c, col_d, col_e, col_f = st.columns(4)
    entry = col_c.number_input("Entry", value=0.0, format="%.4f")
    sl = col_d.number_input("SL", value=0.0, format="%.4f")
    tp = col_e.number_input("TP", value=0.0, format="%.4f")
    rr = col_f.number_input("RR", value=0.0, format="%.2f")
    
    submitted = st.form_submit_button("Add Signal")
    if submitted:
        new_row = pd.DataFrame([{
            "id": str(uuid.uuid4()),
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
        st.rerun()

st.divider()

# -------------------------
# ANALYSE & AFFICHAGE
# -------------------------
if not df.empty:
    # Stats
    wins = len(df[df["result"]=="win"])
    losses = len(df[df["result"]=="loss"])
    closed = wins + losses
    winrate = round((wins/closed)*100,2) if closed>0 else 0
    profit_r = df.apply(lambda t: float(t["rr"]) if t["result"]=="win" else -1 if t["result"]=="loss" else 0, axis=1).sum()

    col1,col2,col3,col4,col5 = st.columns(5)
    col1.metric("Signals", len(df))
    col2.metric("Wins", wins)
    col3.metric("Losses", losses)
    col4.metric("Winrate", f"{winrate}%")
    col5.metric("Profit (R)", round(profit_r,2))

    st.divider()

    # Graph
    perf = df.copy()
    perf["profit"] = perf.apply(lambda t: float(t["rr"]) if t["result"]=="win" else -1 if t["result"]=="loss" else 0, axis=1)
    perf["equity"] = perf["profit"].cumsum()

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=perf["date"], y=perf["equity"], mode="lines+markers", line=dict(width=3)))
    fig.update_layout(title="Equity Curve", template="plotly_dark", height=400)
    st.plotly_chart(fig, use_container_width=True)

    # Liste des signaux
    st.subheader("Signals")
    selected = st.selectbox("Filter Pair", ["All"] + list(df["pair"].unique()))
    
    filtered_df = df if selected == "All" else df[df["pair"] == selected]
    
    for _, sig in filtered_df.iloc[::-1].iterrows():
        card_class = "buy" if sig["sens"] == "BUY" else "sell"
        with st.container():
            st.markdown(f'<div class="signal-card {card_class}">', unsafe_allow_html=True)
            c1, c2 = st.columns([3, 1])
            with c1:
                st.subheader(f"{sig['pair']} — {sig['sens']}")
                st.write(f"Entry: {sig['entry']} | SL: {sig['sl']} | TP: {sig['tp']} | RR: {sig['rr']}")
                
                if sig["result"] == "open":
                    b1, b2 = st.columns(2)
                    if b1.button("🏆 WIN", key=f"win{sig['id']}"):
                        df.loc[df["id"]==sig["id"], "result"] = "win"
                        df.to_csv(DATA_FILE, index=False)
                        st.rerun()
                    if b2.button("❌ LOSS", key=f"loss{sig['id']}"):
                        df.loc[df["id"]==sig["id"], "result"] = "loss"
                        df.to_csv(DATA_FILE, index=False)
                        st.rerun()
                else:
                    st.write(f"Status: **{sig['result'].upper()}**")
            with c2:
                st.caption(pd.to_datetime(sig["date"]).strftime("%Y-%m-%d %H:%M"))
            st.markdown("</div>", unsafe_allow_html=True)
else:
    st.info("No signals found. Add one to start tracking!")
