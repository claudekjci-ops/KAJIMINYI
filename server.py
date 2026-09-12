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


@app.route("/api/init-db")
def init_db():
    try:
        if not DATABASE_URL:
            return jsonify({
                "success": False,
                "message": "DATABASE_URL n'est pas configurée"
            }), 500

        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cursor:

                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        full_name VARCHAR(150) NOT NULL,
                        phone VARCHAR(30) UNIQUE NOT NULL,
                        email VARCHAR(150) UNIQUE,
                        password_hash VARCHAR(255) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

            conn.commit()

        return jsonify({
            "success": True,
            "message": "Table users créée avec succès !"
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Erreur lors de la création de la table users",
            "error": str(e)
        }), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
