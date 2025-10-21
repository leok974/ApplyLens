import { useEffect } from "react";

interface LoginGuardProps {
  children: React.ReactNode;
}

export default function LoginGuard({ children }: LoginGuardProps) {
  useEffect(() => {
    fetch("/auth/me", { credentials: "include" })
      .then((r) => r.ok ? r.json() : Promise.reject())
      .then((me) => { if (!me?.email) window.location.href = "/welcome"; })
      .catch(() => { window.location.href = "/welcome"; });
  }, []);

  return <>{children}</>;
}
