"use client";

/**
 * CitationBadge.tsx
 * ──────────────────
 * Parses RAG response text for citation tags and renders them as interactive
 * inline pill badges.  Integrates with CitationDrawer via an onCitationClick
 * callback.
 *
 * Patterns parsed (order = priority)
 * ------------------------------------
 *   [Standard: IS 10500, Clause: 4.2]       ← primary backend format
 *   [Standard: IS 10500:2012, Clause: 4.2]
 *   [IS 10500:2012, Clause 4.2]
 *   [IS 10500, Clause: 4.2]
 *   IS 10500:2012 — Clause 4.2 — (Sources block)
 *
 * Exports
 * -------
 *   ParsedCitation         — normalised citation shape
 *   parseCitations()       — pure utility: text → segments
 *   CitationBadge          — single pill atom (receives ParsedCitation)
 *   CitationText (default) — drops into any text node; replaces tags with pills
 */

import React, { useMemo } from "react";
import { BookOpen, ExternalLink } from "lucide-react";

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

export interface ParsedCitation {
  /** Raw matched string, e.g. "[Standard: IS 10500, Clause: 4.2]" */
  raw: string;
  /** e.g. "IS 10500" or "IS 10500:2012" */
  standardCode: string;
  /** e.g. "4.2" or "unknown" */
  clauseNumber: string;
  /** Optional — populated from metadata payload */
  clauseTitle?: string;
  /** Optional — populated from metadata payload */
  excerpt?: string;
  /** Optional — populated from metadata payload */
  pageNumber?: number;
  /** Similarity score from vector DB (0–1) */
  score?: number;
}

/** One segment of text — either plain text or an inline citation */
export type TextSegment =
  | { kind: "text"; content: string }
  | { kind: "citation"; citation: ParsedCitation };

// ─────────────────────────────────────────────────────────────────────────────
// Regex patterns
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Matches all inline citation formats produced by the backend system prompt.
 *
 * Group 1 → standard code (e.g. "IS 10500" or "IS 10500:2012")
 * Group 2 → clause number (e.g. "4.2" or "unknown")
 */
const INLINE_CITATION_RE =
  /\[\s*(?:Standard:\s*)?(IS\s*\d+(?:[:.]\d+)*(?::\d{4})?)\s*,\s*Clause:?\s*([\w.]+)\s*\]/gi;

/**
 * Matches the "## Sources Used" list lines:
 *   - IS 10500:2012 — Clause 4.2 — Bacteriological Quality
 */
const SOURCES_LINE_RE =
  /^[\s*-]+?(IS\s*\d+(?:[:.]\d+)*(?::\d{4})?)\s*[—–-]+\s*Clause\s*([\w.]+)(?:\s*[—–-]+\s*(.+))?$/gim;

// ─────────────────────────────────────────────────────────────────────────────
// Parse utility
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Splits raw text into alternating plain-text and citation segments.
 * Handles both inline tags and "Sources Used" list entries.
 *
 * @param text     Raw LLM response string
 * @param metadata Optional citation metadata from the SSE metadata event
 *                 used to enrich parsed citations with titles / excerpts
 */
export function parseCitations(
  text: string,
  metadata?: ParsedCitation[]
): TextSegment[] {
  if (!text) return [];

  // Build a metadata lookup keyed by "STANDARD|CLAUSE"
  const metaMap = new Map<string, ParsedCitation>();
  metadata?.forEach((c) => {
    const key = `${c.standardCode.toUpperCase()}|${c.clauseNumber}`;
    metaMap.set(key, c);
  });

  const segments: TextSegment[] = [];
  let lastIndex = 0;

  // Reset global regex
  INLINE_CITATION_RE.lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = INLINE_CITATION_RE.exec(text)) !== null) {
    // Push plain text before this match
    if (match.index > lastIndex) {
      segments.push({ kind: "text", content: text.slice(lastIndex, match.index) });
    }

    const standardCode = match[1].replace(/\s+/, " ").trim();
    const clauseNumber = match[2].trim();
    const key = `${standardCode.toUpperCase()}|${clauseNumber}`;
    const meta = metaMap.get(key);

    const citation: ParsedCitation = {
      raw: match[0],
      standardCode,
      clauseNumber,
      clauseTitle: meta?.clauseTitle,
      excerpt:     meta?.excerpt,
      pageNumber:  meta?.pageNumber,
      score:       meta?.score,
    };

    segments.push({ kind: "citation", citation });
    lastIndex = match.index + match[0].length;
  }

  // Remaining plain text
  if (lastIndex < text.length) {
    segments.push({ kind: "text", content: text.slice(lastIndex) });
  }

  return segments;
}

/**
 * Extract all unique ParsedCitations from text (no segments, just the list).
 * Useful for the "citation chips" row shown below a message.
 */
export function extractCitations(
  text: string,
  metadata?: ParsedCitation[]
): ParsedCitation[] {
  const segs = parseCitations(text, metadata);
  const seen = new Set<string>();
  const out: ParsedCitation[] = [];
  for (const seg of segs) {
    if (seg.kind === "citation") {
      const key = `${seg.citation.standardCode}|${seg.citation.clauseNumber}`;
      if (!seen.has(key)) {
        seen.add(key);
        out.push(seg.citation);
      }
    }
  }
  return out;
}

