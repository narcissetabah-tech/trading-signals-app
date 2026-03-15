import streamlit as st
import pandas as pd
import os
from flask import Flask, request, jsonify
from threading import Thread

# Configuration de la page
st.set_page_config(page_title="Trading Signals Hub", layout="wide")

# Interface stylée
st.title("📈 Trading is bouddha")
st.markdown("---")

# Gestion des données
DATA_FILE = "signals.csv"

def load_data():
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE)
    return pd.DataFrame(columns=["pair", "sens", "score", "entry", "sl", "tp", "rr"])

# Sidebar pour les paramètres
st.sidebar.header("Paramètres")
refresh_rate = st.sidebar.slider("Fréquence de rafraîchissement (sec)", 5, 60, 10)

# Affichage des données
data = load_data()
st.subheader("Derniers Signaux")
st.table(data.tail(10))

# Partie API Flask pour le Webhook
app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    new_data = request.json
    df = load_data()
    df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
    df.to_csv(DATA_FILE, index=False)
    return jsonify({"status": "success"}), 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# Lancement du serveur Flask en arrière-plan
if __name__ == "__main__":
    # Démarre l'API seulement si elle n'est pas déjà lancée
    if not hasattr(st, "_flask_started"):
        Thread(target=run_flask, daemon=True).start()
        st._flask_started = True
