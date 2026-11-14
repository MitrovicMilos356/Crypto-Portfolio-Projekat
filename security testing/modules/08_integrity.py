"""
A08:2025 — Software or Data Integrity Failures.

Integritet = da li aplikacija verifikuje podatke/kod na koje se oslanja, umesto
da im slepo veruje. Ovaj modul proverava dve konkretne tacke:

  1. Google id_token potpis — da li se kriptografski proverava (RS256 preko
     Google-ovih javnih kljuceva) ili se token samo base64-dekodira i veruje mu
     se na osnovu toga sto je "stigao preko HTTPS-a". (provera koda u google_auth.py)

  2. Subresource Integrity (SRI) — da li <script>/<link> sa spoljnih izvora
     (CDN) imaju `integrity=` hash, da izmenjen fajl ne bi prosao. (provera
     posluzene HTML stranice)
"""

import os
import re

try:
    import requests
except ImportError:
    requests = None

NAME = "Integritet: Google id_token + SRI (A08)"
DESCRIPTION = "Proverava da li se id_token potpis verifikuje i da li spoljni resursi imaju SRI."

_BASEDIR = os.path.abspath(os.path.dirname(__file__))
KOREN = os.path.abspath(os.path.join(_BASEDIR, "..", ".."))
GOOGLE_AUTH = os.path.join(KOREN, "flaskr", "google_auth.py")

#tragovi da se potpis STVARNO proverava
MARKERI_VERIFIKACIJE = [
    "verify_oauth2_token", "id_token.verify", "pyjwkclient", "get_signing_key",
    "jwt.decode", "jwks", "verify_signature", "public_key", "oauth2/v3/certs",
]


def _proveri_id_token(ctx):
    ctx.log("--- 1. Google id_token: da li se potpis proverava? ---")
    if not os.path.isfile(GOOGLE_AUTH):
        ctx.info("flaskr/google_auth.py nije pronadjen."); return
    src = open(GOOGLE_AUTH, encoding="utf-8").read().lower()
    rucno_dekodira = "b64decode" in src or "urlsafe_b64decode" in src
    verifikuje = any(m in src for m in MARKERI_VERIFIKACIJE)
    if verifikuje:
        ctx.blocked("Kod proverava potpis id_token-a (kriptografska verifikacija).")
    elif rucno_dekodira:
        ctx.exposed("id_token potpis se NE proverava: payload se samo base64-dekodira,")
        ctx.log("     a proveravaju se samo claim-ovi (iss/aud/exp/nonce). Oslanja se na to")
        ctx.log("     sto token stize direktno sa Google-a preko HTTPS-a (TLS), ne na potpis.")
        ctx.log("     Jaca praksa: verifikovati RS256 potpis preko Google JWKS-a.")
    else:
        ctx.info("Ne mogu pouzdano da utvrdim rukovanje id_token-om iz koda.")


def _proveri_sri(ctx):
    ctx.log("--- 2. Subresource Integrity (SRI) na posluzenoj stranici ---")
    if requests is None:
        ctx.info("'requests' nije instaliran -> preskacem SRI proveru."); return
    try:
        r = requests.get(ctx.target.rstrip("/") + "/", timeout=5)
    except requests.RequestException as e:
        ctx.info(f"Aplikacija ne odgovara: {e}"); return
    html = r.text or ""
    tagovi = re.findall(r"<(?:script|link)\b[^>]*>", html, re.I)
    spoljni = []
    for t in tagovi:
        m = re.search(r'(?:src|href)\s*=\s*["\']([^"\']+)["\']', t, re.I)
        if not m:
            continue
        url = m.group(1)
        if url.startswith("http://") or url.startswith("https://") or url.startswith("//"):
            spoljni.append((url, "integrity=" in t.lower()))
    if not spoljni:
        ctx.blocked("Nema spoljnih (CDN) resursa - sve je same-origin bundle; SRI nije kljucan.")
    else:
        bez = [u for u, ima in spoljni if not ima]
        if bez:
            ctx.exposed(f"{len(bez)} spoljnih resursa bez SRI (integrity):")
            for u in bez[:8]:
                ctx.log(f"    {u}")
        else:
            ctx.blocked("Svi spoljni resursi imaju integrity (SRI).")


def run(ctx):
    ctx.log(f"Projekat: {KOREN}")
    ctx.log("")
    _proveri_id_token(ctx)
    ctx.log("")
    _proveri_sri(ctx)
    ctx.log("")
    ctx.log(ctx.summary())
