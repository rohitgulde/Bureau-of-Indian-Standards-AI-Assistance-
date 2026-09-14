"use client";

/**
 * HallmarkChecker.tsx
 * ────────────────────
 * Interactive Gold Hallmarking guide & HUID validator.
 *
 * Sections
 * ────────
 *  1. Visual Explainer — three hallmarking components (BIS Logo, Purity Mark, HUID)
 *  2. HUID Validator  — live regex check (^[A-Z0-9]{6}$) with visual feedback
 *  3. BIS Care App Tutorial — step-by-step illustrated guide for verifying jewellery
 */

import React, { useState, useCallback, useRef } from "react";
import {
  ShieldCheck,
  Gem,
  Hash,
  CheckCircle2,
  XCircle,
  Info,
  Smartphone,
  Download,
  ScanLine,
  Search,
  ExternalLink,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  Star,
  Sparkles,
  ArrowRight,
  Copy,
  Check,
} from "lucide-react";

// ─────────────────────────────────────────────────────────────────────────────
// Constants
// ─────────────────────────────────────────────────────────────────────────────

const HUID_REGEX = /^[A-Z0-9]{6}$/;

const PURITY_MARKS: { karat: string; purity: string; fineness: string; color: string; bg: string }[] = [
  { karat: "24K", purity: "99.9%", fineness: "999", color: "text-yellow-700", bg: "bg-yellow-50 border-yellow-300" },
  { karat: "23K", purity: "95.8%", fineness: "958", color: "text-yellow-700", bg: "bg-yellow-50 border-yellow-300" },
  { karat: "22K", purity: "91.6%", fineness: "916", color: "text-amber-700",  bg: "bg-amber-50  border-amber-300"  },
  { karat: "21K", purity: "87.5%", fineness: "875", color: "text-amber-700",  bg: "bg-amber-50  border-amber-300"  },
  { karat: "18K", purity: "75.0%", fineness: "750", color: "text-orange-700", bg: "bg-orange-50 border-orange-300" },
  { karat: "14K", purity: "58.5%", fineness: "585", color: "text-orange-700", bg: "bg-orange-50 border-orange-300" },
];

const APP_STEPS: {
  step: number;
  icon: React.ReactNode;
  title: string;
  description: string;
  tip?: string;
  badge?: string;
}[] = [
  {
    step: 1,
    icon: <Download size={20} />,
    title: "Download BIS Care App",
    description:
      "Install the official BIS Care app from Google Play Store or Apple App Store. It's free and available in English and Hindi.",
    tip: "Search 'BIS Care' — look for the BIS/GoI logo. Avoid unofficial clones.",
    badge: "Free",
  },
  {
    step: 2,
    icon: <Smartphone size={20} />,
    title: "Open & Select 'Verify HUID'",
    description:
      "Launch the app and tap 'Verify HUID' on the home screen. You can either scan the HUID directly from the jewellery or type it manually.",
    tip: "The app also verifies hallmarked articles via QR code in some cases.",
  },
  {
    step: 3,
    icon: <ScanLine size={20} />,
    title: "Scan or Enter the 6-digit HUID",
    description:
      "Hold your phone camera over the 6-character alphanumeric HUID engraved or laser-etched on the jewellery. Alternatively, enter it manually in the input field.",
    tip: "Ensure good lighting for scan accuracy. The HUID is always uppercase A–Z and 0–9.",
  },
  {
    step: 4,
    icon: <Search size={20} />,
    title: "Review Verification Result",
    description:
      "The app queries the BIS HUID database and shows: article type, metal purity, assaying & hallmarking centre details, date of hallmarking, and jeweller registration.",
    tip: "A green ✓ means the article is genuinely hallmarked. Red ✗ or 'Not Found' means the HUID is invalid — do not purchase.",
    badge: "Key step",
  },
  {
    step: 5,
    icon: <ShieldCheck size={20} />,
    title: "Verify Jeweller Registration",
    description:
      "Tap 'Jeweller Details' to see the registered business name, city, and licence status. Cross-check this with the physical shop name before buying.",
    tip: "You can also report suspicious listings directly from the app to BIS enforcement.",
  },
];

// ─────────────────────────────────────────────────────────────────────────────
// Sub-components
// ─────────────────────────────────────────────────────────────────────────────

