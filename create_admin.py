# Fichier: create_admin.py

from app import app, db, Admin
from werkzeug.security import generate_password_hash
import os

ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'MonPassSecre2025') 
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'admin@manoor.com')

def create_admin_user():
    """Crée l'utilisateur administrateur initial si aucun administrateur n'existe."""
    with app.app_context():
        if db.session.query(Admin).filter_by(username=ADMIN_USERNAME).first() is None:
            
            hashed_password = generate_password_hash(ADMIN_PASSWORD)
            
            admin_user = Admin(
                username=ADMIN_USERNAME,
                email=ADMIN_EMAIL,
                password=hashed_password
            )
            
            db.session.add(admin_user)
            db.session.commit()
            
            print("==============================================")
            print("✅ Utilisateur Admin créé avec succès!")
            print(f"Nom d'utilisateur: {ADMIN_USERNAME}")
            print("==============================================")
        else:
            print(f"Utilisateur Admin '{ADMIN_USERNAME}' existe déjà. Aucune action n'est requise.")

if __name__ == '__main__':
    create_admin_user()
