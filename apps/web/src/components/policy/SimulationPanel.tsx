/**
 * Simulation Panel - Run what-if simulations on policy rules
 */

import { useState } from 'react'
import { Play, AlertCircle, TrendingUp, TrendingDown, Download } from 'lucide-react'
import { Button } from '../ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card'
import { Alert, AlertDescription } from '../ui/alert'
import { Badge } from '../ui/badge'
import { Label } from '../ui/label'
import { RadioGroup, RadioGroupItem } from '../ui/radio-group'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs'
import { simulateRules, type PolicyRule, type SimResponse } from '../../lib/policyClient'
import { useToast } from '../ui/use-toast'

interface SimulationPanelProps {
  rules: PolicyRule[]
}

export function SimulationPanel({ rules }: SimulationPanelProps) {
  const [dataset, setDataset] = useState<'fixtures' | 'synthetic'>('fixtures')
  const [syntheticCount, setSyntheticCount] = useState<number>(100)
  const [running, setRunning] = useState(false)
  const [result, setResult] = useState<SimResponse | null>(null)
  const { toast } = useToast()

  const handleRunSimulation = async () => {
    if (rules.length === 0) {
      toast({
        title: 'No rules to simulate',
        description: 'Add at least one rule before running a simulation.',
        variant: 'destructive',
      })
      return
    }

    setRunning(true)
    try {
      const response = await simulateRules({
        rules,
        dataset,
        synthetic_count: dataset === 'synthetic' ? syntheticCount : undefined,
      })
      setResult(response)
      toast({
        title: 'Simulation complete',
        description: `Processed ${response.summary.total_cases} cases`,
      })
    } catch (error) {
      console.error('Simulation error:', error)
      toast({
        title: 'Simulation failed',
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: 'destructive',
      })
    } finally {
      setRunning(false)
    }
  }

  const handleExportResults = () => {
    if (!result) return

    const blob = new Blob([JSON.stringify(result, null, 2)], {
      type: 'application/json',
    })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `simulation-${Date.now()}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  const handleDatasetChange = (value: string) => {
    if (value === 'fixtures') {
      setDataset('fixtures')
    } else if (value === 'synthetic-100') {
      setDataset('synthetic')
      setSyntheticCount(100)
    } else if (value === 'synthetic-1000') {
      setDataset('synthetic')
      setSyntheticCount(1000)
    }
  }

  return (
    <div className="space-y-4">
      {/* Configuration */}
      <Card>
        <CardHeader>
          <CardTitle>Simulation Configuration</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Label>Dataset</Label>
            <RadioGroup value={dataset} onValueChange={handleDatasetChange} className="mt-2">
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="fixtures" id="fixtures" />
                <Label htmlFor="fixtures" className="font-normal">
                  Test Fixtures (~50 cases)
                </Label>
              </div>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="synthetic-100" id="synthetic-100" />
                <Label htmlFor="synthetic-100" className="font-normal">
                  Synthetic - Small (100 cases)
                </Label>
              </div>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="synthetic-1000" id="synthetic-1000" />
                <Label htmlFor="synthetic-1000" className="font-normal">
                  Synthetic - Large (1,000 cases)
                </Label>
              </div>
            </RadioGroup>
          </div>

          <div className="flex gap-2">
            <Button onClick={handleRunSimulation} disabled={running || rules.length === 0}>
              <Play className="mr-2 h-4 w-4" />
              {running ? 'Running...' : 'Run Simulation'}
            </Button>
            {result && (
              <Button variant="outline" onClick={handleExportResults}>
                <Download className="mr-2 h-4 w-4" />
                Export Results
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Results */}
      {result && (
        <Tabs defaultValue="summary">
          <TabsList>
            <TabsTrigger value="summary">Summary</TabsTrigger>
            <TabsTrigger value="examples">Examples</TabsTrigger>
          </TabsList>

          <TabsContent value="summary" className="space-y-4">
            {/* Breach Warnings */}
            {result.summary.breaches.length > 0 && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  <div className="font-semibold mb-2">Budget Breaches Detected</div>
                  <ul className="list-disc list-inside space-y-1">
                    {result.summary.breaches.map((breach, index) => (
                      <li key={index}>{breach}</li>
                    ))}
                  </ul>
                </AlertDescription>
              </Alert>
            )}

            {/* Effect Distribution */}
            <Card>
              <CardHeader>
                <CardTitle>Effect Distribution</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-3 gap-4">
                  <div className="text-center">
                    <div className="text-3xl font-bold text-green-600">
                      {result.summary.allow_count}
                    </div>
                    <div className="text-sm text-muted-foreground">Allowed</div>
                    <div className="text-xs text-muted-foreground">
                      {(result.summary.allow_rate * 100).toFixed(1)}%
                    </div>
                  </div>
                  <div className="text-center">
                    <div className="text-3xl font-bold text-red-600">
                      {result.summary.deny_count}
                    </div>
                    <div className="text-sm text-muted-foreground">Denied</div>
                    <div className="text-xs text-muted-foreground">
                      {(result.summary.deny_rate * 100).toFixed(1)}%
                    </div>
                  </div>
                  <div className="text-center">
                    <div className="text-3xl font-bold text-yellow-600">
                      {result.summary.approval_count}
                    </div>
                    <div className="text-sm text-muted-foreground">Needs Approval</div>
                    <div className="text-xs text-muted-foreground">
                      {(result.summary.approval_rate * 100).toFixed(1)}%
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Budget Summary */}
            <Card>
              <CardHeader>
                <CardTitle>Budget Impact</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <div className="flex items-center gap-2">
                      <TrendingUp className="h-4 w-4 text-muted-foreground" />
                      <span className="text-sm text-muted-foreground">Estimated Cost</span>
                    </div>
                    <div className="text-2xl font-bold mt-1">
                      ${result.summary.estimated_cost.toFixed(2)}
                    </div>
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <TrendingDown className="h-4 w-4 text-muted-foreground" />
                      <span className="text-sm text-muted-foreground">Estimated Compute</span>
                    </div>
                    <div className="text-2xl font-bold mt-1">
                      {result.summary.estimated_compute.toFixed(2)} units
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Overall Stats */}
            <Card>
              <CardHeader>
                <CardTitle>Overall Statistics</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Total Cases</span>
                    <span className="font-medium">{result.summary.total_cases}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Cases Matched</span>
                    <span className="font-medium">
                      {result.summary.total_cases - result.summary.no_match_count}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Cases Unmatched</span>
                    <span className="font-medium">{result.summary.no_match_count}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Match Rate</span>
                    <span className="font-medium">
                      {(((result.summary.total_cases - result.summary.no_match_count) / result.summary.total_cases) * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="examples">
            <Card>
              <CardHeader>
                <CardTitle>Example Cases</CardTitle>
              </CardHeader>
              <CardContent>
                {result.examples.length > 0 ? (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Case ID</TableHead>
                        <TableHead>Matched Rule</TableHead>
                        <TableHead>Effect</TableHead>
                        <TableHead>Reason</TableHead>
                        <TableHead>Budget</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {result.examples.map((example, index) => (
                        <TableRow key={index}>
                          <TableCell className="font-mono text-xs">
                            {example.case_id}
                          </TableCell>
                          <TableCell className="font-mono text-xs">
                            {example.matched_rule || 'N/A'}
                          </TableCell>
                          <TableCell>
                            <Badge
                              variant={
                                example.effect === 'allow'
                                  ? 'default'
                                  : example.effect === 'deny'
                                  ? 'destructive'
                                  : 'secondary'
                              }
                            >
                              {example.effect || 'no_match'}
                            </Badge>
                          </TableCell>
                          <TableCell className="max-w-xs truncate">
                            {example.reason || 'No rule matched'}
                          </TableCell>
                          <TableCell>
                            {example.budget ? (
                              <div className="text-xs">
                                <div>${example.budget.cost.toFixed(2)}</div>
                                <div className="text-muted-foreground">
                                  {example.budget.compute.toFixed(1)} compute
                                </div>
                              </div>
                            ) : (
                              '-'
                            )}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                ) : (
                  <div className="text-center text-muted-foreground py-8">
                    No example cases available
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      )}

      {/* Empty State */}
      {!result && !running && (
        <Card>
          <CardContent className="pt-6">
            <div className="text-center text-muted-foreground py-8">
              <p>Configure and run a simulation to see results</p>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