/** Animated BIS Logo SVG — stylised shield with "BIS" text */
function BISLogoMark({ size = 56 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 56 56"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-label="BIS Hallmark Logo"
    >
      {/* Shield */}
      <path
        d="M28 4L6 14v14c0 12.7 9.3 24.6 22 27.4C41.7 52.6 50 40.7 50 28V14L28 4z"
        fill="url(#bisGrad)"
        stroke="#0f2d6e"
        strokeWidth="1.5"
      />
      {/* BIS text */}
      <text
        x="28"
        y="31"
        textAnchor="middle"
        fill="white"
        fontSize="12"
        fontWeight="bold"
        fontFamily="ui-monospace, monospace"
        letterSpacing="1"
      >
        BIS
      </text>
      {/* Star decoration */}
      <path
        d="M28 8l1.5 4.5H34l-3.7 2.7 1.4 4.3L28 17l-3.7 2.5 1.4-4.3L22 12.5h4.5z"
        fill="#e8521a"
        opacity="0.9"
      />
      <defs>
        <linearGradient id="bisGrad" x1="6" y1="4" x2="50" y2="56" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#1e54b0" />
          <stop offset="100%" stopColor="#0f2d6e" />
        </linearGradient>
      </defs>
    </svg>
  );
}

/** Gold purity stamp component */
function PurityStamp({ karat = "22K916" }: { karat?: string }) {
  return (
    <div className="relative inline-flex items-center justify-center">
      <div
        className="w-16 h-16 rounded-full border-4 border-amber-400 bg-gradient-to-br
          from-yellow-300 via-amber-300 to-yellow-400 shadow-lg flex flex-col items-center justify-center
          ring-2 ring-amber-200 ring-offset-1"
      >
        <span className="text-amber-900 font-black text-sm leading-none tracking-tight">
          {karat.slice(0, 3)}
        </span>
        <span className="text-amber-800 font-bold text-[10px] leading-none mt-0.5">
          {karat.slice(3)}
        </span>
      </div>
      {/* Glow effect */}
      <div className="absolute inset-0 rounded-full bg-amber-300/30 blur-md -z-10" />
    </div>
  );
}

/** 6-digit HUID stamp component */
function HUIDStamp({ value = "AB1C2D", valid }: { value?: string; valid?: boolean }) {
  return (
    <div
      className={`relative inline-flex items-center gap-1 px-3 py-2 rounded-lg border-2 font-mono
        tracking-[0.3em] text-lg font-black shadow-inner transition-all duration-300
        ${valid === undefined
          ? "border-gov-slate-300 bg-gov-slate-50 text-gov-slate-700"
          : valid
          ? "border-emerald-400 bg-emerald-50 text-emerald-800 shadow-emerald-100"
          : "border-red-400 bg-red-50 text-red-800 shadow-red-100"
        }`}
    >
      {value.split("").map((ch, i) => (
        <span
          key={i}
          className={`transition-all duration-200 ${
            valid === true
              ? "text-emerald-700"
              : valid === false
              ? "text-red-600"
              : "text-gov-slate-700"
          }`}
        >
          {ch}
        </span>
      ))}
    </div>
  );
}

