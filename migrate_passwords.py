
#Sifre su ranije bile u obicnom tekstu, ovim su migrirane u hash vrednosti.
from flaskr import app, db
from flaskr.models.Korisnici import Korisnici

def je_hesirana(lozinka):
    return lozinka.startswith(('$2a$', '$2b$', '$2y$')) and len(lozinka) == 60

if __name__ == '__main__':
    with app.app_context():
        korisnici = Korisnici.query.all()
        promenjeno = 0
        for k in korisnici:
            if not je_hesirana(k.lozinka):
                k.postavi_lozinku(k.lozinka)
                promenjeno += 1
        db.session.commit()
        print(f'Hesirano lozinki: {promenjeno} (ukupno korisnika: {len(korisnici)})')
