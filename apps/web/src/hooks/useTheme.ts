import { useEffect, useState } from "react";

export type ThemeMode = "light" | "dark" | "system";

export function useTheme() {
  const [theme, setTheme] = useState<ThemeMode>(() => {
    // try localStorage first
    const saved = window.localStorage.getItem("applylens-theme");
    if (saved === "dark" || saved === "light" || saved === "system") return saved as ThemeMode;
    // default to dark for now (keep current look by default)
    return "dark";
  });

  useEffect(() => {
    const applyTheme = (mode: ThemeMode) => {
      let effectiveTheme: "light" | "dark";

      if (mode === "system") {
        // Check system preference
        effectiveTheme = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
      } else {
        effectiveTheme = mode;
      }

      if (effectiveTheme === "dark") {
        document.documentElement.classList.add("dark");
      } else {
        document.documentElement.classList.remove("dark");
      }
    };

    applyTheme(theme);
    window.localStorage.setItem("applylens-theme", theme);

    // Listen for system theme changes if mode is "system"
    if (theme === "system") {
      const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
      const handleChange = () => applyTheme("system");
      mediaQuery.addEventListener("change", handleChange);
      return () => mediaQuery.removeEventListener("change", handleChange);
    }
  }, [theme]);

  return { theme, setTheme };
}
