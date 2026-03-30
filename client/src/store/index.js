import { configureStore } from '@reduxjs/toolkit'
import authReducer from './authSlice'
import jobsReducer from './jobsSlice'

export const store = configureStore({
  reducer: {
    auth: authReducer,
    jobs: jobsReducer,
  },
  devTools: import.meta.env.DEV,
})
