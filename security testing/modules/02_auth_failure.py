"""
Odgovor aplikacije na neuspelu prijavu i registraciju.

Gadja lokalnu instancu aplikacije (ctx.target) i proverava tri stvari vazne za
bezbednost naloga:
  1. PRIJAVA -- user enumeration: da li je poruka o gresci ista za nepostojeci
     email i za postojeci email sa pogresnom lozinkom. Razlicite poruke otkrivaju
     koji nalozi postoje.
  2. PRIJAVA -- rate limiting: da li postoji ogranicenje broja pokusaja. Ako
     mnogo uzastopnih pogresnih prijava prodje bez blokade, brute-force je moguc.
  3. REGISTRACIJA -- user enumeration: da li registracija sa VEC POSTOJECIM
     email-om vraca prepoznatljivu poruku ("vec registrovan"), cime otkriva da
     nalog postoji.
"""

import os
import time

try:
    import requests
except ImportError:
    requests = None

NAME = "Enumeracija naloga + rate limiting (A07)"
DESCRIPTION = "Proverava poruke o gresci i ogranicenje pokusaja na login-u i register-u."

#izmisljeni nalozi -- sigurno ne postoje (login nikad ne pravi nalog, bezbedno).
#Validan format email-a (@primer.com), da zahtev prodje validaciju i stigne do
#provere postojanja naloga (inace bi vratio genericku validacionu gresku).
NEPOSTOJECI = {"email": "nepostojeci_nalog@primer.com", "lozinka": "pogresna1"}
NEPOSTOJECI2 = {"email": "jos_jedan_nepostojeci@primer.com", "lozinka": "pogresna2"}
BROJ_POKUSAJA = 8

#email za probu enumeracije na register-u -- MORA da postoji u instanci koju
#gadjamo, inace bi se napravio nalog. Zadaje se preko okruzenja, bez default-a.
REGISTER_PROBE_EMAIL = os.environ.get("REGISTER_PROBE_EMAIL", "mickomitr01@gmail.com").strip()

#validni profil koji zadovoljava RegisterForm (ime>=2, drzava>=4, telefon 8-10, lozinka>=8)
PROFIL = {
    "ime": "Test", "prezime": "Testic", "adresa": "Ulica 1",
    "grad": "Novi Sad", "drzava": "Srbija", "telefon": "0601234567",
    "lozinka": "Lozinka123", "lozinka_confirm": "Lozinka123",
}


def _post(ctx, ruta, telo):
    #POST na lokalnu instancu; vraca (status, tekst_do_200, trajanje_s) ili None
    url = ctx.target.rstrip("/") + ruta
    start = time.perf_counter()
    try:
        r = requests.post(url, json=telo, timeout=5)
    except requests.RequestException as e:
        ctx.log(f"  greska u vezi: {e}")
        return None
    return r.status_code, (r.text or "").strip()[:200], time.perf_counter() - start


