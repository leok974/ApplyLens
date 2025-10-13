import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert"
import { Info } from "lucide-react"

export function DryRunNotice() {
  return (
    <Alert className="border bg-card">
      <Info className="h-4 w-4" />
      <AlertTitle>Dry-run mode</AlertTitle>
      <AlertDescription>
        Quick actions (Archive, Mark Safe/Suspicious, Unsubscribe) are logged but don't modify Gmail yet.
      </AlertDescription>
    </Alert>
  )
}
