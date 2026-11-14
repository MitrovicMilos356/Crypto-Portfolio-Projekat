"""
A02 (Cryptographic Failures) — zastita session kolacica.

Posle prijave server salje session cookie kojim se korisnik identifikuje.
Taj cookie mora da ima zastitne flagove, inace ga je lakse ukrasti ili
zloupotrebiti:

  HttpOnly  -> JavaScript ne moze da ga procita (stiti pri XSS-u)
  Secure    -> salje se samo preko HTTPS (stiti od presretanja na mrezi)
  SameSite  -> ne salje se uz zahteve sa tudjih sajtova (stiti od CSRF-a)

Modul se prijavljuje i cita sirova `Set-Cookie` zaglavlja, pa proverava flagove
na `session` kolacicu. Samo cita, nista ne menja. Time proverava da li je moguce
izvrsiti napad.
"""

import os

try:
    import requests
except ImportError:
    requests = None

NAME = "Zastita session kolacica (A04)"
DESCRIPTION = "Proverava flagove na session kolacicu posle prijave (A02)."

EMAIL = (os.environ.get("APP_TEST_EMAIL") or os.environ.get("CSRF_TEST_EMAIL") or "").strip()
LOZINKA = os.environ.get("APP_TEST_PASSWORD") or os.environ.get("CSRF_TEST_PASSWORD") or ""


def _set_cookie_zaglavlja(r):
    #vraca listu sirovih Set-Cookie vrednosti (requests ih zna spojiti u jedno)
    try:
        return r.raw.headers.getlist("Set-Cookie")
    except Exception:
        jedan = r.headers.get("Set-Cookie")
        return [jedan] if jedan else []


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
    preko_https = baza.lower().startswith("https://")
    ctx.log(f"Prijava kao {EMAIL} na {baza} ...")
    try:
        r = requests.post(baza + "/api/auth/login", json={"email": EMAIL, "lozinka": LOZINKA},
                          timeout=5, allow_redirects=False)
    except requests.RequestException as e:
        ctx.info(f"Aplikacija ne odgovara: {e}")
        ctx.log(ctx.summary())
        return
    if r.status_code != 200:
        ctx.info(f"Prijava nije uspela (HTTP {r.status_code}). Proveri kredencijale.")
        ctx.log(ctx.summary())
        return

    kolacici = _set_cookie_zaglavlja(r)
    session_ck = next((c for c in kolacici if c.lower().lstrip().startswith("session=")), None)
    if not session_ck:
        ctx.info("Server nije poslao 'session' kolacic na prijavi.")
        ctx.log(f"  (vidjeni kolacici: {[c.split('=')[0] for c in kolacici]})")
        ctx.log(ctx.summary())
        return

    ctx.log(f"  Set-Cookie: {session_ck}")
    nisko = session_ck.lower()
    atributi = [d.strip() for d in nisko.split(";")[1:]]
    ctx.log("")

    #--- HttpOnly ---
    ctx.log("--- HttpOnly (zastita pri XSS-u) ---")
    if "httponly" in atributi:
        ctx.blocked("HttpOnly postavljen -> JavaScript ne moze da procita kolacic.")
    else:
        ctx.exposed("Nema HttpOnly -> ubacena skripta (XSS) moze procitati session.")
    ctx.log("")

    #--- SameSite ---
    ctx.log("--- SameSite (zastita od CSRF-a) ---")
    samesite = next((a.split("=", 1)[1] for a in atributi if a.startswith("samesite")), None)
    if samesite in ("lax", "strict"):
        ctx.blocked(f"SameSite={samesite} -> kolacic se ne salje sa tudjih sajtova.")
    elif samesite == "none":
        ctx.exposed("SameSite=None -> kolacic se salje i sa tudjih sajtova (olaksava CSRF).")
    else:
        ctx.exposed("Nema SameSite -> kolacic se salje uz zahteve sa tudjih sajtova (CSRF).")
    ctx.log("")

    #--- Secure ---
    ctx.log("--- Secure (zastita od presretanja na mrezi) ---")
    if "secure" in atributi:
        ctx.blocked("Secure postavljen -> kolacic ide samo preko HTTPS.")
    elif preko_https:
        ctx.exposed("Nema Secure preko HTTPS-a -> kolacic moze procuriti preko HTTP-a.")
    else:
        ctx.info("Nema Secure, ali veza je HTTP (lokalno). Preko HTTPS-a Secure je obavezan.")

    ctx.log("")
    ctx.log(ctx.summary())
