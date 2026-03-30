import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'
import api, { extractError } from '../api/axiosInstance'

// ── Thunks ────────────────────────────────────────────────────────────────────

export const fetchJobs = createAsyncThunk(
  'jobs/fetchAll',
  async (source = null, { rejectWithValue }) => {
    try {
      const params = source ? { source } : {}
      const res = await api.get('/jobs/', { params })
      return res.data
    } catch (err) {
      return rejectWithValue(extractError(err))
    }
  }
)

export const triggerScrape = createAsyncThunk(
  'jobs/triggerScrape',
  async (_, { rejectWithValue }) => {
    try {
      const res = await api.post('/jobs/scrape')
      return res.data.message
    } catch (err) {
      return rejectWithValue(extractError(err))
    }
  }
)

export const clearJobs = createAsyncThunk(
  'jobs/clear',
  async (_, { rejectWithValue }) => {
    try {
      await api.delete('/jobs/')
    } catch (err) {
      return rejectWithValue(extractError(err))
    }
  }
)

// ── Slice ───────────────────────────────────────────────────────────────────

const jobsSlice = createSlice({
  name: 'jobs',
  initialState: {
    items: [],          // all jobs returned from backend
    loading: false,
    scraping: false,    // true while POST /jobs/scrape is in-flight
    error: null,
    scrapeMsg: null,
  },
  reducers: {
    clearScrapeMsg(state) { state.scrapeMsg = null },
    clearError(state)     { state.error = null },
  },
  extraReducers: (builder) => {
    // fetchJobs
    builder
      .addCase(fetchJobs.pending,  (s) => { s.loading = true; s.error = null })
      .addCase(fetchJobs.fulfilled,(s, a) => { s.loading = false; s.items = a.payload })
      .addCase(fetchJobs.rejected, (s, a) => { s.loading = false; s.error = a.payload })

    // triggerScrape
    builder
      .addCase(triggerScrape.pending,  (s) => { s.scraping = true; s.scrapeMsg = null; s.error = null })
      .addCase(triggerScrape.fulfilled,(s, a) => { s.scraping = false; s.scrapeMsg = a.payload })
      .addCase(triggerScrape.rejected, (s, a) => { s.scraping = false; s.error = a.payload })

    // clearJobs
    builder
      .addCase(clearJobs.fulfilled, (s) => { s.items = [] })
  },
})

export const { clearScrapeMsg, clearError: clearJobsError } = jobsSlice.actions
export default jobsSlice.reducer
