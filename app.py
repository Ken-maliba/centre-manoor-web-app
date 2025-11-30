# app.py

import os
from datetime import datetime

# Importation des modules Flask et extensions
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash

# Charger les variables d'environnement si besoin (ex: localement avec python-dotenv)
# Note: Render charge directement les variables d'environnement.
# if os.path.exists('.env'):
#     from dotenv import load_dotenv
#     load_dotenv()


# ====================================================
# I. CONFIGURATION DE L'APPLICATION
# ====================================================

app = Flask(__name__)

# --- Configuration (Utilise .env localement ou variables Render en production) ---
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'votre_cle_secrete_par_defaut')

# Configuration de la Base de Données
# Utilise DATABASE_URL (PostgreSQL) si défini (Render), sinon SQLite localement
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL', 
    'sqlite:///site.db'
).replace('postgres://', 'postgresql://') # Correction pour SQLAlchemy 1.4+
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Configuration de Flask-Mail
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'True').lower() in ('true', '1', 't')
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', 'centremmanoor@gmail.com')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', 'VotreMotDePasseAppMail') # Utiliser un mot de passe d'application si Gmail
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', 'centremmanoor@gmail.com')

mail = Mail(app)

# Configuration de Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'admin_login'
login_manager.login_message_category = 'danger'
login_manager.login_message = "Veuillez vous connecter pour accéder à cette page."


# ====================================================
# II. MODÈLES DE BASE DE DONNÉES
# ====================================================

class AdminUser(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))

    def set_password(self, password):
        # Utilisation de scrypt est plus sécuritaire que sha256
        self.password_hash = generate_password_hash(password, method='scrypt') 

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    return AdminUser.query.get(int(user_id))


class Inscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    
    # Informations Personnelles
    nom = db.Column(db.String(100), nullable=False)
    prenom = db.Column(db.String(100), nullable=False)
    date_naissance = db.Column(db.Date, nullable=False)
    # Contraintes uniques pour prévenir les doublons
    telephone = db.Column(db.String(15), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    etablissement_actuel = db.Column(db.String(150), nullable=False)
    
    # Choix de Formation
    formation_option = db.Column(db.String(50), nullable=False)
    niveau_etude = db.Column(db.String(50), nullable=False)
    
    # Suivi et Validation
    date_soumission = db.Column(db.DateTime, default=datetime.utcnow)
    is_validated = db.Column(db.Boolean, default=False)
    methode_paiement = db.Column(db.String(50), nullable=True)
    validation_date = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f"Inscription('{self.nom}', '{self.prenom}', '{self.email}')"


# ====================================================
# III. INITIALISATION DE LA BASE DE DONNÉES (Méthode 2)
# ====================================================

# Ce bloc s'assure que les tables existent au démarrage de l'application.
with app.app_context():
    db.create_all()


# ====================================================
# IV. FONCTIONS UTILITAIRES
# ====================================================

def send_validation_email(inscription):
    """Envoie un e-mail de confirmation après la soumission du formulaire."""
    try:
        msg = Message(
            f'Pré-Inscription Soumise - Centre Manoor (ID: {inscription.id})',
            recipients=[inscription.email]
        )
        msg.body = (
            f"Cher(ère) {inscription.prenom} {inscription.nom},\n\n"
            f"Votre formulaire de pré-inscription pour la formation en {inscription.formation_option} "
            f"au Centre Manoor a été soumis avec succès le {inscription.date_soumission.strftime('%d/%m/%Y à %H:%M')}.\n\n"
            f"Votre numéro de dossier est: #{inscription.id}\n\n"
            f"Prochaine étape: Notre équipe vérifiera la réception des frais de dossier. "
            f"Vous recevrez une confirmation finale par e-mail et par téléphone dans les 72 heures.\n\n"
            f"Merci de votre confiance.\n"
            f"L'Administration du Centre Manoor"
        )
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Erreur lors de l'envoi de l'email : {e}")
        # L'échec de l'envoi d'e-mail ne doit pas bloquer la transaction principale
        return False


# ====================================================
# V. ROUTES DE L'APPLICATION
# ====================================================

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        try:
            # --- 1. Collecte et validation des données du formulaire ---
            data = request.form
            
            # Liste des champs requis pour la validation initiale
            required_fields = [
                'nom', 'prenom', 'date_naissance', 'telephone', 'email', 
                'etablissement_actuel', 'formation_option', 'niveau_etude', 'methode_paiement'
            ]
            
            # Vérification si un champ obligatoire est vide
            for field in required_fields:
                if not data.get(field):
                    # Génère une erreur personnalisée si un champ manque
                    raise ValueError(f"Le champ '{field.replace('_', ' ')}' est manquant ou vide.")

            # Extraction des données
            nom = data.get('nom')
            prenom = data.get('prenom')
            
            # Conversion de la date (point de plantage fréquent)
            try:
                date_naissance_str = data.get('date_naissance')
                date_naissance = datetime.strptime(date_naissance_str, '%Y-%m-%d').date()
            except ValueError:
                raise ValueError("Format de la date de naissance invalide. Veuillez utiliser AAAA-MM-JJ.")

            # Nettoyage et autres données
            telephone = data.get('telephone').replace(' ', '')
            email = data.get('email')
            etablissement_actuel = data.get('etablissement_actuel')
            formation_option = data.get('formation_option')
            niveau_etude = data.get('niveau_etude')
            methode_paiement = data.get('methode_paiement')


            # --- 2. Vérification d'unicité (pour un message plus clair) ---
            if Inscription.query.filter_by(telephone=telephone).first():
                raise Exception(f"Ce numéro de téléphone ('{telephone}') est déjà utilisé(e).")
            
            if Inscription.query.filter_by(email=email).first():
                raise Exception(f"Cette adresse e-mail ('{email}') est déjà utilisée.")
            
            
            # --- 3. Création et Enregistrement dans la Base de Données ---
            new_inscription = Inscription(
                nom=nom, prenom=prenom, date_naissance=date_naissance, 
                telephone=telephone, email=email, 
                etablissement_actuel=etablissement_actuel,
                formation_option=formation_option, 
                niveau_etude=niveau_etude,
                methode_paiement=methode_paiement
            )

            db.session.add(new_inscription)
            db.session.commit()
            
            inscription_id = new_inscription.id

            # Envoi de l'email de confirmation (non bloquant)
            send_validation_email(new_inscription)

            # Redirection vers la page de succès
            return redirect(url_for('succes_inscription', inscription_id=inscription_id))

        
        except Exception as e:
            # Gère les erreurs de validation (ValueError) ou les erreurs de base de données (IntegrityError, etc.)
            db.session.rollback()
            # Affiche l'erreur complète dans les logs de Render
            print(f"Erreur d'enregistrement critique: {e}") 
            
            # Redirection vers la page d'échec avec le message d'erreur
            return redirect(url_for('echec_inscription', error_message=str(e)))

    # Pour la requête GET, afficher le formulaire principal
    return render_template('index.html')

@app.route('/succes-inscription')
def succes_inscription():
    inscription_id = request.args.get('inscription_id')
    return render_template('succes_inscription.html', inscription_id=inscription_id)

@app.route('/echec-inscription')
def echec_inscription():
    # Récupère le message d'erreur passé dans l'URL
    error_message = request.args.get('error_message', None) 
    return render_template('echec_inscription.html', error_message=error_message)


# ----------------------------------------------------
# ROUTES DE L'ADMINISTRATION
# ----------------------------------------------------

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated:
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = AdminUser.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            flash('Connexion réussie.', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('admin_dashboard'))
        else:
            flash('Identifiants incorrects.', 'danger')

    return render_template('login.html')

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    # Statistiques
    total_inscriptions = Inscription.query.count()
    validated_count = Inscription.query.filter_by(is_validated=True).count()
    pending_count = total_inscriptions - validated_count
    
    # Filtres
    filter_status = request.args.get('status', 'all')
    
    query = Inscription.query.order_by(Inscription.date_soumission.desc())
    
    if filter_status == 'pending':
        query = query.filter_by(is_validated=False)
    elif filter_status == 'validated':
        query = query.filter_by(is_validated=True)
        
    inscriptions = query.all()
    
    return render_template('admin_dashboard.html', 
                           inscriptions=inscriptions,
                           total_inscriptions=total_inscriptions,
                           validated_count=validated_count,
                           pending_count=pending_count,
                           filter_status=filter_status)


@app.route('/admin/details/<int:inscription_id>')
@login_required
def inscription_details(inscription_id):
    inscription = Inscription.query.get_or_404(inscription_id)
    return render_template('inscription_details.html', inscription=inscription)


@app.route('/admin/validate/<int:inscription_id>', methods=['POST'])
@login_required
def validate_inscription(inscription_id):
    inscription = Inscription.query.get_or_404(inscription_id)
    
    if not inscription.is_validated:
        inscription.is_validated = True
        inscription.validation_date = datetime.utcnow()
        flash(f'Inscription #{inscription_id} validée.', 'success')
    else:
        inscription.is_validated = False
        inscription.validation_date = None
        flash(f'Inscription #{inscription_id} remise en attente.', 'warning')
        
    db.session.commit()
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/delete/<int:inscription_id>', methods=['POST'])
@login_required
def delete_inscription(inscription_id):
    inscription = Inscription.query.get_or_404(inscription_id)
    
    try:
        db.session.delete(inscription)
        db.session.commit()
        flash(f'Inscription #{inscription_id} a été SUPPRIMÉE.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors de la suppression: {e}', 'danger')
        
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/logout')
@login_required
def admin_logout():
    logout_user()
    flash('Vous avez été déconnecté.', 'info')
    return redirect(url_for('admin_login'))


# ====================================================
# VI. EXÉCUTION DE L'APPLICATION
# ====================================================

if __name__ == '__main__':
    # Ceci est exécuté uniquement en mode développement local
    app.run(debug=True)
