from flask import Flask, send_from_directory, send_file
import os

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ✅ Serve dashboard UI
@app.route("/")
def dashboard():
    return send_from_directory(BASE_DIR, "dashboard.html")

# ✅ Serve CSV correctly
@app.route("/call_sheet.csv")
def call_sheet():
    file_path = os.path.join(BASE_DIR, "call_sheet.csv")

    if not os.path.exists(file_path):
        return "CSV NOT FOUND", 404

    return send_file(file_path)

# ✅ Run server
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port)