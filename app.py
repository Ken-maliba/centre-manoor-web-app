# app.py

from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime

# ====================================================
# I. CONFIGURATION DE L'APPLICATION
# ====================================================

app = Flask(__name__)

# --- Configuration (Utilise .env localement ou variables Render en production) ---
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default_secret_key_pour_test_local')

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
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', 'VotreMotDePasseApp')
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
    telephone = db.Column(db.String(15), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    etablissement_actuel = db.Column(db.String(150), nullable=False)
    
    # Choix de Formation
    formation_option = db.Column(db.String(50), nullable=False) # Ex: LGCGM, LCCM, ...
    niveau_etude = db.Column(db.String(50), nullable=False)     # Ex: Licence, Master
    
    # Suivi et Validation
    date_soumission = db.Column(db.DateTime, default=datetime.utcnow)
    # Champ booléen pour indiquer si l'inscription a été validée par l'admin
    is_validated = db.Column(db.Boolean, default=False) 
    methode_paiement = db.Column(db.String(50), nullable=True) # Ex: Orange Money, Virement
    validation_date = db.Column(db.DateTime, nullable=True) # Date de la validation

    def __repr__(self):
        return f"Inscription('{self.nom}', '{self.prenom}', '{self.email}')"


# ====================================================
# III. INITIALISATION DE LA BASE DE DONNÉES (Méthode 2)
# ====================================================

# Crée les tables si elles n'existent pas. 
# Ce bloc est exécuté au démarrage de l'application sur Render.
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
        return False


# ====================================================
# V. ROUTES DE L'APPLICATION
# ====================================================

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        try:
            # 1. Collecte des données du formulaire
            nom = request.form['nom']
            prenom = request.form['prenom']
            date_naissance = datetime.strptime(request.form['date_naissance'], '%Y-%m-%d').date()
            telephone = request.form['telephone'].replace(' ', '') # Nettoyage du numéro
            email = request.form['email']
            etablissement_actuel = request.form['etablissement_actuel']
            formation_option = request.form['formation_option']
            niveau_etude = request.form['niveau_etude']
            methode_paiement = request.form['methode_paiement']

            # 2. Vérification d'unicité (Flask-SQLAlchemy gère la violation UNIQUE, mais un check aide)
            if Inscription.query.filter_by(telephone=telephone).first() or \
               Inscription.query.filter_by(email=email).first():
                flash('Ce numéro de téléphone ou cette adresse e-mail est déjà utilisé(e).', 'warning')
                return redirect(url_for('echec_inscription', error_message='Données déjà enregistrées.'))
            
            # 3. Création de l'objet Inscription
            new_inscription = Inscription(
                nom=nom, prenom=prenom, date_naissance=date_naissance, 
                telephone=telephone, email=email, 
                etablissement_actuel=etablissement_actuel,
                formation_option=formation_option, 
                niveau_etude=niveau_etude,
                methode_paiement=methode_paiement
            )

            # 4. Enregistrement dans la base de données
            db.session.add(new_inscription)
            db.session.commit()
            
            inscription_id = new_inscription.id

            # 5. Envoi de l'email de confirmation (Non bloquant)
            send_validation_email(new_inscription)

            # 6. Redirection vers la page de succès
            return redirect(url_for('succes_inscription', inscription_id=inscription_id))

        except Exception as e:
            # En cas d'erreur de base de données (ex: UniqueViolation non capturée, etc.)
            db.session.rollback()
            print(f"Erreur d'enregistrement critique: {e}")
            # Redirection vers la page d'échec avec un message
            return redirect(url_for('echec_inscription', error_message=str(e)))

    # Pour la requête GET, afficher le formulaire principal
    return render_template('index.html')

@app.route('/succes-inscription')
def succes_inscription():
    inscription_id = request.args.get('inscription_id')
    return render_template('succes_inscription.html', inscription_id=inscription_id)

@app.route('/echec-inscription')
def echec_inscription():
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
            # Redirige vers la page d'où l'utilisateur venait, ou vers le tableau de bord
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
    
    # Bascule le statut de validation
    if not inscription.is_validated:
        inscription.is_validated = True
        inscription.validation_date = datetime.utcnow()
        flash(f'Inscription #{inscription_id} (de {inscription.nom} {inscription.prenom}) marquée comme VALIDÉE.', 'success')
    else:
        inscription.is_validated = False
        inscription.validation_date = None
        flash(f'Inscription #{inscription_id} (de {inscription.nom} {inscription.prenom}) marquée comme EN ATTENTE.', 'warning')
        
    db.session.commit()
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/delete/<int:inscription_id>', methods=['POST'])
@login_required
def delete_inscription(inscription_id):
    inscription = Inscription.query.get_or_404(inscription_id)
    
    try:
        db.session.delete(inscription)
        db.session.commit()
        flash(f'Inscription #{inscription_id} de {inscription.nom} {inscription.prenom} a été SUPPRIMÉE.', 'success')
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
