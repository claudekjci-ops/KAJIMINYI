import os

from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg


app = Flask(__name__)
CORS(app)

DATABASE_URL = os.environ.get("DATABASE_URL")


# ============================================================
# DATABASE
# ============================================================

def get_db():
    if not DATABASE_URL:
        raise Exception("DATABASE_URL n'est pas configurée.")

    return psycopg.connect(DATABASE_URL)


# ============================================================
# TEST API
# ============================================================

@app.route("/api/test", methods=["GET"])
def api_test():
    return jsonify({
        "success": True,
        "message": "API KAJIMINYI fonctionne !"
    })


# ============================================================
# TEST DATABASE
# ============================================================

@app.route("/api/db-test", methods=["GET"])
def db_test():

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                result = cur.fetchone()[0]

        return jsonify({
            "success": True,
            "message": "Connexion à PostgreSQL réussie !",
            "result": result
        })

    except Exception as e:

        print("ERREUR DATABASE:", e)

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


# ============================================================
# INITIALISATION DATABASE
# ============================================================

@app.route("/api/init-db", methods=["GET"])
def init_db():

    try:

        with get_db() as conn:

            with conn.cursor() as cur:

                cur.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        full_name VARCHAR(150) NOT NULL,
                        phone VARCHAR(30) UNIQUE NOT NULL,
                        email VARCHAR(150) UNIQUE,
                        password_hash VARCHAR(255) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                cur.execute("""
                    CREATE TABLE IF NOT EXISTS groups (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(150) NOT NULL,
                        description TEXT,
                        photo_url TEXT,
                        created_by INTEGER NOT NULL
                            REFERENCES users(id)
                            ON DELETE CASCADE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                cur.execute("""
                    CREATE TABLE IF NOT EXISTS group_members (
                        id SERIAL PRIMARY KEY,
                        group_id INTEGER NOT NULL
                            REFERENCES groups(id)
                            ON DELETE CASCADE,
                        user_id INTEGER NOT NULL
                            REFERENCES users(id)
                            ON DELETE CASCADE,
                        role VARCHAR(20) DEFAULT 'member',
                        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(group_id, user_id)
                    )
                """)

                conn.commit()

        return jsonify({
            "success": True,
            "message": "Base de données KAJIMINYI initialisée."
        })

    except Exception as e:

        print("ERREUR INIT DB:", e)

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


# ============================================================
# INSCRIPTION
# ============================================================

@app.route("/api/register", methods=["POST"])
def register():

    try:

        data = request.get_json() or {}

        full_name = str(data.get("full_name", "")).strip()
        phone = str(data.get("phone", "")).strip()
        email = str(data.get("email", "")).strip()
        password = str(data.get("password", ""))

        if not full_name:
            return jsonify({
                "success": False,
                "message": "Le nom complet est obligatoire."
            }), 400

        if not phone:
            return jsonify({
                "success": False,
                "message": "Le numéro de téléphone est obligatoire."
            }), 400

        if not password:
            return jsonify({
                "success": False,
                "message": "Le mot de passe est obligatoire."
            }), 400

        if len(password) < 6:
            return jsonify({
                "success": False,
                "message": "Le mot de passe doit contenir au moins 6 caractères."
            }), 400

        password_hash = generate_password_hash(password)

        with get_db() as conn:

            with conn.cursor() as cur:

                cur.execute("""
                    SELECT id
                    FROM users
                    WHERE phone = %s
                """, (phone,))

                if cur.fetchone():

                    return jsonify({
                        "success": False,
                        "message": "Ce numéro de téléphone est déjà utilisé."
                    }), 409

                if email:

                    cur.execute("""
                        SELECT id
                        FROM users
                        WHERE email = %s
                    """, (email,))

                    if cur.fetchone():

                        return jsonify({
                            "success": False,
                            "message": "Cette adresse email est déjà utilisée."
                        }), 409

                cur.execute("""
                    INSERT INTO users
                    (
                        full_name,
                        phone,
                        email,
                        password_hash
                    )
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                """, (
                    full_name,
                    phone,
                    email if email else None,
                    password_hash
                ))

                user_id = cur.fetchone()[0]

                conn.commit()

        return jsonify({
            "success": True,
            "message": "Compte KAJIMINYI créé avec succès.",
            "user": {
                "id": user_id,
                "full_name": full_name,
                "phone": phone,
                "email": email
            }
        }), 201

    except Exception as e:

        print("ERREUR REGISTER:", e)

        return jsonify({
            "success": False,
            "message": "Erreur lors de la création du compte."
        }), 500


# ============================================================
# CONNEXION
# ============================================================

@app.route("/api/login", methods=["POST"])
def login():

    try:

        data = request.get_json() or {}

        phone = str(data.get("phone", "")).strip()
        password = str(data.get("password", ""))

        if not phone or not password:

            return jsonify({
                "success": False,
                "message": "Numéro de téléphone et mot de passe obligatoires."
            }), 400

        with get_db() as conn:

            with conn.cursor() as cur:

                cur.execute("""
                    SELECT
                        id,
                        full_name,
                        phone,
                        email,
                        password_hash,
                        created_at
                    FROM users
                    WHERE phone = %s
                """, (phone,))

                user = cur.fetchone()

        if not user:

            return jsonify({
                "success": False,
                "message": "Numéro de téléphone ou mot de passe incorrect."
            }), 401

        if not check_password_hash(user[4], password):

            return jsonify({
                "success": False,
                "message": "Numéro de téléphone ou mot de passe incorrect."
            }), 401

        return jsonify({
            "success": True,
            "message": "Connexion réussie.",
            "user": {
                "id": user[0],
                "full_name": user[1],
                "phone": user[2],
                "email": user[3],
                "created_at": (
                    user[5].isoformat()
                    if user[5]
                    else None
                )
            }
        })

    except Exception as e:

        print("ERREUR LOGIN:", e)

        return jsonify({
            "success": False,
            "message": "Erreur lors de la connexion."
        }), 500


# ============================================================
# UTILISATEURS
# ============================================================

@app.route("/api/users", methods=["GET"])
def get_users():

    try:

        with get_db() as conn:

            with conn.cursor() as cur:

                cur.execute("""
                    SELECT
                        id,
                        full_name,
                        phone,
                        email,
                        created_at
                    FROM users
                    ORDER BY full_name ASC
                """)

                rows = cur.fetchall()

        users = []

        for row in rows:

            users.append({
                "id": row[0],
                "full_name": row[1],
                "phone": row[2],
                "email": row[3],
                "created_at": row[4]
            })

        return jsonify({
            "success": True,
            "users": users
        })

    except Exception as e:

        print("ERREUR USERS:", e)

        return jsonify({
            "success": False,
            "message": "Impossible de récupérer les utilisateurs."
        }), 500


# ============================================================
# CREER UN GROUPE
# ============================================================

@app.route("/api/groups", methods=["POST"])
def create_group():

    try:

        data = request.get_json() or {}

        name = str(data.get("name", "")).strip()
        description = str(data.get("description", "")).strip()
        photo_url = str(data.get("photo_url", "")).strip()

        creator_id = data.get("creator_id")
        member_ids = data.get("member_ids", [])

        if not name:

            return jsonify({
                "success": False,
                "message": "Le nom du groupe est obligatoire."
            }), 400

        if not creator_id:

            return jsonify({
                "success": False,
                "message": "Créateur du groupe manquant."
            }), 400

        try:
            creator_id = int(creator_id)
        except Exception:

            return jsonify({
                "success": False,
                "message": "Identifiant du créateur invalide."
            }), 400

        if not isinstance(member_ids, list):
            member_ids = []

        cleaned_members = []

        for member_id in member_ids:

            try:

                member_id = int(member_id)

                if member_id not in cleaned_members:
                    cleaned_members.append(member_id)

            except Exception:
                pass

        if creator_id not in cleaned_members:
            cleaned_members.append(creator_id)

        with get_db() as conn:

            with conn.cursor() as cur:

                cur.execute("""
                    SELECT id
                    FROM users
                    WHERE id = %s
                """, (creator_id,))

                if not cur.fetchone():

                    return jsonify({
                        "success": False,
                        "message": "Créateur introuvable."
                    }), 404

                cur.execute("""
                    INSERT INTO groups
                    (
                        name,
                        description,
                        photo_url,
                        created_by
                    )
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                """, (
                    name,
                    description,
                    photo_url,
                    creator_id
                ))

                group_id = cur.fetchone()[0]

                for member_id in cleaned_members:

                    cur.execute("""
                        SELECT id
                        FROM users
                        WHERE id = %s
                    """, (member_id,))

                    if cur.fetchone():

                        role = (
                            "admin"
                            if member_id == creator_id
                            else "member"
                        )

                        cur.execute("""
                            INSERT INTO group_members
                            (
                                group_id,
                                user_id,
                                role
                            )
                            VALUES (%s, %s, %s)
                            ON CONFLICT
                            (
                                group_id,
                                user_id
                            )
                            DO NOTHING
                        """, (
                            group_id,
                            member_id,
                            role
                        ))

                conn.commit()

        return jsonify({
            "success": True,
            "message": "Groupe créé avec succès.",
            "group": {
                "id": group_id,
                "name": name,
                "description": description,
                "photo_url": photo_url,
                "created_by": creator_id
            }
        }), 201

    except Exception as e:

        print("ERREUR CREATE GROUP:", e)

        return jsonify({
            "success": False,
            "message": "Impossible de créer le groupe."
        }), 500


# ============================================================
# GROUPES
# ============================================================

@app.route("/api/groups", methods=["GET"])
def get_groups():

    try:

        user_id = request.args.get("user_id")

        if not user_id:

            return jsonify({
                "success": False,
                "message": "user_id est obligatoire."
            }), 400

        try:
            user_id = int(user_id)
        except Exception:

            return jsonify({
                "success": False,
                "message": "user_id invalide."
            }), 400

        with get_db() as conn:

            with conn.cursor() as cur:

                cur.execute("""
                    SELECT
                        g.id,
                        g.name,
                        g.description,
                        g.photo_url,
                        g.created_by,
                        g.created_at
                    FROM groups g
                    INNER JOIN group_members gm
                        ON gm.group_id = g.id
                    WHERE gm.user_id = %s
                    ORDER BY g.created_at DESC
                """, (user_id,))

                rows = cur.fetchall()

        groups = []

        for row in rows:

            groups.append({
                "id": row[0],
                "name": row[1],
                "description": row[2],
                "photo_url": row[3],
                "created_by": row[4],
                "created_at": row[5]
            })

        return jsonify({
            "success": True,
            "groups": groups
        })

    except Exception as e:

        print("ERREUR GET GROUPS:", e)

        return jsonify({
            "success": False,
            "message": "Impossible de récupérer les groupes."
        }), 500


# ============================================================
# ASSISTANT KAJIMINYI - MODE GRATUIT
# ============================================================

def assistant_local(message):

    text = message.lower().strip()

    if any(word in text for word in [
        "bonjour",
        "salut",
        "hello",
        "bonsoir",
        "coucou"
    ]):

        return (
            "Bonjour 👋 Je suis l'Assistant KAJIMINYI 🤖.\n\n"
            "Je suis là pour t'aider avec ton application "
            "et répondre à tes questions."
        )

    if (
        "qui es-tu" in text
        or "qui est tu" in text
        or "tu es qui" in text
    ):

        return (
            "Je suis l'Assistant KAJIMINYI 🤖.\n\n"
            "Je suis l'assistant intégré à l'application "
            "KAJIMINYI. Cette version fonctionne gratuitement "
            "sans utiliser de crédit OpenAI."
        )

    if "kajiminyi" in text:

        return (
            "KAJIMINYI 📱 est une application de messagerie "
            "que nous sommes en train de construire.\n\n"
            "Elle comprend notamment :\n"
            "💬 Conversations\n"
            "👥 Groupes\n"
            "📞 Appels audio\n"
            "📹 Appels vidéo\n"
            "🤖 Assistant\n"
            "👤 Profils."
        )

    if (
        "aide" in text
        or "help" in text
        or "comment utiliser" in text
    ):

        return (
            "Bien sûr 😊 Je peux t'aider avec KAJIMINYI.\n\n"
            "Tu peux utiliser :\n"
            "💬 Conversations\n"
            "👥 Groupes\n"
            "📞 Appels audio\n"
            "📹 Appels vidéo\n"
            "🤖 Assistant IA\n"
            "👤 Profil."
        )

    if (
        "fonctionnalité" in text
        or "fonctionnalites" in text
        or "fonction" in text
    ):

        return (
            "Voici les principales fonctionnalités prévues "
            "pour KAJIMINYI 🚀 :\n\n"
            "💬 Messagerie\n"
            "👥 Groupes\n"
            "📞 Appels audio\n"
            "📹 Appels vidéo\n"
            "🤖 Assistant\n"
            "👤 Profils\n"
            "🔔 Notifications\n"
            "📎 Partage de fichiers."
        )

    if "merci" in text or "thanks" in text:

        return (
            "Avec plaisir ! 😊\n\n"
            "Je suis là pour t'aider."
        )

    if "idée" in text or "idee" in text:

        return (
            "💡 Une bonne idée pour KAJIMINYI serait "
            "d'ajouter progressivement les messages vocaux, "
            "les réactions, le partage de fichiers et les "
            "appels vidéo."
        )

    if (
        "rédige" in text
        or "redige" in text
        or "écris" in text
        or "ecris" in text
    ):

        return (
            "✍️ Bien sûr.\n\n"
            "Donne-moi le type de message que tu souhaites "
            "préparer et son destinataire."
        )

    if (
        "traduis" in text
        or "traduire" in text
    ):

        return (
            "🌍 Je peux t'aider à préparer une traduction.\n\n"
            "Écris le texte à traduire et indique la langue "
            "souhaitée."
        )

    if (
        "explique" in text
        or "expliquer" in text
    ):

        return (
            "🧠 Bien sûr.\n\n"
            "Donne-moi le sujet que tu souhaites comprendre "
            "et je vais essayer de te l'expliquer simplement."
        )

    return (
        "Je comprends ta question 😊.\n\n"
        "Je fonctionne actuellement en mode gratuit KAJIMINYI, "
         "sans crédit OpenAI.\n\n"
        "Tu peux par exemple me demander :\n"
        "• « Qui es-tu ? »\n"
        "• « Qu'est-ce que KAJIMINYI ? »\n"
        "• « Donne-moi de l'aide »\n"
        "• « Quelles sont les fonctionnalités ? »"
    )


# ============================================================
# API ASSISTANT
# ============================================================

@app.route("/api/ai/chat", methods=["POST"])
def ai_chat():

    try:

        data = request.get_json() or {}

        message = str(
            data.get("message", "")
        ).strip()

        if not message:

            return jsonify({
                "success": False,
                "message": "Message vide."
            }), 400

        if len(message) > 5000:

            return jsonify({
                "success": False,
                "message": "Message trop long."
            }), 400

        history = data.get("history", [])

        if not isinstance(history, list):
            history = []

        reply = assistant_local(message)

        return jsonify({
            "success": True,
            "reply": reply,
            "model": "kajiminyi-local-free"
        })

    except Exception as e:

        print("ERREUR ASSISTANT:", e)

        return jsonify({
            "success": False,
            "message": "Erreur de l'assistant KAJIMINYI."
        }), 500


# ============================================================
# RACINE
# ============================================================

@app.route("/", methods=["GET"])
def home():

    return jsonify({
        "success": True,
        "application": "KAJIMINYI",
        "message": "Backend KAJIMINYI opérationnel.",
        "ai": "Mode local gratuit"
    })


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    port = int(
        os.environ.get("PORT", 5000)
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
