FROM python:3.9-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
EXPOSE 8080
# Commande pour lancer Streamlit sur le port 8080 exigé par Google Cloud
CMD ["streamlit", "run", "signal_app.py", "--server.port=8080", "--server.address=0.0.0.0"]
