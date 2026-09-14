"use client";

import React, { createContext, useContext, useState, useEffect, ReactNode } from "react";
import i18nInstance from "../i18n";
import { useTranslation, I18nextProvider } from "react-i18next";

export const LANGUAGES = [
  { code: "en", label: "English", nativeLabel: "English" },
  { code: "hi", label: "Hindi", nativeLabel: "हिन्दी" },
  { code: "te", label: "Telugu", nativeLabel: "తెలుగు" },
  { code: "bn", label: "Bengali", nativeLabel: "বাংলা" },
  { code: "mr", label: "Marathi", nativeLabel: "मराठी" },
  { code: "ta", label: "Tamil", nativeLabel: "தமிழ்" },
  { code: "ur", label: "Urdu", nativeLabel: "اردو" },
  { code: "gu", label: "Gujarati", nativeLabel: "ગુજરાતી" },
  { code: "ml", label: "Malayalam", nativeLabel: "മലയാളം" },
  { code: "kn", label: "Kannada", nativeLabel: "ಕನ್ನಡ" },
  { code: "or", label: "Odia", nativeLabel: "ଓଡ଼ିଆ" },
  { code: "pa", label: "Punjabi", nativeLabel: "ਪੰਜਾਬੀ" },
] as const;

export type LangCode = (typeof LANGUAGES)[number]["code"];

interface LanguageContextType {
  lang: LangCode;
  setLang: (lang: LangCode) => void;
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<LangCode>("en");

  // Sync state with i18n initialized language (if loaded from localStorage/detector)
  useEffect(() => {
    // Read from localStorage to respect user's previous choice
    const savedLang = localStorage.getItem("i18nextLng");
    if (savedLang && LANGUAGES.some(l => l.code === savedLang)) {
      setLangState(savedLang as LangCode);
      i18nInstance.changeLanguage(savedLang);
    }
  }, []);

  const setLang = (newLang: LangCode) => {
    setLangState(newLang);
    localStorage.setItem("i18nextLng", newLang);
    i18nInstance.changeLanguage(newLang); // triggers i18n static translation
  };

  return (
    <LanguageContext.Provider value={{ lang, setLang }}>
      <I18nextProvider i18n={i18nInstance}>
        {children}
      </I18nextProvider>
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const context = useContext(LanguageContext);
  if (context === undefined) {
    throw new Error("useLanguage must be used within a LanguageProvider");
  }
  return context;
}
