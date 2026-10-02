import { useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'
import Navbar from '../components/Navbar'

const polja = [
  { name: 'ime', placeholder: 'Ime' },
  { name: 'prezime', placeholder: 'Prezime' },
  { name: 'adresa', placeholder: 'Adresa' },
  { name: 'grad', placeholder: 'Grad' },
  { name: 'drzava', placeholder: 'Drzava' },
  { name: 'telefon', placeholder: 'Telefon' },
  { name: 'email', placeholder: 'Email', type: 'email' },
  { name: 'lozinka', placeholder: 'Lozinka', type: 'password' },
  { name: 'lozinkapotvrde', placeholder: 'Potvrda lozinke', type: 'password' },
]

export default function ModifyProfile() {
  const { setUser } = useAuth()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  //posle prve prijave preko Google-a fale adresa, grad, drzava i telefon
  const dopuni = params.get('dopuni') === '1'
  const [podaci, setPodaci] = useState(Object.fromEntries(polja.map((p) => [p.name, ''])))
  const [poruka, setPoruka] = useState('')
  const [info, setInfo] = useState('')

  const submit = async (e) => {
    e.preventDefault()
    try {
      const novi = await api('/profile', { method: 'PUT', body: podaci })
      setUser(novi)
      //nova adresa mora da se potvrdi - kazemo korisniku umesto da ga odmah prebacimo
      if (podaci.email && novi.potrebna_potvrda) {
        setPoruka('')
        setInfo(`Email je promenjen. Link za potvrdu je poslat na ${novi.email}; do potvrde je stranica Obaveštenja zaključana.`)
        setPodaci(Object.fromEntries(polja.map((p) => [p.name, ''])))
        return
      }
      navigate('/portfolio')
    } catch (err) {
      setPoruka(err.message)
    }
  }

  return (
    <div className="page-light">
      <Navbar />
      <div className="form">
        <form onSubmit={submit}>
          <h1>Izmena profila</h1>
          {dopuni ? (
            <div className="info-box">
              Nalog je napravljen preko Google-a. Dopunite adresu, grad, državu i telefon.
              Lozinku možete postaviti ako želite da se prijavljujete i bez Google-a.
            </div>
          ) : (
            <p>(Popunite polja koja zelite da izmenite!)</p>
          )}
          {polja.map(({ name, placeholder, type = 'text' }) => (
            <input key={name} className="input" type={type} placeholder={placeholder}
              value={podaci[name]} onChange={(e) => setPodaci({ ...podaci, [name]: e.target.value })} />
          ))}
          {poruka && <div className="msg-error">{poruka}</div>}
          {info && <div className="info-box">{info}</div>}
          <button className="button" type="submit">Izmeni nalog</button>
        </form>
      </div>
    </div>
  )
}
