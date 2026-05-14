import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  },
)

export default api

export const authApi = {
  login: (password: string) =>
    api.post<{ access_token: string }>('/auth/login', { password }),
  verify: () => api.get('/auth/verify'),
}

export const accountsApi = {
  list: () => api.get('/accounts/'),
  create: (data: object) => api.post('/accounts/', data),
  deactivate: (id: string) => api.delete(`/accounts/${id}`),
}

export const transactionsApi = {
  list: (params?: object) => api.get('/transactions/', { params }),
  preview: (formData: FormData) => api.post('/transactions/preview', formData),
  import: (formData: FormData) => api.post('/transactions/import', formData),
  diagnose: (formData: FormData) => api.post('/transactions/diagnose', formData),
}

export const manualApi = {
  list: (owner?: string) => api.get('/manual/', { params: owner ? { owner } : {} }),
  add: (data: object) => api.post('/manual/', data),
  latest: () => api.get('/manual/latest'),
}

export const networthApi = {
  dashboard: () => api.get('/networth/dashboard'),
  history: (period: string) => api.get('/networth/history', { params: { period } }),
  snapshot: (params: object) => api.post('/networth/snapshot', null, { params }),
}

export const projectionsApi = {
  run: (scenario: object) => api.post('/projections/run', scenario),
  save: (scenario: object) => api.post('/projections/save', scenario),
  saved: () => api.get('/projections/saved'),
}

export const brokersApi = {
  list: (includeInactive = false) =>
    api.get('/brokers/', { params: includeInactive ? { include_inactive: true } : {} }),
  add: (data: { broker_id: string; broker_name: string }) =>
    api.post('/brokers/', data),
  toggle: (brokerId: string, active: boolean) =>
    api.patch(`/brokers/${brokerId}`, { active }),
}

export const pnlApi = {
  get: (params: { account_id?: string; period?: string; ticker?: string }) =>
    api.get('/pnl/', { params }),
  validate: (account_id?: string) =>
    api.get('/pnl/validate', { params: account_id ? { account_id } : {} }),
}
