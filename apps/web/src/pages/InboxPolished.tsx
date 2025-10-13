import * as React from "react";
import { Mail, Archive, ShieldCheck, ShieldAlert, Wand2, Search as SearchIcon, Filter, MoreHorizontal, Loader2, X, ExternalLink } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuLabel } from "@/components/ui/dropdown-menu";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription, SheetFooter, SheetClose } from "@/components/ui/sheet";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { useToast } from "@/components/ui/use-toast";
import { ModeToggle } from "@/components/theme/ModeToggle";

// API helpers
import { actions, explainEmail } from "@/lib/api"; 

// Types
type EmailItem = {
  id: string;
  subject: string;
  sender?: string;
  sender_domain?: string;
  snippet?: string;
  received_at?: string;
  labels?: string[];
  reason?: string;
  thread_id?: string;
};

type FetchState =
  | { status: "idle" | "loading" }
  | { status: "error"; error: string }
  | { status: "success"; data: EmailItem[]; total: number };

const ReasonBadge: React.FC<{ reason?: string }> = ({ reason }) => {
  if (!reason) return <Badge variant="secondary">unknown</Badge>;
  const map: Record<string, { label: string; tone: "default" | "secondary" | "destructive" | "outline" }> = {
    promo: { label: "Promo", tone: "secondary" },
    newsletter: { label: "Newsletter/Ads", tone: "outline" },
    application: { label: "Application", tone: "default" },
    interview: { label: "Interview", tone: "default" },
    suspicious: { label: "Suspicious", tone: "destructive" },
  };
  const cfg = map[reason] ?? { label: reason, tone: "secondary" };
  return <Badge variant={cfg.tone}>{cfg.label}</Badge>;
};

const formatDate = (iso?: string) => {
  if (!iso) return "—";
  const d = new Date(iso);
  const t = d.getTime();
  if (Number.isNaN(t) || t === 0) return "—";
  return new Intl.DateTimeFormat(undefined, {
    year: "numeric", month: "short", day: "2-digit",
    hour: "numeric", minute: "2-digit"
  }).format(d);
};

const HeaderBar: React.FC<{
  q: string; setQ: (v: string) => void;
  onSearch: () => void;
}> = ({ q, setQ, onSearch }) => {
  return (
    <div className="flex items-center gap-3 px-4 py-3 border-b bg-white dark:bg-slate-900">
      <div className="flex items-center gap-2">
        <Mail className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
        <span className="font-semibold tracking-tight">ApplyLens</span>
      </div>
      <Separator orientation="vertical" className="mx-3 h-6" />
      <div className="relative w-full max-w-xl">
        <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search subject, sender, content…"
          className="pl-9"
          onKeyDown={(e) => { if (e.key === "Enter") onSearch(); }}
        />
      </div>
      <Button variant="secondary" size="icon" onClick={onSearch} title="Search">
        <SearchIcon className="h-4 w-4" />
      </Button>
      
      {/* Right-aligned actions */}
      <div className="ml-auto flex items-center gap-2">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon"><MoreHorizontal className="h-4 w-4" /></Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuLabel>Quick Filters</DropdownMenuLabel>
            <DropdownMenuItem>Unread</DropdownMenuItem>
            <DropdownMenuItem>Has attachments</DropdownMenuItem>
            <DropdownMenuItem>Interview invites</DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem>Expired promos</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
        <ModeToggle />
      </div>
    </div>
  );
};

