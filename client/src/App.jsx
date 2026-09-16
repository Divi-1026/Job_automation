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
import Applications from './pages/Applications'

import ProtectedLayout from './components/ProtectedLayout'

import { useAuth } from './store/hooks'
import { triggerScrape } from './store/jobsSlice'

import './index.css'


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

        {/* PUBLIC ROUTES */}
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />
        <Route path="/support" element={<Support />} />

        {/* PROTECTED ROUTES WITH SINGLE NAVBAR */}
        <Route element={<ProtectedLayout />}>

          <Route
            path="/dashboard"
            element={<Dashboard />}
          />

          <Route
            path="/about"
            element={<About />}
          />

          <Route
            path="/profile"
            element={<Profile />}
          />

          <Route
            path="/jobs"
            element={<Jobs />}
          />

          <Route
            path="/applications"
            element={<Applications />}
          />

        </Route>


        {/* FALLBACK */}
        <Route
          path="*"
          element={<Navigate to="/login" replace />}
        />

      </Routes>

    </BrowserRouter>
  )
}

export default App