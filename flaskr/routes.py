import os
import math
from flaskr import app, db
from flask import request, jsonify, send_from_directory, abort
from flask_login import LoginManager, login_user, login_required, current_user, logout_user
from flaskr.models.Korisnici import Korisnici
from flaskr.models.FlaskForms import LoginForm, RegisterForm
from flaskr.models.Coin import Coin
from flaskr import market
from flaskr.mailer import format_novac
from flaskr.potvrda import email_potvrdjen, potrebna_potvrda, zapocni_potvrdu
from functools import wraps
from flaskr.models.Transaction import Transaction
from flaskr.models.Alert import PriceAlert
from multiprocessing import Queue, Process
from itertools import groupby
from operator import attrgetter
from datetime import datetime, date, timedelta
import ccxt


#flask login

login_manager = LoginManager()
login_manager.init_app(app)
@login_manager.user_loader
def user_loader(id):
    return Korisnici.query.get(int(id))

@login_manager.unauthorized_handler
def unauthorized():
    return jsonify(error='Niste ulogovani.'), 401


def greska(poruka, status=400):
    return jsonify(error=poruka), status

def prva_greska(form):
    #prva poruka greske iz WTForms validacije
    for poruke in form.errors.values():
        if poruke:
            return poruke[0]
    return 'Unesite validne podatke.'

def cene_nedostupne(e):
    #bez CMC_API_KEY cene nikad nece raditi - kazemo tacno sta treba podesiti
    if isinstance(e, RuntimeError) and 'CMC_API_KEY' in str(e):
        return greska('Cene nisu dostupne: CMC_API_KEY nije podesen (vidi .env.example).', 503)
    return greska('Cene trenutno nisu dostupne, pokusajte ponovo.', 503)

def korisnik_json(u):
    return {'id': u.id, 'ime': u.ime, 'prezime': u.prezime, 'adresa': u.adresa, 'grad': u.grad,
            'drzava': u.drzava, 'telefon': u.telefon, 'email': u.email,
            'email_potvrdjen': email_potvrdjen(u), 'potrebna_potvrda': potrebna_potvrda(u)}

def transakcija_json(t):
    datum = None
    if t.date:
        datum = t.date.isoformat()
    return {'id': t.id, 'coin_name': t.coin_name, 'price': t.price, 'amount': t.amount,
            'date': datum}


#auth
@app.route('/api/me')
@login_required
def me():
    return jsonify(korisnik_json(current_user))

@app.route('/api/auth/login', methods=['POST'])
def login():
    form = LoginForm(meta={'csrf': False})
    if not form.validate():
        return greska('Uneli ste neispravne podatke!')
    email = form.email.data
    lozinka = form.lozinka.data
    if(email == "" or email.isspace()
       or  lozinka == "" or lozinka.isspace()):
        return greska('Uneli ste neispravne podatke!')
    u = Korisnici.query.filter_by(email=email).first()
    if (not u or not u.proveri_lozinku(lozinka)):
        return greska('Uneli ste neispravne podatke!')
    login_user(u)
    return jsonify(korisnik_json(u))

