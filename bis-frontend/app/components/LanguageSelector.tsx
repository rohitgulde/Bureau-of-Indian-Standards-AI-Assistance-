"use client";

import React, { useState, useRef, useEffect } from "react";
import { Globe, ChevronDown } from "lucide-react";
import { useLanguage, LANGUAGES } from "./LanguageContext";
import { useTranslation } from "react-i18next";

export default function LanguageSelector() {
  const { lang, setLang } = useLanguage();
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const selected = LANGUAGES.find((l) => l.code === lang) || LANGUAGES[0];

  useEffect(() => {
    function handle(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node))
        setOpen(false);
    }
    document.addEventListener("mousedown", handle);
    return () => document.removeEventListener("mousedown", handle);
  }, []);

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        title="Select language"
        className="flex items-center gap-1.5 h-10 px-3 rounded-xl
          bg-card border border-border text-sm text-foreground
          hover:border-primary/50 hover:bg-muted/40
          transition-all duration-150 min-w-[90px]"
      >
        <Globe size={14} className="text-muted-foreground flex-shrink-0" />
        <span className="hidden sm:inline text-xs">{selected.nativeLabel}</span>
        <span className="sm:hidden text-xs uppercase font-mono">{selected.code}</span>
        <ChevronDown
          size={12}
          className={`ml-auto text-muted-foreground transition-transform ${open ? "rotate-180" : ""}`}
        />
      </button>

      {open && (
        <div
          className="absolute bottom-full mb-2 right-0 z-50 w-52
            bg-card border border-border rounded-2xl shadow-2xl
            overflow-hidden py-1"
        >
          <p className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-widest
            text-muted-foreground border-b border-border mb-1">
            Language / भाषा
          </p>
          <div className="max-h-72 overflow-y-auto">
            {LANGUAGES.map((l) => (
              <button
                key={l.code}
                onClick={() => { setLang(l.code); setOpen(false); }}
                className={`w-full flex items-center justify-between px-3 py-2
                  text-sm hover:bg-accent transition-colors
                  ${lang === l.code ? "text-primary font-medium bg-primary/8" : "text-foreground"}`}
              >
                <span>{l.label}</span>
                <span className="text-xs text-muted-foreground font-mono">
                  {l.nativeLabel}
                </span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
