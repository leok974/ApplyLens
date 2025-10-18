/**
 * Policy Bundle Editor - Main editing interface
 * 
 * Features:
 * - Create/edit policy bundles
 * - Rule builder with visual interface
 * - Real-time linting
 * - What-if simulation
 * - Version management
 */

import { useState, useEffect } from 'react'
import { Save, X, Play, AlertTriangle, CheckCircle2 } from 'lucide-react'
import { Button } from '../ui/button'
import { Input } from '../ui/input'
import { Label } from '../ui/label'
import { Textarea } from '../ui/textarea'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs'
import { Alert, AlertDescription } from '../ui/alert'
import { RuleBuilder } from './RuleBuilder'
import { LintPanel } from './LintPanel'
import { SimulationPanel } from './SimulationPanel'
import {
  createBundle,
  updateBundle,
  lintRules,
  type PolicyBundle,
  type PolicyRule,
  type LintResult,
} from '../../lib/policyClient'
import { useToast } from '../ui/use-toast'

interface PolicyBundleEditorProps {
  bundle: PolicyBundle | null
  onSave: () => void
  onCancel: () => void
}

export function PolicyBundleEditor({
  bundle,
  onSave,
  onCancel,
}: PolicyBundleEditorProps) {
  const { toast } = useToast()
  const [version, setVersion] = useState(bundle?.version || '')
  const [notes, setNotes] = useState(bundle?.notes || '')
  const [rules, setRules] = useState<PolicyRule[]>(bundle?.rules || [])
  const [lintResult, setLintResult] = useState<LintResult | null>(null)
  const [saving, setSaving] = useState(false)
  const [linting, setLinting] = useState(false)

  // Auto-lint when rules change
  useEffect(() => {
    const timer = setTimeout(() => {
      if (rules.length > 0) {
        runLint()
      }
    }, 500) // Debounce 500ms

    return () => clearTimeout(timer)
  }, [rules])

  const runLint = async () => {
    try {
      setLinting(true)
      const result = await lintRules(rules)
      setLintResult(result)
    } catch (err) {
      console.error('Lint failed:', err)
    } finally {
      setLinting(false)
    }
  }

  const handleSave = async () => {
    if (!version.trim()) {
      toast({
        title: 'Validation error',
        description: 'Version is required',
        variant: 'destructive',
      })
      return
    }

    if (rules.length === 0) {
      toast({
        title: 'Validation error',
        description: 'At least one rule is required',
        variant: 'destructive',
      })
      return
    }

    if (lintResult && lintResult.errors.length > 0) {
      toast({
        title: 'Lint errors',
        description: 'Fix all lint errors before saving',
        variant: 'destructive',
      })
      return
    }

    try {
      setSaving(true)

      if (bundle) {
        // Update existing
        await updateBundle(bundle.id, { rules, notes })
        toast({
          title: 'Bundle updated',
          description: `Successfully updated v${version}`,
        })
      } else {
        // Create new
        await createBundle({
          version,
          rules,
          notes,
          created_by: 'current-user', // TODO: Get from auth context
        })
        toast({
          title: 'Bundle created',
          description: `Successfully created v${version}`,
        })
      }

      onSave()
    } catch (err: any) {
      toast({
        title: 'Save failed',
        description: err.message || 'Failed to save bundle',
        variant: 'destructive',
      })
    } finally {
      setSaving(false)
    }
  }

  const handleAddRule = (rule: PolicyRule) => {
    setRules([...rules, rule])
  }

  const handleUpdateRule = (index: number, rule: PolicyRule) => {
    const newRules = [...rules]
    newRules[index] = rule
    setRules(newRules)
  }

  const handleDeleteRule = (index: number) => {
    setRules(rules.filter((_, i) => i !== index))
  }

  const canSave = version.trim() && rules.length > 0 && (!lintResult || lintResult.errors.length === 0)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">
            {bundle ? `Edit Bundle v${bundle.version}` : 'Create New Bundle'}
          </h2>
          <p className="text-sm text-muted-foreground">
            {bundle ? 'Modify existing bundle' : 'Create a new policy bundle'}
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={onCancel}>
            <X className="mr-2 h-4 w-4" />
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={!canSave || saving}>
            <Save className="mr-2 h-4 w-4" />
            {saving ? 'Saving...' : 'Save Bundle'}
          </Button>
        </div>
      </div>

      {/* Bundle Metadata */}
      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <Label htmlFor="version">Version *</Label>
          <Input
            id="version"
            placeholder="e.g., 2.1.0"
            value={version}
            onChange={(e) => setVersion(e.target.value)}
            disabled={!!bundle} // Cannot change version when editing
          />
          <p className="text-xs text-muted-foreground mt-1">
            Semantic versioning: MAJOR.MINOR.PATCH
          </p>
        </div>
        <div>
          <Label htmlFor="notes">Notes</Label>
          <Input
            id="notes"
            placeholder="e.g., Added inbox quarantine rules"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
          />
        </div>
      </div>

      {/* Lint Status */}
      {lintResult && (
        <Alert variant={lintResult.errors.length > 0 ? 'destructive' : 'default'}>
          <div className="flex items-center gap-2">
            {lintResult.errors.length > 0 ? (
              <>
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription>
                  {lintResult.errors.length} error(s), {lintResult.warnings.length} warning(s)
                </AlertDescription>
              </>
            ) : (
              <>
                <CheckCircle2 className="h-4 w-4 text-green-600" />
                <AlertDescription>
                  All checks passed! {lintResult.warnings.length > 0 && `(${lintResult.warnings.length} warnings)`}
                </AlertDescription>
              </>
            )}
          </div>
        </Alert>
      )}

      {/* Main Editor Tabs */}
      <Tabs defaultValue="rules" className="space-y-4">
        <TabsList>
          <TabsTrigger value="rules">
            Rules ({rules.length})
          </TabsTrigger>
          <TabsTrigger value="lint">
            Lint {linting && '⋯'}
          </TabsTrigger>
          <TabsTrigger value="simulate">
            <Play className="mr-2 h-4 w-4" />
            Simulate
          </TabsTrigger>
        </TabsList>

        <TabsContent value="rules" className="space-y-4">
          <RuleBuilder
            rules={rules}
            onAddRule={handleAddRule}
            onUpdateRule={handleUpdateRule}
            onDeleteRule={handleDeleteRule}
          />
        </TabsContent>

        <TabsContent value="lint">
          <LintPanel lintResult={lintResult} onRerun={runLint} />
        </TabsContent>

        <TabsContent value="simulate">
          <SimulationPanel rules={rules} />
        </TabsContent>
      </Tabs>
    </div>
  )
}
