import { FLAGS } from '@/lib/flags';
import SummaryCard from '@/components/ai/SummaryCard';
import RiskPopover from '@/components/security/RiskPopover';
import RagResults from '@/components/rag/RagResults';

export default function DemoAI() {
  return (
    <div className="max-w-4xl mx-auto p-4 space-y-6">
      <h2 className="text-xl font-semibold">Phase 4 AI Features Demo</h2>
      
      {FLAGS.SUMMARIZE && (
        <div className="space-y-2">
          <h3 className="text-lg font-medium">1. Email Thread Summarization</h3>
          <p className="text-sm opacity-80">
            AI-powered 5-bullet summaries with citations
          </p>
          <SummaryCard threadId="demo-thread-id" />
        </div>
      )}

      {FLAGS.RISK_BADGE && (
        <div className="space-y-2">
          <h3 className="text-lg font-medium">2. Smart Risk Badge</h3>
          <p className="text-sm opacity-80">
            Click to see top 3 risk signals
          </p>
          <div className="flex items-center gap-3">
            <div className="text-sm">Email Risk Score:</div>
            <RiskPopover messageId="demo-message-id" />
          </div>
        </div>
      )}

      {FLAGS.RAG_SEARCH && (
        <div className="space-y-2">
          <h3 className="text-lg font-medium">3. RAG Search</h3>
          <p className="text-sm opacity-80">
            Semantic search across your inbox
          </p>
          <RagResults />
        </div>
      )}

      {FLAGS.DEMO_MODE && (
        <div className="text-xs opacity-75 text-center py-2 border-t border-white/10">
          🧪 Demo mode enabled — data may be seeded or mocked
        </div>
      )}

      {!FLAGS.SUMMARIZE && !FLAGS.RISK_BADGE && !FLAGS.RAG_SEARCH && (
        <div className="border border-yellow-500/20 bg-yellow-500/5 rounded-lg p-6 text-center">
          <p className="text-sm opacity-70">
            No AI features are currently enabled. Update your <code>.env</code> file:
          </p>
          <pre className="mt-4 text-xs opacity-60 text-left max-w-md mx-auto">
            VITE_FEATURE_SUMMARIZE=1{'\n'}
            VITE_FEATURE_RISK_BADGE=1{'\n'}
            VITE_FEATURE_RAG_SEARCH=1
          </pre>
        </div>
      )}
    </div>
  );
}
