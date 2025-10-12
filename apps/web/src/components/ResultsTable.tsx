import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"

interface EmailResult {
  id: string
  from: string
  subject: string
  received: string
  reason: string
  labels?: string[]
}

interface ResultsTableProps {
  results: EmailResult[]
  onViewDetails?: (id: string) => void
}

export function ResultsTable({ results, onViewDetails }: ResultsTableProps) {
  return (
    <div className="rounded-xl border bg-card shadow-card overflow-hidden">
      <Table>
        <TableHeader className="bg-background/40">
          <TableRow>
            <TableHead className="w-[200px]">From</TableHead>
            <TableHead>Subject</TableHead>
            <TableHead className="w-[140px]">Received</TableHead>
            <TableHead className="w-[180px]">Reason</TableHead>
            <TableHead className="text-right w-[120px]">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {results.length === 0 ? (
            <TableRow>
              <TableCell colSpan={5} className="h-24 text-center text-muted-foreground">
                No results found.
              </TableCell>
            </TableRow>
          ) : (
            results.map((result) => (
              <TableRow key={result.id} className="hover:bg-secondary/50 transition-colors">
                <TableCell className="font-medium">{result.from}</TableCell>
                <TableCell>
                  <div className="flex flex-col gap-1">
                    <span className="line-clamp-1">{result.subject}</span>
                    {result.labels && result.labels.length > 0 && (
                      <div className="flex gap-1 flex-wrap">
                        {result.labels.map((label) => (
                          <Badge key={label} variant="secondary" className="text-xs">
                            {label}
                          </Badge>
                        ))}
                      </div>
                    )}
                  </div>
                </TableCell>
                <TableCell className="text-muted-foreground text-sm">{result.received}</TableCell>
                <TableCell className="text-sm">{result.reason}</TableCell>
                <TableCell className="text-right">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => onViewDetails?.(result.id)}
                  >
                    View
                  </Button>
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
    </div>
  )
}

// Example usage component
export function ResultsTableExample() {
  const sampleData: EmailResult[] = [
    {
      id: "1",
      from: "recruiting@example.com",
      subject: "Interview Invitation - Software Engineer Position",
      received: "2 hours ago",
      reason: "Interview invitation",
      labels: ["Interview", "Important"],
    },
    {
      id: "2",
      from: "noreply@greenhouse.io",
      subject: "Application Status Update",
      received: "1 day ago",
      reason: "Application update",
      labels: ["Tracker"],
    },
  ]

  return <ResultsTable results={sampleData} onViewDetails={(id) => console.log("View:", id)} />
}
