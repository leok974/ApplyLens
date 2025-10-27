/**
 * ActionsTray Component
 *
 * Right-side drawer that displays pending actions for human-in-the-loop approval.
 * Features:
 * - List of proposed actions with email context
 * - Approve/Reject buttons
 * - Screenshot capture on approve (using html2canvas)
 * - Expandable rationale display
 * - "Always do this" button for policy creation
 */

import { useState, useEffect } from "react"
import { X, CheckCircle2, XCircle, ChevronDown, ChevronUp, RefreshCw, Sparkles } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { useToast } from "@/components/ui/use-toast"
import {
  fetchTray,
  approveAction,
  rejectAction,
  alwaysDoThis,
  type ProposedAction,
} from "@/lib/actionsClient"
import html2canvas from "html2canvas"

interface ActionsTrayProps {
  isOpen: boolean
  onClose: () => void
}

const ACTION_LABELS: Record<string, { label: string; color: string }> = {
  label_email: { label: "Add Label", color: "bg-blue-500/20 text-blue-300" },
  archive_email: { label: "Archive", color: "bg-purple-500/20 text-purple-300" },
  move_to_folder: { label: "Move", color: "bg-indigo-500/20 text-indigo-300" },
  unsubscribe_via_header: { label: "Unsubscribe", color: "bg-orange-500/20 text-orange-300" },
  create_calendar_event: { label: "Create Event", color: "bg-green-500/20 text-green-300" },
  create_task: { label: "Create Task", color: "bg-teal-500/20 text-teal-300" },
  block_sender: { label: "Block Sender", color: "bg-red-500/20 text-red-300" },
  quarantine_attachment: { label: "Quarantine", color: "bg-yellow-500/20 text-yellow-300" },
}

