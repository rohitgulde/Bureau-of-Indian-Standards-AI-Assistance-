"use client";

/**
 * CitationDrawer.tsx
 * ───────────────────
 * Right-hand slide-over drawer that shows full clause details when a
 * CitationBadge pill is clicked.
 *
 * Features
 * --------
 *  • Smooth slide-in from the right (CSS transform + transition)
 *  • Backdrop blur overlay — click outside or press Esc to close
 *  • Header: standard code + colour-coded confidence score
 *  • Body: clause title, full excerpt text (verbatim from vector DB),
 *           page number, product category
 *  • "Related clauses" section — fetches similar chunks from /api/rag
 *  • Loading skeleton while fetching
 *  • Copy-to-clipboard button for the excerpt
 *  • "Open BIS portal" external link
 *
 * Usage
 * -----
 *   import CitationDrawer, { useCitationDrawer } from "@/app/components/Citations/CitationDrawer";
 *
 *   // In a parent component:
 *   const { activeCitation, open, close } = useCitationDrawer();
 *
 *   <CitationBadge citation={c} onClick={open} />
 *   <CitationDrawer citation={activeCitation} onClose={close} />
 */

import React, {
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";
import {
  X,
  BookOpen,
  Copy,
  Check,
  ExternalLink,
  FileText,
  Hash,
  Layers,
  Loader2,
  ChevronRight,
  AlertCircle,
  Star,
} from "lucide-react";
import { ParsedCitation, CitationBadge } from "./CitationBadge";

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

export interface FullClauseDetail {
  standard_code:    string;
  standard_title:   string;
  clause_number:    string;
  clause_title:     string;
  content:          string;
  page_number:      number | null;
  product_category: string | null;
  score:            number;
}

interface RelatedClause extends FullClauseDetail {}

// ─────────────────────────────────────────────────────────────────────────────
// Hook — useCitationDrawer
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Minimal state hook for controlling the drawer from a parent.
 *
 * @example
 *   const { activeCitation, open, close } = useCitationDrawer();
 */
export function useCitationDrawer() {
  const [activeCitation, setActive] = useState<ParsedCitation | null>(null);

  const open  = useCallback((c: ParsedCitation) => setActive(c), []);
  const close = useCallback(() => setActive(null), []);

  return { activeCitation, open, close };
}

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

/** BIS official standard URL (approximation via standardised path) */
function bisPortalUrl(standardCode: string): string {
  const num = standardCode.replace(/[^0-9]/g, "");
  return `https://bis.gov.in/standards/?standard=${num}`;
}

/** Confidence percentage label + colour */
function scoreLabel(score: number): { pct: number; color: string; label: string } {
  const pct = Math.round(score * 100);
  if (pct >= 80) return { pct, color: "text-emerald-400", label: "High relevance" };
  if (pct >= 60) return { pct, color: "text-amber-400",   label: "Moderate relevance" };
  return           { pct, color: "text-rose-400",    label: "Low relevance" };
}

// Standard full titles lookup (common BIS standards)
const IS_TITLES: Record<string, string> = {
  "IS 10500":  "Drinking Water — Specification",
  "IS 14543":  "Packaged Natural Mineral Water — Specification",
  "IS 1077":   "Common Burnt Clay Building Bricks — Specification",
  "IS 432":    "Mild Steel and Medium Tensile Steel Bars — Specification",
  "IS 2062":   "Hot Rolled Medium and High Tensile Structural Steel",
  "IS 9000":   "Basic Environmental Testing Procedures",
  "IS 616":    "Performance Requirements for Electric Lamps",
  "IS 694":    "PVC Insulated Cables for Working Voltages up to and including 1100V",
  "IS 13252":  "IT Equipment — Safety Requirements",
  "IS 302":    "Safety of Household and Similar Electrical Appliances",
  "IS 8758":   "Recommendations for Safety Colour Coding",
  "IS 15758":  "Halogen Lamps for General Lighting Services",
};

function inferTitle(code: string): string {
  const normalized = code.replace(/:\d{4}$/, "").replace(/\s+/g, " ").trim();
  return IS_TITLES[normalized] ?? `${code} — Indian Standard`;
}

// ─────────────────────────────────────────────────────────────────────────────
// Loading Skeleton
// ─────────────────────────────────────────────────────────────────────────────

function Skeleton({ className = "" }: { className?: string }) {
  return (
    <div
      className={`rounded-lg bg-gradient-to-r from-muted/60 via-muted/30 to-muted/60
        animate-pulse ${className}`}
    />
  );
}

function DrawerSkeleton() {
  return (
    <div className="p-6 space-y-4">
      <Skeleton className="h-6 w-2/3" />
      <Skeleton className="h-4 w-1/2" />
      <div className="space-y-2 pt-2">
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-4/5" />
        <Skeleton className="h-4 w-3/4" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-2/3" />
      </div>
      <Skeleton className="h-20 w-full rounded-xl mt-4" />
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// CitationDrawer
// ─────────────────────────────────────────────────────────────────────────────

interface CitationDrawerProps {
  citation: ParsedCitation | null;
  onClose: () => void;
}

export default function CitationDrawer({ citation, onClose }: CitationDrawerProps) {
  const [detail,   setDetail]   = useState<FullClauseDetail | null>(null);
  const [related,  setRelated]  = useState<RelatedClause[]>([]);
  const [loading,  setLoading]  = useState(false);
  const [error,    setError]    = useState<string | null>(null);
  const [copied,   setCopied]   = useState(false);
  const [mounted,  setMounted]  = useState(false);
  const drawerRef = useRef<HTMLDivElement>(null);
  const isOpen = citation !== null;

  // Animate in
  useEffect(() => {
    if (isOpen) {
      requestAnimationFrame(() => setMounted(true));
    } else {
      setMounted(false);
      setDetail(null);
      setRelated([]);
      setError(null);
    }
  }, [isOpen]);

  // Keyboard close
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    if (isOpen) document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [isOpen, onClose]);

  // Fetch full clause detail from vector DB
  useEffect(() => {
    if (!citation) return;
    setLoading(true);
    setError(null);
    setDetail(null);
    setRelated([]);

    const ctrl = new AbortController();

    (async () => {
      try {
        // Use the RAG query endpoint to fetch the exact clause
        const query = `${citation.standardCode} clause ${citation.clauseNumber}`;

        const res = await fetch(`${BACKEND_URL}/api/rag/query`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          signal: ctrl.signal,
          body: JSON.stringify({ question: query, top_k: 6 }),
        });

        if (!res.ok) throw new Error(`API ${res.status}`);

        const data = await res.json();

        // The first matching chunk becomes the "detail"
        const chunks: FullClauseDetail[] = (data.retrieved_chunks ?? []).map(
          (c: Record<string, unknown>) => ({
            standard_code:    String(c.standard_code ?? citation.standardCode),
            standard_title:   String(c.standard_title ?? inferTitle(citation.standardCode)),
            clause_number:    String(c.clause_number ?? citation.clauseNumber),
            clause_title:     String(c.clause_title ?? citation.clauseTitle ?? ""),
            content:          String(c.content ?? c.text ?? ""),
            page_number:      typeof c.page_number === "number" ? c.page_number : null,
            product_category: c.product_category ? String(c.product_category) : null,
            score:            typeof c.score === "number" ? c.score : 0,
          })
        );

        // Best-match: exact clause number match
        const exact = chunks.find(
          (c) => c.clause_number === citation.clauseNumber
            &&   c.standard_code.replace(/:\d{4}$/, "").trim()
                   === citation.standardCode.replace(/:\d{4}$/, "").trim()
        );

        setDetail(
          exact ?? chunks[0] ?? {
            standard_code:    citation.standardCode,
            standard_title:   inferTitle(citation.standardCode),
            clause_number:    citation.clauseNumber,
            clause_title:     citation.clauseTitle ?? "",
            content:          citation.excerpt ?? "Full clause text not available in the indexed corpus.",
            page_number:      citation.pageNumber ?? null,
            product_category: null,
            score:            citation.score ?? 0,
          }
        );

        // Remaining chunks become "related"
        setRelated(chunks.filter((c) => c !== exact).slice(0, 4));
      } catch (err) {
        if ((err as Error).name === "AbortError") return;

        // Fallback: use data already available from citation metadata
        setDetail({
          standard_code:    citation.standardCode,
          standard_title:   inferTitle(citation.standardCode),
          clause_number:    citation.clauseNumber,
          clause_title:     citation.clauseTitle ?? "",
          content:          citation.excerpt ?? "The full clause text could not be retrieved. Please check the backend connection.",
          page_number:      citation.pageNumber ?? null,
          product_category: null,
          score:            citation.score ?? 0,
        });
        if (!citation.excerpt) {
          setError("Could not fetch full clause from vector database. Showing available metadata.");
        }
      } finally {
        setLoading(false);
      }
    })();

    return () => ctrl.abort();
  }, [citation]);

  // Copy excerpt to clipboard
  async function copyExcerpt() {
    if (!detail?.content) return;
    await navigator.clipboard.writeText(detail.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  if (!isOpen) return null;

  const scoreInfo = detail ? scoreLabel(detail.score) : null;

  return (
    <>
      {/* ── Backdrop ─────────────────────────────────────────────── */}
      <div
        onClick={onClose}
        aria-label="Close citation drawer"
        className={`fixed inset-0 z-40 bg-black/50 backdrop-blur-[2px]
          transition-opacity duration-300
          ${mounted ? "opacity-100" : "opacity-0"}`}
      />

      {/* ── Drawer panel ─────────────────────────────────────────── */}
      <aside
        ref={drawerRef}
        role="dialog"
        aria-modal="true"
        aria-label={`Citation: ${citation?.standardCode} §${citation?.clauseNumber}`}
        className={`fixed top-0 right-0 h-full z-50
          w-full sm:w-[480px] lg:w-[520px]
          flex flex-col
          bg-card border-l border-border shadow-2xl
          transition-transform duration-300 ease-out
          ${mounted ? "translate-x-0" : "translate-x-full"}`}
      >
        {/* ── Drawer header ─────────────────────────────────────── */}
        <div
          className="flex items-start justify-between px-5 py-4
            border-b border-border bg-sidebar/80 flex-shrink-0"
        >
          <div className="flex items-center gap-3 min-w-0">
            <div
              className="w-9 h-9 rounded-xl bg-primary/15 border border-primary/30
                flex items-center justify-center flex-shrink-0"
            >
              <BookOpen size={16} className="text-primary" />
            </div>
            <div className="min-w-0">
              <p className="font-bold text-foreground text-sm leading-tight font-mono truncate">
                {citation?.standardCode}
              </p>
              <p className="text-[11px] text-muted-foreground mt-0.5">
                Clause&nbsp;
                <span className="text-primary font-semibold">
                  {citation?.clauseNumber}
                </span>
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 flex-shrink-0 ml-3">
            {/* BIS portal link */}
            <a
              href={bisPortalUrl(citation?.standardCode ?? "")}
              target="_blank"
              rel="noopener noreferrer"
              title="Open on BIS portal"
              className="h-8 w-8 rounded-lg flex items-center justify-center
                border border-border text-muted-foreground
                hover:border-primary/40 hover:text-primary transition-colors"
            >
              <ExternalLink size={13} />
            </a>

            {/* Close */}
            <button
              onClick={onClose}
              className="h-8 w-8 rounded-lg flex items-center justify-center
                border border-border text-muted-foreground
                hover:border-destructive/40 hover:text-destructive transition-colors"
            >
              <X size={14} />
            </button>
          </div>
        </div>

        {/* ── Drawer body (scrollable) ──────────────────────────── */}
        <div className="flex-1 overflow-y-auto">

          {loading && <DrawerSkeleton />}

          {!loading && error && (
            <div className="mx-5 mt-5 flex items-start gap-2 px-4 py-3 rounded-xl
              bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs">
              <AlertCircle size={13} className="flex-shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {!loading && detail && (
            <div className="p-5 space-y-5">
              {/* Standard title */}
              <div>
                <p className="text-xs font-semibold uppercase tracking-widest
                  text-muted-foreground mb-1">
                  Standard
                </p>
                <p className="text-sm font-semibold text-foreground">
                  {detail.standard_title}
                </p>
              </div>

              {/* Metadata pills row */}
              <div className="flex flex-wrap gap-2">
                {/* Clause number */}
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1
                  rounded-full text-xs bg-primary/10 border border-primary/25 text-primary">
                  <Hash size={10} />
                  Clause {detail.clause_number}
                </span>

                {/* Page */}
                {detail.page_number != null && (
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-1
                    rounded-full text-xs bg-muted/50 border border-border text-muted-foreground">
                    <FileText size={10} />
                    Page {detail.page_number}
                  </span>
                )}

                {/* Product category */}
                {detail.product_category && (
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-1
                    rounded-full text-xs bg-muted/50 border border-border text-muted-foreground">
                    <Layers size={10} />
                    {detail.product_category}
                  </span>
                )}

                {/* Confidence score */}
                {scoreInfo && detail.score > 0 && (
                  <span
                    className={`inline-flex items-center gap-1.5 px-2.5 py-1
                      rounded-full text-xs bg-muted/50 border border-border ${scoreInfo.color}`}
                    title={scoreInfo.label}
                  >
                    <Star size={10} />
                    {scoreInfo.pct}% match
                  </span>
                )}
              </div>

              {/* Clause title */}
              {detail.clause_title && (
                <div>
                  <p className="text-xs font-semibold uppercase tracking-widest
                    text-muted-foreground mb-1">
                    Clause Title
                  </p>
                  <p className="text-sm font-medium text-foreground">
                    {detail.clause_title}
                  </p>
                </div>
              )}

              {/* Clause content (verbatim) */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <p className="text-xs font-semibold uppercase tracking-widest
                    text-muted-foreground">
                    Clause Text
                  </p>
                  <button
                    onClick={copyExcerpt}
                    className="flex items-center gap-1 text-[11px] text-muted-foreground
                      hover:text-primary transition-colors px-2 py-1 rounded-lg
                      hover:bg-muted/40 border border-transparent hover:border-border"
                  >
                    {copied ? (
                      <><Check size={11} className="text-emerald-400" /> Copied</>
                    ) : (
                      <><Copy size={11} /> Copy</>
                    )}
                  </button>
                </div>

                <div
                  className="relative rounded-xl border border-border bg-muted/20
                    p-4 text-sm text-foreground/90 leading-relaxed
                    whitespace-pre-wrap font-[inherit]"
                >
                  {/* Decorative left bar */}
                  <div className="absolute left-0 top-3 bottom-3 w-0.5
                    rounded-full bg-primary/40" />

                  <div className="pl-3">
                    {detail.content || (
                      <span className="italic text-muted-foreground">
                        Clause text not available in indexed corpus.
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {/* Confidence bar */}
              {detail.score > 0 && (
                <div>
                  <div className="flex items-center justify-between text-[11px]
                    text-muted-foreground mb-1">
                    <span>Vector similarity</span>
                    <span className={scoreInfo?.color}>
                      {scoreInfo?.pct}% — {scoreInfo?.label}
                    </span>
                  </div>
                  <div className="h-1.5 w-full rounded-full bg-muted/50">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-primary to-primary/60
                        transition-all duration-700"
                      style={{ width: `${scoreInfo?.pct ?? 0}%` }}
                    />
                  </div>
                </div>
              )}

              {/* Related clauses */}
              {related.length > 0 && (
                <div>
                  <p className="text-xs font-semibold uppercase tracking-widest
                    text-muted-foreground mb-2">
                    Related Clauses
                  </p>
                  <div className="space-y-2">
                    {related.map((r, i) => (
                      <div
                        key={i}
                        className="group flex items-start gap-3 p-3 rounded-xl
                          border border-border hover:border-primary/30
                          bg-muted/10 hover:bg-muted/20 transition-colors cursor-default"
                      >
                        <div className="flex-shrink-0 mt-0.5">
                          <CitationBadge
                            citation={{
                              raw:          `[${r.standard_code}, Clause: ${r.clause_number}]`,
                              standardCode: r.standard_code,
                              clauseNumber: r.clause_number,
                              clauseTitle:  r.clause_title,
                              score:        r.score,
                            }}
                            variant="chip"
                            showScore
                          />
                        </div>
                        <div className="min-w-0 flex-1">
                          {r.clause_title && (
                            <p className="text-xs font-medium text-foreground mb-0.5 truncate">
                              {r.clause_title}
                            </p>
                          )}
                          <p className="text-[11px] text-muted-foreground line-clamp-2">
                            {r.content}
                          </p>
                        </div>
                        <ChevronRight
                          size={12}
                          className="flex-shrink-0 text-muted-foreground/40
                            group-hover:text-primary transition-colors mt-0.5"
                        />
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* CTA footer */}
              <div className="rounded-xl border border-border bg-muted/10 p-4 space-y-2">
                <p className="text-xs font-semibold text-muted-foreground">
                  Need the full standard?
                </p>
                <div className="flex flex-wrap gap-2">
                  <a
                    href={bisPortalUrl(detail.standard_code)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg
                      bg-primary/10 border border-primary/25 text-primary text-xs
                      hover:bg-primary/20 transition-colors font-medium"
                  >
                    <ExternalLink size={11} />
                    View on BIS Portal
                  </a>
                  <a
                    href="https://manakonline.in"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg
                      bg-muted/50 border border-border text-muted-foreground text-xs
                      hover:border-primary/30 hover:text-primary transition-colors"
                  >
                    <ExternalLink size={11} />
                    Manak Online
                  </a>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* ── Drawer footer ─────────────────────────────────────── */}
        <div
          className="flex-shrink-0 border-t border-border bg-sidebar/50
            px-5 py-3 flex items-center justify-between"
        >
          <p className="text-[11px] text-muted-foreground">
            Retrieved from indexed IS standard corpus
          </p>
          <button
            onClick={onClose}
            className="text-xs text-muted-foreground hover:text-primary
              transition-colors px-3 py-1.5 rounded-lg hover:bg-muted/40
              border border-transparent hover:border-border"
          >
            Close  <kbd className="ml-1 text-[9px] opacity-50">Esc</kbd>
          </button>
        </div>
      </aside>
    </>
  );
}
