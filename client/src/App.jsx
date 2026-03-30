import { useEffect, useRef } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useDispatch } from 'react-redux'
import Signup from './pages/Signup'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Support from './pages/Support'
import About from './pages/About'
import Profile from './pages/Profile'
import Jobs from './pages/Jobs'
import ProtectedRoute from './components/ProtectedRoute'
import { useAuth } from './store/hooks'
import { triggerScrape } from './store/jobsSlice'
import './index.css'

/**
 * Restarts the background scraping loop whenever the user becomes authenticated
 * (login, signup, or page refresh with a stored token).
 */
function AuthScraper() {
  const dispatch = useDispatch()
  const { user } = useAuth()
  const prevUser = useRef(null)

  useEffect(() => {
    if (user && !prevUser.current) {
      dispatch(triggerScrape())
    }
    prevUser.current = user
  }, [user, dispatch])

  return null
}

function App() {
  return (
    <BrowserRouter>
      <AuthScraper />
      <Routes>
        <Route path="/login"      element={<Login />} />
        <Route path="/signup"     element={<Signup />} />
        <Route path="/dashboard"  element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
        <Route path="/support"    element={<Support />} />
        <Route path="/about"      element={<About />} />
        <Route path="/profile"    element={<ProtectedRoute><Profile /></ProtectedRoute>} />
        <Route path="/jobs"       element={<ProtectedRoute><Jobs /></ProtectedRoute>} />
        <Route path="*"           element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
