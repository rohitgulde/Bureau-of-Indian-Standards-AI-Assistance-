export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  citations?: Citation[];
  timestamp: Date;
}

export interface Citation {
  id: string;
  title: string;
  source: string;
  url?: string;
  excerpt: string;
  pageNumber?: number;
}

export interface ChatSession {
  id: string;
  title: string;
  messages: Message[];
  createdAt: Date;
  updatedAt: Date;
}

export interface Lab {
  id: string;
  name: string;
  address: string;
  city: string;
  state: string;
  pincode: string;
  phone: string;
  email?: string;
  services: string[];
  accredited: boolean;
  coordinates?: { lat: number; lng: number };
}

export interface WizardStep {
  id: string;
  title: string;
  description: string;
  completed: boolean;
  current: boolean;
}

export interface ApiResponse<T> {
  data: T;
  success: boolean;
  error?: string;
}