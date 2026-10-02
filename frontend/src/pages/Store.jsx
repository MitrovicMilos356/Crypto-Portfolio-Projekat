import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import Navbar from '../components/Navbar'
import DataTable from '../components/DataTable'
import LineChartPanel from '../components/LineChartPanel'
import { cena, datumVreme, procenat } from '../format'

const kolone = [
  { key: 'rank', label: '#', className: () => 'c2 num' },
  { key: 'name', label: 'Naziv', searchable: true, className: () => 'c1 left' },
  { key: 'symbol', label: 'Simbol', searchable: true, className: () => 'c2' },
  { key: 'price', label: 'Cena', render: (c) => cena(c.price), className: () => 'c1 num' },
  { key: 'percent_change_24h', label: '24h', render: (c) => procenat(c.percent_change_24h),
    className: (c) => {
      const p = Math.round((c.percent_change_24h || 0) * 100) / 100
      return p > 0 ? 'c2 num txt-plus' : p < 0 ? 'c2 num txt-minus' : 'c2 num'
    } },
  { key: 'last_updated', label: 'Azurirano', render: (c) => datumVreme(c.last_updated), className: () => 'c1 nowrap' },
]

const PERIODI = [
  { id: 30, label: '30 dana' },
  { id: 90, label: '90 dana' },
  { id: 365, label: '1 godina' },
]

// jedna serija: slot 1 iz palete
const SERIJA = [{ key: 'price', label: 'Cena', color: '#2a78d6' }]

function CenaGrafikon({ coin }) {
  const [period, setPeriod] = useState(90)
  const [tacke, setTacke] = useState(null)
  const [greska, setGreska] = useState('')

  useEffect(() => {
    let aktivan = true
    setTacke(null)
    setGreska('')
    api(`/coins/${encodeURIComponent(coin.symbol)}/history?days=${period}`)
      .then((d) => aktivan && setTacke(d.points))
      .catch((err) => aktivan && setGreska(err.message))
    //ako korisnik brzo promeni valutu, stari odgovor ignorisemo
    return () => {
      aktivan = false
    }
  }, [coin.symbol, period])

  return (
    <>
      <LineChartPanel title={`${coin.name} (${coin.symbol})`} points={tacke || []} series={SERIJA}
        ranges={PERIODI} range={period} onRange={setPeriod} loading={!tacke && !greska} error={greska}
        empty="Istorija cena za ovu valutu nije dostupna." height={240} />
      <Link className="alert-link" to={`/alerts?coin=${encodeURIComponent(coin.symbol)}`}>
        + Obavesti me o ceni za {coin.symbol}
      </Link>
    </>
  )
}

function TransakcijaForm({ naslov, akcija, coins, poljeLabel, polje, onDone }) {
  const [coin, setCoin] = useState('')
  const [datetime, setDatetime] = useState('')
  const [vrednost, setVrednost] = useState('')

  const submit = async (e) => {
    e.preventDefault()
    try {
      const res = await api(`/store/${akcija}`, {
        method: 'POST',
        body: { selected_coin: coin || coins[0]?.symbol, datetime, [polje]: vrednost },
      })
      onDone(res.message, false)
    } catch (err) {
      onDone(err.message, true)
    }
  }

  return (
    <div className="kupovina">
      <h4>{naslov}</h4>
      <form onSubmit={submit}>
        <label>Valuta:</label>
        <select value={coin} onChange={(e) => setCoin(e.target.value)}>
          {coins.map((c) => (
            <option key={c.symbol} value={c.symbol}>{c.name} ({c.symbol})</option>
          ))}
        </select>
        <label>Datum i vreme:</label>
        <input type="datetime-local" value={datetime} onChange={(e) => setDatetime(e.target.value)} />
        <label>{poljeLabel}</label>
        <input type="text" value={vrednost} onChange={(e) => setVrednost(e.target.value)} />
        <button type="submit">{akcija}</button>
      </form>
    </div>
  )
}

export default function Store() {
  const [data, setData] = useState(null)
  const [poruka, setPoruka] = useState(null)
  const [izabrana, setIzabrana] = useState(null)

  const ucitaj = () =>
    api('/store')
      .then(setData)
      .catch((err) => setPoruka({ text: err.message, error: true }))

  useEffect(() => {
    ucitaj()
  }, [])

  // rang je redosled iz CoinMarketCap liste (po trzisnoj kapitalizaciji)
  const cryptos = useMemo(() => (data ? data.cryptos.map((c, i) => ({ ...c, rank: i + 1 })) : []), [data])

  const onDone = (text, error) => {
    setPoruka({ text, error })
    ucitaj()
  }

  return (
    <div className="store">
      <Navbar />
      {!data && !poruka && <p className="loading">Učitavanje...</p>}
      <div className="content">
        {data && (
          <div className="market">
            {cryptos.length > 0 && <CenaGrafikon coin={izabrana || cryptos[0]} />}
            <p className="market-info">
              Kliknite na valutu da vidite grafikon. Cene osvežene: {datumVreme(data.fetched_at)}
            </p>
            <DataTable className="cryptos" rows={cryptos} columns={kolone} rowKey={(c) => c.symbol}
              placeholder="Pretraga (naziv ili simbol)..."
              onRowClick={setIzabrana} selectedKey={(izabrana || cryptos[0])?.symbol} />
          </div>
        )}
        {poruka && <div className={poruka.error ? 'msg-error' : 'msg-ok'}>{poruka.text}</div>}
        {data && (
          <div className="actions">
            <TransakcijaForm naslov="Kupovina" akcija="kupovina" coins={data.coins}
              poljeLabel="Kupovna cena:" polje="price" onDone={onDone} />
            {data.imakupovina && (
              <TransakcijaForm naslov="Prodaja" akcija="prodaja" coins={data.coins}
                poljeLabel="Kolicina prodate valute:" polje="amount" onDone={onDone} />
            )}
          </div>
        )}
      </div>
    </div>
  )
}
