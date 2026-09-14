"use client";

/**
 * ChatWindow.tsx
 * ──────────────
 * Full-featured conversational UI for the BIS Knowledge Portal.
 *
 * Features
 * --------
 *  • Message history with distinct bubble styles (User / Assistant / System)
 *  • Real-time SSE token streaming from POST /api/chat
 *  • react-markdown with remark-gfm: renders tables, bold, code blocks
 *  • react-syntax-highlighter: highlights IS standard clause code snippets
 *  • Bottom bar: text input · Send · Voice toggle · Language selector (12 langs)
 *  • Citation chips below each assistant message
 *  • Typing indicator animation while streaming
 *  • Auto-scroll to latest message
 *  • Keyboard shortcut: Enter to send, Shift+Enter for newline
 */

import React, {
  useCallback,
  useEffect,
  useRef,
  useState,
  KeyboardEvent,
} from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import {
  Send,
  Mic,
  MicOff,
  Globe,
  ChevronDown,
  AlertCircle,
  Loader2,
  Bot,
  User,
  Info,
  ExternalLink,
  ShieldCheck,
  HelpCircle,
  CheckCircle,
  FlaskConical,
  FileText,
  BookOpen,
  Settings,
} from "lucide-react";
import CitationText, { CitationBadge, ParsedCitation } from "./Citations/CitationBadge";
import CitationDrawer, { useCitationDrawer } from "./Citations/CitationDrawer";
import { FindLabsForStandardButton, LabCard, LabRecord } from "./LabFinder";
import { useLanguage, LANGUAGES } from "./LanguageContext";
import LanguageSelector from "./LanguageSelector";
import { useTranslation } from "react-i18next";

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

export type MessageRole = "user" | "assistant" | "system";

export interface Citation {
  standard_code: string;
  clause_number: string;
  clause_title?: string;
  page_number?: number;
  content?: string;
}

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  isStreaming?: boolean;
  citations?: Citation[];
  intent?: string;
  lang?: string;
  regional_answer?: string;
  suggestions?: string[];
  huid_verification?: any;
  labs?: LabRecord[];
  schemes?: any[];
  faqs?: any[];
  timestamp: Date;
}

interface SSEEvent {
  type: "token" | "metadata" | "error" | "done";
  data?: unknown;
}

interface MetadataPayload {
  intent: string;
  detected_lang: string;
  citations: Citation[];
  answer?: string;
  regional_answer?: string;
  labs?: LabRecord[];
  schemes?: any[];
  faqs?: any[];
  huid_verification?: any;
  fallback_triggered?: boolean;
}

// ─────────────────────────────────────────────────────────────────────────────
// Constants
// ─────────────────────────────────────────────────────────────────────────────

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

const INTENT_LABELS: Record<string, string> = {
  TECHNICAL_CLAUSE_QUERY:  "Technical Clause",
  PRODUCT_STANDARD_LOOKUP: "Standard Lookup",
  LAB_SEARCH:              "Lab Finder",
  SCHEME_GUIDANCE:         "Certification",
  PROCESS_EXPLAINER:       "Process Explainer",
  CONSUMER_HALLMARK:       "Hallmark / HUID",
  GENERAL_QUERY:           "General",
};

const INTENT_COLORS: Record<string, string> = {
  TECHNICAL_CLAUSE_QUERY:  "bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-400 border-blue-300 dark:border-blue-800",
  PRODUCT_STANDARD_LOOKUP: "bg-violet-100 dark:bg-violet-900/40 text-violet-700 dark:text-violet-400 border-violet-300 dark:border-violet-800",
  LAB_SEARCH:              "bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-400 border-emerald-300 dark:border-emerald-800",
  SCHEME_GUIDANCE:         "bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-400 border-amber-300 dark:border-amber-800",
  PROCESS_EXPLAINER:       "bg-orange-100 dark:bg-orange-900/40 text-orange-700 dark:text-orange-400 border-orange-300 dark:border-orange-800",
  CONSUMER_HALLMARK:       "bg-rose-100 dark:bg-rose-900/40 text-rose-700 dark:text-rose-400 border-rose-300 dark:border-rose-800",
  GENERAL_QUERY:           "bg-slate-100 dark:bg-slate-800/60 text-slate-700 dark:text-slate-400 border-slate-300 dark:border-slate-700",
};

function genId() {
  return Math.random().toString(36).slice(2, 10);
}

