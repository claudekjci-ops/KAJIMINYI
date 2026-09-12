import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg
from psycopg.rows import dict_row
from werkzeug.security import generate_password_hash, check_password_hash
from openai import OpenAI


# ============================================================
# APPLICATION
# ============================================================

app = Flask(__name__)

CORS(
    app,
    resources={
        r"/api/*": {
            "origins": "*"
        }
    }
)


# ============================================================
# CONFIGURATION
# ============================================================

DATABASE_URL = os.environ.get("DATABASE_URL")

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

AI_MODEL = "gpt-5.6-luna"


# Client OpenAI
client = None

if OPENAI_API_KEY:
    client = OpenAI(
        api_key=OPENAI_API_KEY
    )


# ============================================================
# DATABASE
# ============================================================

def get_db():

    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL n'est pas configurée."
        )

    return psycopg.connect(
        DATABASE_URL,
        row_factory=dict_row
    )


# ============================================================
# CREATION DES TABLES
# ============================================================

def init_tables():

    with get_db() as conn:

        with conn.cursor() as cur:

            # USERS
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


            # GROUPS
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


            # GROUP MEMBERS
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


# ============================================================
# PAGE PRINCIPALE
# ============================================================

@app.route("/")
def home():

    return jsonify({
        "success": True,
        "message": "API KAJIMINYI fonctionne !",
        "version": "1.0"
    })


# ============================================================
# TEST API
# ============================================================

@app.route("/api/test")
def api_test():

    return jsonify({
        "success": True,
        "message": "API KAJIMINYI fonctionne !"
    })


# ============================================================
# TEST DATABASE
# ============================================================

@app.route("/api/db-test")
def db_test():

    try:

        with get_db() as conn:

            with conn.cursor() as cur:

                cur.execute(
                    "SELECT 1 AS result"
                )

                row = cur.fetchone()


        return jsonify({
            "success": True,
            "message":
                "Connexion à PostgreSQL réussie !",
            "result":
                row["result"]
        })


    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


# ============================================================
# INITIALISER DATABASE
# ============================================================

@app.route("/api/init-db")
def init_db():

    try:

        init_tables()

        return jsonify({
            "success": True,
            "message":
                "Tables KAJIMINYI créées avec succès."
        })


    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


# ============================================================
# INSCRIPTION
# ============================================================

@app.route(
    "/api/register",
    methods=["POST"]
)
def register():

    try:

        data = request.get_json() or {}

        full_name = (
            data.get("full_name") or ""
        ).strip()

        phone = (
            data.get("phone") or ""
        ).strip()

        email = (
            data.get("email") or ""
        ).strip()

        password = (
            data.get("password") or ""
        )


        if not full_name:
            return jsonify({
                "success": False,
                "message":
                    "Le nom complet est obligatoire."
            }), 400


        if not phone:
            return jsonify({
                "success": False,
                "message":
                    "Le numéro de téléphone est obligatoire."
            }), 400


        if not password:
            return jsonify({
                "success": False,
                "message":
                    "Le mot de passe est obligatoire."
            }), 400


        password_hash =
            generate_password_hash(password)


        with get_db() as conn:

            with conn.cursor() as cur:

                cur.execute("""
                    INSERT INTO users
                    (
                        full_name,
                        phone,
                        email,
                        password_hash
                    )
                    VALUES (%s, %s, %s, %s)
                    RETURNING
                        id,
                        full_name,
                        phone,
                        email,
                        created_at
                """, (
                    full_name,
                    phone,
                    email or None,
                    password_hash
                ))


                user =
                    cur.fetchone()


            conn.commit()


        return jsonify({
            "success": True,
            "message":
                "Compte créé avec succès.",
            "user": user
        }), 201


    except psycopg.errors.UniqueViolation:

        return jsonify({
            "success": False,
            "message":
                "Ce numéro ou cet email existe déjà."
        }), 409


    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


# ============================================================
# CONNEXION
# ============================================================

