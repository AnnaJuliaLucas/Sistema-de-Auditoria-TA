"use client";

import { useState, useCallback, useEffect } from "react";
import { Avaliacao, DECISAO_CONFIG, ESCALA, calcularNotaFinal, api, API_BASE } from "@/lib/api";
import { cleanTitle } from "@/lib/utils";
import NotaBadge from "./NotaBadge";
import ChatPanel from "./ChatPanel";

interface SubitemCardProps {
    avaliacao: Avaliacao;
    onSaved: () => void;
    apiKey?: string;
    initialEvidence?: EvidenceData;
    initialCriteria?: CriteriosData;
    modoAnalise?: "completo" | "economico";
    aiProvider?: string;
    aiBaseUrl?: string;
}

interface EvidenceData {
    total: number;
    images: { path: string; name: string }[];
    docs: { path: string; name: string }[];
    videos: { path: string; name: string }[];
    ev_folder: string;
}

interface CriteriosData {
    pratica: string;
    subitem: string;
    descricao: string;
    niveis: Record<number, string>;
    evidencias_exigidas: string;
    regras_especiais: string;
    regras_gerais?: string;
    checklist: {
        verificar: string[];
        armadilhas: string[];
        nota4: string;
        regras: string[];
        hard_rule: string | null;
    };
}

const NIVEL_NAMES: Record<number, string> = {
    0: "🔴 0 – Não tem prática",
    1: "🟠 1 – Iniciando",
    2: "🟡 2 – Regular",
    3: "🔵 3 – Bom",
    4: "🟢 4 – Excelente",
};

