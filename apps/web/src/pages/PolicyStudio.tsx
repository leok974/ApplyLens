/**
 * Policy Studio - Main page for policy bundle management
 * 
 * Features:
 * - List policy bundles with version info
 * - Create new bundles
 * - Edit draft bundles
 * - View active bundle status
 * - Import/export bundles
 */

import { useState, useEffect } from 'react'
import { Plus, Upload, AlertCircle } from 'lucide-react'
import { Button } from '../components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'
import { Badge } from '../components/ui/badge'
import { Alert, AlertDescription } from '../components/ui/alert'
import { PolicyBundleList } from '../components/policy/PolicyBundleList'
import { PolicyBundleEditor } from '../components/policy/PolicyBundleEditor'
import { ImportBundleDialog } from '../components/policy/ImportBundleDialog'
import { fetchBundles, fetchActiveBundle, type PolicyBundle } from '../lib/policyClient'

export default function PolicyStudio() {
  const [bundles, setBundles] = useState<PolicyBundle[]>([])
  const [activeBundle, setActiveBundle] = useState<PolicyBundle | null>(null)
  const [selectedBundle, setSelectedBundle] = useState<PolicyBundle | null>(null)
  const [isCreating, setIsCreating] = useState(false)
  const [isImporting, setIsImporting] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadBundles()
    loadActiveBundle()
  }, [])

  const loadBundles = async () => {
    try {
      setLoading(true)
      const response = await fetchBundles({ limit: 20 })
      setBundles(response.bundles)
      setError(null)
    } catch (err: any) {
      setError(err.message || 'Failed to load policy bundles')
    } finally {
      setLoading(false)
    }
  }

  const loadActiveBundle = async () => {
    try {
      const response = await fetchActiveBundle()
      setActiveBundle(response)
    } catch (err) {
      // No active bundle is okay
      setActiveBundle(null)
    }
  }

  const handleCreateNew = () => {
    setSelectedBundle(null)
    setIsCreating(true)
  }

  const handleEdit = (bundle: PolicyBundle) => {
    if (bundle.active) {
      alert('Cannot edit active bundles. Create a new version instead.')
      return
    }
    setSelectedBundle(bundle)
    setIsCreating(true)
  }

  const handleSave = async () => {
    setIsCreating(false)
    setSelectedBundle(null)
    await loadBundles()
    await loadActiveBundle()
  }

  const handleCancel = () => {
    setIsCreating(false)
    setSelectedBundle(null)
  }

  const handleImport = () => {
    setIsImporting(true)
  }

  const handleImportComplete = async () => {
    setIsImporting(false)
    await loadBundles()
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted-foreground">Loading policy bundles...</p>
        </div>
      </div>
    )
  }

  if (isCreating) {
    return (
      <PolicyBundleEditor
        bundle={selectedBundle}
        onSave={handleSave}
        onCancel={handleCancel}
      />
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Policy Studio</h1>
          <p className="text-muted-foreground">
            Manage policy bundles that govern agentic actions
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={handleImport}>
            <Upload className="mr-2 h-4 w-4" />
            Import Bundle
          </Button>
          <Button onClick={handleCreateNew}>
            <Plus className="mr-2 h-4 w-4" />
            Create New Bundle
          </Button>
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Active Bundle Status */}
      {activeBundle && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              Active Bundle
              <Badge variant="default">
                v{activeBundle.version}
              </Badge>
              {activeBundle.canary_pct < 100 && (
                <Badge variant="secondary">
                  Canary {activeBundle.canary_pct}%
                </Badge>
              )}
            </CardTitle>
            <CardDescription>
              Currently serving {activeBundle.canary_pct}% of traffic
              {activeBundle.activated_at && (
                <> · Activated {new Date(activeBundle.activated_at).toLocaleDateString()}</>
              )}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">
                  {activeBundle.rules.length} rules configured
                </p>
                {activeBundle.notes && (
                  <p className="text-sm mt-1">{activeBundle.notes}</p>
                )}
              </div>
              <Button variant="outline" size="sm" onClick={() => handleEdit(activeBundle)}>
                View Details
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Bundle List */}
      <PolicyBundleList
        bundles={bundles}
        activeBundle={activeBundle}
        onEdit={handleEdit}
        onRefresh={loadBundles}
      />

      {/* Import Dialog */}
      <ImportBundleDialog
        open={isImporting}
        onClose={() => setIsImporting(false)}
        onImportComplete={handleImportComplete}
      />
    </div>
  )
}