// ─────────────────────────────────────────────────────────────────────────────
// Colour helpers  (deterministic from standard number)
// ─────────────────────────────────────────────────────────────────────────────

const PALETTE = [
  "from-blue-100 to-blue-50 border-blue-300 text-blue-700 hover:border-blue-400 hover:bg-blue-200",
  "from-violet-100 to-violet-50 border-violet-300 text-violet-700 hover:border-violet-400 hover:bg-violet-200",
  "from-emerald-100 to-emerald-50 border-emerald-300 text-emerald-700 hover:border-emerald-400 hover:bg-emerald-200",
  "from-amber-100 to-amber-50 border-amber-300 text-amber-700 hover:border-amber-400 hover:bg-amber-200",
  "from-rose-100 to-rose-50 border-rose-300 text-rose-700 hover:border-rose-400 hover:bg-rose-200",
  "from-cyan-100 to-cyan-50 border-cyan-300 text-cyan-700 hover:border-cyan-400 hover:bg-cyan-200",
  "from-pink-100 to-pink-50 border-pink-300 text-pink-700 hover:border-pink-400 hover:bg-pink-200",
];

function colorForStandard(code: string): string {
  const num = parseInt(code.replace(/\D/g, ""), 10) || 0;
  return PALETTE[num % PALETTE.length];
}

// ─────────────────────────────────────────────────────────────────────────────
// CitationBadge  — single pill atom
// ─────────────────────────────────────────────────────────────────────────────

interface CitationBadgeProps {
  citation: ParsedCitation;
  onClick?: (citation: ParsedCitation) => void;
  /** "inline" = compact pill inside text; "chip" = slightly larger below message */
  variant?: "inline" | "chip";
  /** Show score confidence bar */
  showScore?: boolean;
}

export function CitationBadge({
  citation,
  onClick,
  variant = "inline",
  showScore = false,
}: CitationBadgeProps) {
  const color = colorForStandard(citation.standardCode);
  const isInline = variant === "inline";
  const pct = Math.round((citation.score ?? 0) * 100);

  return (
    <button
      type="button"
      onClick={() => onClick?.(citation)}
      title={
        citation.clauseTitle
          ? `${citation.standardCode} §${citation.clauseNumber} — ${citation.clauseTitle}`
          : `${citation.standardCode} §${citation.clauseNumber} — Click to view clause`
      }
      className={`
        group inline-flex items-center gap-1.5 rounded-full border
        bg-gradient-to-r ${color}
        font-mono transition-all duration-150 cursor-pointer
        focus:outline-none focus:ring-2 focus:ring-primary/40
        ${isInline
          ? "px-2 py-0.5 text-[11px] mx-0.5 align-baseline"
          : "px-2.5 py-1 text-xs"
        }
        ${onClick ? "hover:scale-[1.04] active:scale-[0.97] shadow-sm hover:shadow-md" : "cursor-default"}
      `}
    >
      <BookOpen size={isInline ? 9 : 11} className="flex-shrink-0 opacity-80" />

      <span className="font-semibold leading-none">
        {citation.standardCode}
      </span>

      {citation.clauseNumber !== "unknown" && (
        <span className="opacity-75 leading-none">
          §{citation.clauseNumber}
        </span>
      )}

      {citation.clauseTitle && !isInline && (
        <span className="opacity-60 max-w-[140px] truncate hidden sm:inline">
          — {citation.clauseTitle}
        </span>
      )}

      {onClick && (
        <ExternalLink
          size={isInline ? 8 : 9}
          className="flex-shrink-0 opacity-50 group-hover:opacity-100 transition-opacity"
        />
      )}

      {/* Confidence bar (chip variant + score) */}
      {showScore && variant === "chip" && citation.score != null && (
        <span
          className="ml-1 px-1 py-0.5 rounded text-[9px] bg-black/20 opacity-70"
          title={`Similarity: ${pct}%`}
        >
          {pct}%
        </span>
      )}
    </button>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// CitationText  (default export)
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Drop-in replacement for a text node that parses citation tags and renders
 * them as inline CitationBadge pills.  Everything between tags is plain text.
 *
 * Example usage:
 *   <CitationText text={message.content} onCitationClick={openDrawer} />
 *
 * This replaces raw text like:
 *   "[Standard: IS 10500, Clause: 4.2] The pH limit is 6.5–8.5."
 * with:
 *   <CitationBadge citation={…} /> The pH limit is 6.5–8.5.
 */
interface CitationTextProps {
  text: string;
  metadata?: ParsedCitation[];
  onCitationClick?: (citation: ParsedCitation) => void;
  className?: string;
}

export default function CitationText({
  text,
  metadata,
  onCitationClick,
  className = "",
}: CitationTextProps) {
  const segments = useMemo(() => parseCitations(text, metadata), [text, metadata]);

  return (
    <span className={`leading-relaxed ${className}`}>
      {segments.map((seg, i) =>
        seg.kind === "text" ? (
          // Preserve newlines within text segments
          <React.Fragment key={i}>
            {seg.content.split("\n").map((line, j, arr) => (
              <React.Fragment key={j}>
                {line}
                {j < arr.length - 1 && <br />}
              </React.Fragment>
            ))}
          </React.Fragment>
        ) : (
          <CitationBadge
            key={i}
            citation={seg.citation}
            onClick={onCitationClick}
            variant="inline"
          />
        )
      )}
    </span>
  );
}
