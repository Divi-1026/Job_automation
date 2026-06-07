import { useState, useRef, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAppDispatch, useAuth } from '../store/hooks'
import {
  updateProfile, changePassword,
  uploadResume, deleteResume, logoutUser,
} from '../store/authSlice'
import api from '../api/axiosInstance'  // <-- import api for credentials
import {
  Zap, ArrowLeft, LogOut, Link2, MapPin, Github, Linkedin, Globe,
  Briefcase, GraduationCap, Wrench, FileText, Upload, Lock,
  AlertTriangle, CheckCircle, X, Save, Loader2, ExternalLink,
} from 'lucide-react'

const inputCls = (err) =>
  `w-full px-4 py-3 rounded-lg bg-white border text-[#0f0f1a] text-sm placeholder-[#a0a0b0]
   focus:outline-none focus:shadow-[0_0_0_3px_rgba(16,185,129,0.12)] transition-all duration-200
   ${err ? 'border-[#ef4444] shadow-[0_0_0_3px_rgba(239,68,68,0.08)]' : 'border-[#e2e2ed] focus:border-[#10B981]'}`

const Field = ({ label, error, children, hint }) => (
  <div className="flex flex-col gap-1.5">
    <label className="text-xs text-[#6b6b80] uppercase tracking-wide" style={{ fontFamily: 'EuclidSB, sans-serif' }}>
      {label}
    </label>
    {children}
    {hint && !error && <span className="text-xs text-[#a0a0b0]">{hint}</span>}
    {error && (
      <span className="flex items-center gap-1 text-xs text-[#ef4444]">
        <AlertTriangle size={11} strokeWidth={2} /> {error}
      </span>
    )}
  </div>
)

const Section = ({ title, Icon, children }) => (
  <div className="bg-white border border-[#e2e2ed] rounded-2xl p-6 flex flex-col gap-5 shadow-sm">
    <h2 className="text-base text-[#0f0f1a] flex items-center gap-2.5" style={{ fontFamily: 'EuclidSB, sans-serif' }}>
      <div className="w-7 h-7 rounded-lg bg-[#10B981]/10 border border-[#10B981]/20 flex items-center justify-center flex-shrink-0">
        <Icon size={14} className="text-[#10B981]" strokeWidth={1.75} />
      </div>
      {title}
    </h2>
    {children}
  </div>
)

