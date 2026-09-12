import os
import psycopg
from flask import Flask, jsonify

app = Flask(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL")


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


@app.route("/api/db-test")
def db_test():
    try:
        if not DATABASE_URL:
            return jsonify({
                "success": False,
                "message": "DATABASE_URL n'est pas configurée"
            }), 500

        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()

        return jsonify({
            "success": True,
            "message": "Connexion à PostgreSQL réussie !",
            "result": result[0]
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Erreur de connexion à PostgreSQL",
            "error": str(e)
        }), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