const Sidebar: React.FC<{
  activeTab: string; setActiveTab: (v: string) => void;
  counters?: Record<string, number>;
}> = ({ activeTab, setActiveTab, counters }) => {
  const tabItem = (key: string, label: string, icon?: React.ReactNode) => (
    <button
      onClick={() => setActiveTab(key)}
      className={cn(
        "w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm hover:bg-accent transition",
        activeTab === key && "bg-accent"
      )}
    >
      <span className="flex items-center gap-2">
        {icon}{label}
      </span>
      {counters?.[key] != null && (
        <Badge variant="secondary">{counters[key]}</Badge>
      )}
    </button>
  );

  return (
    <div className="w-64 border-r bg-white dark:bg-slate-900 p-3 space-y-2">
      <div className="text-xs uppercase text-muted-foreground px-2 pb-1">Views</div>
      {tabItem("all", "All")}
      {tabItem("application", "Applications")}
      {tabItem("interview", "Interviews")}
      {tabItem("newsletter", "Newsletters/Ads")}
      {tabItem("promo", "Promotions")}
      {tabItem("suspicious", "Suspicious")}
      <Separator className="my-2" />
      <div className="text-xs uppercase text-muted-foreground px-2 pb-1">Actions</div>
      <button className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm hover:bg-accent">
        <Filter className="h-4 w-4" /> Advanced Filters
      </button>
    </div>
  );
};

const EmailRow: React.FC<{
  email: EmailItem;
  onOpen: (e: EmailItem) => void;
  onArchive: (id: string) => void;
  onMarkSafe: (id: string) => void;
  onMarkSuspicious: (id: string) => void;
  onUnsubDry: (id: string) => void;
  onExplain: (id: string) => void;
}> = ({ email, onOpen, onArchive, onMarkSafe, onMarkSuspicious, onUnsubDry, onExplain }) => {
  return (
    <Card className="hover:shadow-sm transition border rounded-xl">
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 flex-wrap">
              <CardTitle className="truncate text-base">{email.subject || "(no subject)"}</CardTitle>
              <ReasonBadge reason={email.reason} />
            </div>
            <div className="text-sm text-muted-foreground truncate">
              From: {email.sender || email.sender_domain || "unknown"}
            </div>
          </div>
          <div className="text-xs text-muted-foreground whitespace-nowrap">{formatDate(email.received_at)}</div>
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        <div className="text-sm text-muted-foreground line-clamp-2">{email.snippet}</div>
        <div className="flex items-center gap-2 mt-3 flex-wrap">
          <Button size="sm" onClick={() => onOpen(email)}>Open</Button>
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button variant="secondary" size="sm" onClick={() => onExplain(email.id)}>
                  <Wand2 className="h-4 w-4 mr-1" /> Explain
                </Button>
              </TooltipTrigger>
              <TooltipContent>Why this was labeled / prioritized</TooltipContent>
            </Tooltip>
          </TooltipProvider>
          <div className="flex-1" />
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button variant="ghost" size="icon" onClick={() => onArchive(email.id)} title="Archive">
                  <Archive className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Archive (remove from Inbox)</TooltipContent>
            </Tooltip>
          </TooltipProvider>
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button variant="ghost" size="icon" onClick={() => onMarkSafe(email.id)} title="Mark safe">
                  <ShieldCheck className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Mark safe / trusted sender</TooltipContent>
            </Tooltip>
          </TooltipProvider>
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button variant="ghost" size="icon" onClick={() => onMarkSuspicious(email.id)} title="Mark suspicious">
                  <ShieldAlert className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Flag as suspicious</TooltipContent>
            </Tooltip>
          </TooltipProvider>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon"><MoreHorizontal className="h-4 w-4" /></Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={() => onUnsubDry(email.id)}>Unsubscribe (dry-run)</DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => onExplain(email.id)}>Explain why</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </CardContent>
    </Card>
  );
};

