# Fichier: init_deploy.py (Exécuté par le service d'hébergement)
import os
from app_v2 import app, db, Admin # Assurez-vous que le nom du fichier est correct
from werkzeug.security import generate_password_hash
from alembic.config import Config
from alembic import command
import sys

# ===============================
# Configuration Admin par défaut
# ===============================
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'adminmanoor')
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'admin@manoor.com')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'ManPass2025') # À CHANGER VIA VARIABLES D'ENVIRONNEMENT

# ===============================
# Création de l'utilisateur Admin
# ===============================
def create_default_admin():
    """Crée l'utilisateur administrateur initial si aucun administrateur n'existe."""
    with app.app_context():
        if Admin.query.filter_by(username=ADMIN_USERNAME).first() is None:
            print(f"INFO: Création de l'administrateur par défaut ({ADMIN_USERNAME})...")
            hashed_password = generate_password_hash(ADMIN_PASSWORD)
            new_admin = Admin(
                username=ADMIN_USERNAME,
                email=ADMIN_EMAIL,
                password=hashed_password
            )
            db.session.add(new_admin)
            db.session.commit()
            print(f"✅ Administrateur '{ADMIN_USERNAME}' créé avec succès !")
            print("!!! NOTE: Changez ce mot de passe par défaut dans l'interface Admin !!!")
        else:
            print(f"ℹ️ Administrateur '{ADMIN_USERNAME}' existe déjà.")

# ===============================
# Appliquer Alembic Migration ou créer les tables
# ===============================
def run_alembic_setup():
    """Applique les migrations ou crée les tables si la base de données est vide."""
    with app.app_context():
        try:
            # 1. Tentative d'exécution des migrations Alembic
            alembic_cfg = Config("alembic.ini")
            print("INFO: Tentative d'application des migrations Alembic...")
            # 'head' amène la DB au schéma le plus récent
            command.upgrade(alembic_cfg, "head") 
            print("✅ Migrations Alembic appliquées avec succès.")
        
        except Exception as e:
            # 2. Fallback si les migrations échouent (par exemple, si la DB est nouvelle et non initialisée par Alembic)
            print(f"⚠️ Erreur lors de l'exécution d'Alembic. Fallback à db.create_all() : {e}", file=sys.stderr)
            try:
                db.create_all()
                print("✅ Tables créées avec succès via db.create_all().")
            except Exception as db_e:
                # 3. Échec critique
                print(f"❌ Échec critique de la création des tables : {db_e}", file=sys.stderr)
                # Nous arrêtons ici car sans tables, le site ne peut pas fonctionner
                sys.exit(1) 

# ===============================
# Exécution complète pour le Déploiement
# ===============================
if __name__ == "__main__":
    run_alembic_setup()
    create_default_admin()
