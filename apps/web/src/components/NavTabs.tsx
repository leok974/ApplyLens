import { Link, useLocation } from "react-router-dom";

export function NavTabs() {
  const { pathname } = useLocation();
  
  const active = (p: string) =>
    pathname.startsWith(p)
      ? "text-white border-b-2 border-white"
      : "text-muted-foreground border-b-2 border-transparent hover:text-white hover:border-border/50";

  return (
    <div className="flex items-center gap-6 text-sm font-medium">
      <Link
        to="/inbox-actions"
        className={`pb-1.5 transition ${active("/inbox-actions")}`}
      >
        Inbox
      </Link>
      <Link
        to="/tracker"
        className={`pb-1.5 transition ${active("/tracker")}`}
      >
        Tracker
      </Link>
    </div>
  );
}
