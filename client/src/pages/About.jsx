import { Link } from 'react-router-dom'
import {
  Zap, ArrowLeft, Users, Target, Unlock, TrendingUp, Handshake,
  Github, Linkedin, ArrowRight, Heart,
} from 'lucide-react'

const TEAM = [
  {
    name: 'Divya Dubey',
    role: 'B.Tech IT — 3rd Year',
    avatar: 'DD',
    avatarBg: 'bg-[#6366f1]',
    bio: 'Frontend specialist focused on crafting delightful user experiences and accessible design systems.',
    links: { github: '#', linkedin: '#' },
  },
  {
    name: 'Ayush Gupta',
    role: 'B.Tech IT — 3rd Year',
    avatar: 'AG',
    avatarBg: 'bg-[#f59e0b]',
    bio: 'Backend and ML enthusiast with a knack for scalable systems and intelligent job-matching algorithms.',
    links: { github: '#', linkedin: '#' },
  },
  {
    name: 'Dibyanshu Yadav',
    role: 'B.Tech IT — 3rd Year',
    avatar: 'DY',
    avatarBg: 'bg-[#10B981]',
    bio: 'Full-stack developer passionate about AI-powered automation and building tools that save people time.',
    links: { github: '#', linkedin: '#' },
  },
]

const VALUES = [
  { Icon: Target, title: 'Student-first', desc: 'Built by students, for students — we know the job-hunt struggle first-hand.' },
  { Icon: Unlock, title: 'Open & honest', desc: 'No dark patterns. We are transparent about what data we collect and why.' },
  { Icon: TrendingUp, title: 'Move fast', desc: 'We ship improvements weekly and listen to every piece of feedback.' },
  { Icon: Handshake, title: 'Community driven', desc: 'Our Discord is where real users shape the roadmap.' },
]

