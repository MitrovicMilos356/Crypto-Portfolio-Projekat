import { useEffect, useMemo, useState } from 'react'
import { api } from '../api'
import Navbar from '../components/Navbar'
import DataTable from '../components/DataTable'
import LineChartPanel from '../components/LineChartPanel'
import { datumVreme, kolicina, novac, novacSaZnakom } from '../format'

// paleta: slot 1 (plava) i slot 2 (narandzasta), uvek istim redom
const SERIJE = [
  { key: 'vrednost', label: 'Vrednost', color: '#2a78d6' },
  { key: 'ulozeno', label: 'Uloženo', color: '#eb6834', step: true },
]

const PERIODI = [
  { id: 30, label: '1M' },
  { id: 90, label: '3M' },
  { id: 180, label: '6M' },
  { id: 365, label: '1G' },
  { id: 0, label: 'Sve' },
]

export default function Portfolio() {
  const [data, setData] = useState(null)
  const [greska, setGreska] = useState('')
  const [istorija, setIstorija] = useState(null)
  const [greskaIstorije, setGreskaIstorije] = useState('')
  const [period, setPeriod] = useState(0)

  const ucitaj = () => {
    api('/portfolio')
      .then(setData)
      .catch((err) => setGreska(err.message))
    //istorija moze da traje duze (Binance), pa se ucitava posebno
    api('/portfolio/history')
      .then((h) => {
        setIstorija(h)
        setGreskaIstorije('')
      })
      .catch((err) => setGreskaIstorije(err.message))
  }

  useEffect(() => {
    ucitaj()
  }, [])

  const ukloni = async (id) => {
    await api(`/transactions/${id}`, { method: 'DELETE' })
    ucitaj()
  }

  const tackeGrafikona = useMemo(() => {
    if (!istorija) return []
    return period ? istorija.points.slice(-(period + 1)) : istorija.points
  }, [istorija, period])

  // prodaje se u bazi cuvaju sa negativnom cenom
  const transakcije = useMemo(
    () => (data ? data.transactions.map((t) => ({ ...t, tip: t.price > 0 ? 'Kupovina' : 'Prodaja', iznos: Math.abs(t.price) })) : []),
    [data]
  )
  const poValuti = useMemo(
    () => (data ? Object.entries(data.result).map(([coin, v]) => ({ coin, ...v, kupljeno: Math.abs(v.kupljeno), prodato: Math.abs(v.prodato) })) : []),
    [data]
  )

  const koloneTransakcija = useMemo(() => [
    { key: 'coin_name', label: 'Valuta', searchable: true, className: () => 'c1' },
    { key: 'tip', label: 'Tip', searchable: true, className: (t) => (t.price > 0 ? 'c2 tip-kupovina' : 'c2 tip-prodaja') },
    { key: 'iznos', label: 'Iznos', render: (t) => novac(t.iznos), className: () => 'c1 num' },
    { key: 'amount', label: 'Kolicina', render: (t) => kolicina(t.amount), className: () => 'c2 num' },
    { key: 'date', label: 'Datum', searchable: true, value: (t) => t.date, render: (t) => datumVreme(t.date), className: () => 'c1' },
    { key: 'akcija', label: '', sortable: false, className: () => 'td1',
      render: (t) => <input type="button" value="ukloni" onClick={() => ukloni(t.id)} /> },
  ], [])

  const koloneValuta = useMemo(() => [
    { key: 'coin', label: 'Valuta', searchable: true },
    { key: 'kupljeno', label: 'Kupljeno', render: (v) => novac(v.kupljeno), className: () => 'num' },
    { key: 'prodato', label: 'Prodato', render: (v) => novac(v.prodato), className: () => 'num' },
    { key: 'preostalo', label: 'Preostalo valute', render: (v) => kolicina(v.preostalo), className: () => 'num' },
    { key: 'ulozeno', label: 'Ulozen novac', render: (v) => novac(v.ulozeno), className: () => 'num' },
    { key: 'profit', label: '+/-', render: (v) => novacSaZnakom(v.profit), className: (v) => (v.profit >= 0 ? 'profit plus' : 'profit minus') },
  ], [])

  return (
    <>
      <Navbar />
      {greska && <div className="msg-error page-msg">{greska}</div>}
      {!data && !greska && <p className="loading">Učitavanje...</p>}
      {data && (
        <div className="portfolio">
          <section className="portfolio-chart">
            <LineChartPanel title="Vrednost portfolija" points={tackeGrafikona} series={SERIJE} format={novac}
              ranges={PERIODI} range={period} onRange={setPeriod}
              loading={!istorija && !greskaIstorije} error={greskaIstorije}
              empty="Dodajte transakciju da biste videli grafikon." />
            {istorija && istorija.nedostaje.length > 0 && (
              <p className="chart-note">Nema istorije cena za: {istorija.nedostaje.join(', ')} (nisu uračunate u prošle dane).</p>
            )}
          </section>

          <section>
            <h2>Transakcije</h2>
            <DataTable className="tabele" rows={transakcije} columns={koloneTransakcija} rowKey={(t) => t.id}
              placeholder="Pretraga (valuta, tip, datum)..." empty="Nemate transakcija." />
          </section>

          <section>
            <h2>Stanje po valutama</h2>
            <DataTable className="tabele" rows={poValuti} columns={koloneValuta} rowKey={(v) => v.coin}
              placeholder="Pretraga valute..." empty="Nemate valuta." />
            <div className="p">
              <p>Ukupna vrednost preostale valute: <b>{novac(data.ukupnavrednost)}</b></p>
              <p>Ukupan profit: <b className={data.ukupanprofit >= 0 ? 'txt-plus' : 'txt-minus'}>{novacSaZnakom(data.ukupanprofit)}</b></p>
            </div>
          </section>
        </div>
      )}
    </>
  )
}
