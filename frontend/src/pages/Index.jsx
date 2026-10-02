import { Link } from 'react-router-dom'

export default function Index() {
  return (
    <div className="landing">
      <div className="header">
        <ul>
          <li><Link to="/auth/register">Registracija</Link></li>
          <li><Link to="/auth/login">Uloguj se</Link></li>
        </ul>
      </div>
      <div className="title">
        <h1>Crypto Portfolio</h1>
      </div>
    </div>
  )
}
