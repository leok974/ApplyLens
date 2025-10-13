import * as React from "react"

const LS = "inbox:legibility"

type State = {
  scale: 0.9 | 1 | 1.1
  density: 0.92 | 1 | 1.08
  contrast: "soft" | "high"
}

const DEFAULTS: State = { scale: 1, density: 1, contrast: "soft" }

export default function LegibilityBar() {
  const [s, setS] = React.useState<State>(() => {
    const raw = localStorage.getItem(LS)
    return raw ? { ...DEFAULTS, ...JSON.parse(raw) } : DEFAULTS
  })

  React.useEffect(() => {
    const root = document.documentElement
    root.style.setProperty("--font-scale", String(s.scale))
    root.style.setProperty("--density", String(s.density))
    // contrast: cards slightly higher border/shadow in "high"
    root.style.setProperty("--border", s.contrast === "high" ? "220 15% 80%" : "220 15% 86%")
    root.style.setProperty("--ring",   s.contrast === "high" ? "220 13% 66%" : "220 13% 72%")
    localStorage.setItem(LS, JSON.stringify(s))
  }, [s])

  return (
    <div className="container-readable mb-4 mt-2 flex flex-wrap items-center gap-2 text-sm">
      <span className="opacity-70">View:</span>

      <div className="inline-flex rounded-md border bg-background">
        {([0.9, 1, 1.1] as const).map(v => (
          <button
            key={v}
            onClick={() => setS(prev => ({ ...prev, scale: v }))}
            className={`px-2 py-1 ${s.scale === v ? "bg-muted" : ""}`}
            title={`Font ${v === 1 ? "M" : v === 1.1 ? "L" : "S"}`}
          >
            {v === 1 ? "M" : v === 1.1 ? "L" : "S"}
          </button>
        ))}
      </div>

      <div className="inline-flex rounded-md border bg-background">
        {([0.92, 1, 1.08] as const).map(v => (
          <button
            key={v}
            onClick={() => setS(prev => ({ ...prev, density: v }))}
            className={`px-2 py-1 ${s.density === v ? "bg-muted" : ""}`}
            title={`Density ${v === 1 ? "Cozy" : v > 1 ? "Spacious" : "Compact"}`}
          >
            {v === 1 ? "Cozy" : v > 1 ? "Spacious" : "Compact"}
          </button>
        ))}
      </div>

      <div className="inline-flex rounded-md border bg-background">
        {(["soft", "high"] as const).map(v => (
          <button
            key={v}
            onClick={() => setS(prev => ({ ...prev, contrast: v }))}
            className={`px-2 py-1 capitalize ${s.contrast === v ? "bg-muted" : ""}`}
          >
            {v}
          </button>
        ))}
      </div>
    </div>
  )
}
