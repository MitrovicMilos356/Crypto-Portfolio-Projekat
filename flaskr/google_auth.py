#Prijava i registracija preko Google naloga
import os
import json
import time
import base64
import hashlib
import secrets
from urllib.parse import urlencode, quote
import requests
from flask import request, session, redirect, jsonify
from flask_login import login_user, current_user
from flaskr import app, db
from flaskr.models.Korisnici import Korisnici
from flaskr.models.GoogleNalog import GoogleNalog
from flaskr.potvrda import oznaci_potvrdjen

AUTH_URL = 'https://accounts.google.com/o/oauth2/v2/auth'
TOKEN_URL = 'https://oauth2.googleapis.com/token'
ISSUERS = ('https://accounts.google.com', 'accounts.google.com')
#koliko dugo korisnik ima da zavrsi prijavu na Google-u
MAX_TRAJANJE = 600


def _podesen():
    return bool(os.environ.get('GOOGLE_CLIENT_ID') and os.environ.get('GOOGLE_CLIENT_SECRET'))

def _redirect_uri():
    return os.environ.get('GOOGLE_REDIRECT_URI') or request.host_url.rstrip('/') + '/api/auth/google/callback'

def _neuspeh(poruka):
    #vraca korisnika na login stranicu sa porukom o gresci
    session.pop('google_oauth', None)
    return redirect('/auth/login?greska=' + quote(poruka))

def _b64url(data):
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('ascii')

def _procitaj_id_token(id_token):
    #id_token stize direktno sa Google token endpoint-a preko HTTPS-a, pa je (po OpenID Connect specifikaciji)
    #dovoljno proveriti sadrzaj; potpis ne mora posebno da se proverava
    try:
        payload = id_token.split('.')[1]
        payload += '=' * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload))
    except (IndexError, ValueError):
        return None


@app.route('/api/auth/providers')
def auth_provajderi():
    return jsonify(google=_podesen())

@app.route('/api/auth/google')
def google_pocetak():
    if not _podesen():
        return _neuspeh('Prijava preko Google-a nije podesena.')
    if current_user.is_authenticated:
        return redirect('/portfolio')
    stanje = {
        'state': secrets.token_urlsafe(32),
        'nonce': secrets.token_urlsafe(32),
        'verifier': secrets.token_urlsafe(64),
        'redirect_uri': _redirect_uri(),
        'vreme': time.time(),
    }
    session['google_oauth'] = stanje
    params = {
        'client_id': os.environ['GOOGLE_CLIENT_ID'],
        'redirect_uri': stanje['redirect_uri'],
        'response_type': 'code',
        'scope': 'openid email profile',
        'state': stanje['state'],
        'nonce': stanje['nonce'],
        'code_challenge': _b64url(hashlib.sha256(stanje['verifier'].encode('ascii')).digest()),
        'code_challenge_method': 'S256',
        'prompt': 'select_account',
    }
    return redirect(AUTH_URL + '?' + urlencode(params))

@app.route('/api/auth/google/callback')
def google_callback():
    stanje = session.pop('google_oauth', None)
    if request.args.get('error'):
        #korisnik je odustao ili je Google odbio zahtev
        return _neuspeh('Prijava preko Google-a je otkazana.')
    if not stanje or not secrets.compare_digest(request.args.get('state', ''), stanje['state']):
        return _neuspeh('Neispravan zahtev za prijavu. Pokusajte ponovo.')
    if time.time() - stanje['vreme'] > MAX_TRAJANJE:
        return _neuspeh('Prijava je istekla. Pokusajte ponovo.')
    code = request.args.get('code')
    if not code:
        return _neuspeh('Neispravan odgovor od Google-a.')

    try:
        odgovor = requests.post(TOKEN_URL, data={
            'code': code,
            'client_id': os.environ['GOOGLE_CLIENT_ID'],
            'client_secret': os.environ['GOOGLE_CLIENT_SECRET'],
            'redirect_uri': stanje['redirect_uri'],
            'grant_type': 'authorization_code',
            'code_verifier': stanje['verifier'],
        }, timeout=15)
    except requests.RequestException:
        return _neuspeh('Google trenutno nije dostupan. Pokusajte ponovo.')
    if odgovor.status_code != 200:
        return _neuspeh('Prijava preko Google-a nije uspela.')

    try:
        id_token = odgovor.json().get('id_token', '')
    except ValueError:
        return _neuspeh('Neispravan odgovor od Google-a.')
    podaci = _procitaj_id_token(id_token)
    if (not podaci
            or podaci.get('iss') not in ISSUERS
            or podaci.get('aud') != os.environ['GOOGLE_CLIENT_ID']
            or podaci.get('exp', 0) < time.time()
            or not secrets.compare_digest(str(podaci.get('nonce', '')), stanje['nonce'])
            or not podaci.get('sub')):
        return _neuspeh('Prijava preko Google-a nije uspela.')
    if not podaci.get('email') or not podaci.get('email_verified'):
        return _neuspeh('Google nalog nema potvrdjenu email adresu.')

    korisnik, nov = _nadji_ili_napravi(podaci)
    if korisnik is None:
        return _neuspeh('Nalog sa ovim emailom je vec povezan sa drugim Google nalogom.')
    #Google je potvrdio ovu adresu (ako je korisnik u medjuvremenu promenio email, tu adresu ne potvrdjujemo)
    if korisnik.email.lower() == podaci['email'].strip().lower():
        oznaci_potvrdjen(korisnik, korisnik.email)
        db.session.commit()
    login_user(korisnik)
    #novi korisnici dopunjuju adresu, grad, drzavu i telefon
    if nov:
        return redirect('/modifyProfile?dopuni=1')
    return redirect('/portfolio')

def _nadji_ili_napravi(podaci):
    #1) vec povezan Google nalog
    veza = GoogleNalog.query.filter_by(google_sub=podaci['sub']).first()
    if veza:
        return veza.korisnik, False

    #2) postojeci korisnik sa istim (Google-om potvrdjenim) emailom - povezujemo naloge
    email = podaci['email'].strip().lower()
    korisnik = Korisnici.query.filter(db.func.lower(Korisnici.email) == email).first()
    if korisnik:
        if korisnik.google_nalog is not None:
            #vec povezan sa DRUGIM Google nalogom - ne preuzimamo tudji nalog
            return None, False
        db.session.add(GoogleNalog(korisnik_id=korisnik.id, google_sub=podaci['sub']))
        db.session.commit()
        return korisnik, False

    #3) nov korisnik
    ime = (podaci.get('given_name') or podaci.get('name') or email.split('@')[0])[:20]
    prezime = (podaci.get('family_name') or '-')[:20]
    korisnik = Korisnici(ime=ime, prezime=prezime, adresa='', grad='', drzava='', telefon='',
                         email=email)
    #nasumicna lozinka koju niko ne zna; korisnik moze da postavi svoju u "Izmena profila"
    korisnik.postavi_lozinku(secrets.token_urlsafe(32))
    db.session.add(korisnik)
    db.session.flush()
    db.session.add(GoogleNalog(korisnik_id=korisnik.id, google_sub=podaci['sub']))
    db.session.commit()
    return korisnik, True
