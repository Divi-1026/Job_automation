import { useDispatch, useSelector } from 'react-redux'

export const useAppDispatch = () => useDispatch()
export const useAppSelector = (selector) => useSelector(selector)

// Convenience auth selector
export const useAuth = () => useAppSelector((state) => state.auth)
