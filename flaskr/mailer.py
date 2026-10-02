#Slanje email obavestenja o ceni preko SMTP-a.
import os
import smtplib
import ssl
import math
from email.message import EmailMessage
from html import escape


def format_novac(value):
    #1234.5 = 1.234,50 $ (isti format kao na frontendu)
    if value != 0 and abs(value) < 1:
        #jeftine valute: 4 znacajne cifre na, primer(0,00001234 $)
        decimale = -math.floor(math.log10(abs(value))) + 3
        tekst = f'{value:.{decimale}f}'.rstrip('0').rstrip('.').replace('.', ',')
    else:
        tekst = f'{value:,.2f}'.replace(',', ' ').replace('.', ',').replace(' ', '.')
    return tekst + ' $'

def podesen():
    return bool(os.environ.get('SMTP_HOST') and os.environ.get('SMTP_USER'))

def _config():
    host = os.environ.get('SMTP_HOST')
    user = os.environ.get('SMTP_USER')
    if not host or not user:
        raise RuntimeError('SMTP nije podesen (SMTP_HOST i SMTP_USER su obavezni).')
    return {
        'host': host,
        'port': int(os.environ.get('SMTP_PORT', 587)),
        'user': user,
        'password': os.environ.get('SMTP_PASSWORD', ''),
        'from': os.environ.get('SMTP_FROM', user),
    }


def napravi_poruku(alert, posiljalac):
    #pravi email i njegovo formatiranje za okinuto obavestenje (bez slanja za sad)
    korisnik = alert.korisnik
    if alert.uslov == 'iznad':
        smer = 'porasla iznad'
    else:
        smer = 'pala ispod'
    naslov = f'Cena {alert.symbol} je {smer} {format_novac(alert.cena)}'
    link = os.environ.get('APP_URL', 'http://localhost:5000').rstrip('/') + '/alerts'

    poruka = EmailMessage()
    poruka['Subject'] = naslov
    poruka['From'] = posiljalac
    poruka['To'] = korisnik.email

    poruka.set_content(
        f'Zdravo {korisnik.ime},\n\n'
        f'cena valute {alert.symbol} je {smer} {format_novac(alert.cena)}.\n'
        f'Trenutna cena: {format_novac(alert.okinuto_cena)}\n\n'
        f'Vaša obaveštenja: {link}\n\n'
        f'Crypto Portfolio'
    )
    poruka.add_alternative(
        f'<p>Zdravo {escape(korisnik.ime)},</p>'
        f'<p>cena valute <b>{escape(alert.symbol)}</b> je {smer} <b>{format_novac(alert.cena)}</b>.<br>'
        f'Trenutna cena: <b>{format_novac(alert.okinuto_cena)}</b></p>'
        f'<p><a href="{escape(link)}">Pogledajte vaša obaveštenja</a></p>'
        f'<p style="color:#777">Crypto Portfolio</p>',
        subtype='html',
    )
    return poruka

def napravi_potvrdu(korisnik, link, posiljalac):
    #email sa linkom za potvrdu adrese
    poruka = EmailMessage()
    poruka['Subject'] = 'Potvrdite email adresu - Crypto Portfolio'
    poruka['From'] = posiljalac
    poruka['To'] = korisnik.email
    poruka.set_content(
        f'Zdravo {korisnik.ime},\n\n'
        f'da biste koristili obaveštenja o ceni, potvrdite svoju email adresu klikom na link:\n\n'
        f'{link}\n\n'
        f'Link važi 48 sati. Ostatak aplikacije možete koristiti i bez potvrde.\n'
        f'Ako niste otvorili nalog u aplikaciji Crypto Portfolio, slobodno zanemarite ovu poruku.\n\n'
        f'Crypto Portfolio'
    )
    poruka.add_alternative(
        f'<p>Zdravo {escape(korisnik.ime)},</p>'
        f'<p>da biste koristili <b>obaveštenja o ceni</b>, potvrdite svoju email adresu:</p>'
        f'<p><a href="{escape(link)}" style="display:inline-block;padding:10px 18px;background:#2a78d6;'
        f'color:#fff;border-radius:6px;text-decoration:none;font-weight:bold">Potvrdi email</a></p>'
        f'<p style="color:#555">Link važi 48 sati. Ostatak aplikacije možete koristiti i bez potvrde.<br>'
        f'Ako niste otvorili nalog u aplikaciji Crypto Portfolio, slobodno zanemarite ovu poruku.</p>'
        f'<p style="color:#777">Crypto Portfolio</p>',
        subtype='html',
    )
    return poruka

def _posalji(poruka, cfg):
    kontekst = ssl.create_default_context()
    if cfg['port'] == 465:
        with smtplib.SMTP_SSL(cfg['host'], cfg['port'], context=kontekst, timeout=15) as smtp:
            smtp.login(cfg['user'], cfg['password'])
            smtp.send_message(poruka)
    else:
        with smtplib.SMTP(cfg['host'], cfg['port'], timeout=15) as smtp:
            smtp.starttls(context=kontekst)
            smtp.login(cfg['user'], cfg['password'])
            smtp.send_message(poruka)

def posalji_obavestenje(alert):
    #salje email korisniku ciji je alert okinut; baca izuzetak ako slanje ne uspe
    cfg = _config()
    _posalji(napravi_poruku(alert, cfg['from']), cfg)

def posalji_potvrdu(korisnik, link):
    #salje link za potvrdu email adrese; baca izuzetak ako slanje ne uspe
    cfg = _config()
    _posalji(napravi_potvrdu(korisnik, link, cfg['from']), cfg)
