import { Outlet } from 'react-router-dom'
import ProtectedRoute from './ProtectedRoute'
import Navbar from './NavBar'

export default function ProtectedLayout() {
  return (
    <ProtectedRoute>
      <Navbar />

      <main>
        <Outlet />
      </main>
    </ProtectedRoute>
  )
}