// Helper to map DB lab to UI lab
function mapDbLabToLabRecord(dbLab: any): LabRecord {
  return {
    id: String(dbLab.id),
    name: dbLab.name,
    address: dbLab.address,
    city: dbLab.city,
    state: dbLab.state,
    pincode: dbLab.pincode,
    phone: dbLab.phone,
    email: dbLab.contact_email,
    services: dbLab.testing_scope ? dbLab.testing_scope.split(",").map((s: string) => s.trim()) : [],
    accredited: Boolean(dbLab.accreditations && dbLab.accreditations.includes("NABL")),
    website: dbLab.website,
  };
}

function SchemeCard({ scheme }: { scheme: any }) {
  return (
    <div className="bg-amber-50/50 border border-amber-200/60 rounded-xl p-4 my-2 text-sm shadow-sm text-left">
      <div className="flex items-start gap-2 mb-2">
        <ShieldCheck className="text-amber-600 flex-shrink-0 mt-0.5" size={16} />
        <div>
          <h4 className="font-bold text-amber-900">{scheme.scheme_name}</h4>
          <span className="text-[10px] font-mono bg-amber-200/50 text-amber-800 px-1.5 py-0.5 rounded">
            {scheme.scheme_code}
          </span>
        </div>
      </div>
      <p className="text-amber-900/80 text-xs mb-3 leading-relaxed">
        {scheme.description}
      </p>
      <div className="grid grid-cols-2 gap-2 text-[11px] text-amber-900/70 mb-3">
        <div>
          <span className="font-semibold block">Target Audience:</span>
          {scheme.target_audience}
        </div>
        <div>
          <span className="font-semibold block">Validity:</span>
          {scheme.validity_period}
        </div>
        <div className="col-span-2">
          <span className="font-semibold block">Applicable Products:</span>
          {scheme.applicable_products}
        </div>
      </div>
      {scheme.application_portal_url && (
        <a 
          href={scheme.application_portal_url} 
          target="_blank" 
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-[11px] font-semibold bg-amber-600 text-white px-3 py-1.5 rounded-lg hover:bg-amber-700 transition-colors"
        >
          <ExternalLink size={12} /> Apply on {scheme.application_portal_url.includes('manakonline') ? 'Manakonline' : 'CRS Portal'}
        </a>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Sub-components
// ─────────────────────────────────────────────────────────────────────────────

/** Blinking three-dot typing indicator */
function TypingIndicator() {
  return (
    <div className="flex items-center gap-1 py-1 px-1">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="w-2 h-2 rounded-full bg-primary/60 animate-bounce"
          style={{ animationDelay: `${i * 120}ms`, animationDuration: "0.8s" }}
        />
      ))}
    </div>
  );
}

/** Single message bubble */
function MessageBubble({
  message,
  onCitationClick,
  onSendQuery,
}: {
  message: ChatMessage;
  onCitationClick?: (c: ParsedCitation) => void;
  /** Inject a pre-built query into the chat (used by Find-labs quick action) */
  onSendQuery?: (query: string) => void;
}) {
  const isUser      = message.role === "user";
  const isSystem    = message.role === "system";
  const isAssistant = message.role === "assistant";

  if (isSystem) {
    return (
      <div className="flex justify-center my-2">
        <div className="flex items-center gap-2 px-4 py-2 rounded-full
          bg-muted/40 border border-border text-muted-foreground text-xs">
          <Info size={12} />
          <span>{message.content}</span>
        </div>
      </div>
    );
  }

  return (
    <div className={`flex gap-3 mb-4 ${isUser ? "flex-row-reverse" : "flex-row"}`}>
      {/* Avatar */}
      <div
        className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center
          shadow-lg ${isUser
            ? "bg-primary text-primary-foreground"
            : "bg-gradient-to-br from-navy-800 to-primary/80 text-white border border-primary/30"
          }`}
      >
        {isUser ? <User size={16} /> : <Bot size={16} />}
      </div>

      {/* Bubble */}
      <div className={`flex flex-col ${isUser ? "items-end" : "items-start"} max-w-[82%]`}>
        {/* Intent badge (assistant only) */}
        {isAssistant && message.intent && !message.isStreaming && (
          <span
            className={`mb-1.5 px-2 py-0.5 rounded-full text-[10px] font-medium
              border tracking-wide ${INTENT_COLORS[message.intent] ?? "bg-muted/40 text-muted-foreground border-border"}`}
          >
            {INTENT_LABELS[message.intent] ?? message.intent}
          </span>
        )}

        {/* Content bubble */}
        <div
          className={`rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-md
            ${isUser
              ? "bg-primary text-primary-foreground rounded-tr-sm"
              : "bg-card border border-border text-card-foreground rounded-tl-sm"
            }`}
        >
          {isUser ? (
            <p className="whitespace-pre-wrap">{message.content}</p>
          ) : message.isStreaming && !message.content ? (
            <TypingIndicator />
          ) : (
            <CitationText
              text={message.content}
              onCitationClick={onCitationClick}
              metadata={message.citations?.map((c) => ({
                raw: `[${c.standard_code}, Clause: ${c.clause_number}]`,
                standardCode: c.standard_code,
                clauseNumber: c.clause_number,
                clauseTitle:  c.clause_title,
                excerpt:      c.content,
                pageNumber:   c.page_number,
              }))}
            />
          )}

          {/* Streaming cursor */}
          {isAssistant && message.isStreaming && message.content && (
            <span className="inline-block w-0.5 h-4 bg-primary/80 ml-0.5 animate-pulse align-middle" />
          )}
        </div>

        {/* Regional translation toggle */}
        {isAssistant && message.regional_answer && message.lang !== "en" && (
          <RegionalTranslation text={message.regional_answer} lang={message.lang} />
        )}

        {/* Render Clickable Suggestions if present */}
        {isAssistant && message.suggestions && message.suggestions.length > 0 && (
          <div className="mt-3 flex flex-col gap-2 w-full max-w-sm text-left">
            {message.suggestions.map((sug, idx) => (
              <button
                key={idx}
                onClick={() => onSendQuery && onSendQuery(sug)}
                className="text-left px-4 py-2 rounded-xl text-sm border-2 border-primary/20 hover:border-primary/50 hover:bg-primary/5 text-foreground transition-all duration-200 shadow-sm"
              >
                {sug}
              </button>
            ))}
          </div>
        )}

        {/* Render Labs if present */}
        {isAssistant && message.labs && message.labs.length > 0 && (
          <div className="mt-3 flex flex-col gap-2 w-full max-w-sm text-left">
            {message.labs.map((lab: any) => (
              <LabCard key={lab.id} lab={lab} />
            ))}
          </div>
        )}

        {/* Render Schemes if present */}
        {isAssistant && message.schemes && message.schemes.length > 0 && (
          <div className="mt-3 flex flex-col gap-2 w-full max-w-sm text-left">
            {message.schemes.map((scheme: any) => (
              <SchemeCard key={scheme.id} scheme={scheme} />
            ))}
          </div>
        )}

        {/* Render FAQs if present */}
        {isAssistant && message.faqs && message.faqs.length > 0 && (
          <div className="mt-3 flex flex-col gap-2 w-full max-w-sm text-left">
            {message.faqs.map((faq: any) => (
              <FaqCard key={faq.id} faq={faq} />
            ))}
          </div>
        )}

        {/* Render HUID Verification if present */}
        {isAssistant && message.huid_verification && (
          <div className="mt-4 p-4 rounded-xl border-2 border-emerald-500/20 bg-emerald-500/5 shadow-sm relative overflow-hidden group">
            <div className="absolute top-0 right-0 p-3 opacity-10 transform translate-x-2 -translate-y-2 group-hover:scale-110 transition-transform">
              <ShieldCheck size={64} className="text-emerald-500" />
            </div>
            
            <div className="flex items-center gap-2 mb-3">
              <CheckCircle className="text-emerald-500" size={20} />
              <h4 className="font-bold text-emerald-700 dark:text-emerald-400">
                Verified HUID: {message.huid_verification.huid}
              </h4>
            </div>
            
            <div className="grid grid-cols-2 gap-y-2 gap-x-4 text-sm relative z-10">
              <div>
                <p className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold">Article Type</p>
                <p className="font-medium text-foreground">{message.huid_verification.article_type}</p>
              </div>
              <div>
                <p className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold">Purity</p>
                <p className="font-medium text-foreground">
                  {message.huid_verification.purity_karat} ({message.huid_verification.purity_fineness})
                </p>
              </div>
              <div className="col-span-2 mt-1 pt-2 border-t border-emerald-500/10">
                <p className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold">Jeweller</p>
                <p className="font-medium text-foreground">{message.huid_verification.jeweller_name}</p>
                <p className="text-xs text-muted-foreground">{message.huid_verification.jeweller_reg_no}</p>
              </div>
              <div className="col-span-2 mt-1 pt-2 border-t border-emerald-500/10">
                <p className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold">Assaying Center</p>
                <p className="font-medium text-foreground">{message.huid_verification.ahc_name}</p>
                <p className="text-xs text-muted-foreground">{message.huid_verification.ahc_location}</p>
              </div>
            </div>
          </div>
        )}

        {/* Citation chips */}
        {isAssistant && message.citations && message.citations.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-2">
            {message.citations
              .filter((c, index, self) => 
                self.findIndex(x => x.standard_code === c.standard_code && x.clause_number === c.clause_number) === index
              )
              .map((c, i) => (
              <CitationBadge
                key={i}
                variant="chip"
                showScore={!!(c as Citation & { score?: number }).score}
                citation={{
                  raw:          `[${c.standard_code}, Clause: ${c.clause_number}]`,
                  standardCode: c.standard_code,
                  clauseNumber: c.clause_number,
                  clauseTitle:  c.clause_title,
                  excerpt:      c.content,
                  pageNumber:   c.page_number,
                }}
                onClick={onCitationClick}
              />
            ))}
            {onSendQuery && message.citations[0]?.standard_code && (
              <ActionChipsForStandard
                standardCode={message.citations[0].standard_code}
                onSend={onSendQuery}
              />
            )}
          </div>
        )}

        {/* Timestamp */}
        <span className="text-[10px] text-muted-foreground mt-1 px-1">
          {message.timestamp.toLocaleTimeString("en-IN", {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </span>
      </div>
    </div>
  );
}

function FaqCard({ faq }: { faq: any }) {
  return (
    <div className="bg-rose-50/50 border border-rose-200/60 rounded-xl p-4 my-2 text-sm shadow-sm text-left">
      <div className="flex items-start gap-2 mb-2">
        <HelpCircle className="text-rose-600 flex-shrink-0 mt-0.5" size={16} />
        <div>
          <h4 className="font-bold text-rose-900">{faq.question}</h4>
          <span className="text-[10px] font-mono bg-rose-200/50 text-rose-800 px-1.5 py-0.5 rounded">
            {faq.topic}
          </span>
        </div>
      </div>
      <div className="text-rose-900/80 text-xs mb-3 leading-relaxed [&>ol]:list-decimal [&>ol]:ml-4 [&>ul]:list-disc [&>ul]:ml-4 [&>p]:mb-2">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>
          {faq.resolution_steps}
        </ReactMarkdown>
      </div>
      {faq.related_url && (
        <a href={faq.related_url} target="_blank" rel="noreferrer" className="text-[11px] text-rose-600 hover:underline">
          Read more →
        </a>
      )}
    </div>
  );
}

/** Collapsible regional translation block */
function RegionalTranslation({ text, lang }: { text: string; lang?: string }) {
  const [show, setShow] = useState(false);
  const langName = LANGUAGES.find((l) => l.code === lang)?.nativeLabel ?? lang;
  return (
    <div className="mt-1.5 w-full">
      <button
        onClick={() => setShow((s) => !s)}
        className="flex items-center gap-1 text-[11px] text-muted-foreground
          hover:text-primary transition-colors"
      >
        <Globe size={11} />
        <span>{langName} translation</span>
        <ChevronDown
          size={11}
          className={`transition-transform ${show ? "rotate-180" : ""}`}
        />
      </button>
      {show && (
        <div className="mt-1 px-3 py-2 rounded-xl bg-muted/30 border border-border
          text-sm text-foreground/80 leading-relaxed">
          {text}
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────

// ─────────────────────────────────────────────────────────────────────────────
// Main ChatWindow
// ─────────────────────────────────────────────────────────────────────────────

interface ChatWindowProps {
  className?: string;
}

export default function ChatWindow({ className = "" }: ChatWindowProps) {
  const [messages,    setMessages]    = useState<ChatMessage[]>([
    {
      id:        "msg-system",
      role:      "system",
      content:   "Welcome to the BIS Knowledge Portal. Ask anything about Indian Standards, labs, or certification.",
      timestamp: new Date(),
    },
    {
      id:        "msg-welcome",
      role:      "assistant",
      content:   "Hello! I'm your BIS Standards Assistant 🇮🇳\n\nI can help you with the following topics. What would you like to know?",
      suggestions: [
        "IS standard requirements and technical clauses",
        "Lab locations for product testing",
        "Certification steps (ISI Mark, CRS, FMCS, Hallmarking)",
        "Gold hallmark & HUID verification"
      ],
      citations:  [],
      timestamp:  new Date(),
    },
  ]);
  const [input,       setInput]       = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [isVoice,     setIsVoice]     = useState(false);
  const { lang } = useLanguage();
  const { t } = useTranslation();
  const [error,       setError]       = useState<string | null>(null);

  // Citation drawer
  const { activeCitation, open: openDrawer, close: closeDrawer } = useCitationDrawer();

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef       = useRef<HTMLTextAreaElement>(null);
  const abortRef       = useRef<AbortController | null>(null);

  // Translate initial welcome messages when language changes
  useEffect(() => {
    setMessages((prev) => {
      const newMsgs = [...prev];
      const sysIdx = newMsgs.findIndex((m) => m.id === "msg-system");
      if (sysIdx !== -1) {
        newMsgs[sysIdx] = {
          ...newMsgs[sysIdx],
          content: t("welcome_system_msg", "Welcome to the BIS Knowledge Portal. Ask anything about Indian Standards, labs, or certification.")
        };
      }
      const welcomeIdx = newMsgs.findIndex((m) => m.id === "msg-welcome");
      if (welcomeIdx !== -1) {
        newMsgs[welcomeIdx] = {
          ...newMsgs[welcomeIdx],
          content: t("welcome_assistant_msg", "Hello! I'm your BIS Standards Assistant 🇮🇳\n\nI can help you with the following topics. What would you like to know?"),
          suggestions: [
            t("suggestion_1", "IS standard requirements and technical clauses"),
            t("suggestion_2", "Lab locations for product testing"),
            t("suggestion_3", "Certification steps (ISI Mark, CRS, FMCS, Hallmarking)"),
            t("suggestion_4", "Gold hallmark & HUID verification")
          ]
        };
      }
      return newMsgs;
    });
  }, [lang, t]);

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Auto-resize textarea
  useEffect(() => {
    const el = inputRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 120) + "px";
  }, [input]);

  const addMessage = useCallback((msg: Omit<ChatMessage, "id" | "timestamp">) => {
    const full: ChatMessage = { ...msg, id: genId(), timestamp: new Date() };
    setMessages((prev) => [...prev, full]);
    return full.id;
  }, []);

  const updateMessage = useCallback(
    (id: string, patch: Partial<ChatMessage>) => {
      setMessages((prev) =>
        prev.map((m) => (m.id === id ? { ...m, ...patch } : m))
      );
    },
    []
  );

  // ── SSE streaming chat ─────────────────────────────────────────────────────
  const sendMessage = useCallback(async (overrideQuery?: string | any) => {
    const q = typeof overrideQuery === "string" ? overrideQuery : input;
    const question = q.trim();
    if (!question || isStreaming) return;

    setInput("");
    setError(null);
    inputRef.current?.focus();

    // Add user bubble
    addMessage({ role: "user", content: question, lang });

    // Add empty assistant bubble (will fill with streamed tokens)
    const assistantId = addMessage({
      role:       "assistant",
      content:    "",
      isStreaming: true,
      citations:  [],
    });

    setIsStreaming(true);
    abortRef.current = new AbortController();

    // Build conversation history from last 10 messages
    const history = messages
      .filter((m) => m.role !== "system")
      .slice(-10)
      .map((m) => ({ role: m.role, content: m.content }));

    let fullText = "";   // accumulated streamed tokens — accessible in catch

    try {
      const res = await fetch(`${BACKEND_URL}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        signal:  abortRef.current.signal,
        body: JSON.stringify({
          question,
          language_code: `${lang}-IN`,
          history,
          stream: true,
        }),
      });

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: ${await res.text()}`);
      }

      const reader  = res.body!.getReader();
      const decoder = new TextDecoder();
      let buffer    = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";   // keep incomplete line

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const raw = line.slice(6).trim();
          if (!raw) continue;

          let event: SSEEvent;
          try { event = JSON.parse(raw); }
          catch { continue; }

          if (event.type === "token") {
            fullText += event.data as string;
            updateMessage(assistantId, { content: fullText, isStreaming: true });
          } else if (event.type === "metadata") {
            const meta = event.data as MetadataPayload;
            const hasStructuredData = (meta.faqs && meta.faqs.length > 0) || (meta.schemes && meta.schemes.length > 0) || (meta.labs && meta.labs.length > 0) || !!meta.huid_verification;
            updateMessage(assistantId, {
              isStreaming:     false,
              content:         meta.answer || fullText || (hasStructuredData ? "" : "Error: No response generated from the selected tool."),
              citations:       meta.citations ?? [],
              intent:          meta.intent,
              lang:            meta.detected_lang,
              regional_answer: meta.regional_answer ?? undefined,
              labs:            meta.labs ? meta.labs.map(mapDbLabToLabRecord) : [],
              schemes:         meta.schemes,
              faqs:            meta.faqs,
              huid_verification: meta.huid_verification,
            });
          } else if (event.type === "error") {
            throw new Error(event.data as string);
          } else if (event.type === "done") {
            updateMessage(assistantId, { isStreaming: false });
            break;
          }
        }
      }
    } catch (err: unknown) {
      if (err instanceof Error && err.name === "AbortError") {
        updateMessage(assistantId, { content: fullText || "_(cancelled)_", isStreaming: false });
      } else {
        const msg = err instanceof Error ? err.message : String(err);
        setError(msg);
        updateMessage(assistantId, {
          content:     `⚠️ Error: ${msg}`,
          isStreaming: false,
        });
      }
    } finally {
      setIsStreaming(false);
      abortRef.current = null;
    }

  }, [input, isStreaming, lang, messages, addMessage, updateMessage]);

  // Listen for quick chat events from outside (e.g. hero pills)
  useEffect(() => {
    const handleQuickChat = (e: Event) => {
      const customEvent = e as CustomEvent<string>;
      if (customEvent.detail) {
        sendMessage(customEvent.detail);
      }
    };
    window.addEventListener("send-quick-chat", handleQuickChat);
    return () => window.removeEventListener("send-quick-chat", handleQuickChat);
  }, [sendMessage]);

  const stopStreaming = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  const handleKey = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    },
    [sendMessage]
  );

  // ─────────────────────────────────────────────────────────────────────────
  // Render
  // ─────────────────────────────────────────────────────────────────────────

  return (
    <div
      className={`flex flex-col h-full bg-background rounded-2xl overflow-hidden
        border border-border shadow-xl ${className}`}
    >
      {/* ── Header ─────────────────────────────────────────────────── */}
      <div
        className="flex items-center justify-between px-5 py-3
          bg-gradient-to-r from-sidebar to-sidebar/90
          border-b border-sidebar-border"
      >
        <div className="flex items-center gap-3">
          <div
            className="w-9 h-9 rounded-xl bg-primary/20 border border-primary/30
              flex items-center justify-center shadow-inner"
          >
            <Bot size={18} className="text-primary" />
          </div>
          <div>
            <p className="text-sm font-semibold text-sidebar-foreground leading-tight">
              BIS Standards Assistant
            </p>
            <p className="text-[10px] text-muted-foreground">
              Powered by Gemini · Bhashini · Qdrant
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="flex items-center gap-1.5 text-[11px] text-emerald-400">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            Live
          </span>
        </div>
      </div>

      {/* ── Message list ───────────────────────────────────────────── */}
      <div
        className="flex-1 overflow-y-auto px-4 py-4 space-y-1
          scrollbar-thin scrollbar-thumb-muted/50 scrollbar-track-transparent"
      >
        {messages.map((msg) => (
          <MessageBubble
            key={msg.id}
            message={msg}
            onCitationClick={openDrawer}
            onSendQuery={(query) => {
              sendMessage(query);
            }}
          />
        ))}

        {error && (
          <div
            className="flex items-center gap-2 mx-2 px-4 py-2 rounded-xl
              bg-destructive/10 border border-destructive/30 text-destructive text-sm"
          >
            <AlertCircle size={14} />
            <span>{error}</span>
            <button
              onClick={() => setError(null)}
              className="ml-auto text-xs hover:underline"
            >
              Dismiss
            </button>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* ── Bottom bar ─────────────────────────────────────────────── */}
      <div
        className="border-t border-border bg-card/60 backdrop-blur-sm px-3 py-3"
      >
        <div className="flex items-end gap-2">
          <LanguageSelector />

          <button
            onClick={() => setIsVoice((v) => !v)}
            title={isVoice ? "Disable voice mode" : "Enable voice mode"}
            className={`flex-shrink-0 h-10 w-10 rounded-xl border flex items-center
              justify-center transition-all duration-200
              ${isVoice
                ? "bg-primary border-primary text-primary-foreground shadow-lg shadow-primary/30 scale-105"
                : "bg-card border-border text-muted-foreground hover:border-primary/50 hover:text-primary"
              }`}
          >
            {isVoice ? <Mic size={16} /> : <MicOff size={16} />}
          </button>

          {/* Text input */}
          <div className="flex-1 relative">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKey}
              disabled={isStreaming}
              placeholder={isVoice ? `Listening in ${LANGUAGES.find((l) => l.code === lang)?.label ?? "English"}...` : t("type_in_your_lang")}
              rows={1}
              className="w-full resize-none rounded-xl bg-background border border-border
                text-sm text-foreground placeholder:text-muted-foreground
                px-4 py-2.5 pr-12
                focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary/60
                disabled:opacity-50 disabled:cursor-not-allowed
                transition-all duration-150 max-h-[120px]"
            />
          </div>

          <button
            onClick={isStreaming ? stopStreaming : sendMessage}
            disabled={!isStreaming && !input.trim()}
            title={isStreaming ? "Stop generation" : "Send message"}
            className={`flex-shrink-0 h-10 w-10 rounded-xl flex items-center justify-center
              font-medium transition-all duration-200 shadow-md
              ${isStreaming
                ? "bg-destructive/80 hover:bg-destructive text-white border border-destructive/50"
                : "bg-primary hover:bg-primary/90 text-primary-foreground border border-primary/50 disabled:opacity-40 disabled:cursor-not-allowed hover:scale-105 disabled:hover:scale-100"
              }`}
          >
            {isStreaming ? (
              <Loader2 size={16} className="animate-spin" />
            ) : (
              <Send size={16} />
            )}
          </button>
        </div>

        <div className="mt-2 flex items-center justify-between text-[10px] text-muted-foreground/60 px-1">
          <div className="flex gap-4">
            <span className="hidden sm:inline">{t("enter_to_send")}</span>
            <span className="hidden sm:inline">{t("shift_enter")}</span>
          </div>
          <span>{t("citations_clickable")}</span>
        </div>
      </div>

      {/* ── Citation Drawer (renders outside scroll area, overlays full page) */}
      <CitationDrawer citation={activeCitation} onClose={closeDrawer} />
    </div>
  );
}

function ActionChipsForStandard({
  standardCode,
  onSend,
}: {
  standardCode: string;
  onSend: (query: string) => void;
}) {
  const actions = [
    { label: "Find labs", query: `Find BIS-recognised laboratories that can test ${standardCode}`, icon: FlaskConical, color: "bg-emerald-100 border-emerald-300 text-emerald-700 hover:bg-emerald-200 hover:border-emerald-400 hover:text-emerald-800" },
    { label: "Certification process", query: `What is the certification process for ${standardCode}?`, icon: Settings, color: "bg-blue-100 border-blue-300 text-blue-700 hover:bg-blue-200 hover:border-blue-400 hover:text-blue-800" },
    { label: "Guidelines", query: `What are the guidelines for ${standardCode}?`, icon: BookOpen, color: "bg-amber-100 border-amber-300 text-amber-700 hover:bg-amber-200 hover:border-amber-400 hover:text-amber-800" },
    { label: "Scheme Guidance", query: `Provide Scheme Guidance for ${standardCode}`, icon: ShieldCheck, color: "bg-purple-100 border-purple-300 text-purple-700 hover:bg-purple-200 hover:border-purple-400 hover:text-purple-800" },
    { label: "Process Explainer", query: `Explain the process for ${standardCode}`, icon: FileText, color: "bg-rose-100 border-rose-300 text-rose-700 hover:bg-rose-200 hover:border-rose-400 hover:text-rose-800" },
  ];

  return (
    <div className="flex flex-wrap gap-1.5 mt-3 pt-3 border-t border-border/50 w-full">
      <span className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider w-full mb-0.5">Explore {standardCode}:</span>
      {actions.map((act) => (
        <button
          key={act.label}
          onClick={() => onSend(act.query)}
          className={`inline-flex items-center gap-1.5 text-[11px] font-semibold px-2.5 py-1 rounded-full border transition-all duration-150 cursor-pointer ${act.color}`}
        >
          <act.icon size={11} />
          {act.label}
        </button>
      ))}
    </div>
  );
}
