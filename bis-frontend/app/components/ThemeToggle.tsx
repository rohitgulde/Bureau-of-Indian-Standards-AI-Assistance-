"use client";

import * as React from "react";
import { Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";

export function ThemeToggle() {
  const { theme, setTheme, systemTheme } = useTheme();
  const [mounted, setMounted] = React.useState(false);

  React.useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return (
      <button className="w-8 h-8 flex items-center justify-center rounded-lg border border-border bg-card/50 text-muted-foreground opacity-50 cursor-default">
        <div className="w-4 h-4 rounded-full bg-muted animate-pulse" />
      </button>
    );
  }

  const isDark = theme === "dark" || (theme === "system" && systemTheme === "dark");

  return (
    <button
      onClick={() => setTheme(isDark ? "light" : "dark")}
      className="relative w-8 h-8 flex items-center justify-center rounded-lg border border-border bg-card/80 text-foreground hover:bg-muted/80 hover:text-primary transition-all shadow-sm overflow-hidden"
      aria-label="Toggle theme"
    >
      <Sun size={16} className={`absolute transition-all duration-300 ${isDark ? 'opacity-0 scale-50 rotate-90' : 'opacity-100 scale-100 rotate-0'}`} />
      <Moon size={16} className={`absolute transition-all duration-300 ${isDark ? 'opacity-100 scale-100 rotate-0' : 'opacity-0 scale-50 -rotate-90'}`} />
    </button>
  );
}
