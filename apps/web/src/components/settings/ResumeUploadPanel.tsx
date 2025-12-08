import { useState, useEffect, useRef } from 'react'
import { uploadResume, getCurrentResume, listResumes, activateResume, ResumeProfile } from '../../api/opportunities'
import { Upload, FileText, Check, AlertCircle, Loader2 } from 'lucide-react'
import { ResumeStatusPill } from '../profile/ResumeStatusPill'

export function ResumeUploadPanel() {
  const [currentResume, setCurrentResume] = useState<ResumeProfile | null>(null)
  const [allResumes, setAllResumes] = useState<ResumeProfile[]>([])
  const [uploading, setUploading] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    loadResumes()
  }, [])

  async function loadResumes() {
    setLoading(true)
    setError(null)
    try {
      const [current, all] = await Promise.all([
        getCurrentResume(),
        listResumes(),
      ])
      setCurrentResume(current)
      setAllResumes(all)
    } catch (err) {
      console.error('Failed to load resumes:', err)
      setError('Failed to load resumes. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  async function handleFileSelect(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    if (!file) return

    // Validate file type
    const validTypes = ['.pdf', '.docx', '.txt']
    const fileExt = '.' + file.name.split('.').pop()?.toLowerCase()
    if (!validTypes.includes(fileExt)) {
      setError('Unsupported file type. Please upload a PDF, DOCX, or TXT file.')
      return
    }

    // Validate file size (max 10MB)
    if (file.size > 10 * 1024 * 1024) {
      setError('File too large. Maximum size is 10MB.')
      return
    }

    setUploading(true)
    setError(null)

    try {
      const resume = await uploadResume(file)
      setCurrentResume(resume)
      await loadResumes()

      // Clear file input
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    } catch (err: any) {
      console.error('Failed to upload resume:', err)
      setError(err.message || 'Failed to upload resume. Please try again.')
    } finally {
      setUploading(false)
    }
  }

  async function handleActivateResume(resumeId: number) {
    try {
      const resume = await activateResume(resumeId)
      setCurrentResume(resume)
      await loadResumes()
    } catch (err) {
      console.error('Failed to activate resume:', err)
      setError('Failed to activate resume. Please try again.')
    }
  }

  if (loading) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6">
        <div className="flex items-center justify-center py-8">
          <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm">
      {/* Header */}
      <div className="border-b border-gray-200 dark:border-gray-700 px-6 py-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Resume</h2>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              Upload your resume for AI-powered job matching
            </p>
          </div>
          <ResumeStatusPill
            resumeUploadedAt={currentResume?.created_at}
            skillsCount={currentResume?.skills?.length ?? 0}
            rolesCount={currentResume?.target_roles?.length ?? 0}
          />
        </div>
      </div>

      <div className="p-6 space-y-6">
        {/* Error Display */}
        {error && (
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-red-800 dark:text-red-300">{error}</div>
          </div>
        )}

        {/* Upload Button */}
        <div>
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.docx,.txt"
            onChange={handleFileSelect}
            className="hidden"
            id="resume-upload"
            disabled={uploading}
          />
          <label
            htmlFor="resume-upload"
            className={`inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors cursor-pointer ${
              uploading ? 'opacity-50 cursor-not-allowed' : ''
            }`}
          >
            {uploading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Uploading...
              </>
            ) : (
              <>
                <Upload className="w-4 h-4" />
                Upload Resume
              </>
            )}
          </label>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
            Supported formats: PDF, DOCX, TXT (max 10MB)
          </p>
        </div>

        {/* Current Active Resume */}
        {currentResume && (
          <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
            <div className="flex items-start gap-3">
              <div className="flex-shrink-0">
                <div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center">
                  <FileText className="w-5 h-5 text-white" />
                </div>
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <h3 className="font-semibold text-gray-900 dark:text-gray-100">
                    {currentResume.headline || 'Untitled Resume'}
                  </h3>
                  <span className="px-2 py-0.5 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 text-xs font-medium rounded flex items-center gap-1">
                    <Check className="w-3 h-3" />
                    Active
                  </span>
                </div>
                {currentResume.summary && (
                  <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-2 mb-2">
                    {currentResume.summary}
                  </p>
                )}
                {currentResume.skills && currentResume.skills.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-2">
                    {currentResume.skills.slice(0, 8).map((skill, idx) => (
                      <span
                        key={idx}
                        className="px-2 py-0.5 bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-600 rounded text-xs"
                      >
                        {skill}
                      </span>
                    ))}
                    {currentResume.skills.length > 8 && (
                      <span className="px-2 py-0.5 text-gray-500 dark:text-gray-400 text-xs">
                        +{currentResume.skills.length - 8} more
                      </span>
                    )}
                  </div>
                )}
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
                  Uploaded {new Date(currentResume.created_at).toLocaleDateString()}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Previous Resumes */}
        {allResumes.length > 1 && (
          <div>
            <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3">
              Previous Resumes
            </h3>
            <div className="space-y-2">
              {allResumes
                .filter((r) => !r.is_active)
                .map((resume) => (
                  <div
                    key={resume.id}
                    className="border border-gray-200 dark:border-gray-700 rounded-lg p-3 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex-1 min-w-0">
                        <h4 className="font-medium text-gray-900 dark:text-gray-100 text-sm">
                          {resume.headline || 'Untitled Resume'}
                        </h4>
                        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                          Uploaded {new Date(resume.created_at).toLocaleDateString()}
                        </p>
                      </div>
                      <button
                        onClick={() => handleActivateResume(resume.id)}
                        className="px-3 py-1 text-xs font-medium text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded transition-colors"
                      >
                        Activate
                      </button>
                    </div>
                  </div>
                ))}
            </div>
          </div>
        )}

        {/* No Resume State */}
        {!currentResume && allResumes.length === 0 && !uploading && (
          <div className="text-center py-8">
            <FileText className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
            <p className="text-gray-600 dark:text-gray-400 text-sm">
              No resume uploaded yet
            </p>
            <p className="text-gray-500 dark:text-gray-500 text-xs mt-1">
              Upload your resume to enable AI-powered job matching
            </p>
          </div>
        )}

        {/* Info Box */}
        <div className="bg-gray-50 dark:bg-gray-700/50 border border-gray-200 dark:border-gray-600 rounded-lg p-4">
          <h4 className="font-medium text-gray-900 dark:text-gray-100 text-sm mb-2">
            How it works
          </h4>
          <ul className="space-y-1 text-xs text-gray-600 dark:text-gray-400">
            <li>• Upload your resume in PDF, DOCX, or TXT format</li>
            <li>• AI extracts your skills, experience, and qualifications</li>
            <li>• Get match scores for job opportunities from aggregator emails</li>
            <li>• Receive personalized resume optimization tips for each role</li>
          </ul>
        </div>

        {/* Privacy Notice */}
        <div className="text-xs text-gray-500 dark:text-gray-400">
          <strong>Privacy:</strong> Your resume is stored securely and only used for matching analysis.
          We never share your resume with third parties or use it to generate content without your permission.
        </div>
      </div>
    </div>
  )
}
