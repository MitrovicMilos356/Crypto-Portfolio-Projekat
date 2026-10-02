import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './auth'
import Index from './pages/Index'
import Login from './pages/Login'
import Register from './pages/Register'
import Portfolio from './pages/Portfolio'
import Store from './pages/Store'
import ModifyProfile from './pages/ModifyProfile'
import Alerts from './pages/Alerts'

// Samo za ulogovane korisnike
function Private({ children }) {
  const { user } = useAuth()
  if (user === undefined) return null
  return user ? children : <Navigate to="/auth/login" replace />
}

// Samo za goste (ulogovani idu na portfolio)
function Guest({ children }) {
  const { user } = useAuth()
  if (user === undefined) return null
  return user ? <Navigate to="/portfolio" replace /> : children
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Guest><Index /></Guest>} />
      <Route path="/auth/login" element={<Guest><Login /></Guest>} />
      <Route path="/auth/register" element={<Guest><Register /></Guest>} />
      <Route path="/portfolio" element={<Private><Portfolio /></Private>} />
      <Route path="/store" element={<Private><Store /></Private>} />
      <Route path="/alerts" element={<Private><Alerts /></Private>} />
      <Route path="/modifyProfile" element={<Private><ModifyProfile /></Private>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
