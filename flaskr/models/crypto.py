import os
from requests import Session
import json

class Crypto:
  def get_top(self, limit=50):
      api_key = os.environ.get('CMC_API_KEY')
      if not api_key:
          raise RuntimeError('CMC_API_KEY nije podesen (vidi .env.example).')
      url = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest'
      parameters = {
        'start':'1',
        'limit':str(limit),
        'convert':'USD'
      }
      headers = {
        'Accepts': 'application/json',
        'X-CMC_PRO_API_KEY': api_key,
      }

      session = Session()
      session.headers.update(headers)

      response = session.get(url, params=parameters)
      data = json.loads(response.text)
      return data['data']