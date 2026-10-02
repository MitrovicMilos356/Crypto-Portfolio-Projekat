import os
import secrets
import time
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt

basedir = os.path.abspath(os.path.dirname(__file__))

def ucitaj_env(putanja):
    #ucitava KEY=vrednost linije iz .env fajla; vec postavljene env varijable imaju prednost
    if not os.path.isfile(putanja):
        return
    with open(putanja, encoding='utf-8') as f:
        for linija in f:
            linija = linija.strip()
            if not linija or linija.startswith('#') or '=' not in linija:
                continue
            kljuc, vrednost = linija.split('=', 1)
            vrednost = vrednost.strip()
            if len(vrednost) >= 2 and vrednost[0] == vrednost[-1] and vrednost[0] in ('"', "'"):
                vrednost = vrednost[1:-1]
            os.environ.setdefault(kljuc.strip(), vrednost)

ucitaj_env(os.path.join(basedir, '..', '.env'))

def secret_key():
    #SECRET_KEY iz okruzenja/.env; ako ga nema, generise se jednom i cuva u fajlu (npr. u Docker volumenu)
    kljuc = os.environ.get('SECRET_KEY')
    if kljuc:
        return kljuc
    putanja = os.environ.get('SECRET_KEY_FILE', os.path.join(basedir, '..', 'instance', 'secret_key'))
    try:
        #O_EXCL: ako dva procesa (web i worker) krenu istovremeno, samo jedan pravi fajl
        fd = os.open(putanja, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        #drugi proces je mozda upravo napravio fajl i jos upisuje kljuc
        for _ in range(50):
            with open(putanja, encoding='utf-8') as f:
                kljuc = f.read().strip()
            if kljuc:
                return kljuc
            time.sleep(0.1)
        raise RuntimeError(f'Fajl sa SECRET_KEY je prazan: {putanja}')
    except FileNotFoundError:
        os.makedirs(os.path.dirname(putanja), exist_ok=True)
        return secret_key()
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        kljuc = secrets.token_hex(32)
        f.write(kljuc)
    return kljuc

app = Flask(__name__)
app.secret_key = secret_key()
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///' + os.path.join(basedir, 'database.db'))
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

from flaskr import routes
from flaskr.models import Market, Alert, GoogleNalog, PotvrdaEmaila
from flaskr import google_auth, potvrda

#kreira tabele koje fale (postojece ne dira)
with app.app_context():
    db.create_all()
    #zatvori konekcije: gunicorn (--preload) i multiprocessing posle ovoga prave nove procese
    db.engine.dispose()