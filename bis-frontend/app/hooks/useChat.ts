'use client';

import { useState, useCallback, useRef } from 'react';
import { Message, ChatSession } from '../lib/types';
import { chatApi } from '../lib/api';

interface UseChatOptions {
  sessionId?: string;
  onError?: (error: string) => void;
}

export function useChat({ sessionId, onError }: UseChatOptions = {}) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [session, setSession] = useState<ChatSession | null>(null);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim() || isLoading) return;

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);
    setError(null);

    const sid = sessionId ?? session?.id ?? crypto.randomUUID();

    const result = await chatApi.sendMessage(sid, content);

    if (result.success) {
      setMessages(prev => [...prev, result.data]);
    } else {
      const msg = result.error ?? 'Failed to get a response';
      setError(msg);
      onError?.(msg);
    }

    setIsLoading(false);
  }, [isLoading, session, sessionId, onError]);

  const clearMessages = useCallback(() => {
    setMessages([]);
    setError(null);
  }, []);

  const stopGeneration = useCallback(() => {
    abortRef.current?.abort();
    setIsLoading(false);
  }, []);

  return { messages, isLoading, error, session, sendMessage, clearMessages, stopGeneration };
}
