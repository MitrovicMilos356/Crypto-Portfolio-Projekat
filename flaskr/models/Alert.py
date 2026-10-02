from datetime import datetime
from flaskr import db

#obavestenje o ceni: "javi mi kad BTC bude iznad/ispod X $"
class PriceAlert(db.Model):
    __tablename__ = 'price_alert'
    id = db.Column(db.Integer(), primary_key=True)
    korisnik_id = db.Column(db.Integer(), db.ForeignKey('korisnici.id'), nullable=False, index=True)
    symbol = db.Column(db.String(20), nullable=False)
    #'iznad' ili 'ispod'
    uslov = db.Column(db.String(5), nullable=False)
    cena = db.Column(db.Float(), nullable=False)
    #cena u trenutku kreiranja, za prikaz koliko je cena daleko od cilja
    pocetna_cena = db.Column(db.Float(), nullable=False)
    kreirano = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    #popunjava worker kad se uslov ispuni; dok je None, obavestenje je aktivno
    okinuto = db.Column(db.DateTime, nullable=True)
    okinuto_cena = db.Column(db.Float(), nullable=True)
    procitano = db.Column(db.Boolean(), nullable=False, default=False)

    korisnik = db.relationship('Korisnici', backref=db.backref('obavestenja', lazy=True))

    def ispunjen(self, trenutna_cena):
        if self.uslov == 'iznad':
            return trenutna_cena >= self.cena
        return trenutna_cena <= self.cena
