"use client";

import { ExternalLink, FileText, ChevronDown, ChevronUp } from "lucide-react";
import { useState } from "react";
import { Citation } from "../../lib/types";

interface CitationsProps {
  citations: Citation[];
}

function CitationCard({ citation }: { citation: Citation }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="rounded-xl border border-border bg-card p-4 space-y-2 text-sm">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <FileText className="h-4 w-4 text-gov-navy flex-shrink-0" />
          <span className="font-medium text-foreground">{citation.title}</span>
        </div>
        <div className="flex items-center gap-1">
          {citation.url && (
            <a
              href={citation.url}
              target="_blank"
              rel="noreferrer"
              className="p-1 rounded hover:bg-muted transition"
            >
              <ExternalLink className="h-3.5 w-3.5 text-gov-orange" />
            </a>
          )}
          <button
            onClick={() => setExpanded(!expanded)}
            className="p-1 rounded hover:bg-muted transition"
          >
            {expanded ? (
              <ChevronUp className="h-3.5 w-3.5" />
            ) : (
              <ChevronDown className="h-3.5 w-3.5" />
            )}
          </button>
        </div>
      </div>
      <p className="text-xs text-muted-foreground">{citation.source}</p>
      {citation.pageNumber && (
        <p className="text-xs text-gov-navy font-medium">Page {citation.pageNumber}</p>
      )}
      {expanded && (
        <blockquote className="mt-2 border-l-2 border-gov-orange pl-3 text-xs text-muted-foreground italic">
          {citation.excerpt}
        </blockquote>
      )}
    </div>
  );
}

export default function Citations({ citations }: CitationsProps) {
  if (!citations || citations.length === 0) return null;

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
        <FileText className="h-4 w-4 text-gov-navy" />
        Sources ({citations.length})
      </h3>
      <div className="space-y-2">
        {citations.map((c) => (
          <CitationCard key={c.id} citation={c} />
        ))}
      </div>
    </div>
  );
}