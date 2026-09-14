"use client";

import ChatWindow from "@/app/components/ChatWindow";
import PdfUpload from "@/app/components/PdfUpload";
import { ThemeToggle } from "@/app/components/ThemeToggle";
import QuickChats from "@/app/components/QuickChats";
import { Shield, BookOpen, FlaskConical, Award } from "lucide-react";
import { useTranslation, Trans } from "react-i18next";

export default function Home() {
  const { t } = useTranslation();

  const STATS = [
    { icon: BookOpen,    label: t("stat_1_label"),       value: t("stat_1_value") },
    { icon: FlaskConical,label: t("stat_2_label"),     value: t("stat_2_value") },
    { icon: Award,       label: t("stat_3_label"),  value: t("stat_3_value")    },
    { icon: Shield,      label: t("stat_4_label"),    value: t("stat_4_value")     },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-slate-100 dark:from-background dark:via-background dark:to-background flex flex-col relative overflow-hidden">
      {/* ── Global Decorative Blobs (Premium feel in light mode) ── */}
      <div className="absolute top-0 left-0 w-full h-full overflow-hidden pointer-events-none z-0">
        <div className="absolute -top-[20%] -left-[10%] w-[50%] h-[50%] rounded-full bg-primary/5 dark:bg-primary/5 blur-[120px]" />
        <div className="absolute top-[20%] -right-[10%] w-[40%] h-[60%] rounded-full bg-rose-500/5 dark:bg-rose-500/5 blur-[100px]" />
      </div>
      {/* ── Top nav ── */}
      <header className="border-b border-border bg-white/60 dark:bg-sidebar/80 backdrop-blur-xl sticky top-0 z-40 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-primary/20 border border-primary/30 flex items-center justify-center">
              <Shield size={16} className="text-primary" />
            </div>
            <div className="leading-tight">
              <p className="text-sm font-bold text-sidebar-foreground tracking-tight">BIS Knowledge Portal</p>
              <p className="text-[10px] text-muted-foreground hidden sm:block">Bureau of Indian Standards · AI Assistant</p>
            </div>
          </div>
          <nav className="hidden md:flex items-center gap-6 text-xs text-muted-foreground">
            <a href="https://bis.gov.in" target="_blank" rel="noreferrer" className="hover:text-primary transition-colors">bis.gov.in</a>
            <a href="https://manakonline.in" target="_blank" rel="noreferrer" className="hover:text-primary transition-colors">Manak Online</a>
            <a href="https://huidonline.bis.gov.in" target="_blank" rel="noreferrer" className="hover:text-primary transition-colors">HUID Portal</a>
            <a href="http://localhost:8000/docs" target="_blank" rel="noreferrer"
              className="px-3 py-1.5 rounded-lg bg-primary/10 border border-primary/25 text-primary hover:bg-primary/20 transition-colors font-medium">
              API Docs
            </a>
            <ThemeToggle />
          </nav>
        </div>
      </header>

      {/* ── Main layout ── */}
      <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 py-6 grid grid-cols-1 lg:grid-cols-[1fr_550px] gap-6 items-start relative z-10">

        {/* Left: hero + stats */}
        <div className="flex flex-col gap-6 lg:sticky lg:top-20">

          {/* Hero card */}
          <div className="bg-gradient-to-br from-primary/10 to-primary/5 dark:from-sidebar dark:to-sidebar border border-primary/20 dark:border-border rounded-3xl p-8 sm:p-10 shadow-lg relative overflow-hidden">
            <div className="absolute top-0 right-0 w-64 h-64 bg-primary/10 dark:bg-primary/5 rounded-full blur-[80px] -translate-y-1/2 translate-x-1/3" />
            
            <div className="relative z-10">
              <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white dark:bg-primary/10 border border-primary/20 dark:border-primary/20 text-primary text-xs font-semibold mb-6 shadow-sm">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-primary"></span>
                </span>
                {t("ai_assistant_badge")}
              </div>
              <h1 className="text-4xl sm:text-5xl font-extrabold text-foreground tracking-tight mb-4 leading-normal sm:leading-relaxed">
                {t("hero_title")} <br className="hidden sm:block" />
                <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary to-rose-600 pb-2 mt-2 sm:mt-4 inline-block">
                  {t("hero_subtitle")}
                </span>
              </h1>
              <p className="text-base sm:text-lg text-muted-foreground leading-relaxed max-w-lg mb-8">
                <Trans i18nKey="hero_desc">
                  Ask about IS standard requirements, find accredited testing labs, navigate certification workflows, and verify gold hallmarks.
                </Trans>
              </p>
              
              <div className="grid grid-cols-2 gap-3 sm:gap-4 max-w-md">
                {STATS.map((s, i) => (
                  <div key={i} className="flex items-center gap-3 bg-white/50 dark:bg-background/50 border border-border rounded-xl p-3 shadow-sm hover:border-primary/30 transition-colors">
                    <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                      <s.icon size={16} className="text-primary" />
                    </div>
                    <div>
                      <p className="text-lg font-bold text-foreground leading-none mb-0.5">{s.value}</p>
                      <p className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold">{s.label}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Quick Chats & Upload */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <QuickChats />
            <PdfUpload />
          </div>

        </div>

        {/* Right: Chat Window */}
        <div className="h-[600px] lg:h-[80vh] min-h-[600px] flex flex-col bg-sidebar border border-border rounded-3xl shadow-xl overflow-hidden ring-1 ring-black/5 dark:ring-white/5">
          <div className="bg-card border-b border-border px-5 py-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="relative">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-rose-500 flex items-center justify-center shadow-inner">
                  <Shield size={20} className="text-white" />
                </div>
                <div className="absolute -bottom-1 -right-1 w-3.5 h-3.5 bg-green-500 border-2 border-card rounded-full" />
              </div>
              <div>
                <h2 className="text-sm font-bold text-foreground leading-tight">BIS Assistant</h2>
                <p className="text-xs text-muted-foreground flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
                  {t("online_status")}
                </p>
              </div>
            </div>
          </div>
          
          <div className="flex-1 overflow-hidden relative">
            <ChatWindow />
          </div>
        </div>

      </main>

      {/* ── Footer ── */}
      <footer className="border-t border-border bg-white/40 dark:bg-sidebar/60 backdrop-blur-md mt-4 relative z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <p className="text-[11px] text-muted-foreground">
            © 2024 BIS Knowledge Portal · Powered by Gemini 1.5, Bhashini Dhruva, Qdrant
          </p>
          <div className="flex items-center gap-4 text-[11px] text-muted-foreground">
            <a href="https://bis.gov.in/about-bis/" target="_blank" rel="noreferrer" className="hover:text-primary transition-colors">About BIS</a>
            <a href="https://bis.gov.in/consumer-affairs/" target="_blank" rel="noreferrer" className="hover:text-primary transition-colors">Consumer Affairs</a>
            <span>Helpline: 1800-11-4000</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
