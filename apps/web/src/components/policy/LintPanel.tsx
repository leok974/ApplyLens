/**
 * Lint Panel - Display lint results with annotations
 */

import { AlertCircle, AlertTriangle, Info, RefreshCw } from 'lucide-react'
import { Button } from '../ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card'
import { Alert, AlertDescription } from '../ui/alert'
import { Badge } from '../ui/badge'
import type { LintResult } from '../../lib/policyClient'

interface LintPanelProps {
  lintResult: LintResult | null
  onRerun: () => void
}

export function LintPanel({ lintResult, onRerun }: LintPanelProps) {
  if (!lintResult) {
    return (
      <Card>
        <CardContent className="pt-6">
          <div className="text-center text-muted-foreground py-8">
            <p>Add rules to see lint results</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  const { errors, warnings, info: infoList, summary } = lintResult

  return (
    <div className="space-y-4">
      {/* Summary */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Lint Summary</CardTitle>
            <Button variant="outline" size="sm" onClick={onRerun}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Rerun
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-4 gap-4 text-center">
            <div>
              <div className="text-2xl font-bold">{summary.total_rules}</div>
              <div className="text-sm text-muted-foreground">Total Rules</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-destructive">{summary.error_count}</div>
              <div className="text-sm text-muted-foreground">Errors</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-yellow-600">{summary.warning_count}</div>
              <div className="text-sm text-muted-foreground">Warnings</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-blue-600">{summary.info_count}</div>
              <div className="text-sm text-muted-foreground">Info</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Errors */}
      {errors.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-lg font-semibold flex items-center gap-2">
            <AlertCircle className="h-5 w-5 text-destructive" />
            Errors ({errors.length})
          </h3>
          {errors.map((annotation, index) => (
            <Alert key={index} variant="destructive">
              <AlertDescription>
                <div className="space-y-1">
                  <div className="flex items-start justify-between">
                    <div className="font-medium">{annotation.message}</div>
                    {annotation.rule_id && (
                      <Badge variant="outline" className="ml-2">
                        {annotation.rule_id}
                      </Badge>
                    )}
                  </div>
                  {annotation.suggestion && (
                    <div className="text-sm text-muted-foreground">
                      💡 {annotation.suggestion}
                    </div>
                  )}
                  {annotation.line && (
                    <div className="text-xs text-muted-foreground">
                      Line {annotation.line}
                    </div>
                  )}
                </div>
              </AlertDescription>
            </Alert>
          ))}
        </div>
      )}

      {/* Warnings */}
      {warnings.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-lg font-semibold flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-yellow-600" />
            Warnings ({warnings.length})
          </h3>
          {warnings.map((annotation, index) => (
            <Alert key={index}>
              <AlertDescription>
                <div className="space-y-1">
                  <div className="flex items-start justify-between">
                    <div className="font-medium">{annotation.message}</div>
                    {annotation.rule_id && (
                      <Badge variant="outline" className="ml-2">
                        {annotation.rule_id}
                      </Badge>
                    )}
                  </div>
                  {annotation.suggestion && (
                    <div className="text-sm text-muted-foreground">
                      💡 {annotation.suggestion}
                    </div>
                  )}
                </div>
              </AlertDescription>
            </Alert>
          ))}
        </div>
      )}

      {/* Info */}
      {infoList.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-lg font-semibold flex items-center gap-2">
            <Info className="h-5 w-5 text-blue-600" />
            Info ({infoList.length})
          </h3>
          {infoList.map((annotation, index) => (
            <Alert key={index}>
              <AlertDescription>
                <div className="flex items-start justify-between">
                  <div>{annotation.message}</div>
                  {annotation.rule_id && (
                    <Badge variant="outline" className="ml-2">
                      {annotation.rule_id}
                    </Badge>
                  )}
                </div>
              </AlertDescription>
            </Alert>
          ))}
        </div>
      )}

      {/* All Clear */}
      {errors.length === 0 && warnings.length === 0 && infoList.length === 0 && (
        <Alert>
          <AlertDescription className="flex items-center gap-2">
            <div className="text-green-600">✓</div>
            <div>All checks passed! No issues found.</div>
          </AlertDescription>
        </Alert>
      )}
    </div>
  )
}
