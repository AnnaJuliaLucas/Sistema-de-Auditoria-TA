const API_BASE = typeof window !== 'undefined' && window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1'
  ? "" // Na Vercel, usa caminhos relativos
  : "http://127.0.0.1:8000"; // Localmente, usa a porta 8000

async function fetchAPI<T>(path: string, options?: RequestInit): Promise<T> {
  const token = typeof window !== 'undefined' ? localStorage.getItem("audit_token") : null;
  const headers: Record<string, string> = { 
    "Content-Type": "application/json", 
    ...options?.headers 
  };
  
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });
  
  if (res.status === 401 && typeof window !== 'undefined') {
    localStorage.removeItem("audit_token");
    if (!window.location.pathname.includes("/login")) {
      window.location.href = "/login";
    }
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    let message = "Erro na API";
    if (typeof err.detail === 'string') {
      message = err.detail;
    } else if (Array.isArray(err.detail)) {
      // Validation error array
      message = err.detail.map((d: any) => `${d.loc.join('.')}: ${d.msg}`).join('; ');
    } else if (err.detail && typeof err.detail === 'object') {
      message = JSON.stringify(err.detail);
    }
    throw new Error(message || `API Error ${res.status}`);
  }
  return res.json();
}

// ─── Auditorias ──────────────────────────────────────────────────────────────

export interface Auditoria {
  id: number;
  unidade: string;
  area: string;
  ciclo: string;
  status: string;
  data_criacao?: string;
  data_atualizacao?: string;
  total_subitens: number;
  subitens_avaliados: number;
  media_nota_final?: number | null;
  ia_analisados: number;
  assessment_file_path?: string;
  evidence_folder_path?: string;
  openai_api_key?: string;
  ai_provider?: "openai" | "ollama" | "gemini" | "anthropic";
  ai_base_url?: string;
  observacoes?: string;
  modo_analise: "completo" | "economico";
}

export interface Avaliacao {
  id: number;
  auditoria_id: number;
  pratica_num: number;
  pratica_nome: string;
  subitem_idx: number;
  subitem_nome: string;
  evidencia_descricao?: string;
  nivel_0?: string;
  nivel_1?: string;
  nivel_2?: string;
  nivel_3?: string;
  nivel_4?: string;
  nota_self_assessment?: number;
  decisao: string;
  nota_final?: number | null;
  descricao_nc?: string;
  comentarios?: string;
  ia_decisao?: string;
  ia_nota_sugerida?: number | null;
  ia_confianca?: string;
  ia_pontos_atendidos?: string;
  ia_pontos_faltantes?: string;
  ia_analise_detalhada?: string;
  ia_status?: string;
}

export interface Pratica {
  pratica_num: number;
  pratica_nome: string;
  subitens: Avaliacao[];
  media_sa: number;
  media_final: number | null;
  total: number;
  avaliados: number;
  ia_ok: number;
  pendentes: number;
}

export interface ComparativoItem {
  pratica_num: number;
  pratica_nome: string;
  subitem_idx: number;
  subitem_nome: string;
  nota_a: number | null;
  nota_b: number | null;
  decisao_a: string;
  decisao_b: string;
  delta: number | null;
  tendencia: string;
}

export interface AuditLogEntry {
  id: number;
  timestamp: string;
  auditoria_id: number;
  pratica_num: number | null;
  subitem_idx: number | null;
  campo: string;
  valor_antes: string | null;
  valor_depois: string | null;
  usuario: string;
}

