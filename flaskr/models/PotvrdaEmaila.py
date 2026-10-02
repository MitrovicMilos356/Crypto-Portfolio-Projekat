from flaskr import db

#potvrda email adrese korisnika (za email obavestenja o ceni)
#cuva se i SAMA adresa: ako korisnik promeni email, stara potvrda vise ne vazi
class PotvrdaEmaila(db.Model):
    __tablename__ = 'potvrda_emaila'
    korisnik_id = db.Column(db.Integer(), db.ForeignKey('korisnici.id'), primary_key=True)
    email = db.Column(db.String(255), nullable=False)
    #None dok korisnik ne klikne na link
    potvrdjeno = db.Column(db.DateTime, nullable=True)
    #kada je poslednji put poslat link (ogranicenje ponovnog slanja)
    poslato = db.Column(db.DateTime, nullable=True)

    korisnik = db.relationship('Korisnici', backref=db.backref('potvrda', uselist=False))
