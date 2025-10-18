/**
 * Policy Bundle List - Display policy bundles in table format
 */

import { Pencil, Download, Trash2 } from 'lucide-react'
import { Button } from '../ui/button'
import { Badge } from '../ui/badge'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../ui/table'
import { exportBundle, deleteBundle, type PolicyBundle } from '../../lib/policyClient'
import { useState } from 'react'
import { useToast } from '../ui/use-toast'

interface PolicyBundleListProps {
  bundles: PolicyBundle[]
  activeBundle: PolicyBundle | null
  onEdit: (bundle: PolicyBundle) => void
  onRefresh: () => void
}

export function PolicyBundleList({
  bundles,
  onEdit,
  onRefresh,
}: PolicyBundleListProps) {
  const { toast } = useToast()
  const [deletingId, setDeletingId] = useState<number | null>(null)

  const handleExport = async (bundleId: number, version: string) => {
    try {
      const response = await exportBundle(bundleId)
      
      // Create download
      const blob = new Blob([JSON.stringify(response, null, 2)], {
        type: 'application/json',
      })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `policy-bundle-${version}.json`
      a.click()
      URL.revokeObjectURL(url)

      toast({
        title: 'Bundle exported',
        description: `Successfully exported v${version}`,
      })
    } catch (err: any) {
      toast({
        title: 'Export failed',
        description: err.message || 'Failed to export bundle',
        variant: 'destructive',
      })
    }
  }

  const handleDelete = async (bundleId: number, version: string, isActive: boolean) => {
    if (isActive) {
      toast({
        title: 'Cannot delete',
        description: 'Cannot delete active bundles',
        variant: 'destructive',
      })
      return
    }

    if (!confirm(`Delete bundle v${version}? This action cannot be undone.`)) {
      return
    }

    try {
      setDeletingId(bundleId)
      await deleteBundle(bundleId)
      
      toast({
        title: 'Bundle deleted',
        description: `Successfully deleted v${version}`,
      })
      
      onRefresh()
    } catch (err: any) {
      toast({
        title: 'Delete failed',
        description: err.message || 'Failed to delete bundle',
        variant: 'destructive',
      })
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <div className="border rounded-lg">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Version</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Rules</TableHead>
            <TableHead>Notes</TableHead>
            <TableHead>Created</TableHead>
            <TableHead className="text-right">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {bundles.length === 0 ? (
            <TableRow>
              <TableCell colSpan={6} className="text-center text-muted-foreground py-8">
                No policy bundles found. Create your first bundle to get started.
              </TableCell>
            </TableRow>
          ) : (
            bundles.map((bundle) => (
              <TableRow key={bundle.id}>
                <TableCell className="font-mono font-semibold">
                  {bundle.version}
                </TableCell>
                <TableCell>
                  <div className="flex gap-1">
                    {bundle.active ? (
                      <>
                        <Badge variant="default">Active</Badge>
                        {bundle.canary_pct < 100 && (
                          <Badge variant="secondary">{bundle.canary_pct}%</Badge>
                        )}
                      </>
                    ) : (
                      <Badge variant="outline">Draft</Badge>
                    )}
                  </div>
                </TableCell>
                <TableCell>
                  <span className="text-sm">{bundle.rules.length}</span>
                </TableCell>
                <TableCell>
                  <span className="text-sm text-muted-foreground">
                    {bundle.notes || '—'}
                  </span>
                </TableCell>
                <TableCell>
                  <div className="text-sm">
                    <div>{new Date(bundle.created_at).toLocaleDateString()}</div>
                    <div className="text-muted-foreground text-xs">
                      by {bundle.created_by}
                    </div>
                  </div>
                </TableCell>
                <TableCell className="text-right">
                  <div className="flex justify-end gap-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => onEdit(bundle)}
                    >
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleExport(bundle.id, bundle.version)}
                    >
                      <Download className="h-4 w-4" />
                    </Button>
                    {!bundle.active && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDelete(bundle.id, bundle.version, bundle.active)}
                        disabled={deletingId === bundle.id}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    )}
                  </div>
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
    </div>
  )
}
