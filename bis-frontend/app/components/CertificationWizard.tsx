"use client";

/**
 * CertificationWizard.tsx
 * ────────────────────────
 * Step-by-step interactive certification guide for MSMEs & Startups.
 *
 * Steps:
 *  1. Select Product Category
 *  2. Domestic vs. International manufacturing
 *  3. Dynamic scheme determination (ISI / CRS / FMCS)
 *  4. Results — standards, doc checklist & Manak Online link
 */

import React, { useState, useCallback, useEffect } from "react";
import {
  CheckCircle2,
  ChevronRight,
  ChevronLeft,
  X,
  Layers,
  Factory,
  Globe,
  ShieldCheck,
  FileText,
  ExternalLink,
  Info,
  AlertCircle,
  ArrowRight,
  Sparkles,
  ClipboardList,
  BookOpen,
  Package,
} from "lucide-react";

// ─────────────────────────────────────────────────────────────────────────────
// Data model
// ─────────────────────────────────────────────────────────────────────────────

interface ProductCategory {
  id: string;
  label: string;
  icon: React.ReactNode;
  description: string;
  examples: string[];
  color: string;
  bgColor: string;
}

type ManufacturingOrigin = "domestic" | "international";
type CertScheme = "ISI" | "CRS" | "FMCS";

interface SchemeResult {
  scheme: CertScheme;
  fullName: string;
  description: string;
  applicabilityNote: string;
  standards: { code: string; title: string; scope: string }[];
  docs: { label: string; mandatory: boolean; note?: string }[];
  manakLink: string;
  timelineWeeks: string;
  color: string;
  gradientFrom: string;
  gradientTo: string;
  borderColor: string;
  badgeColor: string;
}

// ─────────────────────────────────────────────────────────────────────────────
// Product categories
// ─────────────────────────────────────────────────────────────────────────────

const PRODUCT_CATEGORIES: ProductCategory[] = [
  {
    id: "electronics",
    label: "Electronics & IT Equipment",
    icon: <Package size={20} />,
    description: "Consumer electronics, IT hardware, telecom equipment",
    examples: ["Mobile phones", "Laptops", "LED lights", "Power adapters", "Set-top boxes"],
    color: "text-violet-700",
    bgColor: "bg-violet-50 border-violet-200 hover:border-violet-400",
  },
  {
    id: "food",
    label: "Food & Beverages",
    icon: <Layers size={20} />,
    description: "Packaged food, beverages, dairy, water",
    examples: ["Packaged water", "Edible oils", "Milk products", "Fruit juices"],
    color: "text-emerald-700",
    bgColor: "bg-emerald-50 border-emerald-200 hover:border-emerald-400",
  },
  {
    id: "steel",
    label: "Steel & Metal Products",
    icon: <Factory size={20} />,
    description: "Structural steel, pipes, wires, fittings",
    examples: ["TMT bars", "HR sheets", "Stainless steel utensils", "GI pipes"],
    color: "text-slate-700",
    bgColor: "bg-slate-50 border-slate-200 hover:border-slate-400",
  },
  {
    id: "cement",
    label: "Cement & Building Materials",
    icon: <Layers size={20} />,
    description: "Cement, tiles, bricks, paints",
    examples: ["OPC cement", "PPC cement", "Ceramic tiles", "Plywood"],
    color: "text-amber-700",
    bgColor: "bg-amber-50 border-amber-200 hover:border-amber-400",
  },
  {
    id: "chemicals",
    label: "Chemicals & Petrochemicals",
    icon: <AlertCircle size={20} />,
    description: "Chemicals, fertilisers, LPG cylinders",
    examples: ["LPG cylinders", "Pesticides", "Fertilisers", "Industrial chemicals"],
    color: "text-rose-700",
    bgColor: "bg-rose-50 border-rose-200 hover:border-rose-400",
  },
  {
    id: "textiles",
    label: "Textiles & Apparel",
    icon: <Layers size={20} />,
    description: "Fabrics, garments, technical textiles",
    examples: ["Cotton fabrics", "Woollen blankets", "Jute products", "PPE kits"],
    color: "text-pink-700",
    bgColor: "bg-pink-50 border-pink-200 hover:border-pink-400",
  },
  {
    id: "electrical",
    label: "Electrical Appliances",
    icon: <Sparkles size={20} />,
    description: "Wiring accessories, switches, cables, appliances",
    examples: ["MCBs", "Wiring cables", "Switches", "Electric fans", "Geysers"],
    color: "text-yellow-700",
    bgColor: "bg-yellow-50 border-yellow-200 hover:border-yellow-400",
  },
  {
    id: "auto",
    label: "Automotive Components",
    icon: <ShieldCheck size={20} />,
    description: "Vehicle parts, tyres, helmets, batteries",
    examples: ["Helmets", "Tyres", "Automotive batteries", "Brake pads"],
    color: "text-blue-700",
    bgColor: "bg-blue-50 border-blue-200 hover:border-blue-400",
  },
];

