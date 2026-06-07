import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useDispatch, useSelector } from 'react-redux'
import { fetchJobs, triggerScrape, clearJobs, clearScrapeMsg, autoApply, clearAutoApplyMsg, cancelAutoApply } from '../store/jobsSlice'
import { logoutUser } from '../store/authSlice'
import { useAuth } from '../store/hooks'
import api from '../api/axiosInstance'
import {
  Zap, ArrowLeft, User, LogOut, Building2, MapPin, DollarSign,
  ExternalLink, Bot, RefreshCw, Loader2, CheckCircle, AlertTriangle,
  Search, Briefcase, Layers, Trash2, X,
} from 'lucide-react'

const SOURCES = [
  { key: 'all', label: 'All Jobs', Icon: Layers },
  { key: 'naukri', label: 'Naukri', Icon: Briefcase },
  { key: 'indeed', label: 'Indeed', Icon: Search },
  { key: 'internshala', label: 'Internshala', Icon: Bot },
]

const SOURCE_STYLES = {
  naukri:     'bg-[#f59e0b]/10 border-[#f59e0b]/30 text-[#d97706]',
  internshala:'bg-[#3b82f6]/10 border-[#3b82f6]/30 text-[#2563eb]',
  indeed:     'bg-[#10B981]/10 border-[#10B981]/30 text-[#059669]',
}

