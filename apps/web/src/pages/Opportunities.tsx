import { useState, useEffect, useMemo } from 'react'
import { listOpportunities, getOpportunityDetail, JobOpportunity, OpportunityDetail, runBatchRoleMatch, OpportunityPriority } from '../api/opportunities'
import { getRoleMatch } from '../api/agent'
import { getCurrentResume, ResumeProfile } from '../api/opportunities'
import { Briefcase, MapPin, DollarSign, ExternalLink, Sparkles, AlertCircle, TrendingUp, CalendarClock, Flame, ThermometerSun, Snowflake } from 'lucide-react'
import { PriorityBadge } from '@/components/priority-badge'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'

type MatchBucket = 'perfect' | 'strong' | 'possible' | 'skip'

const MATCH_BUCKET_LABELS: Record<MatchBucket, string> = {
  perfect: 'Perfect Match',
  strong: 'Strong Match',
  possible: 'Possible Match',
  skip: 'Skip',
}

const MATCH_BUCKET_COLORS: Record<MatchBucket, string> = {
  perfect: 'bg-green-100 text-green-800 border-green-200',
  strong: 'bg-blue-100 text-blue-800 border-blue-200',
  possible: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  skip: 'bg-gray-100 text-gray-600 border-gray-200',
}

// Priority configuration
const PRIORITY_LABEL: Record<OpportunityPriority, string> = {
  high: 'Hot',
  medium: 'Warm',
  low: 'Cool',
}

const PRIORITY_ICON: Record<OpportunityPriority, JSX.Element> = {
  high: <Flame className="h-3 w-3 text-rose-500" />,
  medium: <ThermometerSun className="h-3 w-3 text-amber-500" />,
  low: <Snowflake className="h-3 w-3 text-slate-400" />,
}

const PRIORITY_BADGE_CLASS: Record<OpportunityPriority, string> = {
  high: 'bg-rose-500/10 text-rose-400 border-rose-500/30',
  medium: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
  low: 'bg-slate-700/60 text-slate-200 border-slate-600',
}

function formatRelative(dateStr?: string | null): string {
  if (!dateStr) return 'No contact yet'
  const date = new Date(dateStr)
  if (Number.isNaN(date.getTime())) return 'No contact yet'

  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

  if (diffDays <= 0) return 'Today'
  if (diffDays === 1) return '1 day ago'
  if (diffDays < 7) return `${diffDays} days ago`
  const weeks = Math.floor(diffDays / 7)
  if (weeks === 1) return '1 week ago'
  return `${weeks} weeks ago`
}

function formatLocation(opportunity: JobOpportunity): string {
  const parts: string[] = []
  if (opportunity.location) parts.push(opportunity.location)
  if (opportunity.remote_flag) parts.push('Remote')
  return parts.join(' • ') || 'Location not specified'
}

function formatSource(opportunity: JobOpportunity): string {
  if (!opportunity.source) return 'Email'
  return opportunity.source.replace(/_/g, ' ')
}

function PriorityLegend() {
  const items: { key: OpportunityPriority; description: string }[] = [
    {
      key: 'high',
      description: 'Interviews, offers, and time-sensitive outreach.',
    },
    {
      key: 'medium',
      description: 'Recent applications and promising recruiter messages.',
    },
    {
      key: 'low',
      description: 'Older or lower-signal leads you can review later.',
    },
  ]

  return (
    <div className="flex flex-wrap items-start gap-4 text-xs text-slate-400">
      {items.map((item) => (
        <div key={item.key} className="flex items-start gap-2">
          <Badge
            variant="outline"
            className={`mt-0.5 flex items-center gap-1 rounded-full border px-2 py-0.5 ${PRIORITY_BADGE_CLASS[item.key]}`}
          >
            {PRIORITY_ICON[item.key]}
            <span className="font-medium">{PRIORITY_LABEL[item.key]}</span>
          </Badge>
          <span className="max-w-xs leading-snug">{item.description}</span>
        </div>
      ))}
    </div>
  )
}

