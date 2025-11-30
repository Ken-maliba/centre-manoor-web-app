# app.py
from flask import Flask, request, redirect, url_for, render_template, abort, flash, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime
import io
import csv
from dotenv import load_dotenv
import logging 

# Configuration du logging pour afficher les erreurs en console
logging.basicConfig(level=logging.INFO)

# Charge les variables d'environnement depuis .env (utile en développement local)
load_dotenv()

app = Flask(__name__)

# --- CONFIGURATION PRINCIPALE ---
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'ma_cle_secrete_pour_les_sessions_manoor')

# 1. Récupération de l'URL de la base de données (Render/PostgreSQL)
DATABASE_URL = os.environ.get('DATABASE_URL')

# 2. Correction nécessaire pour SQLAlchemy : Render utilise 'postgres://', 
#    mais SQLAlchemy a besoin de 'postgresql://' pour se connecter correctement.
#    (Cette ligne est importante si vous testez en local avec une DB Render)
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# 3. Utilisation de PostgreSQL en Prod (via DATABASE_URL) ou SQLite en Dev
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL or 'sqlite:///' + os.path.join(basedir, 'site.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# --- CONFIGURATION D'EMAIL ---
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
# Note : MAIL_PASSWORD DOIT ÊTRE UN MOT DE PASSE D'APPLICATION GOOGLE (16 caractères)
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD') 

# Utilisation dynamique de MAIL_USERNAME comme expéditeur par défaut
MAIL_SENDER = os.environ.get('MAIL_USERNAME', 'centremmanoor@gmail.com')
app.config['MAIL_DEFAULT_SENDER'] = f'Centre Manoor <{MAIL_SENDER}>'

db = SQLAlchemy(app)
mail = Mail(app)

# --- CONFIGURATION FLASK-LOGIN ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# --- MODÈLES DE DONNÉES ---
class Inscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(80), nullable=False)
    prenom = db.Column(db.String(80), nullable=False)
    datenaissance = db.Column(db.String(10))
    # Ces champs DOIVENT être uniques pour éviter les doublons 
    telephone = db.Column(db.String(8), unique=True, nullable=False) 
    email = db.Column(db.String(120), unique=True, nullable=False)
    formation = db.Column(db.String(50), nullable=False)
    
    etablissement_actuel = db.Column(db.String(100), nullable=True)
    
    formation_option = db.Column(db.String(50), nullable=False)
    niveauetude = db.Column(db.String(50))
    methode_paiement = db.Column(db.String(50))
    date_soumission = db.Column(db.DateTime, default=db.func.now())
    is_validated = db.Column(db.Boolean, default=False)
    validation_date = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f'<Inscription {self.nom} {self.prenom} - Validé: {self.is_validated}>'


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    password_hash = db.Column(db.String(200))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


# --- FONCTIONS UTILITAIRES ---
def send_validation_email(inscription):
    """Envoie un email à l'étudiant après validation par la direction."""
    if inscription.formation_option == 'Groupe':
        mensualite = '25 000 F CFA'
    else:
        mensualite = '50 000 F CFA'

    try:
        msg = Message(
            subject=f"✅ Dossier de Pré-Inscription Manoor - {inscription.formation} - Validé",
            recipients=[inscription.email],
            body=f"""
Bonjour {inscription.prenom} {inscription.nom},

Félicitations ! Votre dossier de pré-inscription pour la formation '{inscription.formation}' ({inscription.formation_option}) au Centre Manoor a été examiné et validé par notre direction.

Détails des frais :
- Frais d’inscription uniques : 5 000 F CFA
- Mensualité : {mensualite}

Prochaine étape :
1. **Paiement des Frais de Dossier :** Vous avez choisi le mode de paiement '{inscription.methode_paiement}'. Si le paiement n'est pas encore finalisé, veuillez suivre les instructions détaillées qui vous seront envoyées séparément.
2. **Concours d'Entrée :** Les informations concernant la date et les modalités du concours d'entrée vous seront communiquées par téléphone (sur le {inscription.telephone}) et par email dans les 72 heures.

Nous vous souhaitons le meilleur succès.

Cordialement,
L'Administration du Centre Manoor
"""
        )
        mail.send(msg)
        logging.info(f"✅ EMAIL ENVOYÉ à {inscription.email}")
        return True
    except Exception as e:
        logging.error(f"❌ ÉCHEC ENVOI EMAIL à {inscription.email}: {e}")
        flash(f"Erreur d'envoi d'e-mail (vérifier MAIL_PASSWORD): {e}", 'danger')
        return False


