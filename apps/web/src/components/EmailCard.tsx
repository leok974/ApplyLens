import { Email, createApplicationFromEmail } from '../lib/api'
import { useNavigate } from 'react-router-dom'
import { useState } from 'react'

const LABEL_COLORS: Record<string, string> = {
  interview: 'bg-blue-100 text-blue-800',
  offer: 'bg-green-100 text-green-800',
  rejection: 'bg-red-100 text-red-800',
  application_receipt: 'bg-purple-100 text-purple-800',
  newsletter_ads: 'bg-gray-100 text-gray-600',
}

const LABEL_ICONS: Record<string, string> = {
  interview: '📅',
  offer: '🎉',
  rejection: '❌',
  application_receipt: '✅',
  newsletter_ads: '📰',
}

export default function EmailCard({ e }: { e: Email }) {
  const sender = e.sender || e.from_addr
  const navigate = useNavigate()
  const [creating, setCreating] = useState(false)
  
  const handleCreateApplication = async () => {
    if (!e.id) return
    setCreating(true)
    try {
      const result = await createApplicationFromEmail(e.id)
      navigate(`/tracker?selected=${result.application_id}`)
    } catch (error) {
      console.error('Failed to create application:', error)
      alert('Failed to create application. Email may lack company/role information.')
      setCreating(false)
    }
  }
  
  return (
    <div className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow bg-white">
      <div className="flex justify-between items-start mb-2">
        <div className="flex-1">
          <h3 className="font-semibold text-lg">{e.subject || '(No Subject)'}</h3>
          <p className="text-sm text-gray-600">
            From: <span className="font-mono">{sender}</span>
            {e.recipient && (
              <span> → <span className="font-mono">{e.recipient}</span></span>
            )}
          </p>
          {/* Show company/role if extracted */}
          {(e.company || e.role) && (
            <p className="text-sm text-gray-500 mt-1">
              {e.company && <span className="font-medium">{e.company}</span>}
              {e.company && e.role && <span> • </span>}
              {e.role && <span>{e.role}</span>}
            </p>
          )}
        </div>
        <div className="text-xs text-gray-500">
          {new Date(e.received_at).toLocaleDateString('en-US', { 
            month: 'short', 
            day: 'numeric',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
          })}
        </div>
      </div>
      
      {/* Body Preview */}
      {(e.body_preview || e.body_text) && (
        <p className="text-sm text-gray-700 mb-3 line-clamp-2">
          {e.body_preview || e.body_text}
        </p>
      )}
      
      {/* Labels */}
      <div className="flex gap-2 flex-wrap mb-3">
        {/* Legacy label */}
        {e.label && (
          <span className="px-2 py-1 rounded text-xs bg-blue-50 text-blue-700">
            {e.label}
          </span>
        )}
        
        {/* Heuristic labels */}
        {e.label_heuristics && e.label_heuristics.map(label => (
          <span 
            key={label}
            className={`px-2 py-1 rounded text-xs font-medium ${LABEL_COLORS[label] || 'bg-gray-100 text-gray-600'}`}
          >
            {LABEL_ICONS[label]} {label.replace('_', ' ')}
          </span>
        ))}
        
        {/* Gmail labels */}
        {e.labels && e.labels.length > 0 && (
          <span className="px-2 py-1 rounded text-xs bg-gray-50 text-gray-500 border border-gray-200">
            📧 {e.labels.length} Gmail label{e.labels.length !== 1 ? 's' : ''}
          </span>
        )}
      </div>
      
      {/* Application Actions */}
      <div className="flex gap-2 mt-3 pt-3 border-t border-gray-100">
        {e.application_id ? (
          <a
            href={`/tracker?selected=${e.application_id}`}
            className="text-sm text-blue-600 hover:text-blue-800 font-medium flex items-center gap-1"
          >
            📋 View Application
          </a>
        ) : (
          e.company && (
            <button
              onClick={handleCreateApplication}
              disabled={creating}
              className="text-sm px-3 py-1 bg-green-500 text-white rounded hover:bg-green-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors flex items-center gap-1"
            >
              {creating ? '⏳ Creating...' : '➕ Create Application'}
            </button>
          )
        )}
        {e.source && (
          <span className="text-xs px-2 py-1 bg-indigo-50 text-indigo-700 rounded">
            via {e.source}
          </span>
        )}
      </div>
    </div>
  )
}
