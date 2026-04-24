from flask import Flask, send_from_directory
import os

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

@app.route("/")
def dashboard():
    return send_from_directory(BASE_DIR, "dashboard.html")

@app.route("/call_sheet.csv")
def data():
    return send_from_directory(BASE_DIR, "call_sheet.csv")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)