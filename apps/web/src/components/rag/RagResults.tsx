import { useState } from 'react';
import { RAG } from '@/lib/api';

type Hit = { 
  thread_id: string; 
  message_id?: string; 
  score?: number; 
  highlights?: string[]; 
  why?: string; 
  sender?: string; 
  date?: string 
};

type RagRes = { hits: Hit[] };

export default function RagResults() {
  const [q, setQ] = useState('');
  const [res, setRes] = useState<RagRes>({ hits: [] });
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function run() {
    try { 
      setLoading(true); 
      setErr(null); 
      const r = await RAG.query(q, 5); 
      setRes(r); 
    } catch { 
      setErr('Search failed'); 
    } finally { 
      setLoading(false); 
    }
  }

  return (
    <div className="space-y-3" data-testid="rag-results">
      <div className="flex gap-2">
        <input 
          value={q} 
          onChange={(e) => setQ(e.target.value)} 
          placeholder="Ask your inbox…" 
          className="flex-1 px-3 py-2 rounded-lg bg-white/5 border border-white/10"
          onKeyDown={(e) => e.key === 'Enter' && run()}
        />
        <button 
          onClick={run} 
          className="px-3 py-2 rounded-lg bg-white/10 hover:bg-white/20"
          disabled={loading}
        >
          {loading ? 'Searching…' : 'Ask'}
        </button>
      </div>
      {loading && <div className="text-xs opacity-80">Searching your inbox...</div>}
      {err && <div className="text-xs text-yellow-400">{err}</div>}
      <div className="grid gap-2">
        {res.hits.slice(0, 5).map((h) => (
          <div 
            key={`${h.thread_id}-${h.message_id || ''}`} 
            className="rounded-xl p-3 border border-white/10 bg-white/5"
          >
            <div className="text-sm font-medium">
              {h.sender || 'Thread'} — <span className="opacity-80">{h.date}</span>
            </div>
            <div className="text-xs mt-1 opacity-80">
              why: {h.why || 'bm25'}
            </div>
            <div className="mt-2 space-y-1">
              {(h.highlights || []).slice(0, 2).map((s, i) => (
                <div key={i} className="text-sm">{s}</div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
