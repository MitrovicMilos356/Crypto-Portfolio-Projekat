#Potvrda email adrese za naloge napravljene lozinkom.
import os
from datetime import datetime, timedelta
from urllib.parse import quote
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from flask import request, redirect, jsonify
from flask_login import login_required, current_user
from flaskr import app, db, mailer
from flaskr.models.Korisnici import Korisnici
from flaskr.models.PotvrdaEmaila import PotvrdaEmaila

TRAJANJE_LINKA = 48 * 3600
PAUZA_IZMEDJU_SLANJA = timedelta(seconds=60)

def _serializer():
    return URLSafeTimedSerializer(app.secret_key, salt='potvrda-emaila')


def email_potvrdjen(korisnik):
    potvrda = korisnik.potvrda
    if potvrda is not None:
        return potvrda.potvrdjeno is not None and potvrda.email.lower() == korisnik.email.lower()
    #nalozi povezani sa Google-om su vec potvrdjeni.
    return korisnik.google_nalog is not None

def potrebna_potvrda(korisnik):
    return mailer.podesen() and not email_potvrdjen(korisnik)

def oznaci_potvrdjen(korisnik, email):
    potvrda = korisnik.potvrda or PotvrdaEmaila(korisnik_id=korisnik.id)
    potvrda.email = email
    potvrda.potvrdjeno = datetime.utcnow()
    db.session.add(potvrda)

def zapocni_potvrdu(korisnik):
    #Pravi potvrdu za korisnika koji je zabocinje i stablja je u bazu.
    potvrda = korisnik.potvrda or PotvrdaEmaila(korisnik_id=korisnik.id)
    potvrda.email = korisnik.email
    potvrda.potvrdjeno = None
    potvrda.poslato = None
    db.session.add(potvrda)
    db.session.commit()
    return posalji_link(korisnik)

def posalji_link(korisnik):
    if not mailer.podesen():
        print(f'[potvrda] korisnik {korisnik.id}: link nije poslat jer SMTP nije podesen')
        return None
    token = _serializer().dumps({'id': korisnik.id, 'email': korisnik.email.lower()})
    osnova = os.environ.get('APP_URL') or request.host_url
    link = osnova.rstrip('/') + '/api/auth/potvrda?token=' + quote(token)
    try:
        mailer.posalji_potvrdu(korisnik, link)
    except Exception as e:
        print(f'[potvrda] korisnik {korisnik.id}: link nije poslat: {e}')
        return None
    korisnik.potvrda.poslato = datetime.utcnow()
    db.session.commit()
    print(f'[potvrda] korisnik {korisnik.id}: link poslat')
    return korisnik.email


@app.route('/api/auth/potvrda')
def potvrdi_email():
    #link iz email-a; radi i ako korisnik trenutno nije ulogovan
    def kraj(greska=None):
        if current_user.is_authenticated:
            if greska:
                return redirect('/alerts?greska=' + quote(greska))
            return redirect('/alerts?potvrdjeno=1')
        if greska:
            return redirect('/auth/login?greska=' + quote(greska))
        return redirect('/auth/login?poruka=' + quote('Email je potvrdjen. Prijavite se.'))

    try:
        podaci = _serializer().loads(request.args.get('token', ''), max_age=TRAJANJE_LINKA)
    except SignatureExpired:
        return kraj('Link za potvrdu je istekao. Posaljite novi sa stranice Obavestenja.')
    except BadSignature:
        return kraj('Link za potvrdu nije ispravan.')

    korisnik = db.session.get(Korisnici, podaci.get('id'))
    #link vazi samo za adresu na koju je poslat - ako je email u medjuvremenu promenjen, ne vazi
    if korisnik is None or korisnik.email.lower() != podaci.get('email'):
        return kraj('Link za potvrdu vise ne vazi (email adresa je promenjena).')
    oznaci_potvrdjen(korisnik, korisnik.email)
    db.session.commit()
    return kraj()

@app.route('/api/auth/potvrda/posalji', methods=['POST'])
@login_required
def posalji_ponovo():
    korisnik = db.session.get(Korisnici, current_user.id)
    if email_potvrdjen(korisnik):
        return jsonify(error='Email je vec potvrdjen.'), 400
    if not mailer.podesen():
        return jsonify(error='Slanje email-a nije podeseno na serveru.'), 503
    potvrda = korisnik.potvrda
    if potvrda is None or potvrda.email.lower() != korisnik.email.lower():
        return _odgovor(zapocni_potvrdu(korisnik))
    if potvrda.poslato and datetime.utcnow() - potvrda.poslato < PAUZA_IZMEDJU_SLANJA:
        sekundi = int((PAUZA_IZMEDJU_SLANJA - (datetime.utcnow() - potvrda.poslato)).total_seconds()) + 1
        return jsonify(error=f'Sacekajte {sekundi} s pre ponovnog slanja.'), 429
    return _odgovor(posalji_link(korisnik))

def _odgovor(poslato_na):
    if poslato_na is None:
        return jsonify(error='Slanje email-a nije uspelo. Pokusajte kasnije.'), 502
    return jsonify(message=f'Link je poslat na {poslato_na}.')
