# Projekat_DRS – Crypto Portfolio

Flask backend  + React frontend + SQLite database

## Stare specifikacije projekta:
- registracija i logovanje
- prikaz kripto valuta
- unosenje kupovina i prodaja valuta
- pregled istoruja transakcija
- pokazivanje ulaganja i profit

## Dodata prosirenja:
- google registracija naloga
- slanje mailova za postavljene alarme
- graficki prikaz kretanja cena valuta i graficki prikaz istorije profita.
- popravljeni bagovi od ranije

## Brzo pokretanje (Docker)

```
docker compose up --build
```

Aplikacija je na **http://localhost:5000**
Port moze da se menja: `PORT=5050 docker compose up --build`.

## Pokretanje bez Docker-a (development)

Potrebni su Python 3.11+ i Node.js 14.18+.

Backend (port 5000) – pokreće i worker kao poseban proces:

```
pip install -r requirements.txt
python app.py
```

Frontend 

```
cd frontend
npm install
npm run dev
```

Aplikacija je na http://localhost:3000.

Bez Docker-a baza je `flaskr/database.db` (pravi se automatski ako ne postoji), a automatski
`SECRET_KEY` se čuva u `instance/secret_key`.