// ─────────────────────────────────────────────────────────────────────────────
// Scheme determination logic
// ─────────────────────────────────────────────────────────────────────────────

const SCHEME_DATA: Record<string, SchemeResult> = {
  ISI: {
    scheme: "ISI",
    fullName: "ISI Mark Scheme",
    description:
      "The ISI (Indian Standards Institution) Mark is BIS's most recognised certification scheme for products manufactured in India. It confirms conformity to Indian Standards.",
    applicabilityNote:
      "Mandatory for many product categories including cement, steel, LPG cylinders, electrical wires/cables, and several food items. Voluntary for others.",
    standards: [
      { code: "IS 2062", title: "Hot Rolled Medium and High Tensile Structural Steel", scope: "Structural steel products" },
      { code: "IS 456", title: "Plain and Reinforced Concrete", scope: "Cement and concrete applications" },
      { code: "IS 1554", title: "PVC Insulated Cables", scope: "Electrical wiring cables" },
      { code: "IS 13252", title: "IT Equipment — Safety", scope: "IT & electronic equipment" },
    ],
    docs: [
      { label: "Application Form (Form V)", mandatory: true },
      { label: "Certificate of Incorporation / Partnership Deed", mandatory: true },
      { label: "Factory plan / layout drawing", mandatory: true },
      { label: "List of manufacturing machinery & testing equipment", mandatory: true },
      { label: "Test reports from BIS-recognised laboratory", mandatory: true },
      { label: "Proof of brand ownership / trademark", mandatory: false, note: "Required if brand differs from company name" },
      { label: "Quality Assurance Plan (QAP)", mandatory: true },
      { label: "MSME/Udyam Registration Certificate", mandatory: false, note: "Speeds up fee concession eligibility" },
      { label: "GST Registration Certificate", mandatory: true },
      { label: "Consent-to-Operate from Pollution Control Board", mandatory: false, note: "Required for notified product groups" },
    ],
    manakLink: "https://www.manakonline.in/MANAK/applicationISI.do",
    timelineWeeks: "8 – 16",
    color: "text-gov-navy-800",
    gradientFrom: "from-gov-navy-800",
    gradientTo: "to-gov-navy-600",
    borderColor: "border-gov-navy-200",
    badgeColor: "bg-gov-navy-800/10 text-gov-navy-800",
  },
  CRS: {
    scheme: "CRS",
    fullName: "Compulsory Registration Scheme",
    description:
      "CRS is a registration-based (not licence-based) scheme for electronics and IT goods notified under the Electronics & IT Goods (Requirement for Compulsory Registration) Order, 2012.",
    applicabilityNote:
      "Mandatory for all notified electronics & IT products — including mobile phones, power banks, adapters, laptops, and LED lights — regardless of whether manufactured domestically or imported.",
    standards: [
      { code: "IS 13252 (Part 1)", title: "Safety of ITE — Part 1: General Requirements", scope: "All IT/electronic equipment" },
      { code: "IS 16046 (Part 2)", title: "Safety for Audio/Video Equipment", scope: "AV consumer electronics" },
      { code: "IS 15885 (Part 2/Sec 13)", title: "Safety of Household Appliances — Portable Immersion Heaters", scope: "Small household appliances" },
      { code: "IS 16901", title: "Safety of Wireless Charging Systems", scope: "Wireless chargers" },
    ],
    docs: [
      { label: "Application Form (online via Manak Portal)", mandatory: true },
      { label: "Test Report from BIS-empanelled laboratory (within last 2 years)", mandatory: true },
      { label: "Company / Importer PAN Card & GST Certificate", mandatory: true },
      { label: "Product photograph and technical specifications", mandatory: true },
      { label: "Declaration of Conformity (DoC)", mandatory: true },
      { label: "Udyam / DPIIT Startup Registration", mandatory: false, note: "Required to avail reduced registration fee" },
      { label: "Authorisation Letter (for importers acting on behalf of foreign OEM)", mandatory: false },
      { label: "Sample submission acknowledgement from lab", mandatory: true },
    ],
    manakLink: "https://www.manakonline.in/MANAK/applicationCRS.do",
    timelineWeeks: "4 – 8",
    color: "text-violet-700",
    gradientFrom: "from-violet-700",
    gradientTo: "to-violet-500",
    borderColor: "border-violet-200",
    badgeColor: "bg-violet-100 text-violet-700",
  },
  FMCS: {
    scheme: "FMCS",
    fullName: "Foreign Manufacturers Certification Scheme",
    description:
      "FMCS allows foreign manufacturers to obtain BIS certification (ISI Mark) for products manufactured outside India, enabling them to legally sell in the Indian market.",
    applicabilityNote:
      "Required for foreign manufacturers of products that are compulsorily notified under ISI. Importers must ensure the foreign manufacturer holds a valid FMCS licence before import.",
    standards: [
      { code: "IS 2074", title: "Ready Mixed Paints — Specification", scope: "Paints manufactured abroad" },
      { code: "IS 1240", title: "Domestic Pressure Cookers", scope: "Pressure cookers manufactured abroad" },
      { code: "IS 616", title: "Specification for Miniature Fuses", scope: "Electronic fuses" },
      { code: "IS 9000", title: "Basic Environmental Testing Procedures", scope: "Electronic/electrical products" },
    ],
    docs: [
      { label: "Application Form (FMCS Form I)", mandatory: true },
      { label: "Certificate of Incorporation of foreign company", mandatory: true },
      { label: "Authorisation / Power of Attorney for Indian Representative", mandatory: true },
      { label: "Factory layout and process flow chart", mandatory: true },
      { label: "Test Reports from BIS-recognised or accredited lab", mandatory: true },
      { label: "Quality Control Manual / QAP", mandatory: true },
      { label: "Previous certifications (ISO 9001, CE, etc.)", mandatory: false, note: "Strengthens application" },
      { label: "List of all product models / variants", mandatory: true },
      { label: "Appointment letter of Indian Agent", mandatory: true },
      { label: "Import-Export Code (IEC) of Indian importer", mandatory: true },
    ],
    manakLink: "https://www.manakonline.in/MANAK/applicationFMCS.do",
    timelineWeeks: "16 – 24",
    color: "text-gov-orange-600",
    gradientFrom: "from-gov-orange-600",
    gradientTo: "to-gov-orange-400",
    borderColor: "border-gov-orange-200",
    badgeColor: "bg-gov-orange-600/10 text-gov-orange-600",
  },
};

