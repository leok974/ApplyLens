import * as React from "react";

function initials(from: string) {
  const name = from?.split("@")[0] ?? from ?? "";
  const parts = name.replace(/[^\p{L}\p{N}]+/gu, " ").trim().split(" ");
  const letters = (parts[0]?.[0] ?? "") + (parts[1]?.[0] ?? "");
  return letters.toUpperCase() || "✉";
}

function domainOf(emailOrText: string) {
  const m = /@([^>\s]+)|https?:\/\/([^/]+)/.exec(emailOrText || "");
  return (m?.[1] || m?.[2] || "").replace(/[>\s]/g, "");
}

export function SenderAvatar({ from, size = 32 }: { from: string; size?: number }) {
  const domain = domainOf(from);
  const src = domain ? `https://www.google.com/s2/favicons?sz=64&domain=${domain}` : undefined;
  const [err, setErr] = React.useState(false);

  if (src && !err) {
    return (
      <img
        src={src}
        width={size}
        height={size}
        className="rounded-full border border-[color:hsl(var(--color-border))] bg-card"
        onError={() => setErr(true)}
        alt=""
      />
    );
  }
  return (
    <div
      style={{ width: size, height: size }}
      className="grid place-items-center rounded-full border border-[color:hsl(var(--color-border))] bg-[color:hsl(var(--color-accent))] text-[color:hsl(var(--color-accent-foreground))] shadow-sm"
    >
      <span className="text-xs font-semibold">{initials(from)}</span>
    </div>
  );
}
