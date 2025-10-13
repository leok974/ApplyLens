import * as React from "react"

type ToastProps = {
  title: string
  description?: string
  variant?: "default" | "destructive"
}

type ToastContextValue = {
  toast: (props: ToastProps) => void
}

const ToastContext = React.createContext<ToastContextValue | undefined>(undefined)

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = React.useState<(ToastProps & { id: string })[]>([])

  const toast = React.useCallback((props: ToastProps) => {
    const id = Math.random().toString(36).substr(2, 9)
    setToasts((prev) => [...prev, { ...props, id }])
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id))
    }, 3000)
  }, [])

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={cn(
              "rounded-lg border p-4 shadow-lg animate-in slide-in-from-bottom-5",
              t.variant === "destructive"
                ? "border-destructive bg-destructive text-destructive-foreground"
                : "border bg-background"
            )}
          >
            <div className="font-semibold">{t.title}</div>
            {t.description && (
              <div className="text-sm text-muted-foreground">{t.description}</div>
            )}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast() {
  const context = React.useContext(ToastContext)
  if (!context) {
    throw new Error("useToast must be used within ToastProvider")
  }
  return context
}

import { cn } from "@/lib/utils"