/** Individual hallmark component explainer card */
function HallmarkComponentCard({
  icon,
  title,
  subtitle,
  description,
  visual,
  color,
  borderColor,
  bgColor,
  facts,
}: {
  icon: React.ReactNode;
  title: string;
  subtitle: string;
  description: string;
  visual: React.ReactNode;
  color: string;
  borderColor: string;
  bgColor: string;
  facts: string[];
}) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      className={`relative rounded-2xl border-2 ${borderColor} ${bgColor} p-5 flex flex-col gap-4
        transition-all duration-200 hover:shadow-gov-md`}
    >
      {/* Visual */}
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className={`${color} p-2 rounded-xl bg-white/60`}>{icon}</span>
          <div>
            <h3 className={`font-bold text-sm ${color}`}>{title}</h3>
            <p className="text-xs text-gov-slate-500">{subtitle}</p>
          </div>
        </div>
        <div className="flex-shrink-0">{visual}</div>
      </div>

      {/* Description */}
      <p className="text-sm text-gov-slate-600 leading-relaxed">{description}</p>

      {/* Expandable facts */}
      <button
        type="button"
        onClick={() => setExpanded((e) => !e)}
        className={`flex items-center gap-1 text-xs font-semibold ${color} hover:opacity-80 transition-opacity w-fit`}
      >
        {expanded ? "Hide details" : "Show details"}
        {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
      </button>

      {expanded && (
        <ul className="space-y-1.5 animate-fade-in">
          {facts.map((f, i) => (
            <li key={i} className="flex items-start gap-2 text-xs text-gov-slate-600">
              <CheckCircle2 size={12} className={`${color} flex-shrink-0 mt-0.5`} />
              {f}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// HUID Validator section
// ─────────────────────────────────────────────────────────────────────────────

function HUIDValidator() {
  const [raw, setRaw] = useState("");
  const [copied, setCopied] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const value = raw.toUpperCase().replace(/[^A-Z0-9]/g, "").slice(0, 6);
  const hasInput = value.length > 0;
  const isComplete = value.length === 6;
  const isValid = isComplete && HUID_REGEX.test(value);
  const isInvalid = isComplete && !HUID_REGEX.test(value);

  const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setRaw(e.target.value);
  }, []);

  const handleClear = () => {
    setRaw("");
    inputRef.current?.focus();
  };

  const handleCopy = async () => {
    if (!value) return;
    try { await navigator.clipboard.writeText(value); }
    catch {
      const el = document.createElement("input");
      el.value = value;
      document.body.appendChild(el);
      el.select();
      document.execCommand("copy");
      document.body.removeChild(el);
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Character-by-character display
  const slots = Array.from({ length: 6 }, (_, i) => value[i] ?? "");

  return (
    <div className="space-y-5">
      {/* Input */}
      <div>
        <label
          htmlFor="huid-input"
          className="block text-xs font-semibold text-gov-slate-500 uppercase tracking-wider mb-2"
        >
          Enter HUID (6 alphanumeric characters)
        </label>
        <div className="relative flex items-center gap-2">
          <div className="relative flex-1">
            <Hash
              size={16}
              className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gov-slate-400 pointer-events-none"
            />
            <input
              ref={inputRef}
              id="huid-input"
              type="text"
              value={raw}
              onChange={handleChange}
              maxLength={8}
              spellCheck={false}
              autoComplete="off"
              placeholder="e.g. AB1C2D"
              aria-describedby="huid-status"
              className={`w-full pl-10 pr-10 py-3 rounded-xl border-2 font-mono text-lg tracking-widest font-bold
                uppercase transition-all duration-200 bg-white focus:outline-none focus:ring-2
                placeholder:text-gov-slate-300 placeholder:font-normal placeholder:tracking-normal
                ${isValid
                  ? "border-emerald-400 text-emerald-800 focus:ring-emerald-400/30"
                  : isInvalid
                  ? "border-red-400 text-red-700 focus:ring-red-400/30"
                  : "border-gov-slate-200 text-gov-navy-800 focus:ring-gov-navy-800/20 focus:border-gov-navy-400"
                }`}
            />
            {hasInput && (
              <button
                type="button"
                onClick={handleClear}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gov-slate-400 hover:text-gov-slate-600 transition-colors"
                aria-label="Clear input"
              >
                <XCircle size={16} />
              </button>
            )}
          </div>
          <button
            type="button"
            onClick={handleCopy}
            disabled={!value}
            className="flex items-center gap-1.5 px-3 py-3 rounded-xl border border-gov-slate-200 text-xs font-semibold
              text-gov-slate-600 bg-white hover:bg-gov-slate-50 disabled:opacity-40
              disabled:cursor-not-allowed transition-all"
            aria-label="Copy HUID"
          >
            {copied ? <Check size={14} className="text-emerald-600" /> : <Copy size={14} />}
          </button>
        </div>
      </div>

      {/* Slot display */}
      <div className="flex items-center gap-2" aria-hidden="true">
        {slots.map((ch, i) => (
          <div
            key={i}
            className={`flex-1 h-12 rounded-xl border-2 flex items-center justify-center font-mono text-xl font-black
              transition-all duration-200
              ${ch
                ? isValid
                  ? "border-emerald-400 bg-emerald-50 text-emerald-800 scale-[1.04] shadow-md"
                  : isInvalid
                  ? "border-red-400 bg-red-50 text-red-700 scale-[1.04]"
                  : "border-gov-navy-400 bg-gov-navy-50 text-gov-navy-800 scale-[1.02]"
                : "border-gov-slate-200 bg-gov-slate-50 text-gov-slate-300"
              }`}
          >
            {ch || <span className="text-gov-slate-200 text-sm">•</span>}
          </div>
        ))}
      </div>

      {/* Progress bar */}
      <div>
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-[10px] font-semibold text-gov-slate-500 uppercase tracking-wide">
            Characters entered
          </span>
          <span className="text-[10px] font-bold text-gov-slate-600">{value.length} / 6</span>
        </div>
        <div className="w-full h-1.5 rounded-full bg-gov-slate-200 overflow-hidden">
          <div
            className={`h-1.5 rounded-full transition-all duration-300
              ${isValid ? "bg-emerald-500" : isInvalid ? "bg-red-500" : "bg-gov-navy-600"}`}
            style={{ width: `${(value.length / 6) * 100}%` }}
          />
        </div>
      </div>

      {/* Status message */}
      <div
        id="huid-status"
        role="status"
        aria-live="polite"
        className={`flex items-start gap-3 rounded-xl p-4 border transition-all duration-300
          ${!hasInput
            ? "border-gov-slate-200 bg-gov-slate-50"
            : isValid
            ? "border-emerald-300 bg-emerald-50"
            : isInvalid
            ? "border-red-300 bg-red-50"
            : "border-gov-navy-200 bg-gov-navy-50"
          }`}
      >
        {!hasInput ? (
          <>
            <Info size={16} className="text-gov-slate-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-semibold text-gov-slate-600">Ready to validate</p>
              <p className="text-xs text-gov-slate-400 mt-0.5">
                Enter exactly 6 uppercase letters and/or digits (A–Z, 0–9). Lowercase is auto-converted.
              </p>
            </div>
          </>
        ) : isValid ? (
          <>
            <CheckCircle2 size={16} className="text-emerald-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-bold text-emerald-800">
                ✓ Valid HUID format — <span className="font-mono">{value}</span>
              </p>
              <p className="text-xs text-emerald-700 mt-0.5">
                The format matches <code className="bg-emerald-100 px-1 rounded font-mono">^[A-Z0-9]&#123;6&#125;$</code>.
                Use the BIS Care App to verify this HUID against the national registry.
              </p>
            </div>
          </>
        ) : isInvalid ? (
          <>
            <XCircle size={16} className="text-red-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-bold text-red-800">✗ Invalid HUID</p>
              <p className="text-xs text-red-700 mt-0.5">
                A valid HUID must be exactly 6 characters — uppercase letters (A–Z) and digits (0–9) only.
                Special characters or spaces are not allowed.
              </p>
            </div>
          </>
        ) : (
          <>
            <Info size={16} className="text-gov-navy-700 flex-shrink-0 mt-0.5" />
            <p className="text-sm text-gov-navy-700 font-medium">
              {6 - value.length} more character{6 - value.length !== 1 ? "s" : ""} needed…
            </p>
          </>
        )}
      </div>

      {/* Verify on BIS portal CTA */}
      {isValid && (
        <a
          id="verify-on-bis"
          href={`https://www.bis.gov.in/index.php/hallmarking/verify-hallmark/?huid=${value}`}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center justify-between gap-3 rounded-xl bg-gradient-to-r
            from-gov-navy-800 to-gov-navy-600 px-5 py-3.5 shadow-gov-md hover:shadow-gov-lg
            transition-all animate-fade-in group"
        >
          <div>
            <p className="text-white font-bold text-sm">Verify on BIS Portal</p>
            <p className="text-white/70 text-xs mt-0.5">
              Check HUID <span className="font-mono font-bold text-white">{value}</span> in the official BIS database
            </p>
          </div>
          <ExternalLink size={18} className="text-white/70 group-hover:text-white transition-colors flex-shrink-0" />
        </a>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// BIS Care App tutorial step card
// ─────────────────────────────────────────────────────────────────────────────

function AppStep({
  step,
  icon,
  title,
  description,
  tip,
  badge,
  isLast,
}: (typeof APP_STEPS)[number] & { isLast: boolean }) {
  return (
    <div className="flex gap-4">
      {/* Step connector */}
      <div className="flex flex-col items-center flex-shrink-0">
        <div
          className="w-10 h-10 rounded-xl bg-gradient-to-br from-gov-navy-800 to-gov-navy-600
            flex items-center justify-center text-white shadow-gov-sm"
        >
          {icon}
        </div>
        {!isLast && (
          <div className="w-0.5 flex-1 mt-2 bg-gradient-to-b from-gov-navy-200 to-transparent min-h-[28px]" />
        )}
      </div>

      {/* Content */}
      <div className={`flex-1 pb-6 ${isLast ? "" : ""}`}>
        <div className="flex items-center gap-2 mb-1">
          <span className="text-[10px] font-bold text-gov-navy-600 uppercase tracking-widest">
            Step {step}
          </span>
          {badge && (
            <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-gov-orange-600/10 text-gov-orange-600 border border-gov-orange-200">
              {badge}
            </span>
          )}
        </div>
        <h4 className="text-sm font-bold text-gov-navy-800 mb-1">{title}</h4>
        <p className="text-sm text-gov-slate-600 leading-relaxed">{description}</p>
        {tip && (
          <div className="flex items-start gap-2 mt-2.5 rounded-lg bg-amber-50 border border-amber-200 px-3 py-2">
            <AlertCircle size={12} className="text-amber-600 flex-shrink-0 mt-0.5" />
            <p className="text-xs text-amber-800 leading-relaxed">{tip}</p>
          </div>
        )}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Main HallmarkChecker component
// ─────────────────────────────────────────────────────────────────────────────

type ActiveSection = "explainer" | "validator" | "tutorial";

interface HallmarkCheckerProps {
  /** Optional default open section */
  defaultSection?: ActiveSection;
}

export default function HallmarkChecker({
  defaultSection = "explainer",
}: HallmarkCheckerProps) {
  const [activeSection, setActiveSection] = useState<ActiveSection>(defaultSection);

  const TAB_CONFIG: { id: ActiveSection; label: string; icon: React.ReactNode }[] = [
    { id: "explainer", label: "Hallmark Guide",   icon: <Gem size={14} />          },
    { id: "validator", label: "HUID Validator",   icon: <Hash size={14} />         },
    { id: "tutorial",  label: "BIS Care App",     icon: <Smartphone size={14} />   },
  ];

  return (
    <div className="space-y-5">
      {/* ── Header ──────────────────────────────────────────────────────── */}
      <div className="flex items-center gap-3">
        <div
          className="w-11 h-11 rounded-xl flex items-center justify-center shadow-gov-sm flex-shrink-0
            bg-gradient-to-br from-amber-500 to-yellow-400"
        >
          <Sparkles size={22} className="text-white" />
        </div>
        <div>
          <h2 className="text-base font-bold text-gov-navy-800">Gold Hallmarking Checker</h2>
          <p className="text-xs text-gov-slate-500">
            BIS Hallmarking guide · HUID validator · BIS Care App tutorial
          </p>
        </div>
      </div>

      {/* ── Tab bar ─────────────────────────────────────────────────────── */}
      <div className="flex rounded-xl border border-gov-slate-200 p-1 bg-gov-slate-50 gap-1">
        {TAB_CONFIG.map(({ id, label, icon }) => (
          <button
            key={id}
            id={`hallmark-tab-${id}`}
            onClick={() => setActiveSection(id)}
            className={`flex-1 flex items-center justify-center gap-1.5 py-2.5 rounded-lg text-xs font-semibold
              transition-all duration-200
              ${activeSection === id
                ? "bg-white shadow-gov-sm text-gov-navy-800"
                : "text-gov-slate-500 hover:text-gov-navy-700"
              }`}
          >
            {icon}
            <span className="hidden sm:inline">{label}</span>
          </button>
        ))}
      </div>

      {/* ── Section: Hallmark Visual Explainer ──────────────────────────── */}
      {activeSection === "explainer" && (
        <div className="space-y-4 animate-fade-in">
          <div className="flex items-start gap-2 rounded-xl bg-amber-50 border border-amber-200 px-4 py-3">
            <Info size={14} className="text-amber-600 flex-shrink-0 mt-0.5" />
            <p className="text-xs text-amber-800 leading-relaxed">
              Since 1 September 2021, Hallmarking is <strong>mandatory</strong> in India for gold jewellery sold by
              registered jewellers. Every hallmarked piece must bear all three marks below.
            </p>
          </div>

          {/* Three hallmark components */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {/* 1. BIS Logo */}
            <HallmarkComponentCard
              icon={<ShieldCheck size={18} />}
              title="BIS Logo"
              subtitle="Bureau of Indian Standards"
              description="The official BIS shield mark certifies that the jewellery has been tested and hallmarked at a BIS-recognised Assaying & Hallmarking Centre (AHC)."
              visual={<BISLogoMark size={52} />}
              color="text-gov-navy-800"
              borderColor="border-gov-navy-200"
              bgColor="bg-gov-navy-50"
              facts={[
                "Indicates BIS-supervised quality testing",
                "Only AHCs authorised by BIS can apply this mark",
                "The same logo appears on product packaging, certificates, and the BIS Care App",
                "Absence of this mark means the jewellery is NOT officially hallmarked",
              ]}
            />

            {/* 2. Purity Mark */}
            <HallmarkComponentCard
              icon={<Star size={18} />}
              title="Purity / Fineness Mark"
              subtitle="Karat & fineness grade"
              description="Indicates the actual gold content in the alloy. Written as karat (22K) followed by the fineness number (916 = 91.6% gold). Only 6 grades are legally permitted."
              visual={<PurityStamp karat="22K916" />}
              color="text-amber-700"
              borderColor="border-amber-300"
              bgColor="bg-amber-50"
              facts={[
                "Six permitted grades: 24K/999, 23K/958, 22K/916, 21K/875, 18K/750, 14K/585",
                "22K916 is the most common for jewellery in India",
                "The number (e.g. 916) represents parts per thousand of pure gold",
                "Misrepresenting purity is a punishable offence under BIS Act 2016",
              ]}
            />

            {/* 3. HUID */}
            <HallmarkComponentCard
              icon={<Hash size={18} />}
              title="HUID"
              subtitle="Hallmark Unique ID (6 chars)"
              description="A unique 6-character alphanumeric code laser-engraved on every hallmarked article since July 2021. Links the piece to a secure BIS government registry."
              visual={<HUIDStamp value="AB1C2D" />}
              color="text-violet-700"
              borderColor="border-violet-200"
              bgColor="bg-violet-50"
              facts={[
                "Format: exactly 6 characters — uppercase A–Z and digits 0–9",
                "Each HUID is registered in the national BIS HUID portal",
                "Consumers can verify authenticity via the free BIS Care App",
                "Cannot be duplicated — each code maps to exactly one physical article",
                "Old 4-mark system was replaced by the 3-mark (BIS + Purity + HUID) system in 2021",
              ]}
            />
          </div>

          {/* Purity reference table */}
          <div className="rounded-2xl border border-gov-slate-200 bg-white overflow-hidden shadow-gov-sm">
            <div className="px-4 py-3 bg-gov-slate-50 border-b border-gov-slate-200 flex items-center gap-2">
              <Gem size={14} className="text-amber-600" />
              <h3 className="text-xs font-bold text-gov-slate-700 uppercase tracking-wide">
                Permitted Gold Purity Grades (BIS, India)
              </h3>
            </div>
            <div className="divide-y divide-gov-slate-100">
              {PURITY_MARKS.map((p) => (
                <div
                  key={p.karat}
                  className="flex items-center justify-between px-4 py-2.5 hover:bg-gov-slate-50 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <span
                      className={`text-xs font-black font-mono px-2.5 py-1 rounded-lg border ${p.bg} ${p.color}`}
                    >
                      {p.karat}
                    </span>
                    <span className="text-xs text-gov-slate-600 font-medium">
                      {p.purity} pure gold
                    </span>
                  </div>
                  <span className="font-mono text-xs font-bold text-gov-slate-500">
                    {p.fineness}‰
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* CTA to validator */}
          <button
            id="go-to-validator"
            onClick={() => setActiveSection("validator")}
            className="w-full flex items-center justify-between px-5 py-3.5 rounded-xl
              bg-gradient-to-r from-violet-700 to-violet-500 text-white shadow-gov-sm
              hover:shadow-gov-md transition-all group"
          >
            <div className="flex items-center gap-2">
              <Hash size={16} />
              <span className="text-sm font-bold">Validate a HUID now</span>
            </div>
            <ArrowRight size={16} className="group-hover:translate-x-1 transition-transform" />
          </button>
        </div>
      )}

      {/* ── Section: HUID Validator ──────────────────────────────────────── */}
      {activeSection === "validator" && (
        <div className="space-y-4 animate-fade-in">
          <div className="rounded-2xl border border-violet-200 bg-violet-50 p-5">
            <div className="flex items-center gap-2 mb-4">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-violet-700 to-violet-500 flex items-center justify-center">
                <Hash size={18} className="text-white" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-violet-800">HUID Format Validator</h3>
                <p className="text-xs text-violet-600">
                  Instant client-side check — no network request needed
                </p>
              </div>
            </div>
            <HUIDValidator />
          </div>

          {/* Where to find HUID */}
          <div className="rounded-2xl border border-gov-slate-200 bg-white p-5 space-y-3">
            <h3 className="text-sm font-bold text-gov-navy-800 flex items-center gap-2">
              <Search size={14} className="text-gov-navy-700" />
              Where to find the HUID on your jewellery
            </h3>
            <ul className="space-y-2">
              {[
                "Laser-etched on the surface of the gold ornament — usually on the clasp, inner band, or flat back",
                "Printed on the Hallmark Certificate issued by the AHC at the time of hallmarking",
                "Shown in the receipt / bill from a BIS-registered jeweller",
                "Available on the individual article packaging for branded jewellery",
              ].map((item, i) => (
                <li key={i} className="flex items-start gap-2.5 text-xs text-gov-slate-600">
                  <div className="w-4 h-4 rounded-full bg-gov-navy-100 flex items-center justify-center flex-shrink-0 mt-0.5">
                    <span className="text-[9px] font-bold text-gov-navy-700">{i + 1}</span>
                  </div>
                  {item}
                </li>
              ))}
            </ul>
          </div>

          {/* Format spec box */}
          <div className="rounded-xl border border-gov-slate-200 bg-gov-slate-50 px-4 py-3 flex items-start gap-3">
            <Info size={14} className="text-gov-slate-500 flex-shrink-0 mt-0.5" />
            <div className="text-xs text-gov-slate-600 space-y-1">
              <p>
                <strong className="text-gov-slate-800">Regex pattern:</strong>{" "}
                <code className="bg-white border border-gov-slate-200 px-1.5 py-0.5 rounded font-mono text-[11px] text-violet-700">
                  ^[A-Z0-9]&#123;6&#125;$
                </code>
              </p>
              <p>Exactly 6 characters · Only uppercase A–Z and digits 0–9 · No spaces or special chars</p>
            </div>
          </div>

          <button
            id="go-to-tutorial"
            onClick={() => setActiveSection("tutorial")}
            className="w-full flex items-center justify-between px-5 py-3.5 rounded-xl
              bg-gradient-to-r from-gov-navy-800 to-gov-navy-600 text-white shadow-gov-sm
              hover:shadow-gov-md transition-all group"
          >
            <div className="flex items-center gap-2">
              <Smartphone size={16} />
              <span className="text-sm font-bold">Learn to verify via BIS Care App</span>
            </div>
            <ArrowRight size={16} className="group-hover:translate-x-1 transition-transform" />
          </button>
        </div>
      )}

      {/* ── Section: BIS Care App Tutorial ─────────────────────────────── */}
      {activeSection === "tutorial" && (
        <div className="space-y-4 animate-fade-in">
          {/* App download banner */}
          <div className="rounded-2xl bg-gradient-to-br from-gov-navy-900 to-gov-navy-700 p-5 shadow-gov-lg">
            <div className="flex items-start gap-4">
              <div className="w-14 h-14 rounded-2xl bg-white/15 flex items-center justify-center flex-shrink-0">
                <Smartphone size={28} className="text-white" />
              </div>
              <div className="flex-1">
                <p className="text-white font-bold text-base">BIS Care App</p>
                <p className="text-white/70 text-xs mt-0.5 mb-3 leading-relaxed">
                  Official free app by the Bureau of Indian Standards. Verify gold, silver &amp; bronze
                  hallmarks, register complaints, and check certified products.
                </p>
                <div className="flex flex-wrap gap-2">
                  <a
                    id="bis-care-play-store"
                    href="https://play.google.com/store/apps/details?id=com.bis.care"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 bg-white text-gov-navy-800 px-4 py-2 rounded-xl text-xs font-bold
                      hover:bg-gov-slate-100 transition-all shadow-gov-sm"
                  >
                    <Download size={12} /> Google Play
                  </a>
                  <a
                    id="bis-care-app-store"
                    href="https://apps.apple.com/in/app/bis-care/id1497496799"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 bg-white/10 border border-white/20 text-white px-4 py-2 rounded-xl text-xs font-bold
                      hover:bg-white/20 transition-all"
                  >
                    <Download size={12} /> App Store
                  </a>
                </div>
              </div>
            </div>
          </div>

          {/* Step-by-step tutorial */}
          <div className="rounded-2xl border border-gov-slate-200 bg-white p-5">
            <h3 className="text-sm font-bold text-gov-navy-800 mb-5 flex items-center gap-2">
              <ScanLine size={14} className="text-gov-navy-700" />
              Step-by-step verification guide
            </h3>
            <div>
              {APP_STEPS.map((step, i) => (
                <AppStep
                  key={step.step}
                  {...step}
                  isLast={i === APP_STEPS.length - 1}
                />
              ))}
            </div>
          </div>

          {/* Quick safety tips */}
          <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4 space-y-3">
            <h3 className="text-xs font-bold text-emerald-800 uppercase tracking-wide flex items-center gap-1.5">
              <ShieldCheck size={13} /> Consumer Safety Checklist
            </h3>
            <ul className="space-y-2">
              {[
                "Always insist on a hallmarked piece before purchasing gold jewellery",
                "Verify the HUID on the BIS Care App before making payment",
                "Ensure the jeweller is BIS-registered — ask for their BIS registration number",
                "The making charges, wastage, and metal weight must be itemised in the bill",
                "Report fake hallmarking at the BIS Helpline: 1800-11-4060 (toll-free)",
              ].map((tip, i) => (
                <li key={i} className="flex items-start gap-2 text-xs text-emerald-800">
                  <CheckCircle2 size={12} className="text-emerald-600 flex-shrink-0 mt-0.5" />
                  {tip}
                </li>
              ))}
            </ul>
          </div>

          {/* BIS Helpline */}
          <div className="rounded-xl border border-gov-orange-200 bg-gov-orange-50/60 p-4 flex items-center gap-4">
            <div className="w-10 h-10 rounded-xl bg-gov-orange-600 flex items-center justify-center flex-shrink-0">
              <AlertCircle size={18} className="text-white" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-bold text-gov-orange-800">BIS Consumer Helpline</p>
              <p className="text-xs text-gov-orange-700 mt-0.5">
                Report fake hallmarking or substandard jewellery
              </p>
            </div>
            <a
              id="bis-helpline"
              href="tel:18001114060"
              className="flex-shrink-0 text-sm font-bold text-gov-orange-800 underline underline-offset-2
                hover:text-gov-orange-900 transition-colors"
            >
              1800-11-4060
            </a>
          </div>

          {/* External links */}
          <div className="flex flex-wrap gap-2">
            {[
              { label: "BIS Hallmarking Portal", href: "https://www.bis.gov.in/index.php/hallmarking/" },
              { label: "Verify HUID Online", href: "https://www.bis.gov.in/index.php/hallmarking/verify-hallmark/" },
              { label: "Find AHC Near You", href: "https://www.bis.gov.in/index.php/hallmarking/ahc-locator/" },
            ].map((link) => (
              <a
                key={link.label}
                id={`ext-${link.label.toLowerCase().replace(/\s+/g, "-")}`}
                href={link.href}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-full
                  border border-gov-navy-200 bg-gov-navy-50 text-gov-navy-700
                  hover:bg-gov-navy-100 hover:border-gov-navy-300 transition-all"
              >
                {link.label} <ExternalLink size={10} />
              </a>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
