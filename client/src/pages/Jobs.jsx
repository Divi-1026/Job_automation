import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useDispatch, useSelector } from 'react-redux'

import {
  fetchJobs,
  clearAutoApplyMsg,
  cancelAutoApply,
} from '../store/jobsSlice'

import { logoutUser } from '../store/authSlice'
import { useAuth } from '../store/hooks'
import api from '../api/axiosInstance'

import {
  Zap,
  ArrowLeft,
  User,
  LogOut,
  Building2,
  MapPin,
  DollarSign,
  ExternalLink,
  Bot,
  RefreshCw,
  Loader2,
  CheckCircle,
  AlertTriangle,
  Search,
  Briefcase,
  Layers,
  X,
  SlidersHorizontal,
} from 'lucide-react'


const SOURCES = [
  {
    key: 'all',
    label: 'All Jobs',
    Icon: Layers,
  },
  {
    key: 'naukri',
    label: 'Naukri',
    Icon: Briefcase,
  },
  {
    key: 'indeed',
    label: 'Indeed',
    Icon: Search,
  },
  {
    key: 'internshala',
    label: 'Internshala',
    Icon: Bot,
  },
]


const SOURCE_STYLES = {
  naukri:
    'bg-[#f59e0b]/10 border-[#f59e0b]/30 text-[#d97706]',

  internshala:
    'bg-[#3b82f6]/10 border-[#3b82f6]/30 text-[#2563eb]',

  indeed:
    'bg-[#10B981]/10 border-[#10B981]/30 text-[#059669]',
}


// ---------------------------------------------------------
// Match badge
// ---------------------------------------------------------

function MatchBadge({ score }) {

  if (score === undefined || score === null) {
    return null
  }

  let style =
    'bg-[#f5f5fa] border-[#e2e2ed] text-[#6b6b80]'

  if (score >= 75) {
    style =
      'bg-green-50 border-green-200 text-green-700'
  }
  else if (score >= 50) {
    style =
      'bg-yellow-50 border-yellow-200 text-yellow-700'
  }
  else if (score >= 30) {
    style =
      'bg-orange-50 border-orange-200 text-orange-700'
  }

  return (
    <span
      className={`
        shrink-0
        text-xs
        px-2.5
        py-1
        rounded-full
        border
        ${style}
      `}
      style={{
        fontFamily: 'EuclidSB, sans-serif'
      }}
    >
      {Number(score).toFixed(1)}% Match
    </span>
  )
}


// ---------------------------------------------------------
// Job Card
// ---------------------------------------------------------

