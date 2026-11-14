"""
Bezbednosni HTTP zaglavlja (security headers).

Salje jedan obican GET na lokalnu instancu i proverava da li odgovor sadrzi
zaglavlja koja browseru govore kako da se zastiti. Nedostatak ovih zaglavlja
otvara vrata napadima kao sto su clickjacking, MIME-sniffing i deo XSS-a.

Proverava se:
  X-Frame-Options / frame-ancestors (CSP)    -> clickjacking (ubacivanje u <iframe>)
  X-Content-Type-Options: nosniff            -> MIME-sniffing
  Content-Security-Policy                    -> XSS i kontrola izvora resursa
  Referrer-Policy                            -> curenje adrese u Referer zaglavlju
  Strict-Transport-Security (HSTS)           -> prisila HTTPS-a (vazi samo preko HTTPS)
"""

try:
    import requests
except ImportError:
    requests = None

NAME = "Bezbednosna HTTP zaglavlja (A02)"
DESCRIPTION = "Proverava da li odgovor sadrzi zastitna zaglavlja; samo cita, nista ne menja."


def _oceni_csp(vrednost):
    #gruba procena kvaliteta CSP-a: postoji li uopste i ima li opasnih direktiva
    v = vrednost.lower()
    problemi = []
    if "unsafe-inline" in v:
        problemi.append("sadrzi 'unsafe-inline'")
    if "unsafe-eval" in v:
        problemi.append("sadrzi 'unsafe-eval'")
    if "default-src" not in v and "script-src" not in v:
        problemi.append("nema default-src/script-src")
    return problemi


def run(ctx):
    if requests is None:
        ctx.info("Biblioteka 'requests' nije instalirana (pip install requests).")
        ctx.log(ctx.summary())
        return

    url = ctx.target.rstrip("/") + "/"
    ctx.log(f"GET {url}")
    try:
        r = requests.get(url, timeout=5)
    except requests.RequestException as e:
        ctx.info(f"Aplikacija ne odgovara: {e}")
        ctx.log(ctx.summary())
        return

    h = {k.lower(): v for k, v in r.headers.items()}
    preko_https = url.lower().startswith("https://")
    ctx.log(f"HTTP {r.status_code}, {len(r.headers)} zaglavlja")
    ctx.log("")

    #--- X-Frame-Options (ili CSP frame-ancestors) ---
    ctx.log("--- Clickjacking zastita (X-Frame-Options / frame-ancestors) ---")
    xfo = h.get("x-frame-options")
    csp = h.get("content-security-policy", "")
    if xfo:
        ctx.blocked(f"X-Frame-Options: {xfo} -> stranica se ne moze ubaciti u tudji <iframe>.")
    elif "frame-ancestors" in csp.lower():
        ctx.blocked("CSP sadrzi frame-ancestors -> clickjacking zastita postoji.")
    else:
        ctx.exposed("Nema X-Frame-Options ni frame-ancestors -> clickjacking je moguc.")
    ctx.log("")

    #--- X-Content-Type-Options ---
    ctx.log("--- MIME-sniffing zastita (X-Content-Type-Options) ---")
    xcto = h.get("x-content-type-options", "")
    if xcto.lower() == "nosniff":
        ctx.blocked("X-Content-Type-Options: nosniff -> browser ne pogadja tip sadrzaja.")
    else:
        ctx.exposed("Nema 'nosniff' -> browser moze pogresno protumaciti tip resursa.")
    ctx.log("")

    #--- Content-Security-Policy ---
    ctx.log("--- Content-Security-Policy (XSS / kontrola izvora) ---")
    if csp:
        problemi = _oceni_csp(csp)
        ctx.log(f"CSP: {csp[:160]}")
        if problemi:
            ctx.exposed("CSP postoji ali je slab: " + "; ".join(problemi) + ".")
        else:
            ctx.blocked("CSP postoji i nema ocigledno opasnih direktiva.")
    else:
        ctx.exposed("Nema Content-Security-Policy -> nema dodatne odbrane od XSS-a.")
    ctx.log("")

    #--- Referrer-Policy ---
    ctx.log("--- Referrer-Policy (curenje adrese) ---")
    rp = h.get("referrer-policy")
    if rp:
        ctx.blocked(f"Referrer-Policy: {rp}")
    else:
        ctx.exposed("Nema Referrer-Policy -> puna adresa moze procuriti u Referer zaglavlju.")
    ctx.log("")

    #--- HSTS (samo preko HTTPS) ---
    ctx.log("--- Strict-Transport-Security (HSTS) ---")
    hsts = h.get("strict-transport-security")
    if hsts:
        ctx.blocked(f"HSTS: {hsts}")
    elif preko_https:
        ctx.exposed("Nema HSTS preko HTTPS-a -> moguc downgrade na HTTP.")
    else:
        ctx.info("Nema HSTS, ali veza je HTTP (lokalno) -> HSTS ima smisla tek preko HTTPS.")
    ctx.log("")

    #--- informativno: otkrivanje tehnologije ---
    ctx.log("--- Informativno: otkrivanje tehnologije ---")
    server = h.get("server")
    if server:
        ctx.info(f"Server zaglavlje otkriva: {server} (moze olaksati ciljane napade).")
    else:
        ctx.info("Server zaglavlje nije prisutno.")

    ctx.log("")
    ctx.log(ctx.summary())
