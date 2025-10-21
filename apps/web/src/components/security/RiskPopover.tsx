import { useEffect, useState } from 'react';
import { Security } from '@/lib/api';

type Signal = { id: string; label: string; explain: string };

type RiskTop3 = { score: number; signals: Signal[] };

export function RiskBadge({ score, onClick }: { score?: number; onClick?: () => void }) {
  const color = score && score >= 80 
    ? 'bg-red-500' 
    : score && score >= 50 
    ? 'bg-yellow-500' 
    : 'bg-green-500';
  
  return (
    <button 
      data-testid="risk-badge" 
      onClick={onClick} 
      className={`inline-flex items-center gap-2 px-2 py-1 rounded-full text-white text-xs ${color}`}
    >
      <span className="h-2 w-2 rounded-full bg-white/80" />
      {score != null ? `Risk ${score}` : 'Risk'}
    </button>
  );
}

export default function RiskPopover({ messageId }: { messageId: string }) {
  const [open, setOpen] = useState(false);
  const [data, setData] = useState<RiskTop3 | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => { 
    if (!open) return; 
    
    (async () => {
      try { 
        setErr(null); 
        const res = await Security.top3(messageId); 
        setData(res); 
      } catch { 
        setErr('Failed to load risk'); 
      }
    })(); 
  }, [open, messageId]);

  return (
    <div className="relative" data-testid="risk-popover">
      <RiskBadge score={data?.score} onClick={() => setOpen((v) => !v)} />
      {open && (
        <div className="absolute z-10 mt-2 w-72 rounded-xl border border-white/10 bg-black/80 p-3 shadow-xl">
          <h4 className="text-xs font-semibold mb-2">Top Risk Signals</h4>
          {err && <div className="text-xs text-yellow-400">{err}</div>}
          <ul className="space-y-2">
            {(data?.signals || []).slice(0, 3).map((s) => (
              <li key={s.id} className="text-sm">
                <div className="font-medium">{s.label}</div>
                <div className="text-xs opacity-80">{s.explain}</div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