export default function About() {
  return (
    <div className="min-h-screen bg-[#f5f5fa]" style={{ fontFamily: 'EuclidR, sans-serif' }}>

      {/* Navbar */}
      <header className="sticky top-0 z-50 border-b border-[#e2e2ed] bg-white/90 backdrop-blur-md shadow-sm">
        <div className="max-w-7xl mx-auto px-6 flex items-center justify-between h-16">
          <Link to="/dashboard" className="flex items-center gap-2">
            <span className="text-xl text-[#0f0f1a]" style={{ fontFamily: 'EuclidB, sans-serif' }}>
              AI Assisted:
              <span className="text-[#10B981]"> Job Application and Automation System</span>
            </span>
          </Link>
          <div className="flex items-center gap-4 text-sm">
            <Link to="/dashboard"
              className="flex items-center gap-1.5 text-[#6b6b80] hover:text-[#0f0f1a] transition-colors">
              <ArrowLeft size={15} strokeWidth={2} /> Dashboard
            </Link>
            <Link to="/support" className="text-[#6b6b80] hover:text-[#0f0f1a] transition-colors">
              Support
            </Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="relative px-6 pt-20 pb-16 text-center overflow-hidden">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[700px] h-[400px] bg-[#10B981]/[0.07] rounded-full blur-[120px] pointer-events-none" />
        <div className="relative max-w-2xl mx-auto">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-[#10B981]/[0.1] border border-[#10B981]/30 text-xs text-[#059669] mb-6"
            style={{ fontFamily: 'EuclidSB, sans-serif' }}>
            <Users size={13} strokeWidth={2} /> Meet the team
          </div>
          <h1 className="text-4xl sm:text-5xl text-[#0f0f1a] mb-5 leading-tight"
            style={{ fontFamily: 'EuclidB, sans-serif' }}>
            Built by students who hate{' '}
            <span className="text-[#10B981]">copy-pasting resumes</span>
          </h1>
          <p className="text-[#6b6b80] text-lg leading-relaxed max-w-xl mx-auto">
            We are three third-year IT students who got tired of spending hours
            applying to the same job 30 different ways. So we built ApplyAI to automate the grind.
          </p>
        </div>
      </section>

      {/* Team cards */}
      <section className="px-6 pb-24">
        <div className="max-w-5xl mx-auto grid sm:grid-cols-2 lg:grid-cols-3 gap-8">
          {TEAM.map(({ name, role, avatar, avatarBg, bio, links }) => (
            <div key={name}
              className="flex flex-col items-center text-center p-8 bg-white border border-[#e2e2ed] rounded-2xl hover:border-[#10B981]/50 hover:shadow-[0_4px_32px_rgba(16,185,129,0.09)] transition-all duration-300 group shadow-sm">
              <div className={`w-20 h-20 rounded-full ${avatarBg} flex items-center justify-center text-2xl text-white flex-shrink-0 mb-5 group-hover:scale-105 transition-transform duration-300`}
                style={{ fontFamily: 'EuclidB, sans-serif' }}>
                {avatar}
              </div>
              <h3 className="text-[#0f0f1a] text-lg mb-1" style={{ fontFamily: 'EuclidB, sans-serif' }}>
                {name}
              </h3>
              <span className="inline-block px-3 py-1 rounded-full bg-[#10B981]/10 border border-[#10B981]/25 text-xs text-[#059669] mb-4"
                style={{ fontFamily: 'EuclidSB, sans-serif' }}>
                {role}
              </span>
              <p className="text-sm text-[#6b6b80] leading-relaxed mb-6">{bio}</p>
              <div className="flex gap-3 mt-auto">
                <a href={links.github}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#f5f5fa] border border-[#e2e2ed] text-xs text-[#6b6b80] hover:border-[#10B981]/50 hover:text-[#059669] transition-all"
                  style={{ fontFamily: 'EuclidSB, sans-serif' }}>
                  <Github size={13} strokeWidth={1.75} /> GitHub
                </a>
                <a href={links.linkedin}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#f5f5fa] border border-[#e2e2ed] text-xs text-[#6b6b80] hover:border-[#10B981]/50 hover:text-[#059669] transition-all"
                  style={{ fontFamily: 'EuclidSB, sans-serif' }}>
                  <Linkedin size={13} strokeWidth={1.75} /> LinkedIn
                </a>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Origin story */}
      <section className="px-6 py-20 bg-white border-y border-[#e2e2ed]">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="text-3xl text-[#0f0f1a] mb-6" style={{ fontFamily: 'EuclidB, sans-serif' }}>
            Our story
          </h2>
          <p className="text-[#6b6b80] leading-relaxed text-base mb-4">
            It started during placement season. The three of us were spending 2–3 hours every day
            filling out the same forms on Naukri, Internshala and LinkedIn — same resume, same cover
            letter, same skills — just with different buttons to click.
          </p>
          <p className="text-[#6b6b80] leading-relaxed text-base mb-4">
            We thought:{' '}
            <span className="text-[#0f0f1a]" style={{ fontFamily: 'EuclidSB, sans-serif' }}>
              "There has to be a better way."
            </span>{' '}
            So we made one. ApplyAI started as a weekend hackathon project and grew into a full
            platform that scrapes jobs, scores them with AI, and auto-applies — all before breakfast.
          </p>
          <p className="text-[#6b6b80] leading-relaxed text-base">
            We are still students, still learning, and building this in our spare time. If you have
            feedback, ideas, or just want to say hi —&nbsp;
            <Link to="/support" className="text-[#10B981] hover:text-[#059669] hover:underline transition-colors">
              reach out anytime
            </Link>.
          </p>
        </div>
      </section>

      {/* Values */}
      <section className="px-6 py-20">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-2xl text-[#0f0f1a] mb-10 text-center" style={{ fontFamily: 'EuclidB, sans-serif' }}>
            What we stand for
          </h2>
          <div className="grid sm:grid-cols-2 gap-5">
            {VALUES.map(({ Icon, title, desc }) => (
              <div key={title}
                className="flex gap-4 p-6 bg-white border border-[#e2e2ed] rounded-2xl hover:border-[#10B981]/40 hover:shadow-[0_4px_20px_rgba(16,185,129,0.07)] transition-all duration-200 shadow-sm group">
                <div className="w-10 h-10 rounded-xl bg-[#10B981]/10 border border-[#10B981]/20 flex items-center justify-center flex-shrink-0 group-hover:bg-[#10B981]/15 transition-colors">
                  <Icon size={18} className="text-[#10B981]" strokeWidth={1.75} />
                </div>
                <div>
                  <h3 className="text-[#0f0f1a] mb-1" style={{ fontFamily: 'EuclidSB, sans-serif' }}>{title}</h3>
                  <p className="text-sm text-[#6b6b80]">{desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="px-6 pb-24 text-center">
        <div className="max-w-lg mx-auto bg-white border border-[#e2e2ed] rounded-3xl p-12 relative overflow-hidden shadow-sm">
          <div className="absolute -bottom-16 left-1/2 -translate-x-1/2 w-[300px] h-[150px] bg-[#10B981]/[0.06] rounded-full blur-[70px] pointer-events-none" />
          <div className="relative">
            <h2 className="text-2xl text-[#0f0f1a] mb-4" style={{ fontFamily: 'EuclidB, sans-serif' }}>
              Want to work with us?
            </h2>
            <p className="text-[#6b6b80] mb-6 text-sm">
              We're always looking for contributors, designers and ML enthusiasts to join the mission.
            </p>
            <Link to="/support"
              className="inline-flex items-center gap-2 px-6 py-3 bg-[#10B981] text-white rounded-xl shadow-[0_4px_18px_rgba(16,185,129,0.25)] hover:bg-[#0ea572] hover:-translate-y-0.5 hover:shadow-[0_6px_24px_rgba(16,185,129,0.35)] transition-all duration-200"
              style={{ fontFamily: 'EuclidSB, sans-serif' }}>
              Get in touch <ArrowRight size={15} strokeWidth={2} />
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-[#e2e2ed] bg-white py-6 px-6 text-center text-xs text-[#a0a0b0]">
        © 2026 ApplyAI · Made with{' '}
        <Heart size={11} className="inline text-[#ef4444] fill-[#ef4444] mx-0.5" strokeWidth={0} />{' '}
        by three IT students
      </footer>
    </div>
  )
}