#Kes cena: trenutne cene (CoinMarketCap) i dnevna istorija (Binance).
#Worker (flaskr/worker.py) ovo osvezava u pozadini, a rute samo citaju iz baze.
#Ako worker ne radi, rute same osveze podatke kad zastare.
import os
import json
import ccxt
from datetime import datetime, date, timedelta, timezone
from flaskr import db
from flaskr.models.Coin import Coin
from flaskr.models.Market import MarketSnapshot, PriceHistory
from flaskr.models.Alert import PriceAlert
from flaskr.models.Transaction import Transaction
from flaskr.models.crypto import Crypto
from flaskr import mailer

#CoinMarketCap besplatni plan: ~333 poziva dnevno, pa je 5 min bezbedno
REFRESH_SECONDS = int(os.environ.get('PRICE_REFRESH_SECONDS', 300))
MAX_AGE = timedelta(seconds=REFRESH_SECONDS * 2)

#valute koje su uvek ~1$ i nemaju par sa USDT na Binance-u
STABILNE = {'USDT'}

_crypto = Crypto()
_exchange = None

def _binance():
    #jedna instanca po procesu, ucitavanje marketa traje par sekundi
    global _exchange
    if _exchange is None:
        _exchange = ccxt.binance()
        _exchange.load_markets()
    return _exchange


def refresh_market():
    #skine top 50 sa CoinMarketCap-a, sacuva snapshot i azurira tabelu coin
    cryptos = _crypto.get_top()
    snapshot = db.session.get(MarketSnapshot, 1) or MarketSnapshot(id=1)
    snapshot.fetched_at = datetime.utcnow()
    snapshot.data = json.dumps(cryptos)
    db.session.add(snapshot)

    postojeci = {coin.symbol: coin for coin in Coin.query.all()}
    for crypto in cryptos:
        cena = crypto['quote']['USD']['price']
        if crypto['symbol'] in postojeci:
            postojeci[crypto['symbol']].current_value = cena
        else:
            db.session.add(Coin(name=crypto['name'], symbol=crypto['symbol'], current_value=cena))
    db.session.commit()
    check_alerts({c['symbol']: c['quote']['USD']['price'] for c in cryptos})
    return cryptos

def check_alerts(cene):
    #okida aktivna obavestenja ciji je uslov ispunjen po novim cenama
    okinuta = []
    for alert in PriceAlert.query.filter(PriceAlert.okinuto.is_(None)).all():
        cena = cene.get(alert.symbol)
        if cena is not None and alert.ispunjen(cena):
            alert.okinuto = datetime.utcnow()
            alert.okinuto_cena = cena
            alert.procitano = False
            okinuta.append(alert)
    db.session.commit()
    if okinuta:
        posalji_emailove(okinuta)
    return okinuta

def posalji_emailove(okinuta):
    if not mailer.podesen():
        print(f'[alerts] okinuto obavestenja: {len(okinuta)}; email se ne salje jer SMTP nije podesen (vidi .env)')
        return
    from flaskr.potvrda import email_potvrdjen
    #podrazumevano samo na potvrdjene adrese: lozinkom se moze registrovati i tudja adresa
    svima = os.environ.get('ALERT_EMAIL_SVIMA') == '1'
    for alert in okinuta:
        if not svima and not email_potvrdjen(alert.korisnik):
            print(f'[alerts] obavestenje {alert.id}: email preskocen (adresa nije potvrdjena)')
            continue
        try:
            mailer.posalji_obavestenje(alert)
            print(f'[alerts] obavestenje {alert.id}: email poslat')
        except Exception as e:
            print(f'[alerts] obavestenje {alert.id}: email nije poslat: {e}')

def get_market():
    #vraca (lista valuta, vreme osvezavanja); osvezi ako je kes prazan ili star
    snapshot = db.session.get(MarketSnapshot, 1)
    if snapshot is None or datetime.utcnow() - snapshot.fetched_at > MAX_AGE:
        try:
            cryptos = refresh_market()
            return cryptos, datetime.utcnow()
        except Exception:
            db.session.rollback()
            if snapshot is None:
                raise
            #API nije dostupan - bolje stari podaci nego nikakvi
    return json.loads(snapshot.data), snapshot.fetched_at

def current_prices():
    cryptos, _ = get_market()
    return {c['symbol']: c['quote']['USD']['price'] for c in cryptos}


def _day_ms(d):
    return int(datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp() * 1000)

def update_history(symbol, start):
    #dopuni kes dnevnih cena za valutu od datuma start do danas
    if symbol in STABILNE:
        return
    exchange = _binance()
    pair = symbol + '/USDT'
    if pair not in exchange.markets:
        return

    danas = datetime.now(timezone.utc).date()
    prvi, poslednji = db.session.query(db.func.min(PriceHistory.day), db.func.max(PriceHistory.day)).filter_by(symbol=symbol).one()
    if prvi is not None and prvi <= start:
        #vec imamo pocetak - skidamo samo od poslednjeg dana (on je mozda bio nepotpun)
        start = poslednji
    elif prvi is not None and start < prvi:
        #proveri da li Binance uopste ima starije podatke (nova valuta)
        pocetak = exchange.fetch_ohlcv(pair, '1d', _day_ms(start), 1)
        if pocetak and datetime.fromtimestamp(pocetak[0][0] / 1000, timezone.utc).date() >= prvi:
            start = poslednji

    since = _day_ms(start)
    while True:
        candles = exchange.fetch_ohlcv(pair, '1d', since, 1000)
        for ts, _o, _h, _l, close, _v in candles:
            day = datetime.fromtimestamp(ts / 1000, timezone.utc).date()
            db.session.merge(PriceHistory(symbol=symbol, day=day, close=close))
        db.session.commit()
        if len(candles) < 1000 or not candles:
            break
        since = candles[-1][0] + 1
        if datetime.fromtimestamp(since / 1000, timezone.utc).date() > danas:
            break

def get_history(symbol, start):
    #{datum: cena} od datuma start; prazno ako Binance nema tu valutu
    if symbol in STABILNE:
        danas = datetime.now(timezone.utc).date()
        return {start + timedelta(days=i): 1.0 for i in range((danas - start).days + 1)}
    try:
        update_history(symbol, start)
    except Exception:
        #Binance nedostupan - koristimo ono sto je vec u kesu
        db.session.rollback()
    redovi = PriceHistory.query.filter(PriceHistory.symbol == symbol, PriceHistory.day >= start).order_by(PriceHistory.day).all()
    return {r.day: r.close for r in redovi}

def held_symbols():
    return [s for (s,) in db.session.query(Transaction.coin_name).distinct()]

def refresh_history():
    #istorija za sve valute koje korisnici imaju, od prve transakcije
    for symbol in held_symbols():
        prva = db.session.query(db.func.min(Transaction.date)).filter_by(coin_name=symbol).scalar()
        if prva is None:
            continue
        try:
            update_history(symbol, prva.date())
        except Exception as e:
            db.session.rollback()
            print(f'[worker] istorija za {symbol} nije osvezena: {e}')
