"use client";

import { useState, useRef, useEffect } from "react";
import { Send, StopCircle, Bot, User } from "lucide-react";
import { useChat } from "../../hooks/useChat";

export default function Chat() {
  const [input, setInput] = useState("");
  const { messages, isLoading, error, sendMessage, stopGeneration } = useChat();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;
    sendMessage(input);
    setInput("");
  };

  return (
    <div className="flex flex-col h-full">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center text-muted-foreground gap-3">
            <Bot className="h-12 w-12 text-gov-navy" />
            <p className="text-lg font-medium">BIS Knowledge Assistant</p>
            <p className="text-sm">Ask me anything about BIS standards and regulations.</p>
          </div>
        )}
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex gap-3 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            {msg.role === "assistant" && (
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gov-navy flex items-center justify-center">
                <Bot className="h-4 w-4 text-white" />
              </div>
            )}
            <div
              className={`max-w-[75%] rounded-2xl px-4 py-3 text-sm ${
                msg.role === "user"
                  ? "bg-gov-navy text-white rounded-tr-sm"
                  : "bg-muted text-foreground rounded-tl-sm"
              }`}
            >
              {msg.content}
            </div>
            {msg.role === "user" && (
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gov-orange flex items-center justify-center">
                <User className="h-4 w-4 text-white" />
              </div>
            )}
          </div>
        ))}
        {isLoading && (
          <div className="flex gap-3 justify-start">
            <div className="w-8 h-8 rounded-full bg-gov-navy flex items-center justify-center">
              <Bot className="h-4 w-4 text-white" />
            </div>
            <div className="bg-muted rounded-2xl rounded-tl-sm px-4 py-3">
              <div className="flex gap-1">
                <span className="w-2 h-2 bg-gov-navy rounded-full animate-bounce [animation-delay:0ms]" />
                <span className="w-2 h-2 bg-gov-navy rounded-full animate-bounce [animation-delay:150ms]" />
                <span className="w-2 h-2 bg-gov-navy rounded-full animate-bounce [animation-delay:300ms]" />
              </div>
            </div>
          </div>
        )}
        {error && (
          <p className="text-center text-sm text-destructive">{error}</p>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <form
        onSubmit={handleSubmit}
        className="border-t p-4 flex gap-2 items-end"
      >
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleSubmit(e as unknown as React.FormEvent);
            }
          }}
          placeholder="Type your question..."
          rows={1}
          className="flex-1 resize-none rounded-xl border border-input bg-background px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gov-navy transition"
        />
        {isLoading ? (
          <button
            type="button"
            onClick={stopGeneration}
            className="p-2 rounded-xl bg-destructive text-white hover:bg-destructive/90 transition"
          >
            <StopCircle className="h-5 w-5" />
          </button>
        ) : (
          <button
            type="submit"
            disabled={!input.trim()}
            className="p-2 rounded-xl bg-gov-navy text-white hover:bg-gov-navy/90 disabled:opacity-40 transition"
          >
            <Send className="h-5 w-5" />
          </button>
        )}
      </form>
    </div>
  );
}