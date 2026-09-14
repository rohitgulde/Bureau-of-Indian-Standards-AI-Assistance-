"use client";

/**
 * LabFinder.tsx
 * ──────────────
 * Interactive laboratory search for BIS-recognised / NABL-accredited labs.
 *
 * Features
 * ────────
 *  • State → City → Material/Product cascading dropdown filters
 *  • Text search (lab name / service keyword)
 *  • Responsive card grid — address, phone, email, services, accreditation badge
 *  • "Copy Contact Details" one-click clipboard action per card
 *  • Chat quick-action button prop: onFindForStandard(standardCode) injects a
 *    "Find labs for this standard" query pre-filled with the IS standard code
 *  • Empty / loading / error states with helpful messaging
 *  • Fully self-contained — works inline or as a panel/modal
 */

import React, {
  useState,
  useMemo,
  useCallback,
  useEffect,
  useRef,
} from "react";
import {
  Search,
  MapPin,
  Phone,
  Mail,
  CheckCircle2,
  Loader2,
  Copy,
  Check,
  FlaskConical,
  ChevronDown,
  X,
  SlidersHorizontal,
  Microscope,
  ExternalLink,
  AlertCircle,
  FlaskRound,
} from "lucide-react";

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

export interface LabRecord {
  id: string;
  name: string;
  address: string;
  city: string;
  state: string;
  pincode: string;
  phone: string;
  email?: string;
  services: string[];       // product categories / IS standards tested
  accredited: boolean;      // NABL / BIS recognised
  bisCode?: string;         // BIS lab recognition number
  website?: string;
  coordinates?: { lat: number; lng: number };
}

// ─────────────────────────────────────────────────────────────────────────────
// Static reference data — exhaustive list used for dropdowns and demo cards
// (Replace with API calls in production)
// ─────────────────────────────────────────────────────────────────────────────

const STATES: string[] = [
  "All States",
  "Andhra Pradesh", "Bihar", "Delhi", "Gujarat", "Haryana",
  "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra",
  "Punjab", "Rajasthan", "Tamil Nadu", "Telangana",
  "Uttar Pradesh", "West Bengal",
];

const CITIES_BY_STATE: Record<string, string[]> = {
  "All States": ["All Cities"],
  "Delhi":            ["All Cities", "New Delhi", "Dwarka", "Rohini"],
  "Maharashtra":      ["All Cities", "Mumbai", "Pune", "Nagpur", "Nashik"],
  "Tamil Nadu":       ["All Cities", "Chennai", "Coimbatore", "Madurai"],
  "Karnataka":        ["All Cities", "Bengaluru", "Mysuru", "Hubballi"],
  "Gujarat":          ["All Cities", "Ahmedabad", "Surat", "Vadodara"],
  "Telangana":        ["All Cities", "Hyderabad", "Warangal"],
  "Uttar Pradesh":    ["All Cities", "Lucknow", "Kanpur", "Agra", "Noida"],
  "West Bengal":      ["All Cities", "Kolkata", "Asansol"],
  "Rajasthan":        ["All Cities", "Jaipur", "Jodhpur", "Udaipur"],
  "Punjab":           ["All Cities", "Ludhiana", "Amritsar", "Jalandhar"],
  "Haryana":          ["All Cities", "Gurgaon", "Faridabad", "Panipat"],
  "Kerala":           ["All Cities", "Thiruvananthapuram", "Kochi", "Kozhikode"],
  "Madhya Pradesh":   ["All Cities", "Bhopal", "Indore", "Jabalpur"],
  "Andhra Pradesh":   ["All Cities", "Visakhapatnam", "Vijayawada"],
  "Bihar":            ["All Cities", "Patna", "Gaya"],
};

const MATERIALS: string[] = [
  "All Products",
  "Steel & Metals", "Cement", "Electronics & IT", "Electrical Equipment",
  "Food & Beverages", "Chemicals", "Textiles", "Automotive", "Medical Devices",
  "Plastics & Rubber", "Glass & Ceramics", "Paper & Packaging", "Paints & Coatings",
];