function JobCard({ job }) {
  const sourceCls = SOURCE_STYLES[job.source] || SOURCE_STYLES.indeed

  return (
    <div className="bg-white border border-[#e2e2ed] rounded-2xl p-5 flex flex-col gap-3 hover:border-[#10B981]/50 hover:-translate-y-0.5 hover:shadow-[0_4px_24px_rgba(16,185,129,0.08)] transition-all duration-200 shadow-sm">
      <div className="flex items-start justify-between gap-2">
        <h3 className="text-base text-[#0f0f1a] leading-snug flex-1" style={{ fontFamily: 'EuclidSB, sans-serif' }}>
          {job.title}
        </h3>
        <span className={`shrink-0 text-xs px-2 py-0.5 rounded-full border capitalize ${sourceCls}`}
          style={{ fontFamily: 'EuclidSB, sans-serif' }}>
          {job.source}
        </span>
      </div>

      <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-[#6b6b80]">
        {job.company && <span className="flex items-center gap-1.5"><Building2 size={13} strokeWidth={1.75} className="text-[#a0a0b0]" />{job.company}</span>}
        {job.location && <span className="flex items-center gap-1.5"><MapPin size={13} strokeWidth={1.75} className="text-[#a0a0b0]" />{job.location}</span>}
        {job.salary && <span className="flex items-center gap-1.5"><DollarSign size={13} strokeWidth={1.75} className="text-[#a0a0b0]" />{job.salary}</span>}
      </div>

      {job.skill_query && (
        <span className="self-start text-xs px-2.5 py-0.5 rounded-full bg-[#10B981]/10 border border-[#10B981]/25 text-[#059669]"
          style={{ fontFamily: 'EuclidSB, sans-serif' }}>
          {job.skill_query}
        </span>
      )}

      {job.description && (
        <p className="text-xs text-[#a0a0b0] line-clamp-2">{job.description}</p>
      )}

      {job.applied && (
        <span className="self-start text-xs px-2.5 py-0.5 rounded-full bg-green-100 border border-green-300 text-green-700">
          Applied
        </span>
      )}

      {job.url ? (
        <a href={job.url} target="_blank" rel="noreferrer"
          className="self-start mt-auto flex items-center gap-1.5 px-4 py-2 rounded-lg bg-[#10B981]/[0.08] border border-[#10B981]/30 text-xs text-[#059669] hover:bg-[#10B981]/[0.15] transition-colors"
          style={{ fontFamily: 'EuclidSB, sans-serif' }}>
          View Job <ExternalLink size={11} strokeWidth={2} />
        </a>
      ) : (
        <span className="self-start mt-auto px-4 py-2 rounded-lg bg-[#f5f5fa] border border-[#e2e2ed] text-xs text-[#a0a0b0]">
          No link available
        </span>
      )}
    </div>
  )
}

function EmptyState({ scraping, onScrape }) {
  return (
    <div className="flex flex-col items-center gap-6 py-24 text-center">
      <div className="w-20 h-20 rounded-2xl bg-[#10B981]/10 border border-[#10B981]/20 flex items-center justify-center">
        <Bot size={36} className="text-[#10B981]" strokeWidth={1.5} />
      </div>
      <div>
        <h3 className="text-xl text-[#0f0f1a] mb-2" style={{ fontFamily: 'EuclidB, sans-serif' }}>
          No jobs scraped yet
        </h3>
        <p className="text-sm text-[#6b6b80] max-w-sm">
          Click the button below to search Indeed and Naukri for jobs matching your skills.
        </p>
      </div>
      <button onClick={onScrape} disabled={scraping}
        className="flex items-center gap-2 px-6 py-3 bg-[#10B981] text-white rounded-xl shadow-[0_4px_18px_rgba(16,185,129,0.25)] hover:bg-[#0ea572] hover:-translate-y-0.5 transition-all duration-200 disabled:opacity-60 disabled:cursor-not-allowed disabled:transform-none text-sm"
        style={{ fontFamily: 'EuclidSB, sans-serif' }}>
        {scraping
          ? <><Loader2 size={15} className="animate-spin" /> Scraping…</>
          : <><Search size={15} strokeWidth={2} /> Scrape Jobs Now</>
        }
      </button>
    </div>
  )
}

export default function Jobs() {
  const dispatch = useDispatch()
  const navigate = useNavigate()
  const { user } = useAuth()
  const { items, loading, scraping, error, scrapeMsg, autoApplying, autoApplyMsg, cancelling } = useSelector(s => s.jobs)

  const [activeSource, setActiveSource] = useState('all')
  const [pollCount, setPollCount] = useState(0)
  const [checkingCreds, setCheckingCreds] = useState(false)

  useEffect(() => { dispatch(fetchJobs()) }, [dispatch])

  useEffect(() => {
    if (!scrapeMsg || pollCount >= 10) return
    const t = setTimeout(() => {
      dispatch(fetchJobs())
      setPollCount(c => c + 1)
    }, 4000)
    return () => clearTimeout(t)
  }, [scrapeMsg, pollCount, dispatch])

  const handleScrape = async () => {
    setPollCount(0)
    dispatch(clearScrapeMsg())
    await dispatch(triggerScrape())
    dispatch(fetchJobs())
  }

  const checkAndAutoApply = async () => {
    setCheckingCreds(true)
    try {
      const res = await api.get('/credentials/naukri')
      if (res.data.exists) {
        dispatch(clearAutoApplyMsg())
        dispatch(autoApply(5))
      } else {
        navigate('/profile')
      }
    } catch (err) {
      console.error('Failed to check credentials', err)
      navigate('/profile')
    } finally {
      setCheckingCreds(false)
    }
  }

  const handleCancelAutoApply = () => {
    dispatch(cancelAutoApply())
  }

  const handleLogout = async () => {
    await dispatch(logoutUser())
    navigate('/login')
  }

  const unappliedNaukriCount = items.filter(job => !job.applied && job.source === 'naukri').length

  const displayed = activeSource === 'all' ? items : items.filter(j => j.source === activeSource)
  const counts = {
    all: items.length,
    naukri: items.filter(j => j.source === 'naukri').length,
    indeed: items.filter(j => j.source === 'indeed').length,
    internshala: items.filter(j => j.source === 'internshala').length,
  }

  return (
    <div className="min-h-screen bg-[#f5f5fa]" style={{ fontFamily: 'EuclidR, sans-serif' }}>

      <header className="sticky top-0 z-50 border-b border-[#e2e2ed] bg-white/90 backdrop-blur-md shadow-sm">
        <div className="max-w-7xl mx-auto px-6 flex items-center justify-between h-16">
          <Link to="/dashboard" className="flex items-center gap-2">
            <span className="text-xl text-[#0f0f1a]" style={{ fontFamily: 'EuclidB, sans-serif' }}>
              Career<span className="text-[#10B981]">Sync</span>
            </span>
          </Link>
          <div className="flex items-center gap-3">
            <Link to="/dashboard"
              className="flex items-center gap-1.5 text-sm text-[#6b6b80] hover:text-[#0f0f1a] transition-colors">
              <ArrowLeft size={15} strokeWidth={2} /> Dashboard
            </Link>
            <Link to="/profile"
              className="flex items-center gap-1.5 text-sm text-[#6b6b80] hover:text-[#0f0f1a] transition-colors">
              <User size={15} strokeWidth={1.75} /> Profile
            </Link>
            <button onClick={handleLogout}
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm text-[#6b6b80] hover:text-[#ef4444] hover:bg-[#ef4444]/[0.06] border border-transparent hover:border-[#ef4444]/20 transition-all duration-200">
              <LogOut size={15} /> Log out
            </button>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-10">

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
          <div>
            <h1 className="text-3xl text-[#0f0f1a]" style={{ fontFamily: 'EuclidB, sans-serif' }}>
              Job Matches
            </h1>
            <p className="text-sm text-[#6b6b80] mt-1 flex flex-wrap items-center gap-1">
              Based on your skills:
              {(user?.skills ?? []).length > 0
                ? user.skills.slice(0, 5).map(s => (
                  <span key={s}
                    className="inline-block px-2 py-0.5 bg-[#10B981]/10 border border-[#10B981]/25 rounded-full text-xs text-[#059669]"
                    style={{ fontFamily: 'EuclidSB, sans-serif' }}>
                    {s}
                  </span>
                ))
                : <span className="text-[#a0a0b0]">no skills set — add them in your profile</span>
              }
            </p>
          </div>

          <div className="flex items-center gap-3">
            {items.length > 0 && (
              <button onClick={() => { dispatch(clearJobs()); setActiveSource('all') }}
                className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs text-[#6b6b80] border border-[#e2e2ed] hover:text-[#ef4444] hover:border-[#ef4444]/40 transition-all duration-200 bg-white shadow-sm"
                style={{ fontFamily: 'EuclidSB, sans-serif' }}>
                <Trash2 size={13} strokeWidth={2} /> Clear all
              </button>
            )}
            <button onClick={handleScrape} disabled={scraping || loading}
              className="flex items-center gap-2 px-5 py-2.5 bg-[#10B981] text-white rounded-xl shadow-[0_4px_18px_rgba(16,185,129,0.25)] hover:bg-[#0ea572] hover:-translate-y-0.5 transition-all duration-200 disabled:opacity-60 disabled:cursor-not-allowed disabled:transform-none text-sm"
              style={{ fontFamily: 'EuclidSB, sans-serif' }}>
              {scraping
                ? <><Loader2 size={15} className="animate-spin" /> Scraping…</>
                : <><RefreshCw size={15} strokeWidth={2} /> Re-scrape</>
              }
            </button>
          </div>
        </div>

        {/* Auto Apply / Cancel Button */}
        {items.length > 0 && unappliedNaukriCount > 0 && (
          <div className="mb-4 flex items-center gap-3">
            {!autoApplying ? (
              <button onClick={checkAndAutoApply} disabled={autoApplying || checkingCreds}
                className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition-all disabled:opacity-60 text-sm"
                style={{ fontFamily: 'EuclidSB, sans-serif' }}>
                {(checkingCreds)
                  ? <><Loader2 size={15} className="animate-spin" /> Checking...</>
                  : <><Zap size={15} strokeWidth={2} /> Auto Apply ({unappliedNaukriCount})</>
                }
              </button>
            ) : (
              <button onClick={handleCancelAutoApply} disabled={cancelling}
                className="flex items-center gap-2 px-5 py-2.5 bg-red-600 text-white rounded-xl hover:bg-red-700 transition-all disabled:opacity-60 text-sm"
                style={{ fontFamily: 'EuclidSB, sans-serif' }}>
                {cancelling
                  ? <><Loader2 size={15} className="animate-spin" /> Cancelling...</>
                  : <><X size={15} strokeWidth={2} /> Cancel Auto-Apply</>
                }
              </button>
            )}
            {autoApplyMsg && (
              <div className="flex items-center gap-2 text-sm text-[#059669]">
                <CheckCircle size={15} strokeWidth={2} />
                {autoApplyMsg}
              </div>
            )}
          </div>
        )}

        {scrapeMsg && (
          <div className="mb-6 px-4 py-3 bg-[#10B981]/[0.08] border border-[#10B981]/30 rounded-xl text-sm text-[#059669] flex items-center gap-2">
            <CheckCircle size={15} strokeWidth={2} className="flex-shrink-0" />
            {scrapeMsg}
            {pollCount < 10 && (
              <span className="text-xs text-[#a0a0b0] ml-1">Auto-refreshing results…</span>
            )}
          </div>
        )}
        {error && (
          <div className="mb-6 px-4 py-3 bg-[#ef4444]/[0.07] border border-[#ef4444]/30 rounded-xl text-sm text-[#ef4444] flex items-center gap-2">
            <AlertTriangle size={15} strokeWidth={2} className="flex-shrink-0" /> {error}
          </div>
        )}

        {items.length > 0 && (
          <div className="flex gap-2 mb-6 flex-wrap">
            {SOURCES.map(({ key, label, Icon }) => (
              <button key={key} onClick={() => setActiveSource(key)}
                className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm border transition-all duration-200
                  ${activeSource === key
                    ? 'bg-[#10B981]/[0.08] border-[#10B981] text-[#059669] shadow-[0_0_12px_rgba(16,185,129,0.12)]'
                    : 'bg-white border-[#e2e2ed] text-[#6b6b80] hover:border-[#10B981]/40 hover:text-[#0f0f1a]'
                  }`}
                style={{ fontFamily: 'EuclidSB, sans-serif' }}>
                <Icon size={14} strokeWidth={1.75} />
                {label}
                <span className={`text-xs px-1.5 py-0.5 rounded-full ${activeSource === key ? 'bg-[#10B981]/20 text-[#059669]' : 'bg-[#f5f5fa] text-[#a0a0b0]'}`}>
                  {counts[key]}
                </span>
              </button>
            ))}
          </div>
        )}

        {loading && items.length === 0 ? (
          <div className="flex justify-center py-32">
            <div className="w-10 h-10 rounded-full border-2 border-[#10B981] border-t-transparent animate-spin" />
          </div>
        ) : items.length === 0 ? (
          <EmptyState scraping={scraping} onScrape={handleScrape} />
        ) : displayed.length === 0 ? (
          <div className="flex flex-col items-center gap-4 py-20 text-center">
            <div className="w-14 h-14 rounded-2xl bg-[#f5f5fa] border border-[#e2e2ed] flex items-center justify-center">
              <Search size={24} className="text-[#a0a0b0]" strokeWidth={1.5} />
            </div>
            <p className="text-[#6b6b80] text-sm">
              No jobs from <span className="text-[#0f0f1a] capitalize" style={{ fontFamily: 'EuclidSB, sans-serif' }}>{activeSource}</span> yet.
            </p>
          </div>
        ) : (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {displayed.map(job => <JobCard key={job.id} job={job} />)}
          </div>
        )}
      </div>
    </div>
  )
}