def create_default_admin():
    """Crée un compte admin par défaut si aucun n'existe."""
    if User.query.filter_by(username='adminmanoor').first() is None:
        admin_user = User(username='adminmanoor')
        admin_user.set_password('motdepasse2025') # MOT DE PASSE PAR DÉFAUT
        db.session.add(admin_user)
        db.session.commit()
        logging.info("👤 Compte administrateur par défaut créé : adminmanoor / motdepasse2025")


# --- ROUTES FRONTEND (Identiques) ---
URL_PAGE_SUCCES = '/succes-inscription'

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/soumettre-inscription', methods=['POST'])
def soumettre_inscription():
    if request.method == 'POST':
        # 1. Récupération des données du formulaire (Même logique, les noms de champs sont corrects)
        donnees_formulaire = {
            "nom": request.form.get('nom'),
            "prenom": request.form.get('prenom'),
            "datenaissance": request.form.get('datenaissance'),
            "telephone": request.form.get('telephone'),
            "email": request.form.get('email'),
            "formation": request.form.get('formation'),
            
            "etablissement_actuel": request.form.get('etablissement_actuel'),
            
            "formation_option": request.form.get('formation_option'),
            "niveauetude": request.form.get('niveauetude'),
            "methode_paiement": request.form.get('methode_paiement')
        }

        # 2. CRÉATION ET ENREGISTREMENT DE LA NOUVELLE INSCRIPTION
        try:
            nouvelle_inscription = Inscription(
                nom=donnees_formulaire['nom'],
                prenom=donnees_formulaire['prenom'],
                datenaissance=donnees_formulaire['datenaissance'],
                telephone=donnees_formulaire['telephone'],
                email=donnees_formulaire['email'],
                formation=donnees_formulaire['formation'],
                
                etablissement_actuel=donnees_formulaire['etablissement_actuel'],
                
                formation_option=donnees_formulaire['formation_option'],
                niveauetude=donnees_formulaire['niveauetude'],
                methode_paiement=donnees_formulaire['methode_paiement']
            )

            db.session.add(nouvelle_inscription)
            db.session.commit()
            logging.info(f"💾 Inscription enregistrée pour {nouvelle_inscription.email}")

        except Exception as e:
            db.session.rollback()
            # Log l'erreur pour aider au diagnostic 
            logging.error(f"❌ ÉCHEC ENREGISTREMENT DB: {e}") 
            # Redirige vers la page d'échec
            return redirect(url_for('page_echec_inscription'))

        return redirect(URL_PAGE_SUCCES)

    return redirect(url_for('index'))


@app.route('/succes-inscription')
def page_succes():
    return render_template('succes_inscription.html') # Assurez-vous d'avoir ce template


@app.route('/echec-inscription')
def page_echec_inscription():
    return render_template('echec_inscription.html') # Assurez-vous d'avoir ce template


# --- ROUTES D'AUTHENTIFICATION, ADMIN, CRUD (Identiques) ---
# ... (Gardez toutes les autres routes : login, logout, admin_dashboard, validate, export, edit, delete) ...

@app.route('/login', methods=['GET', 'POST'])
def login():
    # ... (code login) ...
    pass # Placeholder pour les autres routes non affichées


# --- NOUVELLE PARTIE CRITIQUE POUR RENDER ---
def setup_db_and_admin():
    """Fonction utilitaire pour créer la DB et l'admin dans le contexte de l'application."""
    with app.app_context():
        # 1. CRÉATION DE LA TABLE MANQUANTE (Inscription et User)
        try:
            db.create_all() 
            logging.info("✅ Tables de la base de données vérifiées/créées.")
        except Exception as e:
             logging.error(f"❌ ÉCHEC FATAL lors de db.create_all(): {e}")

        # 2. CRÉATION DE L'UTILISATEUR ADMIN PAR DÉFAUT
        try:
            create_default_admin()
            logging.info("✅ Utilisateur admin par défaut vérifié/créé.")
        except Exception as e:
             logging.error(f"❌ ÉCHEC FATAL lors de la création de l'admin: {e}")
             
# Point d'entrée pour Gunicorn (Render)
# Gunicorn appellera cette fonction, assurant la création de la table AVANT de servir les requêtes.
def gunicorn_startup():
    setup_db_and_admin()
    return app

# Point d'entrée pour le développement local (python app.py)
if __name__ == '__main__':
    setup_db_and_admin()
    app.run(debug=True)

# FIN DU FICHIER
