import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_admin import Admin as FlaskAdmin
from flask_admin.contrib.sqla import ModelView
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user

# ====================================================
# CONFIGURATION
# ====================================================

app = Flask(__name__)

# Configuration de la base de données PostgreSQL pour Render
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL is None:
    # Fallback pour le développement local
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
else:
    # S'assurer que le schéma est correct pour SQLAlchemy
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default_secret_key_change_me')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'admin_login'


# ====================================================
# MODÈLES DE BASE DE DONNÉES
# ====================================================

class Inscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(50), nullable=False)
    prenom = db.Column(db.String(50), nullable=False)
    date_naissance = db.Column(db.Date, nullable=False)
    telephone = db.Column(db.String(8), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    etablissement_actuel = db.Column(db.String(100), nullable=True)
    niveau_etude = db.Column(db.String(50), nullable=False)
    
    # NOUVELLE COLONNE pour la formation principale
    formation_principale = db.Column(db.String(100), nullable=False) 
    
    formation_option = db.Column(db.String(50), nullable=False)
    methode_paiement = db.Column(db.String(50), nullable=False)
    date_soumission = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Champs pour le suivi
    is_valide = db.Column(db.Boolean, default=False)
    is_validation_date = db.Column(db.Boolean, default=False)
    validation_date = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f"Inscription('{self.prenom} {self.nom}', Tel: {self.telephone})"


class Admin(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False) # Hashed password

    def __repr__(self):
        return f"Admin('{self.username}')"

@login_manager.user_loader
def load_user(user_id):
    return Admin.query.get(int(user_id))

# ====================================================
# VUES ADMINISTRATEUR
# ====================================================

class CustomAdminModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated

    def inaccessible_callback(self, name, **kwargs):
        # Rediriger vers la page de connexion si l'utilisateur n'est pas connecté
        return redirect(url_for('admin_login'))

# Configuration Flask-Admin
admin = FlaskAdmin(app, name='Administration Manoor', template_mode='bootstrap3', url='/admin')
admin.add_view(CustomAdminModelView(Inscription, db.session, name="Inscriptions"))
admin.add_view(CustomAdminModelView(Admin, db.session, name="Gestion Admins"))


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated:
        return redirect(url_for('admin.index'))
    
    # Ceci est juste une page de connexion simple (pas de formulaire HTML fourni)
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = Admin.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('admin.index'))
        else:
            flash('Échec de la connexion. Vérifiez le nom d\'utilisateur et le mot de passe.', 'error')
            
    # Pour la connexion, on redirige l'utilisateur vers la page de connexion par défaut de Flask-Admin
    return render_template('admin_login.html') # Assurez-vous d'avoir ce template ou utilisez un simple template

@app.route('/admin/logout')
@login_required
def admin_logout():
    logout_user()
    return redirect(url_for('index'))


# ====================================================
# ROUTES PRINCIPALES (FORMULAIRE)
# ====================================================

@app.route('/', methods=['GET', 'POST'])
def index():
    
    if request.method == 'POST':
        
        # Liste des champs OBLIGATOIRES (Mise à jour pour correspondre à index.html)
        required_fields = [
            'nom', 'prenom', 'date_naissance', 'telephone', 'email', 
            'niveau_etude', 'formation_principale', 'formation_option', 
            'methode_paiement'
        ]
        
        # S'assurer que les données sont bien dans request.form (ou request.json)
        data = request.form
        
        # 1. Vérification des champs manquants
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            error_message = f"Le champ {', '.join(missing_fields)} est manquant ou vide."
            return redirect(url_for('echec_inscription', error_message=error_message))
        
        # 2. Extraction des données (y compris le nouveau champ)
        nom = data.get('nom')
        prenom = data.get('prenom')
        date_naissance_str = data.get('date_naissance')
        telephone = data.get('telephone')
        email = data.get('email')
        etablissement_actuel = data.get('etablissement_actuel')
        niveau_etude = data.get('niveau_etude')
        
        # LE CHAMP QUI A ÉTÉ RENOMMÉ DANS INDEX.HTML
        formation_principale = data.get('formation_principale') 
        
        formation_option = data.get('formation_option')
        methode_paiement = data.get('methode_paiement')

        try:
            # 3. Conversion de la date de naissance
            date_naissance = datetime.strptime(date_naissance_str, '%Y-%m-%d').date()
            
            # 4. Vérification des doublons (téléphone et email)
            if Inscription.query.filter_by(telephone=telephone).first():
                error_message = "Ce numéro de téléphone est déjà utilisé."
                return redirect(url_for('echec_inscription', error_message=error_message))
            
            if Inscription.query.filter_by(email=email).first():
                error_message = "Cette adresse e-mail est déjà utilisée."
                return redirect(url_for('echec_inscription', error_message=error_message))

            # 5. Création et ajout de l'inscription
            nouvelle_inscription = Inscription(
                nom=nom,
                prenom=prenom,
                date_naissance=date_naissance,
                telephone=telephone,
                email=email,
                etablissement_actuel=etablissement_actuel,
                niveau_etude=niveau_etude,
                formation_principale=formation_principale, # NOUVEAU NOM DU CHAMP
                formation_option=formation_option,
                methode_paiement=methode_paiement,
                date_soumission=datetime.now(),
                is_valide=False,
                is_validation_date=False,
                validation_date=None
            )

            db.session.add(nouvelle_inscription)
            db.session.commit()
            
            # 6. Redirection vers le succès
            return redirect(url_for('succes_inscription'))

        except ValueError as e:
            # Erreur de format de date
            error_message = f"Erreur de format des données : {str(e)}"
            return redirect(url_for('echec_inscription', error_message=error_message))
        except Exception as e:
            # Erreur d'enregistrement critique (ex: base de données)
            db.session.rollback()
            # Pour l'affichage, nous utilisons un message d'erreur générique mais critique
            # Le log de Render affichera la vraie erreur SQL ou autre
            error_message = f"Erreur d'enregistrement critique. Détail technique : {str(e)}"
            return redirect(url_for('echec_inscription', error_message=error_message))

    # Méthode GET: afficher le formulaire
    return render_template('index.html')


@app.route('/succes-inscription')
def succes_inscription():
    return render_template('succes_inscription.html')

@app.route('/echec-inscription')
def echec_inscription():
    error_message = request.args.get('error_message', 'Une erreur inconnue est survenue.')
    return render_template('echec_inscription.html', error_message=error_message)

# ====================================================
# INITIALISATION DE LA BASE DE DONNÉES
# ====================================================

@app.cli.command("init-db")
def init_db():
    """Crée les tables de la base de données."""
    with app.app_context():
        db.create_all()
        print('Base de données initialisée.')

if __name__ == '__main__':
    # Ceci est généralement utilisé pour le développement local
    # Sur Render, le serveur Gunicorn gère le lancement
    with app.app_context():
        db.create_all()
    app.run(debug=True)
