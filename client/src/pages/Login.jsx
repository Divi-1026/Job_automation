import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAppDispatch, useAuth } from '../store/hooks'
import { loginUser, clearError } from '../store/authSlice'
import {
  Zap, Bot, BarChart2, Search, Eye, EyeOff,
  AlertTriangle, Loader2, ArrowRight,
} from 'lucide-react'

export default function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPass, setShowPass] = useState(false)
  const [errors, setErrors] = useState({})
  const navigate = useNavigate()
  const dispatch = useAppDispatch()
  const { loading, error: apiError } = useAuth()

  const handleSubmit = async (e) => {
    e.preventDefault()
    dispatch(clearError())
    const errs = {}
    if (!email.trim()) errs.email = 'Email is required'
    if (!password.trim()) errs.password = 'Password is required'
    setErrors(errs)
    if (Object.keys(errs).length) return

    const result = await dispatch(loginUser({ email, password }))
    if (loginUser.fulfilled.match(result)) navigate('/dashboard')
  }

  const inputCls = (err) =>
    `w-full px-3.5 py-3 bg-white border rounded-lg text-sm text-[#0f0f1a] placeholder-[#a0a0b0] outline-none transition-all duration-200 ${err
      ? 'border-[#ef4444] shadow-[0_0_0_3px_rgba(239,68,68,0.08)]'
      : 'border-[#e2e2ed] focus:border-[#10B981] focus:shadow-[0_0_0_3px_rgba(16,185,129,0.12)]'
    }`

  return (
    <div className="flex min-h-screen bg-[#f5f5fa]" style={{ fontFamily: 'EuclidR, sans-serif' }}>

      {/* ── Left panel ─────────────────────────────────────────────── */}
      <div className="hidden lg:flex flex-col justify-between w-[420px] min-h-screen bg-white border-r border-[#e2e2ed] px-10 py-12 relative overflow-hidden flex-shrink-0 shadow-sm">
        <div className="relative z-10">
          <div className="flex items-center gap-2.5 mb-10">
            <span className="text-xl text-[#0f0f1a]" style={{ fontFamily: 'EuclidB, sans-serif' }}>
              AI Assisted:
              <span className="text-[#10B981]"> Job Application and Automation System</span>
            </span>
          </div>
          <h2 className="text-2xl text-[#0f0f1a] leading-tight mb-4" style={{ fontFamily: 'EuclidB, sans-serif' }}>
            Welcome back! Your next job is one click away.
          </h2>
          <p className="text-[#6b6b80] text-sm leading-relaxed">
            Sign in to continue your job hunt.
          </p>
        </div>

        <div className="flex flex-col gap-4 relative z-10">
          {[
            { Icon: Bot, title: 'Auto-Apply', desc: 'Apply to 100s of jobs in one click' },
            { Icon: BarChart2, title: 'Skill Match Score', desc: 'See how well you fit every role' },
            { Icon: Search, title: 'Multi-Platform', desc: 'Naukri, Internshala & more' },
          ].map(({ Icon, title, desc }) => (
            <div key={title}
              className="flex items-center gap-4 bg-[#f5f5fa] border border-[#e2e2ed] rounded-xl px-4 py-4 hover:border-[#10B981]/50 hover:shadow-[0_4px_16px_rgba(16,185,129,0.08)] hover:translate-x-1 transition-all duration-200">
              <div className="w-9 h-9 rounded-lg bg-[#10B981]/10 border border-[#10B981]/20 flex items-center justify-center flex-shrink-0">
                <Icon size={17} className="text-[#10B981]" strokeWidth={1.75} />
              </div>
              <div>
                <p className="text-sm text-[#0f0f1a]" style={{ fontFamily: 'EuclidSB, sans-serif' }}>{title}</p>
                <p className="text-xs text-[#6b6b80] mt-0.5">{desc}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Subtle bottom glow */}
        <div className="absolute -bottom-20 left-1/2 -translate-x-1/2 w-[300px] h-[200px] bg-[#10B981]/[0.08] rounded-full blur-[80px] pointer-events-none" />
      </div>

      {/* ── Right form panel ───────────────────────────────────────── */}
      <div className="flex-1 flex items-center justify-center px-6 py-10">
        <div className="w-full max-w-[440px]">

          {/* Mobile logo */}
          <div className="flex items-center gap-2.5 mb-8 lg:hidden">
            <div className="w-8 h-8 rounded-lg bg-[#10B981] flex items-center justify-center">
              <Zap size={15} className="text-white" strokeWidth={2.5} />
            </div>
            <span className="text-xl text-[#0f0f1a]" style={{ fontFamily: 'EuclidB, sans-serif' }}>
              Apply<span className="text-[#10B981]">AI</span>
            </span>
          </div>

          <div className="mb-8">
            <h1 className="text-3xl text-[#0f0f1a] mb-1" style={{ fontFamily: 'EuclidB, sans-serif' }}>
              Sign In
            </h1>
            <p className="text-[#6b6b80] text-sm">
              Don't have an account?{' '}
              <Link to="/signup" className="text-[#10B981] hover:text-[#059669] transition-colors"
                style={{ fontFamily: 'EuclidSB, sans-serif' }}>
                Create one
              </Link>
            </p>
          </div>

          <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-5">

            {/* Email */}
            <div className="flex flex-col gap-1.5">
              <label className="text-xs text-[#6b6b80] uppercase tracking-wide"
                style={{ fontFamily: 'EuclidSB, sans-serif' }}>
                Email Address
              </label>
              <input type="email" placeholder="rahul@example.com"
                value={email} onChange={e => setEmail(e.target.value)}
                className={inputCls(errors.email)} />
              {errors.email && (
                <span className="flex items-center gap-1 text-xs text-[#ef4444]">
                  <AlertTriangle size={11} strokeWidth={2} /> {errors.email}
                </span>
              )}
            </div>

            {/* Password */}
            <div className="flex flex-col gap-1.5">
              <label className="text-xs text-[#6b6b80] uppercase tracking-wide"
                style={{ fontFamily: 'EuclidSB, sans-serif' }}>
                Password
              </label>
              <div className="relative">
                <input type={showPass ? 'text' : 'password'} placeholder="Your password"
                  value={password} onChange={e => setPassword(e.target.value)}
                  className={inputCls(errors.password) + ' pr-11'} />
                <button type="button" onClick={() => setShowPass(p => !p)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-[#a0a0b0] hover:text-[#6b6b80] transition-colors">
                  {showPass ? <EyeOff size={16} strokeWidth={1.75} /> : <Eye size={16} strokeWidth={1.75} />}
                </button>
              </div>
              {errors.password && (
                <span className="flex items-center gap-1 text-xs text-[#ef4444]">
                  <AlertTriangle size={11} strokeWidth={2} /> {errors.password}
                </span>
              )}
            </div>

            {/* Remember me / forgot */}
            <div className="flex items-center justify-between text-sm">
              <label className="flex items-center gap-2 text-[#6b6b80] cursor-pointer select-none">
                <input type="checkbox" className="w-4 h-4 accent-[#10B981] cursor-pointer" />
                Remember me
              </label>
              <a href="#" className="text-[#10B981] hover:text-[#059669] text-xs transition-colors"
                style={{ fontFamily: 'EuclidSB, sans-serif' }}>
                Forgot password?
              </a>
            </div>

            {/* API error */}
            {apiError && (
              <div className="px-4 py-3 bg-[#ef4444]/[0.07] border border-[#ef4444]/30 rounded-lg text-sm text-[#ef4444] flex items-center gap-2">
                <AlertTriangle size={15} strokeWidth={2} className="flex-shrink-0" /> {apiError}
              </div>
            )}

            {/* Submit */}
            <button type="submit" disabled={loading}
              className="w-full flex items-center justify-center gap-2 py-3 bg-[#10B981] text-white rounded-lg text-sm shadow-[0_4px_18px_rgba(16,185,129,0.25)] hover:bg-[#0ea572] hover:-translate-y-0.5 hover:shadow-[0_6px_24px_rgba(16,185,129,0.38)] transition-all duration-200 mt-1 disabled:opacity-60 disabled:cursor-not-allowed disabled:transform-none"
              style={{ fontFamily: 'EuclidSB, sans-serif' }}>
              {loading
                ? <><Loader2 size={15} className="animate-spin" /> Signing in...</>
                : <>Sign In <ArrowRight size={15} strokeWidth={2.5} /></>
              }
            </button>

            {/* Divider */}
            <div className="flex items-center gap-3 text-[#a0a0b0] text-xs">
              <div className="flex-1 h-px bg-[#e2e2ed]" />
              <span>or</span>
              <div className="flex-1 h-px bg-[#e2e2ed]" />
            </div>

            {/* Google */}
            <button type="button"
              className="w-full py-3 bg-white border border-[#e2e2ed] text-[#6b6b80] rounded-lg text-sm flex items-center justify-center gap-2.5 hover:border-[#10B981]/50 hover:text-[#0f0f1a] hover:shadow-[0_4px_16px_rgba(16,185,129,0.08)] transition-all duration-200 shadow-sm"
              style={{ fontFamily: 'EuclidSB, sans-serif' }}>
              <img src="https://www.svgrepo.com/show/475656/google-color.svg" alt="Google" className="w-4 h-4" />
              Continue with Google
            </button>

          </form>
        </div>
      </div>
    </div>
  )
}