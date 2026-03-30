import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000',
  // Do NOT set Content-Type here — axios sets it automatically:
  //   application/json  for plain objects
  //   multipart/form-data (with boundary) for FormData
})

// Attach JWT token to every request if present
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// On 401 – clear auth state so user is redirected to login
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

// FastAPI returns validation errors as an array of {msg, loc} objects.
// Flatten them into a single readable string.
export const extractError = (err, fallback = 'Something went wrong.') => {
  const detail = err.response?.data?.detail
  if (!detail) return fallback
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return detail.map(d => d.msg).join(', ')
  return fallback
}

export default api
