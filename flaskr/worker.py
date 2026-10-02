#Pozadinski proces koji osvezava cene, da stranice ne bi cekale na spoljne API-je.
import time
import schedule
from multiprocessing import Process
from flaskr import app, db
from flaskr import market

HISTORY_REFRESH_SECONDS = 3600

def _posao(naziv, funkcija):
    def pokreni():
        with app.app_context():
            try:
                funkcija()
                print(f'[worker] {naziv} osvezeno')
            except Exception as e:
                db.session.rollback()
                print(f'[worker] {naziv} nije osvezeno: {e}')
    return pokreni

def run():
    cene = _posao('cene', market.refresh_market)
    istorija = _posao('istorija', market.refresh_history)
    schedule.every(market.REFRESH_SECONDS).seconds.do(cene)
    schedule.every(HISTORY_REFRESH_SECONDS).seconds.do(istorija)
    cene()
    istorija()
    while True:
        schedule.run_pending()
        time.sleep(1)

def start_in_background():
    p = Process(target=run, name='price-worker', daemon=True)
    p.start()
    return p

if __name__ == '__main__':
    run()
