import { useEffect, useState } from 'react';
import { AI } from '@/lib/api';

export type SummaryData = { 
  bullets: string[]; 
  citations?: { snippet: string; message_id?: string; offset?: number }[] 
};

export default function SummaryCard({ threadId }: { threadId: string }) {
  const [data, setData] = useState<SummaryData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function run() {
    try { 
      setLoading(true); 
      setError(null);
      const res = await AI.summarize(threadId, 3);
      setData(res);
    } catch (e: any) { 
      setError('Unable to summarize'); 
    } finally { 
      setLoading(false); 
    }
  }

  useEffect(() => { /* mounted idle */ }, []);

  return (
    <div data-testid="summary-card" className="rounded-2xl p-4 border border-white/10 bg-white/5">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-semibold">AI Summary</h3>
        <button 
          onClick={run} 
          className="text-xs px-2 py-1 rounded bg-white/10 hover:bg-white/20"
          disabled={loading}
        >
          {loading ? 'Summarizing…' : 'Summarize'}
        </button>
      </div>
      {loading && <div className="text-xs opacity-80">Generating summary...</div>}
      {error && <div className="text-xs text-yellow-400">{error}</div>}
      {data && (
        <ul className="list-disc pl-5 space-y-1">
          {(data.bullets || []).slice(0, 5).map((b, i) => (
            <li key={i} className="text-sm">{b}</li>
          ))}
        </ul>
      )}
      {data?.citations?.length ? (
        <div className="mt-3 flex flex-wrap gap-2" data-testid="summary-citations">
          {data.citations.slice(0, 3).map((c, i) => (
            <span 
              key={i} 
              className="text-[11px] px-2 py-1 rounded bg-white/10" 
              title={c.snippet}
            >
              {c.message_id || 'cite'} @{c.offset ?? 0}
            </span>
          ))}
        </div>
      ) : null}
    </div>
  );
}
