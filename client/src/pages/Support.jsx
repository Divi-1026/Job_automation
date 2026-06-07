import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Zap, ArrowLeft, Mail, MessageSquare, Bug,
  ChevronDown, CheckCircle, Send, HelpCircle,
} from 'lucide-react'

const FAQS = [
  {
    q: 'How does ApplyAI find jobs for me?',
    a: 'ApplyAI scrapes listings from Naukri, Internshala, LinkedIn and other platforms daily. Our AI then scores each listing against your resume and skills profile to surface the most relevant matches.',
  },
  {
    q: 'Is my resume data safe?',
    a: 'Yes. Your resume is stored securely on our servers and is never shared with third parties. It is only used to match and tailor your applications.',
  },
  {
    q: 'How do I install the browser extension?',
    a: 'Visit the extension section on the dashboard and click "Add to Chrome" or "Add to Firefox". The extension only activates on supported job portals and never reads unrelated pages.',
  },
  {
    q: 'Can I edit or delete my account?',
    a: 'Yes. Go to your Profile page to update any information. To delete your account, reach out to us at support@applyai.dev and we will process it within 48 hours.',
  },
  {
    q: 'Why did an application fail to submit?',
    a: 'Some portals require CAPTCHA or phone-OTP verification which the extension cannot bypass. In those cases you will be notified to complete the step manually.',
  },
  {
    q: 'Is ApplyAI free?',
    a: 'The core features including job matching and the browser extension are free. Premium features like bulk auto-apply and resume tailoring will be available in a paid plan later.',
  },
]

const CONTACT_METHODS = [
  { Icon: Mail, label: 'Email us', value: 'support@applyai.dev', href: 'mailto:support@applyai.dev' },
  { Icon: MessageSquare, label: 'Discord community', value: 'discord.gg/applyai', href: '#' },
  { Icon: Bug, label: 'Report a bug', value: 'GitHub Issues', href: '#' },
]

const inputCls =
  `w-full px-4 py-3 rounded-lg bg-white border border-[#e2e2ed] text-[#0f0f1a] text-sm
   placeholder-[#a0a0b0] focus:outline-none focus:border-[#10B981]
   focus:shadow-[0_0_0_3px_rgba(16,185,129,0.12)] transition-all duration-200`

