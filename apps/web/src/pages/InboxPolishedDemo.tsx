import { ModeToggle } from "@/components/theme/ModeToggle";
import { FiltersPanel } from "@/components/inbox/FiltersPanel";
import { EmailList } from "@/components/inbox/EmailList";
import { BulkBar } from "@/components/inbox/BulkBar";
import { ShortcutsDialog } from "@/components/inbox/ShortcutsDialog";
import { EmailDetailsPanel, EmailDetails } from "@/components/inbox/EmailDetailsPanel";
import { Segmented } from "@/components/ui/segmented";
import LegibilityBar from "@/components/LegibilityBar";
import { Mail, Search as SearchIcon, Columns2, Maximize2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { useToast } from "@/components/ui/use-toast";
import * as React from "react";

type PanelMode = "overlay" | "split";
const MODE_KEY = "inbox:panelMode";
const DESKTOP_BP = 1024; // 1024px breakpoint (lg)

// Demo data
type MailItem = {
  id: string;
  subject: string;
  sender: string;
  preview: string;
  receivedAtISO: string;
  reason?: string;
  risk?: "low" | "med" | "high" | undefined;
};

const demoEmails: MailItem[] = [
  {
    id: "1",
    subject: "Your application to Software Engineer at TechCorp",
    sender: "careers@techcorp.com",
    preview: "Thank you for applying to the Software Engineer position. We've reviewed your application and would like to schedule an interview...",
    receivedAtISO: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(), // 2h ago
    reason: "ats",
  },
  {
    id: "2",
    subject: "Interview Invitation - Senior Developer Role",
    sender: "hr@startupxyz.com",
    preview: "Congratulations! We're impressed with your background and would like to invite you for a technical interview on Tuesday, 3pm EST...",
    receivedAtISO: new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString(), // 5h ago
    reason: "ats",
  },
  {
    id: "3",
    subject: "🎉 50% OFF - Summer Sale Ends Tonight!",
    sender: "deals@shopnow.com",
    preview: "Don't miss out! Our biggest sale of the year ends at midnight. Shop now and save on electronics, fashion, home goods...",
    receivedAtISO: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000).toISOString(), // 1d ago
    reason: "promo",
  },
  {
    id: "4",
    subject: "Your invoice from AWS - October 2025",
    sender: "no-reply@aws.amazon.com",
    preview: "Your AWS billing statement for October is now available. Total amount due: $127.45. Payment will be automatically...",
    receivedAtISO: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(), // 2d ago
    reason: "bill",
  },
  {
    id: "5",
    subject: "Verify your account - Urgent action required",
    sender: "security@suspicious-domain.xyz",
    preview: "Your account has been temporarily suspended. Click here immediately to verify your identity and restore access...",
    receivedAtISO: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(), // 3d ago
    reason: "suspicious",
    risk: "high" as const,
  },
  {
    id: "6",
    subject: "Weekly Tech Newsletter - Issue #42",
    sender: "newsletter@techdigest.com",
    preview: "This week: AI advances, new JavaScript frameworks, cloud computing trends, and more. Plus an exclusive interview with...",
    receivedAtISO: new Date(Date.now() - 4 * 24 * 60 * 60 * 1000).toISOString(), // 4d ago
    reason: "safe",
  },
  {
    id: "7",
    subject: "Team standup notes - Oct 11",
    sender: "workspace@slack.com",
    preview: "Here are today's standup notes from the engineering team. Sprint velocity is up 15% this week...",
    receivedAtISO: new Date().toISOString(), // today
    reason: "safe",
  },
  {
    id: "8",
    subject: "Action required: Complete your profile",
    sender: "notifications@linkedin.com",
    preview: "Your profile is 75% complete. Add your skills and experience to get more recruiter views...",
    receivedAtISO: new Date(Date.now() - 10 * 24 * 60 * 60 * 1000).toISOString(), // 10d ago
    reason: "promo",
  },
];

