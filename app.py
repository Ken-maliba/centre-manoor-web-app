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
# Assurez-vous d'avoir un fichier .env si vous développez en local
load_dotenv() 

app = Flask(__name__)

# --- CONFIGURATION PRINCIPALE ---
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'ma_cle_secrete_pour_les_sessions_manoor')

# 1. Récupération de l'URL de la base de données (Render/PostgreSQL)
DATABASE_URL = os.environ.get('DATABASE_URL')

# 2. Correction nécessaire pour SQLAlchemy : Render utilise parfois 'postgres://', 
#    mais SQLAlchemy a besoin de 'postgresql://' pour se connecter correctement.
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
        # Ceci peut se produire si MAIL_PASSWORD est faux
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


# --- ROUTES FRONTEND ---
URL_PAGE_SUCCES = '/succes-inscription'

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/soumettre-inscription', methods=['POST'])
def soumettre_inscription():
    if request.method == 'POST':
        # 1. Récupération des données du formulaire
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
            # Log l'erreur exacte pour le diagnostic 
            logging.error(f"❌ ÉCHEC ENREGISTREMENT DB: {e}") 
            # Redirige vers la page d'échec
            return redirect(url_for('page_echec_inscription'))

        return redirect(URL_PAGE_SUCCES)

    return redirect(url_for('index'))


@app.route('/succes-inscription')
def page_succes():
    return render_template('succes_inscription.html')


@app.route('/echec-inscription')
def page_echec_inscription():
    return render_template('echec_inscription.html')


# --- ROUTES D'AUTHENTIFICATION ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            flash('Connexion réussie.', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Identifiants invalides.', 'danger')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Vous avez été déconnecté.', 'info')
    return redirect(url_for('index'))


# --- ROUTES ADMIN ---
@app.route('/admin')
@login_required
def admin_dashboard():
    inscriptions = Inscription.query.all()
    # Classement par date de soumission (les plus récentes en premier)
    inscriptions.sort(key=lambda x: x.date_soumission, reverse=True)
    return render_template('admin_dashboard.html', inscriptions=inscriptions)

@app.route('/admin/validate/<int:inscription_id>', methods=['POST'])
@login_required
def validate_inscription(inscription_id):
    inscription = Inscription.query.get_or_404(inscription_id)
    if not inscription.is_validated:
        inscription.is_validated = True
        inscription.validation_date = datetime.now()
        
        try:
            db.session.commit()
            if send_validation_email(inscription):
                flash(f"Inscription de {inscription.nom} validée et email envoyé.", 'success')
            else:
                flash(f"Inscription de {inscription.nom} validée, mais l'envoi de l'email a échoué (vérifiez MAIL_PASSWORD).", 'warning')
        except Exception as e:
            db.session.rollback()
            flash(f"Erreur lors de la validation : {e}", 'danger')
            
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete/<int:inscription_id>', methods=['POST'])
@login_required
def delete_inscription(inscription_id):
    inscription = Inscription.query.get_or_404(inscription_id)
    try:
        db.session.delete(inscription)
        db.session.commit()
        flash(f"Inscription de {inscription.nom} supprimée.", 'success')
    except Exception as e:
        db.session.rollback()
        flash(f"Erreur lors de la suppression : {e}", 'danger')
        
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/export/csv')
@login_required
def export_csv():
    inscriptions = Inscription.query.all()
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')

    # En-tête du fichier CSV
    writer.writerow([
        'ID', 'Nom', 'Prénom', 'Date de Naissance', 'Téléphone', 'Email', 
        'Formation', 'Option', 'Niveau d\'étude', 'Établissement Actuel', 
        'Méthode Paiement', 'Date Soumission', 'Validée', 'Date Validation'
    ])

    # Données
    for i in inscriptions:
        writer.writerow([
            i.id, i.nom, i.prenom, i.datenaissance, i.telephone, i.email, 
            i.formation, i.formation_option, i.niveauetude, i.etablissement_actuel, 
            i.methode_paiement, i.date_soumission.strftime('%Y-%m-%d %H:%M:%S') if i.date_soumission else '', 
            'Oui' if i.is_validated else 'Non', 
            i.validation_date.strftime('%Y-%m-%d %H:%M:%S') if i.validation_date else ''
        ])

    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=inscriptions_manoor.csv"
    response.headers["Content-type"] = "text/csv; charset=utf-8"
    return response


# --- PARTIE DE DÉMARRAGE CRITIQUE (Mise à Jour) ---

if __name__ == '__main__':
    # Ceci s'exécute uniquement si vous lancez 'python app.py' en local.
    # Pour Render, cela est souvent sauté, d'où la nécessité de la commande 'flask shell'.
    try:
        with app.app_context():
            db.create_all() # Tente de créer les tables (Inscription et User)
            create_default_admin() # Crée l'admin si inexistant
        app.run(debug=True)
    except Exception as e:
        logging.error(f"❌ ERREUR FATALE AU DÉMARRAGE LOCAL : {e}")
        print("Vérifiez votre DATABASE_URL ou votre configuration SQLite.")
