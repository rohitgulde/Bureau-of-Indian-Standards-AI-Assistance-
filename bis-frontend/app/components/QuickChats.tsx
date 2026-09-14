"use client";

import { useTranslation } from "react-i18next";

export default function QuickChats() {
  const { t } = useTranslation();
  return (
    <div className="flex flex-wrap gap-2">
      {[
        t("quick_chat_1"),
        t("quick_chat_2"),
        t("quick_chat_3"),
        t("quick_chat_4"),
        t("quick_chat_5"),
      ].map((q) => (
        <button
          key={q}
          onClick={() => {
            if (typeof window !== "undefined") {
              window.dispatchEvent(new CustomEvent("send-quick-chat", { detail: q }));
            }
          }}
          className="px-3 py-1.5 rounded-full text-xs font-medium bg-white/60 dark:bg-muted/50 border border-slate-200 dark:border-border
            text-slate-600 dark:text-muted-foreground hover:border-primary/40 hover:text-primary hover:bg-primary/5
            transition-all duration-300 cursor-pointer shadow-sm hover:shadow text-left"
        >
          {q}
        </button>
      ))}
    </div>
  );
}
