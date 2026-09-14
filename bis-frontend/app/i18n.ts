"use client";

import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import enTranslation from "../public/locales/en.json";
import hiTranslation from "../public/locales/hi.json";
import teTranslation from "../public/locales/te.json";
import bnTranslation from "../public/locales/bn.json";
import mrTranslation from "../public/locales/mr.json";
import taTranslation from "../public/locales/ta.json";
import urTranslation from "../public/locales/ur.json";
import guTranslation from "../public/locales/gu.json";
import mlTranslation from "../public/locales/ml.json";
import knTranslation from "../public/locales/kn.json";
import orTranslation from "../public/locales/or.json";
import paTranslation from "../public/locales/pa.json";

const resources = {
  en: { translation: enTranslation },
  hi: { translation: hiTranslation },
  te: { translation: teTranslation },
  bn: { translation: bnTranslation },
  mr: { translation: mrTranslation },
  ta: { translation: taTranslation },
  ur: { translation: urTranslation },
  gu: { translation: guTranslation },
  ml: { translation: mlTranslation },
  kn: { translation: knTranslation },
  or: { translation: orTranslation },
  pa: { translation: paTranslation },
};

i18n
  .use(initReactI18next)
  .init({
    resources,
    lng: "en",
    fallbackLng: "en",
    supportedLngs: [
      "en", "hi", "te", "bn", "mr", "ta", "ur", "gu", "ml", "kn", "or", "pa"
    ],
    interpolation: {
      escapeValue: false, // React already escapes values
    },
    react: {
      useSuspense: false, // Easier for SSR/hydration in Next.js
    }
  });

export default i18n;
