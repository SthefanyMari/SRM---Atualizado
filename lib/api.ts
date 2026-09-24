export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type User = {
  id: number;
  name: string;
  email: string;
  role: "user" | "admin";
  is_active: boolean;
  avatar: string;
  preference_profile: Record<string, unknown>;
  created_at: string;
};

export type Content = {
  id: number;
  title: string;
  description: string;
  domain: string;
  category: string;
  image_url: string | null;
  external_url: string | null;
  source_name: string;
  external_id: string;
  metadata: Record<string, unknown>;
  is_published: boolean;
  created_at: string;
  updated_at: string;
};

export type Recommendation = {
  content: Content;
  score: number;
  reason: string;
};

export type DomainRecord = {
  id: number;
  code: string;
  name: string;
  description: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type InteractionHistory = {
  id: number;
  content_id: number;
  interaction_type: "view" | "click" | "rating" | "recommendation";
  value: number | null;
  context: Record<string, unknown>;
  created_at: string;
  content: Content | null;
};

export type ChatMessage = {
  id: number;
  role: "user" | "assistant";
  content: string;
  sources: Array<{ content_id: number; title: string; domain: string }>;
  created_at: string;
};

export type Statistics = {
  users: number;
  active_users: number;
  contents: number;
  interactions: number;
  feedbacks: number;
  contents_by_domain: Record<string, number>;
  interactions_by_type: Record<string, number>;
};

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}

export async function api<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  if (!response.ok) {
    let message = `Erro ${response.status}`;
    try {
      const data = (await response.json()) as { detail?: string };
      message = data.detail ?? message;
    } catch {
      // Mantém a mensagem padrão quando a resposta não é JSON.
    }
    throw new ApiError(message, response.status);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}