export default function Opportunities() {
  const [opportunities, setOpportunities] = useState<JobOpportunity[]>([])
  const [selectedOpportunity, setSelectedOpportunity] = useState<OpportunityDetail | null>(null)
  const [resume, setResume] = useState<ResumeProfile | null>(null)
  const [loading, setLoading] = useState(true)
  const [detailLoading, setDetailLoading] = useState(false)
  const [matchLoading, setMatchLoading] = useState(false)
  const [isBatchMatching, setIsBatchMatching] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Filters
  const [sourceFilter, setSourceFilter] = useState<string>('')
  const [matchFilter, setMatchFilter] = useState<MatchBucket | ''>('')
  const [search, setSearch] = useState('')

  // Group opportunities by priority
  const grouped = useMemo(() => {
    const base: Record<OpportunityPriority, JobOpportunity[]> = {
      high: [],
      medium: [],
      low: [],
    }

    if (!opportunities) return base

    for (const opp of opportunities) {
      const p = opp.priority ?? 'low'
      base[p].push(opp)
    }

    // Sort each bucket by created_at desc (most recent first)
    (Object.keys(base) as OpportunityPriority[]).forEach((p) => {
      base[p] = base[p].slice().sort((a, b) => {
        return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      })
    })

    return base
  }, [opportunities])

  const isLoading = loading
  const hasAny = grouped.high.length + grouped.medium.length + grouped.low.length > 0

  // Filter state for All vs Hot+Warm
  const [focusHotWarmOnly, setFocusHotWarmOnly] = useState(false)

  const visibleSections = useMemo(
    () =>
      (['high', 'medium', 'low'] as const).filter((priority) =>
        focusHotWarmOnly ? priority !== 'low' : true
      ),
    [focusHotWarmOnly]
  )

  // Load opportunities and resume on mount
  useEffect(() => {
    loadOpportunities()
    loadResume()
  }, [])

  async function loadOpportunities() {
    setLoading(true)
    setError(null)
    try {
      const data = await listOpportunities({
        source: sourceFilter || undefined,
        matchBucket: matchFilter || undefined,
      })
      setOpportunities(data)
    } catch (err) {
      console.error('Failed to load opportunities:', err)
      setError('Failed to load opportunities. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  async function loadResume() {
    try {
      const data = await getCurrentResume()
      setResume(data)
    } catch (err) {
      // Only log real errors (5xx, network issues)
      // 404 is handled by getCurrentResume returning null
      console.error('Failed to load resume:', err)
      setError('Failed to load resume. Please try again.')
    }
  }

  async function selectOpportunity(opp: JobOpportunity) {
    setDetailLoading(true)
    try {
      const detail = await getOpportunityDetail(opp.id)
      setSelectedOpportunity(detail)
    } catch (err) {
      console.error('Failed to load opportunity detail:', err)
    } finally {
      setDetailLoading(false)
    }
  }

  async function runRoleMatch(opportunityId: number) {
    if (!resume) {
      alert('Please upload a resume first to use role matching.')
      return
    }

    setMatchLoading(true)
    try {
      await getRoleMatch({ opportunityId })

      // Reload opportunity detail to show updated match
      const detail = await getOpportunityDetail(opportunityId)
      setSelectedOpportunity(detail)

      // Reload opportunities list to update match badges
      await loadOpportunities()
    } catch (err) {
      console.error('Failed to run role match:', err)
      alert('Failed to analyze role match. Please try again.')
    } finally {
      setMatchLoading(false)
    }
  }

  async function handleBatchMatch() {
    if (!resume) {
      alert('Please upload a resume first to use role matching.')
      return
    }

    setIsBatchMatching(true)
    try {
      const res = await runBatchRoleMatch(50)
      alert(`Successfully matched ${res.processed} opportunities`)

      // Reload opportunities list to show updated matches
      await loadOpportunities()

      // If detail panel is open, reload it too
      if (selectedOpportunity) {
        const detail = await getOpportunityDetail(selectedOpportunity.id)
        setSelectedOpportunity(detail)
      }
    } catch (err) {
      console.error('Failed to batch match:', err)
      alert('Failed to batch match opportunities. Please try again.')
    } finally {
      setIsBatchMatching(false)
    }
  }

  // Apply search filter client-side, then sort and group
  const filteredOpportunities = opportunities.filter((opp) => {
    if (search) {
      const searchLower = search.toLowerCase()
      return (
        opp.title.toLowerCase().includes(searchLower) ||
        opp.company.toLowerCase().includes(searchLower) ||
        (opp.location?.toLowerCase() || '').includes(searchLower)
      )
    }
    return true
  })

  const sortedOpportunities = sortOpportunities(filteredOpportunities)
  const groupedOpportunities = groupByPriority(sortedOpportunities)

  return (
    <div className="h-screen flex flex-col bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Job Opportunities</h1>
            <p className="text-sm text-gray-500 mt-1">
              {resume ? `Active resume: ${resume.headline || 'Untitled'}` : 'No active resume'}
            </p>
          </div>
          <div className="flex items-center gap-3">
            {resume && (
              <button
                type="button"
                onClick={handleBatchMatch}
                disabled={isBatchMatching}
                data-testid="opportunities-batch-match"
                className="rounded-full border border-amber-400/60 bg-amber-500/10 px-3 py-1 text-xs hover:bg-amber-500/20 disabled:opacity-50 transition-colors"
              >
                {isBatchMatching ? 'Matching…' : 'Match all new'}
              </button>
            )}
            {!resume && (
              <a
                href="/settings"
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
              >
                Upload Resume
              </a>
            )}
          </div>
        </div>

        {/* Filters */}
        <div className="mt-4 flex items-center gap-3">
          <input
            type="text"
            placeholder="Search by title, company, or location..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />

          <select
            value={sourceFilter}
            onChange={(e) => {
              setSourceFilter(e.target.value)
              setOpportunities([])
              loadOpportunities()
            }}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">All Sources</option>
            <option value="indeed">Indeed</option>
            <option value="linkedin">LinkedIn</option>
            <option value="handshake">Handshake</option>
            <option value="ziprecruiter">ZipRecruiter</option>
          </select>

          <select
            value={matchFilter}
            onChange={(e) => {
              setMatchFilter(e.target.value as MatchBucket | '')
              setOpportunities([])
              loadOpportunities()
            }}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">All Matches</option>
            <option value="perfect">Perfect</option>
            <option value="strong">Strong</option>
            <option value="possible">Possible</option>
            <option value="skip">Skip</option>
          </select>
        </div>
      </div>

      {/* Content: List + Detail Split */}
      <div className="flex-1 flex overflow-hidden">
        {/* List Panel */}
        <div className="w-1/2 border-r border-slate-800 overflow-y-auto bg-slate-950">
          <div className="p-6">
            {isLoading && (
              <div className="space-y-4">
                <Skeleton className="h-8 w-40 bg-slate-800" />
                <div className="grid gap-3">
                  {Array.from({ length: 6 }).map((_, i) => (
                    <Card key={i} className="border-slate-800 bg-slate-900/60">
                      <CardHeader className="space-y-2 pb-3">
                        <Skeleton className="h-4 w-3/4 bg-slate-700" />
                        <Skeleton className="h-3 w-1/2 bg-slate-700" />
                      </CardHeader>
                      <CardContent className="space-y-2">
                        <Skeleton className="h-3 w-full bg-slate-700" />
                        <Skeleton className="h-3 w-2/3 bg-slate-700" />
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </div>
            )}

            {error && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                <div className="text-sm text-red-800">{error}</div>
              </div>
            )}

            {!isLoading && !error && !hasAny && (
              <div className="flex flex-col items-center justify-center py-16 text-center text-slate-300">
                <div className="mb-3 text-sm font-semibold uppercase tracking-wide text-emerald-400">
                  No opportunities yet
                </div>
                <p className="max-w-md text-sm text-slate-400">
                  Once ApplyLens sees real roles in your inbox, they'll show up here
                  grouped by urgency. Try syncing the last 60 days of Gmail and
                  searching for "interview" or "role".
                </p>
              </div>
            )}

            {!isLoading && !error && hasAny && (
              <div className="space-y-8">
                {/* Legend + Filter Bar */}
                <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                  <PriorityLegend />

                  <div className="inline-flex items-center gap-2">
                    <span className="text-xs text-slate-400">Focus</span>
                    <div className="inline-flex rounded-full border border-slate-700 bg-slate-900/70 p-0.5 text-xs">
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        className={`h-7 rounded-full px-3 text-xs ${
                          !focusHotWarmOnly
                            ? 'bg-slate-200 text-slate-900 shadow-sm'
                            : 'text-slate-300'
                        }`}
                        onClick={() => setFocusHotWarmOnly(false)}
                      >
                        All
                      </Button>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        className={`h-7 rounded-full px-3 text-xs ${
                          focusHotWarmOnly
                            ? 'bg-emerald-500 text-emerald-950 shadow-sm'
                            : 'text-slate-300'
                        }`}
                        onClick={() => setFocusHotWarmOnly(true)}
                      >
                        Hot + Warm
                      </Button>
                    </div>
                  </div>
                </div>

                {visibleSections.map((priority) => {
                  const list = grouped[priority]
                  if (!list.length) return null

                  const descriptions = {
                    high: 'Interviews, offers, and time-sensitive outreach.',
                    medium: 'Recent applications and promising recruiter messages.',
                    low: 'Older or lower-signal leads for later review.',
                  }

                  return (
                    <section key={priority} className="space-y-3">
                      <div className="flex items-center justify-between gap-2">
                        <div>
                          <div className="flex items-center gap-2">
                            <Badge
                              variant="outline"
                              className={`flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium ${PRIORITY_BADGE_CLASS[priority]}`}
                            >
                              {PRIORITY_ICON[priority]}
                              <span>{PRIORITY_LABEL[priority]}</span>
                            </Badge>
                            <span className="text-xs text-slate-400">
                              {list.length} opportunit{list.length === 1 ? 'y' : 'ies'}
                            </span>
                          </div>
                          <p className="mt-1 text-xs text-slate-400">
                            {descriptions[priority]}
                          </p>
                        </div>
                      </div>

                      <div className="grid gap-3">
                        {list.map((opp) => (
                          <Card
                            key={opp.id}
                            onClick={() => selectOpportunity(opp)}
                            className={`group cursor-pointer border-slate-800 bg-slate-900/70 transition hover:border-emerald-500/60 hover:bg-slate-900 ${
                              selectedOpportunity?.id === opp.id ? 'border-emerald-500/60 bg-slate-900' : ''
                            }`}
                          >
                            <CardHeader className="space-y-1 pb-3">
                              <CardTitle className="flex items-start justify-between gap-2 text-sm font-semibold text-slate-50">
                                <span className="line-clamp-2">{opp.title}</span>
                              </CardTitle>
                              <div className="flex flex-wrap items-center gap-1.5 text-xs text-slate-400">
                                <span className="font-medium text-slate-200">
                                  {opp.company || 'Unknown company'}
                                </span>
                                <span className="text-slate-600">•</span>
                                <span>{formatLocation(opp)}</span>
                              </div>
                            </CardHeader>

                            <CardContent className="space-y-3 text-xs">
                              <div className="flex flex-wrap gap-1.5">
                                <Badge
                                  variant="outline"
                                  className={`rounded-full border px-2 py-0.5 text-[11px] ${PRIORITY_BADGE_CLASS[opp.priority]}`}
                                >
                                  {PRIORITY_ICON[opp.priority]}
                                  <span className="ml-1">
                                    {PRIORITY_LABEL[opp.priority]}
                                  </span>
                                </Badge>

                                <Badge
                                  variant="outline"
                                  className="rounded-full border-slate-700 bg-slate-900/70 text-[11px] text-slate-200"
                                >
                                  Source: {formatSource(opp)}
                                </Badge>

                                {opp.match_bucket && (
                                  <Badge
                                    variant="outline"
                                    className="rounded-full border-emerald-700/60 bg-emerald-500/5 text-[11px] text-emerald-300"
                                  >
                                    {opp.match_bucket}
                                    {typeof opp.match_score === 'number' && (
                                      <span className="ml-1 opacity-80">
                                        ({Math.round(opp.match_score)}%)
                                      </span>
                                    )}
                                  </Badge>
                                )}
                              </div>

                              <div className="flex items-center justify-between text-[11px] text-slate-400">
                                <span>
                                  Last contact:{' '}
                                  <span className="text-slate-200">
                                    {formatRelative(opp.created_at)}
                                  </span>
                                </span>
                                {opp.posted_at && (
                                  <span className="hidden md:inline">
                                    Posted:{' '}
                                    {new Date(opp.posted_at).toLocaleDateString(undefined, {
                                      month: 'short',
                                      day: 'numeric',
                                    })}
                                  </span>
                                )}
                              </div>

                              <div className="flex items-center justify-between pt-1">
                                <div className="flex flex-wrap gap-1 text-[11px] text-slate-500">
                                  {opp.level && <span>{opp.level}</span>}
                                  {opp.level && opp.tech_stack && (
                                    <span className="text-slate-700">•</span>
                                  )}
                                  {opp.tech_stack && (
                                    <span className="line-clamp-1">{opp.tech_stack.join(', ')}</span>
                                  )}
                                </div>

                                {opp.apply_url && (
                                  <Button
                                    asChild
                                    variant="ghost"
                                    size="icon"
                                    className="h-7 w-7 text-slate-300 hover:text-emerald-300"
                                  >
                                    <a
                                      href={opp.apply_url}
                                      target="_blank"
                                      rel="noreferrer"
                                      aria-label="Open job link"
                                      onClick={(e) => e.stopPropagation()}
                                    >
                                      <ExternalLink className="h-3.5 w-3.5" />
                                    </a>
                                  </Button>
                                )}
                              </div>
                            </CardContent>
                          </Card>
                        ))}
                      </div>
                    </section>
                  )
                })}
              </div>
            )}
          </div>
        </div>

        {/* Detail Panel */}
        <div className="w-1/2 overflow-y-auto bg-white">
          {!selectedOpportunity && (
            <div className="flex items-center justify-center h-full text-gray-400">
              <div className="text-center">
                <Briefcase className="w-16 h-16 mx-auto mb-3 text-gray-300" />
                <p>Select an opportunity to view details</p>
              </div>
            </div>
          )}

          {detailLoading && (
            <div className="flex items-center justify-center h-full">
              <div className="text-gray-500">Loading details...</div>
            </div>
          )}

          {selectedOpportunity && !detailLoading && (
            <div className="p-6">
              {/* Header */}
              <div className="mb-6">
                <h2 className="text-2xl font-bold text-gray-900">{selectedOpportunity.title}</h2>
                <p className="text-lg text-gray-600 mt-1">{selectedOpportunity.company}</p>

                <div className="flex items-center gap-4 mt-3 text-sm text-gray-600">
                  {selectedOpportunity.location && (
                    <span className="flex items-center gap-1">
                      <MapPin className="w-4 h-4" />
                      {selectedOpportunity.location}
                    </span>
                  )}
                  {selectedOpportunity.level && (
                    <span className="px-2 py-1 bg-gray-100 rounded">{selectedOpportunity.level}</span>
                  )}
                  {selectedOpportunity.remote_flag && (
                    <span className="px-2 py-1 bg-green-100 text-green-700 rounded">Remote</span>
                  )}
                </div>

                {selectedOpportunity.salary_text && (
                  <div className="mt-3 flex items-center gap-2 text-gray-700">
                    <DollarSign className="w-4 h-4" />
                    <span className="font-medium">{selectedOpportunity.salary_text}</span>
                  </div>
                )}

                {selectedOpportunity.apply_url && (
                  <a
                    href={selectedOpportunity.apply_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mt-4 inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    Apply Now
                    <ExternalLink className="w-4 h-4" />
                  </a>
                )}
              </div>

              {/* Tech Stack */}
              {selectedOpportunity.tech_stack && selectedOpportunity.tech_stack.length > 0 && (
                <div className="mb-6">
                  <h3 className="text-sm font-semibold text-gray-700 mb-2">Tech Stack</h3>
                  <div className="flex flex-wrap gap-2">
                    {selectedOpportunity.tech_stack.map((tech, idx) => (
                      <span key={idx} className="px-3 py-1 bg-gray-100 text-gray-700 rounded-lg text-sm">
                        {tech}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Match Analysis */}
              <div className="border-t border-gray-200 pt-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold text-gray-900">Role Match Analysis</h3>
                  <button
                    onClick={() => runRoleMatch(selectedOpportunity.id)}
                    disabled={matchLoading || !resume}
                    className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 text-sm"
                  >
                    <Sparkles className="w-4 h-4" />
                    {matchLoading ? 'Analyzing...' : selectedOpportunity.match ? 'Re-analyze' : 'Analyze Match'}
                  </button>
                </div>

                {!resume && (
                  <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                    <p className="text-sm text-yellow-800">
                      Upload a resume to get AI-powered match analysis for this role.
                    </p>
                  </div>
                )}

                {resume && !selectedOpportunity.match && (
                  <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                    <p className="text-sm text-gray-600">
                      Click "Analyze Match" to get AI-powered insights on how well you match this role.
                    </p>
                  </div>
                )}

                {selectedOpportunity.match && (
                  <div className="space-y-4">
                    {/* Match Score */}
                    <div className={`p-4 rounded-lg border ${MATCH_BUCKET_COLORS[selectedOpportunity.match.bucket]}`}>
                      <div className="flex items-center justify-between">
                        <div>
                          <div className="text-sm font-medium mb-1">Match Quality</div>
                          <div className="text-2xl font-bold">{MATCH_BUCKET_LABELS[selectedOpportunity.match.bucket]}</div>
                        </div>
                        <div className="text-right">
                          <div className="text-sm font-medium mb-1">Score</div>
                          <div className="text-2xl font-bold">{selectedOpportunity.match.score}/100</div>
                        </div>
                      </div>
                    </div>

                    {/* Reasons */}
                    {selectedOpportunity.match.reasons && selectedOpportunity.match.reasons.length > 0 && (
                      <div>
                        <h4 className="font-semibold text-gray-900 mb-2 flex items-center gap-2">
                          <TrendingUp className="w-4 h-4 text-green-600" />
                          Why You're a Good Match
                        </h4>
                        <ul className="space-y-2">
                          {selectedOpportunity.match.reasons.map((reason, idx) => (
                            <li key={idx} className="flex items-start gap-2 text-sm text-gray-700">
                              <span className="text-green-600 mt-0.5">✓</span>
                              <span>{reason}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Missing Skills */}
                    {selectedOpportunity.match.missing_skills && selectedOpportunity.match.missing_skills.length > 0 && (
                      <div>
                        <h4 className="font-semibold text-gray-900 mb-2 flex items-center gap-2">
                          <AlertCircle className="w-4 h-4 text-yellow-600" />
                          Skills to Highlight or Develop
                        </h4>
                        <div className="flex flex-wrap gap-2">
                          {selectedOpportunity.match.missing_skills.map((skill, idx) => (
                            <span key={idx} className="px-3 py-1 bg-yellow-50 text-yellow-800 border border-yellow-200 rounded-lg text-sm">
                              {skill}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Resume Tweaks */}
                    {selectedOpportunity.match.resume_tweaks && selectedOpportunity.match.resume_tweaks.length > 0 && (
                      <div>
                        <h4 className="font-semibold text-gray-900 mb-2 flex items-center gap-2">
                          <Sparkles className="w-4 h-4 text-purple-600" />
                          Resume Optimization Tips
                        </h4>
                        <ul className="space-y-2">
                          {selectedOpportunity.match.resume_tweaks.map((tweak, idx) => (
                            <li key={idx} className="flex items-start gap-2 text-sm text-gray-700">
                              <span className="text-purple-600 mt-0.5">•</span>
                              <span>{tweak}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Metadata */}
              <div className="border-t border-gray-200 mt-6 pt-4">
                <div className="text-xs text-gray-500 space-y-1">
                  <div>Source: {selectedOpportunity.source}</div>
                  {selectedOpportunity.posted_at && (
                    <div>Posted: {new Date(selectedOpportunity.posted_at).toLocaleDateString()}</div>
                  )}
                  <div>Added: {new Date(selectedOpportunity.created_at).toLocaleDateString()}</div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