export function ActionsTray({ isOpen, onClose }: ActionsTrayProps) {
  const [actions, setActions] = useState<ProposedAction[]>([])
  const [loading, setLoading] = useState(false)
  const [processing, setProcessing] = useState<number | null>(null)
  const { toast } = useToast()

  async function loadTray() {
    setLoading(true)
    try {
      const data = await fetchTray()
      setActions(data)
    } catch (error: any) {
      console.error("Failed to load tray:", error)
      toast({
        title: "❌ Failed to load actions",
        description: error?.message ?? String(error),
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (isOpen) {
      loadTray()
    }
  }, [isOpen])

  async function handleApprove(action: ProposedAction) {
    setProcessing(action.id)
    try {
      // Capture screenshot of the entire page
      let screenshotDataUrl: string | undefined
      try {
        const canvas = await html2canvas(document.body, {
          allowTaint: true,
          useCORS: true,
          logging: false,
          scale: 0.5, // Reduce size for faster upload
        })
        screenshotDataUrl = canvas.toDataURL("image/png")
      } catch (screenshotError) {
        console.warn("Screenshot capture failed:", screenshotError)
        // Continue without screenshot
      }

      const result = await approveAction(action.id, screenshotDataUrl)

      if (result.ok) {
        toast({
          title: "✅ Action approved",
          description: `${ACTION_LABELS[action.action]?.label || action.action} executed successfully`,
        })
        // Remove from tray
        setActions((prev) => prev.filter((a) => a.id !== action.id))
      } else {
        toast({
          title: "⚠️ Action failed",
          description: result.error || "Unknown error",
          variant: "destructive",
        })
      }
    } catch (error: any) {
      console.error("Approve error:", error)
      toast({
        title: "❌ Failed to approve action",
        description: error?.message ?? String(error),
        variant: "destructive",
      })
    } finally {
      setProcessing(null)
    }
  }

  async function handleReject(action: ProposedAction) {
    setProcessing(action.id)
    try {
      await rejectAction(action.id)
      toast({
        title: "🚫 Action rejected",
        description: "Action has been dismissed",
      })
      // Remove from tray
      setActions((prev) => prev.filter((a) => a.id !== action.id))
    } catch (error: any) {
      console.error("Reject error:", error)
      toast({
        title: "❌ Failed to reject action",
        description: error?.message ?? String(error),
        variant: "destructive",
      })
    } finally {
      setProcessing(null)
    }
  }

  async function handleAlways(action: ProposedAction) {
    setProcessing(action.id)
    try {
      const features = action.rationale?.features || {}
      const result = await alwaysDoThis(action.id, features)
      toast({
        title: "✨ Policy created",
        description: `New policy created (ID: ${result.policy_id}). Future similar emails will be handled automatically.`,
      })
      // Also approve this action
      await handleApprove(action)
    } catch (error: any) {
      console.error("Always error:", error)
      toast({
        title: "❌ Failed to create policy",
        description: error?.message ?? String(error),
        variant: "destructive",
      })
    } finally {
      setProcessing(null)
    }
  }

  if (!isOpen) return null

  return (
    <>
      {/* Backdrop - Click to close */}
      <div
        className="fixed inset-0 bg-black/50 z-40 cursor-pointer"
        onClick={onClose}
        aria-label="Close actions tray"
      />

      {/* Tray */}
      <div className="fixed right-0 top-0 h-full w-[420px] bg-neutral-900 border-l border-neutral-800 z-50 flex flex-col shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-neutral-800">
          <div className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-blue-400" />
            <h3 className="text-lg font-semibold text-neutral-100">
              Proposed Actions
            </h3>
            {actions.length > 0 && (
              <Badge variant="secondary" className="ml-1">
                {actions.length}
              </Badge>
            )}
          </div>
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="ghost"
              onClick={loadTray}
              disabled={loading}
            >
              <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            </Button>
            <Button size="sm" variant="ghost" onClick={onClose}>
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* Actions List */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {loading && actions.length === 0 && (
            <div className="text-center text-neutral-400 py-8">
              Loading actions...
            </div>
          )}

          {!loading && actions.length === 0 && (
            <div className="text-center text-neutral-400 py-8">
              <Sparkles className="h-12 w-12 mx-auto mb-3 opacity-50" />
              <p className="text-sm">No pending actions</p>
              <p className="text-xs mt-1 opacity-70">
                Actions will appear here when policies match emails
              </p>
            </div>
          )}

          {actions.map((action) => (
            <ActionCard
              key={action.id}
              action={action}
              processing={processing === action.id}
              onApprove={() => handleApprove(action)}
              onReject={() => handleReject(action)}
              onAlways={() => handleAlways(action)}
            />
          ))}
        </div>
      </div>
    </>
  )
}

interface ActionCardProps {
  action: ProposedAction
  processing: boolean
  onApprove: () => void
  onReject: () => void
  onAlways: () => void
}

function ActionCard({ action, processing, onApprove, onReject, onAlways }: ActionCardProps) {
  const [expanded, setExpanded] = useState(false)
  const actionInfo = ACTION_LABELS[action.action] || {
    label: action.action,
    color: "bg-neutral-500/20 text-neutral-300",
  }

  return (
    <div className="bg-neutral-800/50 border border-neutral-700 rounded-lg p-3 space-y-3">
      {/* Email Info */}
      <div className="space-y-1">
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-neutral-100 truncate">
              {action.email_subject || "No subject"}
            </p>
            <p className="text-xs text-neutral-400 truncate">
              {action.email_sender || "Unknown sender"}
            </p>
          </div>
          <Badge className={`${actionInfo.color} text-xs shrink-0`}>
            {actionInfo.label}
          </Badge>
        </div>

        {/* Confidence */}
        <div className="flex items-center gap-2">
          <div className="flex-1 h-1.5 bg-neutral-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-blue-500 transition-all"
              style={{ width: `${action.confidence * 100}%` }}
            />
          </div>
          <span className="text-xs text-neutral-400 tabular-nums">
            {Math.round(action.confidence * 100)}%
          </span>
        </div>
      </div>

      {/* Action Params */}
      {Object.keys(action.params || {}).length > 0 && (
        <div className="text-xs text-neutral-400 space-y-0.5">
          {Object.entries(action.params).map(([key, value]) => (
            <div key={key}>
              <span className="text-neutral-500">{key}:</span>{" "}
              <span className="text-neutral-300">{String(value)}</span>
            </div>
          ))}
        </div>
      )}

      {/* Policy */}
      {action.policy_name && (
        <div className="text-xs text-neutral-500">
          via <span className="text-neutral-400">{action.policy_name}</span>
        </div>
      )}

      {/* Rationale (Expandable) */}
      {action.rationale && (
        <div className="border-t border-neutral-700 pt-2">
          <button
            onClick={() => setExpanded(!expanded)}
            className="flex items-center justify-between w-full text-xs text-neutral-400 hover:text-neutral-200 transition-colors"
          >
            <span>Explain</span>
            {expanded ? (
              <ChevronUp className="h-3 w-3" />
            ) : (
              <ChevronDown className="h-3 w-3" />
            )}
          </button>

          {expanded && (
            <div className="mt-2 space-y-2 text-xs text-neutral-300">
              <p>{action.rationale.narrative || "No explanation available"}</p>
              {action.rationale.reasons && action.rationale.reasons.length > 0 && (
                <ul className="list-disc list-inside space-y-1 text-neutral-400">
                  {action.rationale.reasons.map((reason, idx) => (
                    <li key={idx}>{reason}</li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-2">
        <Button
          size="sm"
          variant="default"
          className="flex-1 bg-green-600 hover:bg-green-700"
          onClick={onApprove}
          disabled={processing}
        >
          <CheckCircle2 className="h-4 w-4 mr-1" />
          Approve
        </Button>
        <Button
          size="sm"
          variant="outline"
          className="flex-1"
          onClick={onReject}
          disabled={processing}
        >
          <XCircle className="h-4 w-4 mr-1" />
          Reject
        </Button>
      </div>

      {/* Always do this - Creates a learned policy */}
      <Button
        size="sm"
        variant="ghost"
        className="w-full text-xs text-purple-400 hover:text-purple-300 hover:bg-purple-500/10"
        onClick={onAlways}
        disabled={processing}
      >
        <Sparkles className="h-3 w-3 mr-1" />
        Always do this
      </Button>
    </div>
  )
}
