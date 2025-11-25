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

app = Flask(__name__)

# --- CONFIGURATION PRINCIPALE ---
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'ma_cle_secrete_pour_les_sessions_manoor')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'site.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# --- CONFIGURATION D'EMAIL (À MODIFIER) ---
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')  # ⬅️ REMPLACEZ PAR VOTRE EMAIL RÉEL
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')  # ⬅️ REMPLACEZ PAR VOTRE MOT DE PASSE D'APPLICATION
app.config['MAIL_DEFAULT_SENDER'] = 'Centre Manoor <VOTRE_EMAIL_SMTP@gmail.com>'  # ⬅️ REMPLACEZ PAR VOTRE EMAIL RÉEL

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
    telephone = db.Column(db.String(8), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    formation = db.Column(db.String(50), nullable=False)
    # NOUVEAU : Option de formation (Groupe ou Individuelle)
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
    # Déterminer les frais de scolarité basés sur l'option
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
        print(f"📧 EMAIL ENVOYÉ avec succès à {inscription.email}")
        return True
    except Exception as e:
        print(f"❌ ÉCHEC ENVOI EMAIL à {inscription.email}: {e}")
        return False


def create_default_admin():
    """Crée un compte admin par défaut si aucun n'existe."""
    if User.query.filter_by(username='adminmanoor').first() is None:
        admin_user = User(username='adminmanoor')
        admin_user.set_password('motdepasse2025')  # MOT DE PASSE PAR DÉFAUT
        db.session.add(admin_user)
        db.session.commit()
        print("👤 Compte administrateur par défaut créé : adminmanoor / motdepasse2025")


# --- ROUTES FRONTEND ---
URL_PAGE_SUCCES = '/succes-inscription'


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/soumettre-inscription', methods=['POST'])
def soumettre_inscription():
    if request.method == 'POST':
        # 1. Récupération des données du formulaire (formation_option ajoutée)
        donnees_formulaire = {
            "nom": request.form.get('nom'),
            "prenom": request.form.get('prenom'),
            "datenaissance": request.form.get('datenaissance'),
            "telephone": request.form.get('telephone'),
            "email": request.form.get('email'),
            "formation": request.form.get('formation'),
            "formation_option": request.form.get('formation_option'),  # NOUVEAU
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
                formation_option=donnees_formulaire['formation_option'],  # NOUVEAU
                niveauetude=donnees_formulaire['niveauetude'],
                methode_paiement=donnees_formulaire['methode_paiement']
            )

            db.session.add(nouvelle_inscription)
            db.session.commit()

            print(f"\n✅ INSCRIPTION ENREGISTRÉE dans la BDD: {nouvelle_inscription}")

        except Exception as e:
            db.session.rollback()
            print(f"\n❌ ERREUR LORS DE L'ENREGISTREMENT : {e}")
            return redirect(url_for('page_echec_inscription'))

        if donnees_formulaire['methode_paiement'] == 'Orange Money':
            print(f"-> Déclenchement SIMULÉ de la requête Orange Money pour {donnees_formulaire['telephone']}")

        return redirect(URL_PAGE_SUCCES)

    return redirect(url_for('index'))


@app.route('/succes-inscription')
def page_succes():
    return """
        <!DOCTYPE html>
        <html lang="fr">
        <head><title>Succès</title></head>
        <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
            <div style="max-width: 600px; margin: auto; padding: 30px; border: 1px solid #007bff; border-radius: 8px;">
                <h1>✅ Pré-Inscription Reçue et Enregistrée !</h1>
                <p>Merci de votre intérêt pour le Centre Manoor. Votre candidature a été enregistrée dans notre système.</p>
                <p style="color: #28a745; font-weight: bold; margin-top: 15px;">Veuillez vérifier votre email pour les instructions de paiement et de concours.</p>
                <a href="/" style="display: inline-block; margin-top: 30px; padding: 10px 20px; background-color: #007bff; color: white; text-decoration: none; border-radius: 50px;">Retour à l'Accueil</a>
            </div>
        </body>
        </html>
    """


@app.route('/echec-inscription')
def page_echec_inscription():
    return """
        <!DOCTYPE html>
        <html lang="fr">
        <head><title>Échec</title></head>
        <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
            <div style="max-width: 600px; margin: auto; padding: 30px; border: 1px solid #ff6347; border-radius: 8px;">
                <h1>❌ Échec de l'Inscription</h1>
                <p>Une erreur est survenue lors de l'enregistrement de votre candidature. Cela peut être dû à un email ou un numéro de téléphone déjà utilisé.</p>
                <p style="color: #ff6347; font-weight: bold; margin-top: 15px;">Veuillez vérifier vos informations ou contacter le centre.</p>
                <a href="/" style="display: inline-block; margin-top: 30px; padding: 10px 20px; background-color: #007bff; color: white; text-decoration: none; border-radius: 50px;">Retour à l'Accueil</a>
            </div>
        </body>
        </html>
    """


# --- ROUTES D'AUTHENTIFICATION ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('admin_dashboard'))
        else:
            return render_template('login.html', error_message="Nom d'utilisateur ou mot de passe invalide.")

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


# --- ROUTES D'ADMINISTRATION SÉCURISÉES ---
@app.route('/admin')
@login_required
def admin_dashboard():
    inscriptions = Inscription.query.order_by(Inscription.date_soumission.desc()).all()
    return render_template('admin_dashboard.html', inscriptions=inscriptions)


@app.route('/admin/details/<int:inscription_id>')
@login_required
def inscription_details(inscription_id):
    inscription = Inscription.query.get_or_404(inscription_id)
    return render_template('inscription_details.html', inscription=inscription)


@app.route('/admin/validate/<int:inscription_id>')
@login_required
def validate_inscription(inscription_id):
    inscription = Inscription.query.get_or_404(inscription_id)

    if not inscription.is_validated:
        inscription.is_validated = True
        inscription.validation_date = datetime.now()

        try:
            db.session.commit()
            print(f"✅ Inscription ID {inscription_id} validée dans la BDD.")
            send_validation_email(inscription)

        except Exception as e:
            db.session.rollback()
            print(f"❌ ERREUR lors de la validation: {e}")

    return redirect(url_for('admin_dashboard'))


@app.route('/admin/export')
@login_required
def export_inscriptions():
    """Exporte toutes les inscriptions vers un fichier CSV."""

    inscriptions = Inscription.query.all()

    csv_header = [
        'ID', 'NOM', 'PRENOM', 'DATE_NAISSANCE', 'TELEPHONE', 'EMAIL',
        'FORMATION', 'OPTION', 'NIVEAU_ETUDE', 'METHODE_PAIEMENT',
        'DATE_SOUMISSION', 'VALIDEE', 'DATE_VALIDATION'
    ]

    csv_data = [csv_header]
    for ins in inscriptions:
        row = [
            ins.id, ins.nom, ins.prenom, ins.datenaissance, ins.telephone, ins.email,
            ins.formation, ins.formation_option, ins.niveauetude, ins.methode_paiement,
            ins.date_soumission.strftime('%Y-%m-%d %H:%M:%S'),
            'OUI' if ins.is_validated else 'NON',
            ins.validation_date.strftime('%Y-%m-%d %H:%M:%S') if ins.validation_date else ''
        ]
        csv_data.append(row)

    si = io.StringIO()
    cw = csv.writer(si, delimiter=';')
    cw.writerows(csv_data)
    output = si.getvalue().encode('utf-8')

    response = make_response(output)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    response.headers["Content-Disposition"] = f"attachment; filename=inscriptions_manoor_{timestamp}.csv"
    response.headers["Content-type"] = "text/csv; charset=utf-8"

    return response


# --- LANCEMENT DU SERVEUR ---
with app.app_context():
    db.create_all()
    create_default_admin()

if __name__ == '__main__':
    app.run(debug=True)