function determineScheme(categoryId: string, origin: ManufacturingOrigin): CertScheme {
  if (origin === "international") return "FMCS";
  if (categoryId === "electronics") return "CRS";
  return "ISI";
}

// ─────────────────────────────────────────────────────────────────────────────
// Step progress bar
// ─────────────────────────────────────────────────────────────────────────────

const STEPS = ["Product", "Origin", "Scheme", "Results"] as const;

function StepBar({ current }: { current: number }) {
  return (
    <div className="flex items-center gap-0 mb-8">
      {STEPS.map((label, i) => {
        const done = i < current;
        const active = i === current;
        return (
          <React.Fragment key={label}>
            <div className="flex flex-col items-center">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center border-2 transition-all duration-300 text-xs font-bold
                  ${done
                    ? "bg-gov-navy-800 border-gov-navy-800 text-white"
                    : active
                    ? "border-gov-navy-800 text-gov-navy-800 bg-white scale-110 shadow-md"
                    : "border-gov-slate-300 text-gov-slate-400 bg-white"
                  }`}
              >
                {done ? <CheckCircle2 size={14} /> : i + 1}
              </div>
              <span
                className={`mt-1.5 text-[10px] font-semibold tracking-wide uppercase transition-colors ${
                  active ? "text-gov-navy-800" : done ? "text-gov-navy-600" : "text-gov-slate-400"
                }`}
              >
                {label}
              </span>
            </div>
            {i < STEPS.length - 1 && (
              <div
                className={`flex-1 h-0.5 mx-1 mt-[-12px] transition-colors duration-500 ${
                  done ? "bg-gov-navy-800" : "bg-gov-slate-200"
                }`}
              />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Step 1 — Product Category
// ─────────────────────────────────────────────────────────────────────────────

function Step1({
  selected,
  onSelect,
  onNext,
}: {
  selected: string | null;
  onSelect: (id: string) => void;
  onNext: () => void;
}) {
  return (
    <div className="animate-fade-in">
      <div className="mb-5">
        <h3 className="text-lg font-bold text-gov-navy-800">Select Your Product Category</h3>
        <p className="text-sm text-gov-slate-500 mt-1">
          Choose the category that best describes your product. This determines which BIS scheme applies.
        </p>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-6">
        {PRODUCT_CATEGORIES.map((cat) => (
          <button
            key={cat.id}
            id={`category-${cat.id}`}
            onClick={() => onSelect(cat.id)}
            className={`group relative text-left rounded-xl border-2 p-4 transition-all duration-200
              ${
                selected === cat.id
                  ? "border-gov-navy-700 bg-gov-navy-50 shadow-gov-sm ring-2 ring-gov-navy-800/20"
                  : `${cat.bgColor} border-opacity-60`
              }
            `}
          >
            <div className="flex items-start gap-3">
              <span className={`mt-0.5 ${selected === cat.id ? "text-gov-navy-800" : cat.color}`}>
                {cat.icon}
              </span>
              <div className="flex-1 min-w-0">
                <p className={`font-semibold text-sm ${selected === cat.id ? "text-gov-navy-800" : cat.color}`}>
                  {cat.label}
                </p>
                <p className="text-xs text-gov-slate-500 mt-0.5 line-clamp-1">{cat.description}</p>
                <div className="flex flex-wrap gap-1 mt-2">
                  {cat.examples.slice(0, 3).map((ex) => (
                    <span
                      key={ex}
                      className="text-[10px] bg-white/70 border border-gov-slate-200 px-1.5 py-0.5 rounded-full text-gov-slate-600"
                    >
                      {ex}
                    </span>
                  ))}
                </div>
              </div>
              {selected === cat.id && (
                <CheckCircle2 size={18} className="text-gov-navy-800 flex-shrink-0 mt-0.5" />
              )}
            </div>
          </button>
        ))}
      </div>
      <div className="flex justify-end">
        <button
          id="step1-next"
          disabled={!selected}
          onClick={onNext}
          className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-gov-navy-800 text-white text-sm font-semibold
            disabled:opacity-40 disabled:cursor-not-allowed hover:bg-gov-navy-700 active:bg-gov-navy-900
            transition-all duration-150 shadow-gov-sm hover:shadow-gov-md"
        >
          Continue <ChevronRight size={16} />
        </button>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Step 2 — Manufacturing Origin
// ─────────────────────────────────────────────────────────────────────────────

function Step2({
  origin,
  onSelect,
  onNext,
  onBack,
}: {
  origin: ManufacturingOrigin | null;
  onSelect: (o: ManufacturingOrigin) => void;
  onNext: () => void;
  onBack: () => void;
}) {
  return (
    <div className="animate-fade-in">
      <div className="mb-6">
        <h3 className="text-lg font-bold text-gov-navy-800">Manufacturing Location</h3>
        <p className="text-sm text-gov-slate-500 mt-1">
          Is the product manufactured within India or outside India? This is the primary factor that determines
          the applicable BIS scheme.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-8">
        {/* Domestic */}
        <button
          id="origin-domestic"
          onClick={() => onSelect("domestic")}
          className={`group relative rounded-2xl border-2 p-6 text-left transition-all duration-200
            ${
              origin === "domestic"
                ? "border-gov-navy-700 bg-gov-navy-50 shadow-gov-md ring-2 ring-gov-navy-800/20"
                : "border-gov-slate-200 bg-white hover:border-gov-navy-300 hover:shadow-gov-sm"
            }
          `}
        >
          <div className="flex flex-col items-start gap-3">
            <div
              className={`w-12 h-12 rounded-xl flex items-center justify-center transition-colors
                ${origin === "domestic" ? "bg-gov-navy-800 text-white" : "bg-gov-slate-100 text-gov-slate-600"}`}
            >
              <Factory size={22} />
            </div>
            <div>
              <p className="font-bold text-base text-gov-navy-800">🇮🇳 Made in India</p>
              <p className="text-sm text-gov-slate-500 mt-1">
                Manufacturing unit is located within India. Product is made domestically.
              </p>
              <div className="mt-3 flex items-center gap-1.5 text-xs font-medium text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-full w-fit">
                <Sparkles size={11} />
                ISI Mark or CRS applies
              </div>
            </div>
          </div>
          {origin === "domestic" && (
            <CheckCircle2
              size={20}
              className="absolute top-4 right-4 text-gov-navy-800"
            />
          )}
        </button>

        {/* International */}
        <button
          id="origin-international"
          onClick={() => onSelect("international")}
          className={`group relative rounded-2xl border-2 p-6 text-left transition-all duration-200
            ${
              origin === "international"
                ? "border-gov-orange-500 bg-gov-orange-50 shadow-gov-md ring-2 ring-gov-orange-600/20"
                : "border-gov-slate-200 bg-white hover:border-gov-orange-300 hover:shadow-gov-sm"
            }
          `}
        >
          <div className="flex flex-col items-start gap-3">
            <div
              className={`w-12 h-12 rounded-xl flex items-center justify-center transition-colors
                ${origin === "international" ? "bg-gov-orange-600 text-white" : "bg-gov-slate-100 text-gov-slate-600"}`}
            >
              <Globe size={22} />
            </div>
            <div>
              <p className="font-bold text-base text-gov-navy-800">🌏 Manufactured Abroad</p>
              <p className="text-sm text-gov-slate-500 mt-1">
                Manufacturing unit is outside India. Product is imported or will be imported.
              </p>
              <div className="mt-3 flex items-center gap-1.5 text-xs font-medium text-gov-orange-700 bg-gov-orange-50 px-2.5 py-1 rounded-full w-fit border border-gov-orange-200">
                <Globe size={11} />
                FMCS applies
              </div>
            </div>
          </div>
          {origin === "international" && (
            <CheckCircle2
              size={20}
              className="absolute top-4 right-4 text-gov-orange-600"
            />
          )}
        </button>
      </div>

      <div className="flex items-center justify-between">
        <button
          id="step2-back"
          onClick={onBack}
          className="flex items-center gap-1.5 px-4 py-2 rounded-xl border border-gov-slate-200 text-sm text-gov-slate-600
            hover:border-gov-slate-300 hover:bg-gov-slate-50 transition-all"
        >
          <ChevronLeft size={15} /> Back
        </button>
        <button
          id="step2-next"
          disabled={!origin}
          onClick={onNext}
          className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-gov-navy-800 text-white text-sm font-semibold
            disabled:opacity-40 disabled:cursor-not-allowed hover:bg-gov-navy-700 active:bg-gov-navy-900
            transition-all duration-150 shadow-gov-sm hover:shadow-gov-md"
        >
          Determine Scheme <ChevronRight size={16} />
        </button>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Step 3 — Scheme determination display
// ─────────────────────────────────────────────────────────────────────────────

function Step3({
  scheme,
  category,
  origin,
  onNext,
  onBack,
}: {
  scheme: CertScheme;
  category: ProductCategory;
  origin: ManufacturingOrigin;
  onNext: () => void;
  onBack: () => void;
}) {
  const data = SCHEME_DATA[scheme];

  return (
    <div className="animate-fade-in">
      <div className="mb-5">
        <h3 className="text-lg font-bold text-gov-navy-800">Applicable BIS Scheme</h3>
        <p className="text-sm text-gov-slate-500 mt-1">
          Based on your inputs, here is the certification scheme that applies to your product.
        </p>
      </div>

      {/* Summary pill row */}
      <div className="flex flex-wrap gap-2 mb-5">
        <span className="flex items-center gap-1.5 text-xs bg-gov-slate-100 border border-gov-slate-200 rounded-full px-3 py-1 text-gov-slate-600 font-medium">
          <Package size={11} />
          {category.label}
        </span>
        <span className="flex items-center gap-1.5 text-xs bg-gov-slate-100 border border-gov-slate-200 rounded-full px-3 py-1 text-gov-slate-600 font-medium">
          {origin === "domestic" ? <Factory size={11} /> : <Globe size={11} />}
          {origin === "domestic" ? "Domestic Manufacturing" : "International Manufacturing"}
        </span>
      </div>

      {/* Scheme card */}
      <div
        className={`rounded-2xl border-2 ${data.borderColor} overflow-hidden shadow-gov-md mb-6`}
      >
        {/* Gradient header */}
        <div className={`bg-gradient-to-r ${data.gradientFrom} ${data.gradientTo} px-6 py-5`}>
          <div className="flex items-center gap-3">
            <div className="w-14 h-14 rounded-2xl bg-white/20 backdrop-blur-sm flex items-center justify-center">
              <ShieldCheck size={28} className="text-white" />
            </div>
            <div>
              <span className="text-white/70 text-xs font-semibold tracking-widest uppercase">
                Recommended Scheme
              </span>
              <h4 className="text-white font-bold text-2xl leading-tight">{data.scheme}</h4>
              <p className="text-white/80 text-sm font-medium">{data.fullName}</p>
            </div>
          </div>
        </div>

        {/* Body */}
        <div className="p-5 bg-white space-y-4">
          <p className="text-sm text-gov-slate-600 leading-relaxed">{data.description}</p>

          <div className="flex items-start gap-2.5 rounded-xl bg-blue-50 border border-blue-200 p-3.5">
            <Info size={15} className="text-blue-600 flex-shrink-0 mt-0.5" />
            <p className="text-xs text-blue-800 leading-relaxed">{data.applicabilityNote}</p>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-gov-slate-500 uppercase tracking-wide">
              Typical Timeline:
            </span>
            <span className={`text-xs font-bold px-2.5 py-0.5 rounded-full ${data.badgeColor}`}>
              {data.timelineWeeks} weeks
            </span>
          </div>
        </div>
      </div>

      <div className="flex items-center justify-between">
        <button
          id="step3-back"
          onClick={onBack}
          className="flex items-center gap-1.5 px-4 py-2 rounded-xl border border-gov-slate-200 text-sm text-gov-slate-600
            hover:border-gov-slate-300 hover:bg-gov-slate-50 transition-all"
        >
          <ChevronLeft size={15} /> Back
        </button>
        <button
          id="step3-next"
          onClick={onNext}
          className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-gov-navy-800 text-white text-sm font-semibold
            hover:bg-gov-navy-700 active:bg-gov-navy-900 transition-all duration-150 shadow-gov-sm hover:shadow-gov-md"
        >
          View Full Checklist <ArrowRight size={16} />
        </button>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Step 4 — Full results
// ─────────────────────────────────────────────────────────────────────────────

function Step4({
  scheme,
  onBack,
  onReset,
}: {
  scheme: CertScheme;
  onBack: () => void;
  onReset: () => void;
}) {
  const data = SCHEME_DATA[scheme];
  const [tab, setTab] = useState<"standards" | "docs">("standards");
  const [checkedDocs, setCheckedDocs] = useState<Record<number, boolean>>({});

  const toggleDoc = (i: number) =>
    setCheckedDocs((prev) => ({ ...prev, [i]: !prev[i] }));

  const mandatoryCount = data.docs.filter((d) => d.mandatory).length;
  const checkedMandatoryCount = data.docs.filter((d, i) => d.mandatory && checkedDocs[i]).length;
  const progress = mandatoryCount > 0 ? Math.round((checkedMandatoryCount / mandatoryCount) * 100) : 0;

  return (
    <div className="animate-fade-in">
      {/* Header with scheme badge */}
      <div className="flex items-center gap-3 mb-5">
        <div
          className={`flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r ${data.gradientFrom} ${data.gradientTo} shadow-gov-sm`}
        >
          <ShieldCheck size={16} className="text-white" />
          <span className="text-white font-bold text-sm">{data.scheme} Scheme</span>
        </div>
        <div>
          <p className="text-sm font-semibold text-gov-navy-800">{data.fullName}</p>
          <p className="text-xs text-gov-slate-500">Complete your certification requirements below</p>
        </div>
      </div>

      {/* Tab switcher */}
      <div className="flex rounded-xl border border-gov-slate-200 p-1 mb-5 bg-gov-slate-50">
        <button
          id="tab-standards"
          onClick={() => setTab("standards")}
          className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-lg text-sm font-semibold transition-all
            ${tab === "standards" ? "bg-white shadow-gov-sm text-gov-navy-800" : "text-gov-slate-500 hover:text-gov-navy-800"}`}
        >
          <BookOpen size={14} /> Testing Standards
        </button>
        <button
          id="tab-docs"
          onClick={() => setTab("docs")}
          className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-lg text-sm font-semibold transition-all
            ${tab === "docs" ? "bg-white shadow-gov-sm text-gov-navy-800" : "text-gov-slate-500 hover:text-gov-navy-800"}`}
        >
          <ClipboardList size={14} /> Document Checklist
        </button>
      </div>

      {/* Standards tab */}
      {tab === "standards" && (
        <div className="space-y-3 mb-6 animate-fade-in">
          {data.standards.map((std, i) => (
            <div
              key={i}
              className="flex items-start gap-3 rounded-xl border border-gov-slate-200 bg-white p-4 hover:border-gov-navy-300 hover:shadow-gov-sm transition-all"
            >
              <div className="w-9 h-9 rounded-lg bg-gov-navy-50 flex items-center justify-center flex-shrink-0">
                <FileText size={16} className="text-gov-navy-800" />
              </div>
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-mono text-xs font-bold text-gov-navy-800 bg-gov-navy-50 border border-gov-navy-200 px-2 py-0.5 rounded">
                    {std.code}
                  </span>
                </div>
                <p className="text-sm font-semibold text-gov-slate-800 mt-1">{std.title}</p>
                <p className="text-xs text-gov-slate-500 mt-0.5">{std.scope}</p>
              </div>
            </div>
          ))}
          <div className="flex items-start gap-2 rounded-xl bg-amber-50 border border-amber-200 p-3.5 mt-2">
            <AlertCircle size={14} className="text-amber-600 flex-shrink-0 mt-0.5" />
            <p className="text-xs text-amber-800">
              These are representative standards. Always verify the exact IS number applicable to your specific product model on the{" "}
              <a
                href="https://www.bis.gov.in/standardization/bis-standards/"
                target="_blank"
                rel="noopener noreferrer"
                className="underline font-semibold hover:text-amber-900"
              >
                BIS Standards portal
              </a>
              .
            </p>
          </div>
        </div>
      )}

      {/* Docs tab */}
      {tab === "docs" && (
        <div className="mb-6 animate-fade-in">
          {/* Progress bar */}
          <div className="mb-4 rounded-xl bg-gov-slate-50 border border-gov-slate-200 p-3.5">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-xs font-semibold text-gov-slate-600">
                Mandatory documents: {checkedMandatoryCount} / {mandatoryCount}
              </span>
              <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${data.badgeColor}`}>
                {progress}%
              </span>
            </div>
            <div className="w-full h-2 rounded-full bg-gov-slate-200 overflow-hidden">
              <div
                className={`h-2 rounded-full bg-gradient-to-r ${data.gradientFrom} ${data.gradientTo} transition-all duration-500`}
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>

          <div className="space-y-2">
            {data.docs.map((doc, i) => (
              <label
                key={i}
                htmlFor={`doc-check-${i}`}
                className={`flex items-start gap-3 rounded-xl border p-3.5 cursor-pointer select-none transition-all
                  ${checkedDocs[i]
                    ? "border-gov-navy-300 bg-gov-navy-50"
                    : "border-gov-slate-200 bg-white hover:border-gov-slate-300"
                  }`}
              >
                <input
                  id={`doc-check-${i}`}
                  type="checkbox"
                  className="mt-0.5 accent-gov-navy-800 w-4 h-4 flex-shrink-0 cursor-pointer"
                  checked={!!checkedDocs[i]}
                  onChange={() => toggleDoc(i)}
                />
                <div className="flex-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-sm font-medium text-gov-slate-800">{doc.label}</span>
                    {doc.mandatory ? (
                      <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-full bg-red-100 text-red-700 border border-red-200">
                        REQUIRED
                      </span>
                    ) : (
                      <span className="text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-gov-slate-100 text-gov-slate-500 border border-gov-slate-200">
                        Optional
                      </span>
                    )}
                  </div>
                  {doc.note && (
                    <p className="text-xs text-gov-slate-400 mt-0.5 italic">{doc.note}</p>
                  )}
                </div>
              </label>
            ))}
          </div>
        </div>
      )}

      {/* Manak Online CTA */}
      <div className="rounded-2xl bg-gradient-to-br from-gov-navy-900 to-gov-navy-700 p-5 mb-5 shadow-gov-lg">
        <div className="flex items-start gap-4">
          <div className="w-12 h-12 rounded-xl bg-white/15 flex items-center justify-center flex-shrink-0">
            <ExternalLink size={22} className="text-white" />
          </div>
          <div className="flex-1">
            <p className="text-white font-bold text-base">Apply on Manak Online Portal</p>
            <p className="text-white/70 text-xs mt-0.5 mb-3 leading-relaxed">
              The official BIS online portal for submitting your {data.scheme} application, uploading documents, and
              tracking your licence status.
            </p>
            <a
              id="manak-online-link"
              href={data.manakLink}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 bg-white text-gov-navy-800 px-5 py-2 rounded-xl text-sm font-bold
                hover:bg-gov-slate-100 active:bg-gov-slate-200 transition-all shadow-gov-sm hover:shadow-gov-md"
            >
              Open Manak Online <ExternalLink size={13} />
            </a>
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center justify-between">
        <button
          id="step4-back"
          onClick={onBack}
          className="flex items-center gap-1.5 px-4 py-2 rounded-xl border border-gov-slate-200 text-sm text-gov-slate-600
            hover:border-gov-slate-300 hover:bg-gov-slate-50 transition-all"
        >
          <ChevronLeft size={15} /> Back
        </button>
        <button
          id="step4-restart"
          onClick={onReset}
          className="flex items-center gap-2 px-5 py-2 rounded-xl border border-gov-navy-200 text-gov-navy-800 text-sm font-semibold
            hover:bg-gov-navy-50 transition-all"
        >
          Start Over
        </button>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Main Wizard component (modal + tab)
// ─────────────────────────────────────────────────────────────────────────────

interface CertificationWizardProps {
  /** Controls whether to render inline or as a floating modal */
  mode?: "inline" | "modal";
  /** When mode="modal": callback to close the modal */
  onClose?: () => void;
  /** Whether the modal is open (mode="modal" only) */
  isOpen?: boolean;
}

export default function CertificationWizard({
  mode = "inline",
  onClose,
  isOpen = true,
}: CertificationWizardProps) {
  const [step, setStep] = useState(0);
  const [category, setCategory] = useState<string | null>(null);
  const [origin, setOrigin] = useState<ManufacturingOrigin | null>(null);
  const [scheme, setScheme] = useState<CertScheme | null>(null);

  // Determine scheme when moving past step 2
  const handleStep2Next = useCallback(() => {
    if (category && origin) {
      setScheme(determineScheme(category, origin));
      setStep(2);
    }
  }, [category, origin]);

  const handleStep3Next = useCallback(() => setStep(3), []);

  const reset = useCallback(() => {
    setStep(0);
    setCategory(null);
    setOrigin(null);
    setScheme(null);
  }, []);

  // Close on Escape key (modal mode)
  useEffect(() => {
    if (mode !== "modal") return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose?.();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [mode, onClose]);

  if (mode === "modal" && !isOpen) return null;

  const selectedCategory = PRODUCT_CATEGORIES.find((c) => c.id === category) ?? null;

  const content = (
    <div
      className={`bg-white rounded-2xl shadow-gov-lg flex flex-col
        ${mode === "modal" ? "w-full max-w-2xl max-h-[90vh] overflow-hidden" : "w-full"}`}
    >
      {/* Modal / panel header */}
      <div className="flex items-center justify-between px-6 pt-6 pb-4 border-b border-gov-slate-100">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-gov-navy-800 to-gov-navy-600 flex items-center justify-center shadow-gov-sm">
            <ShieldCheck size={20} className="text-white" />
          </div>
          <div>
            <h2 className="text-base font-bold text-gov-navy-800">BIS Certification Wizard</h2>
            <p className="text-xs text-gov-slate-500">For MSMEs &amp; Startups</p>
          </div>
        </div>
        {mode === "modal" && onClose && (
          <button
            id="wizard-close"
            onClick={onClose}
            className="p-1.5 rounded-lg text-gov-slate-400 hover:bg-gov-slate-100 hover:text-gov-slate-700 transition-all"
            aria-label="Close wizard"
          >
            <X size={18} />
          </button>
        )}
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto px-6 py-5">
        <StepBar current={step} />

        {step === 0 && (
          <Step1
            selected={category}
            onSelect={setCategory}
            onNext={() => setStep(1)}
          />
        )}
        {step === 1 && (
          <Step2
            origin={origin}
            onSelect={setOrigin}
            onNext={handleStep2Next}
            onBack={() => setStep(0)}
          />
        )}
        {step === 2 && scheme && selectedCategory && origin && (
          <Step3
            scheme={scheme}
            category={selectedCategory}
            origin={origin}
            onNext={handleStep3Next}
            onBack={() => setStep(1)}
          />
        )}
        {step === 3 && scheme && (
          <Step4
            scheme={scheme}
            onBack={() => setStep(2)}
            onReset={reset}
          />
        )}
      </div>
    </div>
  );

  if (mode === "inline") return content;

  // Modal mode — portal-style overlay
  return (
    <div
      id="certification-wizard-overlay"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-gov-navy-900/60 backdrop-blur-sm animate-fade-in"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose?.();
      }}
    >
      {content}
    </div>
  );
}
