import { useState, useEffect } from 'react'
import { listOpportunities, getOpportunityDetail, JobOpportunity, OpportunityDetail } from '../api/opportunities'
import { getRoleMatch } from '../api/agent'
import { getCurrentResume, ResumeProfile } from '../api/opportunities'
import { Briefcase, MapPin, DollarSign, ExternalLink, Sparkles, AlertCircle, TrendingUp } from 'lucide-react'

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

export default function Opportunities() {
  const [opportunities, setOpportunities] = useState<JobOpportunity[]>([])
  const [selectedOpportunity, setSelectedOpportunity] = useState<OpportunityDetail | null>(null)
  const [resume, setResume] = useState<ResumeProfile | null>(null)
  const [loading, setLoading] = useState(true)
  const [detailLoading, setDetailLoading] = useState(false)
  const [matchLoading, setMatchLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Filters
  const [sourceFilter, setSourceFilter] = useState<string>('')
  const [matchFilter, setMatchFilter] = useState<MatchBucket | ''>('')
  const [search, setSearch] = useState('')

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
      console.error('Failed to load resume:', err)
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

  // Apply search filter client-side
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
        <div className="w-1/2 border-r border-gray-200 overflow-y-auto bg-white">
          {loading && (
            <div className="flex items-center justify-center h-64">
              <div className="text-gray-500">Loading opportunities...</div>
            </div>
          )}

          {error && (
            <div className="p-6">
              <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                <div className="text-sm text-red-800">{error}</div>
              </div>
            </div>
          )}

          {!loading && !error && filteredOpportunities.length === 0 && (
            <div className="flex flex-col items-center justify-center h-64 text-gray-500">
              <Briefcase className="w-12 h-12 mb-3 text-gray-400" />
              <p className="text-lg font-medium">No opportunities yet</p>
              <p className="text-sm text-gray-400 mt-1">Job aggregator emails will appear here</p>
            </div>
          )}

          {!loading && !error && filteredOpportunities.length > 0 && (
            <div className="divide-y divide-gray-100">
              {filteredOpportunities.map((opp) => (
                <div
                  key={opp.id}
                  onClick={() => selectOpportunity(opp)}
                  className={`p-4 cursor-pointer hover:bg-gray-50 transition-colors ${
                    selectedOpportunity?.id === opp.id ? 'bg-blue-50 border-l-4 border-blue-600' : ''
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1 min-w-0">
                      <h3 className="font-semibold text-gray-900 truncate">{opp.title}</h3>
                      <p className="text-sm text-gray-600 mt-1">{opp.company}</p>

                      <div className="flex items-center gap-3 mt-2 text-xs text-gray-500">
                        {opp.location && (
                          <span className="flex items-center gap-1">
                            <MapPin className="w-3 h-3" />
                            {opp.location}
                          </span>
                        )}
                        {opp.remote_flag && (
                          <span className="px-2 py-0.5 bg-green-100 text-green-700 rounded">Remote</span>
                        )}
                        {opp.salary_text && (
                          <span className="flex items-center gap-1">
                            <DollarSign className="w-3 h-3" />
                            {opp.salary_text}
                          </span>
                        )}
                      </div>
                    </div>

                    {opp.match_bucket && (
                      <div className={`px-2 py-1 rounded border text-xs font-medium ${MATCH_BUCKET_COLORS[opp.match_bucket]}`}>
                        {MATCH_BUCKET_LABELS[opp.match_bucket]}
                      </div>
                    )}
                  </div>

                  {opp.tech_stack && opp.tech_stack.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {opp.tech_stack.slice(0, 5).map((tech, idx) => (
                        <span key={idx} className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded text-xs">
                          {tech}
                        </span>
                      ))}
                      {opp.tech_stack.length > 5 && (
                        <span className="px-2 py-0.5 text-gray-400 text-xs">
                          +{opp.tech_stack.length - 5} more
                        </span>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
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
