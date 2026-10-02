import flask_login
from flaskr import db, bcrypt

class Korisnici(db.Model, flask_login.UserMixin):
    id = db.Column(db.Integer(), primary_key=True, unique = True)
    ime = db.Column(db.String(length=20), nullable = False)
    prezime = db.Column(db.String(length=20), nullable = False)
    adresa = db.Column(db.String(length=40), nullable = False)
    grad = db.Column(db.String(length=20), nullable = False)
    drzava = db.Column(db.String(length=20), nullable = False)
    telefon = db.Column(db.String(length=10), nullable = False)
    email = db.Column(db.String(length=40), nullable = False, unique=True)
    #bcrypt hash lozinke (nikad cista lozinka)
    lozinka = db.Column(db.String(length=128), nullable=False)
    def is_authencticated(self):
        return True

    def postavi_lozinku(self, lozinka):
        self.lozinka = bcrypt.generate_password_hash(lozinka).decode('utf-8')

    def proveri_lozinku(self, lozinka):
        try:
            return bcrypt.check_password_hash(self.lozinka, lozinka)
        except ValueError:
            #vrednost u bazi nije validan bcrypt hash
            return False
