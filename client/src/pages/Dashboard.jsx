import { useNavigate, Link } from 'react-router-dom'
import { useAppDispatch, useAuth } from '../store/hooks'
import { logoutUser } from '../store/authSlice'
import {
  Search,
  Bot,
  Zap,
  BarChart2,
  FileText,
  Bell,
  Settings,
  Sparkles,
  MousePointerClick,
  TrendingUp,
  Puzzle,
  LogOut,
  User,
  Briefcase,
  Download,
  Globe,
  ChevronRight,
  CheckCircle2,
} from 'lucide-react'

const FEATURES = [
  {
    Icon: Search,
    title: 'Smart Job Scraping',
    desc: 'Pulls fresh listings from Naukri, Internshala, LinkedIn and more — updated daily.',
  },
  {
    Icon: Bot,
    title: 'AI Match Scoring',
    desc: 'Our model reads your resume and ranks every job by how well it fits your profile.',
  },
  {
    Icon: Zap,
    title: 'One-Click Apply',
    desc: 'Auto-fills forms and submits applications in seconds, not hours.',
  },
  {
    Icon: BarChart2,
    title: 'Application Tracker',
    desc: "See every application you've sent, its status, and follow-up reminders.",
  },
  {
    Icon: FileText,
    title: 'Resume Tailoring',
    desc: 'AI rewrites your resume summary to match each job description automatically.',
  },
  {
    Icon: Bell,
    title: 'Instant Alerts',
    desc: 'Get notified the moment a job matching your skills goes live.',
  },
]

const HOW_IT_WORKS = [
  {
    step: '01',
    Icon: Settings,
    title: 'Set your preferences',
    desc: 'Tell us your skills, location, salary range and job type once.',
  },
  {
    step: '02',
    Icon: Sparkles,
    title: 'AI finds the best matches',
    desc: 'We score and rank thousands of jobs against your profile every day.',
  },
  {
    step: '03',
    Icon: MousePointerClick,
    title: 'Apply in one click',
    desc: 'Our extension auto-fills every application form so you only click "Submit".',
  },
  {
    step: '04',
    Icon: TrendingUp,
    title: 'Track & optimise',
    desc: "See what's working, get follow-up nudges, and keep improving your hit rate.",
  },
]