export default function SubitemCard({ 
    avaliacao: av, onSaved, apiKey, initialEvidence, initialCriteria,
    modoAnalise, aiProvider, aiBaseUrl 
}: SubitemCardProps) {
    const [expanded, setExpanded] = useState(av.decisao === "pendente");
    const [decisao, setDecisao] = useState(av.decisao || "pendente");
    const [descNc, setDescNc] = useState(av.descricao_nc || "");
    const [comentarios, setComentarios] = useState(av.comentarios || "");
    const [notaLivre, setNotaLivre] = useState<number | null>(null);
    const [saving, setSaving] = useState(false);
    const [analyzing, setAnalyzing] = useState(false);
    const [toast, setToast] = useState<string | null>(null);
    const [showChat, setShowChat] = useState(false);
    const [uploading, setUploading] = useState(false);

    // Evidence & Criteria state
    const [evidence, setEvidence] = useState<EvidenceData | null>(initialEvidence || null);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const [criterios, setCriterios] = useState<CriteriosData | null>(initialCriteria || null);
    const [showGallery, setShowGallery] = useState(true);
    const [showCriterios, setShowCriterios] = useState(true);
    const [showDocuments, setShowDocuments] = useState(true); // Nova galeria de documentos
    const [showIaDetail, setShowIaDetail] = useState(false);
    const [criteriaTab, setCriteriaTab] = useState(0); // 0: Níveis, 1: Evidência Exigida
    const [selectedDoc, setSelectedDoc] = useState("");
    const [checkedItems, setCheckedItems] = useState<Set<string>>(new Set());
    const [lightboxIndex, setLightboxIndex] = useState<number | null>(null);
    const [activeDocUrl, setActiveDocUrl] = useState<string | null>(null);
    const [activeDocName, setActiveDocName] = useState("");
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const [docPreview, setDocPreview] = useState<any>(null);
    const [docLoading, setDocLoading] = useState(false);

    const notaSa = av.nota_self_assessment ?? 0;
    const notaFinal = calcularNotaFinal(notaSa, decisao, notaLivre);
    const decConfig = DECISAO_CONFIG[decisao] || DECISAO_CONFIG.pendente;

    // Auto-generate comment based on decision
    useEffect(() => {
        const AUTO_PATTERNS = ["Nota permanece", "Nota passa para ", "Evidência insuficiente"];
        const isAuto = !comentarios || AUTO_PATTERNS.some(p => comentarios.startsWith(p));
        if (isAuto && decisao !== (av.decisao || "pendente")) {
            const nf = calcularNotaFinal(notaSa, decisao, notaLivre);
            if (decisao === "permanece") setComentarios("Nota permanece");
            else if (decisao === "inexistente") setComentarios("Nota passa para 0");
            else if (decisao === "insuficiente") setComentarios(nf != null ? `Nota passa para ${nf}` : "Evidência insuficiente");
            else if (decisao === "aumentar") setComentarios(nf != null ? `Nota passa para ${nf}` : "Nota aumentada");
        }
    }, [decisao, notaLivre]);

    // Sync local state when avaliacao prop changes (e.g. after AI analysis refetch)
    useEffect(() => {
        setDecisao(av.decisao || "pendente");
        setDescNc(av.descricao_nc || "");
        setComentarios(av.comentarios || "");
        // Sincroniza nota manual se a decisão for de alteração de nota
        if (av.decisao === "insuficiente" || av.decisao === "aumentar") {
            setNotaLivre(av.nota_final || null);
        } else {
            setNotaLivre(null);
        }
    }, [av.id, av.ia_status, av.decisao, av.descricao_nc, av.comentarios, av.nota_final]);

    // Load criteria on expand (Evidence is now passed as prop)
    useEffect(() => {
        if (!expanded) return;
        
        // Only fetch evidence if not provided by parent (fallback)
        if (!evidence) {
            fetch(`${API_BASE}/api/evidencias/${av.auditoria_id}/${av.pratica_num}/${av.subitem_idx}`)
                .then(r => r.json()).then(setEvidence).catch(err => console.error("Erro ao carregar evidências:", err));
        }

        // Only fetch criteria if not provided by parent (fallback)
        if (!criterios) {
            fetch(`${API_BASE}/api/evidencias/criterios/${av.pratica_num}/${av.subitem_idx}`)
                .then(r => r.json())
                .then(data => {
                    console.log(`✅ Critérios carregados para ${av.pratica_num}.${av.subitem_idx + 1}:`, data);
                    setCriterios(data);
                })
                .catch(err => {
                    console.error(`❌ Erro ao carregar critérios para ${av.pratica_num}.${av.subitem_idx + 1}:`, err);
                    // NUCLEAR FIX V3: "any" total para forçar o deploy
                    setCriterios({ 
                        pratica: String(av.pratica_num),
                        subitem: String(av.subitem_idx + 1),
                        descricao: av.subitem_nome || "",
                        niveis: {}, 
                        evidencias_exigidas: "", 
                        regras_especiais: "", 
                        regras_gerais: "", 
                        checklist: { 
                            verificar: [], 
                            armadilhas: [], 
                            nota4: "", 
                            regras: [], 
                            hard_rule: null 
                        } 
                    } as CriteriosData);
                });
        }
    }, [expanded, av.auditoria_id, av.pratica_num, av.subitem_idx, evidence, criterios]);

    const showToast = useCallback((msg: string) => {
        setToast(msg);
        setTimeout(() => setToast(null), 3000);
    }, []);

    async function handleSave() {
        setSaving(true);
        try {
            await api.saveDecisao(av.id, {
                decisao,
                nota_final: notaFinal,
                descricao_nc: (decisao === "insuficiente" || decisao === "inexistente" || decisao === "aumentar") ? descNc : "",
                comentarios,
            });
            showToast("✅ Decisão salva!");
            onSaved();
        } catch (e: unknown) {
            showToast(`❌ Erro: ${e instanceof Error ? e.message : "Falha ao salvar"}`);
        } finally {
            setSaving(false);
        }
    }

    async function handleAnalyze() {
        if (!apiKey) { showToast("❌ Configure a chave API OpenAI"); return; }
        setAnalyzing(true);
        try {
            const result = await api.analyzeSubitem(
                av.id, 
                apiKey, 
                modoAnalise === 'economico', 
                modoAnalise, 
                aiProvider || "openai" as any, 
                aiBaseUrl
            );
            showToast(`🤖 Análise concluída! Decisão: ${result.decisao}`);
            onSaved();
        } catch (e: unknown) {
            showToast(`❌ Erro IA: ${e instanceof Error ? e.message : "Falha"}`);
        } finally {
            setAnalyzing(false);
        }
    }

    async function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
        const file = e.target.files?.[0];
        if (!file) return;

        setUploading(true);
        try {
            await api.uploadEvidenciaSubitem(av.auditoria_id, av.pratica_num, av.subitem_idx, file);
            showToast("✅ Arquivo enviado com sucesso!");
            
            // Refresh evidence list
            const res = await fetch(`${API_BASE}/api/evidencias/${av.auditoria_id}/${av.pratica_num}/${av.subitem_idx}?refresh=true`);
            const data = await res.json();
            setEvidence(data);
        } catch (err: unknown) {
            showToast(`❌ Erro no upload: ${err instanceof Error ? err.message : "Falha"}`);
        } finally {
            setUploading(false);
            if (e.target) e.target.value = ""; // Clear input
        }
    }

    async function handleRemoveFile(path: string) {
        if (!confirm("Tem certeza que deseja remover esta evidência?")) return;
        
        try {
            await api.removerEvidenciaSubitem(av.auditoria_id, path);
            showToast("✅ Arquivo removido!");
            
            // Refresh evidence list
            const res = await fetch(`${API_BASE}/api/evidencias/${av.auditoria_id}/${av.pratica_num}/${av.subitem_idx}?refresh=true`);
            const data = await res.json();
            setEvidence(data);
        } catch (err: unknown) {
            showToast(`❌ Erro ao remover: ${err instanceof Error ? err.message : "Falha"}`);
        }
    }

    async function handleClearEvidences() {
        if (!confirm("🔥 ATENÇÃO: Deseja remover TODAS as evidências deste subitem? Esta ação é irreversível.")) return;
        
        try {
            await api.limparEvidenciasSubitem(av.auditoria_id, av.pratica_num, av.subitem_idx);
            showToast("🗑️ Todas as evidências foram removidas!");
            
            // Refresh
            const res = await fetch(`${API_BASE}/api/evidencias/${av.auditoria_id}/${av.pratica_num}/${av.subitem_idx}?refresh=true`);
            const data = await res.json();
            setEvidence(data);
        } catch (err: unknown) {
            showToast(`❌ Erro ao limpar: ${err instanceof Error ? err.message : "Falha"}`);
        }
    }

    function toggleCheck(key: string) {
        setCheckedItems(prev => {
            const next = new Set(prev);
            if (next.has(key)) next.delete(key);
            else next.add(key);
            return next;
        });
    }

    // Parse IA points
    let pontosAtendidos: string[] = [];
    let pontosFaltantes: string[] = [];
    try {
        pontosAtendidos = av.ia_pontos_atendidos ? JSON.parse(av.ia_pontos_atendidos) : [];
        pontosFaltantes = av.ia_pontos_faltantes ? JSON.parse(av.ia_pontos_faltantes) : [];
    } catch { /* ignore */ }

    // Divergence detection
    const iaNota = av.ia_nota_sugerida;
    const divergencia = av.ia_status === "ok" && iaNota != null && notaSa != null
        ? (notaSa - iaNota >= 2
            ? `IA sugeriu nota ${iaNota}, mas SA declarou ${notaSa} (diferença de ${notaSa - iaNota} pontos).`
            : pontosFaltantes.length > 0 && iaNota >= 3
                ? `IA atribuiu nota ${iaNota} mas identificou ${pontosFaltantes.length} ponto(s) faltante(s). Evidência pode ser insuficiente.`
                : null)
        : null;

    // Pre-fill desc_nc from IA if user hasn't saved manually
    const effectiveDescNc = descNc || (av.ia_status === "ok" && av.decisao === av.ia_decisao ? (av.ia_analise_detalhada || "").slice(0, 2000) : "");

    return (
        <div className="glass-card animate-fade-in mb-3">
            {/* Header */}
            <div
                onClick={() => setExpanded(!expanded)}
                onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setExpanded(!expanded); } }}
                role="button"
                tabIndex={0}
                className="w-full flex items-center justify-between p-4 hover:bg-slate-700/30 transition-colors text-left cursor-pointer outline-none focus:bg-slate-700/50"
            >
                <div className="flex items-center gap-3">
                    <span className="text-lg">{decConfig.icon}</span>
                    <div>
                        <span className="font-semibold text-white text-sm">
                            {av.pratica_num}.{av.subitem_idx + 1}
                        </span>
                        <span className="text-slate-300 text-sm"> {cleanTitle(av.subitem_nome)}</span>
                    </div>
                </div>
                <div className="flex items-center gap-3">
                    {evidence && evidence.total > 0 && (
                        <span className="text-xs text-slate-500">📁 {evidence.total}</span>
                    )}
                    <NotaBadge nota={notaSa} size="sm" showLabel={false} />
                    <span className="text-slate-500">→</span>
                    <NotaBadge nota={av.nota_final} size="sm" showLabel={false} />
                    {av.ia_status === "ok" && <span className="text-xs text-blue-400">🤖</span>}
                    
                    {analyzing && (
                        <span className="text-[10px] font-bold text-purple-400 animate-pulse bg-purple-600/10 px-2 py-1 rounded-lg border border-purple-600/20">
                            ANALISANDO...
                        </span>
                    )}

                    <span className={`text-slate-400 transition-transform duration-200 ${expanded ? "rotate-180" : ""}`}>
                        ▼
                    </span>
                </div>
            </div>

            {/* Expanded content — TWO COLUMNS */}
            {expanded && (
                <div className="border-t border-slate-700/50 animate-fade-in">
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-0">

                        {/* ═══════════ LEFT COLUMN: EVIDENCES ═══════════ */}
                        <div className="p-5 border-r border-slate-700/30 space-y-4">
                            <div className="flex items-center justify-between mb-2">
                                <h4 className="text-sm font-bold text-white flex items-center gap-2">
                                    📁 Evidências
                                    {evidence && <span className="text-xs text-slate-400 font-normal">{evidence.total} arquivo(s)</span>}
                                </h4>

                                <div className="flex items-center gap-2">
                                    {evidence && (evidence.total > 0) && (
                                        <button 
                                            onClick={handleClearEvidences}
                                            className="px-3 py-1.5 rounded-lg bg-red-600/10 hover:bg-red-600/30 text-red-500 text-[10px] font-bold transition-all flex items-center gap-1.5 border border-red-500/20"
                                            title="Remover todos os arquivos deste item"
                                        >
                                            <span className="text-xs">🗑️</span>
                                            LIMPAR TUDO
                                        </button>
                                    )}

                                    <label className={`cursor-pointer px-3 py-1.5 rounded-lg bg-blue-600/20 hover:bg-blue-600/40 text-blue-400 text-[10px] font-bold transition-all flex items-center gap-1.5 border border-blue-500/30 ${uploading ? 'opacity-50 cursor-not-allowed' : ''}`}>
                                        {uploading ? (
                                            <>
                                                <span className="animate-spin">⏳</span>
                                                ENVIANDO...
                                            </>
                                        ) : (
                                            <>
                                                <span className="text-xs">➕</span>
                                                ADICIONAR
                                            </>
                                        )}
                                        <input 
                                            type="file" 
                                            className="hidden" 
                                            onChange={handleFileUpload} 
                                            disabled={uploading}
                                        />
                                    </label>
                                </div>
                            </div>

                            {evidence && evidence.total > 0 ? (
                                <>
                                    <div className="flex gap-3 text-xs text-slate-400">
                                        {evidence.images.length > 0 && <span>📷 {evidence.images.length} imagem(ns)</span>}
                                        {evidence.docs.length > 0 && <span>📄 {evidence.docs.length} documento(s)</span>}
                                        {evidence.videos.length > 0 && <span>🎬 {evidence.videos.length} vídeo(s)</span>}
                                    </div>

                                    {evidence.images.length > 0 && (
                                        <div>
                                            <button onClick={() => setShowGallery(!showGallery)}
                                                className="text-xs text-blue-400 hover:text-blue-300 mb-2 flex items-center gap-1">
                                                {showGallery ? "▼" : "▶"} 📷 Galeria ({evidence.images.length}) — clique para ampliar
                                            </button>
                                            {showGallery && (
                                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                                    {evidence.images.map((img, i) => (
                                                        <div key={i}
                                                            onClick={() => setLightboxIndex(i)}
                                                            className="flex flex-col rounded-xl overflow-hidden bg-slate-900/40 border border-slate-700 hover:border-blue-500/50 hover:ring-2 hover:ring-blue-500/20 group cursor-pointer transition-all shadow-lg"
                                                        >
                                                            <div className="h-44 w-full bg-slate-950 flex items-center justify-center p-2 relative">
                                                                <img
                                                                    src={`${API_BASE}/api/evidencias/file?path=${encodeURIComponent(img.path)}`}
                                                                    alt={img.name}
                                                                    className="max-w-full max-h-full object-contain group-hover:scale-105 transition-transform duration-500"
                                                                    loading="lazy"
                                                                />
                                                                <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                                                    <button 
                                                                        onClick={(e) => { e.stopPropagation(); handleRemoveFile(img.path); }}
                                                                        className="p-1.5 bg-red-600/80 hover:bg-red-600 text-white rounded-full shadow-lg border border-red-400/20 backdrop-blur-sm"
                                                                        title="Remover evidência"
                                                                    >
                                                                        🗑️
                                                                    </button>
                                                                </div>
                                                            </div>
                                                            <div className="bg-slate-800/80 px-3 py-2 border-t border-slate-700/50">
                                                                <span className="text-[10px] text-slate-300 font-medium truncate block">
                                                                    {img.name}
                                                                </span>
                                                            </div>
                                                        </div>
                                                    ))}
                                                </div>
                                            )}
                                        </div>
                                    )}

                                    {evidence.docs.length > 0 && (
                                        <div className="pt-2">
                                            <button onClick={() => setShowDocuments(!showDocuments)}
                                                className="text-xs text-blue-400 hover:text-blue-300 mb-3 flex items-center gap-1">
                                                {showDocuments ? "▼" : "▶"} 📄 Documentos ({evidence.docs.length}) — selecione para visualizar
                                            </button>

                                            {showDocuments && (
                                                <>
                                                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                                                        {evidence.docs.map((doc, i) => (
                                                            <div key={i} className="group relative">
                                                                <button
                                                                    onClick={async () => {
                                                                        const previewUrl = `${API_BASE}/api/evidencias/preview?path=${encodeURIComponent(doc.path)}`;
                                                                        if (activeDocUrl === doc.path) {
                                                                            setActiveDocUrl(null);
                                                                            setDocPreview(null);
                                                                        } else {
                                                                            setActiveDocUrl(doc.path);
                                                                            setActiveDocName(doc.name);
                                                                            setDocPreview(null);
                                                                            setDocLoading(true);
                                                                            try {
                                                                                const res = await fetch(previewUrl);
                                                                                const data = await res.json();
                                                                                setDocPreview(data);
                                                                            } catch {
                                                                                setDocPreview({ type: "error", name: doc.name, error: "Falha ao carregar preview" });
                                                                            } finally {
                                                                                setDocLoading(false);
                                                                            }
                                                                        }
                                                                    }}
                                                                    className={`w-full flex flex-col items-center justify-center p-2 rounded-lg border transition-all hover:bg-slate-700/50 ${activeDocUrl === doc.path
                                                                        ? "bg-blue-600/20 border-blue-500 shadow-glow-blue"
                                                                        : "bg-slate-800/40 border-slate-700"
                                                                        }`}
                                                                >
                                                                    <span className="text-xl mb-1">📄</span>
                                                                    <span className="text-[10px] text-center line-clamp-2 text-slate-300 group-hover:text-blue-200">
                                                                        {doc.name}
                                                                    </span>
                                                                </button>
                                                                
                                                                <button 
                                                                    onClick={(e) => { e.stopPropagation(); handleRemoveFile(doc.path); }}
                                                                    className="absolute -top-1 -right-1 p-1 bg-red-600/90 text-[10px] text-white rounded-full opacity-0 group-hover:opacity-100 transition-opacity border border-red-400/20 shadow-lg"
                                                                    title="Remover"
                                                                >
                                                                    🗑️
                                                                </button>
                                                            </div>
                                                        ))}
                                                    </div>

                                                    {activeDocUrl && (
                                                        <div className="mt-4 rounded-xl overflow-hidden border border-slate-600 bg-slate-900/50 shadow-xl animate-scale-in">
                                                            <div className="bg-slate-800/80 px-4 py-2 flex items-center justify-between border-b border-slate-700">
                                                                <span className="text-xs font-medium text-blue-300 truncate max-w-[80%]">
                                                                    👀 {activeDocName}
                                                                </span>
                                                                <button
                                                                    onClick={() => { setActiveDocUrl(null); setDocPreview(null); }}
                                                                    className="text-slate-400 hover:text-white transition-colors"
                                                                >
                                                                    ✕
                                                                </button>
                                                            </div>

                                                            <div className="relative">
                                                                {docLoading && (
                                                                    <div className="p-12 text-center">
                                                                        <div className="inline-block animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500 mb-4"></div>
                                                                        <p className="text-sm text-slate-400">Carregando visualização...</p>
                                                                    </div>
                                                                )}

                                                                {docPreview && (
                                                                    <div className="animate-fade-in">
                                                                        {docPreview.type === "pdf" && (
                                                                            <object
                                                                                data={`data:application/pdf;base64,${docPreview.data}`}
                                                                                type="application/pdf"
                                                                                className="w-full"
                                                                                style={{ height: "600px" }}
                                                                            >
                                                                                <div className="p-8 text-center text-slate-400">
                                                                                    <p>Visualização de PDF não disponível.</p>
                                                                                    <a href={`${API_BASE}/api/evidencias/file?path=${encodeURIComponent(activeDocUrl)}`}
                                                                                        target="_blank" rel="noopener noreferrer" className="text-blue-400 underline">
                                                                                        Baixar para ver
                                                                                    </a>
                                                                                </div>
                                                                            </object>
                                                                        )}

                                                                        {docPreview.type === "excel" && (
                                                                            <div className="p-0 max-h-[600px] overflow-auto bg-white/95">
                                                                                <div
                                                                                    dangerouslySetInnerHTML={{ __html: docPreview.html }}
                                                                                    className="text-[11px] text-black [&_table]:w-full [&_table]:border-collapse [&_th]:bg-slate-200 [&_th]:border [&_th]:border-slate-300 [&_th]:p-1.5 [&_td]:border [&_td]:border-slate-200 [&_td]:p-1.5"
                                                                                />
                                                                            </div>
                                                                        )}

                                                                        {docPreview.type === "word" && (
                                                                            <div className="p-6 max-h-[600px] overflow-auto bg-white/95 text-slate-900">
                                                                                {(docPreview.paragraphs || []).map((p: any, pi: number) => (
                                                                                    <p key={pi} className="mb-3 text-sm leading-relaxed">{p}</p>
                                                                                ))}
                                                                            </div>
                                                                        )}

                                                                        {docPreview.type === "error" && (
                                                                            <div className="p-8 text-center text-red-400">
                                                                                <p className="mb-4">❌ {docPreview.error}</p>
                                                                                <a href={`${API_BASE}/api/evidencias/file?path=${encodeURIComponent(activeDocUrl)}`}
                                                                                    target="_blank" rel="noopener noreferrer" className="text-blue-400 underline">
                                                                                    Baixar arquivo
                                                                                </a>
                                                                            </div>
                                                                        )}
                                                                    </div>
                                                                )}
                                                            </div>

                                                            <div className="px-4 py-3 bg-slate-800/40 flex justify-center gap-4">
                                                                <a
                                                                    href={`${API_BASE}/api/evidencias/file?path=${encodeURIComponent(activeDocUrl)}`}
                                                                    download={activeDocName}
                                                                    className="px-4 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-medium transition-colors"
                                                                >
                                                                    ⬇️ Baixar Completo
                                                                </a>
                                                                <button
                                                                    onClick={() => { setActiveDocUrl(null); setDocPreview(null); }}
                                                                    className="px-4 py-1.5 bg-slate-700 hover:bg-slate-600 text-white rounded-lg text-xs font-medium transition-colors"
                                                                >
                                                                    ❌ Fechar
                                                                </button>
                                                            </div>
                                                        </div>
                                                    )}
                                                </>
                                            )}
                                        </div>
                                    )}

                                    {evidence.videos.length > 0 && (
                                        <div>
                                            <p className="text-xs text-slate-400 mb-2">🎬 Vídeos:</p>
                                            {evidence.videos.map((vid, i) => (
                                                <div key={i} className="bg-slate-700/40 rounded-lg p-2 mb-2">
                                                    <p className="text-xs text-slate-300 mb-1">▶ {vid.name}</p>
                                                    <video controls className="w-full rounded" preload="metadata">
                                                        <source src={`${API_BASE}/api/evidencias/file?path=${encodeURIComponent(vid.path)}`} />
                                                    </video>
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </>
                            ) : evidence && evidence.ev_folder ? (
                                <div className="text-xs text-slate-500 space-y-1">
                                    <p>📭 Pasta {av.pratica_num}.{av.subitem_idx + 1} não encontrada ou vazia</p>
                                    <p className="text-[10px]">📂 {evidence.ev_folder}</p>
                                </div>
                            ) : (
                                <div className="text-xs text-slate-500 p-3 bg-slate-800/30 rounded-lg">
                                    ⚙️ Configure a pasta de evidências em Configurações
                                </div>
                            )}
                        </div>
                        {/* ═══════════ RIGHT COLUMN: EVALUATION ═══════════ */}
                        <div className="p-5 space-y-4">
                            <h4 className="text-sm font-bold text-white uppercase tracking-wider mb-2">📊 Avaliação</h4>

                            {/* Nota SA */}
                            <div className="flex items-center gap-2 text-sm mb-4">
                                <span className="text-slate-400">Nota Self Assessment:</span>
                                <NotaBadge nota={notaSa} />
                            </div>

                            {/* [PREMIUM] Regras Especiais — IDENTICAL to old system (Yellow Alert) */}
                            {criterios?.regras_especiais && (
                                <div className="animate-fade-in bg-[#FFFDE7]/95 border border-[#FFF59D] p-5 rounded-xl shadow-md my-4 flex items-start gap-3">
                                    <span className="text-[#FFD600] text-xl mt-0.5">⚠️</span>
                                    <div>
                                        <p className="text-sm text-[#827717] leading-relaxed font-semibold">
                                            <span className="text-[#FBC02D] font-bold">Regras Especiais:</span> {criterios?.regras_especiais}
                                        </p>
                                    </div>
                                </div>
                            )}

                            {/* ── PO.AUT.002 Criteria ── */}
                            <div className="rounded-xl border border-slate-700/50 bg-[#F8F9FA]/5 overflow-hidden shadow-sm">
                                <button onClick={() => setShowCriterios(!showCriterios)}
                                    className="w-full text-left text-sm font-semibold text-slate-200 flex items-center justify-between p-3.5 bg-slate-800/40 hover:bg-slate-800 transition-colors">
                                    <div className="flex items-center gap-2">
                                        <span className={`transition-transform duration-200 ${showCriterios ? "rotate-0" : "-rotate-90"}`}>▼</span>
                                        <span className="text-lg">📖</span>
                                        Critérios (PO.AUT.002)
                                    </div>
                                </button>

                                {showCriterios && (
                                    <div className="p-4 space-y-4 animate-scale-in">
                                        {!criterios ? (
                                            <div className="text-center py-6">
                                                <div className="inline-block animate-spin rounded-full h-6 w-6 border-t-2 border-b-2 border-blue-500 mb-2"></div>
                                                <p className="text-slate-400 text-sm">Carregando critérios...</p>
                                            </div>
                                        ) : (
                                            <>
                                                {/* Tabs Header - MATCHING OLD SYSTEM */}
                                                <div className="flex border-b border-slate-700/50">
                                                    <button 
                                                        onClick={() => setCriteriaTab(0)}
                                                        className={`flex items-center gap-2 px-5 py-2.5 text-xs font-semibold transition-all border-b-2 ${criteriaTab === 0 ? "border-red-500 text-red-500 bg-red-500/5" : "border-transparent text-slate-400 hover:text-slate-200"}`}
                                                    >
                                                        📊 Critérios por nível 0–4
                                                    </button>
                                                    <button 
                                                        onClick={() => setCriteriaTab(1)}
                                                        className={`flex items-center gap-2 px-5 py-2.5 text-xs font-semibold transition-all border-b-2 ${criteriaTab === 1 ? "border-red-500 text-red-500 bg-red-500/5" : "border-transparent text-slate-400 hover:text-slate-200"}`}
                                                    >
                                                        📋 Evidência exigida
                                                    </button>
                                                </div>

                                                {/* Tab Content: Níveis */}
                                                {criteriaTab === 0 && (
                                                    <div className="overflow-hidden rounded-lg border border-slate-700/30 bg-white/5 shadow-sm">
                                                        <table className="w-full text-xs text-left border-collapse">
                                                            <thead className="bg-slate-100/5 text-slate-400 font-medium border-b border-slate-700/50">
                                                                <tr>
                                                                    <th className="px-4 py-3 w-32">Nível</th>
                                                                    <th className="px-4 py-3">Descrição</th>
                                                                </tr>
                                                            </thead>
                                                            <tbody className="divide-y divide-slate-700/30">
                                                                {[0, 1, 2, 3, 4].map(n => {
                                                                    const text = (criterios.niveis || {})[n] || "";
                                                                    if (!text) return null;
                                                                    return (
                                                                        <tr key={n} className="hover:bg-white/5 transition-colors">
                                                                            <td className="px-4 py-4 whitespace-nowrap font-medium align-top">
                                                                                <span className="flex items-center gap-2">
                                                                                    {NIVEL_NAMES[n]}
                                                                                </span>
                                                                            </td>
                                                                            <td className="px-4 py-4 text-slate-300 leading-relaxed text-[12.5px]">
                                                                                {text}
                                                                            </td>
                                                                        </tr>
                                                                    );
                                                                })}
                                                            </tbody>
                                                        </table>
                                                    </div>
                                                )}

                                                {/* Tab Content: Evidência Exigida */}
                                                {criteriaTab === 1 && (
                                                    <div className="overflow-hidden rounded-lg border border-slate-700/30 bg-white/5 shadow-sm">
                                                        <table className="w-full text-xs text-left border-collapse">
                                                            <thead className="bg-slate-100/5 text-slate-400 font-medium border-b border-slate-700/50">
                                                                <tr>
                                                                    <th className="px-4 py-3 w-10 text-center">
                                                                        <span className="text-slate-500 font-bold">#</span>
                                                                    </th>
                                                                    <th className="px-3 py-3 w-10 text-center">
                                                                        <span className="text-slate-500 font-bold">Check</span>
                                                                    </th>
                                                                    <th className="px-4 py-3">Item de Verificação / Evidência Exigida</th>
                                                                </tr>
                                                            </thead>
                                                            <tbody className="divide-y divide-slate-700/30">
                                                                {(() => {
                                                                    const items: { text: string; id: string; type: 'ev' | 'chk' | 'trap' }[] = [];
                                                                    
                                                                    // 1. Oficiais da prática
                                                                    if (criterios.evidencias_exigidas) {
                                                                        criterios.evidencias_exigidas.split(";").filter(Boolean).forEach((ev, i) => {
                                                                            items.push({ text: ev.trim(), id: `ev_${i}`, type: 'ev' });
                                                                        });
                                                                    }
                                                                    
                                                                    // 2. Do Checklist (Verificar)
                                                                    if (criterios.checklist?.verificar) {
                                                                        criterios.checklist.verificar.forEach((chk, i) => {
                                                                            if (!items.find(it => it.text.toLowerCase() === chk.toLowerCase())) {
                                                                                items.push({ text: `🔍 ${chk}`, id: `chk_${i}`, type: 'chk' });
                                                                            }
                                                                        });
                                                                    }

                                                                    // 3. Do Checklist (Armadilhas)
                                                                    if (criterios.checklist?.armadilhas) {
                                                                        criterios.checklist.armadilhas.forEach((trap, i) => {
                                                                            items.push({ text: `🪤 ${trap}`, id: `trap_${i}`, type: 'trap' });
                                                                        });
                                                                    }

                                                                    if (items.length === 0) {
                                                                        return (
                                                                            <tr>
                                                                                <td colSpan={3} className="px-4 py-10 text-center text-slate-500 italic">Nenhum item catalogado.</td>
                                                                            </tr>
                                                                        );
                                                                    }

                                                                    return items.map((item, i) => (
                                                                        <tr key={item.id} className="hover:bg-white/5 transition-colors group">
                                                                            <td className="px-4 py-3.5 text-center text-slate-500 font-mono border-r border-slate-700/30 text-[10px]">{i + 1}</td>
                                                                            <td className="px-3 py-3.5 text-center border-r border-slate-700/30">
                                                                                <input 
                                                                                    type="checkbox"
                                                                                    checked={checkedItems.has(item.id)}
                                                                                    onChange={() => toggleCheck(item.id)}
                                                                                    className="w-4 h-4 rounded border-slate-600 bg-slate-700 text-blue-600 focus:ring-blue-500 cursor-pointer"
                                                                                />
                                                                            </td>
                                                                            <td className="px-4 py-3.5">
                                                                                <span className={`text-[13px] leading-relaxed cursor-pointer select-none ${checkedItems.has(item.id) ? "text-slate-500 line-through" : item.type === 'trap' ? "text-amber-200" : "text-slate-300"}`}
                                                                                      onClick={() => toggleCheck(item.id)}>
                                                                                    {item.text}
                                                                                </span>
                                                                            </td>
                                                                        </tr>
                                                                    ));
                                                                })()}
                                                            </tbody>
                                                        </table>
                                                    </div>
                                                )}
                                            </>
                                        )}
                                    </div>
                                )}
                            </div>

                            {/* ── Regras Gerais (Todas as práticas) ── */}
                            {criterios?.regras_gerais && (
                                <div className="rounded-xl border border-slate-700/50 bg-slate-900/30 overflow-hidden mt-4 shadow-sm">
                                    <button onClick={() => setCriteriaTab(criteriaTab === 2 ? 0 : 2)}
                                        className="w-full text-left text-sm font-semibold text-slate-200 flex items-center justify-between p-3.5 bg-slate-800/40 hover:bg-slate-800 transition-colors">
                                        <div className="flex items-center gap-2">
                                            <span className={`transition-transform duration-200 ${criteriaTab === 2 ? "rotate-0" : "-rotate-90"}`}>▼</span>
                                            <span className="text-lg">🖋️</span>
                                            Regras gerais (todas as práticas)
                                        </div>
                                    </button>
                                    {criteriaTab === 2 && (
                                        <div className="p-5 bg-slate-900/40 border-t border-slate-700/50 animate-scale-in">
                                            <p className="text-[10px] font-bold uppercase tracking-[0.1em] text-slate-500 mb-4 pb-2 border-b border-white/5">
                                                REGRAS OFICIAIS DE AVALIAÇÃO (PO.AUT.002 Rev3):
                                            </p>
                                            <div className="text-[12.5px] text-slate-400 space-y-4 leading-relaxed overflow-y-auto max-h-[500px]">
                                                {criterios.regras_gerais.split('\n').filter(Boolean).map((line, idx) => (
                                                    <div key={idx} className="flex gap-2">
                                                        <span className="text-slate-500 flex-shrink-0">•</span>
                                                        <span>{line.trim()}</span>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    )}
                                </div>
                            )}

                            {/* ── Additional Rules (Hard Rule & Nota 4) ── */}
                            {criterios && criterios.checklist && (criterios.checklist.hard_rule || criterios.checklist.nota4) && (
                                <div className="space-y-3 mt-4">
                                    {/* Hard rule */}
                                    {criterios.checklist.hard_rule && (
                                        <div className="text-xs text-red-300 bg-red-900/30 rounded-xl p-4 border border-red-700/30 shadow-sm animate-scale-in">
                                            🚨 <strong className="text-red-400">REGRA RÍGIDA — NOTA 0:</strong> {criterios.checklist.hard_rule}
                                        </div>
                                    )}

                                    {/* Nota 4 criterion */}
                                    {criterios.checklist.nota4 && (
                                        <div className="text-xs text-green-300 bg-green-900/20 rounded-xl p-4 border border-green-700/25 shadow-sm animate-scale-in">
                                            🟢 <strong className="text-green-400">Critério Nota 4:</strong> {criterios.checklist.nota4}
                                        </div>
                                    )}
                                </div>
                            )}

                            {/* ── IA Analysis Result ── */}
                            {av.ia_status === "ok" && (
                                <div className="rounded-xl p-5 space-y-4 shadow-xl animate-fade-in"
                                    style={{ 
                                        background: "linear-gradient(135deg, rgba(59, 130, 246, 0.12) 0%, rgba(147, 51, 234, 0.08) 100%)", 
                                        border: "1px solid rgba(59, 130, 246, 0.3)",
                                        boxShadow: "0 10px 25px -5px rgba(0, 0, 0, 0.2)"
                                    }}>
                                    <div className="flex items-center justify-between border-b border-blue-500/20 pb-2">
                                        <div className="flex items-center gap-2">
                                            <span className="text-xl">🤖</span>
                                            <span className="text-sm font-bold text-blue-100 tracking-wide uppercase">Parecer do Consultor IA</span>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold uppercase ${
                                                av.ia_confianca === "alta" ? "bg-green-500/20 text-green-400" : 
                                                av.ia_confianca === "media" ? "bg-amber-500/20 text-amber-400" : 
                                                "bg-red-500/20 text-red-400"
                                            }`}>
                                                Confiança: {av.ia_confianca}
                                            </span>
                                            <NotaBadge nota={av.ia_nota_sugerida} size="sm" />
                                        </div>
                                    </div>

                                    {/* Decision Summary */}
                                    <div className={`text-xs font-semibold px-3 py-2 rounded-lg ${
                                        av.ia_decisao === "permanece" ? "bg-green-500/10 text-green-400" :
                                        av.ia_decisao === "insuficiente" ? "bg-amber-500/10 text-amber-400" :
                                        "bg-red-500/10 text-red-400"
                                    }`}>
                                        Veredito Sugerido: {av.ia_decisao?.toUpperCase()}
                                    </div>

                                    {/* Points */}
                                    {(pontosAtendidos.length > 0 || pontosFaltantes.length > 0) && (
                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                                            {pontosAtendidos.length > 0 && (
                                                <div className="bg-slate-900/40 p-3 rounded-lg border border-green-500/10">
                                                    <p className="text-green-400 font-bold mb-2 flex items-center gap-1.5">
                                                        <span className="text-sm">✅</span> PONTOS ATENDIDOS:
                                                    </p>
                                                    <ul className="text-slate-300 space-y-1.5 leading-snug">
                                                        {pontosAtendidos.map((p, i) => <li key={i} className="flex gap-2">
                                                            <span className="text-green-500/50">•</span>
                                                            <span>{p}</span>
                                                        </li>)}
                                                    </ul>
                                                </div>
                                            )}
                                            {pontosFaltantes.length > 0 && (
                                                <div className="bg-slate-900/40 p-3 rounded-lg border border-red-500/10">
                                                    <p className="text-red-400 font-bold mb-2 flex items-center gap-1.5">
                                                        <span className="text-sm">❌</span> DIVERGÊNCIAS / GAPS:
                                                    </p>
                                                    <ul className="text-slate-300 space-y-1.5 leading-snug">
                                                        {pontosFaltantes.map((p, i) => <li key={i} className="flex gap-2">
                                                            <span className="text-red-500/50">•</span>
                                                            <span>{p}</span>
                                                        </li>)}
                                                    </ul>
                                                </div>
                                            )}
                                        </div>
                                    )}

                                    {/* Detailed analysis toggle */}
                                    {av.ia_analise_detalhada && (
                                        <div className="pt-1">
                                            <button onClick={() => setShowIaDetail(!showIaDetail)}
                                                className="text-[11px] font-bold text-blue-400 hover:text-blue-300 flex items-center gap-1 transition-all">
                                                {showIaDetail ? "▼ OCULTAR" : "▶ VER"} ANÁLISE TÉCNICA DO SQUAD
                                            </button>
                                            {showIaDetail && (
                                                <div className="mt-3 p-4 bg-black/30 rounded-xl border border-blue-500/10 animate-scale-in">
                                                    <p className="text-xs text-slate-300 leading-relaxed whitespace-pre-wrap max-h-60 overflow-y-auto custom-scrollbar">
                                                        {av.ia_analise_detalhada}
                                                    </p>
                                                </div>
                                            )}
                                        </div>
                                    )}
                                </div>
                            )}

                            {/* ── Divergence Banner ── */}
                            {divergencia && (
                                <div className="text-xs text-amber-100 bg-gradient-to-r from-amber-900/40 to-amber-800/20 border border-amber-600/30 rounded-xl p-4 shadow-lg animate-pulse-subtle">
                                    <div className="flex items-center gap-2 mb-1.5">
                                        <span className="text-lg">⚠️</span>
                                        <strong className="text-amber-400 uppercase tracking-wider">Divergência detectada!</strong>
                                    </div>
                                    <p className="text-amber-200/80 mb-2 leading-relaxed">{divergencia}</p>
                                    <div className="h-px bg-amber-500/20 my-2" />
                                    <span className="text-slate-400 italic">O Consultor IA sugere uma nota diferente do Self-Assessment. Analise as evidências cuidadosamente.</span>
                                </div>
                            )}

                            {av.ia_status === "ok" && (
                                <div className="text-xs text-blue-300 bg-blue-900/15 rounded-lg p-2">
                                    💡 Aceite a sugestão da IA, sobrescreva manualmente abaixo, ou revise colaborativamente com a IA.
                                </div>
                            )}

                            {/* ── Decision Form ── */}
                            <div className="space-y-4">
                                <h4 className="text-sm font-semibold text-white">Decisão Final do Auditor:</h4>

                                <div className="grid grid-cols-2 gap-2">
                                    {Object.entries(DECISAO_CONFIG).map(([key, cfg]) => (
                                        <button key={key}
                                            onClick={() => setDecisao(key)}
                                            className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium transition-all duration-200
                        ${decisao === key
                                                    ? "ring-2 ring-offset-1 ring-offset-slate-800 shadow-lg"
                                                    : "opacity-60 hover:opacity-90"
                                                }`}
                                            style={{
                                                background: decisao === key ? cfg.bg : "rgba(51, 65, 85, 0.3)",
                                                color: decisao === key ? cfg.color : "#94a3b8",
                                            }}>
                                            {cfg.icon} {cfg.label}
                                        </button>
                                    ))}
                                </div>

                                {/* Nota livre for insuficiente */}
                                {decisao === "insuficiente" && notaSa > 0 && (
                                    <div className="flex items-center gap-3">
                                        <label className="text-sm text-slate-400">Nota manual:</label>
                                        <select
                                            value={notaLivre ?? ""}
                                            onChange={(e) => setNotaLivre(e.target.value ? Number(e.target.value) : null)}
                                            className="bg-slate-700 border border-slate-600 rounded-lg px-3 py-1.5 text-sm text-white">
                                            <option value="">Automática (SA−1)</option>
                                            {Array.from({ length: Math.max(0, notaSa) }, (_, i) => i).map((n) => (
                                                <option key={n} value={n}>{n}</option>
                                            ))}
                                        </select>
                                    </div>
                                )}

                                {/* Nota livre for aumentar */}
                                {decisao === "aumentar" && notaSa < 4 && (
                                    <div className="flex items-center gap-3">
                                        <label className="text-sm text-slate-400">Nota manual:</label>
                                        <select
                                            value={notaLivre ?? ""}
                                            onChange={(e) => setNotaLivre(e.target.value ? Number(e.target.value) : null)}
                                            className="bg-slate-700 border border-slate-600 rounded-lg px-3 py-1.5 text-sm text-white">
                                            <option value="">Automática (SA+1)</option>
                                            {Array.from({ length: 4 - notaSa }, (_, i) => notaSa + 1 + i).map((n) => (
                                                <option key={n} value={n}>{n}</option>
                                            ))}
                                        </select>
                                    </div>
                                )}

                                {/* Nota Final Preview */}
                                <div className="flex items-center gap-3">
                                    <span className="text-sm text-slate-400 font-medium">Nota Final:</span>
                                    <NotaBadge nota={notaFinal} />
                                </div>

                                {/* Description NC */}
                                {(decisao === "insuficiente" || decisao === "inexistente" || decisao === "aumentar") && (
                                    <div>
                                        <label className="text-sm text-slate-400 block mb-1.5">
                                            {decisao === "aumentar" ? "📝 Justificativa do Aumento" : "📝 Descrição da Não Conformidade"}
                                        </label>
                                        <textarea
                                            value={descNc || effectiveDescNc}
                                            onChange={(e) => setDescNc(e.target.value)}
                                            placeholder="Descreva o que falta ou por que a evidência não é válida..."
                                            className="w-full bg-slate-700/50 border border-slate-600 rounded-xl px-4 py-3 text-sm text-white placeholder-slate-500 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all resize-none"
                                            rows={4}
                                        />
                                    </div>
                                )}

                                {/* Show saved desc_nc readonly when permanece */}
                                {decisao === "permanece" && av.descricao_nc && (
                                    <div>
                                        <label className="text-sm text-slate-400 block mb-1.5">📝 Descrição (salva)</label>
                                        <div className="bg-slate-700/30 rounded-xl px-4 py-3 text-sm text-slate-400 max-h-32 overflow-y-auto">
                                            {av.descricao_nc.slice(0, 2000)}
                                        </div>
                                    </div>
                                )}

                                {/* Comments */}
                                <div>
                                    <label className="text-sm text-slate-400 block mb-1.5">💬 Comentários</label>
                                    <textarea
                                        value={comentarios}
                                        onChange={(e) => setComentarios(e.target.value)}
                                        placeholder="Observações, recomendações..."
                                        className="w-full bg-slate-700/50 border border-slate-600 rounded-xl px-4 py-3 text-sm text-white placeholder-slate-500 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all resize-none"
                                        rows={2}
                                    />
                                </div>

                                {/* Action Buttons */}
                                <div className="flex flex-col gap-3 pt-2">
                                    {(apiKey || aiProvider === 'ollama') && (
                                        <button 
                                            onClick={handleAnalyze} 
                                            disabled={analyzing || saving}
                                            className={`w-full flex items-center justify-center gap-2 px-5 py-3.5 rounded-xl font-bold text-sm transition-all duration-300 shadow-xl ${
                                                analyzing 
                                                ? "bg-purple-900/50 text-purple-300 cursor-not-allowed" 
                                                : "bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-500 hover:to-blue-500 text-white shadow-purple-600/20 hover:scale-[1.02] active:scale-95"
                                            }`}
                                        >
                                            {analyzing ? (
                                                <><span className="animate-spin text-lg">🤖</span> ANALISANDO EVIDÊNCIAS...</>
                                            ) : (
                                                <>🤖 ANALISAR SUBITEM COM IA</>
                                            )}
                                        </button>
                                    )}

                                    <div className="flex gap-3">
                                        <button onClick={handleSave} disabled={saving || analyzing}
                                            className="flex-1 flex items-center justify-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-800 disabled:opacity-50 text-white rounded-xl font-medium text-sm transition-all duration-200 shadow-lg shadow-blue-600/20 active:scale-95">
                                            {saving ? <span className="animate-pulse">Salvando...</span> : <>💾 Salvar Decisão</>}
                                        </button>

                                        {(apiKey || aiProvider === 'ollama') && (
                                            <button onClick={() => setShowChat(!showChat)}
                                                className={`flex items-center gap-2 px-5 py-2.5 rounded-xl font-medium text-sm transition-all active:scale-95 ${showChat ? "bg-emerald-600 hover:bg-emerald-700 text-white shadow-lg shadow-emerald-600/20" : "bg-slate-700 hover:bg-slate-600 text-slate-200 border border-slate-600"
                                                    }`}>
                                                💬 {showChat ? "Fechar Chat" : "Chat com Consultor IA"}
                                            </button>
                                        )}
                                    </div>
                                </div>

                                {/* Chat Panel */}
                                {showChat && apiKey && (
                                    <ChatPanel
                                        avaliacaoId={av.id}
                                        auditoriaId={av.auditoria_id}
                                        praticaNum={av.pratica_num}
                                        subitemIdx={av.subitem_idx}
                                        apiKey={apiKey}
                                    />
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Toast */}
            {toast && <div className="toast">{toast}</div>}

            {/* ═══ LIGHTBOX OVERLAY ═══ */}
            {lightboxIndex !== null && evidence && evidence.images.length > 0 && (
                <div
                    className="fixed inset-0 z-[100] flex flex-col items-center justify-center bg-black/95 backdrop-blur-md transition-all animate-fade-in"
                    onClick={() => setLightboxIndex(null)}
                    onKeyDown={(e) => {
                        if (e.key === "Escape") setLightboxIndex(null);
                        if (e.key === "ArrowRight" && evidence) setLightboxIndex(Math.min(lightboxIndex + 1, evidence.images.length - 1));
                        if (e.key === "ArrowLeft" && evidence) setLightboxIndex(Math.max(lightboxIndex - 1, 0));
                    }}
                    tabIndex={0}
                    ref={(el) => (el as HTMLElement)?.focus?.()}
                >
                    {/* Header bar */}
                    <div className="w-full flex items-center justify-between p-4 bg-black/40 z-10">
                        <div className="flex flex-col">
                            <span className="text-white font-medium text-sm">
                                {evidence.images[lightboxIndex]?.name}
                            </span>
                            <span className="text-slate-500 text-[10px]">
                                {lightboxIndex + 1} de {evidence.images.length}
                            </span>
                        </div>
                        <button
                            onClick={(e) => { e.stopPropagation(); setLightboxIndex(null); }}
                            className="w-10 h-10 flex items-center justify-center rounded-xl bg-white/5 hover:bg-white/10 text-white transition-all text-xl"
                        >
                            ✕
                        </button>
                    </div>

                    {/* Main Image View Port */}
                    <div className="flex-1 w-full relative flex items-center justify-center p-4 md:p-12">
                        {/* Prev arrow */}
                        {lightboxIndex > 0 && (
                            <button
                                onClick={(e) => { e.stopPropagation(); setLightboxIndex(lightboxIndex - 1); }}
                                className="absolute left-4 z-20 w-14 h-14 flex items-center justify-center rounded-full bg-white/5 hover:bg-white/10 text-white text-3xl transition-all"
                            >
                                ‹
                            </button>
                        )}

                        {/* Next arrow */}
                        {lightboxIndex < evidence.images.length - 1 && (
                            <button
                                onClick={(e) => { e.stopPropagation(); setLightboxIndex(lightboxIndex + 1); }}
                                className="absolute right-4 z-20 w-14 h-14 flex items-center justify-center rounded-full bg-white/5 hover:bg-white/10 text-white text-3xl transition-all"
                            >
                                ›
                            </button>
                        )}

                        {/* The Image */}
                        <div className="relative w-full h-full flex items-center justify-center">
                            <img
                                src={`${API_BASE}/api/evidencias/file?path=${encodeURIComponent(evidence?.images[lightboxIndex]?.path || "")}`}
                                alt={evidence?.images[lightboxIndex]?.name}
                                className="max-w-full max-h-full object-contain rounded-sm shadow-[0_0_50px_rgba(0,0,0,0.5)] animate-scale-in"
                                onClick={(e) => e.stopPropagation()}
                            />
                        </div>
                    </div>

                    {/* Minimal Controls/Status */}
                    <div className="p-6 w-full flex justify-center gap-4 bg-gradient-to-t from-black/60 to-transparent">
                        <button 
                            onClick={(e) => { 
                                e.stopPropagation(); 
                                if (evidence?.images[lightboxIndex]) {
                                    window.open(`${API_BASE}/api/evidencias/file?path=${encodeURIComponent(evidence.images[lightboxIndex].path)}`, '_blank'); 
                                }
                            }}
                            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-semibold shadow-lg transition-all"
                        >
                            📥 Baixar Original
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
