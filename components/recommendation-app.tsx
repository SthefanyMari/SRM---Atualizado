"use client";

import {
  ArrowLeft,
  ArrowUpRight,
  BookOpen,
  Bot,
  Check,
  ChevronLeft,
  ChevronRight,
  Clock3,
  Database,
  Film,
  GraduationCap,
  Heart,
  Home,
  LayoutGrid,
  Loader2,
  LogIn,
  LogOut,
  Menu,
  Music2,
  Package,
  Pencil,
  Plus,
  Save,
  Search,
  Send,
  ShieldCheck,
  Sparkles,
  Star,
  Rotate3D,
  Images,
  Trash2,
  UserRound,
  Users,
  X,
} from "lucide-react";
import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { toast, Toaster } from "sonner";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import {
  api,
  ApiError,
  ChatMessage,
  Content,
  DomainRecord,
  InteractionHistory,
  Recommendation,
  Statistics,
  User,
} from "@/lib/api";

type View =
  | "inicio"
  | "catalogo"
  | "detalhes"
  | "recomendacoes"
  | "assistente"
  | "historico"
  | "perfil"
  | "administracao";

type AdminTab = "registro" | "dominios" | "conteudos" | "usuarios";
type DetailsMediaMode = "images" | "3d";

const appViews: View[] = [
  "inicio",
  "catalogo",
  "detalhes",
  "recomendacoes",
  "assistente",
  "historico",
  "perfil",
  "administracao",
];

function isAppView(value: unknown): value is View {
  return typeof value === "string" && appViews.includes(value as View);
}

function isProtectedView(value: View) {
  return ["recomendacoes", "assistente", "historico", "perfil", "administracao"].includes(value);
}

const knownDomainLabels: Record<string, string> = {
  filme: "Filmes",
  musica: "Músicas",
  livro: "Livros",
  curso: "Cursos",
  produto: "Produtos",
};

const knownDomainIcons = {
  filme: Film,
  musica: Music2,
  livro: BookOpen,
  curso: GraduationCap,
  produto: Package,
};

const fallbackDomains: DomainRecord[] = Object.entries(knownDomainLabels).map(
  ([code, name], index) => ({
    id: -(index + 1),
    code,
    name,
    description: "",
    is_active: true,
    created_at: "",
    updated_at: "",
  }),
);

const avatarOptions = [
  { id: "astronauta", emoji: "🚀", label: "Astronauta" },
  { id: "robo", emoji: "🤖", label: "Robô" },
  { id: "coruja", emoji: "🦉", label: "Coruja" },
  { id: "panda", emoji: "🐼", label: "Panda" },
  { id: "raposa", emoji: "🦊", label: "Raposa" },
  { id: "gato", emoji: "😺", label: "Gato" },
  { id: "mago", emoji: "🧙", label: "Mago" },
  { id: "estrela", emoji: "🌟", label: "Estrela" },
];

const navigation: Array<{ icon: typeof Home; label: string; view: View; protected?: boolean }> = [
  { icon: Home, label: "Início", view: "inicio" },
  { icon: LayoutGrid, label: "Catálogo", view: "catalogo" },
  { icon: Star, label: "Recomendações", view: "recomendacoes", protected: true },
  { icon: Sparkles, label: "Assistente IA", view: "assistente", protected: true },
  { icon: Clock3, label: "Histórico", view: "historico", protected: true },
  { icon: UserRound, label: "Perfil", view: "perfil", protected: true },
];

const contentColors = [
  "from-[#763b22] to-[#172a48]",
  "from-[#59338b] to-[#192443]",
  "from-[#805712] to-[#182844]",
  "from-[#08735e] to-[#12314a]",
  "from-[#9a470c] to-[#2a1b28]",
  "from-[#214f82] to-[#14263f]",
];

type AuthResponse = { user: User; message: string; access_token?: string };
type DeleteTarget = { kind: "domain" | "content" | "user"; id: number; label: string };

function errorMessage(error: unknown) {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return "Não foi possível concluir a operação.";
}

function avatarEmoji(avatar?: string) {
  return avatarOptions.find((item) => item.id === avatar)?.emoji ?? "🚀";
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
}

const metadataLabels: Record<string, string> = {
  year: "Ano",
  duration: "Duração",
  author: "Autor",
  artist: "Artista",
  level: "Nível",
  hours: "Carga horária",
  institution: "Instituição",
  brand: "Marca",
  connection: "Conexão",
};

function metadataLabel(key: string) {
  return metadataLabels[key] ?? key.replaceAll("_", " ");
}

function metadataValue(key: string, value: unknown) {
  if (key === "hours" && typeof value === "number") return `${value} horas`;
  if (typeof value === "boolean") return value ? "Sim" : "Não";
  if (typeof value === "object" && value !== null) return JSON.stringify(value);
  return String(value);
}

