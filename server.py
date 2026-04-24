from flask import Flask, send_from_directory
import os

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

@app.route("/")
def dashboard():
    return send_from_directory(BASE_DIR, "dashboard.html")

# 🔥 THIS IS THE FIX
@app.route("/call_sheet.csv")
def call_sheet():
    return send_from_directory(BASE_DIR, "call_sheet.csv")

# optional raw file too
@app.route("/inventory_raw.csv")
def raw():
    return send_from_directory(BASE_DIR, "inventory_raw.csv")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)