from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import psycopg
from psycopg.rows import dict_row
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
CORS(app)

DATABASE_URL = os.environ.get("DATABASE_URL")


# =========================================================
# CONNEXION DATABASE
# =========================================================

def get_db():
    if not DATABASE_URL:
        raise Exception("DATABASE_URL n'est pas configurée")

    return psycopg.connect(
        DATABASE_URL,
        row_factory=dict_row
    )


# =========================================================
# PAGE PRINCIPALE
# =========================================================

@app.route("/")
def home():
    return jsonify({
        "success": True,
        "message": "API KAJIMINYI fonctionne !"
    })


# =========================================================
# TEST API
# =========================================================

@app.route("/api/test", methods=["GET"])
def api_test():
    return jsonify({
        "success": True,
        "message": "API KAJIMINYI fonctionne !"
    })


# =========================================================
# TEST POSTGRESQL
# =========================================================

@app.route("/api/db-test", methods=["GET"])
def db_test():
    try:
        conn = get_db()

        with conn.cursor() as cur:
            cur.execute("SELECT 1 AS result")
            result = cur.fetchone()

        conn.close()

        return jsonify({
            "success": True,
            "message": "Connexion à PostgreSQL réussie !",
            "result": result["result"]
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


# =========================================================
# INITIALISATION DE LA BASE
# =========================================================

@app.route("/api/init-db", methods=["GET", "POST"])
def init_db():

    try:
        conn = get_db()

        with conn.cursor() as cur:

            # -------------------------------------------------
            # TABLE USERS
            # -------------------------------------------------

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

            # -------------------------------------------------
            # TABLE GROUPS
            # -------------------------------------------------

            cur.execute("""
                CREATE TABLE IF NOT EXISTS groups (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(150) NOT NULL,
                    description TEXT,
                    photo_url TEXT,
                    created_by INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # -------------------------------------------------
            # TABLE GROUP MEMBERS
            # -------------------------------------------------

            cur.execute("""
                CREATE TABLE IF NOT EXISTS group_members (
                    id SERIAL PRIMARY KEY,
                    group_id INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    role VARCHAR(20) DEFAULT 'member',
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(group_id, user_id)
                )
            """)

        conn.commit()
        conn.close()

        return jsonify({
            "success": True,
            "message": "Tables KAJIMINYI créées avec succès !"
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


# =========================================================
# INSCRIPTION
# =========================================================

@app.route("/api/register", methods=["POST"])
def register():

    try:

        data = request.get_json() or {}

        full_name = data.get("full_name", "").strip()
        phone = data.get("phone", "").strip()
        email = data.get("email", "").strip() or None
        password = data.get("password", "")

        if not full_name or not phone or not password:
            return jsonify({
                "success": False,
                "message": "Nom, téléphone et mot de passe sont obligatoires."
            }), 400

        password_hash = generate_password_hash(password)

        conn = get_db()

        with conn.cursor() as cur:

            cur.execute("""
                INSERT INTO users
                (full_name, phone, email, password_hash)
                VALUES (%s, %s, %s, %s)
                RETURNING id, full_name, phone, email, created_at
            """, (
                full_name,
                phone,
                email,
                password_hash
            ))

            user = cur.fetchone()

        conn.commit()
        conn.close()

        return jsonify({
            "success": True,
            "message": "Compte créé avec succès.",
            "user": user
        }), 201

    except psycopg.errors.UniqueViolation:

        return jsonify({
            "success": False,
            "message": "Ce numéro de téléphone ou cet email existe déjà."
        }), 409

    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


# =========================================================
# CONNEXION
# =========================================================

@app.route("/api/login", methods=["POST"])
def login():

    try:

        data = request.get_json() or {}

        phone = data.get("phone", "").strip()
        password = data.get("password", "")

        if not phone or not password:
            return jsonify({
                "success": False,
                "message": "Téléphone et mot de passe obligatoires."
            }), 400

        conn = get_db()

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

        conn.close()

        if not user:
            return jsonify({
                "success": False,
                "message": "Numéro de téléphone ou mot de passe incorrect."
            }), 401

        if not check_password_hash(
            user["password_hash"],
            password
        ):
            return jsonify({
                "success": False,
                "message": "Numéro de téléphone ou mot de passe incorrect."
            }), 401

        user.pop("password_hash", None)

        return jsonify({
            "success": True,
            "message": "Connexion réussie.",
            "user": user
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


# =========================================================
# UTILISATEURS
# =========================================================

@app.route("/api/users", methods=["GET"])
def get_users():

    try:

        conn = get_db()

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

            users = cur.fetchall()

        conn.close()

        return jsonify({
            "success": True,
            "users": users
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


# =========================================================
# CREER UN GROUPE
# =========================================================

@app.route("/api/groups", methods=["POST"])
def create_group():

    try:

        data = request.get_json() or {}

        name = data.get("name", "").strip()
        description = data.get("description", "").strip()
        photo_url = data.get("photo_url")
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
                "message": "Utilisateur créateur manquant."
            }), 400

        try:
            creator_id = int(creator_id)
        except:
            return jsonify({
                "success": False,
                "message": "ID utilisateur invalide."
            }), 400

        # Nettoyage des membres
        clean_member_ids = []

        for member_id in member_ids:

            try:
                member_id = int(member_id)

                if member_id not in clean_member_ids:
                    clean_member_ids.append(member_id)

            except:
                pass

        # Le créateur doit toujours être membre
        if creator_id not in clean_member_ids:
            clean_member_ids.insert(0, creator_id)

        conn = get_db()

        with conn.cursor() as cur:

            # Vérifier le créateur
            cur.execute("""
                SELECT id, full_name
                FROM users
                WHERE id = %s
            """, (creator_id,))

            creator = cur.fetchone()

            if not creator:

                conn.rollback()
                conn.close()

                return jsonify({
                    "success": False,
                    "message": "Utilisateur créateur introuvable."
                }), 404

            # Créer le groupe
            cur.execute("""
                INSERT INTO groups
                (name, description, photo_url, created_by)
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
                photo_url,
                creator_id
            ))

            group = cur.fetchone()

            # Ajouter les membres existants
            for member_id in clean_member_ids:

                cur.execute("""
                    INSERT INTO group_members
                    (group_id, user_id, role)
                    SELECT %s, id,
                           CASE
                               WHEN id = %s THEN 'admin'
                               ELSE 'member'
                           END
                    FROM users
                    WHERE id = %s
                    ON CONFLICT (group_id, user_id)
                    DO NOTHING
                """, (
                    group["id"],
                    creator_id,
                    member_id
                ))

        conn.commit()
        conn.close()

        return jsonify({
            "success": True,
            "message": "Groupe créé avec succès.",
            "group": group
        }), 201

    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


# =========================================================
# RECUPERER LES GROUPES D'UN UTILISATEUR
# =========================================================

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
        except:

            return jsonify({
                "success": False,
                "message": "user_id invalide."
            }), 400

        conn = get_db()

        with conn.cursor() as cur:

            cur.execute("""
                SELECT
                    g.id,
                    g.name,
                    g.description,
                    g.photo_url,
                    g.created_by,
                    g.created_at,

                    (
                        SELECT COUNT(*)
                        FROM group_members gm2
                        WHERE gm2.group_id = g.id
                    ) AS member_count

                FROM groups g

                INNER JOIN group_members gm
                    ON gm.group_id = g.id

                WHERE gm.user_id = %s

                ORDER BY g.created_at DESC
            """, (user_id,))

            groups = cur.fetchall()

        conn.close()

        return jsonify({
            "success": True,
            "groups": groups
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


# =========================================================
# MEMBRES D'UN GROUPE
# =========================================================

@app.route("/api/groups/<int:group_id>/members", methods=["GET"])
def get_group_members(group_id):

    try:

        conn = get_db()

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

                ORDER BY
                    CASE
                        WHEN gm.role = 'admin'
                        THEN 0
                        ELSE 1
                    END,
                    u.full_name ASC
            """, (group_id,))

            members = cur.fetchall()

        conn.close()

        return jsonify({
            "success": True,
            "members": members
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


# =========================================================
# AJOUTER DES MEMBRES
# =========================================================

@app.route("/api/groups/<int:group_id>/members", methods=["POST"])
def add_group_members(group_id):

    try:

        data = request.get_json() or {}

        member_ids = data.get("member_ids", [])

        if not isinstance(member_ids, list):
            return jsonify({
                "success": False,
                "message": "member_ids doit être une liste."
            }), 400

        conn = get_db()

        added = 0

        with conn.cursor() as cur:

            # Vérifier que le groupe existe
            cur.execute("""
                SELECT id
                FROM groups
                WHERE id = %s
            """, (group_id,))

            group = cur.fetchone()

            if not group:

                conn.close()

                return jsonify({
                    "success": False,
                    "message": "Groupe introuvable."
                }), 404

            for member_id in member_ids:

                try:
                    member_id = int(member_id)
                except:
                    continue

                cur.execute("""
                    INSERT INTO group_members
                    (group_id, user_id, role)
                    SELECT %s, id, 'member'
                    FROM users
                    WHERE id = %s
                    ON CONFLICT (group_id, user_id)
                    DO NOTHING
                """, (
                    group_id,
                    member_id
                ))

                if cur.rowcount:
                    added += 1

        conn.commit()
        conn.close()

        return jsonify({
            "success": True,
            "message": "Membres ajoutés.",
            "added": added
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


# =========================================================
# SUPPRIMER UN GROUPE
# =========================================================

@app.route("/api/groups/<int:group_id>", methods=["DELETE"])
def delete_group(group_id):

    try:

        conn = get_db()

        with conn.cursor() as cur:

            cur.execute("""
                DELETE FROM groups
                WHERE id = %s
                RETURNING id
            """, (group_id,))

            deleted = cur.fetchone()

        conn.commit()
        conn.close()

        if not deleted:

            return jsonify({
                "success": False,
                "message": "Groupe introuvable."
            }), 404

        return jsonify({
            "success": True,
            "message": "Groupe supprimé."
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


# =========================================================
# LANCEMENT
# =========================================================

if __name__ == "__main__":

    port = int(os.environ.get("PORT", 5000))

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
        )
