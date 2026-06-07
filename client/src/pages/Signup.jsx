import { useState, useRef, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAppDispatch, useAuth } from '../store/hooks'
import { signupUser, clearError } from '../store/authSlice'
import {
  Zap, Bot, BarChart2, Search, GraduationCap, Briefcase,
  Lightbulb, AlertTriangle, Check, X, Eye, EyeOff,
} from 'lucide-react'

const STEPS = ['Account', 'Profile', 'Experience', 'Skills']

const initialForm = {
  fullName: '', email: '', password: '', confirmPassword: '',
  phone: '', githubId: '', linkedinId: '', portfolioUrl: '',
  location: '', experienceType: 'fresher', yearsOfExperience: '',
  currentCompany: '', currentRole: '', highestEducation: '',
  college: '', graduationYear: '', skills: [], bio: '',
}

export default function Signup() {
  const [step, setStep] = useState(0)
  const [form, setForm] = useState(initialForm)
  const [skillInput, setSkillInput] = useState('')
  const [errors, setErrors] = useState({})
  const [showPass, setShowPass] = useState(false)
  const [showConfirmPass, setShowConfirmPass] = useState(false)
  const navigate = useNavigate()
  const dispatch = useAppDispatch()
  const { loading, error: apiError } = useAuth()

  useEffect(() => { dispatch(clearError()) }, [step, dispatch])

  const set = (field, value) => {
    setForm(prev => ({ ...prev, [field]: value }))
    setErrors(prev => ({ ...prev, [field]: '' }))
  }

  const addSkill = (e) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault()
      const skill = skillInput.trim().replace(/,$/, '')
      if (skill && !form.skills.includes(skill)) set('skills', [...form.skills, skill])
      setSkillInput('')
    }
  }
  const removeSkill = (s) => set('skills', form.skills.filter(x => x !== s))

  const validateStep = () => {
    const e = {}
    if (step === 0) {
      if (!form.fullName.trim()) e.fullName = 'Full name is required'
      if (!form.email.trim() || !/^[^@]+@[^@]+\.[^@]+$/.test(form.email)) e.email = 'Valid email required'
      if (form.password.length < 8) e.password = 'Min 8 characters'
      if (form.password !== form.confirmPassword) e.confirmPassword = 'Passwords do not match'
      if (!form.phone.trim() || !/^[6-9]\d{9}$/.test(form.phone)) e.phone = 'Valid 10-digit phone required'
    }
    if (step === 2 && form.experienceType === 'experienced' && !form.yearsOfExperience) {
      e.yearsOfExperience = 'Required'
    }
    setErrors(e)
    return Object.keys(e).length === 0
  }

  const next = () => { if (validateStep()) setStep(s => Math.min(s + 1, STEPS.length - 1)) }
  const prev = () => setStep(s => Math.max(s - 1, 0))

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!validateStep()) return

    const payload = {
      full_name: form.fullName,
      email: form.email,
      password: form.password,
      phone: form.phone || null,
      github_id: form.githubId || null,
      linkedin_id: form.linkedinId || null,
      portfolio_url: form.portfolioUrl || null,
      location: form.location || null,
      bio: form.bio || null,
      experience_type: form.experienceType,
      years_of_experience: form.yearsOfExperience ? Number(form.yearsOfExperience) : null,
      current_company: form.currentCompany || null,
      current_role: form.currentRole || null,
      highest_education: form.highestEducation || null,
      college: form.college || null,
      graduation_year: form.graduationYear ? Number(form.graduationYear) : null,
      skills: form.skills,
    }

    const result = await dispatch(signupUser(payload))
    if (signupUser.fulfilled.match(result)) {
      navigate('/dashboard')
    }
  }

  return (
    <div className="flex min-h-screen bg-[#f5f5fa]" style={{ fontFamily: 'EuclidR, sans-serif' }}>

      {/* Left Branding Panel - unchanged */}
      <div className="hidden lg:flex flex-col justify-between w-[420px] min-h-screen bg-white border-r border-[#e2e2ed] px-10 py-12 relative overflow-hidden flex-shrink-0 shadow-sm">
        <div className="relative z-10">
          <div className="flex items-center gap-2.5 mb-10">
            <span className="text-2xl text-[#0f0f1a]" style={{ fontFamily: 'EuclidB, sans-serif' }}>
              Career<span className="text-[#10B981]"> Sync</span>
            </span>
          </div>
          <h2 className="text-3xl text-[#0f0f1a] leading-tight mb-4" style={{ fontFamily: 'EuclidB, sans-serif' }}>
            Land your dream job
          </h2>
          <p className="text-[#6b6b80] text-sm leading-relaxed">
            Automate applications, match skills, and get hired faster.
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
        <div className="absolute -bottom-20 left-1/2 -translate-x-1/2 w-[300px] h-[200px] bg-[#10B981]/[0.08] rounded-full blur-[80px] pointer-events-none" />
      </div>

      {/* Right Form Panel */}
      <div className="flex-1 overflow-y-auto flex items-start justify-center px-6 py-10">
        <div className="w-full max-w-[560px]">

          {/* Mobile logo */}
          <div className="flex items-center gap-2.5 mb-6 lg:hidden">
            <div className="w-8 h-8 rounded-lg bg-[#10B981] flex items-center justify-center">
              <Zap size={15} className="text-white" strokeWidth={2.5} />
            </div>
            <span className="text-xl text-[#0f0f1a]" style={{ fontFamily: 'EuclidB, sans-serif' }}>
              Career<span className="text-[#10B981]"> Sync</span>
            </span>
          </div>

          <div className="mb-7">
            <h1 className="text-3xl text-[#0f0f1a] mb-1" style={{ fontFamily: 'EuclidB, sans-serif' }}>
              Create Account
            </h1>
            <p className="text-[#6b6b80] text-sm">
              Already have an account?{' '}
              <Link to="/login" className="text-[#10B981] hover:text-[#059669] transition-colors"
                style={{ fontFamily: 'EuclidSB, sans-serif' }}>Sign in</Link>
            </p>
          </div>

          {/* Stepper */}
          <div className="flex items-center mb-8">
            {STEPS.map((label, i) => (
              <div key={label} className="flex items-center">
                <div className="flex items-center gap-2">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs flex-shrink-0 transition-all duration-300 ${i < step
                    ? 'bg-[#10B981] text-white'
                    : i === step
                      ? 'bg-[#10B981] text-white shadow-[0_0_16px_rgba(16,185,129,0.35)]'
                      : 'bg-white border-2 border-[#e2e2ed] text-[#a0a0b0]'
                    }`} style={{ fontFamily: 'EuclidSB, sans-serif' }}>
                    {i < step ? <Check size={14} strokeWidth={2.5} /> : i + 1}
                  </div>
                  <span className={`text-xs hidden sm:block ${i === step ? 'text-[#0f0f1a]' : i < step ? 'text-[#10B981]' : 'text-[#a0a0b0]'
                    }`} style={{ fontFamily: 'EuclidSB, sans-serif' }}>{label}</span>
                </div>
                {i < STEPS.length - 1 && (
                  <div className={`h-0.5 mx-2 flex-1 min-w-[16px] transition-all duration-300 ${i < step ? 'bg-[#10B981]' : 'bg-[#e2e2ed]'
                    }`} />
                )}
              </div>
            ))}
          </div>

          <form onSubmit={handleSubmit} noValidate>

            {/* Step 0: Account */}
            {step === 0 && (
              <div className="flex flex-col gap-5 animate-fade-in-up">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <Field label="Full Name" error={errors.fullName}>
                    <input type="text" placeholder="Rahul Sharma"
                      value={form.fullName} onChange={e => set('fullName', e.target.value)}
                      className={inputCls(errors.fullName)} />
                  </Field>
                  <Field label="Phone Number" error={errors.phone}>
                    <input type="tel" placeholder="9876543210"
                      value={form.phone} onChange={e => set('phone', e.target.value)}
                      className={inputCls(errors.phone)} />
                  </Field>
                </div>
                <Field label="Email Address" error={errors.email}>
                  <input type="email" placeholder="rahul@example.com"
                    value={form.email} onChange={e => set('email', e.target.value)}
                    className={inputCls(errors.email)} />
                </Field>
                <Field label="Password" error={errors.password}>
                  <PasswordInput value={form.password} onChange={v => set('password', v)}
                    show={showPass} toggleShow={() => setShowPass(p => !p)}
                    placeholder="Min 8 characters" hasError={!!errors.password} />
                </Field>
                <Field label="Confirm Password" error={errors.confirmPassword}>
                  <PasswordInput value={form.confirmPassword} onChange={v => set('confirmPassword', v)}
                    show={showConfirmPass} toggleShow={() => setShowConfirmPass(p => !p)}
                    placeholder="Repeat password" hasError={!!errors.confirmPassword} />
                </Field>
              </div>
            )}

            {/* Step 1: Profile (without resume upload) */}
            {step === 1 && (
              <div className="flex flex-col gap-5 animate-fade-in-up">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <Field label="GitHub Username" hint="optional">
                    <div className="flex">
                      <span className="flex items-center px-3 bg-[#f5f5fa] border border-r-0 border-[#e2e2ed] rounded-l-lg text-xs text-[#a0a0b0] whitespace-nowrap">
                        github.com/
                      </span>
                      <input type="text" placeholder="yourusername"
                        value={form.githubId} onChange={e => set('githubId', e.target.value)}
                        className={inputCls() + ' rounded-l-none'} />
                    </div>
                  </Field>
                  <Field label="LinkedIn ID" hint="optional">
                    <div className="flex">
                      <span className="flex items-center px-3 bg-[#f5f5fa] border border-r-0 border-[#e2e2ed] rounded-l-lg text-xs text-[#a0a0b0] whitespace-nowrap">
                        linkedin.com/in/
                      </span>
                      <input type="text" placeholder="yourprofile"
                        value={form.linkedinId} onChange={e => set('linkedinId', e.target.value)}
                        className={inputCls() + ' rounded-l-none'} />
                    </div>
                  </Field>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <Field label="Portfolio / Website" hint="optional">
                    <input type="url" placeholder="https://yoursite.com"
                      value={form.portfolioUrl} onChange={e => set('portfolioUrl', e.target.value)}
                      className={inputCls()} />
                  </Field>
                  <Field label="Location">
                    <input type="text" placeholder="City, State"
                      value={form.location} onChange={e => set('location', e.target.value)}
                      className={inputCls()} />
                  </Field>
                </div>
                <Field label="Short Bio" hint="optional">
                  <textarea rows={3} placeholder="Tell us about yourself..."
                    value={form.bio} onChange={e => set('bio', e.target.value)}
                    className={inputCls() + ' resize-none'} />
                </Field>
                {/* Resume upload removed – now only in Profile page */}
              </div>
            )}

            {/* Step 2: Experience - unchanged */}
            {step === 2 && (
              <div className="flex flex-col gap-5 animate-fade-in-up">
                <Field label="I am a...">
                  <div className="flex gap-3">
                    {[
                      { opt: 'fresher', Icon: GraduationCap, label: 'Fresher' },
                      { opt: 'experienced', Icon: Briefcase, label: 'Experienced' },
                    ].map(({ opt, Icon, label }) => (
                      <button key={opt} type="button"
                        onClick={() => set('experienceType', opt)}
                        className={`flex-1 flex items-center justify-center gap-2 py-3 px-4 rounded-lg border-2 text-sm transition-all duration-200
                          ${form.experienceType === opt
                            ? 'border-[#10B981] bg-[#10B981]/[0.08] text-[#059669] shadow-[0_0_12px_rgba(16,185,129,0.15)]'
                            : 'border-[#e2e2ed] bg-white text-[#6b6b80] hover:border-[#10B981]/50 hover:text-[#0f0f1a]'
                          }`}
                        style={{ fontFamily: 'EuclidSB, sans-serif' }}>
                        <Icon size={16} strokeWidth={1.75} />
                        {label}
                      </button>
                    ))}
                  </div>
                </Field>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <Field label="Highest Education">
                    <select value={form.highestEducation} onChange={e => set('highestEducation', e.target.value)}
                      className={selectCls()}>
                      <option value="">Select...</option>
                      {['10th', '12th', 'Diploma', 'B.Tech / B.E.', 'B.Sc', 'BCA', 'MCA', 'M.Tech', 'MBA', 'PhD', 'Other'].map(o => <option key={o}>{o}</option>)}
                    </select>
                  </Field>
                  <Field label="Graduation Year">
                    <input type="number" placeholder="2024" min="2000" max="2030"
                      value={form.graduationYear} onChange={e => set('graduationYear', e.target.value)}
                      className={inputCls()} />
                  </Field>
                </div>
                <Field label="College / University">
                  <input type="text" placeholder="IIT Delhi, VIT etc."
                    value={form.college} onChange={e => set('college', e.target.value)}
                    className={inputCls()} />
                </Field>
                {form.experienceType === 'experienced' && (
                  <>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <Field label="Years of Experience" error={errors.yearsOfExperience}>
                        <input type="number" placeholder="2" min="0" max="50"
                          value={form.yearsOfExperience} onChange={e => set('yearsOfExperience', e.target.value)}
                          className={inputCls(errors.yearsOfExperience)} />
                      </Field>
                      <Field label="Current Role">
                        <input type="text" placeholder="Software Engineer"
                          value={form.currentRole} onChange={e => set('currentRole', e.target.value)}
                          className={inputCls()} />
                      </Field>
                    </div>
                    <Field label="Current / Last Company">
                      <input type="text" placeholder="Google, Infosys etc."
                        value={form.currentCompany} onChange={e => set('currentCompany', e.target.value)}
                        className={inputCls()} />
                    </Field>
                  </>
                )}
              </div>
            )}

            {/* Step 3: Skills - unchanged */}
            {step === 3 && (
              <div className="flex flex-col gap-5 animate-fade-in-up">
                <div className="flex items-center gap-3 px-4 py-3 bg-[#10B981]/[0.07] border border-[#10B981]/25 rounded-lg text-sm text-[#059669]">
                  <Lightbulb size={17} className="flex-shrink-0" strokeWidth={1.75} />
                  <span>These skills will be used by AI to match you with the best jobs.</span>
                </div>
                <Field label="Add Skills" hint="Press Enter or comma to add">
                  <div className="flex flex-wrap gap-2 p-3 bg-white border border-[#e2e2ed] rounded-lg focus-within:border-[#10B981] focus-within:shadow-[0_0_0_3px_rgba(16,185,129,0.12)] transition-all duration-200 min-h-[48px] items-center">
                    {form.skills.map(s => (
                      <span key={s} className="flex items-center gap-1.5 px-3 py-1 bg-[#10B981]/10 border border-[#10B981]/30 rounded-full text-xs text-[#059669]"
                        style={{ fontFamily: 'EuclidSB, sans-serif' }}>
                        {s}
                        <button type="button" onClick={() => removeSkill(s)}
                          className="text-[#a0a0b0] hover:text-[#ef4444] transition-colors leading-none">
                          <X size={11} strokeWidth={2.5} />
                        </button>
                      </span>
                    ))}
                    <input type="text"
                      placeholder={form.skills.length === 0 ? 'e.g. React, Python, Node.js...' : ''}
                      value={skillInput} onChange={e => setSkillInput(e.target.value)} onKeyDown={addSkill}
                      className="flex-1 min-w-[140px] bg-transparent border-none outline-none text-sm text-[#0f0f1a] placeholder-[#a0a0b0]" />
                  </div>
                </Field>
                <div>
                  <p className="text-xs text-[#a0a0b0] mb-2">Popular skills:</p>
                  <div className="flex flex-wrap gap-2">
                    {['React', 'Node.js', 'Python', 'JavaScript', 'Java', 'SQL', 'AWS', 'Docker', 'MongoDB', 'TypeScript', 'Communication', 'Problem Solving'].map(s =>
                      !form.skills.includes(s) && (
                        <button key={s} type="button" onClick={() => set('skills', [...form.skills, s])}
                          className="px-3 py-1.5 bg-white border border-[#e2e2ed] rounded-full text-xs text-[#6b6b80] hover:border-[#10B981]/50 hover:text-[#059669] hover:bg-[#10B981]/[0.05] transition-all duration-200">
                          + {s}
                        </button>
                      )
                    )}
                  </div>
                </div>
                <label className="flex items-start gap-2.5 text-sm text-[#6b6b80] cursor-pointer">
                  <input type="checkbox" required className="mt-0.5 w-4 h-4 accent-[#10B981] cursor-pointer flex-shrink-0" />
                  <span>I agree to the <a href="#" className="text-[#10B981] hover:text-[#059669] hover:underline">Terms of Service</a> and <a href="#" className="text-[#10B981] hover:text-[#059669] hover:underline">Privacy Policy</a></span>
                </label>
              </div>
            )}

            {/* API error banner */}
            {apiError && (
              <div className="mt-5 px-4 py-3 bg-[#ef4444]/[0.08] border border-[#ef4444]/30 rounded-lg text-sm text-[#ef4444] flex items-center gap-2">
                <AlertTriangle size={15} strokeWidth={2} /> {apiError}
              </div>
            )}

            {/* Navigation buttons */}
            <div className="flex justify-end gap-3 mt-8">
              {step > 0 && (
                <button type="button" onClick={prev}
                  className="px-6 py-3 bg-white border border-[#e2e2ed] text-[#6b6b80] rounded-lg text-sm hover:border-[#10B981]/50 hover:text-[#0f0f1a] transition-all duration-200 shadow-sm"
                  style={{ fontFamily: 'EuclidSB, sans-serif' }}>
                  ← Back
                </button>
              )}
              {step < STEPS.length - 1 ? (
                <button type="button" onClick={next}
                  className="px-6 py-3 bg-[#10B981] text-white rounded-lg text-sm shadow-[0_4px_18px_rgba(16,185,129,0.3)] hover:bg-[#0ea572] hover:-translate-y-0.5 hover:shadow-[0_6px_24px_rgba(16,185,129,0.4)] transition-all duration-200"
                  style={{ fontFamily: 'EuclidSB, sans-serif' }}>
                  Continue →
                </button>
              ) : (
                <button type="submit" disabled={loading}
                  className="px-6 py-3 bg-[#10B981] text-white rounded-lg text-sm shadow-[0_4px_18px_rgba(16,185,129,0.3)] hover:bg-[#0ea572] hover:-translate-y-0.5 hover:shadow-[0_6px_26px_rgba(16,185,129,0.4)] transition-all duration-200 disabled:opacity-60 disabled:cursor-not-allowed disabled:transform-none"
                  style={{ fontFamily: 'EuclidSB, sans-serif' }}>
                  {loading ? '⏳ Creating account...' : '🚀 Create My Account'}
                </button>
              )}
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}

// Helper components (unchanged)
const inputCls = (err) =>
  `w-full px-3.5 py-3 bg-white border rounded-lg text-sm text-[#0f0f1a] placeholder-[#a0a0b0] outline-none transition-all duration-200 ${err
    ? 'border-[#ef4444] shadow-[0_0_0_3px_rgba(239,68,68,0.1)]'
    : 'border-[#e2e2ed] focus:border-[#10B981] focus:shadow-[0_0_0_3px_rgba(16,185,129,0.12)]'
  }`

const selectCls = () =>
  `w-full px-3.5 py-3 bg-white border border-[#e2e2ed] rounded-lg text-sm text-[#0f0f1a] outline-none cursor-pointer transition-all duration-200 focus:border-[#10B981] focus:shadow-[0_0_0_3px_rgba(16,185,129,0.12)] appearance-none`

function PasswordInput({ value, onChange, show, toggleShow, placeholder, hasError }) {
  return (
    <div className="relative">
      <input type={show ? 'text' : 'password'} placeholder={placeholder}
        value={value} onChange={e => onChange(e.target.value)}
        className={inputCls(hasError) + ' pr-11'} />
      <button type="button" onClick={toggleShow}
        className="absolute right-3 top-1/2 -translate-y-1/2 text-base text-[#a0a0b0] hover:text-[#6b6b80] transition-colors">
        {show ? <EyeOff size={20} /> : <Eye size={20} />}
      </button>
    </div>
  )
}

function Field({ label, hint, error, children }) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-xs tracking-wide uppercase text-[#6b6b80]"
        style={{ fontFamily: 'EuclidSB, sans-serif' }}>
        {label}
        {hint && <span className="text-[#a0a0b0] normal-case font-normal tracking-normal"> · {hint}</span>}
      </label>
      {children}
      {error && <span className="text-xs text-[#ef4444]">⚠ {error}</span>}
    </div>
  )
}