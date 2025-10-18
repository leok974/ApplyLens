/**
 * Import Bundle Dialog - Upload and verify signed policy bundles
 */

import { useState } from 'react'
import { Upload, AlertCircle, CheckCircle2, Clock } from 'lucide-react'
import { Button } from '../ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog'
import { Alert, AlertDescription } from '../ui/alert'
import { Label } from '../ui/label'
import { Input } from '../ui/input'
import { Badge } from '../ui/badge'
import { importBundle } from '../../lib/policyClient'
import { useToast } from '../ui/use-toast'

interface ImportBundleDialogProps {
  open: boolean
  onClose: () => void
  onImportComplete: () => void
}

interface ParsedBundle {
  version: string
  rules_count: number
  exported_at: string
  expires_at: string
  source_signature: string
}

export function ImportBundleDialog({ open, onClose, onImportComplete }: ImportBundleDialogProps) {
  const [file, setFile] = useState<File | null>(null)
  const [parsed, setParsed] = useState<ParsedBundle | null>(null)
  const [importAsVersion, setImportAsVersion] = useState('')
  const [importing, setImporting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const { toast } = useToast()

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0]
    if (!selectedFile) return

    setFile(selectedFile)
    setError(null)

    // Parse the JSON file
    const reader = new FileReader()
    reader.onload = (event) => {
      try {
        const content = event.target?.result as string
        const data = JSON.parse(content)

        // Validate required fields
        if (!data.version || !data.rules || !data.exported_at || !data.expires_at || !data.source_signature) {
          setError('Invalid bundle format: missing required fields')
          setParsed(null)
          return
        }

        // Check expiry
        const expiresAt = new Date(data.expires_at)
        const now = new Date()
        if (expiresAt < now) {
          setError(`Bundle expired on ${expiresAt.toLocaleString()}`)
          setParsed(null)
          return
        }

        // Set parsed data
        setParsed({
          version: data.version,
          rules_count: Array.isArray(data.rules) ? data.rules.length : 0,
          exported_at: data.exported_at,
          expires_at: data.expires_at,
          source_signature: data.source_signature,
        })
      } catch (err) {
        setError('Failed to parse JSON file')
        setParsed(null)
      }
    }
    reader.readAsText(selectedFile)
  }

  const handleImport = async () => {
    if (!file || !parsed) return

    setImporting(true)
    setError(null)

    try {
      // Read file content
      const reader = new FileReader()
      reader.onload = async (event) => {
        try {
          const content = event.target?.result as string
          const signedBundle = JSON.parse(content)

          // Call import API
          await importBundle(signedBundle, importAsVersion || undefined)

          toast({
            title: 'Bundle imported successfully',
            description: `Imported as version ${importAsVersion || parsed.version}`,
          })
          onImportComplete()
          handleClose()
        } catch (err) {
          console.error('Import error:', err)
          setError(err instanceof Error ? err.message : 'Import failed')
        } finally {
          setImporting(false)
        }
      }
      reader.readAsText(file)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Import failed')
      setImporting(false)
    }
  }

  const handleClose = () => {
    setFile(null)
    setParsed(null)
    setImportAsVersion('')
    setError(null)
    onClose()
  }

  const isExpiringSoon = parsed ? new Date(parsed.expires_at).getTime() - Date.now() < 24 * 60 * 60 * 1000 : false

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Import Policy Bundle</DialogTitle>
          <DialogDescription>
            Upload a signed policy bundle JSON file to import
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* File Upload */}
          <div>
            <Label htmlFor="file-upload">Bundle File</Label>
            <Input
              id="file-upload"
              type="file"
              accept=".json"
              onChange={handleFileChange}
              className="mt-1"
            />
            {file && (
              <div className="mt-2 text-sm text-muted-foreground flex items-center gap-2">
                <Upload className="h-4 w-4" />
                {file.name}
              </div>
            )}
          </div>

          {/* Error Alert */}
          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {/* Parsed Bundle Info */}
          {parsed && (
            <div className="space-y-4">
              <Alert>
                <CheckCircle2 className="h-4 w-4" />
                <AlertDescription>Bundle parsed successfully</AlertDescription>
              </Alert>

              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Version</span>
                  <span className="font-mono font-medium">{parsed.version}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Rules</span>
                  <span className="font-medium">{parsed.rules_count}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Exported</span>
                  <span className="text-xs">{new Date(parsed.exported_at).toLocaleString()}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-muted-foreground">Expires</span>
                  <div className="flex items-center gap-2">
                    <span className="text-xs">{new Date(parsed.expires_at).toLocaleString()}</span>
                    {isExpiringSoon && (
                      <Badge variant="destructive" className="text-xs">
                        <Clock className="h-3 w-3 mr-1" />
                        Soon
                      </Badge>
                    )}
                  </div>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Signature</span>
                  <Badge variant="outline" className="font-mono text-xs">
                    {parsed.source_signature.substring(0, 12)}...
                  </Badge>
                </div>
              </div>

              {/* Expiry Warning */}
              {isExpiringSoon && (
                <Alert>
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>
                    This bundle expires within 24 hours. Consider re-exporting with longer expiry.
                  </AlertDescription>
                </Alert>
              )}

              {/* Import As Different Version */}
              <div>
                <Label htmlFor="import-version">
                  Import As Version (optional)
                </Label>
                <Input
                  id="import-version"
                  value={importAsVersion}
                  onChange={(e) => setImportAsVersion(e.target.value)}
                  placeholder={`Default: ${parsed.version}`}
                  className="mt-1"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Leave empty to use original version ({parsed.version})
                </p>
              </div>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={importing}>
            Cancel
          </Button>
          <Button onClick={handleImport} disabled={!parsed || importing}>
            {importing ? 'Importing...' : 'Import Bundle'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
