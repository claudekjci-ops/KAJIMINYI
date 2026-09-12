import os
import re

from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg


# ============================================================
# KAJIMINYI - BACKEND
# ============================================================

app = Flask(__name__)
CORS(app)

DATABASE_URL = os.environ.get("DATABASE_URL")


# ============================================================
# BASE DE DONNÉES
# ============================================================

def get_db():
    if not DATABASE_URL:
        raise Exception("DATABASE_URL n'est pas configurée.")
    return psycopg.connect(DATABASE_URL)


# ============================================================
# ROUTE TEST
# ============================================================

@app.route("/api/test", methods=["GET"])
def api_test():
    return jsonify({
        "success": True,
        "message": "API KAJIMINYI opérationnelle."
    })


# ============================================================
# TEST BASE DE DONNÉES
# ============================================================

@app.route("/api/db-test", methods=["GET"])
def db_test():
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                result = cur.fetchone()

        return jsonify({
            "success": True,
            "message": "Base de données connectée.",
            "result": result[0]
        })

    except Exception as e:
        print("ERREUR DB:", e)

        return jsonify({
            "success": False,
            "message": "Erreur de connexion à la base de données.",
            "error": str(e)
        }), 500


# ============================================================
# INITIALISATION BASE DE DONNÉES
# ============================================================

@app.route("/api/init-db", methods=["GET"])
def init_db():
    try:
        with get_db() as conn:
            with conn.cursor() as cur:

                # TABLE USERS
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
# COLONNES PROFIL
cur.execute("""
    ALTER TABLE users
    ADD COLUMN IF NOT EXISTS username VARCHAR(50)
""")

cur.execute("""
    ALTER TABLE users
    ADD COLUMN IF NOT EXISTS status VARCHAR(255)
""")

