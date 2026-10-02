import os
from flaskr import app
#premesteno ovde zbog komplikacija sa cirularnim pokretanjem
#pokretanje
if __name__ == '__main__':
    #debug reloader pokrece app.py dva puta - worker pokrecemo samo u procesu koji zaista sluzi zahteve
    if os.environ.get('START_WORKER', '1') == '1' and os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        from flaskr.worker import start_in_background
        start_in_background()
    app.run(debug=True)
