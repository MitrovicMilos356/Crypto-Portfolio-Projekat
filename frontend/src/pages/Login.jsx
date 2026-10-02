import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useAuth } from '../auth'
import GoogleButton from '../components/GoogleButton'

export default function Login() {
  const { login } = useAuth()
  const [email, setEmail] = useState('')
  const [lozinka, setLozinka] = useState('')
  const [params] = useSearchParams()
  //greska sa Google prijave stize kao ?greska=...
  const [poruka, setPoruka] = useState(params.get('greska') || '')
  //npr. posle potvrde email-a stize ?poruka=...
  const info = params.get('poruka')

  const submit = async (e) => {
    e.preventDefault()
    try {
      await login(email, lozinka)
    } catch (err) {
      setPoruka(err.message)
    }
  }

  return (
    <div className="page-light">
      <div className="header header-light">
        <ul>
          <li><Link to="/auth/register">Registracija</Link></li>
        </ul>
      </div>
      <div className="form">
        {info && !poruka && <div className="info-box">{info}</div>}
        <GoogleButton />
        <form onSubmit={submit}>
          <input className="input" type="email" placeholder="Upiši email" maxLength={40} required
            value={email} onChange={(e) => setEmail(e.target.value)} />
          <input className="input" type="password" placeholder="Upiši lozinku" maxLength={40} required
            value={lozinka} onChange={(e) => setLozinka(e.target.value)} />
          {poruka && <div className="msg-error">{poruka}</div>}
          <button className="button" type="submit">Uloguj se</button>
        </form>
      </div>
    </div>
  )
}
