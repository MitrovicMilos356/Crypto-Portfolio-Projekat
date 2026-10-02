export async function api(path, { method = 'GET', body } = {}) {
  const res = await fetch('/api' + path, {
    method,
    credentials: 'same-origin',
    headers: body !== undefined ? { 'Content-Type': 'application/json' } : undefined,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })
  let data = null
  try {
    data = await res.json()
  } catch {
    // prazan ili ne-JSON odgovor
  }
  if (!res.ok) {
    const err = new Error((data && data.error) || 'Doslo je do greske.')
    err.status = res.status
    throw err
  }
  return data
}
