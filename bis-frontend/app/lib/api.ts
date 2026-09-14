import { ApiResponse, ChatSession, Message, Lab } from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(
  endpoint: string,
  options?: RequestInit
): Promise<ApiResponse<T>> {
  try {
    const res = await fetch(`${API_BASE_URL}${endpoint}`, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
    if (!res.ok) {
      const error = await res.text();
      return { data: null as T, success: false, error };
    }
    const data: T = await res.json();
    return { data, success: true };
  } catch (err) {
    return {
      data: null as T,
      success: false,
      error: err instanceof Error ? err.message : "Unknown error",
    };
  }
}

// Chat API
export const chatApi = {
  sendMessage: (sessionId: string, content: string) =>
    request<Message>("/api/chat", {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId, content }),
    }),

  getSessions: () => request<ChatSession[]>("/api/chat/sessions"),

  getSession: (id: string) =>
    request<ChatSession>(`/api/chat/sessions/${id}`),
};

// Lab Finder API
export const labApi = {
  searchLabs: (query: string, pincode?: string) => {
    const params = new URLSearchParams({ q: query });
    if (pincode) params.set("pincode", pincode);
    return request<Lab[]>(`/api/labs?${params.toString()}`);
  },

  getLabById: (id: string) => request<Lab>(`/api/labs/${id}`),
};

// Document API
export const documentApi = {
  uploadPdf: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<{ id: string; name: string }>("/api/documents/upload", {
      method: "POST",
      headers: {},
      body: form,
    });
  },

  listDocuments: () =>
    request<{ id: string; name: string }[]>("/api/documents"),
};