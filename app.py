# Fichier: app_v2.0.py
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

# --- Gestion de la Base de Données PostgreSQL ---
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL is None:
    # Fallback pour le développement local (SQLite)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
else:
    # Corrige 'postgres://' en 'postgresql://' pour SQLAlchemy (Standard Render/Heroku fix)
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
    formation_principale = db.Column(db.String(100), nullable=False)
    formation_option = db.Column(db.String(50), nullable=False)
    methode_paiement = db.Column(db.String(50), nullable=False)
    date_soumission = db.Column(db.DateTime, default=datetime.utcnow)
    is_valide = db.Column(db.Boolean, default=False)
    is_validation_date = db.Column(db.Boolean, default=False)
    validation_date = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f"Inscription('{self.prenom} {self.nom}', Tel: {self.telephone})"


class Admin(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

    def __repr__(self):
        return f"Admin('{self.username}')"

@login_manager.user_loader
def load_user(user_id):
    return Admin.query.get(int(user_id))

# ====================================================
# VUES ADMINISTRATEUR & ROUTES PRINCIPALES
# ====================================================

class CustomAdminModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('admin_login'))

admin = FlaskAdmin(app, name='Administration Manoor', url='/admin', endpoint='flask_admin_dashboard')
admin.add_view(CustomAdminModelView(Inscription, db.session, name="Inscriptions"))
admin.add_view(CustomAdminModelView(Admin, db.session, name="Gestion Admins"))


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated:
        return redirect(url_for('admin.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = Admin.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('admin.index')) 
        else:
            flash('Échec de la connexion. Vérifiez le nom d\'utilisateur et le mot de passe.', 'error')
            
    return render_template('admin_login.html')

@app.route('/admin/logout')
@login_required
def admin_logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        required_fields = ['nom', 'prenom', 'date_naissance', 'telephone', 'email', 'niveau_etude', 'formation_principale', 'formation_option', 'methode_paiement']
        data = request.form
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            error_message = f"Le champ {', '.join(missing_fields)} est manquant ou vide."
            return redirect(url_for('echec_inscription', error_message=error_message))
        
        nom = data.get('nom')
        prenom = data.get('prenom')
        date_naissance_str = data.get('date_naissance')
        telephone = data.get('telephone')
        email = data.get('email')
        etablissement_actuel = data.get('etablissement_actuel')
        niveau_etude = data.get('niveau_etude')
        formation_principale = data.get('formation_principale')
        formation_option = data.get('formation_option')
        methode_paiement = data.get('methode_paiement')

        try:
            date_naissance = datetime.strptime(date_naissance_str, '%Y-%m-%d').date()
            
            if Inscription.query.filter_by(telephone=telephone).first():
                error_message = "Ce numéro de téléphone est déjà utilisé."
                return redirect(url_for('echec_inscription', error_message=error_message))
            
            if Inscription.query.filter_by(email=email).first():
                error_message = "Cette adresse e-mail est déjà utilisée."
                return redirect(url_for('echec_inscription', error_message=error_message))

            nouvelle_inscription = Inscription(
                nom=nom, prenom=prenom, date_naissance=date_naissance, telephone=telephone, email=email, 
                etablissement_actuel=etablissement_actuel, niveau_etude=niveau_etude, formation_principale=formation_principale, 
                formation_option=formation_option, methode_paiement=methode_paiement, date_soumission=datetime.now(),
                is_valide=False, is_validation_date=False, validation_date=None
            )

            db.session.add(nouvelle_inscription)
            db.session.commit()
            
            return redirect(url_for('succes_inscription')) 

        except ValueError as e:
            error_message = f"Erreur de format des données : {str(e)}"
            db.session.rollback()
            return redirect(url_for('echec_inscription', error_message=error_message))
        except Exception as e:
            db.session.rollback()
            error_message = f"Erreur d'enregistrement critique. Détail technique : {str(e)}"
            return redirect(url_for('echec_inscription', error_message=error_message))

    return render_template('index.html')


@app.route('/succes-inscription')
def succes_inscription():
    return render_template('succes_inscription.html')

@app.route('/echec-inscription')
def echec_inscription():
    error_message = request.args.get('error_message', 'Une erreur inconnue est survenue.')
    return render_template('echec_inscription.html', error_message=error_message)

@app.cli.command("init-db")
def init_db_cli():
    """Commande CLI de secours pour créer les tables (usage local/test)."""
    with app.app_context():
        db.create_all()
        print('Base de données initialisée.')

if __name__ == '__main__':
    app.run(debug=True)