function JobCard({ job }) {

  const [showDetails, setShowDetails] = useState(false)

  const sourceCls =
    SOURCE_STYLES[job.source] ||
    SOURCE_STYLES.indeed

  const experienceText = getExperienceDisplay(job)

  const detectedJobType = getJobType(job)

  return (
    <>
      <div
        className="
          bg-white
          border
          border-[#e2e2ed]
          rounded-2xl
          p-5
          flex
          flex-col
          gap-3
          hover:border-[#10B981]/50
          hover:-translate-y-0.5
          hover:shadow-[0_4px_24px_rgba(16,185,129,0.08)]
          transition-all
          duration-200
          shadow-sm
          w-full
        "
      >

        {/* Title + Score + Source */}
        <div className="flex items-start justify-between gap-3">

          <h3
            className="text-[17px] text-semibold text-[#0f0f1a] leading-snug flex-1"
            style={{ fontFamily: 'EuclidSB, sans-serif' }}
          >
            {job.title}
          </h3>

          <div className="flex items-center gap-2 flex-wrap justify-end">
            <MatchBadge
              score={
                job.confidence_score ??
                job.match_score
              }
            />

            <span
              className={`
                shrink-0
                text-xs
                px-2
                py-0.5
                rounded-full
                border
                capitalize
                ${sourceCls}
              `}
              style={{ fontFamily: 'EuclidSB, sans-serif' }}
            >
              {job.source}
            </span>
          </div>

        </div>

        {/* Company / location / salary / experience / job type */}
        <div className="flex flex-wrap gap-x-4 gap-y-2 text-sm text-[#393941]">

          {job.company && (
            <span className="flex items-center gap-1.5">
              <Building2
                size={16}
                strokeWidth={2}
                className="text-[#0f7434]"
              />
              {job.company}
            </span>
          )}

          {job.location && (
            <span className="flex text-[15px] items-center gap-1.5">
              <MapPin
                size={16}
                strokeWidth={2}
                className="text-[#c11313]"
              />
              {job.location}
            </span>
          )}

          {job.salary && (
            <span className="flex items-center gap-1.5">
              <DollarSign
                size={13}
                strokeWidth={1.75}
                className="text-[#a0a0b0]"
              />
              {job.salary}
            </span>
          )}

          {experienceText && (
            <span className="flex items-center gap-1.5 text-[15px]">
              <Briefcase
                size={15}
                strokeWidth={2}
                className="text-[#693408]"
              />
              {experienceText}
            </span>
          )}

          {detectedJobType !== 'unknown' && (
            <span
              className="
                text-xs
                px-2.5
                py-0.5
                rounded-full
                bg-[#f5f5fa]
                border
                border-[#e2e2ed]
                text-[#6b6b80]
                capitalize
              "
              style={{ fontFamily: 'EuclidSB, sans-serif' }}
            >
              {detectedJobType === 'internship' ? 'Internship' : 'Full-time'}
            </span>
          )}

        </div>

        {/* Short description only. No skill_query badge on normal cards. */}
        {job.description && (
          <p className="text-sm text-[#8a8a9d] line-clamp-2 leading-relaxed">
            {job.description}
          </p>
        )}

        {job.applied && (
          <span
            className="
              self-start
              text-xs
              px-2.5
              py-0.5
              rounded-full
              bg-green-100
              border
              border-green-300
              text-green-700
            "
          >
            Applied
          </span>
        )}

        {/* Actions */}
        <div className="mt-auto flex items-center gap-2 flex-wrap pt-1">

          <button
            type="button"
            onClick={() => setShowDetails(true)}
            className="
              flex
              items-center
              gap-1.5
              px-4
              py-2
              rounded-lg
              bg-white
              border
              border-[#2f2fbc]
              text-sm
              text-[#0f0f1a]
              hover:border-[#2f2fbc]/50
              hover:bg-[#10B981]/[0.04]
              transition-colors
            "
            style={{ fontFamily: 'EuclidSB, sans-serif' }}
          >
            Details
          </button>

          {job.url ? (
            <a
              href={job.url}
              target="_blank"
              rel="noreferrer"
              className="
                flex
                items-center
                gap-1.5
                px-4
                py-2
                rounded-lg
                bg-[#10B981]/[0.08]
                border
                border-[#10B981]/30
                text-sm
                text-[#059669]
                hover:bg-[#10B981]/[0.15]
                transition-colors
              "
              style={{ fontFamily: 'EuclidSB, sans-serif' }}
            >
              View Job
              <ExternalLink size={11} strokeWidth={2} />
            </a>
          ) : (
            <span
              className="
                px-4
                py-2
                rounded-lg
                bg-[#f5f5fa]
                border
                border-[#e2e2ed]
                text-xs
                text-[#a0a0b0]
              "
            >
              No link available
            </span>
          )}

        </div>
      </div>

      {/* Job Details Modal */}
      {showDetails && (
        <div
          className="
            fixed
            inset-0
            z-[100]
            bg-black/40
            backdrop-blur-sm
            flex
            items-center
            justify-center
            p-4
          "
          onClick={() => setShowDetails(false)}
        >
          <div
            className="
              w-full
              max-w-3xl
              max-h-[85vh]
              overflow-y-auto
              bg-white
              rounded-2xl
              border
              border-[#e2e2ed]
              shadow-2xl
              p-6
            "
            onClick={e => e.stopPropagation()}
          >

            <div className="flex items-start justify-between gap-4 mb-5">
              <div>
                <h2
                  className="text-xl text-[#0f0f1a]"
                  style={{ fontFamily: 'EuclidB, sans-serif' }}
                >
                  {job.title}
                </h2>

                {job.company && (
                  <p className="text-sm text-[#6b6b80] mt-1">
                    {job.company}
                  </p>
                )}
              </div>

              <button
                type="button"
                onClick={() => setShowDetails(false)}
                className="
                  p-2
                  rounded-lg
                  text-[#6b6b80]
                  hover:text-[#0f0f1a]
                  hover:bg-[#f5f5fa]
                  transition-colors
                "
                aria-label="Close job details"
              >
                <X size={18} />
              </button>
            </div>

            <div className="flex flex-wrap gap-2 mb-5">
              {job.source && (
                <span className={`text-xs px-2.5 py-1 rounded-full border capitalize ${sourceCls}`}>
                  {job.source}
                </span>
              )}

              {detectedJobType !== 'unknown' && (
                <span className="text-xs px-2.5 py-1 rounded-full border border-[#e2e2ed] bg-[#f5f5fa] text-[#6b6b80]">
                  {detectedJobType === 'internship' ? 'Internship' : 'Full-time'}
                </span>
              )}

              <MatchBadge
                score={job.confidence_score ?? job.match_score}
              />
            </div>

            <div className="grid sm:grid-cols-2 gap-3 mb-6 text-sm">
              {job.location && (
                <div className="rounded-xl bg-[#f8f8fb] border border-[#ededf3] p-3">
                  <span className="text-xs text-[#8a8a9d] block mb-1">Location</span>
                  <span className="text-[#0f0f1a]">{job.location}</span>
                </div>
              )}

              {job.salary && (
                <div className="rounded-xl bg-[#f8f8fb] border border-[#ededf3] p-3">
                  <span className="text-xs text-[#8a8a9d] block mb-1">Salary</span>
                  <span className="text-[#0f0f1a]">{job.salary}</span>
                </div>
              )}

              {experienceText && (
                <div className="rounded-xl bg-[#f8f8fb] border border-[#ededf3] p-3">
                  <span className="text-xs text-[#8a8a9d] block mb-1">Experience</span>
                  <span className="text-[#0f0f1a]">{experienceText}</span>
                </div>
              )}

              {job.skill_query && (
                <div className="rounded-xl bg-[#f8f8fb] border border-[#ededf3] p-3">
                  <span className="text-xs text-[#8a8a9d] block mb-1">Matched Role / Skill</span>
                  <span className="text-[#0f0f1a]">{job.skill_query}</span>
                </div>
              )}
            </div>

            <div>
              <h3
                className="text-sm text-[#0f0f1a] mb-2"
                style={{ fontFamily: 'EuclidSB, sans-serif' }}
              >
                Job Description
              </h3>

              <div
                className="
                  whitespace-pre-wrap
                  break-words
                  text-sm
                  leading-6
                  text-[#5f5f72]
                  bg-[#fafafd]
                  border
                  border-[#ededf3]
                  rounded-xl
                  p-4
                "
              >
                {job.description || 'No detailed description available.'}
              </div>
            </div>

            <div className="mt-6 flex items-center justify-end gap-2 flex-wrap">
              <button
                type="button"
                onClick={() => setShowDetails(false)}
                className="px-4 py-2 rounded-lg border border-[#e2e2ed] text-sm text-[#6b6b80] hover:text-[#0f0f1a]"
              >
                Close
              </button>

              {job.url && (
                <a
                  href={job.url}
                  target="_blank"
                  rel="noreferrer"
                  className="
                    flex
                    items-center
                    gap-1.5
                    px-4
                    py-2
                    rounded-lg
                    bg-[#10B981]
                    text-white
                    text-sm
                    hover:bg-[#0ea572]
                    transition-colors
                  "
                  style={{ fontFamily: 'EuclidSB, sans-serif' }}
                >
                  View Job
                  <ExternalLink size={13} />
                </a>
              )}
            </div>

          </div>
        </div>
      )}
    </>
  )
}


// ---------------------------------------------------------
// Empty State
// ---------------------------------------------------------

function EmptyState({ hasResume }) {

  return (
    <div
      className="
        flex
        flex-col
        items-center
        gap-6
        py-24
        text-center
      "
    >

      <div
        className="
          w-20
          h-20
          rounded-2xl
          bg-[#10B981]/10
          border
          border-[#10B981]/20
          flex
          items-center
          justify-center
        "
      >
        <Search
          size={36}
          className="text-[#10B981]"
          strokeWidth={1.5}
        />
      </div>


      <div>

        <h3
          className="
            text-xl
            text-[#0f0f1a]
            mb-2
          "
          style={{
            fontFamily: 'EuclidB, sans-serif'
          }}
        >
          {
            hasResume
              ? 'No matching jobs found'
              : 'Upload your resume first'
          }
        </h3>


        <p
          className="
            text-sm
            text-[#6b6b80]
            max-w-md
          "
        >
          {
            hasResume
              ? 'Fresh jobs are added automatically. Try refreshing results or updating your profile.'
              : 'Upload your resume in Profile so CareerSync can rank global jobs according to your experience and skills.'
          }
        </p>

      </div>


      {!hasResume && (

        <Link
          to="/profile"
          className="
            px-5
            py-2.5
            rounded-xl
            bg-[#10B981]
            text-white
            text-sm
            hover:bg-[#0ea572]
            transition-colors
          "
          style={{
            fontFamily: 'EuclidSB, sans-serif'
          }}
        >
          Upload Resume
        </Link>

      )}

    </div>
  )
}



// ---------------------------------------------------------
// Filter helpers
// ---------------------------------------------------------

// ---------------------------------------------------------
// Job type / experience helpers
// ---------------------------------------------------------

function getJobType(job) {
  const explicit = String(
    job.job_type ||
    job.employment_type ||
    job.type ||
    ''
  ).toLowerCase()

  const combined = [
    explicit,
    job.title,
    job.description,
  ]
    .filter(Boolean)
    .join(' ')
    .toLowerCase()

  if (
    /\bintern(ship)?\b|\btrainee\b/.test(combined)
  ) {
    return 'internship'
  }

  if (
    /\bfull[ -]?time\b|\bpermanent\b/.test(combined)
  ) {
    return 'full_time'
  }

  // Normal Naukri/Indeed jobs are generally full-time unless marked as internships.
  if (job.source === 'naukri' || job.source === 'indeed') {
    return 'full_time'
  }

  return 'unknown'
}


function parseExperienceRange(text) {
  if (!text) return null

  const value = String(text)
    .replace(/\u2013|\u2014/g, '-')
    .trim()

  if (!value) return null

  if (/\b(?:no\s+fixed\s+duration|not\s+specified|not\s+mentioned|na|n\/a)\b/i.test(value)) {
    return null
  }

  if (/\bfresher(?:s)?\b|\bno\s+experience\b/i.test(value)) {
    return { min: 0, max: 0, raw: 'Fresher' }
  }

  // 0-4, 0 - 4 years, 5 to 10 yrs, 3–7 etc.
  const rangeMatch = value.match(
    /\b(\d+(?:\.\d+)?)\s*(?:-|to)\s*(\d+(?:\.\d+)?)\s*(?:\+?\s*(?:years?|yrs?))?/i
  )

  if (rangeMatch) {
    const a = Number(rangeMatch[1])
    const b = Number(rangeMatch[2])

    if (Number.isFinite(a) && Number.isFinite(b)) {
      const min = Math.min(a, b)
      const max = Math.max(a, b)
      return {
        min,
        max,
        raw: `${min}-${max} years`,
      }
    }
  }

  // 6+ years / minimum 2 years / 2 years experience.
  const plusMatch = value.match(
    /\b(\d+(?:\.\d+)?)\s*\+\s*(?:years?|yrs?)?/i
  )

  if (plusMatch) {
    const min = Number(plusMatch[1])
    if (Number.isFinite(min)) {
      return { min, max: Infinity, raw: `${min}+ years` }
    }
  }

  const singleMatch = value.match(
    /\b(\d+(?:\.\d+)?)\s*(?:years?|yrs?)\b/i
  )

  if (singleMatch) {
    const years = Number(singleMatch[1])
    if (Number.isFinite(years)) {
      return { min: years, max: years, raw: `${years} years` }
    }
  }

  return null
}


function getExperienceYears(job) {
  // 1) Prefer explicit/structured fields if backend ever starts returning them.
  const explicitValues = [
    job.required_experience,
    job.experience_required,
    job.experience_range,
    job.experience,
  ]

  for (const value of explicitValues) {
    const parsed = parseExperienceRange(value)
    if (parsed) return parsed
  }

  const description = String(job.description || '')
  const title = String(job.title || '')

  // 2) CareerSync's Naukri descriptions already contain this normalized marker.
  //    Example: "Required Experience: 0-4"
  const requiredMatch = description.match(
    /Required\s+Experience\s*:\s*([^\n\r|]+)/i
  )

  if (requiredMatch) {
    const parsed = parseExperienceRange(requiredMatch[1])
    if (parsed) return parsed
  }

  // 3) Common JD formats used by Internshala / other sources.
  //    Examples: "Experience Range: 5 to 10 Years", "Experience: 4 to 10 years"
  const labelledPatterns = [
    /Experience\s+Range\s*:\s*([^\n\r|]+)/i,
    /Total\s+Experience\s*:\s*([^\n\r|]+)/i,
    /Experience\s*:\s*([^\n\r|]+)/i,
    /Minimum\s+(?:of\s+)?(\d+(?:\.\d+)?\s*(?:-|to)\s*\d+(?:\.\d+)?\s*(?:years?|yrs?))/i,
    /Minimum\s+(?:of\s+)?(\d+(?:\.\d+)?\s*\+?\s*(?:years?|yrs?))/i,
  ]

  for (const pattern of labelledPatterns) {
    const match = description.match(pattern)
    if (match) {
      const parsed = parseExperienceRange(match[1])
      if (parsed) return parsed
    }
  }

  // 4) Last fallback: scan title + description only when no labelled experience exists.
  //    This is intentionally last so unrelated numeric ranges do not override
  //    "Required Experience".
  const combined = `${title} | ${description}`

  const genericRange = combined.match(
    /\b(\d+(?:\.\d+)?)\s*(?:-|\u2013|\u2014|to)\s*(\d+(?:\.\d+)?)\s*(?:years?|yrs?)\b/i
  )

  if (genericRange) {
    return parseExperienceRange(genericRange[0])
  }

  const genericPlus = combined.match(
    /\b(\d+(?:\.\d+)?)\s*\+\s*(?:years?|yrs?)\b/i
  )

  if (genericPlus) {
    return parseExperienceRange(genericPlus[0])
  }

  if (/\bfresher(?:s)?\b|\bno\s+experience\b/i.test(combined)) {
    return { min: 0, max: 0, raw: 'Fresher' }
  }

  return null
}


function getExperienceDisplay(job) {
  const range = getExperienceYears(job)
  if (!range) return ''
  return range.raw
}


function matchesExperienceFilter(job, filter) {
  if (filter === 'all') return true

  const range = getExperienceYears(job)
  if (!range) return false

  // Experience filter is based on the MINIMUM experience required by the job.
  // Example: "Required Experience: 0-4" means minimum required experience is 0,
  // so it belongs to the 0-1 bucket — NOT the 3-5 bucket merely because 4 overlaps.
  const minRequired = Number(range.min)

  if (!Number.isFinite(minRequired)) return false

  if (filter === 'fresher') {
    return minRequired >= 0 && minRequired < 1
  }

  if (filter === '1-3') {
    return minRequired >= 1 && minRequired < 3
  }

  if (filter === '3-5') {
    return minRequired >= 3 && minRequired < 5
  }

  if (filter === '5+') {
    return minRequired >= 5
  }

  return true
}


function salaryToMonthlyMinimum(salaryText) {
  if (!salaryText) return null

  const text = String(salaryText)
    .toLowerCase()
    .replace(/,/g, '')
    .replace(/₹/g, ' rs ')

  if (
    text.includes('not disclosed') ||
    text.includes('not specified') ||
    text.includes('undisclosed') ||
    text.includes('negotiable')
  ) {
    return null
  }

  const numericValues = [
    ...text.matchAll(/(\d+(?:\.\d+)?)/g)
  ].map(match => Number(match[1]))
    .filter(value => Number.isFinite(value))

  if (!numericValues.length) return null

  const firstTwo = numericValues.slice(0, 2)
  let minimum = Math.min(...firstTwo)

  const isAnnualLakh =
    /\b(lpa|lac|lacs|lakh|lakhs)\b/.test(text) ||
    /per\s*annum|p\.?\s*a\.?|annum/.test(text)

  const isMonthly =
    /per\s*month|monthly|\/\s*month|\/\s*mo\b/.test(text)

  if (/\bcrore|crores|cr\b/.test(text)) {
    return (minimum * 10000000) / 12
  }

  if (isAnnualLakh) {
    // Naukri commonly shows ranges such as "3-5 Lacs P.A."
    // If the value already looks like an absolute annual amount,
    // do not multiply by one lakh again.
    if (minimum >= 10000) {
      return minimum / 12
    }
    return (minimum * 100000) / 12
  }

  if (isMonthly) {
    const hasK =
      /\d+(?:\.\d+)?\s*k\b/.test(text)

    if (hasK && minimum < 1000) {
      return minimum * 1000
    }

    return minimum
  }

  // A raw value such as 300000 is most likely annual salary.
  if (minimum >= 100000) {
    return minimum / 12
  }

  // Without a trustworthy unit, do not use the value for a strict filter.
  return null
}


function requestedMinimumMonthly(value, unit) {
  const numeric = Number(value)

  if (!Number.isFinite(numeric) || numeric <= 0) {
    return null
  }

  return unit === 'lpa'
    ? (numeric * 100000) / 12
    : numeric
}


// ---------------------------------------------------------
// Main Jobs Page
// ---------------------------------------------------------

export default function Jobs() {

  const dispatch = useDispatch()

  const navigate = useNavigate()

  const { user } = useAuth()


  const {
    items,
    loading,
    error,
    autoApplying,
    autoApplyMsg,
    cancelling,
  } = useSelector(
    state => state.jobs
  )


  const [activeSource, setActiveSource] =
    useState('all')

  const [
    checkingCreds,
    setCheckingCreds
  ] = useState(false)

  const [
    notEligibleJobs,
    setNotEligibleJobs
  ] = useState([])

  const [
    reviewJobs,
    setReviewJobs
  ] = useState([])

  // Show eligibility failures only for 1 minute after the CURRENT auto-apply run.
  // They stay permanently saved in Application History on the backend.
  const [showEligibilityResults, setShowEligibilityResults] =
    useState(false)

  const eligibilityTimerRef = useRef(null)

  const showEligibilityResultsForOneMinute = () => {
    setShowEligibilityResults(true)

    if (eligibilityTimerRef.current) {
      clearTimeout(eligibilityTimerRef.current)
    }

    eligibilityTimerRef.current = setTimeout(() => {
      setShowEligibilityResults(false)
      eligibilityTimerRef.current = null
    }, 60 * 1000)
  }


  const [maxApplies, setMaxApplies] =
    useState(5)

  const [minSalary, setMinSalary] =
    useState('')

  const [salaryUnit, setSalaryUnit] =
    useState('lpa')

  const [locationFilter, setLocationFilter] =
    useState('')

  const [minMatch, setMinMatch] =
    useState('')

  const [searchFilter, setSearchFilter] =
    useState('')

  const [experienceFilter, setExperienceFilter] =
    useState('all')

  const [jobTypeFilter, setJobTypeFilter] =
    useState('all')

  const [
    localAutoApplying,
    setLocalAutoApplying
  ] = useState(false)

  const [
    localAutoApplyMsg,
    setLocalAutoApplyMsg
  ] = useState('')

  const [
    filterError,
    setFilterError
  ] = useState('')


  // -------------------------------------------------------
  // Eligibility result history
  // -------------------------------------------------------

  const fetchEligibilityResults = async () => {

    try {

      const [
        notEligibleRes,
        reviewRes
      ] = await Promise.all([
        api.get(
          '/jobs/applications?status=not_eligible'
        ),
        api.get(
          '/jobs/applications?status=needs_review'
        ),
      ])

      setNotEligibleJobs(
        notEligibleRes.data?.applications || []
      )

      setReviewJobs(
        reviewRes.data?.applications || []
      )

    }
    catch (err) {

      console.error(
        'Failed to fetch eligibility results',
        err
      )

    }

  }


  // -------------------------------------------------------
  // Fetch GLOBAL DB jobs
  // -------------------------------------------------------

  useEffect(() => {

    dispatch(fetchJobs())

  }, [dispatch])




  // -------------------------------------------------------
  // Refresh recommendations
  // DOES NOT scrape
  // -------------------------------------------------------

  const handleRefresh = () => {

    dispatch(fetchJobs())

  }


  // -------------------------------------------------------
  // Auto Apply
  // -------------------------------------------------------

  const checkAndAutoApply = async (platform = 'naukri') => {

    console.log(`[CareerSync] Auto Apply clicked: ${platform}`)

    const requested = Number(maxApplies)

    if (
      !Number.isInteger(requested) ||
      requested < 1 ||
      requested > 20
    ) {
      setFilterError(
        'Number of jobs must be between 1 and 20.'
      )
      return
    }

    if (
      minSalary !== '' &&
      (
        !Number.isFinite(Number(minSalary)) ||
        Number(minSalary) < 0
      )
    ) {
      setFilterError(
        'Minimum salary must be a valid positive number.'
      )
      return
    }

    if (
      minMatch !== '' &&
      (
        !Number.isFinite(Number(minMatch)) ||
        Number(minMatch) < 0 ||
        Number(minMatch) > 100
      )
    ) {
      setFilterError(
        'Minimum match score must be between 0 and 100.'
      )
      return
    }

    setFilterError('')
    setCheckingCreds(true)
    setLocalAutoApplyMsg('')
    setShowEligibilityResults(false)

    if (eligibilityTimerRef.current) {
      clearTimeout(eligibilityTimerRef.current)
      eligibilityTimerRef.current = null
    }

    try {

      const res =
        await api.get(
          `/credentials/${platform}`
        )

      if (!res.data.exists) {
        navigate(
          platform === 'internshala'
            ? '/profile#internshala-credentials'
            : '/profile#naukri-credentials'
        )
        return
      }

      dispatch(
        clearAutoApplyMsg()
      )

      const params =
        new URLSearchParams()

      params.set(
        'max_applies',
        String(requested)
      )

      if (
        minSalary !== '' &&
        Number(minSalary) > 0
      ) {
        params.set(
          'min_salary_value',
          String(Number(minSalary))
        )
        params.set(
          'min_salary_unit',
          salaryUnit
        )
      }

      if (locationFilter.trim()) {
        params.set(
          'location',
          locationFilter.trim()
        )
      }

      if (
        minMatch !== '' &&
        Number(minMatch) > 0
      ) {
        params.set(
          'min_score',
          String(Number(minMatch))
        )
      }

      if (searchFilter.trim()) {
        params.set(
          'search',
          searchFilter.trim()
        )
      }

      // IMPORTANT:
      // Auto-apply must ONLY consider jobs that survived the CURRENT frontend
      // filters. Send those exact visible platform job IDs to the backend.
      //
      // Do not re-sort here: filteredItems already represents the same jobs
      // the user is seeing on this page.
      const visiblePlatformIds = filteredItems
        .filter(
          job =>
            !job.applied &&
            job.source === platform &&
            job.id
        )
        .slice(0, requested)
        .map(job => String(job.id))

      if (visiblePlatformIds.length === 0) {
        setLocalAutoApplyMsg(
          `No ${platform === 'naukri' ? 'Naukri' : 'Internshala'} jobs match the current filters.`
        )
        setCheckingCreds(false)
        return
      }

      params.set(
        'job_ids',
        visiblePlatformIds.join(',')
      )

      console.log(
        `[CareerSync] Visible ${platform} job IDs sent to auto-apply:`,
        visiblePlatformIds
      )

      setLocalAutoApplying(true)
      setCheckingCreds(false)

      // Use an explicit platform endpoint.
      // IMPORTANT: Internshala must call its own backend route after
      // the credential check succeeds.
      const endpoint =
        platform === 'internshala'
          ? '/jobs/auto-apply/internshala'
          : '/jobs/auto-apply'

      console.log(
        `[CareerSync] Starting ${platform} auto-apply:`,
        `${endpoint}?${params.toString()}`
      )

      const applyRes = await api.post(
        `${endpoint}?${params.toString()}`,
        {},
        {
          timeout: 0,
        }
      )

      console.log(
        `[CareerSync] ${platform} auto-apply response:`,
        applyRes.data
      )

      setLocalAutoApplyMsg(
        applyRes.data?.message ||
        'Auto-apply completed.'
      )

      await fetchEligibilityResults()
      showEligibilityResultsForOneMinute()

      dispatch(
        fetchJobs()
      )

    }
    catch (err) {

      console.error(
        'Auto-apply failed',
        err
      )

      const detail =
        err.response?.data?.detail

      setLocalAutoApplyMsg(
        typeof detail === 'string'
          ? detail
          : 'Auto-apply failed. Check the backend terminal for details.'
      )

    }
    finally {

      setCheckingCreds(false)
      setLocalAutoApplying(false)

    }

  }


  // -------------------------------------------------------
  // Cancel Auto Apply
  // -------------------------------------------------------

  const handleCancelAutoApply = async () => {

    await dispatch(
      cancelAutoApply()
    )

    setLocalAutoApplying(false)

  }


  // -------------------------------------------------------
  // Logout
  // -------------------------------------------------------

  const handleLogout = async () => {

    await dispatch(
      logoutUser()
    )

    navigate('/login')

  }


  // -------------------------------------------------------
  // Counts
  // -------------------------------------------------------

  const minMonthlySalary =
    requestedMinimumMonthly(
      minSalary,
      salaryUnit
    )

  const filteredItems =
    items.filter(job => {

      if (
        searchFilter.trim()
      ) {
        const needle =
          searchFilter
            .trim()
            .toLowerCase()

        const haystack = [
          job.title,
          job.description,
        ]
          .filter(Boolean)
          .join(' ')
          .toLowerCase()

        if (!haystack.includes(needle)) {
          return false
        }
      }

      if (
        locationFilter.trim()
      ) {
        const location =
          String(
            job.location || ''
          ).toLowerCase()

        if (
          !location.includes(
            locationFilter
              .trim()
              .toLowerCase()
          )
        ) {
          return false
        }
      }

      if (
        minMatch !== '' &&
        Number(minMatch) > 0
      ) {
        const score =
          Number(
            job.confidence_score ??
            job.match_score ??
            0
          )

        if (score < Number(minMatch)) {
          return false
        }
      }

      if (
        minMonthlySalary !== null
      ) {
        const jobMinimum =
          salaryToMonthlyMinimum(
            job.salary
          )

        // Strict salary filter:
        // unknown/undisclosed salary is excluded because we
        // cannot guarantee it meets the user's threshold.
        if (
          jobMinimum === null ||
          jobMinimum < minMonthlySalary
        ) {
          return false
        }
      }

      if (
        experienceFilter !== 'all' &&
        !matchesExperienceFilter(job, experienceFilter)
      ) {
        return false
      }

      if (
        jobTypeFilter !== 'all' &&
        getJobType(job) !== jobTypeFilter
      ) {
        return false
      }

      return true
    })


  const unappliedNaukriCount =
    filteredItems.filter(
      job =>
        !job.applied &&
        job.source === 'naukri'
    ).length


  const unappliedInternshalaCount =
    filteredItems.filter(
      job =>
        !job.applied &&
        job.source === 'internshala'
    ).length


  const displayed =
    activeSource === 'all'
      ? filteredItems
      : filteredItems.filter(
          job =>
            job.source === activeSource
        )


  const counts = {

    all: filteredItems.length,

    naukri:
      filteredItems.filter(
        job =>
          job.source === 'naukri'
      ).length,

    indeed:
      filteredItems.filter(
        job =>
          job.source === 'indeed'
      ).length,

    internshala:
      filteredItems.filter(
        job =>
          job.source === 'internshala'
      ).length,

  }


  // -------------------------------------------------------
  // Resume availability
  // adjust field later according to backend response
  // -------------------------------------------------------

  const hasResume =
    Boolean(
      user?.resume_filename ||
      user?.resume_text ||
      user?.has_resume
    )

  const isAutoApplying =
    autoApplying ||
    localAutoApplying

  const shownAutoApplyMsg =
    localAutoApplyMsg ||
    autoApplyMsg

  const effectiveRequestedCount =
    Math.min(
      Number(maxApplies) || 0,
      unappliedNaukriCount
    )


  const effectiveInternshalaRequestedCount =
    Math.min(
      Number(maxApplies) || 0,
      unappliedInternshalaCount
    )

  useEffect(() => {
    return () => {
      if (eligibilityTimerRef.current) {
        clearTimeout(eligibilityTimerRef.current)
      }
    }
  }, [])


  return (

    <div
      className="
        min-h-screen
        bg-[#f5f5fa]
      "
      style={{
        fontFamily:
          'EuclidR, sans-serif'
      }}
    >

      {/* NAVBAR */}

      

      {/* PAGE */}

      <div
        className="
          max-w-7xl
          mx-auto
          px-6
          py-10
        "
      >

        {/* TITLE */}

        <div
          className="
            flex
            flex-col
            sm:flex-row
            sm:items-center
            justify-between
            gap-4
            mb-8
          "
        >

          <div>

            <h1
              className="
                text-3xl
                text-[#0f0f1a]
              "
              style={{
                fontFamily:
                  'EuclidB, sans-serif'
              }}
            >
              Job Matches
            </h1>


            <p
              className="
                text-sm
                text-[#6b6b80]
                mt-1
              "
            >
              Ranked using your saved
              resume and profile.
            </p>

          </div>


          {/* Refresh DB results only */}

          <button
            onClick={handleRefresh}
            disabled={loading}
            className="
              flex
              items-center
              gap-2
              px-5
              py-2.5
              bg-[#10B981]
              text-white
              rounded-xl
              shadow-[0_4px_18px_rgba(16,185,129,0.25)]
              hover:bg-[#0ea572]
              hover:-translate-y-0.5
              transition-all
              duration-200
              disabled:opacity-60
              disabled:cursor-not-allowed
              disabled:transform-none
              text-sm
            "
            style={{
              fontFamily:
                'EuclidSB, sans-serif'
            }}
          >

            {
              loading
                ? (
                    <>
                      <Loader2
                        size={15}
                        className="animate-spin"
                      />
                      Loading...
                    </>
                  )
                : (
                    <>
                      <RefreshCw
                        size={15}
                        strokeWidth={2}
                      />
                      Refresh Results
                    </>
                  )
            }

          </button>

        </div>



        {/* AUTO APPLY FILTERS */}

        {
          items.length > 0 && (

            <div
              className="
                mb-5
                bg-white
                border
                border-[#e2e2ed]
                rounded-2xl
                p-5
                shadow-sm
              "
            >

              <div
                className="
                  flex
                  items-center
                  gap-2
                  mb-4
                "
              >
                <SlidersHorizontal
                  size={17}
                  className="text-[#10B981]"
                />

                <div>
                  <h3
                    className="
                      text-sm
                      text-[#0f0f1a]
                    "
                    style={{
                      fontFamily:
                        'EuclidSB, sans-serif'
                    }}
                  >
                    Auto-Apply Filters
                  </h3>

                  <p
                    className="
                      text-xs
                      text-[#8a8a9d]
                      mt-0.5
                    "
                  >
                    These filters are applied before Naukri auto-apply.
                  </p>
                </div>
              </div>


              <div
                className="
                  grid
                  sm:grid-cols-2
                  lg:grid-cols-4
                  xl:grid-cols-7
                  gap-3
                "
              >

                <label className="block">
                  <span
                    className="
                      text-xs
                      text-[#6b6b80]
                    "
                  >
                    Number of jobs
                  </span>

                  <input
                    type="number"
                    min="1"
                    max="20"
                    value={maxApplies}
                    onChange={e =>
                      setMaxApplies(
                        e.target.value
                      )
                    }
                    className="
                      mt-1.5
                      w-full
                      px-3
                      py-2.5
                      rounded-xl
                      border
                      border-[#e2e2ed]
                      bg-white
                      text-sm
                      text-[#0f0f1a]
                      placeholder:text-[#a0a0b0]
                      outline-none
                      focus:border-[#10B981]
                    "
                  />
                </label>


                <label className="block">
                  <span
                    className="
                      text-xs
                      text-[#6b6b80]
                    "
                  >
                    Minimum salary
                  </span>

                  <div
                    className="
                      mt-1.5
                      flex
                      rounded-xl
                      border
                      border-[#e2e2ed]
                      overflow-hidden
                      focus-within:border-[#10B981]
                    "
                  >
                    <input
                      type="number"
                      min="0"
                      step="0.1"
                      placeholder={
                        salaryUnit === 'lpa'
                          ? 'e.g. 3'
                          : 'e.g. 30000'
                      }
                      value={minSalary}
                      onChange={e =>
                        setMinSalary(
                          e.target.value
                        )
                      }
                      className="
                        min-w-0
                        flex-1
                        px-3
                        py-2.5
                        text-sm
                        text-[#0f0f1a]
                        placeholder:text-[#a0a0b0]
                        outline-none
                      "
                    />

                    <select
                      value={salaryUnit}
                      onChange={e =>
                        setSalaryUnit(
                          e.target.value
                        )
                      }
                      className="
                        border-l
                        border-[#e2e2ed]
                        px-2
                        text-xs
                        text-[#0f0f1a]
                        bg-[#f8f8fb]
                        outline-none
                      "
                    >
                      <option value="lpa">
                        LPA
                      </option>
                      <option value="monthly">
                        / month
                      </option>
                    </select>
                  </div>
                </label>


                <label className="block">
                  <span
                    className="
                      text-xs
                      text-[#6b6b80]
                    "
                  >
                    Location
                  </span>

                  <input
                    type="text"
                    placeholder="e.g. Bangalore"
                    value={locationFilter}
                    onChange={e =>
                      setLocationFilter(
                        e.target.value
                      )
                    }
                    className="
                      mt-1.5
                      w-full
                      px-3
                      py-2.5
                      rounded-xl
                      border
                      border-[#e2e2ed]
                      bg-white
                      text-sm
                      text-[#0f0f1a]
                      placeholder:text-[#a0a0b0]
                      outline-none
                      focus:border-[#10B981]
                    "
                  />
                </label>


                <label className="block">
                  <span
                    className="
                      text-xs
                      text-[#6b6b80]
                    "
                  >
                    Minimum match %
                  </span>

                  <input
                    type="number"
                    min="0"
                    max="100"
                    placeholder="e.g. 50"
                    value={minMatch}
                    onChange={e =>
                      setMinMatch(
                        e.target.value
                      )
                    }
                    className="
                      mt-1.5
                      w-full
                      px-3
                      py-2.5
                      rounded-xl
                      border
                      border-[#e2e2ed]
                      bg-white
                      text-sm
                      text-[#0f0f1a]
                      placeholder:text-[#a0a0b0]
                      outline-none
                      focus:border-[#10B981]
                    "
                  />
                </label>


                <label className="block">
                  <span
                    className="
                      text-xs
                      text-[#6b6b80]
                    "
                  >
                    Role / skill
                  </span>

                  <input
                    type="text"
                    placeholder="e.g. React"
                    value={searchFilter}
                    onChange={e =>
                      setSearchFilter(
                        e.target.value
                      )
                    }
                    className="
                      mt-1.5
                      w-full
                      px-3
                      py-2.5
                      rounded-xl
                      border
                      border-[#e2e2ed]
                      bg-white
                      text-sm
                      text-[#0f0f1a]
                      placeholder:text-[#a0a0b0]
                      outline-none
                      focus:border-[#10B981]
                    "
                  />
                </label>


                <label className="block">
                  <span className="text-xs text-[#6b6b80]">
                    Experience
                  </span>

                  <select
                    value={experienceFilter}
                    onChange={e =>
                      setExperienceFilter(e.target.value)
                    }
                    className="
                      mt-1.5
                      w-full
                      px-3
                      py-2.5
                      rounded-xl
                      border
                      border-[#e2e2ed]
                      bg-white
                      text-sm
                      text-[#0f0f1a]
                      outline-none
                      focus:border-[#10B981]
                    "
                  >
                    <option value="all">All experience</option>
                    <option value="fresher">Fresher / 0-1 yr</option>
                    <option value="1-3">1-3 years</option>
                    <option value="3-5">3-5 years</option>
                    <option value="5+">5+ years</option>
                  </select>
                </label>


                <label className="block">
                  <span className="text-xs text-[#6b6b80]">
                    Job type
                  </span>

                  <select
                    value={jobTypeFilter}
                    onChange={e =>
                      setJobTypeFilter(e.target.value)
                    }
                    className="
                      mt-1.5
                      w-full
                      px-3
                      py-2.5
                      rounded-xl
                      border
                      border-[#e2e2ed]
                      bg-white
                      text-sm
                      text-[#0f0f1a]
                      outline-none
                      focus:border-[#10B981]
                    "
                  >
                    <option value="all">All job types</option>
                    <option value="internship">Internship</option>
                    <option value="full_time">Full-time</option>
                  </select>
                </label>


              </div>


              <div
                className="
                  mt-4
                  flex
                  items-center
                  justify-between
                  gap-3
                  flex-wrap
                "
              >

                {/* <p
                  className="
                    text-xs
                    text-[#6b6b80]
                  "
                > */}
                  {/* <span
                    style={{
                      fontFamily:
                        'EuclidSB, sans-serif'
                    }}
                  >
                    {unappliedNaukriCount}
                  </span> */}
                  {' '}Naukri +{' '}
                  {/* <span
                    style={{
                      fontFamily:
                        'EuclidSB, sans-serif'
                    }}
                  >
                    {unappliedInternshalaCount}
                  </span> */}
                  {/* {' '}Internshala jobs match the current filters.
                  {
                    minSalary !== '' &&
                    Number(minSalary) > 0
                      ? ' Jobs with undisclosed salary are excluded.'
                      : ''
                  }
                </p> */}


                <button
                  type="button"
                  onClick={() => {
                    setMaxApplies(5)
                    setMinSalary('')
                    setSalaryUnit('lpa')
                    setLocationFilter('')
                    setMinMatch('')
                    setSearchFilter('')
                    setExperienceFilter('all')
                    setJobTypeFilter('all')
                    setFilterError('')
                  }}
                  className="
                    text-xs
                    px-3
                    py-2
                    rounded-lg
                    border
                    border-[#ec1906]
                    text-[#6b6b80]
                    hover:text-[#d72219]
                    hover:border-[#840303]
                    transition-colors
                  "
                >
                  Clear Filters
                </button>

              </div>


              {
                filterError && (
                  <p
                    className="
                      mt-3
                      text-xs
                      text-red-600
                    "
                  >
                    {filterError}
                  </p>
                )
              }

            </div>

          )
        }


        {/* AUTO APPLY */}

        {
          items.length > 0 && (

            <div
              className="
                mb-5
                flex
                items-center
                gap-3
                flex-wrap
              "
            >

              {
                activeSource === 'all' ? (

                  <div
                    className="
                      w-full
                      px-4
                      py-3
                      rounded-xl
                      border
                      border-[#e2e2ed]
                      bg-white
                      text-sm
                      text-[#6b6b80]
                    "
                  >
                    For auto-apply, go to a specific platform section:
                    <span
                      className="
                        ml-1
                        text-[#0f0f1a]
                      "
                      style={{
                        fontFamily:
                          'EuclidSB, sans-serif'
                      }}
                    >
                      Naukri or Internshala
                    </span>
                  </div>

                ) : activeSource === 'naukri' ? (

                  !isAutoApplying ? (

                    <button
                      onClick={() =>
                        checkAndAutoApply(
                          'naukri'
                        )
                      }
                      disabled={
                        checkingCreds ||
                        unappliedNaukriCount === 0
                      }
                      className="
                        flex
                        items-center
                        gap-2
                        px-5
                        py-2.5
                        bg-blue-600
                        text-white
                        rounded-xl
                        hover:bg-blue-700
                        transition-all
                        disabled:opacity-60
                        disabled:cursor-not-allowed
                        text-sm
                      "
                      style={{
                        fontFamily:
                          'EuclidSB, sans-serif'
                      }}
                    >
                      {
                        checkingCreds
                          ? (
                              <>
                                <Loader2
                                  size={15}
                                  className="animate-spin"
                                />
                                Checking...
                              </>
                            )
                          : (
                              <>
                                <Zap
                                  size={15}
                                  strokeWidth={2}
                                />
                                Auto Apply Naukri
                                ({effectiveRequestedCount})
                              </>
                            )
                      }
                    </button>

                  ) : (

                    <button
                      onClick={
                        handleCancelAutoApply
                      }
                      disabled={
                        cancelling
                      }
                      className="
                        flex
                        items-center
                        gap-2
                        px-5
                        py-2.5
                        bg-red-600
                        text-white
                        rounded-xl
                        hover:bg-red-700
                        transition-all
                        disabled:opacity-60
                        text-sm
                      "
                      style={{
                        fontFamily:
                          'EuclidSB, sans-serif'
                      }}
                    >
                      {
                        cancelling
                          ? (
                              <>
                                <Loader2
                                  size={15}
                                  className="animate-spin"
                                />
                                Cancelling...
                              </>
                            )
                          : (
                              <>
                                <X
                                  size={15}
                                  strokeWidth={2}
                                />
                                Cancel Auto-Apply
                              </>
                            )
                      }
                    </button>

                  )

                ) : activeSource === 'internshala' ? (

                  !isAutoApplying ? (

                    <button
                      onClick={() =>
                        checkAndAutoApply(
                          'internshala'
                        )
                      }
                      disabled={
                        checkingCreds ||
                        unappliedInternshalaCount === 0
                      }
                      className="
                        flex
                        items-center
                        gap-2
                        px-5
                        py-2.5
                        bg-[#3b82f6]
                        text-white
                        rounded-xl
                        hover:bg-[#2563eb]
                        transition-all
                        disabled:opacity-60
                        disabled:cursor-not-allowed
                        text-sm
                      "
                      style={{
                        fontFamily:
                          'EuclidSB, sans-serif'
                      }}
                    >
                      {
                        checkingCreds
                          ? (
                              <>
                                <Loader2
                                  size={15}
                                  className="animate-spin"
                                />
                                Checking...
                              </>
                            )
                          : (
                              <>
                                <Bot
                                  size={15}
                                  strokeWidth={2}
                                />
                                Auto Apply Internshala
                                ({effectiveInternshalaRequestedCount})
                              </>
                            )
                      }
                    </button>

                  ) : (

                    <button
                      onClick={
                        handleCancelAutoApply
                      }
                      disabled={
                        cancelling
                      }
                      className="
                        flex
                        items-center
                        gap-2
                        px-5
                        py-2.5
                        bg-red-600
                        text-white
                        rounded-xl
                        hover:bg-red-700
                        transition-all
                        disabled:opacity-60
                        text-sm
                      "
                      style={{
                        fontFamily:
                          'EuclidSB, sans-serif'
                      }}
                    >
                      {
                        cancelling
                          ? (
                              <>
                                <Loader2
                                  size={15}
                                  className="animate-spin"
                                />
                                Cancelling...
                              </>
                            )
                          : (
                              <>
                                <X
                                  size={15}
                                  strokeWidth={2}
                                />
                                Cancel Auto-Apply
                              </>
                            )
                      }
                    </button>

                  )

                ) : (

                  <div
                    className="
                      w-full
                      px-4
                      py-3
                      rounded-xl
                      border
                      border-[#e2e2ed]
                      bg-white
                      text-sm
                      text-[#6b6b80]
                    "
                  >
                    Auto-apply is currently available for
                    <span
                      className="
                        ml-1
                        text-[#0f0f1a]
                      "
                      style={{
                        fontFamily:
                          'EuclidSB, sans-serif'
                      }}
                    >
                      Naukri and Internshala
                    </span>
                    .
                  </div>

                )
              }


              {
                shownAutoApplyMsg &&
                activeSource !== 'all' && (
                  <div
                    className="
                      flex
                      items-center
                      gap-2
                      text-sm
                      text-[#059669]
                    "
                  >
                    <CheckCircle
                      size={15}
                    />
                    {shownAutoApplyMsg}
                  </div>
                )
              }

            </div>
          )
        }


        {/* ELIGIBILITY RESULTS */}

        {
          showEligibilityResults &&
          (
            notEligibleJobs.length > 0 ||
            reviewJobs.length > 0
          ) && (

            <div
              className="
                mb-6
                grid
                lg:grid-cols-2
                gap-4
              "
            >

              {/* NOT ELIGIBLE */}

              <div
                className="
                  bg-white
                  border
                  border-red-200
                  rounded-2xl
                  p-5
                  shadow-sm
                "
              >

                <div
                  className="
                    flex
                    items-center
                    justify-between
                    gap-3
                    mb-4
                  "
                >

                  <div
                    className="
                      flex
                      items-center
                      gap-2
                    "
                  >
                    <AlertTriangle
                      size={17}
                      className="text-red-500"
                    />

                    <h3
                      className="text-[#0f0f1a]"
                      style={{
                        fontFamily:
                          'EuclidSB, sans-serif'
                      }}
                    >
                      Not Eligible
                    </h3>
                  </div>

                  <span
                    className="
                      text-xs
                      px-2.5
                      py-1
                      rounded-full
                      bg-red-50
                      border
                      border-red-200
                      text-red-600
                    "
                  >
                    {notEligibleJobs.length}
                  </span>

                </div>

                {
                  notEligibleJobs.length === 0
                    ? (
                        <p
                          className="
                            text-sm
                            text-[#8b8b9d]
                          "
                        >
                          No jobs failed a hard
                          eligibility requirement.
                        </p>
                      )
                    : (
                        <div className="space-y-3">

                          {
                            notEligibleJobs.map(
                              application => (

                                <div
                                  key={
                                    application.id ||
                                    application.job_id
                                  }
                                  className="
                                    p-3.5
                                    rounded-xl
                                    bg-red-50/50
                                    border
                                    border-red-100
                                  "
                                >

                                  <div
                                    className="
                                      flex
                                      items-start
                                      justify-between
                                      gap-3
                                    "
                                  >

                                    <div>

                                      <p
                                        className="
                                          text-sm
                                          text-[#0f0f1a]
                                        "
                                        style={{
                                          fontFamily:
                                            'EuclidSB, sans-serif'
                                        }}
                                      >
                                        {application.title}
                                      </p>

                                      {
                                        application.company && (
                                          <p
                                            className="
                                              text-xs
                                              text-[#6b7280]
                                              mt-0.5
                                            "
                                          >
                                            {application.company}
                                          </p>
                                        )
                                      }

                                    </div>

                                    {
                                      application.url && (

                                        <a
                                          href={application.url}
                                          target="_blank"
                                          rel="noreferrer"
                                          className="
                                            text-red-500
                                            hover:text-red-700
                                          "
                                          title="View job"
                                        >
                                          <ExternalLink
                                            size={15}
                                          />
                                        </a>

                                      )
                                    }

                                  </div>

                                  <p
                                    className="
                                      mt-2
                                      text-xs
                                      leading-relaxed
                                      text-red-700
                                    "
                                  >
                                    <span
                                      style={{
                                        fontFamily:
                                          'EuclidSB, sans-serif'
                                      }}
                                    >
                                      Reason:
                                    </span>{' '}
                                    {
                                      application.note ||
                                      'A hard eligibility requirement was not met.'
                                    }
                                  </p>

                                </div>

                              )
                            )
                          }

                        </div>
                      )
                }

              </div>


              {/* NEEDS REVIEW */}

              <div
                className="
                  bg-white
                  border
                  border-amber-200
                  rounded-2xl
                  p-5
                  shadow-sm
                "
              >

                <div
                  className="
                    flex
                    items-center
                    justify-between
                    gap-3
                    mb-4
                  "
                >

                  <div
                    className="
                      flex
                      items-center
                      gap-2
                    "
                  >
                    <Search
                      size={17}
                      className="text-amber-500"
                    />

                    <h3
                      className="text-[#0f0f1a]"
                      style={{
                        fontFamily:
                          'EuclidSB, sans-serif'
                      }}
                    >
                      Needs Review
                    </h3>
                  </div>

                  <span
                    className="
                      text-xs
                      px-2.5
                      py-1
                      rounded-full
                      bg-amber-50
                      border
                      border-amber-200
                      text-amber-700
                    "
                  >
                    {reviewJobs.length}
                  </span>

                </div>

                {
                  reviewJobs.length === 0
                    ? (
                        <p
                          className="
                            text-sm
                            text-[#8b8b9d]
                          "
                        >
                          No jobs are waiting for
                          eligibility review.
                        </p>
                      )
                    : (
                        <div className="space-y-3">

                          {
                            reviewJobs.map(
                              application => (

                                <div
                                  key={
                                    application.id ||
                                    application.job_id
                                  }
                                  className="
                                    p-3.5
                                    rounded-xl
                                    bg-amber-50/50
                                    border
                                    border-amber-100
                                  "
                                >

                                  <div
                                    className="
                                      flex
                                      items-start
                                      justify-between
                                      gap-3
                                    "
                                  >

                                    <div>

                                      <p
                                        className="
                                          text-sm
                                          text-[#0f0f1a]
                                        "
                                        style={{
                                          fontFamily:
                                            'EuclidSB, sans-serif'
                                        }}
                                      >
                                        {application.title}
                                      </p>

                                      {
                                        application.company && (
                                          <p
                                            className="
                                              text-xs
                                              text-[#6b6b80]
                                              mt-0.5
                                            "
                                          >
                                            {application.company}
                                          </p>
                                        )
                                      }

                                    </div>

                                    {
                                      application.url && (

                                        <a
                                          href={application.url}
                                          target="_blank"
                                          rel="noreferrer"
                                          className="
                                            text-amber-600
                                            hover:text-amber-800
                                          "
                                          title="Review job"
                                        >
                                          <ExternalLink
                                            size={15}
                                          />
                                        </a>

                                      )
                                    }

                                  </div>

                                  <p
                                    className="
                                      mt-2
                                      text-xs
                                      leading-relaxed
                                      text-amber-800
                                    "
                                  >
                                    <span
                                      style={{
                                        fontFamily:
                                          'EuclidSB, sans-serif'
                                      }}
                                    >
                                      Review:
                                    </span>{' '}
                                    {
                                      application.note ||
                                      'Eligibility could not be confirmed safely.'
                                    }
                                  </p>

                                </div>

                              )
                            )
                          }

                        </div>
                      )
                }

              </div>

            </div>

          )
        }


        {/* ERROR */}

        {/* {
          error && (

            <div
              className="
                mb-6
                px-4
                py-3
                bg-[#ef4444]/[0.07]
                border
                border-[#ef4444]/30
                rounded-xl
                text-sm
                text-[#ef4444]
                flex
                items-center
                gap-2
              "
            >

              <AlertTriangle
                size={15}
                strokeWidth={2}
                className="flex-shrink-0"
              />

              {error}

            </div>

          )
        } */}


        {/* SOURCE FILTERS */}

        {
          items.length > 0 && (

            <div
              className="
                flex
                gap-2
                mb-6
                flex-wrap
              "
            >

              {
                SOURCES.map(
                  ({
                    key,
                    label,
                    Icon
                  }) => (

                    <button
                      key={key}
                      onClick={() =>
                        setActiveSource(key)
                      }
                      className={`
                        flex
                        items-center
                        gap-2
                        px-4
                        py-2
                        rounded-xl
                        text-sm
                        border
                        transition-all
                        duration-200

                        ${
                          activeSource === key
                            ? `
                              bg-[#10B981]/[0.08]
                              border-[#10B981]
                              text-[#059669]
                              shadow-[0_0_12px_rgba(16,185,129,0.12)]
                            `
                            : `
                              bg-white
                              border-[#e2e2ed]
                              text-[#6b6b80]
                              hover:border-[#10B981]/40
                              hover:text-[#0f0f1a]
                            `
                        }
                      `}
                      style={{
                        fontFamily:
                          'EuclidSB, sans-serif'
                      }}
                    >

                      <Icon
                        size={14}
                        strokeWidth={1.75}
                      />

                      {label}


                      <span
                        className={`
                          text-xs
                          px-1.5
                          py-0.5
                          rounded-full

                          ${
                            activeSource === key
                              ? `
                                bg-[#10B981]/20
                                text-[#059669]
                              `
                              : `
                                bg-[#f5f5fa]
                                text-[#a0a0b0]
                              `
                          }
                        `}
                      >
                        {counts[key]}
                      </span>

                    </button>

                  )
                )
              }

            </div>

          )
        }


        {/* JOB LIST */}

        {
          loading &&
          items.length === 0
            ? (

                <div
                  className="
                    flex
                    justify-center
                    py-32
                  "
                >

                  <div
                    className="
                      w-10
                      h-10
                      rounded-full
                      border-2
                      border-[#10B981]
                      border-t-transparent
                      animate-spin
                    "
                  />

                </div>

              )

            : items.length === 0

              ? (

                  <EmptyState
                    hasResume={hasResume}
                  />

                )

              : displayed.length === 0

                ? (

                    <div
                      className="
                        flex
                        flex-col
                        items-center
                        gap-4
                        py-20
                        text-center
                      "
                    >

                      <div
                        className="
                          w-14
                          h-14
                          rounded-2xl
                          bg-[#f5f5fa]
                          border
                          border-[#e2e2ed]
                          flex
                          items-center
                          justify-center
                        "
                      >

                        <Search
                          size={24}
                          className="text-[#a0a0b0]"
                          strokeWidth={1.5}
                        />

                      </div>


                      <p
                        className="
                          text-[#6b6b80]
                          text-sm
                        "
                      >

                        No jobs from{' '}

                        <span
                          className="
                            text-[#0f0f1a]
                            capitalize
                          "
                          style={{
                            fontFamily:
                              'EuclidSB, sans-serif'
                          }}
                        >
                          {activeSource}
                        </span>

                        {' '}right now.

                      </p>

                    </div>

                  )

                : (

                    <div
                      className="
                        grid
                        grid-cols-1
                        gap-4
                      "
                    >

                      {
                        displayed.map(
                          job => (

                            <JobCard
                              key={job.id}
                              job={job}
                            />

                          )
                        )
                      }

                    </div>

                  )
        }

      </div>

    </div>
  )
}