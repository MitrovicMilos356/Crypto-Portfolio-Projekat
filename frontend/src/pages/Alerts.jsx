import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'
import Navbar, { OBAVESTENJA_PROCITANA } from '../components/Navbar'
import DataTable from '../components/DataTable'
import { cena as formatCena, datumVreme, procenat } from '../format'

const OSVEZAVANJE_MS = 60 * 1000

const PROCENTI = [5, 10, 20]

// cena za brzo popunjavanje: 2 decimale, a za jeftine valute 4 znacajne cifre
const zaokruzi = (v) => (v >= 1 ? v.toFixed(2) : String(Number(v.toPrecision(4))))

const opisUslova = (a) => `${a.uslov === 'iznad' ? 'iznad' : 'ispod'} ${formatCena(a.cena)}`

// Stranica je zakljucana dok korisnik ne potvrdi email (obavestenja se salju na tu adresu)
export default function Alerts() {
  const { user } = useAuth()
  const [params] = useSearchParams()
  return (
    <>
      <Navbar />
      {params.get('greska') && <div className="msg-error page-msg">{params.get('greska')}</div>}
      {user.potrebna_potvrda ? <PotvrdaPanel user={user} /> : <Sadrzaj potvrdjeno={params.get('potvrdjeno') === '1'} />}
    </>
  )
}

function PotvrdaPanel({ user }) {
  const [poruka, setPoruka] = useState(null)
  const [salje, setSalje] = useState(false)

  const posalji = async () => {
    setSalje(true)
    try {
      const r = await api('/auth/potvrda/posalji', { method: 'POST' })
      setPoruka({ text: r.message, error: false })
    } catch (err) {
      setPoruka({ text: err.message, error: true })
    }
    setSalje(false)
  }

  return (
    <div className="verify-panel">
      <h2>Potvrdite email adresu</h2>
      <p>
        Obaveštenja o ceni stižu na vaš email, pa adresu prvo treba potvrditi.
        Link za potvrdu smo poslali na <b>{user.email}</b>.
      </p>
      <p className="verify-hint">
        Ne vidite poruku? Proverite i Spam folder. Pogrešna adresa? Promenite je u <Link to="/modifyProfile">Izmena profila</Link>.
      </p>
      <button type="button" onClick={posalji} disabled={salje}>{salje ? 'Slanje...' : 'Pošalji link ponovo'}</button>
      {poruka && <div className={poruka.error ? 'msg-error' : 'msg-ok'}>{poruka.text}</div>}
    </div>
  )
}

