"""
A10:2025 — Mishandling of Exceptional Conditions.

Ne napada jednu rupu, nego gleda KAKO se aplikacija ponasa na neocekivan unos:
da li oda interne detalje (stack trace, SQL, putanje), da li "pukne" sa HTTP 500
umesto kontrolisane greske, ili da li debugger stranica procuri.

Salje namerno neispravne/granicne zahteve i klasifikuje odgovor:
  - oda detalje (traceback / Werkzeug / sqlite / SELECT / putanja) 
  - HTTP 500 (nekontrolisana greska umesto 400)                     
  - kontrolisana greska (400/401/404, bez detalja)                  

"""

import os

try:
    import requests
except ImportError:
    requests = None

NAME = "Rukovanje greskama / izuzecima (A10)"
DESCRIPTION = "Salje neispravne zahteve i trazi stack trace, interne detalje ili 500."

EMAIL = (os.environ.get("APP_TEST_EMAIL") or os.environ.get("CSRF_TEST_EMAIL") or "").strip()
LOZINKA = os.environ.get("APP_TEST_PASSWORD") or os.environ.get("CSRF_TEST_PASSWORD") or ""

#markeri koji u telu odgovora znace curenje internih detalja
MARKERI = [
    "traceback (most recent call", "werkzeug", "sqlite3", "operationalerror",
    "programmingerror", "select ", "/app/", "flaskr/", "psycopg", "sqlalchemy",
]


def _analiziraj(ctx, naziv, status, telo):
    t = (telo or "").lower()
    nadjeni = [m for m in MARKERI if m in t]
    izvod = (telo or "").strip().replace("\n", " ")[:120]
    ctx.log(f"  {naziv}: HTTP {status}")
    if nadjeni:
        ctx.exposed(f"{naziv}: odgovor oda interne detalje ({', '.join(nadjeni)}).")
        ctx.log(f"     odgovor: {izvod}")
    elif status == 500:
        ctx.exposed(f"{naziv}: HTTP 500 - nekontrolisana greska (trebalo bi 400).")
        ctx.log(f"     odgovor: {izvod}")
    else:
        ctx.blocked(f"{naziv}: kontrolisana greska bez internih detalja.")


def _raw_post(ctx, sess, ruta, data=None, json=None):
    try:
        if json is not None:
            r = sess.post(ctx.target.rstrip("/") + ruta, json=json, timeout=10)
        else:
            r = sess.post(ctx.target.rstrip("/") + ruta, data=data,
                          headers={"Content-Type": "application/json"}, timeout=10)
        return r.status_code, r.text
    except requests.RequestException as e:
        return None, str(e)


def run(ctx):
    if requests is None:
        ctx.info("Biblioteka 'requests' nije instalirana (pip install requests).")
        ctx.log(ctx.summary())
        return

    baza = ctx.target.rstrip("/")
    s = requests.Session()

    #--- 1. neautentikovani probe-ovi ---
    ctx.log("--- 1. Neispravan ulaz bez prijave ---")
    st, tel = _raw_post(ctx, s, "/api/auth/login", data="{neispravan json")
    if st is None:
        ctx.info(f"Aplikacija ne odgovara: {tel}")
        ctx.log(ctx.summary()); return
    _analiziraj(ctx, "Login + neispravan JSON", st, tel)

    st, tel = _raw_post(ctx, s, "/api/auth/login", json={"email": {"a": 1}, "lozinka": [1, 2]})
    _analiziraj(ctx, "Login + pogresni tipovi", st, tel)

    try:
        r = s.get(baza + "/api/nepostojeca-ruta-xyz", timeout=5)
        _analiziraj(ctx, "Nepostojeca ruta (404?)", r.status_code, r.text)
    except requests.RequestException as e:
        ctx.info(f"404 probe greska: {e}")
    ctx.log("")

    #--- 2. autentikovani probe-ovi (pretraga) ---
    ctx.log("--- 2. Neispravan ulaz na pretrazi (trazi prijavu) ---")
    if not EMAIL or not LOZINKA:
        ctx.info("APP_TEST_EMAIL/PASSWORD nisu postavljeni -> preskacem probe pretrage.")
    else:
        lr = s.post(baza + "/api/auth/login", json={"email": EMAIL, "lozinka": LOZINKA}, timeout=5)
        if lr.status_code != 200:
            ctx.info(f"Prijava nije uspela (HTTP {lr.status_code}) -> preskacem probe pretrage.")
        else:
            #samo jedan navodnik: razbija sirov SQL u ranjivoj pretrazi
            try:
                r = s.get(baza + "/api/coins/search", params={"q": "'"}, timeout=10)
                _analiziraj(ctx, "Pretraga + nezatvoren navodnik", r.status_code, r.text)
            except requests.RequestException as e:
                ctx.info(f"probe greska: {e}")
            #ogroman unos
            try:
                r = s.get(baza + "/api/coins/search", params={"q": "A" * 100000}, timeout=15)
                _analiziraj(ctx, "Pretraga + ogroman unos (100k)", r.status_code, r.text)
            except requests.RequestException as e:
                ctx.info(f"probe (veliki unos) greska: {e}")

    ctx.log("")
    ctx.log("(sa debug=True izuzetak bi vratio Werkzeug stack trace)")
    ctx.log("")
    ctx.log(ctx.summary())
