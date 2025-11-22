export default function ExtensionSupport() {
  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <h1 className="text-3xl font-extrabold">ApplyLens Companion — Support</h1>

      <section className="mt-6 space-y-2 text-gray-700 dark:text-gray-300">
        <h2 className="text-xl font-semibold">Quick checks</h2>
        <ul className="list-disc pl-5 space-y-1">
          <li>Make sure the API is reachable: open <code>/api/ops/diag/health</code> in your browser — it should return OK.</li>
          <li>Reload the extension in <code>chrome://extensions</code> after updating.</li>
          <li>Grant permissions on Greenhouse/Lever/Workday or LinkedIn when prompted.</li>
        </ul>
      </section>

      <section className="mt-6 space-y-2 text-gray-700 dark:text-gray-300">
        <h2 className="text-xl font-semibold">Common issues</h2>
        <details className="rounded-lg border border-gray-200 dark:border-gray-800 p-4">
          <summary className="font-semibold cursor-pointer">Popup says "offline"</summary>
          <p className="mt-2 text-sm">
            The extension couldn't reach your API. Check your network and that your ApplyLens backend is running.
          </p>
        </details>
        <details className="rounded-lg border border-gray-200 dark:border-gray-800 p-4 mt-2">
          <summary className="font-semibold cursor-pointer">Form doesn't autofill</summary>
          <p className="mt-2 text-sm">
            Some ATS pages change field names/selectors. Click "Scan form &amp; suggest" again or refresh the page.
          </p>
        </details>
        <details className="rounded-lg border border-gray-200 dark:border-gray-800 p-4 mt-2">
          <summary className="font-semibold cursor-pointer">LinkedIn DM not copying</summary>
          <p className="mt-2 text-sm">
            Your browser may block clipboard on insecure contexts. Ensure HTTPS and try again.
          </p>
        </details>
      </section>

      <section className="mt-6 space-y-2 text-gray-700 dark:text-gray-300">
        <h2 className="text-xl font-semibold">Contact</h2>
        <p>
          Email: <a className="underline" href="mailto:leoklemet.pa@gmail.com">leoklemet.pa@gmail.com</a>
        </p>
        <p className="text-sm opacity-80">
          Please include screenshots (DevTools Console/Network) and steps to reproduce.
        </p>
      </section>

      <section className="mt-8 text-sm text-gray-500">
        <a className="underline" href="/extension/privacy">Privacy Policy</a>
      </section>
    </main>
  );
}
