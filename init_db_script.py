# Fichier: init_db_script.py

from app import app, db

def initialize_database():
    """Crée les tables de la base de données en utilisant le contexte de l'application."""
    with app.app_context():
        # Crée toutes les tables définies dans app.py (Inscription et Admin)
        db.create_all()
        print('✅ Base de données initialisée avec succès (tables créées).')

if __name__ == '__main__':
    initialize_database()