def run(ctx):
    if requests is None:
        ctx.info("Biblioteka 'requests' nije instalirana (pip install requests).")
        ctx.log(ctx.summary())
        return

    ctx.log(f"Cilj: {ctx.target}  (mora biti pokrenuta lokalna instanca)")
    ctx.log("")

    #--- 1. Prijava: da li poruke otkrivaju koji nalozi postoje ---
    #Login sa pogresnom lozinkom NIKAD ne pravi nalog niti salje mejl -> bezbedno.
    #Poredimo dva razlicita nepostojeca email-a: ako su poruke iste, aplikacija
    #ne otkriva postojanje naloga. (Ako zelis strozi test sa stvarno postojecim
    #email-om, zadaj REGISTER_PROBE_EMAIL -- koristi se i ovde ako je postavljen.)
    ctx.log("--- 1. PRIJAVA: da li poruke otkrivaju koji nalozi postoje? ---")
    prvi_login = NEPOSTOJECI
    drugi_login = NEPOSTOJECI2
    if REGISTER_PROBE_EMAIL:
        drugi_login = {"email": REGISTER_PROBE_EMAIL, "lozinka": "sigurnoPogresna1"}
        ctx.log(f"  (poredim nepostojeci email sa zadatim postojecim: {REGISTER_PROBE_EMAIL})")
    else:
        ctx.log("  (poredim dva razlicita NEPOSTOJECA email-a; bezbedno, nista se ne kreira)")

    a = _post(ctx, "/api/auth/login", prvi_login)
    b = _post(ctx, "/api/auth/login", drugi_login)
    if a is None or b is None:
        ctx.info("Aplikacija ne odgovara. Pokreni je pa ponovi test.")
        ctx.log(ctx.summary())
        return

    ctx.log(f"  email #1 -> HTTP {a[0]}, odgovor: {a[1]}")
    ctx.log(f"  email #2 -> HTTP {b[0]}, odgovor: {b[1]}")
    if a[0] == b[0] and a[1] == b[1]:
        ctx.blocked("Poruke su identicne -> login ne otkriva koji nalozi postoje.")
    else:
        ctx.exposed("Poruke se razlikuju -> moguce otkriti koji nalozi postoje.")
    ctx.log("")

    #--- 2. Prijava: ima li ogranicenja broja pokusaja ---
    ctx.log(f"--- 2. PRIJAVA: {BROJ_POKUSAJA} uzastopnih pogresnih pokusaja (rate limiting?) ---")
    blokiran = False
    for i in range(1, BROJ_POKUSAJA + 1):
        r = _post(ctx, "/api/auth/login", NEPOSTOJECI)
        if r is None:
            break
        ctx.log(f"  pokusaj {i:>2}: HTTP {r[0]}  ({r[2]*1000:.0f} ms)")
        if r[0] == 429:  #Too Many Requests -> rate limiting radi
            blokiran = True
            break
    if blokiran:
        ctx.blocked("Server je vratio HTTP 429 -> rate limiting radi.")
    else:
        ctx.exposed(f"Svih {BROJ_POKUSAJA} pokusaja proslo bez blokade -> nema rate limiting-a.")
    ctx.log("")

    #--- 3. Registracija: otkriva li da email vec postoji ---
    ctx.log("--- 3. REGISTRACIJA: da li otkriva da nalog vec postoji? ---")
    if not REGISTER_PROBE_EMAIL:
        ctx.info("REGISTER_PROBE_EMAIL nije postavljen -> preskacem (da se ne bi napravio nalog).")
        ctx.log("  Postavi adresu za koju POUZDANO znas da postoji u pokrenutoj instanci:")
        ctx.log('     PowerShell:  $env:REGISTER_PROBE_EMAIL = "postojeci@primer.com"')
        ctx.log("  pa ponovo ucitaj module i pokreni test.")
    else:
        telo = dict(PROFIL, email=REGISTER_PROBE_EMAIL)
        ctx.log(f"  registracija sa (tvrdis: postojecim) email-om: {REGISTER_PROBE_EMAIL}")
        ctx.log("  (validni podaci; AKO email postoji, zahtev staje PRE pravljenja naloga)")
        r = _post(ctx, "/api/auth/register", telo)
        if r is None:
            ctx.info("Aplikacija ne odgovara.")
        else:
            ctx.log(f"  odgovor -> HTTP {r[0]}: {r[1]}")
            tekst = r[1].lower()
            if "vec registrovan" in tekst or "already" in tekst or "vec je registrovan" in tekst:
                ctx.exposed("Registracija potvrdjuje da email postoji -> enumeracija naloga.")
            elif r[0] in (200, 201) and '"id"' in r[1]:
                #SIGURNOSNA MREZA: email NIJE postojao, pa je napravljen nalog.
                #Upozori glasno -- korisnik je dao pogresan email za ovu instancu.
                ctx.exposed("PAZNJA: email NIJE postojao -> napravljen je NOV nalog i verovatno")
                ctx.exposed("poslat mejl za potvrdu. Zadati REGISTER_PROBE_EMAIL ne postoji u OVOJ")
                ctx.exposed("instanci. Obrisi taj nalog i zadaj email koji stvarno postoji ovde.")
            else:
                ctx.blocked("Odgovor ne otkriva postojanje naloga (npr. validaciona greska).")

    ctx.log("")
    ctx.log(ctx.summary())
