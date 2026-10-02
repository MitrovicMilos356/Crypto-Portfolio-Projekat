import { createContext, useContext, useEffect, useState } from 'react'
import { api } from './api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  // undefined = jos proveravamo, null = nije ulogovan
  const [user, setUser] = useState(undefined)

  useEffect(() => {
    api('/me')
      .then(setUser)
      .catch(() => setUser(null))
  }, [])

  const login = async (email, lozinka) => setUser(await api('/auth/login', { method: 'POST', body: { email, lozinka } }))
  const register = async (podaci) => setUser(await api('/auth/register', { method: 'POST', body: podaci }))
  const logout = async () => {
    await api('/auth/logout', { method: 'POST' })
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, setUser, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
