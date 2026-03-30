import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'
import api, { extractError } from '../api/axiosInstance'

// ─── Helpers ────────────────────────────────────────────────────────────────
const persistAuth = (token, user) => {
  localStorage.setItem('token', token)
  localStorage.setItem('user', JSON.stringify(user))
}

const clearAuth = () => {
  localStorage.removeItem('token')
  localStorage.removeItem('user')
}

// ─── Thunks ─────────────────────────────────────────────────────────────────
export const signupUser = createAsyncThunk(
  'auth/signup',
  async (formData, { rejectWithValue }) => {
    try {
      const { data } = await api.post('/auth/signup', formData)
      persistAuth(data.access_token, data.user)
      return data
    } catch (err) {
      return rejectWithValue(
        extractError(err, 'Signup failed. Please try again.')
      )
    }
  }
)

export const loginUser = createAsyncThunk(
  'auth/login',
  async ({ email, password }, { rejectWithValue }) => {
    try {
      const { data } = await api.post('/auth/login', { email, password })
      persistAuth(data.access_token, data.user)
      return data
    } catch (err) {
      return rejectWithValue(
        extractError(err, 'Invalid email or password.')
      )
    }
  }
)

export const fetchMe = createAsyncThunk(
  'auth/fetchMe',
  async (_, { rejectWithValue }) => {
    try {
      const { data } = await api.get('/users/me')
      return data
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Session expired.')
    }
  }
)

export const updateProfile = createAsyncThunk(
  'auth/updateProfile',
  async (fields, { rejectWithValue }) => {
    try {
      const { data } = await api.patch('/profile/me', fields)
      localStorage.setItem('user', JSON.stringify(data))
      return data
    } catch (err) {
      return rejectWithValue(extractError(err, 'Profile update failed.'))
    }
  }
)

export const changePassword = createAsyncThunk(
  'auth/changePassword',
  async ({ current_password, new_password }, { rejectWithValue }) => {
    try {
      const { data } = await api.post('/profile/me/password', { current_password, new_password })
      return data
    } catch (err) {
      return rejectWithValue(extractError(err, 'Password change failed.'))
    }
  }
)

export const uploadResume = createAsyncThunk(
  'auth/uploadResume',
  async (file, { rejectWithValue }) => {
    try {
      const fd = new FormData()
      fd.append('file', file)
      const { data } = await api.post('/profile/me/resume', fd)
      localStorage.setItem('user', JSON.stringify(data))
      return data
    } catch (err) {
      return rejectWithValue(extractError(err, 'Resume upload failed.'))
    }
  }
)

export const deleteResume = createAsyncThunk(
  'auth/deleteResume',
  async (_, { rejectWithValue }) => {
    try {
      const { data } = await api.delete('/profile/me/resume')
      localStorage.setItem('user', JSON.stringify(data))
      return data
    } catch (err) {
      return rejectWithValue(extractError(err, 'Resume removal failed.'))
    }
  }
)

export const logoutUser = createAsyncThunk(
  'auth/logout',
  async (_, { dispatch }) => {
    try {
      await api.post('/auth/logout')
    } catch (_) {
      // Always clear local session even if API call fails
    }
    dispatch(authSlice.actions.logout())
  }
)

// ─── Slice ───────────────────────────────────────────────────────────────────
const storedUser = (() => {
  try { return JSON.parse(localStorage.getItem('user')) } catch { return null }
})()

const authSlice = createSlice({
  name: 'auth',
  initialState: {
    user: storedUser || null,
    token: localStorage.getItem('token') || null,
    loading: false,
    error: null,
  },
  reducers: {
    logout(state) {
      state.user = null
      state.token = null
      state.error = null
      clearAuth()
    },
    clearError(state) {
      state.error = null
    },
  },
  extraReducers: (builder) => {
    const pending  = (state) => { state.loading = true;  state.error = null }
    const rejected = (state, action) => { state.loading = false; state.error = action.payload }

    builder
      // signup
      .addCase(signupUser.pending, pending)
      .addCase(signupUser.fulfilled, (state, action) => {
        state.loading = false
        state.token   = action.payload.access_token
        state.user    = action.payload.user
      })
      .addCase(signupUser.rejected, rejected)
      // login
      .addCase(loginUser.pending, pending)
      .addCase(loginUser.fulfilled, (state, action) => {
        state.loading = false
        state.token   = action.payload.access_token
        state.user    = action.payload.user
      })
      .addCase(loginUser.rejected, rejected)
      // fetchMe
      .addCase(fetchMe.pending, pending)
      .addCase(fetchMe.fulfilled, (state, action) => {
        state.loading = false
        state.user    = action.payload
      })
      .addCase(fetchMe.rejected, (state) => {
        state.loading = false
        state.user    = null
        state.token   = null
        clearAuth()
      })
      // updateProfile
      .addCase(updateProfile.pending, pending)
      .addCase(updateProfile.fulfilled, (state, action) => {
        state.loading = false
        state.user    = action.payload
      })
      .addCase(updateProfile.rejected, rejected)
      // changePassword
      .addCase(changePassword.pending, pending)
      .addCase(changePassword.fulfilled, (state) => { state.loading = false })
      .addCase(changePassword.rejected, rejected)
      // uploadResume
      .addCase(uploadResume.pending, pending)
      .addCase(uploadResume.fulfilled, (state, action) => {
        state.loading = false
        state.user    = action.payload
      })
      .addCase(uploadResume.rejected, rejected)
      // deleteResume
      .addCase(deleteResume.pending, pending)
      .addCase(deleteResume.fulfilled, (state, action) => {
        state.loading = false
        state.user    = action.payload
      })
      .addCase(deleteResume.rejected, rejected)
  },
})

export const { logout, clearError } = authSlice.actions
export default authSlice.reducer
