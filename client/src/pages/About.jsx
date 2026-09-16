import { Link } from 'react-router-dom'
import {
  Users,
  Target,
  ShieldCheck,
  Sparkles,
  Search,
  BrainCircuit,
  Send,
  ArrowRight,
  Heart,
  CheckCircle2,
  BriefcaseBusiness,
  FileSearch,
  Zap,
} from 'lucide-react'

import { FaGithub, FaLinkedin } from 'react-icons/fa'

const TEAM = [
  {
    name: 'Divya Dubey',
    role: 'B.Tech IT — Final Year',
    avatar: 'DD',
    bio: 'Full-stack developer focused on building intuitive interfaces, job discovery workflows and intelligent matching experiences.',
    github: '#',
    linkedin: '#',
  },
  {
    name: 'Ayush Gupta',
    role: 'B.Tech IT — Final Year',
    avatar: 'AG',
    bio: 'Backend and ML enthusiast working on scalable services, automation pipelines and intelligent job-matching systems.',
    github: '#',
    linkedin: '#',
  },
  {
    name: 'Dibyanshu Yadav',
    role: 'B.Tech IT — Final Year',
    avatar: 'DY',
    bio: 'Full-stack developer passionate about automation and building practical tools that simplify repetitive workflows.',
    github: '#',
    linkedin: '#',
  },
]

const FEATURES = [
  {
    Icon: Search,
    title: 'Discover',
    desc: 'Jobs from multiple platforms are collected and organized in one place.',
  },
  {
    Icon: BrainCircuit,
    title: 'Match',
    desc: 'Semantic matching analyzes your profile and ranks jobs by relevance.',
  },
  {
    Icon: Send,
    title: 'Apply',
    desc: 'CareerSync helps reduce repetitive application work through automation.',
  },
]

const VALUES = [
  {
    Icon: Target,
    title: 'Candidate-first',
    desc: 'Designed around the actual problems students face while searching and applying for jobs.',
  },
  {
    Icon: ShieldCheck,
    title: 'Privacy conscious',
    desc: 'User information is handled carefully while keeping automation transparent and under user control.',
  },
  {
    Icon: Sparkles,
    title: 'Practical AI',
    desc: 'AI is used where it adds real value — understanding jobs, profiles and relevance.',
  },
  {
    Icon: Zap,
    title: 'Less repetitive work',
    desc: 'The goal is simple: spend less time filling forms and more time preparing for opportunities.',
  },
]