@app.route(
    "/api/login",
    methods=["POST"]
)
def login():

    try:

        data = request.get_json() or {}

        phone = (
            data.get("phone") or ""
        ).strip()

        password = (
            data.get("password") or ""
        )


        if not phone or not password:

            return jsonify({
                "success": False,
                "message":
                    "Téléphone et mot de passe obligatoires."
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


                user =
                    cur.fetchone()


        if not user:

            return jsonify({
                "success": False,
                "message":
                    "Numéro ou mot de passe incorrect."
            }), 401


        if not check_password_hash(
            user["password_hash"],
            password
        ):

            return jsonify({
                "success": False,
                "message":
                    "Numéro ou mot de passe incorrect."
            }), 401


        user.pop(
            "password_hash",
            None
        )


        return jsonify({
            "success": True,
            "message":
                "Connexion réussie.",
            "user": user
        })


    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


# ============================================================
# LISTE DES UTILISATEURS
# ============================================================

@app.route("/api/users")
def users():

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
                    ORDER BY created_at DESC
                """)

                users_list =
                    cur.fetchall()


        return jsonify({
            "success": True,
            "users": users_list
        })


    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


# ============================================================
# CREER UN GROUPE
# ============================================================

@app.route(
    "/api/groups",
    methods=["POST"]
)
def create_group():

    try:

        data = request.get_json() or {}

        name = (
            data.get("name") or ""
        ).strip()

        description = (
            data.get("description") or ""
        ).strip()

        photo_url = (
            data.get("photo_url") or ""
        ).strip()

        creator_id = data.get(
            "creator_id"
        )

        member_ids =
            data.get("member_ids") or []


        if not name:

            return jsonify({
                "success": False,
                "message":
                    "Le nom du groupe est obligatoire."
            }), 400


        if not creator_id:

            return jsonify({
                "success": False,
                "message":
                    "Le créateur du groupe est obligatoire."
            }), 400


        # Nettoyage des IDs
        clean_members = []

        for member_id in member_ids:

            try:

                member_id =
                    int(member_id)

                if member_id not in clean_members:

                    clean_members.append(
                        member_id
                    )

            except:

                pass


        # Le créateur doit toujours être membre
        if creator_id not in clean_members:

            clean_members.append(
                int(creator_id)
            )


        with get_db() as conn:

            with conn.cursor() as cur:

                # Vérifier créateur
                cur.execute("""
                    SELECT id
                    FROM users
                    WHERE id = %s
                """, (creator_id,))

                creator =
                    cur.fetchone()


                if not creator:

                    return jsonify({
                        "success": False,
                        "message":
                            "Utilisateur créateur introuvable."
                    }), 404


                # Créer groupe
                cur.execute("""
                    INSERT INTO groups
                    (
                        name,
                        description,
                        photo_url,
                        created_by
                    )
                    VALUES (%s, %s, %s, %s)
                    RETURNING
                        id,
                        name,
                        description,
                        photo_url,
                        created_by,
                        created_at
                """, (
                    name,
                    description or None,
                    photo_url or None,
                    creator_id
                ))


                group =
                    cur.fetchone()


                # Ajouter membres
                for member_id in clean_members:

                    role = (
                        "admin"
                        if member_id == int(creator_id)
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
                        group["id"],
                        member_id,
                        role
                    ))


            conn.commit()


        return jsonify({
            "success": True,
            "message":
                "Groupe créé avec succès.",
            "group": group
        }), 201


    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


# ============================================================
# LISTE DES GROUPES D'UN UTILISATEUR
# ============================================================

@app.route("/api/groups")
def get_groups():

    try:

        user_id =
            request.args.get(
                "user_id",
                type=int
            )


        if not user_id:

            return jsonify({
                "success": False,
                "message":
                    "user_id est obligatoire."
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


                groups =
                    cur.fetchall()


        return jsonify({
            "success": True,
            "groups": groups
        })


    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


# ============================================================
# MEMBRES D'UN GROUPE
# ============================================================

@app.route(
    "/api/groups/<int:group_id>/members"
)
def get_group_members(group_id):

    try:

        with get_db() as conn:

            with conn.cursor() as cur:

                cur.execute("""
                    SELECT
                        u.id,
                        u.full_name,
                        u.phone,
                        u.email,
                        gm.role,
                        gm.joined_at
                    FROM group_members gm
                    INNER JOIN users u
                        ON u.id = gm.user_id
                    WHERE gm.group_id = %s
                    ORDER BY gm.joined_at ASC
                """, (group_id,))


                members =
                    cur.fetchall()


        return jsonify({
            "success": True,
            "members": members
        })


    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


# ============================================================
# AJOUTER UN MEMBRE
# ============================================================

@app.route(
    "/api/groups/<int:group_id>/members",
    methods=["POST"]
)
def add_group_member(group_id):

    try:

        data = request.get_json() or {}

        user_id =
            data.get("user_id")

        role =
            data.get(
                "role",
                "member"
            )


        if not user_id:

            return jsonify({
                "success": False,
                "message":
                    "user_id est obligatoire."
            }), 400


        with get_db() as conn:

            with conn.cursor() as cur:

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
                    RETURNING
                        id,
                        group_id,
                        user_id,
                        role,
                        joined_at
                """, (
                    group_id,
                    user_id,
                    role
                ))


                member =
                    cur.fetchone()


            conn.commit()


        return jsonify({
            "success": True,
            "message":
                "Membre ajouté.",
            "member": member
        })


    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


# ============================================================
# SUPPRIMER UN GROUPE
# ============================================================

@app.route(
    "/api/groups/<int:group_id>",
    methods=["DELETE"]
)
def delete_group(group_id):

    try:

        with get_db() as conn:

            with conn.cursor() as cur:

                cur.execute("""
                    DELETE FROM groups
                    WHERE id = %s
                    RETURNING id
                """, (group_id,))


                deleted =
                    cur.fetchone()


            conn.commit()


        if not deleted:

            return jsonify({
                "success": False,
                "message":
                    "Groupe introuvable."
            }), 404


        return jsonify({
            "success": True,
            "message":
                "Groupe supprimé."
        })


    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


# ============================================================
# ===================== ASSISTANT IA =========================
# ============================================================

AI_INSTRUCTION = """
Tu es l'Assistant IA officiel intégré à l'application KAJIMINYI.

Ton nom est Assistant KAJIMINYI.

Tu dois répondre principalement en français, sauf si
l'utilisateur demande une autre langue.

Tu es chaleureux, professionnel, clair et utile.

Tu peux notamment aider avec :

- rédaction de messages
- correction de textes
- traduction
- explications
- idées
- études
- programmation
- développement de KAJIMINYI
- création de contenu
- organisation
- questions générales

Lorsque l'utilisateur demande du code,
donne du code propre et explique brièvement
comment l'utiliser.

Ne prétends jamais avoir effectué une action
que tu n'as pas réellement effectuée.

Si une information n'est pas connue,
dis-le clairement.

KAJIMINYI est une application de messagerie
développée par l'utilisateur.

L'objectif est de construire progressivement
une application moderne avec messagerie,
groupes, appels, IA et autres fonctionnalités.
"""


@app.route(
    "/api/ai/chat",
    methods=["POST"]
)
def ai_chat():

    try:

        # ----------------------------------------------------
        # Vérifier clé API
        # ----------------------------------------------------

        if not OPENAI_API_KEY or client is None:

            return jsonify({
                "success": False,
                "message":
                    "OPENAI_API_KEY n'est pas configurée sur le serveur."
            }), 500


        # ----------------------------------------------------
        # Récupérer requête
        # ----------------------------------------------------

        data =
            request.get_json() or {}


        message =
            (data.get("message") or "").strip()


        history =
            data.get("history") or []


        if not message:

            return jsonify({
                "success": False,
                "message":
                    "Le message est vide."
            }), 400


        # Limite de sécurité
        if len(message) > 12000:

            return jsonify({
                "success": False,
                "message":
                    "Message trop long."
            }), 400


        # ----------------------------------------------------
        # Construire historique
        # ----------------------------------------------------

        input_messages = []


        # On limite l'historique envoyé
        # pour garder les requêtes raisonnables.
        history = history[-12:]


        for item in history:

            role =
                item.get("role")

            content =
                item.get("content")


            if role not in [
                "user",
                "assistant"
            ]:

                continue


            if not content:
                continue


            input_messages.append({
                "role": role,
                "content": str(content)[:12000]
            })


        # ----------------------------------------------------
        # Ajouter nouveau message
        # ----------------------------------------------------

        input_messages.append({
            "role": "user",
            "content": message
        })


        # ----------------------------------------------------
        # APPEL OPENAI
        # ----------------------------------------------------

        response = client.responses.create(

            model=AI_MODEL,

            instructions=AI_INSTRUCTIONS,

            input=input_messages,

            max_output_tokens=1200
        )


        reply =
            response.output_text


        if not reply:

            reply =
                "Je n'ai pas pu générer une réponse."


        # ----------------------------------------------------
        # REPONSE AU TELEPHONE
        # ----------------------------------------------------

        return jsonify({
            "success": True,
            "reply": reply,
            "model": AI_MODEL
        })


    except Exception as e:

        print(
            "ERREUR ASSISTANT IA:",
            str(e)
        )


        return jsonify({
            "success": False,
            "message":
                "Une erreur est survenue avec l'Assistant IA."
        }), 500


# ============================================================
# DEMARRAGE
# ============================================================

try:

    init_tables()

except Exception as e:

    print(
        "Initialisation DB:",
        str(e)
    )


if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(
            os.environ.get(
                "PORT",
                5000
            )
        )
    )