const PreviewPanel: React.FC<{
  open: boolean; onOpenChange: (v: boolean) => void;
  email?: EmailItem | null;
  explain?: { reason?: string; evidence?: Record<string, any> } | null;
  loadingExplain: boolean;
}> = ({ open, onOpenChange, email, explain, loadingExplain }) => {
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-[560px] sm:w-[640px] p-0">
        <div className="flex flex-col h-full">
          <SheetHeader className="px-4 py-3 border-b">
            <div className="flex items-start gap-2 pr-8">
              <SheetTitle className="text-base">{email?.subject || "(no subject)"}</SheetTitle>
            </div>
            <SheetDescription className="flex items-center gap-2 text-xs">
              <span className="truncate">From: {email?.sender || email?.sender_domain || "unknown"}</span>
              <Separator orientation="vertical" className="h-4" />
              <span>{formatDate(email?.received_at)}</span>
            </SheetDescription>
            <SheetClose asChild>
              <Button variant="ghost" size="icon" className="absolute right-2 top-2"><X className="h-4 w-4" /></Button>
            </SheetClose>
          </SheetHeader>

          <ScrollArea className="flex-1 p-4">
            <div className="space-y-4">
              <div>
                <div className="text-xs uppercase text-muted-foreground mb-1">Reason</div>
                {loadingExplain ? (
                  <div className="flex items-center gap-2 text-muted-foreground text-sm">
                    <Loader2 className="h-4 w-4 animate-spin" /> Analyzing…
                  </div>
                ) : (
                  <div className="flex items-center gap-2">
                    <ReasonBadge reason={email?.reason || explain?.reason} />
                    <span className="text-sm text-muted-foreground">
                      {explain?.reason ? `Labelled as ${explain.reason}` : "—"}
                    </span>
                  </div>
                )}
              </div>

              {explain?.evidence && (
                <div>
                  <div className="text-xs uppercase text-muted-foreground mb-1">Evidence</div>
                  <Card className="border rounded-lg">
                    <CardContent className="text-sm text-muted-foreground pt-4">
                      <pre className="whitespace-pre-wrap break-words">
                        {JSON.stringify(explain.evidence, null, 2)}
                      </pre>
                    </CardContent>
                  </Card>
                </div>
              )}

              <div>
                <div className="text-xs uppercase text-muted-foreground mb-1">Snippet</div>
                <p className="text-sm">{email?.snippet || "—"}</p>
              </div>

              {email?.thread_id && (
                <a
                  className="inline-flex items-center gap-2 text-sm text-indigo-600 hover:underline"
                  href={`https://mail.google.com/mail/u/0/#search/rfc822msgid:${email.thread_id}`}
                  target="_blank" rel="noreferrer"
                >
                  Open in Gmail <ExternalLink className="h-3.5 w-3.5" />
                </a>
              )}
            </div>
          </ScrollArea>

          <SheetFooter className="px-4 py-3 border-t" />
        </div>
      </SheetContent>
    </Sheet>
  );
};

const EmptyState: React.FC<{ title: string; subtitle?: string; action?: React.ReactNode }> = ({ title, subtitle, action }) => (
  <div className="flex flex-col items-center justify-center text-center p-12 border rounded-2xl bg-white">
    <Mail className="w-10 h-10 text-indigo-500 mb-2" />
    <h3 className="font-semibold">{title}</h3>
    {subtitle && <p className="text-sm text-muted-foreground mt-1">{subtitle}</p>}
    {action && <div className="mt-4">{action}</div>}
  </div>
);