export default function About() {
  return (
    <div
      className="min-h-screen bg-[#f8fafc] text-[#111827]"
      style={{ fontFamily: 'EuclidR, sans-serif' }}
    >
      {/* HERO */}
      <section className="relative overflow-hidden px-6 pt-24 pb-24">
        {/* Background decorations */}
        <div className="absolute -top-32 left-1/2 h-[420px] w-[700px] -translate-x-1/2 rounded-full bg-emerald-200/30 blur-[120px]" />
        <div className="absolute top-32 -left-40 h-[350px] w-[350px] rounded-full bg-blue-200/20 blur-[100px]" />
        <div className="absolute top-10 -right-40 h-[350px] w-[350px] rounded-full bg-violet-200/20 blur-[100px]" />

        <div className="relative mx-auto max-w-5xl text-center">
          <div className="mb-7 inline-flex items-center gap-2 rounded-full border border-emerald-200 bg-white/80 px-4 py-2 text-[12px] font-semibold text-emerald-700 shadow-sm backdrop-blur">
            <Sparkles size={14} />
            Built to simplify your job search
          </div>

          <h1
            className="mx-auto max-w-4xl text-4xl font-bold leading-[1.12] tracking-tight text-[#111827] sm:text-5xl lg:text-6xl"
            style={{ fontFamily: 'EuclidB, sans-serif' }}
          >
            Job hunting shouldn't feel like
            <span className="block mt-2 bg-gradient-to-r from-emerald-500 to-teal-600 bg-clip-text text-transparent">
              a full-time job.
            </span>
          </h1>

          <p className="mx-auto mt-7 max-w-2xl text-[16px] leading-7 text-slate-500 sm:text-[17px]">
            CareerSync brings job discovery, intelligent matching and
            application assistance into one place — helping candidates focus
            on opportunities that actually matter.
          </p>

          <div className="mt-9 flex flex-wrap items-center justify-center gap-4">
            <Link
              to="/jobs"
              className="inline-flex items-center gap-2 rounded-xl bg-emerald-500 px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-emerald-500/20 transition-all hover:-translate-y-0.5 hover:bg-emerald-600"
            >
              <BriefcaseBusiness size={17} />
              Explore Jobs
            </Link>

            <Link
              to="/profile"
              className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-6 py-3 text-sm font-semibold text-slate-700 shadow-sm transition-all hover:-translate-y-0.5 hover:border-emerald-300 hover:text-emerald-700"
            >
              <FileSearch size={17} />
              View Profile
            </Link>
          </div>
        </div>
      </section>

      {/* HOW IT WORKS */}
      <section className="px-6 pb-24">
        <div className="mx-auto max-w-5xl">
          <div className="mb-10 text-center">
            <p className="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-emerald-600">
              One platform
            </p>

            <h2
              className="text-3xl font-bold text-slate-900"
              style={{ fontFamily: 'EuclidB, sans-serif' }}
            >
              From search to application
            </h2>

            <p className="mx-auto mt-3 max-w-xl text-sm leading-6 text-slate-500">
              CareerSync is designed to reduce the repetitive steps between
              finding a relevant job and applying for it.
            </p>
          </div>

          <div className="grid gap-5 md:grid-cols-3">
            {FEATURES.map(({ Icon, title, desc }, index) => (
              <div
                key={title}
                className="group relative overflow-hidden rounded-2xl border border-slate-200 bg-white p-7 shadow-sm transition-all duration-300 hover:-translate-y-1 hover:border-emerald-200 hover:shadow-xl hover:shadow-slate-200/60"
              >
                <span className="absolute right-5 top-4 text-5xl font-bold text-slate-50">
                  0{index + 1}
                </span>

                <div className="relative">
                  <div className="mb-5 flex h-12 w-12 items-center justify-center rounded-xl bg-emerald-50 text-emerald-600 transition-colors group-hover:bg-emerald-500 group-hover:text-white">
                    <Icon size={21} />
                  </div>

                  <h3 className="mb-2 text-lg font-semibold text-slate-900">
                    {title}
                  </h3>

                  <p className="text-sm leading-6 text-slate-500">
                    {desc}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* STORY */}
      <section className="border-y border-slate-200 bg-white px-6 py-24">
        <div className="mx-auto grid max-w-5xl items-center gap-14 lg:grid-cols-2">
          <div>
            <div className="mb-5 inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-600">
              <Heart size={21} />
            </div>

            <p className="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-emerald-600">
              Our story
            </p>

            <h2
              className="mb-6 text-3xl font-bold leading-tight text-slate-900 sm:text-4xl"
              style={{ fontFamily: 'EuclidB, sans-serif' }}
            >
              Born from a problem we faced ourselves.
            </h2>

            <p className="mb-4 text-[15px] leading-7 text-slate-500">
              During placement preparation, we realized how fragmented the job
              search process had become. Opportunities were spread across
              different platforms, while candidates repeatedly searched,
              compared and filled similar application forms.
            </p>

            <p className="text-[15px] leading-7 text-slate-500">
              CareerSync began with a simple idea: build one intelligent
              workflow that can discover opportunities, understand a
              candidate's profile, identify relevant jobs and reduce repetitive
              application work.
            </p>
          </div>

          {/* Story visual */}
          <div className="relative">
            <div className="rounded-3xl border border-slate-200 bg-[#f8fafc] p-7 shadow-sm">
              <div className="mb-6 flex items-center justify-between">
                <div>
                  <p className="text-xs text-slate-400">CareerSync</p>
                  <h3 className="mt-1 font-semibold text-slate-800">
                    Smarter job workflow
                  </h3>
                </div>

                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-500 text-white shadow-md shadow-emerald-500/20">
                  <Zap size={19} />
                </div>
              </div>

              <div className="space-y-3">
                {[
                  'Collect relevant job opportunities',
                  'Analyze candidate profile and resume',
                  'Rank jobs using semantic relevance',
                  'Assist with repetitive application steps',
                ].map((item) => (
                  <div
                    key={item}
                    className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white px-4 py-4"
                  >
                    <CheckCircle2
                      size={18}
                      className="flex-shrink-0 text-emerald-500"
                    />
                    <span className="text-sm text-slate-600">{item}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="absolute -bottom-5 -right-5 -z-10 h-full w-full rounded-3xl bg-emerald-100/50" />
          </div>
        </div>
      </section>

      {/* TEAM */}
      <section className="px-6 py-24">
        <div className="mx-auto max-w-5xl">
          <div className="mb-12 text-center">
            <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-4 py-1.5 text-xs font-semibold text-emerald-700">
              <Users size={14} />
              Meet the team
            </div>

            <h2
              className="text-3xl font-bold text-slate-900"
              style={{ fontFamily: 'EuclidB, sans-serif' }}
            >
              The people behind CareerSync
            </h2>

            <p className="mx-auto mt-3 max-w-xl text-sm leading-6 text-slate-500">
              A student team building a practical solution to make the
              job-search process simpler and smarter.
            </p>
          </div>

          <div className="grid gap-6 md:grid-cols-3">
            {TEAM.map(({ name, role, avatar, bio, github, linkedin }) => (
              <div
                key={name}
                className="group rounded-3xl border border-slate-200 bg-white p-7 shadow-sm transition-all duration-300 hover:-translate-y-1 hover:border-emerald-200 hover:shadow-xl hover:shadow-slate-200/60"
              >
                <div className="mb-6 flex items-center gap-4">
                  <div
                    className="flex h-14 w-14 flex-shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-emerald-400 to-teal-600 text-lg font-bold text-white shadow-lg shadow-emerald-500/15"
                    style={{ fontFamily: 'EuclidB, sans-serif' }}
                  >
                    {avatar}
                  </div>

                  <div>
                    <h3 className="font-semibold text-slate-900">
                      {name}
                    </h3>
                    <p className="mt-1 text-xs font-medium text-emerald-600">
                      {role}
                    </p>
                  </div>
                </div>

                <p className="min-h-[96px] text-sm leading-6 text-slate-500">
                  {bio}
                </p>

                <div className="mt-6 flex gap-3 border-t border-slate-100 pt-5">
                  <a
                    href={github}
                    target="_blank"
                    rel="noreferrer"
                    className="flex flex-1 items-center justify-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-xs font-semibold text-slate-600 transition hover:border-slate-300 hover:bg-white hover:text-slate-900"
                  >
                    <FaGithub size={15} />
                    GitHub
                  </a>

                  <a
                    href={linkedin}
                    target="_blank"
                    rel="noreferrer"
                    className="flex flex-1 items-center justify-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-xs font-semibold text-slate-600 transition hover:border-blue-200 hover:bg-blue-50 hover:text-blue-600"
                  >
                    <FaLinkedin size={15} />
                    LinkedIn
                  </a>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* VALUES */}
      <section className="border-y border-slate-200 bg-white px-6 py-24">
        <div className="mx-auto max-w-5xl">
          <div className="mb-12 text-center">
            <p className="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-emerald-600">
              Our approach
            </p>

            <h2
              className="text-3xl font-bold text-slate-900"
              style={{ fontFamily: 'EuclidB, sans-serif' }}
            >
              What CareerSync stands for
            </h2>
          </div>

          <div className="grid gap-5 sm:grid-cols-2">
            {VALUES.map(({ Icon, title, desc }) => (
              <div
                key={title}
                className="group flex gap-5 rounded-2xl border border-slate-200 bg-white p-6 transition-all duration-300 hover:border-emerald-200 hover:bg-emerald-50/20"
              >
                <div className="flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-xl bg-emerald-50 text-emerald-600 transition-colors group-hover:bg-emerald-500 group-hover:text-white">
                  <Icon size={19} />
                </div>

                <div>
                  <h3 className="mb-2 font-semibold text-slate-900">
                    {title}
                  </h3>

                  <p className="text-sm leading-6 text-slate-500">
                    {desc}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="px-6 py-24">
        <div className="relative mx-auto max-w-4xl overflow-hidden rounded-[32px] bg-slate-900 px-8 py-14 text-center shadow-2xl sm:px-16">
          <div className="absolute -left-20 -top-20 h-64 w-64 rounded-full bg-emerald-500/20 blur-[80px]" />
          <div className="absolute -bottom-24 -right-20 h-64 w-64 rounded-full bg-teal-400/10 blur-[80px]" />

          <div className="relative">
            <div className="mx-auto mb-5 flex h-12 w-12 items-center justify-center rounded-2xl bg-white/10 text-emerald-400">
              <BriefcaseBusiness size={21} />
            </div>

            <h2
              className="text-3xl font-bold text-white sm:text-4xl"
              style={{ fontFamily: 'EuclidB, sans-serif' }}
            >
              Find opportunities that fit you.
            </h2>

            <p className="mx-auto mt-4 max-w-xl text-sm leading-6 text-slate-400">
              Let CareerSync organize the search while you focus on building
              the skills that get you hired.
            </p>

            <Link
              to="/jobs"
              className="mt-8 inline-flex items-center gap-2 rounded-xl bg-emerald-500 px-6 py-3 text-sm font-semibold text-white transition-all hover:-translate-y-0.5 hover:bg-emerald-400"
            >
              Explore Jobs
              <ArrowRight size={16} />
            </Link>
          </div>
        </div>
      </section>

      {/* FOOTER */}
      <footer className="border-t border-slate-200 bg-white px-6 py-7">
        <div className="mx-auto flex max-w-5xl flex-col items-center justify-between gap-3 text-xs text-slate-400 sm:flex-row">
          <span className="font-semibold text-slate-500">
            CareerSync
          </span>

          <span>
            © 2026 CareerSync · Built by B.Tech IT students
          </span>
        </div>
      </footer>
    </div>
  )
}