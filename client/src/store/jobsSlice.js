import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'
import api, { extractError } from '../api/axiosInstance'

// ── Thunks ────────────────────────────────────────────────────────────────────

export const fetchJobs = createAsyncThunk(
  'jobs/fetchAll',
  async (source = null, { rejectWithValue }) => {
    try {
      const params = source ? { source, limit: 500 } : { limit: 500 }
      const res = await api.get('/jobs/', { params })
      return res.data
    } catch (err) {
      return rejectWithValue(extractError(err))
    }
  }
)

export const triggerScrape = createAsyncThunk(
  'jobs/triggerScrape',
  async (_, { rejectWithValue, dispatch }) => {
    try {
      const res = await api.post('/jobs/scrape')
      dispatch(fetchJobs())
      return res.data.message
    } catch (err) {
      return rejectWithValue(extractError(err))
    }
  }
)

export const clearJobs = createAsyncThunk(
  'jobs/clear',
  async (_, { rejectWithValue, dispatch }) => {
    try {
      await api.delete('/jobs/')
      dispatch(fetchJobs())
    } catch (err) {
      return rejectWithValue(extractError(err))
    }
  }
)

export const cancelAutoApply = createAsyncThunk(
  'jobs/cancelAutoApply',
  async (_, { rejectWithValue }) => {
    try {
      const res = await api.post('/jobs/auto-apply/cancel')
      return res.data.message
    } catch (err) {
      return rejectWithValue(extractError(err))
    }
  }
)

// Auto‑apply thunk
export const autoApply = createAsyncThunk(
  'jobs/autoApply',
  async (max_applies = 5, { rejectWithValue, dispatch }) => {
    try {
      const res = await api.post(`/jobs/auto-apply?max_applies=${max_applies}`)
      // Refresh jobs to update applied flags
      dispatch(fetchJobs())
      return res.data
    } catch (err) {
      return rejectWithValue(extractError(err))
    }
  }
)

// ── Slice ───────────────────────────────────────────────────────────────────

const jobsSlice = createSlice({
  name: 'jobs',
  initialState: {
    items: [],  
    rankedItems: [],
  rankingLoaded: false,        // jobs array
    total: 0,
    skip: 0,
    limit: 500,
    user_skills: [],
    loading: false,
    scraping: false,    // true while POST /jobs/scrape is in-flight
    autoApplying: false, // true while auto‑apply is running
    cancelling: false,   // true while cancelling
    error: null,
    scrapeMsg: null,
    autoApplyMsg: null,
  },
  reducers: {
    clearScrapeMsg(state) { state.scrapeMsg = null },
    clearAutoApplyMsg(state) { state.autoApplyMsg = null },
    clearError(state) { state.error = null },
    clearRankedJobs(state) {
    state.rankedItems = []
    state.rankingLoaded = false
  },
  },
  extraReducers: (builder) => {
    // fetchJobs
    builder
      .addCase(fetchJobs.pending, (s) => { s.loading = true; s.error = null })
      .addCase(fetchJobs.fulfilled, (s, a) => {
        s.loading = false
        s.items = a.payload.jobs || []
        s.rankedItems = a.payload.jobs || []
s.rankingLoaded = true
        s.total = a.payload.total || 0
        s.skip = a.payload.skip || 0
        s.limit = a.payload.limit || 20
        s.user_skills = a.payload.user_skills || []
      })
      .addCase(fetchJobs.rejected, (s, a) => { s.loading = false; s.error = a.payload })

    // triggerScrape
    builder
      .addCase(triggerScrape.pending, (s) => { s.scraping = true; s.scrapeMsg = null; s.error = null })
      .addCase(triggerScrape.fulfilled, (s, a) => { s.scraping = false; s.scrapeMsg = a.payload })
      .addCase(triggerScrape.rejected, (s, a) => { s.scraping = false; s.error = a.payload })

    // clearJobs (no direct state change because fetchJobs will be dispatched)

    // autoApply
    builder
      .addCase(autoApply.pending, (s) => { 
        s.autoApplying = true; 
        s.autoApplyMsg = null; 
        s.error = null; 
        s.cancelling = false 
      })
      .addCase(autoApply.fulfilled, (s, a) => {
        s.autoApplying = false
        s.autoApplyMsg = a.payload.message || 'Auto-apply completed'
      })
      .addCase(autoApply.rejected, (s, a) => { 
        s.autoApplying = false; 
        s.error = a.payload 
      })

    // cancelAutoApply
    builder
      .addCase(cancelAutoApply.pending, (s) => { 
        s.cancelling = true; 
        s.error = null 
      })
      .addCase(cancelAutoApply.fulfilled, (s, a) => {
        s.cancelling = false
        s.autoApplying = false  // ensure the button state resets
        s.autoApplyMsg = a.payload
      })
      .addCase(cancelAutoApply.rejected, (s, a) => { 
        s.cancelling = false; 
        s.error = a.payload 
      })
  },
})

export const { clearScrapeMsg, clearAutoApplyMsg, clearError: clearJobsError,clearRankedJobs } = jobsSlice.actions
export default jobsSlice.reducer