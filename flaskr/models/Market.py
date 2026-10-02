from flaskr import db

#poslednja lista top valuta sa CoinMarketCap-a (jedan red, id=1), cuva se kao JSON
class MarketSnapshot(db.Model):
    __tablename__ = 'market_snapshot'
    id = db.Column(db.Integer(), primary_key=True)
    fetched_at = db.Column(db.DateTime, nullable=False)
    data = db.Column(db.Text, nullable=False)

#dnevne cene (zatvaranje dana, UTC) sa Binance-a, kes za grafikone
class PriceHistory(db.Model):
    __tablename__ = 'price_history'
    symbol = db.Column(db.String(20), primary_key=True)
    day = db.Column(db.Date, primary_key=True)
    close = db.Column(db.Float, nullable=False)