export default function Dashboard() {
  const dispatch = useAppDispatch()
  const navigate = useNavigate()
  const { user } = useAuth()

  const handleLogout = async () => {
    await dispatch(logoutUser())
    navigate('/login')
  }

  return (
    <div className="min-h-screen bg-[#f5f5fa]" style={{ fontFamily: 'EuclidR, sans-serif' }}>

      {/* ── Navbar ─────────────────────────────────────────────────────── */}
      <header className="sticky top-0 z-50 border-b border-[#e2e2ed] bg-white/90 backdrop-blur-md shadow-sm">
        <div className="max-w-7xl mx-auto px-6 flex items-center justify-between h-16">

          {/* Logo */}
          <div className="flex items-center gap-2">
            <span
              className="text-xl text-[#0f0f1a]"
              style={{ fontFamily: 'EuclidB, sans-serif' }}
            >
              Career
              <span className="text-[#10B981]">Sync</span>
            </span>
          </div>

          {/* Nav links */}
          <nav className="hidden md:flex items-center gap-6 text-sm text-[#6b6b80]">
            <a href="#features" className="hover:text-[#0f0f1a] transition-colors">Features</a>
            <a href="#how-it-works" className="hover:text-[#0f0f1a] transition-colors">How it works</a>
            <Link to="/support" className="hover:text-[#0f0f1a] transition-colors">Support</Link>
            <Link to="/about" className="hover:text-[#0f0f1a] transition-colors">About us</Link>
          </nav>

          {/* Right actions */}
          <div className="flex items-center gap-3">
            <Link
              to="/profile"
              className="flex items-center gap-2 px-3 py-2 rounded-lg bg-[#f5f5fa] border border-[#e2e2ed] text-sm text-[#6b6b80] hover:border-[#10B981]/50 hover:text-[#0f0f1a] transition-all duration-200"
            >
              <span className="w-6 h-6 rounded-full bg-[#10B981] flex items-center justify-center text-white text-xs flex-shrink-0"
                style={{ fontFamily: 'EuclidSB, sans-serif' }}>
                {user?.full_name?.[0]?.toUpperCase() ?? <User size={12} />}
              </span>
              <span className="hidden sm:block">{user?.full_name?.split(' ')[0] ?? 'Profile'}</span>
            </Link>
            <button
              onClick={handleLogout}
              className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-[#6b6b80] hover:text-[#ef4444] hover:bg-[#ef4444]/[0.06] border border-transparent hover:border-[#ef4444]/20 transition-all duration-200"
            >
              <LogOut size={15} />
              <span className="hidden sm:block">Log out</span>
            </button>
          </div>
        </div>
      </header>

      {/* ── Hero ───────────────────────────────────────────────────────── */}
      <section className="relative overflow-hidden px-6 pt-24 pb-28 text-center">
        {/* Background glow */}
        {/* <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[500px] bg-[#10B981]/[0.08] rounded-full blur-[130px] pointer-events-none" /> */}
        {/* <div className="absolute top-32 right-1/4 w-[260px] h-[260px] bg-[#10B981]/[0.05] rounded-full blur-[90px] pointer-events-none" /> */}

        <div className="relative max-w-4xl mx-auto">
          {/* Badge */}
          {/* <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-[#10B981]/[0.1] border border-[#10B981]/30 text-xs text-[#059669] mb-6"
            style={{ fontFamily: 'EuclidSB, sans-serif' }}>
            <span className="w-1.5 h-1.5 rounded-full bg-[#10B981] animate-pulse" />
            AI-powered job automation is live
          </div> */}

          <h1
            className="text-2xl sm:text-3xl lg:text-4xl text-[#0f0f1a] leading-tight mb-6"
            style={{ fontFamily: 'EuclidB, sans-serif' }}
          >
            Discover Jobs That Fit Your Skills, Get Smart Matches, and Apply with Ease {' '}
            <span className="text-[#10B981]">All in One Platform.</span>
          </h1>

          <p className="text-lg text-[#6b6b80] max-w-xl mx-auto mb-10 leading-relaxed">
            Our plateform scrapes thousands of jobs, scores them against your resume, and auto-applies
            to the best matches — all while you sleep.
          </p>

          {/* CTAs */}
          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
            <button
              onClick={() => navigate('/jobs')}
              className="group inline-flex items-center gap-3 px-8 py-4 bg-[#10B981] text-white rounded-xl shadow-[0_8px_32px_rgba(16,185,129,0.25)] hover:shadow-[0_12px_40px_rgba(16,185,129,0.4)] hover:-translate-y-0.5 transition-all duration-200 w-full sm:w-auto justify-center"
              style={{ fontFamily: 'EuclidSB, sans-serif' }}
            >
              <Briefcase size={18} strokeWidth={2.5} />
              Get Jobs Now
              <ChevronRight size={16} className="group-hover:translate-x-0.5 transition-transform" />
            </button>

            <a
              href="#extension"
              className="group inline-flex items-center gap-3 px-8 py-4 bg-white border border-[#e2e2ed] text-[#0f0f1a] rounded-xl hover:border-[#10B981]/50 hover:shadow-[0_8px_28px_rgba(16,185,129,0.1)] hover:-translate-y-0.5 transition-all duration-200 w-full sm:w-auto justify-center shadow-sm"
              style={{ fontFamily: 'EuclidSB, sans-serif' }}
            >
              <Puzzle size={18} className="text-[#6b6b80]" />
              Download Extension
              <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-[#10B981]/10 border border-[#10B981]/30 text-[#059669] text-xs"
                style={{ fontFamily: 'EuclidSB, sans-serif' }}>
                Free
              </span>
            </a>
          </div>

          <p className="mt-5 text-xs text-[#a0a0b0]">
            No credit card required &nbsp;·&nbsp; Works with Chrome & Firefox &nbsp;·&nbsp; 2-minute setup
          </p>
        </div>
      </section>

      {/* ── Features ───────────────────────────────────────────────────── */}
      <section id="features" className="py-24 px-6 bg-white">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-14">
            <h2
              className="text-3xl sm:text-4xl text-[#0f0f1a] mb-4"
              style={{ fontFamily: 'EuclidB, sans-serif' }}
            >
              Everything you need to land a job faster
            </h2>
            <p className="text-[#6b6b80] max-w-lg mx-auto">
              One platform. Zero repetitive form-filling. Maximum interview callbacks.
            </p>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {FEATURES.map(({ Icon, title, desc }) => (
              <div
                key={title}
                className="p-6 bg-[#f5f5fa] border border-[#e8e8f0] rounded-2xl hover:border-[#10B981]/40 hover:shadow-[0_4px_24px_rgba(16,185,129,0.08)] transition-all duration-300 group"
              >
                <div className="w-10 h-10 rounded-xl bg-[#10B981]/10 border border-[#10B981]/20 flex items-center justify-center mb-4 group-hover:bg-[#10B981]/15 transition-colors">
                  <Icon size={18} className="text-[#10B981]" strokeWidth={1.75} />
                </div>
                <h3
                  className="text-[#0f0f1a] text-base mb-2 group-hover:text-[#059669] transition-colors"
                  style={{ fontFamily: 'EuclidSB, sans-serif' }}
                >
                  {title}
                </h3>
                <p className="text-sm text-[#6b6b80] leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── How it works ───────────────────────────────────────────────── */}
      <section id="how-it-works" className="py-24 px-6 bg-[#f5f5fa]">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-14">
            <h2
              className="text-3xl sm:text-4xl text-[#0f0f1a] mb-4"
              style={{ fontFamily: 'EuclidB, sans-serif' }}
            >
              How it works
            </h2>
            <p className="text-[#6b6b80]">From signup to offer letter in four simple steps.</p>
          </div>

          <div className="flex flex-col gap-4">
            {HOW_IT_WORKS.map(({ step, Icon, title, desc }, i) => (
              <div key={step} className="flex items-start gap-5 group">
                {/* Step number + connector */}
                <div className="flex flex-col items-center flex-shrink-0">
                  <div className="w-12 h-12 rounded-xl bg-white border border-[#e2e2ed] flex items-center justify-center group-hover:border-[#10B981]/50 group-hover:bg-[#10B981]/[0.07] transition-all duration-300 shadow-sm">
                    <Icon size={18} className="text-[#a0a0b0] group-hover:text-[#10B981] transition-colors" strokeWidth={1.75} />
                  </div>
                  {i < HOW_IT_WORKS.length - 1 && (
                    <div className="w-px h-8 bg-[#e2e2ed] mt-1" />
                  )}
                </div>

                <div className="pt-2.5 pb-6">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs text-[#10B981]" style={{ fontFamily: 'EuclidSB, sans-serif' }}>
                      {step}
                    </span>
                    <h3
                      className="text-[#0f0f1a]"
                      style={{ fontFamily: 'EuclidSB, sans-serif' }}
                    >
                      {title}
                    </h3>
                  </div>
                  <p className="text-sm text-[#6b6b80] leading-relaxed">{desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Extension CTA ──────────────────────────────────────────────── */}
      <section id="extension" className="py-24 px-6 bg-white">
        <div className="max-w-3xl mx-auto text-center bg-[#f5f5fa] border border-[#e2e2ed] rounded-3xl p-12 relative overflow-hidden shadow-sm">
          {/* Subtle glow */}
          <div className="absolute inset-0 bg-[#10B981]/[0.02] pointer-events-none rounded-3xl" />
          <div className="absolute -bottom-20 left-1/2 -translate-x-1/2 w-[400px] h-[200px] bg-[#10B981]/[0.07] rounded-full blur-[80px] pointer-events-none" />

          <div className="relative">
            <div className="w-14 h-14 rounded-2xl bg-[#10B981]/10 border border-[#10B981]/20 flex items-center justify-center mx-auto mb-6">
              <Puzzle size={26} className="text-[#10B981]" strokeWidth={1.75} />
            </div>

            <h2
              className="text-3xl text-[#0f0f1a] mb-4"
              style={{ fontFamily: 'EuclidB, sans-serif' }}
            >
              Get the browser extension
            </h2>
            <p className="text-[#6b6b80] mb-8 leading-relaxed">
              Install our Chrome or Firefox extension and let ApplyAI auto-fill job applications
              directly on Naukri, Internshala and LinkedIn — no copy-pasting ever again.
            </p>

            <div className="flex flex-col sm:flex-row gap-3 justify-center">
              <a
                href="#"
                className="inline-flex items-center justify-center gap-2 px-6 py-3 bg-[#10B981] text-white rounded-xl hover:bg-[#0ea572] transition-colors shadow-[0_4px_16px_rgba(16,185,129,0.25)]"
                style={{ fontFamily: 'EuclidSB, sans-serif' }}
              >
                <Globe size={16} strokeWidth={2} />
                Add to Chrome
              </a>
              <a
                href="#"
                className="inline-flex items-center justify-center gap-2 px-6 py-3 bg-white border border-[#e2e2ed] text-[#0f0f1a] rounded-xl hover:border-[#10B981]/40 hover:bg-[#10B981]/[0.04] transition-all shadow-sm"
                style={{ fontFamily: 'EuclidSB, sans-serif' }}
              >
                <Download size={16} strokeWidth={2} />
                Add to Firefox
              </a>
            </div>

            <div className="flex items-center justify-center gap-4 mt-5 text-xs text-[#a0a0b0]">
              {['Free forever', 'No account sharing', 'Open source'].map((item) => (
                <span key={item} className="flex items-center gap-1">
                  <CheckCircle2 size={11} className="text-[#10B981]/60" />
                  {item}
                </span>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── Footer ─────────────────────────────────────────────────────── */}
      <footer className="border-t border-[#e2e2ed] bg-white py-10 px-6">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4 text-sm text-[#a0a0b0]">
          <div className="flex items-center gap-2 text-[#6b6b80]" style={{ fontFamily: 'EuclidSB, sans-serif' }}>
            <div className="w-6 h-6 rounded-md bg-[#10B981] flex items-center justify-center">
              <Zap size={12} className="text-white" strokeWidth={2.5} />
            </div>
            ApplyAI
          </div>

          <div className="flex gap-6">
            <Link to="/support" className="hover:text-[#10B981] transition-colors">Support</Link>
            <Link to="/profile" className="hover:text-[#10B981] transition-colors">My Profile</Link>
            <a href="#" className="hover:text-[#10B981] transition-colors">Privacy</a>
            <a href="#" className="hover:text-[#10B981] transition-colors">Terms</a>
          </div>

          <p>© 2026 ApplyAI. All rights reserved.</p>
        </div>
      </footer>
    </div>
  )
}