export const api = {
  // Auth
  login: (username: string, password: string) => {
    const formData = new URLSearchParams();
    formData.append("username", username);
    formData.append("password", password);
    
    return fetchAPI<{ access_token: string; token_type: string; email: string }>("/api/auth/login", {
      method: "POST",
      body: formData,
      headers: { 
        "Content-Type": "application/x-www-form-urlencoded" 
      }
    });
  },

  register: (email: string, password: string) => {
    return fetchAPI<{ ok: boolean; message: string }>("/api/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
  },

  // Auditorias
  listAuditorias: () => fetchAPI<Auditoria[]>("/api/auditorias"),
  getAuditoria: (id: number) => fetchAPI<Auditoria>(`/api/auditorias/${id}`),
  criarAuditoria: (data: Partial<Auditoria>) => 
    fetchAPI<{ ok: boolean; id: number }>("/api/auditorias", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  getUnidadesAreas: () => fetchAPI<Record<string, string[]>>("/api/unidades-areas"),
  updateStatus: (id: number, status: string) =>
    fetchAPI(`/api/auditorias/${id}/status`, {
      method: "PUT",
      body: JSON.stringify({ status }),
    }),
  getEstatisticas: (id: number) =>
    fetchAPI<{ total: number; avaliados: number; ia_ok: number; media_final: number | null; media_sa: number | null }>(
      `/api/auditorias/${id}/estatisticas`
    ),

  // Avaliações
  listAvaliacoes: (auditoriaId: number) =>
    fetchAPI<Pratica[]>(`/api/auditorias/${auditoriaId}/avaliacoes`),
  getAvaliacao: (id: number) => fetchAPI<Avaliacao>(`/api/avaliacoes/${id}`),
  saveDecisao: (id: number, data: {
    decisao: string;
    nota_final?: number | null;
    descricao_nc: string;
    comentarios: string;
  }) =>
    fetchAPI<{ ok: boolean; decisao: string; nota_final: number | null }>(
      `/api/avaliacoes/${id}/decisao`,
      { method: "PUT", body: JSON.stringify(data) }
    ),
  previewNota: (data: { decisao: string; nota_sa: number; nota_livre?: number | null }) =>
    fetchAPI<{ nota_final: number | null }>(
      "/api/avaliacoes/nota-preview",
      { method: "POST", body: JSON.stringify(data) }
    ),

  // IA
  analyzeSubitem: (avaliacaoId: number, apiKey: string, economico = false, modo_analise?: "completo" | "economico", provider = "openai", base_url?: string) =>
    fetchAPI<{
      ok: boolean;
      decisao: string;
      nota_sugerida: number;
      confianca: string;
      analise_detalhada: string;
      pontos_atendidos: string[];
      pontos_faltantes: string[];
    }>(`/api/ia/analisar/${avaliacaoId}`, {
      method: "POST",
      body: JSON.stringify({ api_key: apiKey, economico, modo_analise, provider, base_url }),
    }),

  // Health
  health: () => fetchAPI<{ status: string; version: string }>("/api/health"),

  // ── Dados & Histórico ─────────────────────────────────────────────────────
  excluirAuditoria: (id: number) =>
    fetchAPI<{ ok: boolean }>(`/api/dados/auditorias/${id}`, { method: "DELETE" }),
  duplicarAuditoria: (id: number, novo_ciclo: string) =>
    fetchAPI<{ ok: boolean; novo_id: number; novo_ciclo: string }>(
      `/api/dados/auditorias/${id}/duplicar`,
      { method: "POST", body: JSON.stringify({ novo_ciclo }) }
    ),
  getComparativo: (idA: number, idB: number) =>
    fetchAPI<{
      auditoria_a: { id: number; unidade: string; area: string; ciclo: string };
      auditoria_b: { id: number; unidade: string; area: string; ciclo: string };
      comparativo: ComparativoItem[];
    }>(`/api/dados/comparativo?id_a=${idA}&id_b=${idB}`),
  getAuditLog: (auditoriaId?: number, limit = 200) =>
    fetchAPI<AuditLogEntry[]>(
      `/api/dados/audit-log${auditoriaId ? `?auditoria_id=${auditoriaId}&limit=${limit}` : `?limit=${limit}`}`
    ),

  // Utilities
  pickFile: () => fetchAPI<{ path: string }>("/api/utils/pick-file"),
  pickFolder: () => fetchAPI<{ path: string }>("/api/utils/pick-folder"),
  getAllEvidences: (auditoriaId: number, refresh = false) => 
    fetchAPI<Record<string, any>>(`/api/evidencias/audit/${auditoriaId}/all${refresh ? '?refresh=true' : ''}`),
  getAllCriterios: () => fetchAPI<Record<string, any>>("/api/evidencias/criterios/all"),
};

// ─── Utility Functions ───────────────────────────────────────────────────────

export const ESCALA: Record<number, { emoji: string; desc: string; color: string }> = {
  0: { emoji: "🔴", desc: "Não tem prática", color: "#dc2626" },
  1: { emoji: "🟠", desc: "Informal", color: "#ea580c" },
  2: { emoji: "🟡", desc: "Formal", color: "#ca8a04" },
  3: { emoji: "🔵", desc: "Gerenciado", color: "#2563eb" },
  4: { emoji: "🟢", desc: "Excelente", color: "#16a34a" },
};

export const DECISAO_CONFIG: Record<string, { icon: string; label: string; color: string; bg: string }> = {
  permanece: { icon: "✅", label: "Nota permanece", color: "#16a34a", bg: "#dcfce7" },
  insuficiente: { icon: "⚠️", label: "Evidência insuficiente (−1)", color: "#ea580c", bg: "#ffedd5" },
  inexistente: { icon: "❌", label: "Evidência inexistente (→ 0)", color: "#dc2626", bg: "#fee2e2" },
  pendente: { icon: "⏳", label: "Pendente", color: "#6b7280", bg: "#f3f4f6" },
};

export function calcularNotaFinal(notaSa: number, decisao: string, notaLivre?: number | null): number | null {
  if (notaSa == null) return null;
  if (decisao === "permanece") return notaSa;
  if (decisao === "insuficiente") {
    if (notaLivre != null) return Math.max(0, Math.min(notaLivre, Math.max(0, notaSa - 1)));
    return Math.max(0, notaSa - 1);
  }
  if (decisao === "inexistente") return 0;
  return null; // pendente
}