function Sadrzaj({ potvrdjeno }) {
  const [params] = useSearchParams()
  const [trziste, setTrziste] = useState(null)
  const [obavestenja, setObavestenja] = useState(null)
  const [symbol, setSymbol] = useState(params.get('coin') || '')
  const [ciljna, setCiljna] = useState('')
  const [uslov, setUslov] = useState('iznad')
  const [poruka, setPoruka] = useState(null)
  //obavestenja koja su bila nova kad je korisnik otvorio stranicu - oznaka 'novo' ostaje do kraja posete
  const [novi, setNovi] = useState(() => new Set())

  const ucitajObavestenja = () =>
    api('/alerts')
      .then(async (lista) => {
        setObavestenja(lista)
        //obavestenja se smatraju procitanim kad ih korisnik vidi na ovoj stranici
        const neprocitana = lista.filter((a) => a.okinuto && !a.procitano)
        if (neprocitana.length) {
          setNovi((stari) => new Set([...stari, ...neprocitana.map((a) => a.id)]))
          await api('/alerts/procitano', { method: 'POST' })
          window.dispatchEvent(new Event(OBAVESTENJA_PROCITANA))
        }
      })
      .catch((err) => setPoruka({ text: err.message, error: true }))

  useEffect(() => {
    api('/store')
      .then(setTrziste)
      .catch((err) => setPoruka({ text: err.message, error: true }))
    ucitajObavestenja()
    const t = setInterval(ucitajObavestenja, OSVEZAVANJE_MS)
    return () => clearInterval(t)
  }, [])

  const cene = useMemo(() => Object.fromEntries((trziste?.cryptos || []).map((c) => [c.symbol, c.price])), [trziste])
  const izabrana = symbol || trziste?.cryptos[0]?.symbol || ''
  const trenutna = cene[izabrana]
  const broj = parseFloat(String(ciljna).replace(',', '.'))
  const brojOk = Number.isFinite(broj) && broj > 0 && trenutna !== undefined
  //"iznad" trazi cenu vecu od trenutne, "ispod" manju - inace bi se obavestenje odmah okinulo
  const smerOk = brojOk && (uslov === 'iznad' ? broj > trenutna : broj < trenutna)
  const validna = brojOk && smerOk

  const popuni = (procenat) => {
    if (trenutna === undefined) return
    setCiljna(zaokruzi(trenutna * (1 + (uslov === 'iznad' ? procenat : -procenat) / 100)))
  }

  const dodaj = async (e) => {
    e.preventDefault()
    try {
      const a = await api('/alerts', { method: 'POST', body: { symbol: izabrana, cena: broj, uslov } })
      setPoruka({ text: `Obaveštenje dodato: ${a.symbol} ${opisUslova(a)}.`, error: false })
      setCiljna('')
      ucitajObavestenja()
    } catch (err) {
      setPoruka({ text: err.message, error: true })
    }
  }

  const obrisi = async (id) => {
    await api(`/alerts/${id}`, { method: 'DELETE' })
    ucitajObavestenja()
  }

  const aktivna = useMemo(
    () => (obavestenja || []).filter((a) => !a.okinuto).map((a) => ({
      ...a,
      trenutna: cene[a.symbol],
      //koliko cena jos treba da se promeni do cilja
      doCilja: cene[a.symbol] ? ((a.cena - cene[a.symbol]) / cene[a.symbol]) * 100 : null,
    })),
    [obavestenja, cene]
  )
  const okinuta = useMemo(() => (obavestenja || []).filter((a) => a.okinuto), [obavestenja])

  const dugmeObrisi = (a) => <input type="button" value="obriši" onClick={() => obrisi(a.id)} />

  const koloneAktivna = [
    { key: 'symbol', label: 'Valuta', searchable: true, className: () => 'c1' },
    { key: 'uslov', label: 'Uslov', searchable: true, value: opisUslova, className: () => 'c2' },
    { key: 'trenutna', label: 'Trenutna cena', render: (a) => formatCena(a.trenutna), className: () => 'c1 num' },
    { key: 'doCilja', label: 'Do cilja', render: (a) => procenat(a.doCilja), className: () => 'c2 num' },
    { key: 'kreirano', label: 'Kreirano', render: (a) => datumVreme(a.kreirano), className: () => 'c1 nowrap' },
    { key: 'akcija', label: '', sortable: false, className: () => 'td1', render: dugmeObrisi },
  ]
  const koloneOkinuta = [
    { key: 'symbol', label: 'Valuta', searchable: true, className: () => 'c1',
      render: (a) => <>{a.symbol}{novi.has(a.id) && <span className="badge-new">novo</span>}</> },
    { key: 'uslov', label: 'Uslov', searchable: true, value: opisUslova, className: () => 'c2' },
    { key: 'okinuto_cena', label: 'Cena tada', render: (a) => formatCena(a.okinuto_cena), className: () => 'c1 num' },
    { key: 'okinuto', label: 'Ispunjeno', render: (a) => datumVreme(a.okinuto), className: () => 'c2 nowrap' },
    { key: 'akcija', label: '', sortable: false, className: () => 'td1', render: dugmeObrisi },
  ]

  return (
    <>
      {potvrdjeno && <div className="msg-ok page-msg">Email je potvrđen. Sada možete da dodajete obaveštenja.</div>}
      <div className="alerts">
        <section className="alert-form">
          <h2>Novo obaveštenje</h2>
          <form onSubmit={dodaj}>
            <label>Valuta:</label>
            <select value={izabrana} onChange={(e) => setSymbol(e.target.value)} disabled={!trziste}>
              {(trziste?.cryptos || []).map((c) => (
                <option key={c.symbol} value={c.symbol}>{c.name} ({c.symbol})</option>
              ))}
            </select>
            <p className="alert-current">Trenutna cena: <b>{formatCena(trenutna)}</b></p>
            <label>Obavesti me kad cena:</label>
            <div className="direction-toggle" role="radiogroup" aria-label="Smer">
              {[['iznad', '↑ Poraste iznad'], ['ispod', '↓ Padne ispod']].map(([vrednost, tekst]) => (
                <button key={vrednost} type="button" role="radio" aria-checked={uslov === vrednost}
                  className={uslov === vrednost ? `active ${vrednost}` : ''} onClick={() => setUslov(vrednost)}>
                  {tekst}
                </button>
              ))}
            </div>
            <label>Ciljna cena ($):</label>
            <input type="text" inputMode="decimal" value={ciljna} onChange={(e) => setCiljna(e.target.value)} />
            <div className="quick-fill">
              {PROCENTI.map((p) => (
                <button key={p} type="button" onClick={() => popuni(p)} disabled={trenutna === undefined}>
                  {uslov === 'iznad' ? '+' : '−'}{p} %
                </button>
              ))}
            </div>
            {validna && (
              <p className="alert-preview">
                Obavestiću vas kad {izabrana} {uslov === 'iznad' ? 'poraste iznad' : 'padne ispod'} <b>{formatCena(broj)}</b>
                {' '}({procenat(((broj - trenutna) / trenutna) * 100)} od trenutne cene).
              </p>
            )}
            {brojOk && !smerOk && (
              <p className="alert-warning">
                {izabrana} je već {uslov === 'iznad' ? 'iznad' : 'ispod'} te cene (trenutno {formatCena(trenutna)}).
                Unesite {uslov === 'iznad' ? 'veću' : 'manju'} cenu ili promenite smer.
              </p>
            )}
            <button type="submit" disabled={!validna}>Dodaj</button>
          </form>
          {poruka && <div className={poruka.error ? 'msg-error' : 'msg-ok'}>{poruka.text}</div>}
          <p className="alert-note">Cene se proveravaju na svakih nekoliko minuta.</p>
        </section>

        <section>
          <h2>Aktivna obaveštenja</h2>
          {!obavestenja ? <p className="loading">Učitavanje...</p> : (
            <DataTable className="tabele" rows={aktivna} columns={koloneAktivna} rowKey={(a) => a.id}
              placeholder="Pretraga..." empty="Nemate aktivnih obaveštenja." />
          )}

          <h2 className="alerts-h2">Ispunjena obaveštenja</h2>
          {obavestenja && (
            <DataTable className="tabele" rows={okinuta} columns={koloneOkinuta} rowKey={(a) => a.id}
              placeholder="Pretraga..." empty="Još nijedno obaveštenje nije ispunjeno." />
          )}
        </section>
      </div>
    </>
  )
}
