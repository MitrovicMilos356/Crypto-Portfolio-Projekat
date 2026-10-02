import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { cena, datumDan, datumKratko, datumMesec, osaNovac } from '../format'

//"okrugle" oznake na y-osi (npr. 60k, 70k, 80k); cene i vrednosti nikad nisu negativne
function osaTicks(min, max, broj = 5) {
  const raspon = max - min || Math.abs(max) * 0.1 || 1
  const grubo = raspon / (broj - 1)
  const red = Math.pow(10, Math.floor(Math.log10(grubo)))
  const n = grubo / red
  const korak = (n <= 1 ? 1 : n <= 2 ? 2 : n <= 2.5 ? 2.5 : n <= 5 ? 5 : 10) * red
  let od = Math.max(0, Math.floor(min / korak) * korak)
  let doo = Math.ceil(max / korak) * korak
  if (od === doo) {
    od = Math.max(0, od - korak)
    doo += korak
  }
  const ticks = []
  //zaokruzivanje da ne bi bilo 0.30000000000000004
  for (let v = od; v <= doo + korak / 2; v += korak) ticks.push(Number(v.toPrecision(12)))
  return ticks
}

/*
  Linijski grafikon kroz vreme.
  points: [{ date: 'YYYY-MM-DD', <key>: broj, ... }]
  series: [{ key, label, color, step? }]   (boje po redosledu iz palete, nikad po rangu; step za vrednosti koje se menjaju skokovito)
  ranges: [{ id, label }], range, onRange  - dugmad za period iznad grafikona
*/
export default function LineChartPanel({ title, points, series, ranges, range, onRange, loading, error, empty = 'Nema podataka.', format = cena, height = 280 }) {
  const viseSerija = series.length > 1
  //za periode duze od ~6 meseci na osi pokazujemo mesec i godinu
  const dugPeriod = points.length > 200
  //oznaka vise linije ide iznad kraja, nize ispod - da se ne preklapaju
  const poslednja = points[points.length - 1] || {}
  const vrednosti = points.flatMap((p) => series.map((s) => p[s.key])).filter((v) => typeof v === 'number')
  const min = Math.min(...vrednosti)
  const max = Math.max(...vrednosti)
  const ticks = vrednosti.length ? osaTicks(min, max) : null
  const smerOznake = (key) => (series.every((s) => s.key === key || (poslednja[key] ?? 0) >= (poslednja[s.key] ?? 0)) ? -6 : 14)

  return (
    <div className="chart-panel">
      <div className="chart-head">
        <h3>{title}</h3>
        {ranges && (
          <div className="range-buttons" role="group" aria-label="Period">
            {ranges.map((r) => (
              <button key={r.id} type="button" className={r.id === range ? 'active' : ''}
                aria-pressed={r.id === range} onClick={() => onRange(r.id)}>
                {r.label}
              </button>
            ))}
          </div>
        )}
      </div>

      {viseSerija && (
        <div className="chart-legend">
          {series.map((s) => (
            <span key={s.key}><i style={{ background: s.color }} />{s.label}</span>
          ))}
        </div>
      )}

      <div className="chart-body" style={{ height }}>
        {loading && <div className="chart-msg">Učitavanje...</div>}
        {!loading && error && <div className="chart-msg msg-error">{error}</div>}
        {!loading && !error && points.length === 0 && <div className="chart-msg">{empty}</div>}
        {!loading && !error && points.length > 0 && (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={points} margin={{ top: 10, right: viseSerija ? 90 : 20, bottom: 0, left: 10 }}>
              <CartesianGrid vertical={false} stroke="#e4e3df" />
              <XAxis dataKey="date" tickFormatter={dugPeriod ? datumMesec : datumKratko} minTickGap={40}
                tick={{ fill: '#52514e', fontSize: 12 }} axisLine={{ stroke: '#d6d5d0' }} tickLine={false} />
              <YAxis tickFormatter={osaNovac} width={70} domain={ticks ? [ticks[0], ticks[ticks.length - 1]] : ['auto', 'auto']} ticks={ticks || undefined} interval={0}
                tick={{ fill: '#52514e', fontSize: 12 }} axisLine={false} tickLine={false} />
              <Tooltip content={<ChartTooltip series={series} format={format} />}
                cursor={{ stroke: '#8f8e89', strokeWidth: 1 }} isAnimationActive={false} />
              {series.map((s) => (
                <Line key={s.key} type={s.step ? 'stepAfter' : 'linear'} dataKey={s.key} name={s.label} stroke={s.color}
                  strokeWidth={2} dot={false} activeDot={{ r: 4, stroke: '#fff', strokeWidth: 2 }}
                  isAnimationActive={false}
                  label={viseSerija ? <EndLabel count={points.length} text={s.label} dy={smerOznake(s.key)} /> : false} />
              ))}
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  )
}

// Direktna oznaka serije na kraju linije
function EndLabel({ x, y, index, count, text, dy }) {
  if (index !== count - 1) return null
  return (
    <text x={x + 6} y={y} dy={dy} fontSize={12} fill="#52514e">{text}</text>
  )
}

function ChartTooltip({ active, payload, label, series, format }) {
  if (!active || !payload || !payload.length) return null
  return (
    <div className="chart-tooltip">
      <div className="chart-tooltip-date">{datumDan(label)}</div>
      {series.map((s) => {
        const p = payload.find((x) => x.dataKey === s.key)
        if (!p) return null
        return (
          <div key={s.key} className="chart-tooltip-row">
            <i style={{ background: s.color }} />
            <b>{format(p.value)}</b>
            {series.length > 1 && <span>{s.label}</span>}
          </div>
        )
      })}
    </div>
  )
}
