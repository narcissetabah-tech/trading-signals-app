import streamlit as st
import pandas as pd
import os
from threading import Thread
from flask import Flask, request, jsonify

# --- PARTIE 1 : RÉCEPTEUR API (FLASK) ---
app = Flask(__name__)
DATA_FILE = "signals_history.csv"

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    new_sig = pd.DataFrame([{
        "date": pd.Timestamp.now().strftime("%d %b, %H:%M"),
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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
    
# Lancement du récepteur en arrière-plan
if 'flask_started' not in st.session_state:
    Thread(target=run_flask, daemon=True).start()
    st.session_state['flask_started'] = True

# --- PARTIE 2 : INTERFACE (STREAMLIT) ---
st.set_page_config(page_title="Signal Bot", page_icon="📈")
st.title("💎 Signal Institutionnel Live de Mr Allamine")

if os.path.exists(DATA_FILE):
    df = pd.read_csv(DATA_FILE)
    for _, sig in df.iloc[::-1].iterrows():
        with st.chat_message("assistant", avatar="📈"):
            st.markdown(f"**PAIR :** {sig['pair']}\n**SENS :** {sig['sens']}")
            st.divider()
            st.write(f"🎯 **ENTRY :** {sig['entry']} | 🛑 **SL :** {sig['sl']} | ✅ **TP :** {sig['tp']}")
            st.caption(f"🕒 {sig['date']}")
else:
    st.info("Aucun signal reçu pour le moment...")
