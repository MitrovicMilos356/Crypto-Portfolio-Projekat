from flaskr import db

#veza izmedju korisnika i njegovog Google naloga (Google "sub" je trajni ID naloga, email moze da se promeni)
class GoogleNalog(db.Model):
    __tablename__ = 'google_nalog'
    id = db.Column(db.Integer(), primary_key=True)
    korisnik_id = db.Column(db.Integer(), db.ForeignKey('korisnici.id'), nullable=False, unique=True)
    google_sub = db.Column(db.String(255), nullable=False, unique=True)

    korisnik = db.relationship('Korisnici', backref=db.backref('google_nalog', uselist=False))