cur.execute("""
    ALTER TABLE users
    ADD COLUMN IF NOT EXISTS photo_url TEXT
""")
                # TABLE GROUPS
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

                # TABLE GROUP MEMBERS
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
            "message": "Erreur lors de l'initialisation.",
            "error": str(e)
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
                    INSERT INTO users
                    (full_name, phone, email, password_hash)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id, full_name, phone, email, created_at
                """, (
                    full_name,
                    phone,
                    email if email else None,
                    password_hash
                ))

                user = cur.fetchone()
                conn.commit()

        return jsonify({
            "success": True,
            "message": "Compte créé avec succès.",
            "user": {
                "id": user[0],
                "full_name": user[1],
                "phone": user[2],
                "email": user[3],
                "created_at": user[4]
            }
        })

    except psycopg.errors.UniqueViolation:
        return jsonify({
            "success": False,
            "message": "Ce numéro de téléphone ou cet email existe déjà."
        }), 409

    except Exception as e:
        print("ERREUR REGISTER:", e)

        return jsonify({
            "success": False,
            "message": "Erreur lors de l'inscription."
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
                "message": "Numéro et mot de passe obligatoires."
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
                "message": "Utilisateur introuvable."
            }), 401

        if not check_password_hash(user[4], password):
            return jsonify({
                "success": False,
                "message": "Mot de passe incorrect."
            }), 401

        return jsonify({
            "success": True,
            "message": "Connexion réussie.",
            "user": {
                "id": user[0],
                "full_name": user[1],
                "phone": user[2],
                "email": user[3],
                "created_at": user[5]
            }
        })

    except Exception as e:
        print("ERREUR LOGIN:", e)

        return jsonify({
            "success": False,
            "message": "Erreur lors de la connexion."
        }), 500


# ============================================================
# LISTE DES UTILISATEURS
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
# PROFIL UTILISATEUR - RÉCUPÉRER
# ============================================================

@app.route("/api/profile/<int:user_id>", methods=["GET"])
def get_profile(user_id):

    try:
        with get_db() as conn:
            with conn.cursor() as cur:

                cur.execute("""
                    SELECT
                        id,
                        full_name,
                        phone,
                        email,
                        username,
                        status,
                        photo_url,
                        created_at
                    FROM users
                    WHERE id = %s
                """, (user_id,))

                user = cur.fetchone()

        if not user:
            return jsonify({
                "success": False,
                "message": "Utilisateur introuvable."
            }), 404

        return jsonify({
            "success": True,
            "user": {
                "id": user[0],
                "full_name": user[1],
                "phone": user[2],
                "email": user[3],
                "username": user[4],
                "status": user[5],
                "photo_url": user[6],
                "created_at": user[7]
            }
        })

    except Exception as e:
        print("ERREUR PROFILE GET:", e)

        return jsonify({
            "success": False,
            "message": "Impossible de récupérer le profil."
        }), 500
# ============================================================
# PROFIL UTILISATEUR - MODIFIER
# ============================================================

@app.route("/api/profile/<int:user_id>", methods=["PUT"])
def update_profile(user_id):

    try:
        data = request.get_json() or {}

        full_name = str(data.get("full_name", "")).strip()
        username = str(data.get("username", "")).strip()
        status = str(data.get("status", "")).strip()
        photo_url = str(data.get("photo_url", "")).strip()

        if not full_name:
            return jsonify({
                "success": False,
                "message": "Le nom complet est obligatoire."
            }), 400

        if len(full_name) > 150:
            return jsonify({
                "success": False,
                "message": "Le nom est trop long."
            }), 400

        if len(username) > 50:
            return jsonify({
                "success": False,
                "message": "Le nom d'utilisateur est trop long."
            }), 400

        if len(status) > 255:
            return jsonify({
                "success": False,
                "message": "Le statut est trop long."
            }), 400

        with get_db() as conn:
            with conn.cursor() as cur:

                cur.execute("""
                    UPDATE users
                    SET
                        full_name = %s,
                        username = %s,
                        status = %s,
                        photo_url = %s
                    WHERE id = %s
                    RETURNING
                        id,
                        full_name,
                        phone,
                        email,
                        username,
                        status,
                        photo_url,
                        created_at
                """, (
                    full_name,
                    username if username else None,
                    status if status else None,
                    photo_url if photo_url else None,
                    user_id
                ))

                user = cur.fetchone()

                if not user:
                    return jsonify({
                        "success": False,
                        "message": "Utilisateur introuvable."
                    }), 404

            conn.commit()

        return jsonify({
            "success": True,
            "message": "Profil mis à jour avec succès.",
            "user": {
                "id": user[0],
                "full_name": user[1],
                "phone": user[2],
                "email": user[3],
                "username": user[4],
                "status": user[5],
                "photo_url": user[6],
                "created_at": user[7]
            }
        })

    except Exception as e:

        print("ERREUR PROFILE UPDATE:", e)

        return jsonify({
            "success": False,
            "message": "Impossible de modifier le profil."
        }), 500
# ============================================================
# CRÉER UN GROUPE
# ============================================================

@app.route("/api/groups", methods=["POST"])
def create_group():

    try:
        data = request.get_json() or {}

        name = str(data.get("name", "")).strip()
        description = str(data.get("description", "")).strip()
        photo_url = str(data.get("photo_url", "")).strip()
        created_by = data.get("created_by")
        members = data.get("members", [])

        if not name:
            return jsonify({
                "success": False,
                "message": "Le nom du groupe est obligatoire."
            }), 400

        if not created_by:
            return jsonify({
                "success": False,
                "message": "Le créateur du groupe est obligatoire."
            }), 400

        if not isinstance(members, list):
            members = []

        with get_db() as conn:
            with conn.cursor() as cur:

                # Vérifier créateur
                cur.execute("""
                    SELECT id
                    FROM users
                    WHERE id = %s
                """, (created_by,))

                creator = cur.fetchone()

                if not creator:
                    return jsonify({
                        "success": False,
                        "message": "Utilisateur créateur introuvable."
                    }), 404

                # Créer groupe
                cur.execute("""
                    INSERT INTO groups
                    (name, description, photo_url, created_by)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id, name, description, photo_url,
                              created_by, created_at
                """, (
                    name,
                    description,
                    photo_url if photo_url else None,
                    created_by
                ))

                group = cur.fetchone()

                group_id = group[0]

                # Ajouter créateur
                cur.execute("""
                    INSERT INTO group_members
                    (group_id, user_id, role)
                    VALUES (%s, %s, 'admin')
                    ON CONFLICT (group_id, user_id)
                    DO NOTHING
                """, (group_id, created_by))

                # Ajouter membres
                for user_id in members:

                    try:
                        user_id = int(user_id)
                    except:
                        continue

                    cur.execute("""
                        SELECT id
                        FROM users
                        WHERE id = %s
                    """, (user_id,))

                    if cur.fetchone():

                        cur.execute("""
                            INSERT INTO group_members
                            (group_id, user_id, role)
                            VALUES (%s, %s, 'member')
                            ON CONFLICT (group_id, user_id)
                            DO NOTHING
                        """, (
                            group_id,
                            user_id
                        ))

                conn.commit()

        return jsonify({
            "success": True,
            "message": "Groupe créé avec succès.",
            "group": {
                "id": group[0],
                "name": group[1],
                "description": group[2],
                "photo_url": group[3],
                "created_by": group[4],
                "created_at": group[5]
            }
        })

    except Exception as e:
        print("ERREUR CREATE GROUP:", e)

        return jsonify({
            "success": False,
            "message": "Erreur lors de la création du groupe."
        }), 500


# ============================================================
# LISTE DES GROUPES D'UN UTILISATEUR
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
# ASSISTANT IA LOCAL GRATUIT
# ============================================================

def assistant_local(message):

    text = message.lower().strip()

    # --------------------------------------------------------
    # SALUTATIONS
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # IDENTITÉ
    # --------------------------------------------------------

    if (
        "qui es tu" in text
        or "qui es-tu" in text
        or "tu es qui" in text
    ):
        return (
            "Je suis l'Assistant IA de KAJIMINYI 🤖.\n\n"
            "Je peux t'aider à utiliser l'application, "
            "rédiger du contenu, trouver des idées, "
            "traduire des textes et expliquer différents sujets.\n\n"
            "Je fonctionne actuellement en mode gratuit."
        )

    # --------------------------------------------------------
    # KAJIMINYI
    # --------------------------------------------------------

    if "kajiminyi" in text:

        return (
            "KAJIMINYI 📱 est une application de communication "
            "qui rassemble plusieurs fonctionnalités :\n\n"
            "💬 Messages\n"
            "👥 Groupes\n"
            "📞 Appels audio\n"
            "🎥 Appels vidéo\n"
            "🤖 Assistant IA\n"
            "✍️ Créateur IA\n"
            "🌍 Traduction\n"
            "👤 Profil\n\n"
            "L'objectif est de créer une plateforme complète "
            "de communication."
        )

    # --------------------------------------------------------
    # AIDE
    # --------------------------------------------------------

    if "aide" in text or "help" in text:

        return (
            "Je peux t'aider avec :\n\n"
            "💬 l'application KAJIMINYI\n"
            "✍️ la rédaction\n"
            "📢 la publicité\n"
            "📱 les publications Facebook\n"
            "🎬 les scripts vidéo\n"
            "🌍 la traduction\n"
            "💡 les idées de contenu\n"
            "📚 les explications\n\n"
            "Essaie par exemple :\n"
            "« Rédige une publicité pour mon produit »."
        )

    # --------------------------------------------------------
    # FONCTIONNALITÉS
    # --------------------------------------------------------

    if (
        "fonctionnalité" in text
        or "fonctionnalites" in text
        or "que peux tu faire" in text
        or "que peux-tu faire" in text
    ):

        return (
            "Voici ce que KAJIMINYI prépare pour toi 🚀 :\n\n"
            "• Messagerie\n"
            "• Groupes\n"
            "• Appels audio et vidéo\n"
            "• Assistant IA\n"
            "• Créateur de contenu IA\n"
            "• Traduction\n"
            "• Profil utilisateur\n"
            "• Partage de fichiers\n"
            "• Historique\n\n"
            "Le projet est construit progressivement."
        )

    # --------------------------------------------------------
    # REMERCIEMENT
    # --------------------------------------------------------

    if any(word in text for word in [
        "merci",
        "thanks",
        "thank you"
    ]):

        return "Avec plaisir ! 😊\nJe suis là pour t'aider."

    # --------------------------------------------------------
    # IDÉES
    # --------------------------------------------------------

    if (
        "idée" in text
        or "idee" in text
        or "suggestion" in text
    ):

        return (
            "Voici quelques idées pour KAJIMINYI 💡 :\n\n"
            "1️⃣ Statuts comme dans les applications modernes\n"
            "2️⃣ Réactions aux messages ❤️\n"
            "3️⃣ Messages vocaux 🎙️\n"
            "4️⃣ Partage de documents 📎\n"
            "5️⃣ Appels vidéo de groupe 🎥\n"
            "6️⃣ Assistant IA 🤖\n"
            "7️⃣ Créateur de contenu IA ✍️\n"
            "8️⃣ Traduction automatique 🌍"
        )

    # --------------------------------------------------------
    # RÉDACTION
    # --------------------------------------------------------

    if (
        "rédige" in text
        or "redige" in text
        or "écris" in text
        or "ecris" in text
        or "écrire" in text
        or "ecrire" in text
    ):

        return (
         "Bien sûr ✍️.\n\n"
            "Dis-moi simplement :\n"
            "• ce que tu veux rédiger ;\n"
            "• pour qui ;\n"
            "• le ton souhaité.\n\n"
            "Exemple :\n"
            "« Rédige une publicité professionnelle "
            "pour une boutique de vêtements. »"
        )

    # --------------------------------------------------------
    # TRADUCTION
    # --------------------------------------------------------

    if (
        "traduis" in text
        or "traduire" in text
        or "traduction" in text
    ):

        return (
            "🌍 Je peux t'aider pour une traduction.\n\n"
            "Envoie-moi le texte et indique la langue "
            "souhaitée : français, anglais, Lingala, etc."
        )

    # --------------------------------------------------------
    # EXPLICATION
    # --------------------------------------------------------

    if (
        "explique" in text
        or "expliquer" in text
        or "explication" in text
    ):

        return (
            "📚 Bien sûr.\n\n"
            "Indique-moi simplement le sujet que tu veux "
            "comprendre et je vais te l'expliquer "
            "de manière simple."
        )

    # --------------------------------------------------------
    # RÉPONSE PAR DÉFAUT
    # --------------------------------------------------------

    return (
        "🤖 Je suis actuellement en mode IA gratuit KAJIMINYI.\n\n"
        "Je peux notamment t'aider à :\n"
        "• rédiger du contenu ;\n"
        "• créer des publicités ;\n"
        "• traduire ;\n"
        "• trouver des idées ;\n"
        "• expliquer un sujet ;\n"
        "• travailler sur ton application KAJIMINYI.\n\n"
        "Essaie une demande précise, par exemple :\n"
        "« Crée une publicité Facebook pour mon produit. »"
    )


# ============================================================
# ASSISTANT IA
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
# CRÉATEUR IA LOCAL
# ============================================================

def clean_text(value, default=""):

    if value is None:
        return default

    return str(value).strip()


def creator_local(
    content_type,
    platform,
    subject,
    language,
    tone,
    length,
    extra
):

    content_type = clean_text(
        content_type,
        "Publication"
    )

    platform = clean_text(
        platform,
        "Réseaux sociaux"
    )

    subject = clean_text(
        subject,
        "mon activité"
    )

    language = clean_text(
        language,
        "Français"
    )

    tone = clean_text(
        tone,
        "Professionnel"
    )

    length = clean_text(
        length,
        "Moyen"
    )

    extra = clean_text(extra)

    # ========================================================
    # NORMALISATION
    # ========================================================

    ct = content_type.lower()
    pf = platform.lower()
    ln = language.lower()

    # ========================================================
    # FACEBOOK
    # ========================================================

    if (
        "facebook" in ct
        or "facebook" in pf
        or "publication" in ct
        or "post" in ct
    ):

        result = (
            f"🚀 Découvrez {subject} !\n\n"
            f"Vous recherchez une solution simple, "
            f"efficace et adaptée à vos besoins ?\n\n"
            f"✨ {subject} est là pour vous accompagner "
            f"avec qualité et professionnalisme.\n\n"
            f"📌 Une solution pensée pour vous.\n"
            f"📲 Contactez-nous dès maintenant pour en savoir plus.\n\n"
            f"#KAJIMINYI #Innovation #Qualité #Business"
        )

    # ========================================================
    # PUBLICITÉ
    # ========================================================

    elif (
        "publicité" in ct
        or "publicite" in ct
        or "advertising" in ct
        or "annonce" in ct
    ):

        result = (
            f"🔥 NE PASSEZ PAS À CÔTÉ ! 🔥\n\n"
            f"Découvrez {subject}.\n\n"
            f"Vous cherchez une solution fiable et efficace ?\n"
            f"Nous avons ce qu'il vous faut.\n\n"
            f"✅ Qualité\n"
            f"✅ Service professionnel\n"
            f"✅ Solution adaptée\n\n"
            f"📞 Contactez-nous aujourd'hui.\n\n"
            f"👉 Faites le choix de la qualité !"
        )

    # ========================================================
    # LÉGENDE PHOTO
    # ========================================================

    elif (
        "photo" in ct
        or "légende" in ct
        or "legende" in ct
        or "caption" in ct
    ):

        result = (
            f"✨ Un moment, une vision, une histoire.\n\n"
            f"{subject} représente bien plus qu'une simple image : "
            f"c'est une expérience à partager.\n\n"
            f"📸 Chaque instant compte.\n\n"
            f"#Moment #Inspiration #KAJIMINYI"
        )

    # ========================================================
    # SCRIPT VIDÉO
    # ========================================================

    elif (
        "vidéo" in ct
        or "video" in ct
        or "script" in ct
    ):

        result = (
            f"🎬 SCRIPT VIDÉO — {subject.upper()}\n\n"
            f"SCÈNE 1 — INTRODUCTION\n"
            f"Présentez rapidement le sujet et attirez "
            f"l'attention du public.\n\n"
            f"SCÈNE 2 — PROBLÈME\n"
            f"Expliquez le besoin ou le problème rencontré "
            f"par votre audience.\n\n"
            f"SCÈNE 3 — SOLUTION\n"
            f"Présentez {subject} comme une solution.\n\n"
            f"SCÈNE 4 — AVANTAGE\n"
            f"Montrez clairement pourquoi cette solution "
            f"est intéressante.\n\n"
            f"SCÈNE 5 — APPEL À L'ACTION\n"
            f"Invitez les spectateurs à vous contacter "
            f"ou à passer à l'action.\n\n"
            f"🎙️ Ton : {tone}"
        )

    # ========================================================
    # MESSAGE PROFESSIONNEL
    # ========================================================

    elif (
        "message" in ct
        or "professionnel" in ct
        or "whatsapp" in ct
    ):

        result = (
            f"Bonjour,\n\n"
            f"Je vous contacte concernant {subject}.\n\n"
            f"Nous souhaitons vous présenter une solution "
            f"professionnelle qui pourrait répondre à vos besoins.\n\n"
            f"Je reste disponible pour vous fournir davantage "
            f"d'informations et échanger avec vous.\n\n"
            f"Bien cordialement."
        )

    # ========================================================
    # LETTRE
    # ========================================================

    elif "lettre" in ct:

        result = (
            f"Objet : {subject}\n\n"
            f"Madame, Monsieur,\n\n"
            f"Je me permets de vous adresser ce message "
            f"afin de vous présenter ma demande concernant "
            f"{subject}.\n\n"
            f"Je serais heureux(se) de pouvoir échanger avec "
            f"vous afin de vous fournir davantage "
            f"d'informations.\n\n"
            f"Je vous remercie pour votre attention et reste "
            f"à votre disposition.\n\n"
            f"Veuillez recevoir mes salutations distinguées."
        )

    # ========================================================
    # ARTICLE
    # ========================================================

    elif "article" in ct:

        result = (
            f"# {subject}\n\n"
            f"## Introduction\n\n"
            f"{subject} est aujourd'hui un sujet qui mérite "
            f"une attention particulière.\n\n"
            f"## Pourquoi ce sujet est important\n\n"
            f"Comprendre les enjeux permet de mieux identifier "
            f"les opportunités et les solutions disponibles.\n\n"
            f"## Les principaux avantages\n\n"
            f"Une bonne approche permet d'améliorer l'efficacité, "
            f"la qualité et l'expérience des utilisateurs.\n\n"
            f"## Conclusion\n\n"
            f"En conclusion, {subject} représente une opportunité "
            f"importante pour celles et ceux qui souhaitent "
            f"progresser et obtenir de meilleurs résultats."
        )

    # ========================================================
    # HASHTAGS
    # ========================================================

    elif (
        "hashtag" in ct
        or "hashtags" in ct
    ):

        words = re.findall(
            r"[a-zA-ZÀ-ÿ0-9]+",
            subject
        )

        hashtags = [
            "#KAJIMINYI",
            "#Innovation",
            "#Business",
            "#Communication",
            "#Digital"
        ]

        for word in words[:5]:

            clean_word = word.capitalize()

            if len(clean_word) > 2:
                hashtags.append("#" + clean_word)

        result = " ".join(hashtags)

    # ========================================================
    # STATUT WHATSAPP
    # ========================================================

    elif "statut" in ct:

        result = (
            f"✨ Aujourd'hui, je choisis d'avancer.\n\n"
            f"Chaque étape compte et chaque expérience "
            f"nous rapproche de nos objectifs.\n\n"
            f"🚀 {subject}\n\n"
            f"#Motivation #Objectif #KAJIMINYI"
        )

    # ========================================================
    # BIO
    # ========================================================

    elif "bio" in ct or "profil" in ct:

        result = (
            f"🚀 Passionné(e) par {subject}.\n"
            f"💡 Créativité • Innovation • Ambition\n"
            f"🌍 Toujours apprendre, créer et avancer.\n"
            f"📱 KAJIMINYI"
        )

    # ========================================================
    # CRÉATION GÉNÉRALE
    # ========================================================

    else:

        result = (
            f"✨ Création KAJIMINYI\n\n"
            f"Sujet : {subject}\n\n"
            f"Voici une proposition {tone.lower()} "
            f"adaptée à {platform} :\n\n"
            f"{subject} représente une belle opportunité "
            f"de créer de la valeur, de communiquer efficacement "
            f"et de toucher votre audience.\n\n"
            f"Notre objectif est de proposer une expérience "
            f"simple, moderne et adaptée aux besoins du public.\n\n"
            f"🚀 Passez à l'action dès aujourd'hui !"
        )

    # ========================================================
    # INFORMATIONS SUPPLÉMENTAIRES
    # ========================================================

    if extra:

        result += (
            "\n\n────────────────────\n"
            "📌 Informations supplémentaires\n\n"
            f"{extra}"
        )

    # ========================================================
    # LANGUES
    # ========================================================

    # Pour le moment, le générateur gratuit produit
    # principalement en français.
    # L'architecture accepte déjà la langue pour
    # permettre l'amélioration future.

    if ln not in [
        "français",
        "francais",
        "fr",
        ""
    ]:

        result += (
            f"\n\n🌍 Langue demandée : {language}\n"
            "La génération multilingue avancée sera "
            "activée avec le moteur IA en ligne."
        )

    return result


# ============================================================
# API CRÉATEUR IA
# ============================================================

@app.route("/api/ai/create", methods=["POST"])
def ai_create():

    try:

        data = request.get_json() or {}

        content_type = clean_text(
            data.get("content_type"),
            "Publication"
        )

        platform = clean_text(
            data.get("platform"),
            "Réseaux sociaux"
        )

        subject = clean_text(
            data.get("subject"),
            ""
        )

        language = clean_text(
            data.get("language"),
            "Français"
        )

        tone = clean_text(
            data.get("tone"),
            "Professionnel"
        )

        length = clean_text(
            data.get("length"),
            "Moyen"
        )

        extra = clean_text(
            data.get("extra"),
            ""
        )

        # ----------------------------------------------------
        # Vérifications
        # ----------------------------------------------------

        if not subject:

            return jsonify({
                "success": False,
                "message": "Veuillez indiquer le sujet de la création."
            }), 400

        if len(subject) > 5000:

            return jsonify({
                "success": False,
                "message": "Le sujet est trop long."
            }), 400

        if len(extra) > 5000:

            return jsonify({
                "success": False,
                "message": "Les informations supplémentaires sont trop longues."
            }), 400

        # ----------------------------------------------------
        # GÉNÉRATION
        # ----------------------------------------------------

        reply = creator_local(
            content_type=content_type,
            platform=platform,
            subject=subject,
            language=language,
            tone=tone,
            length=length,
            extra=extra
        )

        return jsonify({
            "success": True,
            "reply": reply,
            "model": "kajiminyi-creator-free",
            "type": content_type,
            "platform": platform,
            "language": language,
            "tone": tone,
            "length": length
        })

    except Exception as e:

        print("ERREUR CREATEUR IA:", e)

        return jsonify({
            "success": False,
            "message": "Erreur du Créateur IA KAJIMINYI."
        }), 500


# ============================================================
# ROUTE RACINE
# ============================================================

@app.route("/", methods=["GET"])
def home():

    return jsonify({
        "success": True,
        "application": "KAJIMINYI",
        "message": "Backend KAJIMINYI opérationnel.",
        "ai": "Assistant + Créateur IA en mode gratuit",
        "endpoints": [
            "/api/test",
            "/api/db-test",
            "/api/init-db",
            "/api/register",
            "/api/login",
            "/api/users",
            "/api/groups",
            "/api/ai/chat",
            "/api/ai/create"
        ]
    })


# ============================================================
# DÉMARRAGE
# ============================================================

if __name__ == "__main__":

    port = int(
        os.environ.get("PORT", 5000)
    )

    app.run(
        host="0.0.0.0",
        port=port
        )