@app.route('/api/auth/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify(ok=True)

@app.route('/api/auth/register', methods=['POST'])
def register():
    form = RegisterForm(meta={'csrf': False})
    if not form.validate():
        return greska(prva_greska(form))
    ime = form.ime.data
    prezime = form.prezime.data
    adresa = form.adresa.data
    grad = form.grad.data
    drzava = form.drzava.data
    telefon = form.telefon.data
    email = form.email.data
    lozinka = form.lozinka.data
    lozinka_confirm = form.lozinka_confirm.data
    if (ime == "" or ime.isspace()
        or prezime == "" or prezime.isspace()
        or adresa == "" or adresa.isspace()
        or grad == "" or grad.isspace()
        or drzava == "" or drzava.isspace()
        or telefon == "" or telefon.isspace()
        or email == "" or email.isspace()
        or lozinka == "" or lozinka.isspace()
        or lozinka_confirm =="" or lozinka_confirm.isspace() or lozinka != lozinka_confirm):
        return greska('Unesite validne podatke.')
    if (Korisnici.query.filter_by(email=email).first()):
        return greska('Uneli ste email koji je vec registrovan!')
    u = Korisnici(ime=ime, prezime= prezime, adresa=adresa, grad=grad, drzava=drzava, telefon=telefon, email=email)
    u.postavi_lozinku(lozinka)
    db.session.add(u)
    db.session.commit()
    login_user(u)
    #link za potvrdu adrese (potreban za obavestenja o ceni)
    zapocni_potvrdu(u)
    return jsonify(korisnik_json(u)), 201


#store
@app.route('/api/store')
@login_required
def store():
    #skrivanje prodaje
    imakupovina = Transaction.query.filter(Transaction.korisnik_id==current_user.id, Transaction.price > 0).first() is not None

    try:
        cryptos, fetched_at = market.get_market()
    except Exception as e:
        return cene_nedostupne(e)
    coins = Coin.query.all()

    simboli = {crypto['symbol'] for crypto in cryptos}
    return jsonify(
        cryptos=[{'name': c['name'], 'symbol': c['symbol'], 'price': c['quote']['USD']['price'], 'last_updated': c['last_updated'], 'percent_change_24h': c['quote']['USD'].get('percent_change_24h')} for c in cryptos],
        coins=[{'name': c.name, 'symbol': c.symbol} for c in coins if c.symbol in simboli],
        imakupovina=imakupovina,
        fetched_at=fetched_at.isoformat() + 'Z',
    )

@app.route('/api/store/kupovina', methods=['POST'])
@login_required
def store_kupovina():
    data = request.get_json(silent=True) or {}
    selected_coin = data.get('selected_coin')
    datet = data.get('datetime')
    try:
        price = float(data.get('price'))
    except (TypeError, ValueError):
        return greska('Uneta kupovna cena nije validna.')
    if not math.isfinite(price) or price <= 0:
        return greska('Kupovna cena mora biti veca od nule.')
    if not selected_coin or not datet:
        return greska('Neuspela transakcija')

    result_queue = Queue()
    p = Process(target=kupovina, args=(selected_coin, price, current_user.id, result_queue, datet))
    return pokreni(p, result_queue)

@app.route('/api/store/prodaja', methods=['POST'])
@login_required
def store_prodaja():
    data = request.get_json(silent=True) or {}
    selected_coin = data.get('selected_coin')
    datet = data.get('datetime')
    try:
        amount = float(data.get('amount'))
    except (TypeError, ValueError):
        return greska('Unesena vrednost količine nije validna.')
    if not math.isfinite(amount) or amount <= 0:
        return greska('Kolicina mora biti veca od nule.')
    if not selected_coin or not datet:
        return greska('Neuspela transakcija')
    #stanje samo za valutu koja se prodaje (kupljeno - prodato)
    suma = 0
    for transaction in Transaction.query.filter_by(korisnik_id=current_user.id, coin_name=selected_coin).all():
        if transaction.price > 0:
            suma += transaction.amount
        else:
            suma -= transaction.amount
    if amount > suma + 1e-9:
        return greska(f'Uneli ste vise valute nego sto imate ({suma:.6f} {selected_coin}).')

    result_queue = Queue()
    p = Process(target=prodaja, args=(selected_coin, amount, current_user.id, result_queue, datet))
    return pokreni(p, result_queue)

def pokreni(p, result_queue):
    p.start()
    p.join()
    poruka = result_queue.get()
    if poruka == 'Neuspela transakcija':
        return greska(poruka)
    return jsonify(message=poruka)


#Portfolio nakon login-a
@app.route('/api/portfolio')
@login_required
def portfolio():
    transactions = Transaction.query.filter_by(korisnik_id=current_user.id).all()
    try:
        cene = market.current_prices()
    except Exception as e:
        return cene_nedostupne(e)

    transactions_by_coin_name = groupby(sorted(transactions, key=attrgetter('coin_name')), attrgetter('coin_name'))

    result = {}

    ukupnavrednost=0
    ukupanprofit=0


    for coin_name, transakcije in transactions_by_coin_name:
        vrednost =0
        profit=0
        k=0
        p=0
        ka=0.00
        pa=0
        for transakcija in transakcije:


            if transakcija.price >0:
                 k+=transakcija.price
                 ka+=transakcija.amount
            else:
                 p+=transakcija.price
                 pa+=transakcija.amount
        result[coin_name] = { 'kupljeno': 0, 'prodato':0, 'profit': 0, 'preostalo':0, 'ulozeno':0}
        result[coin_name]['kupljeno']= k*-1
        result[coin_name]['prodato']=p *-1
        preostalo = ka-pa
        result[coin_name]['preostalo']=preostalo
        ulozeno = k*-1+ p *-1
        result[coin_name]['ulozeno']= ulozeno* (-1)
        if coin_name in cene:
             vrednost = cene[coin_name] * preostalo
             profit = vrednost + ulozeno
        result[coin_name]['profit']= profit
        ukupanprofit += profit
        ukupnavrednost += vrednost
    return jsonify(
        transactions=[transakcija_json(t) for t in transactions],
        result=result,
        ukupanprofit=ukupanprofit,
        ukupnavrednost=ukupnavrednost,
    )

#istorija cena jedne valute za grafikon
@app.route('/api/coins/<symbol>/history')
@login_required
def istorija_valute(symbol):
    try:
        dana = min(max(int(request.args.get('days', 90)), 1), 1825)
    except ValueError:
        dana = 90
    start = date.today() - timedelta(days=dana)
    istorija = market.get_history(symbol.upper(), start)
    return jsonify(symbol=symbol.upper(), points=[{'date': d.isoformat(), 'price': c} for d, c in sorted(istorija.items())])

#vrednost portfolija kroz vreme: za svaki dan kolicina valuta * cena tog dana
@app.route('/api/portfolio/history')
@login_required
def istorija_portfolija():
    transakcije = sorted(Transaction.query.filter_by(korisnik_id=current_user.id).all(), key=attrgetter('date'))
    if not transakcije:
        return jsonify(points=[], nedostaje=[])
    start = transakcije[0].date.date()
    danas = date.today()
    simboli = sorted({t.coin_name for t in transakcije})
    istorija = {s: market.get_history(s, start) for s in simboli}
    try:
        trenutne = market.current_prices()
    except Exception:
        trenutne = {}
    nedostaje = [s for s in simboli if not istorija[s] and s not in trenutne]

    kolicine = {s: 0.0 for s in simboli}
    poslednja_cena = {}
    ulozeno = 0.0
    i = 0
    points = []
    dan = start
    while dan <= danas:
        while i < len(transakcije) and transakcije[i].date.date() <= dan:
            t = transakcije[i]
            #kupovina ima pozitivnu cenu, prodaja negativnu
            if t.price > 0:
                kolicine[t.coin_name] += t.amount
            else:
                kolicine[t.coin_name] -= t.amount
            ulozeno += t.price
            i += 1
        vrednost = 0.0
        for s in simboli:
            cena = istorija[s].get(dan)
            if dan == danas and s in trenutne:
                cena = trenutne[s]
            if cena is not None:
                poslednja_cena[s] = cena
            vrednost += kolicine[s] * poslednja_cena.get(s, 0.0)
        points.append({'date': dan.isoformat(), 'vrednost': vrednost, 'ulozeno': ulozeno})
        dan += timedelta(days=1)
    return jsonify(points=points, nedostaje=nedostaje)

#obavestenja o ceni
MAX_AKTIVNIH_OBAVESTENJA = 20

def utc_iso(dt):
    if dt:
        return dt.isoformat() + 'Z'
    return None

def potvrda_obavezna(f):
    #stranica Obavestenja je zakljucana dok korisnik ne potvrdi email
    @wraps(f)
    def omot(*args, **kwargs):
        if potrebna_potvrda(current_user):
            return jsonify(error='Potvrdite email adresu da biste koristili obavestenja.', potvrda_potrebna=True), 403
        return f(*args, **kwargs)
    return omot

def obavestenje_json(a):
    return {'id': a.id, 'symbol': a.symbol, 'uslov': a.uslov, 'cena': a.cena, 'pocetna_cena': a.pocetna_cena,
            'kreirano': utc_iso(a.kreirano), 'okinuto': utc_iso(a.okinuto), 'okinuto_cena': a.okinuto_cena,
            'procitano': a.procitano}

@app.route('/api/alerts')
@login_required
@potvrda_obavezna
def obavestenja():
    lista = PriceAlert.query.filter_by(korisnik_id=current_user.id).order_by(PriceAlert.kreirano.desc()).all()
    return jsonify([obavestenje_json(a) for a in lista])

@app.route('/api/alerts/unread')
@login_required
def neprocitana_obavestenja():
    if potrebna_potvrda(current_user):
        return jsonify(count=0)
    broj = PriceAlert.query.filter(PriceAlert.korisnik_id == current_user.id, PriceAlert.okinuto.isnot(None),
                                   PriceAlert.procitano.is_(False)).count()
    return jsonify(count=broj)

@app.route('/api/alerts', methods=['POST'])
@login_required
@potvrda_obavezna
def novo_obavestenje():
    data = request.get_json(silent=True) or {}
    symbol = str(data.get('symbol') or '').upper()
    try:
        cena = float(data.get('cena'))
    except (TypeError, ValueError):
        return greska('Unesite validnu cenu.')
    if not math.isfinite(cena) or cena <= 0:
        return greska('Cena mora biti veca od nule.')
    try:
        trenutne = market.current_prices()
    except Exception as e:
        return cene_nedostupne(e)
    if symbol not in trenutne:
        return greska('Izaberite valutu sa liste.')
    trenutna = trenutne[symbol]
    if cena == trenutna:
        return greska('Ciljna cena je jednaka trenutnoj ceni.')
    #smer bira korisnik; ako ga ne posalje, odredjuje se prema trenutnoj ceni
    uslov = data.get('uslov')
    if not uslov:
        if cena > trenutna:
            uslov = 'iznad'
        else:
            uslov = 'ispod'
    if uslov not in ('iznad', 'ispod'):
        return greska('Izaberite da li cena treba da poraste ili padne.')
    #obavestenje koje bi se odmah okinulo nema smisla
    if uslov == 'iznad' and cena < trenutna:
        return greska(f'{symbol} je vec iznad {format_novac(cena)} (trenutno {format_novac(trenutna)}). Unesite vecu cenu.')
    if uslov == 'ispod' and cena > trenutna:
        return greska(f'{symbol} je vec ispod {format_novac(cena)} (trenutno {format_novac(trenutna)}). Unesite manju cenu.')
    aktivnih = PriceAlert.query.filter(PriceAlert.korisnik_id == current_user.id, PriceAlert.okinuto.is_(None)).count()
    if aktivnih >= MAX_AKTIVNIH_OBAVESTENJA:
        return greska(f'Mozete imati najvise {MAX_AKTIVNIH_OBAVESTENJA} aktivnih obavestenja.')
    alert = PriceAlert(korisnik_id=current_user.id, symbol=symbol, cena=cena, pocetna_cena=trenutna, uslov=uslov)
    db.session.add(alert)
    db.session.commit()
    return jsonify(obavestenje_json(alert)), 201

@app.route('/api/alerts/<int:id>', methods=['DELETE'])
@login_required
@potvrda_obavezna
def obrisi_obavestenje(id):
    PriceAlert.query.filter_by(id=id, korisnik_id=current_user.id).delete()
    db.session.commit()
    return jsonify(ok=True)

@app.route('/api/alerts/procitano', methods=['POST'])
@login_required
@potvrda_obavezna
def procitaj_obavestenja():
    PriceAlert.query.filter(PriceAlert.korisnik_id == current_user.id, PriceAlert.okinuto.isnot(None),
                            PriceAlert.procitano.is_(False)).update({'procitano': True})
    db.session.commit()
    return jsonify(ok=True)

@app.route('/api/transactions/<int:id>', methods=['DELETE'])
@login_required
def ukloni_transakciju(id):
    Transaction.query.filter_by(id=id,korisnik_id=current_user.id).delete()
    db.session.commit()
    return jsonify(ok=True)


@app.route('/api/profile', methods=['PUT'])
@login_required
def modify():
    data = request.get_json(silent=True) or {}
    ime = data.get('ime', '')
    prezime = data.get('prezime', '')
    adresa = data.get('adresa', '')
    grad = data.get('grad', '')
    drzava = data.get('drzava', '')
    telefon = data.get('telefon', '')
    email = data.get('email', '')
    lozinka = data.get('lozinka', '')
    lozinkapotvrde = data.get('lozinkapotvrde', '')
    izmena = Korisnici.query.filter_by(id=current_user.id).first()
    promenjen_email = False
    if (ime != "" and not ime.isspace()):
            izmena.ime = ime
    if (prezime != "" and not prezime.isspace()):
            izmena.prezime = prezime
    if (adresa != "" and not adresa.isspace()):
            izmena.adresa = adresa
    if (grad != "" and not grad.isspace()):
            izmena.grad = grad
    if (drzava != "" and not drzava.isspace()):
            izmena.drzava = drzava
    if(telefon != "" and not telefon.isspace()):
            izmena.telefon = telefon
    if(email !="" and not email.isspace()):
            if (Korisnici.query.filter_by(email=email).first()):
                db.session.rollback()
                return greska('Uneli ste email koji je vec registrovan!')
            izmena.email = email
            promenjen_email = True

    if(lozinka != "" and not lozinka.isspace()):
            if(lozinka != lozinkapotvrde):
                    db.session.rollback()
                    return greska('Unete lozinke nisu iste.')
            if(lozinkapotvrde != "" and not lozinkapotvrde.isspace()):
                izmena.postavi_lozinku(lozinka)
    db.session.commit()
    if promenjen_email:
        #nova adresa mora ponovo da se potvrdi, inace bi obavestenja isla na nepotvrdjenu adresu
        zapocni_potvrdu(izmena)
    return jsonify(korisnik_json(izmena))


#React frontend (build iz frontend/dist)
FRONTEND_DIST = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend', 'dist'))

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def frontend(path):
    if path.startswith('api/'):
        abort(404)
    if path and os.path.isfile(os.path.join(FRONTEND_DIST, path)):
        return send_from_directory(FRONTEND_DIST, path)
    if not os.path.isfile(os.path.join(FRONTEND_DIST, 'index.html')):
        return 'Frontend nije buildovan. Pokrenite "npm run build" u folderu frontend/.', 404
    return send_from_directory(FRONTEND_DIST, 'index.html')

def kupovina(selected_coin, price, current_user_id, result_queue, datet):
    with app.app_context():
        #na Linux-u (Docker) proces nastaje fork-om i nasledjuje konekcije roditelja - ne koristimo ih
        db.engine.dispose(close=False)
        coin = Coin.query.filter_by(symbol=selected_coin).first()
        if coin is not None:
            exchange = ccxt.binance()
            timestamp = int(datetime.strptime(datet, '%Y-%m-%dT%H:%M').timestamp() * 1000)
            valute = selected_coin + '/USDT'
            try:
                response = exchange.fetch_ohlcv(valute, '1m', timestamp, 1)
                onecoin = response[0][1]
            except:
                result_queue.put('Neuspela transakcija')
                return

            bought_amount = float(price) / onecoin
            python_datetime = datetime.strptime(datet, '%Y-%m-%dT%H:%M')
            new_transaction = Transaction(coin_name = selected_coin, korisnik_id = current_user_id,date=python_datetime, amount = bought_amount, price = price)
            db.session.add(new_transaction)
            db.session.commit()
            result_queue.put('Transakcija je uspesno zabelezena')
            return
        else:
            result_queue.put('Neuspela transakcija')
            return

def prodaja(selected_coin, amount, current_user_id, result_queue, datet):
    with app.app_context():
        #na Linux-u (Docker) proces nastaje fork-om i nasledjuje konekcije roditelja - ne koristimo ih
        db.engine.dispose(close=False)
        coin = Coin.query.filter_by(symbol=selected_coin).first()
        if coin is not None:
            exchange = ccxt.binance()
            timestamp = int(datetime.strptime(datet, '%Y-%m-%dT%H:%M').timestamp() * 1000)
            valute = selected_coin + '/USDT'
            try:
                response = exchange.fetch_ohlcv(valute, '1m', timestamp, 1)
                onecoin = response[0][1]
            except:
                result_queue.put('Neuspela transakcija')
                return
            price = onecoin * amount * -1.0
            python_datetime = datetime.strptime(datet, '%Y-%m-%dT%H:%M')
            new_transaction = Transaction(coin_name = selected_coin, korisnik_id = current_user_id,date=python_datetime, amount = amount, price = price)
            db.session.add(new_transaction)
            db.session.commit()
            result_queue.put('Transakcija je uspesno zabelezena')
            return
        else:
            result_queue.put('Neuspela transakcija')
            return