export default function InboxPolishedDemo() {
  const { toast } = useToast();
  const [q, setQ] = React.useState("");
  const [loading, setLoading] = React.useState(false);
  const [items, setItems] = React.useState<MailItem[]>(demoEmails);
  const [selected, setSelected] = React.useState<Set<string>>(new Set());
  const [activeId, setActiveId] = React.useState<string>("1");
  const [showHelp, setShowHelp] = React.useState(false);
  const [density, setDensity] = React.useState<"compact"|"comfortable">("comfortable");
  
  // Panel mode state
  const [panelMode, setPanelMode] = React.useState<PanelMode>(() => {
    const saved = localStorage.getItem(MODE_KEY) as PanelMode | null;
    return saved === "split" || saved === "overlay" ? saved : "overlay";
  });
  
  // Track viewport >= 1024px
  const [isDesktop, setIsDesktop] = React.useState<boolean>(
    typeof window !== "undefined" ? window.innerWidth >= DESKTOP_BP : true
  );

  React.useEffect(() => {
    const onResize = () => setIsDesktop(window.innerWidth >= DESKTOP_BP);
    // Use matchMedia to be extra precise
    const mq = window.matchMedia(`(min-width: ${DESKTOP_BP}px)`);
    const onMQ = (e: MediaQueryListEvent) => setIsDesktop(e.matches);
    window.addEventListener("resize", onResize);
    mq.addEventListener?.("change", onMQ);
    return () => {
      window.removeEventListener("resize", onResize);
      mq.removeEventListener?.("change", onMQ);
    };
  }, []);
  
  // Effective mode: force overlay on small screens, keep saved preference for desktop
  const effectiveMode: PanelMode = isDesktop ? panelMode : "overlay";

  // If we just became desktop and the saved preference is split, ensure open
  React.useEffect(() => {
    if (isDesktop && panelMode === "split") setOpenPanel(true);
  }, [isDesktop, panelMode]);
  
  // Details panel state
  const [selectedDetailId, setSelectedDetailId] = React.useState<string | null>(null);
  const [openPanel, setOpenPanel] = React.useState(false);
  const [loadingDetail, setLoadingDetail] = React.useState(false);
  const [detail, setDetail] = React.useState<EmailDetails | null>(null);
  const [thread, setThread] = React.useState<any[] | null>(null);
  const [indexInThread, setIndexInThread] = React.useState<number | null>(null);
  
  // Filter states
  const [onlyPromo, setOnlyPromo] = React.useState(false);
  const [onlyBills, setOnlyBills] = React.useState(false);
  const [onlySafe, setOnlySafe] = React.useState(false);

  function togglePanelMode() {
    setPanelMode((m) => {
      const next = m === "overlay" ? "split" : "overlay";
      localStorage.setItem(MODE_KEY, next);
      // when switching to split, ensure open; when switching to overlay, keep as-is
      if (next === "split") setOpenPanel(true);
      return next;
    });
  }

  // Open email details with thread support
  async function openDetails(id: string) {
    setSelectedDetailId(id);
    setOpenPanel(true);
    setLoadingDetail(true);
    
    // Simulate API call - in production, use getEmailById and getThread from api.ts
    await new Promise(resolve => setTimeout(resolve, 500));
    
    const email = items.find(e => e.id === id);
    if (email) {
      const mapped: EmailDetails = {
        id: email.id,
        subject: email.subject,
        from: email.sender,
        to: "you@example.com",
        date: new Date(email.receivedAtISO).toLocaleString(),
        labels: ["INBOX", email.reason?.toUpperCase() || "UNKNOWN"],
        risk: email.risk,
        reason: email.reason,
        body_html: undefined,
        body_text: email.preview + "\n\n[Full email content would appear here in production]",
        thread_id: `thread_${id}`,
        unsubscribe_url: email.reason === "promo" ? "https://example.com/unsubscribe" : null,
      };
      setDetail(mapped);

      // Simulate thread (in production: await getThread(mapped.thread_id))
      // For demo, create a simple thread with 2-3 messages
      const demoThread = [
        {
          id: `${id}_1`,
          from: "recruiter@company.com",
          date: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toLocaleString(),
          snippet: "Initial message in the thread...",
          body_html: undefined,
          body_text: "This is the first message in the thread."
        },
        {
          id: email.id,
          from: email.sender,
          date: new Date(email.receivedAtISO).toLocaleString(),
          snippet: email.preview.substring(0, 100),
          body_html: undefined,
          body_text: email.preview + "\n\n[Full email content would appear here in production]"
        }
      ];
      
      // Only set thread if there's more than one message
      if (demoThread.length > 1) {
        setThread(demoThread);
        const idx = demoThread.findIndex((m: any) => m.id === id);
        setIndexInThread(idx >= 0 ? idx : demoThread.length - 1);
      } else {
        setThread(null);
        setIndexInThread(null);
      }
    }
    setLoadingDetail(false);
  }

  function jumpThread(i: number) {
    if (!thread) return;
    setIndexInThread(i);
    const m = thread[i];
    // Rehydrate detail body with that message
    setDetail((prev) => prev ? { 
      ...prev, 
      id: m.id, 
      from: m.from, 
      date: m.date, 
      body_html: m.body_html, 
      body_text: m.body_text 
    } : prev);
    setSelectedDetailId(m.id);
  }

  function prevInThread() {
    if (indexInThread == null || !thread) return;
    if (indexInThread > 0) jumpThread(indexInThread - 1);
  }

  function nextInThread() {
    if (indexInThread == null || !thread) return;
    if (indexInThread < thread.length - 1) jumpThread(indexInThread + 1);
  }

  // Demo handlers
  const runSearch = async () => {
    setLoading(true);
    
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 800));
    
    let filtered = [...demoEmails];
    
    // Apply text search
    if (q.trim()) {
      filtered = filtered.filter(email => 
        email.subject.toLowerCase().includes(q.toLowerCase()) ||
        email.sender.toLowerCase().includes(q.toLowerCase()) ||
        email.preview.toLowerCase().includes(q.toLowerCase())
      );
    }
    
    // Apply category filters
    if (onlyPromo) filtered = filtered.filter(e => e.reason === "promo");
    if (onlyBills) filtered = filtered.filter(e => e.reason === "bill");
    if (onlySafe) filtered = filtered.filter(e => e.reason === "safe");
    
    setItems(filtered);
    setLoading(false);
    
    toast({
      title: "Search complete",
      description: `Found ${filtered.length} email${filtered.length !== 1 ? 's' : ''}`,
    });
  };
  
  const resetFilters = () => {
    setQ("");
    setOnlyPromo(false);
    setOnlyBills(false);
    setOnlySafe(false);
    setItems(demoEmails);
    setSelected(new Set());
    toast({
      title: "Filters reset",
      description: "Showing all emails",
    });
  };

  // Selection helpers
  const toggleSelect = (id: string, value?: boolean) => {
    setSelected((prev) => {
      const next = new Set(prev);
      const v = typeof value === "boolean" ? value : !next.has(id);
      if (v) next.add(id); else next.delete(id);
      return next;
    });
  };
  const clearSelection = () => setSelected(new Set());

  // Keyboard navigation
  React.useEffect(() => {
    function onKey(e: KeyboardEvent) {
      // Ignore if user is typing in an input
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      if (!items.length) return;

      const idx = activeId ? items.findIndex(i => i.id === activeId) : -1;

      // Help dialog
      if (e.key === "?") { 
        setShowHelp((v) => !v); 
        e.preventDefault(); 
        return; 
      }

      // j/k navigation
      if (e.key === "j") {
        const nextIdx = Math.min(items.length - 1, idx + 1);
        setActiveId(items[nextIdx]?.id ?? items[0].id);
        e.preventDefault();
      }
      if (e.key === "k") {
        const prevIdx = Math.max(0, idx <= 0 ? 0 : idx - 1);
        setActiveId(items[prevIdx]?.id ?? items[0].id);
        e.preventDefault();
      }

      if (idx >= 0) {
        const id = items[idx].id;

        // Select with x
        if (e.key === "x") {
          toggleSelect(id);
          e.preventDefault();
        }
        // Archive with e
        if (e.key === "e") {
          handleArchive(id);
          e.preventDefault();
        }
        // Explain with Enter
        if (e.key === "Enter") {
          handleExplain(id);
          e.preventDefault();
        }
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [items, activeId, selected]);

  // Bulk actions
  const bulkArchive = () => {
    const count = selected.size;
    toast({
      title: "Archived",
      description: `${count} email${count !== 1 ? 's' : ''} archived`,
    });
    clearSelection();
  };
  
  const bulkSafe = () => {
    const count = selected.size;
    toast({
      title: "Marked as safe",
      description: `${count} email${count !== 1 ? 's' : ''} marked as safe`,
    });
    clearSelection();
  };
  
  const bulkSus = () => {
    const count = selected.size;
    toast({
      title: "Marked as suspicious",
      description: `${count} email${count !== 1 ? 's' : ''} flagged`,
      variant: "destructive",
    });
    clearSelection();
  };

  const handleArchive = (id: string) => {
    const email = items.find(e => e.id === id);
    toast({
      title: "Archived",
      description: `"${email?.subject}" has been archived`,
    });
  };

  const handleSafe = (id: string) => {
    const email = items.find(e => e.id === id);
    toast({
      title: "Marked as safe",
      description: `Sender "${email?.sender}" has been trusted`,
    });
  };

  const handleSuspicious = (id: string) => {
    const email = items.find(e => e.id === id);
    toast({
      title: "Marked as suspicious",
      description: `"${email?.subject}" has been flagged`,
      variant: "destructive",
    });
  };

  const handleExplain = (id: string) => {
    const email = items.find(e => e.id === id);
    toast({
      title: "AI Explanation",
      description: `Analyzing why "${email?.subject}" was categorized as ${email?.reason || 'unknown'}...`,
    });
  };

  return (
    <main className="min-h-screen bg-[color:hsl(var(--color-background))]">
      {/* Header */}
      <header className="sticky top-0 z-40 flex items-center gap-3 border-b border-[color:hsl(var(--color-border))] bg-[color:hsl(var(--color-background))]/80 backdrop-blur supports-[backdrop-filter]:bg-[color:hsl(var(--color-background))]/60 px-4 py-3">
        <div className="flex items-center gap-2">
          <Mail className="h-5 w-5 text-[color:hsl(var(--color-accent))]" />
          <span className="font-semibold tracking-tight">ApplyLens</span>
        </div>
        <Separator orientation="vertical" className="mx-3 h-6" />
        <div className="relative w-full max-w-xl">
          <SearchIcon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <Input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search subject, sender, content…"
            className="pl-9"
            onKeyDown={(e) => e.key === "Enter" && runSearch()}
          />
        </div>
        <Button variant="outline" size="icon" onClick={runSearch} title="Search" className="border-[color:hsl(var(--color-border))] text-slate-600 dark:text-slate-300">
          <SearchIcon className="h-4 w-4" />
        </Button>
        <div className="ml-auto flex items-center gap-2">
          <Button 
            variant={!isDesktop ? "secondary" : "outline"} 
            size="sm" 
            onClick={togglePanelMode}
            disabled={!isDesktop}
            className="hidden md:inline-flex"
            title={!isDesktop ? "Available on larger screens" : ""}
          >
            {effectiveMode === "split" ? (
              <>
                <Maximize2 className="mr-2 h-4 w-4" /> Overlay Panel
              </>
            ) : (
              <>
                <Columns2 className="mr-2 h-4 w-4" /> Split Panel
              </>
            )}
          </Button>
          <Segmented
            value={density}
            onChange={setDensity}
            options={[
              { value: "comfortable", label: "Comfort" },
              { value: "compact", label: "Compact" },
            ]}
          />
          <ModeToggle />
        </div>
      </header>

      {/* Legibility Controls */}
      <LegibilityBar />

      {/* Bulk bar */}
      <BulkBar
        count={selected.size}
        onClear={clearSelection}
        onArchive={bulkArchive}
        onSafe={bulkSafe}
        onSus={bulkSus}
      />

      {/* Body */}
      <div className="mx-auto grid max-w-7xl grid-cols-1 md:grid-cols-[18rem,1fr]">
        <FiltersPanel
          q={q}
          setQ={setQ}
          onlyPromo={onlyPromo}
          setOnlyPromo={setOnlyPromo}
          onlyBills={onlyBills}
          setOnlyBills={setOnlyBills}
          onlySafe={onlySafe}
          setOnlySafe={setOnlySafe}
          onApply={runSearch}
          onReset={resetFilters}
        />
        
        {/* Content area: list + optional split panel */}
        {effectiveMode === "split" ? (
          // GRID: list on left, details docked right
          <div
            className="grid min-h-[calc(100vh-64px)]"
            style={{ gridTemplateColumns: "1fr auto" }}
          >
            <div className="overflow-hidden">
              <EmailList
                items={items}
                loading={loading}
                selected={selected}
                onToggleSelect={toggleSelect}
                activeId={activeId}
                onSetActive={setActiveId}
                density={density}
                onOpen={(id) => openDetails(id)}
                onArchive={handleArchive}
                onSafe={handleSafe}
                onSus={handleSuspicious}
                onExplain={handleExplain}
              />
            </div>

            {/* Split mode panel (always mounted) */}
            <EmailDetailsPanel
              mode="split"
              open={true}
              onClose={() => setOpenPanel(false)}
              loading={loadingDetail}
              email={detail}
              thread={thread || undefined}
              indexInThread={indexInThread ?? null}
              onPrev={thread && indexInThread != null && indexInThread > 0 ? prevInThread : undefined}
              onNext={thread && indexInThread != null && indexInThread < thread.length - 1 ? nextInThread : undefined}
              onJump={(i) => jumpThread(i)}
              onArchive={() => {
                if (!selectedDetailId) return;
                handleArchive(selectedDetailId);
                setOpenPanel(false);
              }}
              onMarkSafe={() => {
                if (!selectedDetailId) return;
                handleSafe(selectedDetailId);
                setOpenPanel(false);
              }}
              onMarkSus={() => {
                if (!selectedDetailId) return;
                handleSuspicious(selectedDetailId);
                setOpenPanel(false);
              }}
              onExplain={() => {
                if (!selectedDetailId) return;
                handleExplain(selectedDetailId);
              }}
            />
          </div>
        ) : (
          // Overlay mode: list full-width, slide-over when open
          <div className="relative min-h-[calc(100vh-64px)]">
            <EmailList
              items={items}
              loading={loading}
              selected={selected}
              onToggleSelect={toggleSelect}
              activeId={activeId}
              onSetActive={setActiveId}
              density={density}
              onOpen={(id) => openDetails(id)}
              onArchive={handleArchive}
              onSafe={handleSafe}
              onSus={handleSuspicious}
              onExplain={handleExplain}
            />
            <EmailDetailsPanel
              mode="overlay"
              open={openPanel}
              onClose={() => setOpenPanel(false)}
              loading={loadingDetail}
              email={detail}
              thread={thread || undefined}
              indexInThread={indexInThread ?? null}
              onPrev={thread && indexInThread != null && indexInThread > 0 ? prevInThread : undefined}
              onNext={thread && indexInThread != null && indexInThread < thread.length - 1 ? nextInThread : undefined}
              onJump={(i) => jumpThread(i)}
              onArchive={() => {
                if (!selectedDetailId) return;
                handleArchive(selectedDetailId);
                setOpenPanel(false);
              }}
              onMarkSafe={() => {
                if (!selectedDetailId) return;
                handleSafe(selectedDetailId);
                setOpenPanel(false);
              }}
              onMarkSus={() => {
                if (!selectedDetailId) return;
                handleSuspicious(selectedDetailId);
                setOpenPanel(false);
              }}
              onExplain={() => {
                if (!selectedDetailId) return;
                handleExplain(selectedDetailId);
              }}
            />
          </div>
        )}
      </div>

      <ShortcutsDialog open={showHelp} onOpenChange={setShowHelp} />
    </main>
  );
}