export default function Profile() {
  const dispatch = useAppDispatch()
  const navigate = useNavigate()
  const { user, loading } = useAuth()
  const fileRef = useRef()

  const [form, setForm] = useState({
    phone: user?.phone ?? '',
    github_id: user?.github_id ?? '',
    linkedin_id: user?.linkedin_id ?? '',
    portfolio_url: user?.portfolio_url ?? '',
    location: user?.location ?? '',
    bio: user?.bio ?? '',
    experience_type: user?.experience_type ?? 'fresher',
    years_of_experience: user?.years_of_experience ?? '',
    current_company: user?.current_company ?? '',
    current_role: user?.current_role ?? '',
    highest_education: user?.highest_education ?? '',
    college: user?.college ?? '',
    graduation_year: user?.graduation_year ?? '',
    skills: user?.skills ?? [],
  })

  const [skillInput, setSkillInput] = useState('')
  const [passwords, setPasswords] = useState({ current_password: '', new_password: '', confirm: '' })
  const [passErrors, setPassErrors] = useState({})
  const [successMsg, setSuccessMsg] = useState('')
  const [passSuccess, setPassSuccess] = useState('')
  const [sectionError, setSectionError] = useState({})

  // Naukri credentials state
  const [naukriEmail, setNaukriEmail] = useState('')
  const [naukriPassword, setNaukriPassword] = useState('')
  const [credSaved, setCredSaved] = useState(false)
  const [loadingCred, setLoadingCred] = useState(false)

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const flashSuccess = (setter, msg) => {
    setter(msg)
    setTimeout(() => setter(''), 3500)
  }

  // Fetch existing Naukri credentials on mount
  useEffect(() => {
    const fetchCredentials = async () => {
      try {
        const res = await api.get('/credentials/naukri')
        if (res.data.exists) {
          setNaukriEmail(res.data.email)
          setCredSaved(true)
        }
      } catch (err) {
        console.error('Failed to fetch credentials:', err)
      }
    }
    fetchCredentials()
  }, [])

  const addSkill = (e) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault()
      const s = skillInput.trim().replace(/,$/, '')
      if (s && !form.skills.includes(s)) set('skills', [...form.skills, s])
      setSkillInput('')
    }
  }
  const removeSkill = (s) => set('skills', form.skills.filter(x => x !== s))

  const handleSave = async (e) => {
    e.preventDefault()
    setSectionError(p => ({ ...p, profile: '' }))
    const payload = {
      phone: form.phone || null,
      github_id: form.github_id || null,
      linkedin_id: form.linkedin_id || null,
      portfolio_url: form.portfolio_url || null,
      location: form.location || null,
      bio: form.bio || null,
      experience_type: form.experience_type,
      years_of_experience: form.years_of_experience ? Number(form.years_of_experience) : null,
      current_company: form.current_company || null,
      current_role: form.current_role || null,
      highest_education: form.highest_education || null,
      college: form.college || null,
      graduation_year: form.graduation_year ? Number(form.graduation_year) : null,
      skills: form.skills,
    }
    const result = await dispatch(updateProfile(payload))
    if (updateProfile.fulfilled.match(result)) {
      flashSuccess(setSuccessMsg, 'Profile saved successfully!')
    } else {
      setSectionError(p => ({ ...p, profile: result.payload }))
    }
  }

  const handlePasswordChange = async (e) => {
    e.preventDefault()
    const errs = {}
    if (!passwords.current_password) errs.current_password = 'Required'
    if (passwords.new_password.length < 8) errs.new_password = 'Min 8 characters'
    if (passwords.new_password !== passwords.confirm) errs.confirm = 'Passwords do not match'
    setPassErrors(errs)
    if (Object.keys(errs).length) return

    const result = await dispatch(changePassword({
      current_password: passwords.current_password,
      new_password: passwords.new_password,
    }))
    if (changePassword.fulfilled.match(result)) {
      setPasswords({ current_password: '', new_password: '', confirm: '' })
      flashSuccess(setPassSuccess, 'Password changed successfully!')
    } else {
      setPassErrors({ api: result.payload })
    }
  }

  const handleResumeUpload = async (file) => {
    if (!file || file.type !== 'application/pdf') {
      setSectionError(p => ({ ...p, resume: 'Only PDF files are accepted.' }))
      return
    }
    setSectionError(p => ({ ...p, resume: '' }))
    const result = await dispatch(uploadResume(file))
    if (uploadResume.fulfilled.match(result)) {
      flashSuccess(setSuccessMsg, 'Resume updated!')
    } else {
      setSectionError(p => ({ ...p, resume: result.payload }))
    }
  }

  const handleResumeDelete = async () => {
    const result = await dispatch(deleteResume())
    if (!deleteResume.fulfilled.match(result)) {
      setSectionError(p => ({ ...p, resume: result.payload }))
    }
  }

  const handleLogout = async () => {
    await dispatch(logoutUser())
    navigate('/login')
  }

  const handleSaveCredentials = async (e) => {
    e.preventDefault()
    setLoadingCred(true)
    try {
      await api.post('/credentials/naukri', {
        platform: 'naukri',
        email: naukriEmail,
        password: naukriPassword
      })
      setCredSaved(true)
      flashSuccess(setSuccessMsg, 'Naukri credentials saved successfully!')
    } catch (err) {
      setSectionError(prev => ({ ...prev, cred: err.response?.data?.detail || 'Failed to save credentials' }))
    } finally {
      setLoadingCred(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#f5f5fa]" style={{ fontFamily: 'EuclidR, sans-serif' }}>

      <header className="sticky top-0 z-50 border-b border-[#e2e2ed] bg-white/90 backdrop-blur-md shadow-sm">
        <div className="max-w-7xl mx-auto px-6 flex items-center justify-between h-16">
          <Link to="/dashboard" className="flex items-center gap-2">
            <span className="text-xl text-[#0f0f1a]" style={{ fontFamily: 'EuclidB, sans-serif' }}>
              Carrer<span className="text-[#10B981]">Sync </span>
            </span>
          </Link>
          <div className="flex items-center gap-3">
            <Link to="/dashboard"
              className="flex items-center gap-1.5 text-sm text-[#6b6b80] hover:text-[#0f0f1a] transition-colors">
              <ArrowLeft size={15} strokeWidth={2} /> Dashboard
            </Link>
            <button onClick={handleLogout}
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm text-[#6b6b80] hover:text-[#ef4444] hover:bg-[#ef4444]/[0.06] border border-transparent hover:border-[#ef4444]/20 transition-all duration-200">
              <LogOut size={15} /> Log out
            </button>
          </div>
        </div>
      </header>

      <div className="max-w-3xl mx-auto px-6 py-12 flex flex-col gap-6">

        <div className="flex items-center gap-4 mb-2">
          <div className="w-16 h-16 rounded-full bg-[#10B981] flex items-center justify-center text-2xl text-white flex-shrink-0"
            style={{ fontFamily: 'EuclidB, sans-serif' }}>
            {user?.full_name?.[0]?.toUpperCase() ?? 'U'}
          </div>
          <div>
            <h1 className="text-2xl text-[#0f0f1a]" style={{ fontFamily: 'EuclidB, sans-serif' }}>
              {user?.full_name}
            </h1>
            <p className="text-sm text-[#6b6b80]">{user?.email}</p>
            <p className="text-xs text-[#a0a0b0] mt-0.5">
              Name and email cannot be changed — contact support if needed.
            </p>
          </div>
        </div>

        {successMsg && (
          <div className="px-4 py-3 bg-[#10B981]/[0.08] border border-[#10B981]/30 rounded-lg text-sm text-[#059669] flex items-center gap-2">
            <CheckCircle size={15} strokeWidth={2} className="flex-shrink-0" /> {successMsg}
          </div>
        )}

        <form onSubmit={handleSave} className="flex flex-col gap-6">
          <Section title="Contact & Social" Icon={Link2}>
            <div className="grid sm:grid-cols-2 gap-4">
              <Field label="Phone">
                <input type="tel" placeholder="e.g. 9876543210"
                  value={form.phone} onChange={e => set('phone', e.target.value)}
                  className={inputCls()} />
              </Field>
              <Field label="Location">
                <div className="relative">
                  <MapPin size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[#a0a0b0]" strokeWidth={1.75} />
                  <input type="text" placeholder="City, State"
                    value={form.location} onChange={e => set('location', e.target.value)}
                    className={inputCls() + ' pl-9'} />
                </div>
              </Field>
              <Field label="GitHub ID">
                <div className="relative">
                  <Github size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[#a0a0b0]" strokeWidth={1.75} />
                  <input type="text" placeholder="yourhandle"
                    value={form.github_id} onChange={e => set('github_id', e.target.value)}
                    className={inputCls() + ' pl-9'} />
                </div>
              </Field>
              <Field label="LinkedIn ID">
                <div className="relative">
                  <Linkedin size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[#a0a0b0]" strokeWidth={1.75} />
                  <input type="text" placeholder="yourprofile"
                    value={form.linkedin_id} onChange={e => set('linkedin_id', e.target.value)}
                    className={inputCls() + ' pl-9'} />
                </div>
              </Field>
              <Field label="Portfolio URL">
                <div className="relative sm:col-span-2">
                  <Globe size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[#a0a0b0]" strokeWidth={1.75} />
                  <input type="url" placeholder="https://yoursite.dev"
                    value={form.portfolio_url} onChange={e => set('portfolio_url', e.target.value)}
                    className={inputCls() + ' pl-9'} />
                </div>
              </Field>
            </div>
            <Field label="Bio">
              <textarea rows={3} placeholder="A short intro about you..."
                value={form.bio} onChange={e => set('bio', e.target.value)}
                className={inputCls() + ' resize-none'} />
            </Field>
          </Section>

          <Section title="Experience" Icon={Briefcase}>
            <div className="flex gap-3">
              {[
                { opt: 'fresher', label: 'Fresher' },
                { opt: 'experienced', label: 'Experienced' },
              ].map(({ opt, label }) => (
                <button key={opt} type="button" onClick={() => set('experience_type', opt)}
                  className={`flex-1 py-2.5 rounded-lg text-sm border transition-all duration-200
                    ${form.experience_type === opt
                      ? 'bg-[#10B981]/[0.08] border-[#10B981] text-[#059669] shadow-[0_0_12px_rgba(16,185,129,0.12)]'
                      : 'bg-white border-[#e2e2ed] text-[#6b6b80] hover:border-[#10B981]/50 hover:text-[#0f0f1a]'
                    }`}
                  style={{ fontFamily: 'EuclidSB, sans-serif' }}>
                  {label}
                </button>
              ))}
            </div>
            {form.experience_type === 'experienced' && (
              <div className="grid sm:grid-cols-2 gap-4">
                <Field label="Years of Experience">
                  <input type="number" min="0" max="50" placeholder="e.g. 2"
                    value={form.years_of_experience} onChange={e => set('years_of_experience', e.target.value)}
                    className={inputCls()} />
                </Field>
                <Field label="Current Company">
                  <input type="text" placeholder="Google, Infosys etc."
                    value={form.current_company} onChange={e => set('current_company', e.target.value)}
                    className={inputCls()} />
                </Field>
                <Field label="Current Role">
                  <input type="text" placeholder="Software Engineer"
                    value={form.current_role} onChange={e => set('current_role', e.target.value)}
                    className={inputCls()} />
                </Field>
              </div>
            )}
          </Section>

          <Section title="Education" Icon={GraduationCap}>
            <div className="grid sm:grid-cols-2 gap-4">
              <Field label="Highest Education">
                <input type="text" placeholder="B.Tech, MCA etc."
                  value={form.highest_education} onChange={e => set('highest_education', e.target.value)}
                  className={inputCls()} />
              </Field>
              <Field label="College / University">
                <input type="text" placeholder="College name"
                  value={form.college} onChange={e => set('college', e.target.value)}
                  className={inputCls()} />
              </Field>
              <Field label="Graduation Year">
                <input type="number" min="1990" max="2035" placeholder="e.g. 2026"
                  value={form.graduation_year} onChange={e => set('graduation_year', e.target.value)}
                  className={inputCls()} />
              </Field>
            </div>
          </Section>

          <Section title="Skills" Icon={Wrench}>
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
                placeholder={form.skills.length === 0 ? 'Type a skill and press Enter...' : ''}
                value={skillInput}
                onChange={e => setSkillInput(e.target.value)}
                onKeyDown={addSkill}
                className="flex-1 min-w-[160px] bg-transparent border-none outline-none text-sm text-[#0f0f1a] placeholder-[#a0a0b0]"
              />
            </div>
          </Section>

          {sectionError.profile && (
            <div className="px-4 py-3 bg-[#ef4444]/[0.07] border border-[#ef4444]/30 rounded-lg text-sm text-[#ef4444] flex items-center gap-2">
              <AlertTriangle size={15} strokeWidth={2} className="flex-shrink-0" /> {sectionError.profile}
            </div>
          )}

          <button type="submit" disabled={loading}
            className="self-end flex items-center gap-2 px-8 py-3 bg-[#10B981] text-white rounded-xl shadow-[0_4px_18px_rgba(16,185,129,0.25)] hover:bg-[#0ea572] hover:-translate-y-0.5 hover:shadow-[0_6px_24px_rgba(16,185,129,0.35)] transition-all duration-200 disabled:opacity-60 disabled:cursor-not-allowed disabled:transform-none text-sm"
            style={{ fontFamily: 'EuclidSB, sans-serif' }}>
            {loading
              ? <><Loader2 size={15} className="animate-spin" /> Saving...</>
              : <><Save size={15} strokeWidth={2} /> Save changes</>
            }
          </button>
        </form>

        <Section title="Resume" Icon={FileText}>
          {user?.resume_url ? (
            <div className="flex items-center justify-between gap-4 p-4 bg-[#f5f5fa] border border-[#e2e2ed] rounded-xl">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-[#10B981]/10 border border-[#10B981]/20 flex items-center justify-center flex-shrink-0">
                  <FileText size={18} className="text-[#10B981]" strokeWidth={1.75} />
                </div>
                <div>
                  <p className="text-sm text-[#0f0f1a]" style={{ fontFamily: 'EuclidSB, sans-serif' }}>Current resume</p>
                  <a href={`http://127.0.0.1:8000${user.resume_url}`} target="_blank" rel="noreferrer"
                    className="flex items-center gap-1 text-xs text-[#10B981] hover:text-[#059669] hover:underline transition-colors">
                    View PDF <ExternalLink size={11} strokeWidth={2} />
                  </a>
                </div>
              </div>
              <div className="flex gap-2">
                <button type="button" onClick={() => fileRef.current.click()}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#10B981]/[0.08] border border-[#10B981]/30 text-xs text-[#059669] hover:bg-[#10B981]/[0.14] transition-colors"
                  style={{ fontFamily: 'EuclidSB, sans-serif' }}>
                  <Upload size={12} strokeWidth={2} /> Replace
                </button>
                <button type="button" onClick={handleResumeDelete} disabled={loading}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#ef4444]/[0.07] border border-[#ef4444]/25 text-xs text-[#ef4444] hover:bg-[#ef4444]/[0.14] transition-colors disabled:opacity-50"
                  style={{ fontFamily: 'EuclidSB, sans-serif' }}>
                  <X size={12} strokeWidth={2.5} /> Remove
                </button>
              </div>
            </div>
          ) : (
            <button type="button" onClick={() => fileRef.current.click()}
              className="flex flex-col items-center gap-2 w-full py-8 border-2 border-dashed border-[#e2e2ed] rounded-xl text-[#a0a0b0] hover:border-[#10B981]/50 hover:text-[#059669] hover:bg-[#10B981]/[0.03] transition-all duration-200">
              <Upload size={24} strokeWidth={1.5} />
              <span className="text-sm" style={{ fontFamily: 'EuclidSB, sans-serif' }}>
                Upload resume (PDF, max 10 MB)
              </span>
            </button>
          )}
          <input type="file" accept=".pdf" ref={fileRef} className="hidden"
            onChange={e => { if (e.target.files[0]) handleResumeUpload(e.target.files[0]); e.target.value = '' }} />
          {sectionError.resume && (
            <p className="flex items-center gap-1 text-xs text-[#ef4444]">
              <AlertTriangle size={11} strokeWidth={2} /> {sectionError.resume}
            </p>
          )}
        </Section>

        {/* Naukri Credentials Section */}
        <Section title="Naukri Automation Credentials" Icon={Lock}>
          <form onSubmit={handleSaveCredentials} className="flex flex-col gap-4">
            <Field label="Naukri Email">
              <input type="email" placeholder="your.email@example.com"
                value={naukriEmail} onChange={e => setNaukriEmail(e.target.value)}
                className={inputCls()} />
            </Field>
            <Field label="Naukri Password">
              <input type="password" placeholder="Your Naukri password"
                value={naukriPassword} onChange={e => setNaukriPassword(e.target.value)}
                className={inputCls()} />
            </Field>
            {sectionError.cred && (
              <p className="flex items-center gap-1 text-xs text-[#ef4444]">
                <AlertTriangle size={11} strokeWidth={2} /> {sectionError.cred}
              </p>
            )}
            <button type="submit" disabled={loadingCred}
              className="self-start px-6 py-2.5 bg-[#10B981] text-white rounded-lg text-sm hover:bg-[#0ea572] transition-all disabled:opacity-60"
              style={{ fontFamily: 'EuclidSB, sans-serif' }}>
              {loadingCred ? 'Saving...' : 'Save Credentials'}
            </button>
            {credSaved && (
              <p className="text-xs text-[#059669] flex items-center gap-1">
                <CheckCircle size={12} /> Credentials saved
              </p>
            )}
          </form>
        </Section>

        <Section title="Change Password" Icon={Lock}>
          <form onSubmit={handlePasswordChange} className="flex flex-col gap-4">
            <Field label="Current Password" error={passErrors.current_password}>
              <input type="password" placeholder="Enter current password"
                value={passwords.current_password}
                onChange={e => setPasswords(p => ({ ...p, current_password: e.target.value }))}
                className={inputCls(passErrors.current_password)} />
            </Field>
            <Field label="New Password" error={passErrors.new_password}>
              <input type="password" placeholder="Min 8 characters"
                value={passwords.new_password}
                onChange={e => setPasswords(p => ({ ...p, new_password: e.target.value }))}
                className={inputCls(passErrors.new_password)} />
            </Field>
            <Field label="Confirm New Password" error={passErrors.confirm}>
              <input type="password" placeholder="Repeat new password"
                value={passwords.confirm}
                onChange={e => setPasswords(p => ({ ...p, confirm: e.target.value }))}
                className={inputCls(passErrors.confirm)} />
            </Field>
            {passErrors.api && (
              <p className="flex items-center gap-1.5 text-sm text-[#ef4444]">
                <AlertTriangle size={14} strokeWidth={2} /> {passErrors.api}
              </p>
            )}
            {passSuccess && (
              <p className="flex items-center gap-1.5 text-sm text-[#059669]">
                <CheckCircle size={14} strokeWidth={2} /> {passSuccess}
              </p>
            )}
            <button type="submit" disabled={loading}
              className="self-start flex items-center gap-2 px-6 py-2.5 bg-white border border-[#e2e2ed] text-sm text-[#0f0f1a] rounded-lg hover:border-[#10B981]/50 hover:text-[#059669] transition-all duration-200 disabled:opacity-60 shadow-sm"
              style={{ fontFamily: 'EuclidSB, sans-serif' }}>
              {loading
                ? <><Loader2 size={14} className="animate-spin" /> Updating...</>
                : 'Update password'
              }
            </button>
          </form>
        </Section>

        <Section title="Danger Zone" Icon={AlertTriangle}>
          <p className="text-sm text-[#6b6b80]">
            Deactivating your account will sign you out and prevent future logins.
            Your data is retained for 30 days before permanent deletion.
          </p>
          <Link to="/support"
            className="self-start text-sm text-[#ef4444] hover:underline transition-colors">
            Contact support to delete your account →
          </Link>
        </Section>

      </div>
    </div>
  )
}