import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

const token = localStorage.getItem('token')
if (token) api.defaults.headers.common['Authorization'] = `Bearer ${token}`

api.interceptors.response.use(
  res => res,
  err => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      delete api.defaults.headers.common['Authorization']
      window.location.href = '/admin/login'
    }
    return Promise.reject(err)
  }
)

export default api
