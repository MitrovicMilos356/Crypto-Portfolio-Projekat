import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../auth'
import GoogleButton from '../components/GoogleButton'

const polja = [
  { name: 'ime', placeholder: 'Ime', minLength: 2, maxLength: 20 },
  { name: 'prezime', placeholder: 'Prezime', minLength: 2, maxLength: 20 },
  { name: 'adresa', placeholder: 'Adresa', minLength: 3, maxLength: 40 },
  { name: 'grad', placeholder: 'Grad', minLength: 2, maxLength: 20 },
  { name: 'drzava', placeholder: 'Država', minLength: 4, maxLength: 20 },
  { name: 'telefon', placeholder: 'Broj telefona', minLength: 8, maxLength: 10 },
  { name: 'email', placeholder: 'Email', type: 'email', maxLength: 40 },
  { name: 'lozinka', placeholder: 'Lozinka', type: 'password', minLength: 8, maxLength: 40 },
  { name: 'lozinka_confirm', placeholder: 'Potvrda lozinke', type: 'password', minLength: 8, maxLength: 40 },
]

export default function Register() {
  const { register } = useAuth()
  const [podaci, setPodaci] = useState(Object.fromEntries(polja.map((p) => [p.name, ''])))
  const [poruka, setPoruka] = useState('')

  const submit = async (e) => {
    e.preventDefault()
    if (podaci.lozinka !== podaci.lozinka_confirm) {
      setPoruka('Lozinke se ne poklapaju!')
      return
    }
    try {
      await register(podaci)
    } catch (err) {
      setPoruka(err.message)
    }
  }

  return (
    <div className="page-light">
      <div className="header header-light">
        <ul>
          <li><Link to="/auth/login">Uloguj se</Link></li>
        </ul>
      </div>
      <div className="form">
        <h1>Registracija</h1>
        <GoogleButton text="Registruj se preko Google-a" />
        <form onSubmit={submit}>
          {polja.map(({ name, type = 'text', ...rest }) => (
            <input key={name} className="input" type={type} required {...rest}
              value={podaci[name]} onChange={(e) => setPodaci({ ...podaci, [name]: e.target.value })} />
          ))}
          {poruka && <div className="msg-error">{poruka}</div>}
          <button className="button" type="submit">Otvori nalog</button>
        </form>
      </div>
    </div>
  )
}