// Demo lab data — representative BIS/NABL accredited labs
const DEMO_LABS: LabRecord[] = [
  {
    id: "1",
    name: "National Test House (NTH) — Mumbai",
    address: "Sion Trombay Road, Chunabhatti",
    city: "Mumbai",
    state: "Maharashtra",
    pincode: "400022",
    phone: "+91-22-2557-7340",
    email: "nth.mumbai@gov.in",
    services: ["Steel & Metals", "Cement", "Chemicals", "Plastics & Rubber", "Electrical Equipment"],
    accredited: true,
    bisCode: "BIS/NTH/MH/001",
    website: "https://nth.gov.in",
  },
  {
    id: "2",
    name: "ERTL (West) — Mumbai",
    address: "Plot No. C-56, G Block, BKC",
    city: "Mumbai",
    state: "Maharashtra",
    pincode: "400051",
    phone: "+91-22-2659-0220",
    email: "ertlwest@deity.gov.in",
    services: ["Electronics & IT", "Electrical Equipment"],
    accredited: true,
    bisCode: "BIS/ERTL/MH/002",
    website: "https://ertlwest.gov.in",
  },
  {
    id: "3",
    name: "STQC Directorate — New Delhi",
    address: "Electronics Niketan, 6 CGO Complex, Lodhi Road",
    city: "New Delhi",
    state: "Delhi",
    pincode: "110003",
    phone: "+91-11-2436-3072",
    email: "stqc@meity.gov.in",
    services: ["Electronics & IT", "Electrical Equipment", "Medical Devices"],
    accredited: true,
    bisCode: "BIS/STQC/DL/003",
    website: "https://stqc.gov.in",
  },
  {
    id: "4",
    name: "National Test House (NTH) — Kolkata",
    address: "Block GN, Sector 5, Salt Lake",
    city: "Kolkata",
    state: "West Bengal",
    pincode: "700091",
    phone: "+91-33-2357-0005",
    email: "nth.kolkata@gov.in",
    services: ["Steel & Metals", "Cement", "Textiles", "Paper & Packaging"],
    accredited: true,
    bisCode: "BIS/NTH/WB/004",
    website: "https://nth.gov.in",
  },
  {
    id: "5",
    name: "CIPET — Chennai",
    address: "T.V.K. Industrial Estate, Guindy",
    city: "Chennai",
    state: "Tamil Nadu",
    pincode: "600032",
    phone: "+91-44-2249-6900",
    email: "cipet.hq@cipet.gov.in",
    services: ["Plastics & Rubber", "Chemicals", "Automotive"],
    accredited: true,
    bisCode: "BIS/CIPET/TN/005",
    website: "https://cipet.gov.in",
  },
  {
    id: "6",
    name: "CFTRI — Mysuru",
    address: "Cheluvamba Mansion, Mysuru",
    city: "Mysuru",
    state: "Karnataka",
    pincode: "570020",
    phone: "+91-821-251-7760",
    email: "contactcftri@cftri.res.in",
    services: ["Food & Beverages", "Chemicals"],
    accredited: true,
    bisCode: "BIS/CFTRI/KA/006",
    website: "https://cftri.res.in",
  },
  {
    id: "7",
    name: "NABL Accredited Textile Lab — Ahmedabad",
    address: "Ashram Road, Near Gujarat Vidyapith",
    city: "Ahmedabad",
    state: "Gujarat",
    pincode: "380014",
    phone: "+91-79-2754-1881",
    email: "textilelab.ahmedabad@nabl.in",
    services: ["Textiles", "Chemicals", "Paints & Coatings"],
    accredited: true,
  },
  {
    id: "8",
    name: "ERTL (South) — Bengaluru",
    address: "No. 4, 14th Main, 17th Cross, Sadashivanagar",
    city: "Bengaluru",
    state: "Karnataka",
    pincode: "560080",
    phone: "+91-80-2361-3941",
    email: "ertlsouth@meity.gov.in",
    services: ["Electronics & IT", "Electrical Equipment"],
    accredited: true,
    bisCode: "BIS/ERTL/KA/008",
  },
  {
    id: "9",
    name: "NCC Ltd. Testing Lab — Hyderabad",
    address: "Fortune Towers, Banjara Hills",
    city: "Hyderabad",
    state: "Telangana",
    pincode: "500034",
    phone: "+91-40-4007-7500",
    services: ["Steel & Metals", "Cement", "Paints & Coatings"],
    accredited: false,
  },
  {
    id: "10",
    name: "IMMT (CSIR) — Bhubaneswar",
    address: "Acharya Vihar",
    city: "Kolkata",
    state: "West Bengal",
    pincode: "700001",
    phone: "+91-674-2379-008",
    email: "immt@immt.res.in",
    services: ["Steel & Metals", "Chemicals", "Cement"],
    accredited: true,
    website: "https://immt.res.in",
  },
  {
    id: "11",
    name: "RDSO Testing Lab — Lucknow",
    address: "Manak Nagar",
    city: "Lucknow",
    state: "Uttar Pradesh",
    pincode: "226011",
    phone: "+91-522-245-8100",
    email: "rdso@indianrailways.gov.in",
    services: ["Steel & Metals", "Electrical Equipment", "Automotive"],
    accredited: true,
    bisCode: "BIS/RDSO/UP/011",
  },
  {
    id: "12",
    name: "SERC Testing Centre — Chennai",
    address: "CSIR Road, Taramani",
    city: "Chennai",
    state: "Tamil Nadu",
    pincode: "600113",
    phone: "+91-44-2254-2500",
    email: "serc@sercmadras.res.in",
    services: ["Cement", "Steel & Metals", "Glass & Ceramics"],
    accredited: true,
  },
];

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000";

