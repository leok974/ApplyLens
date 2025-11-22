import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Shield, ClipboardCheck, Send, Rocket } from "lucide-react";

const MAIN_APP_PATH = "/"; // Main app route (Job Inbox)

function InstallButton() {
  // When you publish, replace with the real Chrome Web Store URL
  const STORE_URL = "https://chrome.google.com/webstore/detail/applylens-companion/<YOUR_ID>";
  return (
    <a
      href={STORE_URL}
      target="_blank"
      rel="noreferrer"
      className="inline-flex items-center gap-2 rounded-2xl px-5 py-3 shadow hover:shadow-md transition
                 bg-black text-white dark:bg-white dark:text-black"
    >
      Install from Chrome Web Store <ArrowRight size={18} />
    </a>
  );
}

function Badge({ ok }: { ok: boolean }) {
  return (
    <span className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-sm ${ok ? "bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-200" : "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-200"}`}>
      <span className={`inline-block h-2 w-2 rounded-full ${ok ? "bg-green-500" : "bg-red-500"}`} />
      {ok ? "API: Online" : "API: Offline"}
    </span>
  );
}

export default function ExtensionLanding() {
  const [apiOk, setApiOk] = useState<boolean | null>(null);

  useEffect(() => {
    // lightweight health check (your proxy already exists)
    fetch("/api/ops/diag/health")
      .then((r) => setApiOk(r.ok))
      .catch(() => setApiOk(false));
  }, []);

  return (
    <main className="min-h-[calc(100vh-80px)]">
      {/* Hero */}
      <section className="mx-auto max-w-6xl px-6 pt-14 pb-10">
        <div className="grid md:grid-cols-2 gap-10 items-center">
          <div>
            <div className="mb-4">{apiOk !== null && <Badge ok={!!apiOk} />}</div>
            <h1 className="text-3xl sm:text-4xl md:text-5xl font-extrabold tracking-tight">
              ApplyLens Companion
            </h1>
            <p className="mt-4 text-lg text-gray-600 dark:text-gray-300">
              Autofill common ATS forms and draft tailored recruiter DMs using your ApplyLens profile —
              fast, privacy-first, and fully in your control.
            </p>
            <div className="mt-6 flex flex-wrap items-center gap-3">
              <InstallButton />

              <Link
                to={MAIN_APP_PATH}
                className="inline-flex items-center gap-2 rounded-2xl px-5 py-3 shadow hover:shadow-md transition
                           border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                data-testid="companion-back-to-app"
              >
                Back to ApplyLens
              </Link>
              <a
                href="/extension/support"
                className="text-sm underline opacity-80 hover:opacity-100"
              >
                Need help?
              </a>
            </div>
            <ul className="mt-6 text-sm text-gray-600 dark:text-gray-300 space-y-2">
              <li>• Greenhouse, Lever, Workday & more</li>
              <li>• Optional logging of applications & outreach</li>
              <li>• No background browsing history, no ad tracking</li>
            </ul>
          </div>

          <div className="rounded-2xl border border-gray-200 dark:border-gray-800 p-4 shadow-sm">
            {/* Replace with your real screenshot */}
            <img
              src="/extension/assets/screen1.png"
              alt="ApplyLens Companion demo"
              className="rounded-xl"
              onError={(e) => ((e.target as HTMLImageElement).style.opacity = "0.3")}
            />
            <div className="mt-2 text-xs text-gray-500">Demo screenshot</div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="mx-auto max-w-6xl px-6 py-10">
        <div className="grid md:grid-cols-3 gap-6">
          <Feature
            icon={<ClipboardCheck />}
            title="One-click autofill"
            desc="Scan the page and propose clean, relevant answers for fields like 'About you', 'Why us', or portfolio links."
          />
          <Feature
            icon={<Send />}
            title="Recruiter DMs"
            desc="Draft short, personalized Intros for LinkedIn recruiters based on your profile and target role."
          />
          <Feature
            icon={<Shield />}
            title="Privacy-first"
            desc="No background history reads, no ad tracking. You decide what gets logged into ApplyLens."
          />
        </div>
      </section>

      {/* How it works */}
      <section className="mx-auto max-w-6xl px-6 py-12">
        <h2 className="text-2xl font-bold">How it works</h2>
        <ol className="mt-4 space-y-3 text-gray-700 dark:text-gray-300">
          <li>1. Install the extension and open a job application page.</li>
          <li>2. Click the extension → "Scan form &amp; suggest".</li>
          <li>3. (Optional) Click "Draft recruiter DM" on LinkedIn profiles.</li>
          <li>4. (Optional) Log application/outreach to your ApplyLens tracker.</li>
        </ol>
        <div className="mt-6">
          <a href="/extension/privacy" className="inline-flex items-center gap-2 text-sm underline opacity-80 hover:opacity-100">
            <Shield size={16} /> Privacy Policy
          </a>
        </div>
      </section>

      {/* CTA */}
      <section className="mx-auto max-w-6xl px-6 pb-16">
        <div className="rounded-2xl border border-gray-200 dark:border-gray-800 p-8 text-center">
          <h3 className="text-xl md:text-2xl font-semibold">Ready to move faster?</h3>
          <p className="mt-2 text-gray-600 dark:text-gray-300">Install the Companion and cut busywork from applications.</p>
          <div className="mt-5 inline-flex">
            <InstallButton />
          </div>
          <div className="mt-3 text-xs text-gray-500 flex items-center justify-center gap-1">
            <Rocket size={14} /> Works best with your ApplyLens profile filled in.
          </div>
        </div>
      </section>
    </main>
  );
}

function Feature({ icon, title, desc }: { icon: React.ReactNode; title: string; desc: string }) {
  return (
    <div className="rounded-2xl border border-gray-200 dark:border-gray-800 p-5">
      <div className="h-10 w-10 mb-3 rounded-xl border border-gray-200 dark:border-gray-800 flex items-center justify-center">
        {icon}
      </div>
      <h3 className="font-semibold">{title}</h3>
      <p className="mt-1 text-sm text-gray-600 dark:text-gray-300">{desc}</p>
    </div>
  );
}
