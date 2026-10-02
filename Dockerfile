# 1) build React frontend-a
FROM node:20-alpine AS frontend
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# 2) Python backend + buildovan frontend
FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
# zavisnosti posebno, da se ne instaliraju ponovo pri svakoj izmeni koda
COPY requirements.txt ./
RUN pip install -r requirements.txt gunicorn==23.0.0
COPY . .
COPY --from=frontend /frontend/dist ./frontend/dist
EXPOSE 5000
# gunicorn umesto Flask development servera; app:app = objekat "app" iz app.py
# --preload: aplikacija (i pravljenje tabela) se ucitava jednom, pre pokretanja radnih procesa
CMD ["gunicorn", "--preload", "--bind", "0.0.0.0:5000", "--workers", "2", "--threads", "4", "--timeout", "60", "app:app"]