// ─────────────────────────────────────────────────────────────────────────────
// Helper: fetch labs from API (falls back to demo data)
// ─────────────────────────────────────────────────────────────────────────────

async function fetchLabs(params: {
  state?: string;
  city?: string;
  material?: string;
  q?: string;
}): Promise<LabRecord[]> {
  try {
    const qs = new URLSearchParams();
    if (params.state && params.state !== "All States") qs.set("state", params.state);
    if (params.city && params.city !== "All Cities") qs.set("city", params.city);
    if (params.material && params.material !== "All Products") qs.set("service", params.material);
    if (params.q) qs.set("q", params.q);

    const res = await fetch(`${BACKEND_URL}/api/labs?${qs.toString()}`);
    if (!res.ok) throw new Error("API error");
    return await res.json();
  } catch {
    // Fall back to local demo filtering
    let results = [...DEMO_LABS];
    if (params.state && params.state !== "All States")
      results = results.filter((l) => l.state === params.state);
    if (params.city && params.city !== "All Cities")
      results = results.filter((l) => l.city === params.city);
    if (params.material && params.material !== "All Products")
      results = results.filter((l) => l.services.includes(params.material!));
    if (params.q) {
      const q = params.q.toLowerCase();
      results = results.filter(
        (l) =>
          l.name.toLowerCase().includes(q) ||
          l.services.some((s) => s.toLowerCase().includes(q)) ||
          l.city.toLowerCase().includes(q)
      );
    }
    return results;
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Sub-component: custom select dropdown
// ─────────────────────────────────────────────────────────────────────────────

function SelectDropdown({
  id,
  label,
  value,
  options,
  onChange,
  disabled,
}: {
  id: string;
  label: string;
  value: string;
  options: string[];
  onChange: (v: string) => void;
  disabled?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  return (
    <div ref={ref} className="relative flex-1 min-w-[140px]">
      <label htmlFor={id} className="block text-[10px] font-semibold text-gov-slate-500 uppercase tracking-wider mb-1">
        {label}
      </label>
      <button
        id={id}
        type="button"
        disabled={disabled}
        onClick={() => setOpen((o) => !o)}
        className={`w-full flex items-center justify-between gap-2 px-3 py-2.5 rounded-xl border text-sm
          transition-all duration-150 bg-white text-left
          ${disabled
            ? "border-gov-slate-200 text-gov-slate-300 cursor-not-allowed"
            : "border-gov-slate-200 text-gov-slate-700 hover:border-gov-navy-400 focus:outline-none focus:ring-2 focus:ring-gov-navy-800/30"
          }`}
      >
        <span className="truncate">{value}</span>
        <ChevronDown
          size={14}
          className={`flex-shrink-0 text-gov-slate-400 transition-transform ${open ? "rotate-180" : ""}`}
        />
      </button>
      {open && (
        <div className="absolute z-30 top-full mt-1 left-0 w-full bg-white rounded-xl border border-gov-slate-200
          shadow-gov-lg overflow-hidden animate-fade-in">
          <div className="max-h-52 overflow-y-auto">
            {options.map((opt) => (
              <button
                key={opt}
                type="button"
                onClick={() => { onChange(opt); setOpen(false); }}
                className={`w-full text-left px-3 py-2 text-sm transition-colors
                  ${value === opt
                    ? "bg-gov-navy-50 text-gov-navy-800 font-semibold"
                    : "text-gov-slate-700 hover:bg-gov-slate-50"
                  }`}
              >
                {opt}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Sub-component: Lab card
// ─────────────────────────────────────────────────────────────────────────────

export function LabCard({ lab }: { lab: LabRecord }) {
  const [copied, setCopied] = useState(false);

  const copyContact = useCallback(async () => {
    const text = [
      lab.name,
      `${lab.address}, ${lab.city}, ${lab.state} – ${lab.pincode}`,
      `Phone: ${lab.phone}`,
      lab.email ? `Email: ${lab.email}` : "",
      lab.bisCode ? `BIS Code: ${lab.bisCode}` : "",
    ]
      .filter(Boolean)
      .join("\n");

    try {
      await navigator.clipboard.writeText(text);
    } catch {
      // fallback
      const el = document.createElement("textarea");
      el.value = text;
      document.body.appendChild(el);
      el.select();
      document.execCommand("copy");
      document.body.removeChild(el);
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 2200);
  }, [lab]);

  return (
    <div
      className="group relative rounded-2xl border border-gov-slate-200 bg-white
        p-5 flex flex-col gap-4 shadow-gov-sm hover:shadow-gov-md
        hover:border-gov-navy-300 transition-all duration-200"
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3 min-w-0">
          <div className="w-10 h-10 rounded-xl bg-gov-navy-50 flex items-center justify-center flex-shrink-0">
            <Microscope size={18} className="text-gov-navy-700" />
          </div>
          <div className="min-w-0">
            <h3 className="font-bold text-sm text-gov-navy-800 leading-snug line-clamp-2">
              {lab.name}
            </h3>
            {lab.bisCode && (
              <span className="text-[10px] font-mono text-gov-slate-400 mt-0.5 block">
                {lab.bisCode}
              </span>
            )}
          </div>
        </div>
        {lab.accredited ? (
          <span
            className="flex-shrink-0 flex items-center gap-1 text-[10px] font-bold
              text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-1 rounded-full"
          >
            <CheckCircle2 size={10} /> NABL
          </span>
        ) : (
          <span
            className="flex-shrink-0 flex items-center gap-1 text-[10px] font-medium
              text-gov-slate-500 bg-gov-slate-100 border border-gov-slate-200 px-2 py-1 rounded-full"
          >
            Registered
          </span>
        )}
      </div>

      {/* Contact info */}
      <div className="space-y-1.5 text-xs text-gov-slate-600">
        <div className="flex items-start gap-2">
          <MapPin size={12} className="flex-shrink-0 mt-0.5 text-gov-orange-500" />
          <span className="leading-snug">
            {lab.address}, {lab.city}, {lab.state} — {lab.pincode}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <Phone size={12} className="flex-shrink-0 text-gov-orange-500" />
          <a
            href={`tel:${lab.phone}`}
            className="hover:text-gov-navy-800 transition-colors font-medium"
          >
            {lab.phone}
          </a>
        </div>
        {lab.email && (
          <div className="flex items-center gap-2">
            <Mail size={12} className="flex-shrink-0 text-gov-orange-500" />
            <a
              href={`mailto:${lab.email}`}
              className="hover:text-gov-navy-800 transition-colors truncate max-w-[200px]"
            >
              {lab.email}
            </a>
          </div>
        )}
      </div>

      {/* Services */}
      <div className="flex flex-wrap gap-1.5">
        {lab.services.slice(0, 3).map((s) => (
          <span
            key={s}
            className="text-[10px] font-medium bg-gov-navy-800/8 text-gov-navy-700
              border border-gov-navy-100 px-2 py-0.5 rounded-full"
          >
            {s}
          </span>
        ))}
        {lab.services.length > 3 && (
          <span className="text-[10px] text-gov-slate-400 self-center">
            +{lab.services.length - 3} more
          </span>
        )}
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2 pt-1 border-t border-gov-slate-100">
        <button
          id={`copy-contact-${lab.id}`}
          onClick={copyContact}
          className={`flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg transition-all
            ${copied
              ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
              : "bg-gov-slate-50 text-gov-slate-600 border border-gov-slate-200 hover:bg-gov-navy-50 hover:text-gov-navy-800 hover:border-gov-navy-200"
            }`}
        >
          {copied ? <Check size={12} /> : <Copy size={12} />}
          {copied ? "Copied!" : "Copy Contact"}
        </button>

        {lab.website && (
          <a
            href={lab.website}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg
              bg-gov-slate-50 text-gov-slate-600 border border-gov-slate-200
              hover:bg-gov-navy-50 hover:text-gov-navy-800 hover:border-gov-navy-200 transition-all"
          >
            <ExternalLink size={12} /> Website
          </a>
        )}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Chat quick-action button (used inside ChatWindow message bubbles)
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Standalone button to inject a "Find labs for IS XXXXX" query into the chat.
 * Place this inside a ChatMessage bubble alongside citation chips.
 *
 * @param standardCode  e.g. "IS 13252"
 * @param onSend        callback receives the pre-built query string
 */
export function FindLabsForStandardButton({
  standardCode,
  onSend,
}: {
  standardCode: string;
  onSend: (query: string) => void;
}) {
  const query = `Find BIS-recognised laboratories that can test ${standardCode}`;
  return (
    <button
      id={`find-labs-${standardCode.replace(/\s+/g, "-")}`}
      type="button"
      onClick={() => onSend(query)}
      className="inline-flex items-center gap-1.5 text-[11px] font-semibold
        px-2.5 py-1 rounded-full border
        bg-emerald-100 border-emerald-300 text-emerald-700
        hover:bg-emerald-200 hover:border-emerald-400 hover:text-emerald-800
        transition-all duration-150 cursor-pointer"
    >
      <FlaskRound size={11} />
      Find labs for {standardCode}
    </button>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Main LabFinder component
// ─────────────────────────────────────────────────────────────────────────────

interface LabFinderProps {
  /**
   * Pre-fill the text search field (e.g. injected from chat "Find labs for IS 13252").
   * The component will auto-trigger a search when this changes.
   */
  initialQuery?: string;
  /** Called when user clicks "Find labs for this standard" chat action button */
  onChatInject?: (query: string) => void;
}

export default function LabFinder({ initialQuery = "", onChatInject }: LabFinderProps) {
  const [stateFilter, setStateFilter] = useState("All States");
  const [cityFilter, setCityFilter] = useState("All Cities");
  const [materialFilter, setMaterialFilter] = useState("All Products");
  const [textQuery, setTextQuery] = useState(initialQuery);
  const [labs, setLabs] = useState<LabRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);
  const [showFilters, setShowFilters] = useState(true);
  const inputRef = useRef<HTMLInputElement>(null);

  // When initialQuery changes (chat injection), update field and auto-search
  useEffect(() => {
    if (initialQuery) {
      setTextQuery(initialQuery);
    }
  }, [initialQuery]);

  const cityOptions = useMemo(
    () => CITIES_BY_STATE[stateFilter] ?? ["All Cities"],
    [stateFilter]
  );

  // Reset city when state changes
  const handleStateChange = useCallback((s: string) => {
    setStateFilter(s);
    setCityFilter("All Cities");
  }, []);

  const doSearch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const results = await fetchLabs({
        state: stateFilter,
        city: cityFilter,
        material: materialFilter,
        q: textQuery.trim(),
      });
      setLabs(results);
    } catch {
      setError("Failed to fetch labs. Showing demo data.");
      setLabs(DEMO_LABS);
    } finally {
      setLoading(false);
      setSearched(true);
    }
  }, [stateFilter, cityFilter, materialFilter, textQuery]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    doSearch();
  };

  // Auto-search when initialQuery prop arrives
  useEffect(() => {
    if (initialQuery) {
      doSearch();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialQuery]);

  const clearFilters = () => {
    setStateFilter("All States");
    setCityFilter("All Cities");
    setMaterialFilter("All Products");
    setTextQuery("");
    setLabs([]);
    setSearched(false);
    inputRef.current?.focus();
  };

  const hasActiveFilters =
    stateFilter !== "All States" ||
    cityFilter !== "All Cities" ||
    materialFilter !== "All Products" ||
    textQuery.trim() !== "";

  return (
    <div className="space-y-5">
      {/* ── Header ──────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-gov-navy-800 to-gov-navy-600 flex items-center justify-center shadow-gov-sm">
            <FlaskConical size={20} className="text-white" />
          </div>
          <div>
            <h2 className="text-base font-bold text-gov-navy-800">BIS Lab Finder</h2>
            <p className="text-xs text-gov-slate-500">Search BIS-recognised &amp; NABL-accredited labs</p>
          </div>
        </div>
        <button
          id="toggle-filters"
          onClick={() => setShowFilters((f) => !f)}
          className="flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-xl
            border border-gov-slate-200 text-gov-slate-600 hover:bg-gov-slate-50 transition-all"
        >
          <SlidersHorizontal size={13} />
          {showFilters ? "Hide" : "Show"} Filters
        </button>
      </div>

      {/* ── Search form ─────────────────────────────────────────────────── */}
      <form onSubmit={handleSubmit} className="space-y-3">
        {/* Text search */}
        <div className="relative">
          <Search
            size={15}
            className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gov-slate-400 pointer-events-none"
          />
          <input
            ref={inputRef}
            id="lab-search-input"
            value={textQuery}
            onChange={(e) => setTextQuery(e.target.value)}
            placeholder="Search by lab name, IS standard (e.g. IS 13252), or service…"
            className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-gov-slate-200 bg-white text-sm
              text-gov-slate-800 placeholder:text-gov-slate-400
              focus:outline-none focus:ring-2 focus:ring-gov-navy-800/30 focus:border-gov-navy-400 transition-all"
          />
          {textQuery && (
            <button
              type="button"
              onClick={() => setTextQuery("")}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gov-slate-400 hover:text-gov-slate-600"
            >
              <X size={14} />
            </button>
          )}
        </div>

        {/* Cascading dropdowns */}
        {showFilters && (
          <div className="flex flex-wrap gap-3 animate-fade-in">
            <SelectDropdown
              id="filter-state"
              label="State"
              value={stateFilter}
              options={STATES}
              onChange={handleStateChange}
            />
            <SelectDropdown
              id="filter-city"
              label="City"
              value={cityFilter}
              options={cityOptions}
              onChange={setCityFilter}
              disabled={stateFilter === "All States"}
            />
            <SelectDropdown
              id="filter-material"
              label="Material / Product"
              value={materialFilter}
              options={MATERIALS}
              onChange={setMaterialFilter}
            />
          </div>
        )}

        {/* Action bar */}
        <div className="flex items-center gap-3">
          <button
            id="lab-search-submit"
            type="submit"
            disabled={loading}
            className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-gov-navy-800 text-white
              text-sm font-semibold disabled:opacity-50 disabled:cursor-not-allowed
              hover:bg-gov-navy-700 active:bg-gov-navy-900 transition-all shadow-gov-sm hover:shadow-gov-md"
          >
            {loading ? <Loader2 size={15} className="animate-spin" /> : <Search size={15} />}
            {loading ? "Searching…" : "Search Labs"}
          </button>

          {hasActiveFilters && (
            <button
              id="lab-clear-filters"
              type="button"
              onClick={clearFilters}
              className="flex items-center gap-1.5 text-xs font-medium text-gov-slate-500
                hover:text-gov-slate-700 transition-colors"
            >
              <X size={12} /> Clear filters
            </button>
          )}

          {searched && !loading && (
            <span className="ml-auto text-xs text-gov-slate-400 font-medium">
              {labs.length} lab{labs.length !== 1 ? "s" : ""} found
            </span>
          )}
        </div>
      </form>

      {/* ── Error banner ────────────────────────────────────────────────── */}
      {error && (
        <div className="flex items-center gap-2 px-4 py-3 rounded-xl bg-amber-50 border border-amber-200 text-amber-800 text-xs">
          <AlertCircle size={14} className="flex-shrink-0 text-amber-500" />
          <span>{error}</span>
          <button onClick={() => setError(null)} className="ml-auto hover:underline">
            Dismiss
          </button>
        </div>
      )}

      {/* ── Results grid ────────────────────────────────────────────────── */}
      {loading && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="rounded-2xl border border-gov-slate-200 bg-white p-5 space-y-3 animate-pulse">
              <div className="flex gap-3">
                <div className="w-10 h-10 rounded-xl bg-gov-slate-100" />
                <div className="flex-1 space-y-2">
                  <div className="h-3 bg-gov-slate-100 rounded w-3/4" />
                  <div className="h-2 bg-gov-slate-100 rounded w-1/2" />
                </div>
              </div>
              <div className="space-y-2">
                <div className="h-2 bg-gov-slate-100 rounded" />
                <div className="h-2 bg-gov-slate-100 rounded w-2/3" />
              </div>
              <div className="flex gap-2">
                <div className="h-5 w-20 bg-gov-slate-100 rounded-full" />
                <div className="h-5 w-20 bg-gov-slate-100 rounded-full" />
              </div>
            </div>
          ))}
        </div>
      )}

      {!loading && searched && labs.length === 0 && (
        <div className="flex flex-col items-center justify-center py-14 text-center">
          <div className="w-16 h-16 rounded-2xl bg-gov-slate-100 flex items-center justify-center mb-4">
            <FlaskConical size={28} className="text-gov-slate-400" />
          </div>
          <p className="text-sm font-semibold text-gov-slate-700">No labs found</p>
          <p className="text-xs text-gov-slate-400 mt-1 max-w-xs">
            Try broadening your search — change the state or product filter, or search by IS standard code.
          </p>
          <button
            onClick={clearFilters}
            className="mt-4 text-xs font-semibold text-gov-navy-800 underline underline-offset-2"
          >
            Reset all filters
          </button>
        </div>
      )}

      {!loading && labs.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 animate-fade-in">
          {labs.map((lab) => (
            <LabCard key={lab.id} lab={lab} />
          ))}
        </div>
      )}

      {/* ── Initial hint (before first search) ─────────────────────────── */}
      {!searched && !loading && (
        <div className="flex flex-col items-center justify-center py-10 text-center">
          <div className="w-16 h-16 rounded-2xl bg-gov-navy-50 border border-gov-navy-100 flex items-center justify-center mb-4">
            <Microscope size={28} className="text-gov-navy-600" />
          </div>
          <p className="text-sm font-semibold text-gov-slate-700">Search for BIS-recognised labs</p>
          <p className="text-xs text-gov-slate-400 mt-1 max-w-xs leading-relaxed">
            Filter by state, city, and product category, or enter an IS standard code (e.g. <span className="font-mono text-gov-navy-700">IS 13252</span>) to find certified testing laboratories.
          </p>
          {onChatInject && (
            <button
              id="chat-inject-demo"
              onClick={() => onChatInject("Find labs for IS 13252 (Electronics)")}
              className="mt-4 flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-full
                bg-emerald-50 border border-emerald-200 text-emerald-700 hover:bg-emerald-100 transition-all"
            >
              <FlaskRound size={12} /> Try: Find labs for IS 13252
            </button>
          )}
        </div>
      )}
    </div>
  );
}
