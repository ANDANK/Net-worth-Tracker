import { useState, useEffect } from 'react'
import { authApi } from '../services/api'

export function useAuth() {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null)

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (!token) {
      setIsAuthenticated(false)
      return
    }
    authApi.verify()
      .then(() => setIsAuthenticated(true))
      .catch(() => {
        localStorage.removeItem('token')
        setIsAuthenticated(false)
      })
  }, [])

  const login = async (password: string): Promise<boolean> => {
    try {
      const { data } = await authApi.login(password)
      localStorage.setItem('token', data.access_token)
      setIsAuthenticated(true)
      return true
    } catch {
      return false
    }
  }

  const logout = () => {
    localStorage.removeItem('token')
    setIsAuthenticated(false)
  }

  return { isAuthenticated, login, logout }
}