export default function Support() {
  const [open, setOpen] = useState(null)
  const [form, setForm] = useState({ name: '', email: '', message: '' })
  const [sent, setSent] = useState(false)

  const toggle = (i) => setOpen(open === i ? null : i)

  const handleSend = (e) => {
    e.preventDefault()
    setSent(true)
  }

  return (
    <div className="min-h-screen bg-[#f5f5fa]" style={{ fontFamily: 'EuclidR, sans-serif' }}>

      {/* Navbar */}
      <header className="sticky top-0 z-50 border-b border-[#e2e2ed] bg-white/90 backdrop-blur-md shadow-sm">
        <div className="max-w-7xl mx-auto px-6 flex items-center justify-between h-16">
          <Link to="/dashboard" className="flex items-center gap-2">
            <span className="text-xl text-[#0f0f1a]" style={{ fontFamily: 'EuclidB, sans-serif' }}>
              Career
              <span className="text-[#10B981]">Sync</span>
            </span>
          </Link>
          <div className="flex items-center gap-4 text-sm">
            <Link to="/dashboard"
              className="flex items-center gap-1.5 text-[#6b6b80] hover:text-[#0f0f1a] transition-colors">
              <ArrowLeft size={15} strokeWidth={2} /> Back to Dashboard
            </Link>
            <Link to="/about" className="text-[#6b6b80] hover:text-[#0f0f1a] transition-colors">
              About us
            </Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="relative px-6 pt-20 pb-16 text-center overflow-hidden">
        <div className="absolute inset-0 bg-[#10B981]/[0.04] pointer-events-none" />
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-[300px] bg-[#10B981]/[0.07] rounded-full blur-[100px] pointer-events-none" />
        <div className="relative max-w-2xl mx-auto">
          <div className="w-14 h-14 rounded-2xl bg-[#10B981]/10 border border-[#10B981]/20 flex items-center justify-center mx-auto mb-5">
            <HelpCircle size={26} className="text-[#10B981]" strokeWidth={1.75} />
          </div>
          <h1 className="text-4xl text-[#0f0f1a] mb-4" style={{ fontFamily: 'EuclidB, sans-serif' }}>
            How can we help?
          </h1>
          <p className="text-[#6b6b80] text-lg leading-relaxed">
            Browse the FAQs below or reach out directly — we usually respond within 24 hours.
          </p>
        </div>
      </section>

      {/* Contact methods */}
      <section className="px-6 pb-16">
        <div className="max-w-4xl mx-auto grid sm:grid-cols-3 gap-4">
          {CONTACT_METHODS.map(({ Icon, label, value, href }) => (
            <a key={label} href={href}
              className="flex flex-col items-center gap-3 p-6 bg-white border border-[#e2e2ed] rounded-2xl hover:border-[#10B981]/50 hover:shadow-[0_4px_24px_rgba(16,185,129,0.08)] transition-all duration-200 text-center group shadow-sm">
              <div className="w-11 h-11 rounded-xl bg-[#10B981]/10 border border-[#10B981]/20 flex items-center justify-center group-hover:bg-[#10B981]/15 transition-colors">
                <Icon size={20} className="text-[#10B981]" strokeWidth={1.75} />
              </div>
              <span className="text-[#0f0f1a] text-sm group-hover:text-[#059669] transition-colors"
                style={{ fontFamily: 'EuclidSB, sans-serif' }}>{label}</span>
              <span className="text-xs text-[#a0a0b0]">{value}</span>
            </a>
          ))}
        </div>
      </section>

      {/* FAQ */}
      <section className="px-6 pb-20">
        <div className="max-w-2xl mx-auto">
          <h2 className="text-2xl text-[#0f0f1a] mb-8 text-center" style={{ fontFamily: 'EuclidB, sans-serif' }}>
            Frequently asked questions
          </h2>
          <div className="flex flex-col gap-3">
            {FAQS.map((faq, i) => (
              <div key={i}
                className={`bg-white border rounded-xl overflow-hidden transition-all duration-200 shadow-sm ${open === i ? 'border-[#10B981]/50 shadow-[0_4px_20px_rgba(16,185,129,0.08)]' : 'border-[#e2e2ed]'
                  }`}>
                <button type="button" onClick={() => toggle(i)}
                  className="w-full flex items-center justify-between px-5 py-4 text-left text-sm text-[#0f0f1a] hover:text-[#059669] transition-colors"
                  style={{ fontFamily: 'EuclidSB, sans-serif' }}>
                  {faq.q}
                  <ChevronDown
                    size={16}
                    strokeWidth={2}
                    className={`text-[#a0a0b0] ml-4 flex-shrink-0 transition-transform duration-200 ${open === i ? 'rotate-180 text-[#10B981]' : ''
                      }`}
                  />
                </button>
                {open === i && (
                  <div className="px-5 pb-4 text-sm text-[#6b6b80] leading-relaxed border-t border-[#e8e8f0] pt-3">
                    {faq.a}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Contact form */}
      <section className="px-6 pb-24">
        <div className="max-w-xl mx-auto bg-white border border-[#e2e2ed] rounded-2xl p-8 shadow-sm">
          <h2 className="text-xl text-[#0f0f1a] mb-1" style={{ fontFamily: 'EuclidB, sans-serif' }}>
            Still need help?
          </h2>
          <p className="text-sm text-[#6b6b80] mb-6">Send us a message and we'll get back to you.</p>

          {sent ? (
            <div className="flex flex-col items-center gap-3 py-8 text-center">
              <div className="w-14 h-14 rounded-full bg-[#10B981]/10 border border-[#10B981]/20 flex items-center justify-center">
                <CheckCircle size={28} className="text-[#10B981]" strokeWidth={1.75} />
              </div>
              <p className="text-[#0f0f1a]" style={{ fontFamily: 'EuclidSB, sans-serif' }}>Message received!</p>
              <p className="text-sm text-[#6b6b80]">We'll reply to your email within 24 hours.</p>
            </div>
          ) : (
            <form onSubmit={handleSend} className="flex flex-col gap-4">
              <div className="flex flex-col gap-1.5">
                <label className="text-xs text-[#6b6b80] uppercase tracking-wide"
                  style={{ fontFamily: 'EuclidSB, sans-serif' }}>Name</label>
                <input required type="text" placeholder="Your name"
                  value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                  className={inputCls} />
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-xs text-[#6b6b80] uppercase tracking-wide"
                  style={{ fontFamily: 'EuclidSB, sans-serif' }}>Email</label>
                <input required type="email" placeholder="you@example.com"
                  value={form.email} onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
                  className={inputCls} />
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-xs text-[#6b6b80] uppercase tracking-wide"
                  style={{ fontFamily: 'EuclidSB, sans-serif' }}>Message</label>
                <textarea required rows={4} placeholder="Describe your issue or question..."
                  value={form.message} onChange={e => setForm(f => ({ ...f, message: e.target.value }))}
                  className={inputCls + ' resize-none'} />
              </div>
              <button type="submit"
                className="flex items-center justify-center gap-2 py-3 bg-[#10B981] text-white rounded-lg text-sm shadow-[0_4px_18px_rgba(16,185,129,0.25)] hover:bg-[#0ea572] hover:-translate-y-0.5 hover:shadow-[0_6px_24px_rgba(16,185,129,0.35)] transition-all duration-200"
                style={{ fontFamily: 'EuclidSB, sans-serif' }}>
                Send message <Send size={14} strokeWidth={2} />
              </button>
            </form>
          )}
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-[#e2e2ed] bg-white py-6 px-6 text-center text-xs text-[#a0a0b0]">
        © 2026 ApplyAI ·{' '}
        <Link to="/about" className="hover:text-[#10B981] transition-colors">Meet the team</Link>
      </footer>
    </div>
  )
}