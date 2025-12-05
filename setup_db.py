import os
from app import app, db, Admin
from werkzeug.security import generate_password_hash
from alembic.config import Config
from alembic import command

# ===============================
# Configuration Admin par défaut
# ===============================
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'adminmanoor')
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'admin@manoor.com')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'ManPass2025')

# ===============================
# Création de l'utilisateur Admin
# ===============================
def create_default_admin():
    with app.app_context():
        if Admin.query.filter_by(username=ADMIN_USERNAME).first() is None:
            hashed_password = generate_password_hash(ADMIN_PASSWORD)
            new_admin = Admin(
                username=ADMIN_USERNAME,
                email=ADMIN_EMAIL,
                password=hashed_password
            )
            db.session.add(new_admin)
            db.session.commit()
            print(f"✅ Administrateur '{ADMIN_USERNAME}' créé avec succès !")
        else:
            print(f"ℹ️ Administrateur '{ADMIN_USERNAME}' existe déjà.")

# ===============================
# Appliquer Alembic Migration
# ===============================
def run_alembic_migration():
    alembic_cfg = Config("alembic.ini")  # Assurez-vous que alembic.ini est à la racine
    command.upgrade(alembic_cfg, "head")
    print("✅ Migrations Alembic appliquées avec succès !")

# ===============================
# Création des tables si non existantes
# ===============================
def create_tables_if_not_exist():
    with app.app_context():
        try:
            # Test rapide pour voir si la table existe
            db.session.query(Admin).limit(1).all()
            print("ℹ️ Les tables existent déjà. Pas de création manuelle nécessaire.")
        except Exception:
            print("⚠️ Tables manquantes. Création via db.create_all()...")
            db.create_all()
            print("✅ Tables créées via db.create_all()")

# ===============================
# Exécution complète
# ===============================
if __name__ == "__main__":
    create_tables_if_not_exist()
    create_default_admin()
    run_alembic_migration()
