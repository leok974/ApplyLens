import { useState } from "react";
import { Link } from "react-router-dom";
import { Settings, ShieldCheck } from "lucide-react";
import { useRuntimeConfig } from "../hooks/useRuntimeConfig";

export function HeaderSettingsDropdown() {
  const [open, setOpen] = useState(false);
  const { config } = useRuntimeConfig();
  const readOnly = config.readOnly ?? false;

  return (
    <div className="relative">
      <button
        className="flex items-center gap-2 text-xs text-muted-foreground hover:text-white px-2 py-1 rounded-md hover:bg-card/50 border border-border/50 transition"
        onClick={() => setOpen((o) => !o)}
      >
        <Settings className="w-4 h-4" />
        <span>Settings</span>
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-64 rounded-lg border border-border/50 bg-card/90 backdrop-blur-xl shadow-xl p-2 z-50 text-sm">
          {/* Sender Controls link */}
          <Link
            to="/settings/senders"
            className="flex items-start gap-2 rounded-md px-2 py-2 hover:bg-background/50"
            onClick={() => setOpen(false)}
            data-testid="nav-senders-settings"
          >
            <ShieldCheck className="w-4 h-4 text-green-400 flex-shrink-0" />
            <div className="flex flex-col leading-tight">
              <span className="text-white font-medium text-[13px]">
                Sender Controls
              </span>
              <span className="text-[11px] text-muted-foreground">
                Trusted / muted senders
              </span>
            </div>
          </Link>

          {/* Runtime status */}
          <div className="border-t border-border/40 mt-2 pt-2 px-2 text-[11px] leading-snug text-muted-foreground">
            {readOnly ? (
              <span className="text-yellow-400">
                Restricted mode: bulk actions limited
              </span>
            ) : (
              <span className="text-muted-foreground/80">
                Live mode: actions enabled
              </span>
            )}
            {config.version && (
              <div className="text-[10px] text-muted-foreground/60">
                v{config.version}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
