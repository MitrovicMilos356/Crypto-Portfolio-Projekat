import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'

//stranica Obavestenja salje ovaj dogadjaj kad oznaci obavestenja kao procitana
export const OBAVESTENJA_PROCITANA = 'obavestenja-procitana'
const OSVEZAVANJE_MS = 60 * 1000

export default function Navbar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [neprocitana, setNeprocitana] = useState(0)

  useEffect(() => {
    const proveri = () =>
      api('/alerts/unread')
        .then((d) => setNeprocitana(d.count))
        .catch(() => {})
    const procitana = () => setNeprocitana(0)
    proveri()
    const t = setInterval(proveri, OSVEZAVANJE_MS)
    window.addEventListener(OBAVESTENJA_PROCITANA, procitana)
    return () => {
      clearInterval(t)
      window.removeEventListener(OBAVESTENJA_PROCITANA, procitana)
    }
  }, [])

  const izloguj = async (e) => {
    e.preventDefault()
    await logout()
    navigate('/auth/login')
  }

  return (
    <div className="header header-dark">
      <ul>
        <li><Link to="/portfolio">Portfolio</Link></li>
        <li><Link to="/store">Unos transakcije</Link></li>
        <li>
          <Link to="/alerts">
            Obaveštenja
            {user?.potrebna_potvrda && <span title="Potrebna je potvrda email adrese"> 🔒</span>}
            {neprocitana > 0 && <span className="nav-badge" aria-label={`${neprocitana} novih`}>{neprocitana}</span>}
          </Link>
        </li>
        <li><Link to="/modifyProfile">Izmena profila</Link></li>
        <li><a href="/logout" onClick={izloguj}>Izloguj se</a></li>
      </ul>
    </div>
  )
}
