/**
 * Rule Editor Dialog - Modal for creating/editing individual rules
 */

import { useState } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../ui/dialog'
import { Button } from '../ui/button'
import { Input } from '../ui/input'
import { Label } from '../ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select'
import { Textarea } from '../ui/textarea'
import type { PolicyRule } from '../../lib/policyClient'

interface RuleEditorDialogProps {
  rule: PolicyRule | null
  open: boolean
  onClose: () => void
  onSave: (rule: PolicyRule) => void
}

export function RuleEditorDialog({ rule, open, onClose, onSave }: RuleEditorDialogProps) {
  const [ruleId, setRuleId] = useState(rule?.id || '')
  const [agent, setAgent] = useState(rule?.agent || 'inbox.triage')
  const [action, setAction] = useState(rule?.action || 'quarantine')
  const [effect, setEffect] = useState<'allow' | 'deny' | 'needs_approval'>(rule?.effect || 'allow')
  const [reason, setReason] = useState(rule?.reason || '')
  const [priority, setPriority] = useState(rule?.priority || 100)
  const enabled = rule?.enabled ?? true

  const handleSave = () => {
    const newRule: PolicyRule = {
      id: ruleId,
      agent,
      action,
      effect,
      reason,
      priority,
      enabled,
      conditions: rule?.conditions || {},
      budget: rule?.budget,
      tags: rule?.tags || [],
    }
    onSave(newRule)
  }

  const canSave = ruleId.trim() && agent.trim() && action.trim() && reason.trim() && reason.length >= 10

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>{rule ? 'Edit Rule' : 'Create New Rule'}</DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <Label htmlFor="ruleId">Rule ID *</Label>
              <Input
                id="ruleId"
                placeholder="e.g., inbox-quarantine-high-risk"
                value={ruleId}
                onChange={(e) => setRuleId(e.target.value)}
              />
            </div>
            <div>
              <Label htmlFor="priority">Priority *</Label>
              <Input
                id="priority"
                type="number"
                min="1"
                max="1000"
                value={priority}
                onChange={(e) => setPriority(parseInt(e.target.value) || 100)}
              />
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <Label htmlFor="agent">Agent *</Label>
              <Select value={agent} onValueChange={setAgent}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="inbox.triage">inbox.triage</SelectItem>
                  <SelectItem value="knowledge.search">knowledge.search</SelectItem>
                  <SelectItem value="planner.deploy">planner.deploy</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label htmlFor="action">Action *</Label>
              <Input
                id="action"
                placeholder="e.g., quarantine, reindex, deploy"
                value={action}
                onChange={(e) => setAction(e.target.value)}
              />
            </div>
          </div>

          <div>
            <Label htmlFor="effect">Effect *</Label>
            <Select value={effect} onValueChange={(v: any) => setEffect(v)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="allow">Allow</SelectItem>
                <SelectItem value="deny">Deny</SelectItem>
                <SelectItem value="needs_approval">Needs Approval</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div>
            <Label htmlFor="reason">Reason * (minimum 10 characters)</Label>
            <Textarea
              id="reason"
              placeholder="Explain why this rule exists and what it does"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              rows={3}
            />
            <p className="text-xs text-muted-foreground mt-1">
              {reason.length}/10 characters minimum
            </p>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={!canSave}>
            {rule ? 'Update' : 'Create'} Rule
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
