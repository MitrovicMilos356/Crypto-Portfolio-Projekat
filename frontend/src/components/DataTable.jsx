import { useMemo, useState } from 'react'

/*
  Tabela sa pretragom i sortiranjem po kolonama.
  columns: [{ key, label, value?: row => vrednost za sort/pretragu, render?: row => JSX,
              className?: row => string, searchable?: bool, sortable?: bool }]
*/
export default function DataTable({ rows, columns, rowKey, className = '', placeholder = 'Pretraga...', empty = 'Nema podataka.', onRowClick, selectedKey }) {
  const [search, setSearch] = useState('')
  const [sort, setSort] = useState({ key: null, dir: 'asc' })

  const vrednost = (col, row) => (col.value ? col.value(row) : row[col.key])

  const prikazani = useMemo(() => {
    const q = search.trim().toLowerCase()
    let out = rows
    if (q) {
      const kolone = columns.filter((c) => c.searchable)
      out = out.filter((row) => kolone.some((c) => String(vrednost(c, row) ?? '').toLowerCase().includes(q)))
    }
    if (sort.key) {
      const col = columns.find((c) => c.key === sort.key)
      const smer = sort.dir === 'asc' ? 1 : -1
      out = [...out].sort((a, b) => {
        const x = vrednost(col, a)
        const y = vrednost(col, b)
        if (x === y) return 0
        if (x === null || x === undefined) return 1
        if (y === null || y === undefined) return -1
        if (typeof x === 'number' && typeof y === 'number') return (x - y) * smer
        return String(x).localeCompare(String(y), 'sr') * smer
      })
    }
    return out
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rows, columns, search, sort])

  const klikNaKolonu = (col) => {
    if (col.sortable === false) return
    setSort((s) =>
      s.key !== col.key ? { key: col.key, dir: 'asc' }
        : s.dir === 'asc' ? { key: col.key, dir: 'desc' }
        : { key: null, dir: 'asc' } // treci klik vraca originalni redosled
    )
  }

  const strelica = (col) => (sort.key !== col.key ? '↕' : sort.dir === 'asc' ? '▲' : '▼')

  return (
    <div className="data-table">
      <input className="search" type="search" placeholder={placeholder}
        value={search} onChange={(e) => setSearch(e.target.value)} />
      <div className="tables-container">
        <table className={className}>
          <thead>
            <tr>
              {columns.map((col) => (
                <th key={col.key}
                  className={col.sortable === false ? '' : 'sortable'}
                  onClick={() => klikNaKolonu(col)}>
                  {col.label}
                  {col.sortable !== false && <span className={sort.key === col.key ? 'arrow active' : 'arrow'}>{strelica(col)}</span>}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {prikazani.map((row) => (
              <tr key={rowKey(row)}
                className={[onRowClick ? 'clickable' : '', selectedKey === rowKey(row) ? 'selected' : ''].join(' ').trim() || undefined}
                onClick={onRowClick ? () => onRowClick(row) : undefined}>
                {columns.map((col) => (
                  <td key={col.key} className={col.className ? col.className(row) : undefined}>
                    {col.render ? col.render(row) : vrednost(col, row)}
                  </td>
                ))}
              </tr>
            ))}
            {prikazani.length === 0 && (
              <tr>
                <td colSpan={columns.length} className="empty">{search ? 'Nema rezultata pretrage.' : empty}</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <div className="count">Prikazano {prikazani.length} od {rows.length}</div>
    </div>
  )
}
