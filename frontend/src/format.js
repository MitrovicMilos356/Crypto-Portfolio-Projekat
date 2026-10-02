// Formatiranje brojeva i datuma za prikaz (srpski format: 1.234,56)
const LOCALE = 'sr-Latn-RS'

const broj = (value, min, max) =>
  new Intl.NumberFormat(LOCALE, { minimumFractionDigits: min, maximumFractionDigits: max }).format(value)

// Novac: uvek 2 decimale (1.234,56 $)
export function novac(value) {
  if (value === null || value === undefined || isNaN(value)) return '-'
  return broj(value, 2, 2) + ' $'
}

// Cena jedne valute: kao novac, osim za jako jeftine valute (npr. 0,00001877 $) gde pokazujemo 4 znacajne cifre
export function cena(value) {
  if (value === null || value === undefined || isNaN(value)) return '-'
  const abs = Math.abs(value)
  if (abs !== 0 && abs < 1) {
    return new Intl.NumberFormat(LOCALE, { maximumSignificantDigits: 4 }).format(value) + ' $'
  }
  return novac(value)
}

// Novac sa znakom +/- (za profit)
export function novacSaZnakom(value) {
  return (value > 0 ? '+' : '') + novac(value)
}

// Kolicina kriptovalute: do 6 decimala, bez nepotrebnih nula
export function kolicina(value) {
  if (value === null || value === undefined || isNaN(value)) return '-'
  return broj(value, 0, 6)
}

export function procenat(value) {
  if (value === null || value === undefined || isNaN(value)) return '-'
  const zaokruzeno = Math.round(value * 100) / 100
  //bez "-0,00 %" za jako male promene
  if (zaokruzeno === 0) return '0,00 %'
  return (zaokruzeno > 0 ? '+' : '') + broj(zaokruzeno, 2, 2) + ' %'
}

// Oznake na y-osi grafikona: 84.000 -> 84k $, 1.200.000 -> 1,2M $
export function osaNovac(value) {
  const abs = Math.abs(value)
  if (abs >= 1e6) return broj(value / 1e6, 0, 1) + 'M $'
  if (abs >= 1e4) return broj(value / 1e3, 0, 0) + 'k $'
  if (abs >= 100) return broj(value, 0, 0) + ' $'
  if (abs >= 1) return broj(value, 0, 2) + ' $'
  return cena(value)
}

// Datum bez vremena ('2026-09-25' -> 25.09.2026.)
export function datumDan(iso) {
  if (!iso) return '-'
  const [g, m, d] = iso.slice(0, 10).split('-')
  return `${d}.${m}.${g}.`
}

// Kratak datum za osu ('2026-09-25' -> 25.09.)
export function datumKratko(iso) {
  if (!iso) return ''
  const [, m, d] = iso.slice(0, 10).split('-')
  return `${d}.${m}.`
}

// Mesec i godina za osu dugih perioda ('2026-09-25' -> 09.2026.)
export function datumMesec(iso) {
  if (!iso) return ''
  const [g, m] = iso.slice(0, 10).split('-')
  return `${m}.${g}.`
}

// Datum i vreme: 25.09.2026. 14:30
export function datumVreme(iso) {
  if (!iso) return '-'
  const d = new Date(iso)
  if (isNaN(d)) return iso
  const p = (n) => String(n).padStart(2, '0')
  return `${p(d.getDate())}.${p(d.getMonth() + 1)}.${d.getFullYear()}. ${p(d.getHours())}:${p(d.getMinutes())}`
}
