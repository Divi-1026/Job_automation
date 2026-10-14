import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ArrowLeft,
  Briefcase,
  CheckCircle,
  ExternalLink,
  Loader2,
  RefreshCw,
  AlertTriangle,
  Clock3,
  XCircle,
} from 'lucide-react'
import api from '../api/axiosInstance'


const statusConfig = {
  pending_manual: {
    label: 'Pending',
    badge:
      'bg-[#f59e0b]/10 text-[#b45309] border-[#f59e0b]/20',
    icon: Clock3,
  },

  applied: {
    label: 'Applied',
    badge:
      'bg-[#10B981]/10 text-[#059669] border-[#10B981]/20',
    icon: CheckCircle,
  },

  not_eligible: {
    label: 'Not Eligible',
    badge:
      'bg-[#ef4444]/10 text-[#dc2626] border-[#ef4444]/20',
    icon: XCircle,
  },
}


// ---------------------------------------------------------
// Job Card
// ---------------------------------------------------------

const JobCard = ({
  app,
  markingJobId,
  onMarkApplied,
}) => {
  const openUrl =
    app.manual_url || app.url

  const config =
    statusConfig[app.status] ||
    statusConfig.pending_manual

  const isPending =
    app.status === 'pending_manual'

  return (
    <div
      className="
        bg-white
        border
        border-[#e2e2ed]
        rounded-xl
        p-4
        flex
        flex-col
        gap-3
        shadow-sm
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
        <div className="min-w-0">
          <h3
            className="
              text-sm
              text-[#0f0f1a]
              truncate
            "
            style={{
              fontFamily:
                'EuclidSB, sans-serif',
            }}
          >
            {app.title || 'Untitled Job'}
          </h3>

          <p
            className="
              text-xs
              text-[#6b6b80]
              mt-1
            "
          >
            {
              [
                app.company,
                app.location,
              ]
                .filter(Boolean)
                .join(' • ')
            }
          </p>

          {
            typeof app.confidence_score ===
              'number' && (
              <p
                className="
                  text-xs
                  text-[#8a8a9a]
                  mt-1
                "
              >
                Match Score:{' '}
                {
                  app.confidence_score
                    .toFixed(2)
                }
                %
              </p>
            )
          }
        </div>

        <span
          className={`
            flex-shrink-0
            px-2.5
            py-1
            rounded-full
            text-xs
            border
            ${config.badge}
          `}
        >
          {config.label}
        </span>
      </div>

      {
        app.note && (
          <div
            className={`
              text-xs
              rounded-lg
              px-3
              py-2
              ${
                app.status ===
                'not_eligible'
                  ? `
                    bg-[#ef4444]/[0.05]
                    text-[#b91c1c]
                    border
                    border-[#ef4444]/10
                  `
                  : `
                    bg-[#f7f7fb]
                    text-[#6b6b80]
                  `
              }
            `}
          >
            {
              app.status ===
                'not_eligible' && (
                <span className="font-medium">
                  Reason:{' '}
                </span>
              )
            }

            {app.note}
          </div>
        )
      }

      <div
        className="
          flex
          flex-wrap
          items-center
          gap-2
        "
      >
        {
          openUrl && (
            <a
              href={openUrl}
              target="_blank"
              rel="noreferrer"
              className="
                inline-flex
                items-center
                gap-1.5
                px-3
                py-2
                rounded-lg
                text-xs
                border
                border-[#e2e2ed]
                text-[#0f0f1a]
                hover:border-[#10B981]/40
                hover:text-[#059669]
                transition-all
              "
            >
              <ExternalLink size={13} />

              {
                isPending
                  ? 'Open Application'
                  : 'Open Job'
              }
            </a>
          )
        }

        {
          isPending && (
            <button
              type="button"
              onClick={() =>
                onMarkApplied(
                  app.job_id
                )
              }
              disabled={
                markingJobId ===
                app.job_id
              }
              className="
                inline-flex
                items-center
                gap-1.5
                px-3
                py-2
                rounded-lg
                text-xs
                bg-[#10B981]
                text-white
                hover:bg-[#059669]
                disabled:opacity-50
                transition-all
              "
            >
              {
                markingJobId ===
                app.job_id
                  ? (
                    <Loader2
                      size={13}
                      className="
                        animate-spin
                      "
                    />
                  )
                  : (
                    <CheckCircle
                      size={13}
                    />
                  )
              }

              Mark as Applied
            </button>
          )
        }
      </div>
    </div>
  )
}


// ---------------------------------------------------------
// Application Section
// ---------------------------------------------------------

const ApplicationSection = ({
  title,
  Icon,
  count,
  children,
  emptyText,
  tone = 'green',
}) => {
  const toneClasses = {
    green: {
      box:
        'bg-[#10B981]/10 border-[#10B981]/20',
      icon:
        'text-[#10B981]',
    },

    amber: {
      box:
        'bg-[#f59e0b]/10 border-[#f59e0b]/20',
      icon:
        'text-[#b45309]',
    },

    red: {
      box:
        'bg-[#ef4444]/10 border-[#ef4444]/20',
      icon:
        'text-[#dc2626]',
    },
  }

  const toneStyle =
    toneClasses[tone] ||
    toneClasses.green

  return (
    <section
      className={`
        bg-white
        border
        border-[#e2e2ed]
        rounded-2xl
        p-5
        shadow-sm
        flex
        flex-col

        ${
          count === 0
            ? 'h-auto min-h-[150px]'
            : 'h-[520px]'
        }
      `}
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
            gap-2.5
          "
        >
          <div
            className={`
              w-8
              h-8
              rounded-lg
              border
              flex
              items-center
              justify-center
              ${toneStyle.box}
            `}
          >
            <Icon
              size={15}
              className={
                toneStyle.icon
              }
              strokeWidth={1.8}
            />
          </div>

          <h3
            className="
              text-sm
              text-[#0f0f1a]
            "
            style={{
              fontFamily:
                'EuclidSB, sans-serif',
            }}
          >
            {title}
          </h3>
        </div>

        <span
          className="
            px-2.5
            py-1
            rounded-full
            bg-[#f5f5fa]
            text-xs
            text-[#6b6b80]
          "
        >
          {count}
        </span>
      </div>

      {
        count === 0
          ? (
            <div
              className="
                min-h-[72px]
                flex
                flex-col
                items-center
                justify-center
                text-center
                border
                border-dashed
                border-[#dcdce8]
                rounded-xl
                px-3
                py-4
              "
            >
              <Briefcase
                size={20}
                className="
                  mx-auto
                  mb-1.5
                  text-[#a0a0b0]
                "
              />

              <p
                className="
                  text-xs
                  text-[#6b6b80]
                "
              >
                {emptyText}
              </p>
            </div>
          )
          : (
            <div
              className="
                flex-1
                min-h-0
                overflow-y-auto
                pr-2
                flex
                flex-col
                gap-3
              "
            >
              {children}
            </div>
          )
      }
    </section>
  )
}


// ---------------------------------------------------------
// Platform Block
// ---------------------------------------------------------

const PlatformBlock = ({
  platformName,
  platformKey,
  applications,
  markingJobId,
  onMarkApplied,
}) => {
  const pending =
    applications.filter(
      app =>
        app.status ===
        'pending_manual'
    )

  const applied =
    applications.filter(
      app =>
        app.status ===
        'applied'
    )

  const notEligible =
    applications.filter(
      app =>
        app.status ===
        'not_eligible'
    )

  return (
    <section className="mb-10">
      <div
        className="
          flex
          items-center
          justify-between
          gap-3
          mb-4
        "
      >
        <div>
          <h2
            className="
              text-xl
              text-[#0f0f1a]
            "
            style={{
              fontFamily:
                'EuclidB, sans-serif',
            }}
          >
            {platformName}
          </h2>

          <p
            className="
              text-sm
              text-[#6b6b80]
              mt-1
            "
          >
            Applied, pending and
            not eligible jobs for{' '}
            {platformName}.
          </p>
        </div>

        <span
          className="
            px-3
            py-1.5
            rounded-full
            bg-white
            border
            border-[#e2e2ed]
            text-xs
            text-[#6b6b80]
          "
        >
          {applications.length} total
        </span>
      </div>

      <div
        className="
          grid
          xl:grid-cols-3
          md:grid-cols-2
          gap-5
          items-start
        "
      >
        <ApplicationSection
          title="Pending"
          Icon={Clock3}
          count={pending.length}
          emptyText={
            `No pending ${platformName} applications.`
          }
          tone="amber"
        >
          {
            pending.map(
              app => (
                <JobCard
                  key={
                    `${platformKey}-pending-${app.job_id}`
                  }
                  app={app}
                  markingJobId={
                    markingJobId
                  }
                  onMarkApplied={
                    onMarkApplied
                  }
                />
              )
            )
          }
        </ApplicationSection>

        <ApplicationSection
          title="Applied"
          Icon={CheckCircle}
          count={applied.length}
          emptyText={
            `No applied ${platformName} jobs yet.`
          }
          tone="green"
        >
          {
            applied.map(
              app => (
                <JobCard
                  key={
                    `${platformKey}-applied-${app.job_id}`
                  }
                  app={app}
                  markingJobId={
                    markingJobId
                  }
                  onMarkApplied={
                    onMarkApplied
                  }
                />
              )
            )
          }
        </ApplicationSection>

        <ApplicationSection
          title="Not Eligible"
          Icon={XCircle}
          count={
            notEligible.length
          }
          emptyText={
            `No not-eligible ${platformName} jobs.`
          }
          tone="red"
        >
          {
            notEligible.map(
              app => (
                <JobCard
                  key={
                    `${platformKey}-not-eligible-${app.job_id}`
                  }
                  app={app}
                  markingJobId={
                    markingJobId
                  }
                  onMarkApplied={
                    onMarkApplied
                  }
                />
              )
            )
          }
        </ApplicationSection>
      </div>
    </section>
  )
}


// ---------------------------------------------------------
// Applications Page
// ---------------------------------------------------------

export default function Applications() {
  const [
    applications,
    setApplications
  ] = useState([])

  const [
    loading,
    setLoading
  ] = useState(false)

  const [
    error,
    setError
  ] = useState('')

  const [
    markingJobId,
    setMarkingJobId
  ] = useState(null)


  // -------------------------------------------------------
  // Fetch Applications
  // -------------------------------------------------------

  const fetchApplications =
    async () => {

      setLoading(true)
      setError('')

      try {
        const res =
          await api.get(
            '/jobs/applications'
          )

        setApplications(
          res.data?.applications ||
            []
        )
      }
      catch (err) {
        setError(
          err.response?.data?.detail ||
            'Failed to load applications.'
        )
      }
      finally {
        setLoading(false)
      }
    }


  useEffect(() => {
    fetchApplications()
  }, [])


  // -------------------------------------------------------
  // Platform filters
  // -------------------------------------------------------

  const naukriApplications =
    useMemo(
      () =>
        applications.filter(
          app =>
            (
              app.source || ''
            ).toLowerCase() ===
            'naukri'
        ),
      [applications]
    )


  const internshalaApplications =
    useMemo(
      () =>
        applications.filter(
          app =>
            (
              app.source || ''
            ).toLowerCase() ===
            'internshala'
        ),
      [applications]
    )


  const otherApplications =
    useMemo(
      () =>
        applications.filter(
          app => {
            const source =
              (
                app.source || ''
              ).toLowerCase()

            return (
              source !== 'naukri' &&
              source !==
                'internshala'
            )
          }
        ),
      [applications]
    )


  // -------------------------------------------------------
  // Mark pending as applied
  // -------------------------------------------------------

  const markApplicationAsApplied =
    async jobId => {

      setMarkingJobId(jobId)
      setError('')

      try {
        await api.patch(
          `/jobs/applications/${jobId}/status?status=applied`
        )

        setApplications(
          current =>
            current.map(
              app =>
                app.job_id ===
                jobId
                  ? {
                      ...app,
                      status:
                        'applied',
                    }
                  : app
            )
        )
      }
      catch (err) {
        setError(
          err.response?.data
            ?.detail ||
            'Failed to mark application as applied.'
        )
      }
      finally {
        setMarkingJobId(null)
      }
    }


  // -------------------------------------------------------
  // Visible applications
  // -------------------------------------------------------

  const visibleApplications =
    useMemo(
      () =>
        applications.filter(
          app =>
            [
              'applied',
              'pending_manual',
              'not_eligible',
            ].includes(
              app.status
            )
        ),
      [applications]
    )


  return (
    <div
      className="
        min-h-screen
        bg-[#f5f5fa]
      "
      style={{
        fontFamily:
          'EuclidR, sans-serif',
      }}
    >
      {/* HEADER */}

      


      {/* MAIN */}

      <main
        className="
          max-w-7xl
          mx-auto
          px-6
          py-10
        "
      >
        <div
          className="
            flex
            items-start
            justify-between
            gap-4
            mb-8
          "
        >
          <div>
            <h1
              className="
                text-2xl
                text-[#0f0f1a]
              "
              style={{
                fontFamily:
                  'EuclidB, sans-serif',
              }}
            >
              Applications
            </h1>

            <p
              className="
                text-sm
                text-[#6b6b80]
                mt-1
              "
            >
              Track Naukri and
              Internshala applications
              separately.
            </p>
          </div>

          <button
            type="button"
            onClick={
              fetchApplications
            }
            disabled={loading}
            className="
              flex
              items-center
              gap-1.5
              px-3
              py-2
              rounded-lg
              border
              border-[#e2e2ed]
              bg-white
              text-sm
              text-[#6b6b80]
              hover:text-[#0f0f1a]
              disabled:opacity-50
              transition-all
            "
          >
            <RefreshCw
              size={14}
              className={
                loading
                  ? 'animate-spin'
                  : ''
              }
            />

            Refresh
          </button>
        </div>


        {/* ERROR */}

        {
          error && (
            <div
              className="
                mb-5
                px-4
                py-3
                bg-[#ef4444]/[0.06]
                border
                border-[#ef4444]/20
                rounded-lg
                text-sm
                text-[#ef4444]
                flex
                items-center
                gap-2
              "
            >
              <AlertTriangle
                size={14}
              />

              {error}
            </div>
          )
        }


        {/* CONTENT */}

        {
          loading &&
          applications.length === 0
            ? (
              <div
                className="
                  py-16
                  flex
                  items-center
                  justify-center
                  gap-2
                  text-sm
                  text-[#6b6b80]
                "
              >
                <Loader2
                  size={17}
                  className="
                    animate-spin
                  "
                />

                Loading applications...
              </div>
            )

            : visibleApplications
                .length === 0
              ? (
                <div
                  className="
                    bg-white
                    border
                    border-dashed
                    border-[#dcdce8]
                    rounded-2xl
                    py-16
                    text-center
                  "
                >
                  <Briefcase
                    size={28}
                    className="
                      mx-auto
                      mb-3
                      text-[#a0a0b0]
                    "
                  />

                  <p
                    className="
                      text-sm
                      text-[#6b6b80]
                    "
                  >
                    No applications
                    to show yet.
                  </p>
                </div>
              )

              : (
                <>
                  <PlatformBlock
                    platformName="Naukri"
                    platformKey="naukri"
                    applications={
                      naukriApplications.filter(
                        app =>
                          [
                            'applied',
                            'pending_manual',
                            'not_eligible',
                          ].includes(
                            app.status
                          )
                      )
                    }
                    markingJobId={
                      markingJobId
                    }
                    onMarkApplied={
                      markApplicationAsApplied
                    }
                  />

                  <PlatformBlock
                    platformName="Internshala"
                    platformKey="internshala"
                    applications={
                      internshalaApplications.filter(
                        app =>
                          [
                            'applied',
                            'pending_manual',
                            'not_eligible',
                          ].includes(
                            app.status
                          )
                      )
                    }
                    markingJobId={
                      markingJobId
                    }
                    onMarkApplied={
                      markApplicationAsApplied
                    }
                  />

                  {
                    otherApplications.some(
                      app =>
                        [
                          'applied',
                          'pending_manual',
                          'not_eligible',
                        ].includes(
                          app.status
                        )
                    ) && (
                      <PlatformBlock
                        platformName="Other Platforms"
                        platformKey="other"
                        applications={
                          otherApplications.filter(
                            app =>
                              [
                                'applied',
                                'pending_manual',
                                'not_eligible',
                              ].includes(
                                app.status
                              )
                          )
                        }
                        markingJobId={
                          markingJobId
                        }
                        onMarkApplied={
                          markApplicationAsApplied
                        }
                      />
                    )
                  }
                </>
              )
        }
      </main>
    </div>
  )
}