export default function InboxPolished() {
  const { toast } = useToast();
  const [q, setQ] = React.useState("");
  const [activeTab, setActiveTab] = React.useState<"all" | "application" | "interview" | "newsletter" | "promo" | "suspicious">("all");
  const [state, setState] = React.useState<FetchState>({ status: "loading" });
  const [selected, setSelected] = React.useState<EmailItem | null>(null);
  const [openPreview, setOpenPreview] = React.useState(false);
  const [expl, setExpl] = React.useState<{ reason?: string; evidence?: Record<string, any> } | null>(null);
  const [loadingExplain, setLoadingExplain] = React.useState(false);

  // Fetch emails
  const fetchEmails = React.useCallback(async () => {
    try {
      setState({ status: "loading" });
      const params = new URLSearchParams();
      if (q) params.set("q", q);
      if (activeTab !== "all") params.set("reason", activeTab);
      params.set("size", "50");
      const res = await fetch(`/api/search?${params.toString()}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      const data: EmailItem[] = (json?.hits ?? []).map((h: any) => ({
        id: h.id ?? h._id ?? crypto.randomUUID(),
        subject: h.subject,
        sender: h.from_addr,
        sender_domain: h.sender_domain,
        snippet: h.body_text?.slice(0, 240),
        received_at: h.received_at,
        labels: h.labels,
        reason: h.reason,
        thread_id: h.thread_id,
      }));
      setState({ status: "success", data, total: json?.total ?? data.length });
    } catch (e: any) {
      setState({ status: "error", error: e?.message ?? "Failed to fetch" });
    }
  }, [q, activeTab]);

  React.useEffect(() => { fetchEmails(); }, [fetchEmails]);

  const onOpen = async (email: EmailItem) => {
    setSelected(email);
    setExpl(null);
    setOpenPreview(true);
    setLoadingExplain(true);
    try {
      const r = await explainEmail(email.id);
      setExpl(r);
    } catch {
      setExpl(null);
    } finally {
      setLoadingExplain(false);
    }
  };

  const onArchive = async (id: string) => {
    await actions.archive(id);
    toast({ title: "Archived", description: "Email archived (dry-run)." });
  };
  const onMarkSafe = async (id: string) => {
    await actions.markSafe(id);
    toast({ title: "Marked safe", description: "Sender trusted (dry-run)." });
  };
  const onMarkSuspicious = async (id: string) => {
    await actions.markSuspicious(id);
    toast({ title: "Flagged", description: "Email marked suspicious (dry-run)." });
  };
  const onUnsubDry = async (id: string) => {
    await actions.unsubscribeDry(id);
    toast({ title: "Unsubscribe", description: "Attempted unsubscribe (dry-run)." });
  };
  const onExplain = async (id: string) => {
    setLoadingExplain(true);
    try {
      const r = await explainEmail(id);
      setExpl(r);
      setOpenPreview(true);
    } finally {
      setLoadingExplain(false);
    }
  };

  return (
    <div className="h-screen w-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100">
      <HeaderBar q={q} setQ={setQ} onSearch={fetchEmails} />
      <div className="flex h-[calc(100vh-56px)]">
        <Sidebar activeTab={activeTab} setActiveTab={(v) => setActiveTab(v as any)} />
        <main className="flex-1 p-4 overflow-auto">
          <Tabs defaultValue="inbox" className="space-y-3">
            <TabsList>
              <TabsTrigger value="inbox">Inbox</TabsTrigger>
            </TabsList>

            <TabsContent value="inbox">
              {state.status === "loading" && (
                <div className="grid gap-3">
                  {Array.from({ length: 6 }).map((_, i) => (
                    <Card key={i} className="border rounded-xl">
                      <CardHeader className="pb-2">
                        <div className="h-4 w-2/3 bg-slate-200 animate-pulse rounded" />
                        <div className="h-3 w-1/3 bg-slate-100 animate-pulse rounded mt-2" />
                      </CardHeader>
                      <CardContent className="pt-0">
                        <div className="h-10 w-full bg-slate-100 animate-pulse rounded" />
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )}
              {state.status === "error" && (
                <EmptyState title="Couldn't load emails" subtitle={state.error} action={<Button onClick={fetchEmails}>Retry</Button>} />
              )}
              {state.status === "success" && state.data.length === 0 && (
                <EmptyState
                  title="No messages"
                  subtitle="Try widening your filters or search query."
                  action={<Button variant="secondary" onClick={() => { setQ(""); setActiveTab("all"); fetchEmails(); }}>Clear filters</Button>}
                />
              )}
              {state.status === "success" && state.data.length > 0 && (
                <div className="grid gap-3">
                  {state.data.map((email) => (
                    <EmailRow
                      key={email.id}
                      email={email}
                      onOpen={onOpen}
                      onArchive={onArchive}
                      onMarkSafe={onMarkSafe}
                      onMarkSuspicious={onMarkSuspicious}
                      onUnsubDry={onUnsubDry}
                      onExplain={onExplain}
                    />
                  ))}
                </div>
              )}
            </TabsContent>
          </Tabs>

          <PreviewPanel
            open={openPreview}
            onOpenChange={setOpenPreview}
            email={selected}
            explain={expl}
            loadingExplain={loadingExplain}
          />
        </main>
      </div>
    </div>
  );
}
