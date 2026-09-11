from flask import Flask, jsonify

app = Flask(__name__)


@app.route("/")
def home():
    return jsonify({
        "app": "KAJIMINYI",
        "message": "Bienvenue sur le backend KAJIMINYI",
        "status": "online"
    })


@app.route("/api/test")
def test():
    return jsonify({
        "success": True,
        "message": "API KAJIMINYI fonctionne !"
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