function getMetadataString(metadata: Record<string, unknown>, key: string) {
  const value = metadata[key];
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function getGalleryImages(content: Content) {
  const savedImages = Array.isArray(content.metadata?.images)
    ? content.metadata.images.filter(
        (value): value is string => typeof value === "string" && Boolean(value.trim()),
      )
    : [];

  return Array.from(
    new Set(
      [content.image_url, ...savedImages]
        .filter((value): value is string => typeof value === "string" && Boolean(value.trim()))
        .map((value) => value.trim()),
    ),
  );
}

function getAdditionalImages(content: Content | null) {
  if (!content) return "";
  return getGalleryImages(content)
    .filter((image) => image !== content.image_url)
    .join("\n");
}

function PageTitle({ title, description }: { title: string; description: string }) {
  return (
    <div>
      <h1 className="text-3xl font-light tracking-tight sm:text-4xl">{title}</h1>
      <p className="mt-3 text-[#9fc3e5]">{description}</p>
    </div>
  );
}

export function RecommendationApp() {
  const [view, setView] = useState<View>("inicio");
  const [contents, setContents] = useState<Content[]>([]);
  const [domains, setDomains] = useState<DomainRecord[]>(fallbackDomains);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [recommendationsLoading, setRecommendationsLoading] = useState(false);
  const [history, setHistory] = useState<InteractionHistory[]>([]);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [adminContents, setAdminContents] = useState<Content[]>([]);
  const [adminDomains, setAdminDomains] = useState<DomainRecord[]>([]);
  const [statistics, setStatistics] = useState<Statistics | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [query, setQuery] = useState("");
  const [selectedDomain, setSelectedDomain] = useState("");
  const [selectedContent, setSelectedContent] = useState<Content | null>(null);
  const [detailsReturnView, setDetailsReturnView] = useState<View>("catalogo");
  const [detailsMediaMode, setDetailsMediaMode] = useState<DetailsMediaMode>("images");
  const [galleryIndex, setGalleryIndex] = useState(0);
  const [preferredDomains, setPreferredDomains] = useState<string[]>([]);
  const [relevantIds, setRelevantIds] = useState<Set<number>>(new Set());
  const [ratings, setRatings] = useState<Record<number, number>>({});
  const [assistantMessage, setAssistantMessage] = useState("");
  const [assistantSending, setAssistantSending] = useState(false);
  const [assistantProvider, setAssistantProvider] = useState<"local" | "online">("local");
  const [authOpen, setAuthOpen] = useState(false);
  const [authMode, setAuthMode] = useState<"login" | "register">("login");
  const [mobileOpen, setMobileOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [apiOnline, setApiOnline] = useState(true);
  const [domainDialogOpen, setDomainDialogOpen] = useState(false);
  const [contentDialogOpen, setContentDialogOpen] = useState(false);
  const [userDialogOpen, setUserDialogOpen] = useState(false);
  const [editingDomain, setEditingDomain] = useState<DomainRecord | null>(null);
  const [editingContent, setEditingContent] = useState<Content | null>(null);
  const [contentDomain, setContentDomain] = useState("filme");
  const [contentPublished, setContentPublished] = useState(true);
  const [domainActive, setDomainActive] = useState(true);
  const [newUserRole, setNewUserRole] = useState<"user" | "admin">("user");
  const [profileAvatar, setProfileAvatar] = useState("astronauta");
  const [adminTab, setAdminTab] = useState<AdminTab>("registro");
  const [deleteTarget, setDeleteTarget] = useState<DeleteTarget | null>(null);
  const temporaryMessageId = useRef(-1);
  const chatEndRef = useRef<HTMLDivElement | null>(null);
  const userRef = useRef<User | null>(null);

  const labelForDomain = useCallback(
    (code: string) => domains.find((item) => item.code === code)?.name ?? knownDomainLabels[code] ?? code,
    [domains],
  );

  const loadContents = useCallback(async (nextQuery = "", nextDomain = "") => {
    setLoading(true);
    const params = new URLSearchParams({ limit: "100" });
    if (nextQuery.trim()) params.set("q", nextQuery.trim());
    if (nextDomain) params.set("domain", nextDomain);
    try {
      const data = await api<{ total: number; items: Content[] }>(`/api/v1/contents?${params}`);
      setContents(data.items);
      setApiOnline(true);
    } catch (error) {
      setApiOnline(false);
      toast.error(errorMessage(error));
    } finally {
      setLoading(false);
    }
  }, []);

  const loadDomains = useCallback(async () => {
    try {
      const data = await api<DomainRecord[]>("/api/v1/domains");
      if (data.length) setDomains(data);
    } catch {
      setDomains(fallbackDomains);
    }
  }, []);

  const loadHistory = useCallback(async () => {
    try {
      setHistory(await api<InteractionHistory[]>("/api/v1/interactions/history?limit=100"));
    } catch (error) {
      toast.error(errorMessage(error));
    }
  }, []);

  const loadChatHistory = useCallback(async () => {
    try {
      setChatMessages(await api<ChatMessage[]>("/api/v1/assistant/history"));
    } catch (error) {
      toast.error(errorMessage(error));
    }
  }, []);

  const loadAdmin = useCallback(async () => {
    try {
      const [stats, domainData, contentData, userData] = await Promise.all([
        api<Statistics>("/api/v1/admin/statistics"),
        api<DomainRecord[]>("/api/v1/admin/domains"),
        api<{ total: number; items: Content[] }>("/api/v1/admin/contents?limit=500"),
        api<User[]>("/api/v1/admin/users?limit=200"),
      ]);
      setStatistics(stats);
      setAdminDomains(domainData);
      setAdminContents(contentData.items);
      setUsers(userData);
    } catch (error) {
      toast.error(errorMessage(error));
    }
  }, []);

  useEffect(() => {
    // As chamadas assíncronas abaixo sincronizam a tela com a API ao iniciar.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void Promise.all([loadContents(), loadDomains()]);
    void api<User>("/api/v1/auth/me")
      .then((currentUser) => {
        setUser(currentUser);
        setProfileAvatar(currentUser.avatar ?? "astronauta");
        const profile = currentUser.preference_profile as { preferred_domains?: string[] };
        setPreferredDomains(profile.preferred_domains ?? []);
      })
      .catch(() => setUser(null));
  }, [loadContents, loadDomains]);

  useEffect(() => {
    userRef.current = user;
  }, [user]);

  useEffect(() => {
    void import("@google/model-viewer");
  }, []);

  useEffect(() => {
    window.history.replaceState(
      { ...(window.history.state ?? {}), rmView: "inicio" },
      "",
    );

    function handleBrowserNavigation(event: PopStateEvent) {
      const nextView = event.state?.rmView;
      if (!isAppView(nextView)) return;

      const currentUser = userRef.current;
      if (isProtectedView(nextView) && !currentUser) {
        setView("inicio");
        window.history.replaceState({ rmView: "inicio" }, "");
        setAuthMode("login");
        setAuthOpen(true);
        toast.info("Entre na sua conta para abrir esta área.");
        return;
      }
      if (nextView === "administracao" && currentUser?.role !== "admin") {
        setView("inicio");
        window.history.replaceState({ rmView: "inicio" }, "");
        toast.error("Esta área é exclusiva para administradores.");
        return;
      }

      setView(nextView);
      setMobileOpen(false);
      window.scrollTo({ top: 0, behavior: "smooth" });
    }

    window.addEventListener("popstate", handleBrowserNavigation);
    return () => window.removeEventListener("popstate", handleBrowserNavigation);
  }, []);

  useEffect(() => {
    if (!user) return;
    // Cada tela protegida carrega seus próprios dados quando é aberta.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (view === "historico") void loadHistory();
    if (view === "assistente") void loadChatHistory();
    if (view === "administracao" && user.role === "admin") void loadAdmin();
  }, [view, user, loadAdmin, loadChatHistory, loadHistory]);

  useEffect(() => {
    if (view === "assistente") {
      chatEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
    }
  }, [chatMessages, assistantSending, view]);

  const featured = recommendations[0]?.content ?? contents[0] ?? null;
  const featuredReason = recommendations[0]?.reason;
  const activeDomains = domains.filter((item) => item.is_active);

  function openAuth(mode: "login" | "register") {
    setAuthMode(mode);
    setAuthOpen(true);
    setMobileOpen(false);
  }

  function navigate(nextView: View, protectedView = false) {
    if ((protectedView || nextView === "administracao") && !user) {
      openAuth("login");
      toast.info("Entre na sua conta para abrir esta área.");
      return false;
    }
    if (nextView === "administracao" && user?.role !== "admin") {
      toast.error("Esta área é exclusiva para administradores.");
      return false;
    }
    if (nextView !== view) {
      window.history.pushState({ rmView: nextView }, "");
      setView(nextView);
    }
    setMobileOpen(false);
    window.scrollTo({ top: 0, behavior: "smooth" });
    return true;
  }

  async function handleAuth(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const payload = {
      ...(authMode === "register" ? { name: String(form.get("name")) } : {}),
      email: String(form.get("email")),
      password: String(form.get("password")),
    };
    try {
      const data = await api<AuthResponse>(
        authMode === "login" ? "/api/v1/auth/login" : "/api/v1/auth/register",
        { method: "POST", body: JSON.stringify(payload) },
      );
      setUser(data.user);
      setProfileAvatar(data.user.avatar ?? "astronauta");
      setPreferredDomains(
        (data.user.preference_profile.preferred_domains as string[] | undefined) ?? [],
      );
      setAuthOpen(false);
      toast.success(data.message);
    } catch (error) {
      toast.error(errorMessage(error));
    }
  }

  async function logout() {
    try {
      await api<{ message: string }>("/api/v1/auth/logout", { method: "POST" });
    } finally {
      setUser(null);
      setRecommendations([]);
      setChatMessages([]);
      setHistory([]);
      setView("inicio");
      window.history.pushState({ rmView: "inicio" }, "");
      toast.success("Você saiu da conta.");
    }
  }

  async function openContentDetails(content: Content) {
    if (view !== "detalhes") setDetailsReturnView(view);
    setSelectedContent(content);
    setDetailsMediaMode("images");
    setGalleryIndex(0);
    window.history.pushState({ rmView: "detalhes", contentId: content.id }, "");
    setView("detalhes");
    window.scrollTo({ top: 0, behavior: "smooth" });
    try {
      await api(`/api/v1/contents/${content.id}/view`, { method: "POST" });
    } catch (error) {
      toast.error(errorMessage(error));
    }
  }

  async function openExternalContent(content: Content) {
    if (!content.external_url) {
      toast.info("Este conteúdo ainda não possui um link externo cadastrado.");
      return;
    }
    if (user) {
      try {
        await api("/api/v1/interactions", {
          method: "POST",
          body: JSON.stringify({
            content_id: content.id,
            interaction_type: "click",
            context: { source: "content_details" },
          }),
        });
      } catch (error) {
        toast.error(errorMessage(error));
        return;
      }
    }
    window.open(content.external_url, "_blank", "noopener,noreferrer");
  }

  async function rateContent(contentId: number, value: number) {
    if (!user) {
      openAuth("login");
      toast.info("Entre na conta para avaliar este conteúdo.");
      return;
    }
    try {
      await api("/api/v1/interactions", {
        method: "POST",
        body: JSON.stringify({
          content_id: contentId,
          interaction_type: "rating",
          value,
          context: { source: "content_details" },
        }),
      });
      setRatings((current) => ({ ...current, [contentId]: value }));
      toast.success(`Avaliação de ${value} estrela${value > 1 ? "s" : ""} salva.`);
    } catch (error) {
      toast.error(errorMessage(error));
    }
  }

  async function saveFeedback(contentId: number, relevant: boolean) {
    if (!user) {
      openAuth("login");
      return;
    }
    try {
      await api("/api/v1/recommendations/feedback", {
        method: "POST",
        body: JSON.stringify({ content_id: contentId, relevant }),
      });
      setRelevantIds((current) => {
        const next = new Set(current);
        if (relevant) next.add(contentId);
        else next.delete(contentId);
        return next;
      });
      toast.success(relevant ? "Marcado como relevante." : "A recomendação será ajustada.");
    } catch (error) {
      toast.error(errorMessage(error));
    }
  }

  async function savePreferences(showMessage = true) {
    if (!user) {
      openAuth("login");
      return false;
    }
    try {
      await api("/api/v1/preferences", {
        method: "PUT",
        body: JSON.stringify({ preferred_domains: preferredDomains, preferred_categories: [] }),
      });
      if (showMessage) toast.success("Preferências salvas.");
      return true;
    } catch (error) {
      toast.error(errorMessage(error));
      return false;
    }
  }

  async function loadRecommendations() {
  if (!user) {
    openAuth("login");
    return;
  }

  if (!preferredDomains.length) {
    toast.info("Escolha pelo menos um domínio.");
    return;
  }

  if (recommendationsLoading) {
    return;
  }

  setRecommendationsLoading(true);

  try {
    const preferencesSaved = await savePreferences(false);

    if (!preferencesSaved) {
      return;
    }

    const data = await api<{ items: Recommendation[]; provider: string }>(
      "/api/v1/recommendations?limit=20",
    );

    setRecommendations(data.items);
    navigate("recomendacoes", true);

    if (data.provider === "gemini") {
      toast.success("Recomendações geradas com a inteligência artificial.");
    } else {
      toast.success("Recomendações geradas pelo sistema local.");
    }
  } catch (error) {
    toast.error(errorMessage(error));
  } finally {
    setRecommendationsLoading(false);
  }
}

  function togglePreference(domain: string) {
    setPreferredDomains((current) =>
      current.includes(domain) ? current.filter((item) => item !== domain) : [...current, domain],
    );
  }

  async function askAssistant(message: string) {
    const text = message.trim();
    if (!text) return;
    if (!user) {
      openAuth("login");
      return;
    }
    setAssistantSending(true);
    setAssistantMessage("");
    const userMessageId = temporaryMessageId.current;
    temporaryMessageId.current -= 1;
    const temporaryUserMessage: ChatMessage = {
      id: userMessageId,
      role: "user",
      content: text,
      sources: [],
      created_at: new Date().toISOString(),
    };
    setChatMessages((current) => [...current, temporaryUserMessage]);
    try {
      const data = await api<{
        answer: string;
        sources: ChatMessage["sources"];
        provider: string;
      }>("/api/v1/assistant/chat", {
        method: "POST",
        body: JSON.stringify({ message: text }),
      });
      setAssistantProvider(data.provider === "online" ? "online" : "local");
      setChatMessages((current) => [
        ...current,
        {
          id: temporaryMessageId.current--,
          role: "assistant",
          content: data.answer,
          sources: data.sources,
          created_at: new Date().toISOString(),
        },
      ]);
    } catch (error) {
      toast.error(errorMessage(error));
    } finally {
      setAssistantSending(false);
    }
  }

  async function sendAssistant(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await askAssistant(assistantMessage);
  }

  async function handleSuggestion(suggestion: string) {
    if (!navigate("assistente", true)) return;
    await askAssistant(suggestion);
  }

  async function openAssistantSource(contentId: number) {
    try {
      const content = contents.find((item) => item.id === contentId)
        ?? await api<Content>(`/api/v1/contents/${contentId}`);
      await openContentDetails(content);
    } catch (error) {
      toast.error(errorMessage(error));
    }
  }

  async function clearChat() {
    try {
      await api("/api/v1/assistant/history", { method: "DELETE" });
      setChatMessages([]);
      toast.success("Conversa limpa.");
    } catch (error) {
      toast.error(errorMessage(error));
    }
  }

  async function updateProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      const updated = await api<User>("/api/v1/auth/me", {
        method: "PATCH",
        body: JSON.stringify({ name: String(form.get("name")).trim(), avatar: profileAvatar }),
      });
      setUser(updated);
      toast.success("Perfil atualizado.");
    } catch (error) {
      toast.error(errorMessage(error));
    }
  }

  function openDomainDialog(domain: DomainRecord | null = null) {
    setEditingDomain(domain);
    setDomainActive(domain?.is_active ?? true);
    setDomainDialogOpen(true);
  }

  function openContentDialog(content: Content | null = null) {
    setEditingContent(content);
    setContentDomain(content?.domain ?? activeDomains[0]?.code ?? "filme");
    setContentPublished(content?.is_published ?? true);
    setContentDialogOpen(true);
  }

  async function saveDomain(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const payload = {
      ...(!editingDomain ? { code: String(form.get("code")).trim().toLowerCase() } : {}),
      name: String(form.get("name")).trim(),
      description: String(form.get("description")).trim(),
      is_active: domainActive,
    };
    try {
      await api(editingDomain ? `/api/v1/admin/domains/${editingDomain.id}` : "/api/v1/admin/domains", {
        method: editingDomain ? "PATCH" : "POST",
        body: JSON.stringify(payload),
      });
      setDomainDialogOpen(false);
      await Promise.all([loadAdmin(), loadDomains()]);
      toast.success(editingDomain ? "Domínio atualizado." : "Domínio criado.");
    } catch (error) {
      toast.error(errorMessage(error));
    }
  }

  async function saveContent(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const title = String(form.get("title")).trim();
    const requestedPrimaryImage = String(form.get("image_url")).trim();
    const additionalImages = String(form.get("gallery_images") ?? "")
      .split(/\r?\n/)
      .map((value) => value.trim())
      .filter(Boolean);
    const primaryImage = requestedPrimaryImage || additionalImages[0] || null;
    const galleryImages = Array.from(
      new Set([primaryImage, ...additionalImages].filter((value): value is string => Boolean(value))),
    );
    const modelUrl = String(form.get("model_url") ?? "").trim();
    const payload = {
      title,
      description: String(form.get("description")).trim(),
      domain: contentDomain,
      category: String(form.get("category")).trim(),
      image_url: primaryImage,
      external_url: String(form.get("external_url")).trim() || null,
      metadata: {
        ...(editingContent?.metadata ?? {}),
        images: galleryImages,
        model_url: contentDomain === "produto" && modelUrl ? modelUrl : null,
      },
      is_published: contentPublished,
      ...(!editingContent
        ? {
            source_name: "admin",
            external_id: `admin-${Date.now()}-${title.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`,
          }
        : {}),
    };
    try {
      await api(editingContent ? `/api/v1/contents/${editingContent.id}` : "/api/v1/contents", {
        method: editingContent ? "PATCH" : "POST",
        body: JSON.stringify(payload),
      });
      setContentDialogOpen(false);
      await Promise.all([loadAdmin(), loadContents(query, selectedDomain)]);
      toast.success(editingContent ? "Conteúdo atualizado." : "Conteúdo criado.");
    } catch (error) {
      toast.error(errorMessage(error));
    }
  }

  async function createAdminUser(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const password = String(form.get("password"));
    if (password !== String(form.get("confirm_password"))) {
      toast.error("As senhas não são iguais.");
      return;
    }
    try {
      await api<User>("/api/v1/admin/users", {
        method: "POST",
        body: JSON.stringify({
          name: String(form.get("name")).trim(),
          email: String(form.get("email")).trim(),
          password,
          role: newUserRole,
        }),
      });
      setUserDialogOpen(false);
      await loadAdmin();
      toast.success(newUserRole === "admin" ? "Administrador cadastrado." : "Usuário cadastrado.");
    } catch (error) {
      toast.error(errorMessage(error));
    }
  }

  async function updateAdminUser(target: User, values: Partial<Pick<User, "role" | "is_active">>) {
    try {
      await api(`/api/v1/admin/users/${target.id}`, {
        method: "PATCH",
        body: JSON.stringify(values),
      });
      await loadAdmin();
      toast.success("Conta atualizada.");
    } catch (error) {
      toast.error(errorMessage(error));
    }
  }

  async function performDelete() {
    if (!deleteTarget) return;
    const paths = {
      domain: `/api/v1/admin/domains/${deleteTarget.id}`,
      content: `/api/v1/contents/${deleteTarget.id}`,
      user: `/api/v1/admin/users/${deleteTarget.id}`,
    };
    try {
      await api(paths[deleteTarget.kind], { method: "DELETE" });
      setDeleteTarget(null);
      await Promise.all([loadAdmin(), loadDomains(), loadContents(query, selectedDomain)]);
      toast.success("Registro excluído.");
    } catch (error) {
      toast.error(errorMessage(error));
    }
  }

  const firstName = user?.name.split(" ")[0] ?? "visitante";

  function ContentCard({ content, index = 0 }: { content: Content; index?: number }) {
    const Icon = knownDomainIcons[content.domain as keyof typeof knownDomainIcons] ?? LayoutGrid;
    return (
      <button
        onClick={() => void openContentDetails(content)}
        className="group overflow-hidden rounded-2xl border border-[#315675] bg-[#0a2136] text-left shadow-lg shadow-black/10 transition duration-300 hover:-translate-y-1 hover:border-cyan-400 hover:shadow-cyan-950/40"
      >
        <div className={`relative h-40 overflow-hidden bg-gradient-to-br ${contentColors[index % contentColors.length]}`}>
          {content.image_url ? (
            <img
              src={content.image_url}
              alt={`Capa de ${content.title}`}
              className="h-full w-full object-cover transition duration-500 group-hover:scale-105"
            />
          ) : (
            <div className="absolute inset-0">
              <div className="absolute -right-8 -top-8 size-36 rounded-full border border-white/20" />
              <div className="absolute -bottom-12 right-8 size-32 rounded-full bg-white/10 blur-sm" />
              <Icon className="absolute left-5 top-5 size-10 text-white/90" />
              <span className="absolute bottom-4 right-5 text-5xl font-black text-white/10">
                {content.title.slice(0, 2).toUpperCase()}
              </span>
            </div>
          )}
          <div className="absolute inset-0 bg-gradient-to-t from-[#071b2d] via-transparent to-transparent" />
          <Badge className="absolute bottom-3 left-4 border border-white/20 bg-[#071b2d]/85 text-cyan-100 backdrop-blur">
            {labelForDomain(content.domain)}
          </Badge>
        </div>
        <div className="p-5">
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-cyan-300">{content.category}</p>
          <h3 className="mt-2 line-clamp-2 text-xl font-semibold text-white">{content.title}</h3>
          <p className="mt-3 line-clamp-2 min-h-10 text-sm leading-5 text-[#9fc3e5]">{content.description}</p>
          <div className="mt-5 flex items-center justify-between border-t border-[#20415f] pt-4 text-sm text-cyan-200">
            <span>Ver detalhes</span>
            <ArrowUpRight className="size-4 transition group-hover:-translate-y-0.5 group-hover:translate-x-0.5" />
          </div>
        </div>
      </button>
    );
  }

  function DomainSelector({ generate = false }: { generate?: boolean }) {
    return (
      <section className="rounded-3xl border border-[#20415f] bg-[#0a2136] p-6">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div>
            <h2 className="text-2xl font-semibold">Seus interesses</h2>
            <p className="mt-2 text-[#9fc3e5]">Escolha os domínios que devem influenciar as recomendações.</p>
          </div>
          {generate && (
           <Button
  onClick={() => void loadRecommendations()}
  disabled={recommendationsLoading}
  className="bg-[#267ef0] hover:bg-[#1f69c9] disabled:cursor-not-allowed disabled:opacity-70"
>
  {recommendationsLoading ? (
    <Loader2 className="animate-spin" />
  ) : (
    <Sparkles />
  )}

  {recommendationsLoading
    ? "Gerando..."
    : "Gerar recomendações"}
</Button>
          )}
        </div>
        <div className="mt-5 flex flex-wrap gap-3">
          {activeDomains.map((domain) => {
            const Icon = knownDomainIcons[domain.code as keyof typeof knownDomainIcons] ?? LayoutGrid;
            const active = preferredDomains.includes(domain.code);
            return (
              <button
                key={domain.code}
                onClick={() => togglePreference(domain.code)}
                className={`flex items-center gap-2 rounded-full border px-4 py-2 text-sm transition ${active ? "border-cyan-300 bg-cyan-300 text-[#041728]" : "border-[#315675] text-[#b9d3e9] hover:border-cyan-500"}`}
              >
                {active ? <Check className="size-4" /> : <Icon className="size-4" />}
                {domain.name}
              </button>
            );
          })}
        </div>
        {!generate && (
          <Button variant="outline" onClick={() => void savePreferences()} className="mt-5 border-[#315675] bg-transparent text-white hover:bg-[#17334b] hover:text-white">
            <Save /> Salvar preferências
          </Button>
        )}
      </section>
    );
  }

  function HomeScreen() {
    return (
      <div className="space-y-8">
        <div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-center">
          <PageTitle title={`Olá, ${firstName}`} description="Descubra conteúdos escolhidos para você" />
          {user ? (
            <button onClick={() => navigate("perfil", true)} className="flex items-center gap-3 rounded-2xl border border-[#20415f] bg-[#0b2237] px-4 py-3 text-left">
              <span className="grid size-12 place-items-center rounded-full bg-[#208ee8] text-2xl">{avatarEmoji(user.avatar)}</span>
              <span><strong className="block">{user.name}</strong><small className="text-[#9fc3e5]">{user.role === "admin" ? "Administrador" : "Usuário"}</small></span>
            </button>
          ) : (
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => openAuth("login")} className="border-[#275277] bg-transparent text-white hover:bg-[#0d2a43] hover:text-white">Entrar</Button>
              <Button onClick={() => openAuth("register")} className="bg-[#267ef0] hover:bg-[#1f69c9]">Criar conta</Button>
            </div>
          )}
        </div>

        <form
          className="flex overflow-hidden rounded-2xl border border-[#20415f] bg-[#0a2136]"
          onSubmit={(event) => {
            event.preventDefault();
            setSelectedDomain("");
            navigate("catalogo");
            void loadContents(query, "");
          }}
        >
          <div className="flex flex-1 items-center gap-4 px-5"><Search className="size-5 text-[#76a7d1]" /><Input value={query} onChange={(event) => setQuery(event.target.value)} className="h-16 border-0 bg-transparent text-lg shadow-none placeholder:text-[#76a7d1] focus-visible:ring-0" placeholder="Buscar filmes, músicas, livros, cursos ou produtos" /></div>
          <Button type="submit" className="h-16 rounded-none bg-[#267ef0] px-8 text-base font-bold hover:bg-[#1e68ca]">Buscar</Button>
        </form>

        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
          {activeDomains.map((domain) => {
            const Icon = knownDomainIcons[domain.code as keyof typeof knownDomainIcons] ?? LayoutGrid;
            return <button key={domain.code} onClick={() => { setSelectedDomain(domain.code); navigate("catalogo"); void loadContents("", domain.code); }} className="flex items-center gap-3 rounded-2xl border border-[#20415f] bg-[#0a2136] px-5 py-4 text-left transition hover:border-[#3474a8]"><Icon className="size-5 text-cyan-300" />{domain.name}</button>;
          })}
        </div>

        <div className="grid gap-7 xl:grid-cols-[minmax(0,1fr)_405px]">
          <div className="space-y-8">
            <section className="overflow-hidden rounded-3xl border border-[#20415f] bg-[#0a2136]">
              {featured ? (
                <div className="grid lg:grid-cols-[1.25fr_.9fr]">
                  <button onClick={() => void openContentDetails(featured)} className="group relative min-h-[330px] overflow-hidden border-b border-[#20415f] bg-[radial-gradient(circle_at_74%_35%,rgba(251,191,36,.42),transparent_11%),radial-gradient(circle_at_45%_53%,rgba(47,140,255,.24),transparent_18%),linear-gradient(145deg,#0b2945,#0b2036_55%,#143e63)] text-left lg:border-b-0 lg:border-r">
                    {featured.image_url ? <img src={featured.image_url} alt={`Capa de ${featured.title}`} className="absolute inset-0 h-full w-full object-cover opacity-70 transition duration-500 group-hover:scale-105" /> : <div className="absolute inset-0 opacity-50 [background-image:radial-gradient(circle,rgba(255,255,255,.9)_1px,transparent_1px)] [background-size:42px_42px]" />}
                    <div className="absolute inset-0 bg-gradient-to-t from-[#061827] via-[#061827]/20 to-transparent" />
                    <div className="relative flex h-full min-h-[330px] flex-col justify-between p-7"><Badge className="w-fit border border-blue-400/50 bg-blue-500/20 text-blue-100 hover:bg-blue-500/20"><Sparkles className="mr-1 size-3" /> Destaque</Badge><div><p className="text-sm text-cyan-200">Clique para conhecer</p><p className="mt-2 max-w-lg text-3xl font-semibold group-hover:text-cyan-200">{featured.title}</p></div></div>
                  </button>
                  <div className="flex flex-col justify-center p-7"><Badge variant="outline" className="w-fit border-blue-500 text-blue-200">{labelForDomain(featured.domain)}</Badge><h2 className="mt-6 text-4xl font-light tracking-tight">{featured.title}</h2><div className="mt-5 flex items-center gap-2 text-amber-300"><span>★★★★★</span><span className="text-[#9fc3e5]">4,7</span></div><p className="mt-6 leading-7 text-[#b9d3e9]">{featuredReason ?? featured.description}</p><Button onClick={() => navigate("recomendacoes", true)} className="mt-7 bg-[#267ef0]">Ver recomendações</Button></div>
                </div>
              ) : <div className="p-12 text-center text-[#9fc3e5]">Nenhum conteúdo encontrado.</div>}
            </section>
            <section><div className="flex items-center justify-between"><h2 className="text-2xl font-semibold">Explore o catálogo</h2><button onClick={() => navigate("catalogo")} className="flex items-center gap-1 text-cyan-300">Ver todos <ChevronRight className="size-4" /></button></div><div className="mt-5 grid gap-4 sm:grid-cols-2 2xl:grid-cols-5">{contents.slice(0, 5).map((content, index) => <ContentCard key={content.id} content={content} index={index} />)}</div></section>
          </div>
          <aside className="h-fit rounded-3xl border border-[#20415f] bg-[#0a2136] p-5">
            <div className="flex items-center gap-3 border-b border-[#20415f] pb-5"><Sparkles className="text-cyan-300" /><div><h2 className="text-2xl font-semibold">Assistente IA</h2><p className="mt-1 text-sm text-[#9fc3e5]">Conversa usando o catálogo e seu histórico</p></div></div>
            <div className="my-5 rounded-2xl border border-[#315675] bg-[#0d2941] p-4 text-sm leading-6 text-[#d3e2ef]">Posso indicar, comparar e continuar a conversa levando em conta o que você já escolheu.</div>
            {["Comparar dois filmes", "Indicar um livro", "Sugerir um curso"].map((suggestion) => <button key={suggestion} onClick={() => void handleSuggestion(suggestion)} className="mb-2 flex w-full items-center justify-between rounded-xl border border-cyan-800 px-4 py-3 text-left text-sm text-cyan-200 hover:bg-cyan-950/50">{suggestion}<ChevronRight className="size-4" /></button>)}
          </aside>
        </div>
      </div>
    );
  }

  function CatalogScreen() {
    return (
      <div className="space-y-7">
        <PageTitle title="Catálogo" description="Explore todos os conteúdos disponíveis nos diferentes domínios." />
        <form className="flex overflow-hidden rounded-2xl border border-[#20415f] bg-[#0a2136]" onSubmit={(event) => { event.preventDefault(); void loadContents(query, selectedDomain); }}><div className="flex flex-1 items-center gap-4 px-5"><Search className="text-[#76a7d1]" /><Input value={query} onChange={(event) => setQuery(event.target.value)} className="h-14 border-0 bg-transparent shadow-none focus-visible:ring-0" placeholder="Digite um título, tema ou categoria" /></div><Button type="submit" className="h-14 rounded-none bg-[#267ef0] px-7">Buscar</Button></form>
        <div className="flex flex-wrap gap-3"><button onClick={() => { setSelectedDomain(""); void loadContents(query, ""); }} className={`rounded-full border px-4 py-2 text-sm ${!selectedDomain ? "border-cyan-300 bg-cyan-300 text-[#041728]" : "border-[#315675]"}`}>Todos</button>{activeDomains.map((domain) => <button key={domain.code} onClick={() => { setSelectedDomain(domain.code); void loadContents(query, domain.code); }} className={`rounded-full border px-4 py-2 text-sm ${selectedDomain === domain.code ? "border-cyan-300 bg-cyan-300 text-[#041728]" : "border-[#315675]"}`}>{domain.name}</button>)}</div>
        {loading ? <div className="h-72 animate-pulse rounded-3xl bg-[#102b44]" /> : <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">{contents.map((content, index) => <ContentCard key={content.id} content={content} index={index} />)}</div>}
      </div>
    );
  }

  function ContentDetailsScreen() {
    if (!selectedContent) {
      return (
        <div className="rounded-3xl border border-dashed border-[#315675] p-12 text-center">
          <p className="text-[#9fc3e5]">Nenhum conteúdo foi selecionado.</p>
          <Button onClick={() => navigate("catalogo")} className="mt-5 bg-[#267ef0]">Abrir catálogo</Button>
        </div>
      );
    }

    const content = selectedContent;
    const Icon = knownDomainIcons[content.domain as keyof typeof knownDomainIcons] ?? LayoutGrid;
    const galleryImages = getGalleryImages(content);
    const modelUrl = content.domain === "produto"
      ? getMetadataString(content.metadata ?? {}, "model_url")
      : null;
    const currentImage = galleryImages[galleryIndex] ?? null;
    const metadata = Object.entries(content.metadata ?? {}).filter(
      ([key, value]) => !["images", "model_url"].includes(key) && value !== null && value !== "",
    );
    const recommendationReason = recommendations.find((item) => item.content.id === content.id)?.reason;
    const liked = relevantIds.has(content.id);
    const selectedRating = ratings[content.id] ?? 0;
    const similar = contents
      .filter((item) => item.id !== content.id && item.domain === content.domain)
      .slice(0, 4);

    return (
      <div className="space-y-8">
        <Button
          variant="ghost"
          onClick={() => {
            if (window.history.state?.rmView === "detalhes") {
              window.history.back();
            } else {
              navigate(detailsReturnView === "detalhes" ? "catalogo" : detailsReturnView);
            }
          }}
          className="text-[#b9d3e9] hover:bg-[#0c2b46] hover:text-white"
        >
          <ArrowLeft /> Voltar
        </Button>

        <article className="overflow-hidden rounded-3xl border border-[#20415f] bg-[#0a2136]">
          <div className="grid lg:grid-cols-[minmax(360px,.9fr)_1.1fr]">
            <div className="border-b border-[#20415f] lg:border-b-0 lg:border-r">
              <div className={`relative min-h-[420px] overflow-hidden bg-gradient-to-br ${contentColors[content.id % contentColors.length]}`}>
                {detailsMediaMode === "3d" && modelUrl ? (
                  <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_35%,#244d70,#071b2d_70%)]">
                    <model-viewer
                      src={modelUrl}
                      alt={`Modelo 3D de ${content.title}`}
                      camera-controls
                      auto-rotate
                      rotation-per-second="20deg"
                      shadow-intensity="1"
                      environment-image="neutral"
                      exposure="1"
                      interaction-prompt="auto"
                      touch-action="pan-y"
                      loading="eager"
                      className="h-full min-h-[420px] w-full"
                    />
                    <p className="pointer-events-none absolute bottom-5 left-1/2 -translate-x-1/2 whitespace-nowrap rounded-full bg-[#041728]/85 px-4 py-2 text-xs text-cyan-100 backdrop-blur">
                      Arraste para girar · use a roda para aproximar
                    </p>
                  </div>
                ) : currentImage ? (
                  <img
                    src={currentImage}
                    alt={`${content.title} — imagem ${galleryIndex + 1}`}
                    className={`absolute inset-0 h-full w-full ${content.domain === "produto" ? "object-contain p-7" : "object-cover"}`}
                  />
                ) : (
                  <>
                    <div className="absolute -left-20 top-16 size-64 rounded-full border border-white/15" />
                    <div className="absolute -bottom-20 right-0 size-72 rounded-full bg-white/10 blur-md" />
                    <Icon className="absolute left-8 top-8 size-16 text-white/90" />
                    <span className="absolute bottom-8 right-8 text-8xl font-black text-white/10">{content.title.slice(0, 2).toUpperCase()}</span>
                  </>
                )}

                {detailsMediaMode === "images" && <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-[#071b2d]/80 via-transparent to-transparent" />}

                {detailsMediaMode === "images" && galleryImages.length > 1 && (
                  <>
                    <button
                      type="button"
                      onClick={() => setGalleryIndex((current) => (current - 1 + galleryImages.length) % galleryImages.length)}
                      className="absolute left-4 top-1/2 grid size-11 -translate-y-1/2 place-items-center rounded-full border border-white/25 bg-[#041728]/80 text-white backdrop-blur transition hover:bg-[#174b7b]"
                      aria-label="Imagem anterior"
                    >
                      <ChevronLeft />
                    </button>
                    <button
                      type="button"
                      onClick={() => setGalleryIndex((current) => (current + 1) % galleryImages.length)}
                      className="absolute right-4 top-1/2 grid size-11 -translate-y-1/2 place-items-center rounded-full border border-white/25 bg-[#041728]/80 text-white backdrop-blur transition hover:bg-[#174b7b]"
                      aria-label="Próxima imagem"
                    >
                      <ChevronRight />
                    </button>
                    <span className="absolute bottom-7 left-1/2 -translate-x-1/2 rounded-full bg-[#041728]/80 px-3 py-1 text-xs text-white backdrop-blur">
                      {galleryIndex + 1} / {galleryImages.length}
                    </span>
                  </>
                )}

                {modelUrl && (
                  <button
                    type="button"
                    onClick={() => setDetailsMediaMode((current) => current === "3d" ? "images" : "3d")}
                    className="absolute right-5 top-5 flex items-center gap-2 rounded-xl border border-cyan-300/60 bg-[#041728]/90 px-4 py-2.5 text-sm font-semibold text-cyan-100 shadow-lg backdrop-blur transition hover:bg-[#174b7b]"
                  >
                    {detailsMediaMode === "3d" ? <Images className="size-4" /> : <Rotate3D className="size-4" />}
                    {detailsMediaMode === "3d" ? "Ver imagens" : "Opção 3D"}
                  </button>
                )}

                {detailsMediaMode === "images" && (
                  <Badge className="absolute bottom-7 left-7 border border-white/20 bg-[#071b2d]/80 text-cyan-100 backdrop-blur">
                    <Icon className="mr-1 size-3" /> {labelForDomain(content.domain)}
                  </Badge>
                )}
              </div>

              {detailsMediaMode === "images" && galleryImages.length > 1 && (
                <div className="flex gap-3 overflow-x-auto bg-[#071b2d] p-3">
                  {galleryImages.map((image, index) => (
                    <button
                      type="button"
                      key={`${image}-${index}`}
                      onClick={() => setGalleryIndex(index)}
                      className={`h-16 w-20 shrink-0 overflow-hidden rounded-lg border-2 transition ${galleryIndex === index ? "border-cyan-300" : "border-[#315675] opacity-65 hover:opacity-100"}`}
                      aria-label={`Abrir imagem ${index + 1}`}
                    >
                      <img src={image} alt="" className="h-full w-full object-cover" />
                    </button>
                  ))}
                </div>
              )}
            </div>

            <div className="p-7 sm:p-9">
              <p className="text-sm font-semibold uppercase tracking-[0.2em] text-cyan-300">{content.category}</p>
              <h1 className="mt-3 text-4xl font-light tracking-tight sm:text-5xl">{content.title}</h1>
              <p className="mt-6 text-lg leading-8 text-[#c4d6e8]">{content.description}</p>

              {recommendationReason && (
                <div className="mt-6 rounded-2xl border border-cyan-800 bg-cyan-950/30 p-4">
                  <div className="flex gap-3"><Sparkles className="mt-0.5 size-5 shrink-0 text-cyan-300" /><div><p className="font-semibold text-cyan-100">Por que apareceu para você</p><p className="mt-1 text-sm leading-6 text-[#b9d3e9]">{recommendationReason}</p></div></div>
                </div>
              )}

              {metadata.length > 0 && (
                <dl className="mt-7 grid gap-3 sm:grid-cols-2">
                  {metadata.map(([key, value]) => (
                    <div key={key} className="rounded-xl border border-[#315675] bg-[#071b2d] px-4 py-3">
                      <dt className="text-xs uppercase tracking-wider text-[#76a7d1]">{metadataLabel(key)}</dt>
                      <dd className="mt-1 font-medium capitalize">{metadataValue(key, value)}</dd>
                    </div>
                  ))}
                </dl>
              )}

              <div className="mt-7 border-t border-[#20415f] pt-6">
                <p className="text-sm font-medium text-[#b9d3e9]">Sua avaliação</p>
                <div className="mt-2 flex gap-1" aria-label="Avaliação de uma a cinco estrelas">
                  {[1, 2, 3, 4, 5].map((value) => (
                    <button key={value} onClick={() => void rateContent(content.id, value)} aria-label={`Avaliar com ${value} estrela${value > 1 ? "s" : ""}`} className="rounded p-1 hover:bg-amber-400/10">
                      <Star className={`size-7 ${value <= selectedRating ? "fill-amber-300 text-amber-300" : "text-[#557a9a]"}`} />
                    </button>
                  ))}
                </div>
              </div>

              <div className="mt-7 flex flex-wrap gap-3">
                <Button onClick={() => void openExternalContent(content)} className="bg-[#267ef0] hover:bg-[#1f69c9]">
                  <ArrowUpRight /> Acessar conteúdo
                </Button>
                <Button variant="outline" onClick={() => void saveFeedback(content.id, !liked)} className={`border-[#315675] bg-transparent text-white hover:text-white ${liked ? "border-rose-400 bg-rose-500/15 text-rose-200" : "hover:bg-[#17334b]"}`}>
                  <Heart className={liked ? "fill-rose-500 text-rose-500" : ""} /> {liked ? "Relevante" : "Marcar como relevante"}
                </Button>
              </div>
            </div>
          </div>
        </article>

        {similar.length > 0 && (
          <section>
            <div className="flex items-end justify-between gap-4"><div><h2 className="text-2xl font-semibold">Conteúdos semelhantes</h2><p className="mt-2 text-[#9fc3e5]">Outras opções do domínio {labelForDomain(content.domain).toLowerCase()}.</p></div><Button variant="ghost" onClick={() => { setSelectedDomain(content.domain); navigate("catalogo"); void loadContents("", content.domain); }} className="text-cyan-300">Ver todos <ChevronRight /></Button></div>
            <div className="mt-5 grid gap-5 sm:grid-cols-2 xl:grid-cols-4">{similar.map((item, index) => <ContentCard key={item.id} content={item} index={index} />)}</div>
          </section>
        )}
      </div>
    );
  }

  function RecommendationsScreen() {
    return (
      <div className="space-y-7">
        <PageTitle title="Recomendações" description="As escolhas mudam conforme seus interesses, acessos e avaliações." />
        <DomainSelector generate />
        {recommendations.length ? <div className="grid gap-5 lg:grid-cols-2">{recommendations.map(({ content, reason }, index) => { const liked = relevantIds.has(content.id); return <article key={content.id} className="rounded-3xl border border-[#20415f] bg-[#0a2136] p-6"><div className="flex items-start justify-between gap-4"><div><Badge className="bg-blue-600">{labelForDomain(content.domain)}</Badge><h2 className="mt-4 text-2xl font-semibold">{content.title}</h2><p className="mt-2 text-sm text-[#9fc3e5]">{content.category}</p></div><span className="text-3xl font-light text-cyan-300">{index + 1}</span></div><p className="mt-5 leading-7 text-[#c4d6e8]">{reason}</p><div className="mt-6 flex flex-wrap gap-3"><Button variant="outline" onClick={() => void saveFeedback(content.id, true)} className={`border-blue-500 bg-transparent text-white hover:text-white ${liked ? "bg-rose-500/20 text-rose-200" : "hover:bg-blue-500/20"}`}><Heart className={liked ? "fill-rose-500 text-rose-500" : ""} /> Relevante</Button><Button variant="outline" onClick={() => void saveFeedback(content.id, false)} className="border-[#315675] bg-transparent text-white hover:bg-[#17334b] hover:text-white"><X /> Não relevante</Button><Button onClick={() => void openContentDetails(content)} className="bg-[#267ef0]">Ver detalhes</Button></div></article>; })}</div> : <div className="rounded-3xl border border-dashed border-[#315675] p-12 text-center"><Sparkles className="mx-auto size-10 text-cyan-300" /><h2 className="mt-4 text-2xl font-semibold">Pronto para descobrir algo novo?</h2><p className="mt-2 text-[#9fc3e5]">Escolha seus domínios acima e clique em Gerar recomendações.</p></div>}
      </div>
    );
  }

  function AssistantScreen() {
    const suggestions = [
      "Quero um filme de ficção científica",
      "Indique um livro de fantasia",
      "Sugira um curso para iniciantes",
      "Quero uma música tranquila",
    ];
    return (
      <div className="grid gap-7 xl:grid-cols-[minmax(0,1fr)_340px]">
        <section className="overflow-hidden rounded-3xl border border-[#20415f] bg-[#0a2136]">
          <div className="flex items-center justify-between border-b border-[#20415f] p-6">
            <div className="flex items-center gap-3">
              <span className="grid size-11 place-items-center rounded-2xl bg-cyan-400/15"><Bot className="text-cyan-300" /></span>
              <div><h1 className="text-2xl font-semibold">Assistente IA</h1><div className="mt-1 flex items-center gap-2"><span className={`size-2 rounded-full ${assistantProvider === "online" ? "bg-emerald-400" : "bg-cyan-300"}`} /><p className="text-sm text-[#9fc3e5]">{assistantProvider === "online" ? "IA online conectada" : "Assistente local usando o catálogo"}</p></div></div>
            </div>
            {chatMessages.length > 0 && <Button variant="ghost" onClick={() => void clearChat()} className="text-[#9fc3e5]">Limpar</Button>}
          </div>
          <div className="h-[52vh] min-h-[420px] space-y-4 overflow-y-auto p-5 sm:p-7">
            {chatMessages.length === 0 && <div className="mx-auto mt-20 max-w-md text-center"><Sparkles className="mx-auto size-11 text-cyan-300" /><h2 className="mt-4 text-xl font-semibold">O que você gostaria de descobrir?</h2><p className="mt-2 text-[#9fc3e5]">Eu converso, consulto o catálogo e considero suas preferências e mensagens anteriores.</p></div>}
            {chatMessages.map((message) => (
              <div key={`${message.id}-${message.created_at}`} className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}>
                <div className={`max-w-[85%] rounded-2xl px-5 py-4 text-sm leading-6 ${message.role === "user" ? "bg-[#267ef0] text-white" : "border border-[#315675] bg-[#0d2941] text-[#d3e2ef]"}`}>
                  <p className="whitespace-pre-line">{message.content}</p>
                  {message.sources.length > 0 && <div className="mt-3 flex flex-wrap gap-2">{message.sources.map((source) => <button key={`${message.id}-${source.content_id}`} onClick={() => void openAssistantSource(source.content_id)} className="rounded-full border border-cyan-800 px-3 py-1 text-xs text-cyan-200 transition hover:border-cyan-400 hover:bg-cyan-950/60">{source.title} <ArrowUpRight className="ml-1 inline size-3" /></button>)}</div>}
                </div>
              </div>
            ))}
            {assistantSending && <div className="w-fit animate-pulse rounded-2xl border border-[#315675] bg-[#0d2941] px-5 py-4 text-sm text-[#9fc3e5]">Analisando sua pergunta e o catálogo...</div>}
            <div ref={chatEndRef} />
          </div>
          <form onSubmit={sendAssistant} className="flex gap-3 border-t border-[#20415f] p-5"><Input value={assistantMessage} onChange={(event) => setAssistantMessage(event.target.value)} placeholder="Pergunte, compare ou peça outra opção" className="h-12 border-[#315675] bg-[#061827]" autoComplete="off" /><Button type="submit" disabled={assistantSending || assistantMessage.trim().length < 2} className="h-12 bg-[#267ef0]"><Send /><span className="hidden sm:inline">Enviar</span></Button></form>
        </section>
        <aside className="h-fit rounded-3xl border border-[#20415f] bg-[#0a2136] p-5"><h2 className="font-semibold">Sugestões para você</h2><p className="mt-2 text-sm text-[#9fc3e5]">Clique e a pergunta será enviada na hora.</p><div className="mt-5 space-y-3">{suggestions.map((suggestion) => <button key={suggestion} disabled={assistantSending} onClick={() => void askAssistant(suggestion)} className="flex w-full items-center justify-between rounded-xl border border-cyan-800 px-4 py-3 text-left text-sm text-cyan-200 transition hover:bg-cyan-950/50 disabled:cursor-not-allowed disabled:opacity-50">{suggestion}<ChevronRight className="size-4" /></button>)}</div><div className="mt-5 rounded-xl border border-[#315675] bg-[#071b2d] p-4 text-xs leading-5 text-[#76a7d1]">Experimente continuar a conversa com “quero outra opção”, “algo mais leve” ou “compare os dois primeiros”.</div></aside>
      </div>
    );
  }

  function HistoryScreen() {
    const names: Record<string, string> = { view: "Visualizou", click: "Acessou", rating: "Avaliou", recommendation: "Recebeu recomendação" };
    return <div className="space-y-7"><PageTitle title="Histórico" description="Veja como suas ações estão ajudando a personalizar as recomendações." />{history.length ? <div className="space-y-3">{history.map((item) => <article key={item.id} className="flex items-center gap-4 rounded-2xl border border-[#20415f] bg-[#0a2136] p-5"><span className="grid size-11 shrink-0 place-items-center rounded-xl bg-[#173c5f]"><Clock3 className="size-5 text-cyan-300" /></span><div className="min-w-0 flex-1"><p className="font-semibold">{names[item.interaction_type] ?? item.interaction_type}: {item.content?.title ?? `Conteúdo ${item.content_id}`}</p><p className="mt-1 text-sm text-[#9fc3e5]">{item.content ? `${labelForDomain(item.content.domain)} · ${item.content.category}` : "Registro salvo"}</p></div><time className="hidden text-sm text-[#76a7d1] sm:block">{formatDate(item.created_at)}</time></article>)}</div> : <div className="rounded-3xl border border-dashed border-[#315675] p-12 text-center text-[#9fc3e5]">Seu histórico aparecerá depois que você abrir conteúdos e gerar recomendações.</div>}</div>;
  }

  function ProfileScreen() {
    if (!user) return null;
    return <div className="space-y-7"><PageTitle title="Perfil" description="Atualize seu nome, escolha um avatar e ajuste seus interesses." /><div className="grid gap-7 xl:grid-cols-[380px_minmax(0,1fr)]"><form onSubmit={updateProfile} className="rounded-3xl border border-[#20415f] bg-[#0a2136] p-6"><div className="mx-auto grid size-28 place-items-center rounded-full border-4 border-[#267ef0] bg-[#102b44] text-6xl">{avatarEmoji(profileAvatar)}</div><label className="mt-7 grid gap-2 text-sm">Nome<Input name="name" defaultValue={user.name} minLength={2} required className="h-12 border-[#315675] bg-[#061827]" /></label><label className="mt-4 grid gap-2 text-sm text-[#9fc3e5]">E-mail<Input value={user.email} disabled className="h-12 border-[#315675] bg-[#061827]" /></label><Button type="submit" className="mt-5 w-full bg-[#267ef0]"><Save /> Salvar perfil</Button></form><section className="rounded-3xl border border-[#20415f] bg-[#0a2136] p-6"><h2 className="text-2xl font-semibold">Escolha seu avatar</h2><p className="mt-2 text-[#9fc3e5]">Você pode trocar sempre que quiser.</p><div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">{avatarOptions.map((avatar) => <button key={avatar.id} onClick={() => setProfileAvatar(avatar.id)} className={`rounded-2xl border p-4 text-center transition ${profileAvatar === avatar.id ? "border-cyan-300 bg-cyan-300/10" : "border-[#315675] hover:border-cyan-700"}`}><span className="block text-4xl">{avatar.emoji}</span><span className="mt-2 block text-sm">{avatar.label}</span></button>)}</div></section></div><DomainSelector /></div>;
  }

  function AdminScreen() {
    const adminTabClass = "px-4 py-2.5 text-white hover:text-white data-[state=active]:bg-white data-[state=active]:text-[#061827]";
    return <div className="space-y-7"><PageTitle title="Administração" description="Gerencie os registros do sistema em uma área separada." /><Tabs value={adminTab} onValueChange={(value) => setAdminTab(value as AdminTab)}><TabsList className="h-auto flex-wrap border border-[#20415f] bg-[#0a2136] p-1"><TabsTrigger value="registro" className={adminTabClass}><Database /> Registro de dados</TabsTrigger><TabsTrigger value="dominios" className={adminTabClass}><LayoutGrid /> Domínios</TabsTrigger><TabsTrigger value="conteudos" className={adminTabClass}><BookOpen /> Conteúdos</TabsTrigger><TabsTrigger value="usuarios" className={adminTabClass}><Users /> Usuários</TabsTrigger></TabsList>
      <TabsContent value="registro" className="mt-6"><section className="rounded-3xl border border-[#20415f] bg-[#0a2136] p-6"><div><h2 className="text-2xl font-semibold">Registro de dados</h2><p className="mt-2 text-[#9fc3e5]">Resumo dos registros salvos e usados pelo sistema.</p></div><div className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-5">{[["Usuários", statistics?.users ?? 0], ["Ativos", statistics?.active_users ?? 0], ["Conteúdos", statistics?.contents ?? 0], ["Interações", statistics?.interactions ?? 0], ["Feedbacks", statistics?.feedbacks ?? 0]].map(([label, value]) => <div key={String(label)} className="rounded-2xl border border-[#315675] bg-[#102b44] p-5"><p className="text-sm text-[#9fc3e5]">{label}</p><p className="mt-2 text-4xl font-light">{value}</p></div>)}</div><div className="mt-7 grid gap-5 lg:grid-cols-2"><div className="rounded-2xl border border-[#315675] p-5"><h3 className="font-semibold">Conteúdos por domínio</h3><div className="mt-4 space-y-3">{Object.entries(statistics?.contents_by_domain ?? {}).map(([code, total]) => <div key={code} className="flex justify-between text-sm"><span className="text-[#b9d3e9]">{labelForDomain(code)}</span><strong>{total}</strong></div>)}</div></div><div className="rounded-2xl border border-[#315675] p-5"><h3 className="font-semibold">Interações por tipo</h3><div className="mt-4 space-y-3">{Object.entries(statistics?.interactions_by_type ?? {}).map(([kind, total]) => <div key={kind} className="flex justify-between text-sm"><span className="capitalize text-[#b9d3e9]">{kind}</span><strong>{total}</strong></div>)}</div></div></div></section></TabsContent>
      <TabsContent value="dominios" className="mt-6"><div className="mb-5 flex items-center justify-between"><div><h2 className="text-2xl font-semibold">Domínios</h2><p className="mt-1 text-[#9fc3e5]">Crie, edite, ative ou exclua domínios sem alterar o design.</p></div><Button onClick={() => openDomainDialog()} className="bg-[#267ef0]"><Plus /> Novo domínio</Button></div><div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{adminDomains.map((domain) => <article key={domain.id} className="rounded-2xl border border-[#20415f] bg-[#0a2136] p-5"><div className="flex items-start justify-between"><div><Badge className={domain.is_active ? "bg-emerald-600" : "bg-slate-600"}>{domain.is_active ? "Ativo" : "Inativo"}</Badge><h3 className="mt-3 text-xl font-semibold">{domain.name}</h3><code className="text-xs text-cyan-300">{domain.code}</code></div><LayoutGrid className="text-cyan-300" /></div><p className="mt-4 min-h-12 text-sm text-[#9fc3e5]">{domain.description || "Sem descrição."}</p><div className="mt-5 flex gap-2"><Button variant="outline" onClick={() => openDomainDialog(domain)} className="border-[#315675] bg-transparent text-white"><Pencil /> Editar</Button><Button variant="ghost" onClick={() => setDeleteTarget({ kind: "domain", id: domain.id, label: domain.name })} className="text-rose-300 hover:bg-rose-500/10 hover:text-rose-200"><Trash2 /></Button></div></article>)}</div></TabsContent>
      <TabsContent value="conteudos" className="mt-6"><div className="mb-5 flex items-center justify-between"><div><h2 className="text-2xl font-semibold">Conteúdos</h2><p className="mt-1 text-[#9fc3e5]">Gerencie itens de todos os domínios.</p></div><Button onClick={() => openContentDialog()} className="bg-[#267ef0]"><Plus /> Novo conteúdo</Button></div><div className="overflow-hidden rounded-2xl border border-[#20415f]"><div className="overflow-x-auto"><table className="w-full min-w-[760px] text-left text-sm"><thead className="bg-[#102b44] text-[#9fc3e5]"><tr><th className="p-4">Título</th><th className="p-4">Domínio</th><th className="p-4">Categoria</th><th className="p-4">Status</th><th className="p-4 text-right">Ações</th></tr></thead><tbody>{adminContents.map((content) => <tr key={content.id} className="border-t border-[#20415f] bg-[#0a2136]"><td className="p-4 font-medium">{content.title}</td><td className="p-4">{labelForDomain(content.domain)}</td><td className="p-4 text-[#9fc3e5]">{content.category}</td><td className="p-4"><Badge className={content.is_published ? "bg-emerald-600" : "bg-slate-600"}>{content.is_published ? "Publicado" : "Rascunho"}</Badge></td><td className="p-4"><div className="flex justify-end gap-2"><Button size="icon" variant="ghost" onClick={() => openContentDialog(content)}><Pencil /></Button><Button size="icon" variant="ghost" onClick={() => setDeleteTarget({ kind: "content", id: content.id, label: content.title })} className="text-rose-300"><Trash2 /></Button></div></td></tr>)}</tbody></table></div></div></TabsContent>
      <TabsContent value="usuarios" className="mt-6"><div className="mb-5 flex items-center justify-between"><div><h2 className="text-2xl font-semibold">Usuários</h2><p className="mt-1 text-[#9fc3e5]">Somente um administrador pode cadastrar outro administrador.</p></div><Button onClick={() => setUserDialogOpen(true)} className="bg-[#267ef0]"><Plus /> Nova conta</Button></div><div className="grid gap-4 lg:grid-cols-2">{users.map((account) => <article key={account.id} className="flex items-center gap-4 rounded-2xl border border-[#20415f] bg-[#0a2136] p-5"><span className="grid size-12 place-items-center rounded-full bg-[#173c5f] text-2xl">{avatarEmoji(account.avatar)}</span><div className="min-w-0 flex-1"><h3 className="truncate font-semibold">{account.name}</h3><p className="truncate text-sm text-[#9fc3e5]">{account.email}</p></div><div className="flex items-center gap-3"><Select value={account.role} onValueChange={(role) => void updateAdminUser(account, { role: role as "user" | "admin" })} disabled={account.id === user?.id}><SelectTrigger className="w-36 border-[#315675] bg-[#061827]"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="user">Usuário</SelectItem><SelectItem value="admin">Administrador</SelectItem></SelectContent></Select><Switch checked={account.is_active} onCheckedChange={(active) => void updateAdminUser(account, { is_active: active })} disabled={account.id === user?.id} aria-label={`Ativar ${account.name}`} />{account.id !== user?.id && <Button size="icon" variant="ghost" onClick={() => setDeleteTarget({ kind: "user", id: account.id, label: account.name })} className="text-rose-300"><Trash2 /></Button>}</div></article>)}</div></TabsContent>
    </Tabs></div>;
  }

  const screens: Record<View, () => React.JSX.Element | null> = {
    inicio: HomeScreen,
    catalogo: CatalogScreen,
    detalhes: ContentDetailsScreen,
    recomendacoes: RecommendationsScreen,
    assistente: AssistantScreen,
    historico: HistoryScreen,
    perfil: ProfileScreen,
    administracao: AdminScreen,
  };
  const ActiveScreen = screens[view];

  return (
    <main className="min-h-screen bg-[#020d17] text-slate-100">
      <Toaster richColors position="top-right" />
      <div className="min-h-screen lg:grid lg:grid-cols-[298px_minmax(0,1fr)]">
        <aside className={`fixed inset-y-0 left-0 z-50 flex w-[298px] flex-col border-r border-[#17334b] bg-[#041728] px-5 py-4 transition-transform lg:sticky lg:top-0 lg:translate-x-0 ${mobileOpen ? "translate-x-0" : "-translate-x-full"}`}>
          <div className="flex items-center justify-between"><button onClick={() => navigate("inicio")} className="flex items-center gap-4 text-left"><span className="grid size-14 place-items-center rounded-2xl bg-gradient-to-br from-[#2f8cff] to-[#1656c9] text-xl font-black shadow-lg shadow-blue-950/30">RM</span><span className="max-w-40 text-sm font-bold leading-5">Sistema de Recomendação Multidomínio</span></button><Button variant="ghost" size="icon" className="lg:hidden" onClick={() => setMobileOpen(false)} aria-label="Fechar menu"><X /></Button></div>
          <nav className="mt-12 grid gap-2 text-[#9fc3e5]">{navigation.map(({ icon: Icon, label, view: target, protected: protectedView }) => <button key={label} onClick={() => navigate(target, protectedView)} className={`flex items-center gap-5 rounded-2xl border-l-4 px-5 py-3.5 text-left transition hover:bg-[#0c2b46] hover:text-white ${view === target ? "border-[#2f8cff] bg-[#174b7b] text-white" : "border-transparent"}`}><Icon className="size-5" /><span>{label}</span></button>)}</nav>
          <div className="mt-auto grid gap-2 border-t border-[#17334b] pt-5">{user?.role === "admin" && <button onClick={() => navigate("administracao")} className={`flex items-center gap-5 rounded-xl px-5 py-3 text-left hover:bg-[#0c2b46] hover:text-white ${view === "administracao" ? "bg-[#0c2b46] text-white" : "text-[#9fc3e5]"}`}><ShieldCheck className="size-5" /> Administração</button>}{user ? <button onClick={() => void logout()} className="flex items-center gap-5 rounded-xl px-5 py-3 text-left text-[#9fc3e5] hover:bg-[#0c2b46] hover:text-white"><LogOut className="size-5" /> Sair</button> : <button onClick={() => openAuth("login")} className="flex items-center gap-5 rounded-xl px-5 py-3 text-left text-[#9fc3e5] hover:bg-[#0c2b46] hover:text-white"><LogIn className="size-5" /> Entrar</button>}</div>
        </aside>
        {mobileOpen && <button className="fixed inset-0 z-40 bg-black/60 lg:hidden" onClick={() => setMobileOpen(false)} aria-label="Fechar menu" />}
        <section className="min-w-0"><header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-[#17334b] bg-[#020d17]/95 px-4 backdrop-blur lg:hidden"><Button variant="ghost" size="icon" onClick={() => setMobileOpen(true)} aria-label="Abrir menu"><Menu /></Button><span className="font-semibold">RM Multidomínio</span>{user ? <Badge variant="outline" className="border-[#275277] text-[#9fc3e5]">{firstName}</Badge> : <Button size="sm" onClick={() => openAuth("login")}>Entrar</Button>}</header>{!apiOnline && <div className="border-b border-amber-700/50 bg-amber-950/50 px-5 py-3 text-center text-sm text-amber-200">A API não respondeu. Confira o backend na porta 8000.</div>}<div className="mx-auto max-w-[1580px] px-4 py-6 sm:px-7 lg:px-9">{ActiveScreen()}</div></section>
      </div>

      <Dialog open={authOpen} onOpenChange={setAuthOpen}><DialogContent className="border-[#315675] bg-[#071b2d] text-white sm:max-w-md"><DialogHeader><DialogTitle className="flex items-center gap-2"><UserRound className="text-cyan-300" />{authMode === "login" ? "Entrar na conta" : "Criar uma conta"}</DialogTitle><DialogDescription className="text-[#9fc3e5]">{authMode === "login" ? "O mesmo login atende usuários e administradores." : "O cadastro público cria uma conta de usuário."}</DialogDescription></DialogHeader><form onSubmit={handleAuth} className="grid gap-4">{authMode === "register" && <label className="grid gap-1.5 text-sm">Nome<Input name="name" required minLength={2} className="border-[#315675] bg-[#0a2136]" /></label>}<label className="grid gap-1.5 text-sm">E-mail<Input name="email" type="email" defaultValue={authMode === "login" ? "usuario@teste.com" : ""} required className="border-[#315675] bg-[#0a2136]" /></label><label className="grid gap-1.5 text-sm">Senha<Input name="password" type="password" defaultValue={authMode === "login" ? "Teste123@" : ""} required minLength={8} className="border-[#315675] bg-[#0a2136]" /></label><Button type="submit" className="bg-[#267ef0] hover:bg-[#1f69c9]">{authMode === "login" ? "Entrar" : "Cadastrar"}</Button></form><button className="text-sm text-cyan-300 hover:underline" onClick={() => setAuthMode(authMode === "login" ? "register" : "login")}>{authMode === "login" ? "Ainda não tenho uma conta" : "Já tenho uma conta"}</button></DialogContent></Dialog>

      <Dialog open={domainDialogOpen} onOpenChange={setDomainDialogOpen}><DialogContent className="border-[#315675] bg-[#071b2d] text-white"><DialogHeader><DialogTitle>{editingDomain ? "Editar domínio" : "Novo domínio"}</DialogTitle><DialogDescription className="text-[#9fc3e5]">O domínio ficará disponível no catálogo e no cadastro de conteúdos.</DialogDescription></DialogHeader><form onSubmit={saveDomain} className="grid gap-4">{!editingDomain && <label className="grid gap-1.5 text-sm">Código<Input name="code" placeholder="ex.: podcast" pattern="[a-z0-9_-]+" required className="border-[#315675] bg-[#0a2136]" /></label>}<label className="grid gap-1.5 text-sm">Nome<Input name="name" defaultValue={editingDomain?.name} required className="border-[#315675] bg-[#0a2136]" /></label><label className="grid gap-1.5 text-sm">Descrição<Textarea name="description" defaultValue={editingDomain?.description} className="border-[#315675] bg-[#0a2136]" /></label><label className="flex items-center justify-between rounded-xl border border-[#315675] p-4 text-sm">Domínio ativo<Switch checked={domainActive} onCheckedChange={setDomainActive} /></label><Button type="submit" className="bg-[#267ef0]"><Save /> Salvar domínio</Button></form></DialogContent></Dialog>

      <Dialog open={contentDialogOpen} onOpenChange={setContentDialogOpen}>
        <DialogContent className="max-h-[90vh] overflow-y-auto border-[#315675] bg-[#071b2d] text-white sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>{editingContent ? "Editar conteúdo" : "Novo conteúdo"}</DialogTitle>
            <DialogDescription className="text-[#9fc3e5]">Preencha os dados que aparecerão no catálogo.</DialogDescription>
          </DialogHeader>
          <form onSubmit={saveContent} className="grid gap-4 sm:grid-cols-2">
            <label className="grid gap-1.5 text-sm sm:col-span-2">Título<Input name="title" defaultValue={editingContent?.title} required minLength={2} className="border-[#315675] bg-[#0a2136]" /></label>
            <label className="grid gap-1.5 text-sm sm:col-span-2">Descrição<Textarea name="description" defaultValue={editingContent?.description} required minLength={4} className="border-[#315675] bg-[#0a2136]" /></label>
            <label className="grid gap-1.5 text-sm">Domínio<Select value={contentDomain} onValueChange={setContentDomain}><SelectTrigger className="w-full border-[#315675] bg-[#0a2136]"><SelectValue /></SelectTrigger><SelectContent>{adminDomains.filter((domain) => domain.is_active).map((domain) => <SelectItem key={domain.code} value={domain.code}>{domain.name}</SelectItem>)}</SelectContent></Select></label>
            <label className="grid gap-1.5 text-sm">Categoria<Input name="category" defaultValue={editingContent?.category} required className="border-[#315675] bg-[#0a2136]" /></label>
            <label className="grid gap-1.5 text-sm">Imagem principal<Input name="image_url" type="text" placeholder="/banners/produtos/produto-1.jpg" defaultValue={editingContent?.image_url ?? ""} className="border-[#315675] bg-[#0a2136]" /></label>
            <label className="grid gap-1.5 text-sm">Link externo<Input name="external_url" type="url" defaultValue={editingContent?.external_url ?? ""} className="border-[#315675] bg-[#0a2136]" /></label>
            <label className="grid gap-1.5 text-sm sm:col-span-2">
              Imagens adicionais — uma por linha
              <Textarea
                name="gallery_images"
                rows={4}
                placeholder={"/banners/produtos/produto-2.jpg\n/banners/produtos/produto-3.jpg"}
                defaultValue={getAdditionalImages(editingContent)}
                className="border-[#315675] bg-[#0a2136]"
              />
              <span className="text-xs text-[#76a7d1]">Use um caminho por linha. A imagem principal também fará parte da galeria.</span>
            </label>
            {contentDomain === "produto" && (
              <label className="grid gap-1.5 text-sm sm:col-span-2">
                Modelo 3D (.glb)
                <Input
                  name="model_url"
                  type="text"
                  placeholder="/modelos/produtos/nome-do-produto.glb"
                  defaultValue={getMetadataString(editingContent?.metadata ?? {}, "model_url") ?? ""}
                  className="border-[#315675] bg-[#0a2136]"
                />
                <span className="text-xs text-[#76a7d1]">Quando preenchido, o botão Opção 3D aparecerá nos detalhes do produto.</span>
              </label>
            )}
            <label className="flex items-center justify-between rounded-xl border border-[#315675] p-4 text-sm sm:col-span-2">Publicado no catálogo<Switch checked={contentPublished} onCheckedChange={setContentPublished} /></label>
            <Button type="submit" className="bg-[#267ef0] sm:col-span-2"><Save /> Salvar conteúdo</Button>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={userDialogOpen} onOpenChange={setUserDialogOpen}><DialogContent className="border-[#315675] bg-[#071b2d] text-white sm:max-w-lg"><DialogHeader><DialogTitle>Cadastrar conta</DialogTitle><DialogDescription className="text-[#9fc3e5]">Somente um administrador autenticado pode criar outra conta administrativa.</DialogDescription></DialogHeader><form onSubmit={createAdminUser} className="grid gap-4 sm:grid-cols-2"><label className="grid gap-1.5 text-sm">Nome<Input name="name" required minLength={2} className="border-[#315675] bg-[#0a2136]" /></label><label className="grid gap-1.5 text-sm">E-mail<Input name="email" type="email" required className="border-[#315675] bg-[#0a2136]" /></label><label className="grid gap-1.5 text-sm">Senha<Input name="password" type="password" required minLength={8} className="border-[#315675] bg-[#0a2136]" /></label><label className="grid gap-1.5 text-sm">Confirmar senha<Input name="confirm_password" type="password" required minLength={8} className="border-[#315675] bg-[#0a2136]" /></label><label className="grid gap-1.5 text-sm sm:col-span-2">Perfil<Select value={newUserRole} onValueChange={(role) => setNewUserRole(role as "user" | "admin")}><SelectTrigger className="w-full border-[#315675] bg-[#0a2136]"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="user">Usuário</SelectItem><SelectItem value="admin">Administrador</SelectItem></SelectContent></Select></label><Button type="submit" className="bg-[#267ef0] sm:col-span-2">Cadastrar conta</Button></form></DialogContent></Dialog>

      <AlertDialog open={Boolean(deleteTarget)} onOpenChange={(open) => !open && setDeleteTarget(null)}><AlertDialogContent className="border-[#315675] bg-[#071b2d] text-white"><AlertDialogHeader><AlertDialogTitle>Excluir {deleteTarget?.label}?</AlertDialogTitle><AlertDialogDescription className="text-[#9fc3e5]">Esta ação remove o registro e não pode ser desfeita.</AlertDialogDescription></AlertDialogHeader><AlertDialogFooter><AlertDialogCancel className="border-[#315675] bg-transparent text-white">Cancelar</AlertDialogCancel><AlertDialogAction onClick={() => void performDelete()} className="bg-rose-600 hover:bg-rose-700">Excluir</AlertDialogAction></AlertDialogFooter></AlertDialogContent></AlertDialog>
    </main>
  );
}
