// apps/web/src/pages/InboxPageRefactored.tsx
// Polished inbox with shadcn/ui components, clean spacing, and better hierarchy

import { useState, useEffect } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import {
  Inbox as InboxIcon,
  RefreshCw,
  Filter,
  Briefcase,
  Mail,
  ExternalLink,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
} from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { CheckCircle, AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils";

import {
  getGmailStatus,
  getGmailInbox,
  initiateGmailAuth,
  backfillGmail,
  createApplicationFromEmail,
  Email,
  GmailConnectionStatus,
} from "../lib/api";
import { formatDistanceToNowStrict } from "date-fns";

// Map API Email type to display-friendly EmailSummary
type EmailCategory = "all" | "interview" | "offer" | "rejection" | "receipt" | "newsletter";

interface EmailSummary {
  id: string;
  subject: string;
  fromName: string;
  fromEmail: string;
  snippet: string;
  sentAt: string; // ISO string
  category: EmailCategory;
  labels: string[];
  hasApplication: boolean;
  rawEmail: Email; // Keep reference to original data
}

const CATEGORY_FILTERS = [
  { value: "all" as EmailCategory, label: "All" },
  { value: "interview" as EmailCategory, label: "Interview" },
  { value: "offer" as EmailCategory, label: "Offer" },
  { value: "rejection" as EmailCategory, label: "Rejection" },
  { value: "receipt" as EmailCategory, label: "Application Receipt" },
  { value: "newsletter" as EmailCategory, label: "Newsletter / Ads" },
];

// Map API label to category
function mapLabelToCategory(label?: string): EmailCategory {
  if (!label) return "all";
  if (label === "interview") return "interview";
  if (label === "offer") return "offer";
  if (label === "rejection") return "rejection";
  if (label === "application_receipt") return "receipt";
  if (label === "newsletter_ads") return "newsletter";
  return "all";
}

// Map Email to EmailSummary
function mapEmail(e: Email): EmailSummary {
  return {
    id: String(e.id),
    subject: e.subject || "(no subject)",
    fromName: e.sender || e.from_addr.split("@")[0],
    fromEmail: e.from_addr,
    snippet: e.body_preview || e.body_text?.slice(0, 150) || "",
    sentAt: e.received_at,
    category: mapLabelToCategory(e.label),
    labels: e.labels || [],
    hasApplication: !!e.application_id,
    rawEmail: e,
  };
}

function labelForCategory(category: EmailCategory): string {
  const found = CATEGORY_FILTERS.find((c) => c.value === category);
  return found?.label || "All";
}

export default function InboxPageRefactored() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  const [status, setStatus] = useState<GmailConnectionStatus | null>(null);
  const [emails, setEmails] = useState<EmailSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [selectedCategory, setSelectedCategory] = useState<EmailCategory>("all");
  const [selectedEmail, setSelectedEmail] = useState<EmailSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  // Deep-link support: /inbox?open=<emailId>
  useEffect(() => {
    const openId = searchParams.get("open");
    if (!openId) return;

    const targetEmail = emails.find((e) => e.id === openId);
    if (targetEmail) {
      setSelectedEmail(targetEmail);
      // Clean up URL
      searchParams.delete("open");
      setSearchParams(searchParams, { replace: true });
    } else {
      console.warn(`Deep-link target email ${openId} not found in current inbox view`);
    }
  }, [searchParams, emails]);

  // Check connection status on mount
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("connected") === "google") {
      setErr("✅ Successfully connected to Gmail! Click Sync to fetch your messages.");
      setTimeout(() => setErr(null), 5000);
    }

    getGmailStatus()
      .then(setStatus)
      .catch((e) => console.error("Status check failed:", e));
  }, []);

  // Fetch emails when filter or page changes
  useEffect(() => {
    if (!status?.connected) return;

    setLoading(true);
    const labelFilter = selectedCategory === "all" ? undefined : selectedCategory;
    const apiLabel =
      labelFilter === "receipt"
        ? "application_receipt"
        : labelFilter === "newsletter"
        ? "newsletter_ads"
        : labelFilter;

    getGmailInbox(page, 50, apiLabel, status.user_email)
      .then((resp) => {
        setEmails(resp.emails.map(mapEmail));
        setTotal(resp.total);
      })
      .catch((e) => setErr(String(e)))
      .finally(() => setLoading(false));
  }, [status, page, selectedCategory]);

  const handleSync = async (window: "7d" | "60d") => {
    if (!status?.user_email) return;
    setSyncing(true);
    try {
      const days = window === "7d" ? 7 : 60;
      await backfillGmail(days, status.user_email);
      setErr(`✅ Synced last ${days} days of emails`);
      setTimeout(() => setErr(null), 3000);
      // Refresh inbox
      setPage(1);
    } catch (error) {
      setErr(`Failed to sync: ${error}`);
    } finally {
      setSyncing(false);
    }
  };

  const handleOpenApplication = async (email: EmailSummary) => {
    if (email.hasApplication && email.rawEmail.application_id) {
      navigate(`/tracker?selected=${email.rawEmail.application_id}`);
    } else {
      // Create new application from email
      try {
        const result = await createApplicationFromEmail(Number(email.id));
        navigate(`/tracker?selected=${result.application_id}`);
      } catch (error) {
        console.error("Failed to create application:", error);
        setErr("Failed to create application. Email may lack company/role information.");
      }
    }
  };

  const filtered = emails;
  const visibleCount = emails.length;

  // Not connected UI
  if (!status) {
    return <div className="p-4">Loading Gmail status...</div>;
  }

  if (!status.connected) {
    return (
      <div className="mx-auto max-w-2xl p-8 text-center">
        <h1 className="mb-4 text-3xl font-bold">📬 Gmail Inbox</h1>
        <p className="mb-6 text-muted-foreground">
          Connect your Gmail account to start tracking job application emails with intelligent
          labeling.
        </p>
        <button
          onClick={initiateGmailAuth}
          className="rounded-lg bg-primary px-6 py-3 font-semibold text-primary-foreground transition hover:bg-primary/90"
        >
          🔐 Connect Gmail
        </button>
        <Card className="mt-8">
          <CardHeader>
            <CardTitle className="text-base">What happens when you connect:</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="ml-6 list-disc space-y-1 text-left text-sm">
              <li>Secure OAuth 2.0 authentication (read-only access)</li>
              <li>Automatic email labeling (interviews, offers, rejections)</li>
              <li>Full-text search with autocomplete</li>
              <li>Synonym matching for job search terms</li>
              <li>Your credentials are encrypted and never exposed</li>
            </ul>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="flex h-full">
      {/* LEFT: Inbox list */}
      <div className="flex min-w-0 flex-1 flex-col px-6 pb-6 pt-4">
        {/* Page header */}
        <div className="mb-4 flex items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-primary/10">
                <InboxIcon className="h-4 w-4 text-primary" />
              </span>
              <div>
                <div className="flex items-center gap-2">
                  <h1 className="text-base font-semibold leading-tight">Gmail Inbox</h1>
                  <Badge variant="outline" className="text-xs font-normal">
                    <span className="font-mono">{status.user_email}</span>
                  </Badge>
                </div>
                <p className="text-xs text-muted-foreground">
                  Showing {visibleCount} of {total.toLocaleString()} emails
                </p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="outline"
              className="gap-1"
              onClick={() => handleSync("7d")}
              disabled={syncing}
            >
              <RefreshCw className={cn("h-3 w-3", syncing && "animate-spin")} />
              Sync 7d
            </Button>
            <Button
              size="sm"
              variant="outline"
              className="gap-1"
              onClick={() => handleSync("60d")}
              disabled={syncing}
            >
              <RefreshCw className={cn("h-3 w-3", syncing && "animate-spin")} />
              Sync 60d
            </Button>
            <Button
              size="icon"
              variant="ghost"
              className="rounded-full"
              aria-label="Filter inbox"
            >
              <Filter className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* Alert for errors/success */}
        {err && (
          <Alert
            variant={err.startsWith("✅") ? "default" : "destructive"}
            className="mb-4"
          >
            {err.startsWith("✅") ? (
              <CheckCircle className="h-4 w-4" />
            ) : (
              <AlertCircle className="h-4 w-4" />
            )}
            <AlertDescription>{err}</AlertDescription>
          </Alert>
        )}

        {/* Category filters */}
        <Tabs
          value={selectedCategory}
          onValueChange={(v) => {
            setSelectedCategory(v as EmailCategory);
            setPage(1);
          }}
          className="mb-3 w-full"
        >
          <TabsList className="w-full justify-start gap-1 overflow-x-auto rounded-full bg-muted/40 p-1">
            {CATEGORY_FILTERS.map((filter) => (
              <TabsTrigger
                key={filter.value}
                value={filter.value}
                className="px-3 text-xs"
              >
                {filter.label}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>

        <Separator className="mb-3" />

        {/* Email list */}
        <ScrollArea className="flex-1">
          {loading ? (
            <div className="py-8 text-center text-sm text-muted-foreground">
              Loading emails...
            </div>
          ) : (
            <div className="space-y-2 pb-4">
              {filtered.map((email) => (
                <EmailListItem
                  key={email.id}
                  email={email}
                  isSelected={selectedEmail?.id === email.id}
                  onSelect={(e) => setSelectedEmail(e)}
                  onOpenApplication={handleOpenApplication}
                />
              ))}

              {filtered.length === 0 && (
                <Card className="border-dashed border-muted-foreground/30 bg-background/40">
                  <CardContent className="py-8 text-center text-sm text-muted-foreground">
                    {selectedCategory === "all"
                      ? 'No emails yet. Click "Sync" to fetch from Gmail.'
                      : `No emails found in ${labelForCategory(selectedCategory)} category.`}
                  </CardContent>
                </Card>
              )}
            </div>
          )}
        </ScrollArea>

        {/* Pagination */}
        {total > 50 && !loading && (
          <div className="mt-4 flex items-center justify-center gap-2">
            <Button
              size="sm"
              variant="outline"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
            >
              <ChevronLeft className="h-4 w-4" />
              Previous
            </Button>
            <span className="px-4 text-sm text-muted-foreground">
              Page {page} of {Math.ceil(total / 50)}
            </span>
            <Button
              size="sm"
              variant="outline"
              onClick={() => setPage((p) => p + 1)}
              disabled={page >= Math.ceil(total / 50)}
            >
              Next
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        )}
      </div>

      {/* RIGHT: Detail panel */}
      <EmailDetailPanel email={selectedEmail} onOpenApplication={handleOpenApplication} />
    </div>
  );
}

// ============================================================================
// Email List Item Component
// ============================================================================

interface EmailListItemProps {
  email: EmailSummary;
  isSelected: boolean;
  onSelect: (email: EmailSummary) => void;
  onOpenApplication: (email: EmailSummary) => void;
}

function EmailListItem({
  email,
  isSelected,
  onSelect,
  onOpenApplication,
}: EmailListItemProps) {
  return (
    <Card
      onClick={() => onSelect(email)}
      className={cn(
        "group cursor-pointer border-border/60 bg-background/40 transition-colors hover:bg-background/80",
        isSelected && "border-primary/70 bg-primary/5"
      )}
    >
      <CardHeader className="flex flex-row items-start justify-between gap-3 space-y-0 p-4">
        <div className="min-w-0 flex-1 space-y-1">
          <CardTitle className="line-clamp-2 text-sm font-semibold leading-snug">
            {email.subject}
          </CardTitle>
          <p className="truncate text-xs text-muted-foreground">
            From <span className="font-medium">{email.fromName}</span>{" "}
            <span className="font-mono text-[11px]">&lt;{email.fromEmail}&gt;</span>
          </p>
        </div>
        <div className="flex shrink-0 flex-col items-end gap-1">
          <span className="text-[11px] text-muted-foreground">
            {formatDistanceToNowStrict(new Date(email.sentAt), { addSuffix: true })}
          </span>
          <div className="flex flex-wrap justify-end gap-1">
            <Badge
              variant="outline"
              className={cn(
                "border-border/60 text-[11px]",
                email.category === "interview" && "border-emerald-500/70 text-emerald-600 dark:text-emerald-300",
                email.category === "offer" && "border-sky-500/70 text-sky-600 dark:text-sky-300",
                email.category === "rejection" && "border-rose-500/70 text-rose-600 dark:text-rose-300",
                email.category === "receipt" && "border-amber-500/70 text-amber-600 dark:text-amber-300",
                email.category === "newsletter" && "border-purple-500/70 text-purple-600 dark:text-purple-300"
              )}
            >
              {labelForCategory(email.category)}
            </Badge>
          </div>
        </div>
      </CardHeader>

      <CardContent className="flex flex-col gap-3 p-4 pt-0">
        <p className="line-clamp-2 text-xs text-muted-foreground">{email.snippet}</p>

        <div className="flex items-center justify-between gap-2">
          <div className="flex flex-wrap gap-1">
            {email.labels.slice(0, 3).map((label) => (
              <Badge
                key={label}
                variant="secondary"
                className="rounded-full px-2 py-0 text-[11px]"
              >
                {label}
              </Badge>
            ))}
            {email.labels.length > 3 && (
              <Badge variant="outline" className="rounded-full px-2 py-0 text-[11px]">
                +{email.labels.length - 3} more
              </Badge>
            )}
          </div>

          {email.hasApplication && (
            <Button
              size="sm"
              variant="outline"
              className="h-7 gap-1"
              onClick={(e) => {
                e.stopPropagation();
                onOpenApplication(email);
              }}
            >
              <Briefcase className="h-3 w-3" />
              View application
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

// ============================================================================
// Email Detail Panel Component
// ============================================================================

interface EmailDetailPanelProps {
  email: EmailSummary | null;
  onOpenApplication: (email: EmailSummary) => void;
}

function EmailDetailPanel({ email, onOpenApplication }: EmailDetailPanelProps) {
  const openInGmail = () => {
    if (!email?.rawEmail.thread_id) return;
    const url = `https://mail.google.com/mail/u/0/#inbox/${email.rawEmail.thread_id}`;
    window.open(url, "_blank");
  };

  return (
    <aside className="hidden h-full w-[380px] flex-col border-l border-border/60 bg-background/60 md:flex">
      <header className="flex items-center justify-between border-b border-border/60 px-4 py-3">
        <div className="flex items-center gap-2">
          <span className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-muted/60">
            <Mail className="h-4 w-4 text-muted-foreground" />
          </span>
          <div>
            <p className="text-xs font-medium leading-tight">Email detail</p>
            <p className="text-[11px] text-muted-foreground">
              {email ? "Preview content & labels" : "Select an email on the left"}
            </p>
          </div>
        </div>
      </header>

      <div className="flex-1 overflow-auto p-4 text-sm">
        {!email ? (
          <p className="mt-4 text-xs text-muted-foreground">
            When you select an email in the inbox, its content and metadata will appear here.
          </p>
        ) : (
          <div className="space-y-3">
            <div>
              <div className="mb-1 text-[11px] uppercase tracking-wide text-muted-foreground">
                Subject
              </div>
              <div className="text-sm font-semibold leading-snug">
                {email.subject || "(no subject)"}
              </div>
            </div>

            <div>
              <div className="mb-1 text-[11px] uppercase tracking-wide text-muted-foreground">
                From
              </div>
              <p className="text-xs">
                <span className="font-medium">{email.fromName}</span>{" "}
                <span className="font-mono text-[11px]">
                  &lt;{email.fromEmail}&gt;
                </span>
              </p>
            </div>

            <Separator className="my-2" />

            <div>
              <div className="mb-1 text-[11px] uppercase tracking-wide text-muted-foreground">
                Snippet
              </div>
              <p className="text-xs text-muted-foreground whitespace-pre-wrap">
                {email.snippet}
              </p>
            </div>

            <Separator className="my-2" />

            <div className="flex flex-wrap gap-1">
              {email.labels.map((label) => (
                <Badge
                  key={label}
                  variant="secondary"
                  className="rounded-full px-2 py-0 text-[11px]"
                >
                  {label}
                </Badge>
              ))}
            </div>
          </div>
        )}
      </div>

      {email && (
        <footer className="border-t border-border/60 px-4 py-3">
          <Button
            size="sm"
            variant="outline"
            className="w-full gap-1"
            onClick={openInGmail}
          >
            <ExternalLink className="h-3 w-3" />
            Open in Gmail
          </Button>
        </footer>
      )}
    </aside>
  );
}
