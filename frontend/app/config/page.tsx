"use client";

import { useEffect, useState } from "react";
import { api, Auditoria, API_BASE } from "@/lib/api";

interface GlobalConfig {
    openai_api_key: string;
    ai_provider: string;
    ai_base_url: string;
    default_modo_analise: string;
    has_key: boolean;
    db_path: string;
}

export default function ConfigPage() {
    const [activeTab, setActiveTab] = useState<"sistema" | "auditoria" | "ialocal">("sistema");
    const [auditorias, setAuditorias] = useState<Auditoria[]>([]);
    const [selectedId, setSelectedId] = useState<number | null>(null);
    const [globalConfig, setGlobalConfig] = useState<GlobalConfig>({
        openai_api_key: "",
        ai_provider: "openai",
        ai_base_url: "",
        default_modo_analise: "completo",
        has_key: false,
        db_path: "Carregando..."
    });
    const [auditConfig, setAuditConfig] = useState({ 
        assessment_file_path: "", 
        evidence_folder_path: "", 
        openai_api_key: "", 
        ai_provider: "" as "" | "openai" | "ollama" | "gemini" | "anthropic" | "interno",
        ai_base_url: "",
        observacoes: "",
        modo_analise: "completo" as "completo" | "economico"
    });
    
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [toast, setToast] = useState<{ msg: string; type: "success" | "error" } | null>(null);
    const [knowledge, setKnowledge] = useState<any[]>([]);
    const [iaGenerating, setIaGenerating] = useState(false);

    useEffect(() => {
        loadData();
    }, []);

    async function loadData() {
        setLoading(true);
        try {
            const [auds, gConfig, kb] = await Promise.all([
                api.listAuditorias(),
                fetch(`${API_BASE}/api/config/global`).then(r => r.json()),
                fetch(`${API_BASE}/api/config/knowledge`).then(r => r.json())
            ]);
            setAuditorias(auds);
            setGlobalConfig(gConfig);
            setKnowledge(kb);
            if (auds.length > 0) setSelectedId(auds[0].id);
        } catch (e) {
            showToast("Erro ao carregar configurações", "error");
        } finally {
            setLoading(false);
        }
    }

    useEffect(() => {
        if (!selectedId) return;
        api.getAuditoria(selectedId).then(aud => {
            setAuditConfig({
                assessment_file_path: aud.assessment_file_path || "",
                evidence_folder_path: aud.evidence_folder_path || "",
                openai_api_key: aud.openai_api_key || "",
                ai_provider: (aud.ai_provider as any) || "",
                ai_base_url: aud.ai_base_url || "",
                observacoes: aud.observacoes || "",
                modo_analise: (aud.modo_analise as "completo" | "economico") || "completo",
            });
        });
    }, [selectedId]);

    function showToast(msg: string, type: "success" | "error" = "success") {
        setToast({ msg, type });
        setTimeout(() => setToast(null), 3000);
    }

    async function handleSaveGlobal() {
        setSaving(true);
        try {
            const res = await fetch(`${API_BASE}/api/config/global`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    openai_api_key: globalConfig.openai_api_key,
                    ai_provider: globalConfig.ai_provider,
                    ai_base_url: globalConfig.ai_base_url,
                    default_modo_analise: globalConfig.default_modo_analise
                }),
            });
            if (res.ok) {
                showToast("Configurações do sistema salvas!");
                // Re-fetch to get masked key
                const fresh = await fetch(`${API_BASE}/api/config/global`).then(r => r.json());
                setGlobalConfig(fresh);
            } else throw new Error();
        } catch {
            showToast("Erro ao salvar configurações globais", "error");
        } finally {
            setSaving(false);
        }
    }

    async function handleSaveAudit() {
        if (!selectedId) return;
        setSaving(true);
        try {
            await fetch(`${API_BASE}/api/auditorias/${selectedId}/config`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(auditConfig),
            });
            showToast("Configurações da auditoria salvas!");
        } catch {
            showToast("Erro ao salvar", "error");
        } finally {
            setSaving(false);
        }
    }

    async function handleDeleteAudit() {
        if (!selectedId) return;
        const aud = auditorias.find(a => a.id === selectedId);
        if (!confirm(`Tem certeza que deseja excluir a auditoria "${aud?.unidade} - ${aud?.area}"? Esta ação é irreversível.`)) return;

        try {
            const res = await fetch(`${API_BASE}/api/config/auditorias/${selectedId}`, { method: "DELETE" });
            if (res.ok) {
                showToast("Auditoria excluída com sucesso");
                loadData();
            } else throw new Error();
        } catch {
            showToast("Erro ao excluir auditoria", "error");
        }
    }

    if (loading) return <div className="flex items-center justify-center h-64"><div className="text-4xl animate-pulse">⚙️</div></div>;

    return (
        <div className="animate-fade-in max-w-4xl mx-auto pb-20">
            <header className="mb-8">
                <h1 className="text-3xl font-bold text-white mb-2">⚙️ Configurações</h1>
                <p className="text-slate-400">Gerencie as preferências globais e locais do sistema</p>
            </header>

            {/* Tabs Navigation */}
            <div className="flex gap-2 mb-8 p-1 bg-slate-800/50 backdrop-blur-md rounded-2xl w-fit border border-slate-700">
                <button 
                    onClick={() => setActiveTab("sistema")}
                    className={`px-6 py-2.5 rounded-xl font-medium transition-all ${activeTab === "sistema" ? "bg-blue-600 text-white shadow-lg" : "text-slate-400 hover:text-white"}`}
                >
                    🖥️ Sistema
                </button>
                <button 
                    onClick={() => setActiveTab("auditoria")}
                    className={`px-6 py-2.5 rounded-xl font-medium transition-all ${activeTab === "auditoria" ? "bg-blue-600 text-white shadow-lg" : "text-slate-400 hover:text-white"}`}
                >
                    📍 Por Auditoria
                </button>
                <button 
                    onClick={() => setActiveTab("ialocal")}
                    className={`px-6 py-2.5 rounded-xl font-medium transition-all ${activeTab === "ialocal" ? "bg-blue-600 text-white shadow-lg" : "text-slate-400 hover:text-white"}`}
                >
                    🧠 IA Local & Memória
                </button>
            </div>

            {activeTab === "sistema" && (
                <div className="space-y-6">
                    <section className="glass-card p-8">
                        <h3 className="text-xl font-semibold text-white mb-6 flex items-center gap-2">
                            <span>🔑 Integração AI</span>
                            <span className="text-[10px] bg-blue-500/20 text-blue-400 px-2 py-0.5 rounded-full uppercase tracking-wider">Global</span>
                        </h3>
                        
                        <div className="space-y-4">
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm font-medium text-slate-300 mb-2">Provedor de AI</label>
                                    <select 
                                        value={globalConfig.ai_provider}
                                        onChange={e => setGlobalConfig({ ...globalConfig, ai_provider: e.target.value })}
                                        className="w-full bg-slate-900/50 border border-slate-700 focus:border-blue-500 rounded-xl px-4 py-3 text-white text-sm transition-all outline-none"
                                    >
                                        <option value="openai">OpenAI (Padrão)</option>
                                        <option value="ollama">Ollama (Local)</option>
                                        <option value="gemini">Google Gemini</option>
                                        <option value="anthropic">Anthropic Claude</option>
                                        <option value="interno">Sistema Interno (Sem API Externas)</option>
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-slate-300 mb-2">Chave API / Token</label>
                                    <div className="relative">
                                        <input 
                                            type="password" 
                                            value={globalConfig.openai_api_key} 
                                            onChange={e => setGlobalConfig({ ...globalConfig, openai_api_key: e.target.value })}
                                            className="w-full bg-slate-900/50 border border-slate-700 focus:border-blue-500 rounded-xl px-4 py-3 text-white text-sm transition-all"
                                            placeholder={globalConfig.has_key ? "Configurada (digite para alterar)" : "sk-... ou token"}
                                        />
                                        {globalConfig.has_key && (
                                            <div className="absolute right-3 top-3 text-green-500 text-xs flex items-center gap-1">
                                                <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" /> Ativa
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>

                            {globalConfig.ai_provider !== "openai" && globalConfig.ai_provider !== "interno" && (
                                <div>
                                    <label className="block text-sm font-medium text-slate-300 mb-2">Endpoint / Base URL (Opcional)</label>
                                    <input 
                                        type="text" 
                                        value={globalConfig.ai_base_url} 
                                        onChange={e => setGlobalConfig({ ...globalConfig, ai_base_url: e.target.value })}
                                        className="w-full bg-slate-900/50 border border-slate-700 focus:border-blue-500 rounded-xl px-4 py-3 text-white text-sm transition-all"
                                        placeholder={globalConfig.ai_provider === "ollama" ? "http://localhost:11434/v1" : "https://api..."}
                                    />
                                    <p className="text-[10px] text-slate-500 mt-2">
                                        Deixe vazio para usar o endpoint padrão do provedor.
                                    </p>
                                </div>
                            )}

                            <div>
                                <label className="block text-sm font-medium text-slate-300 mb-2">Modo de Análise Padrão</label>
                                <div className="grid grid-cols-2 gap-4">
                                    {["completo", "economico"].map(m => (
                                        <button 
                                            key={m}
                                            onClick={() => setGlobalConfig({ ...globalConfig, default_modo_analise: m })}
                                            className={`p-4 rounded-xl border transition-all text-left ${globalConfig.default_modo_analise === m ? "border-blue-500 bg-blue-500/10 ring-1 ring-blue-500" : "border-slate-700 bg-slate-900/50 hover:border-slate-600"}`}
                                        >
                                            <div className="font-semibold text-white capitalize">{m === "completo" ? "🚀 Completo" : "💰 Econômico"}</div>
                                            <div className="text-[10px] text-slate-400 mt-1">
                                                {m === "completo" ? "GPT-4o — Melhor qualidade" : "GPT-4o-mini — Menor custo"}
                                            </div>
                                        </button>
                                    ))}
                                </div>
                            </div>
                        </div>

                        <button 
                            onClick={handleSaveGlobal} 
                            disabled={saving}
                            className="w-full mt-8 py-3.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded-xl font-semibold transition-all shadow-lg shadow-blue-600/20"
                        >
                            {saving ? "Salvando..." : "💾 Salvar Configurações Globais"}
                        </button>
                    </section>

                    <section className="glass-card p-6 bg-slate-900/20 border-slate-800">
                        <h4 className="text-sm font-semibold text-slate-300 mb-4 flex items-center gap-2">
                            <span>📡 Status do Sistema</span>
                        </h4>
                        <div className="grid grid-cols-2 gap-4">
                            <div className="bg-slate-900/40 p-4 rounded-xl border border-slate-800">
                                <div className="text-[10px] text-slate-500 uppercase font-bold tracking-widest mb-1">Database</div>
                                <div className="text-sm text-white font-mono truncate">{globalConfig.db_path}</div>
                            </div>
                            <div className="bg-slate-900/40 p-4 rounded-xl border border-slate-800">
                                <div className="text-[10px] text-slate-500 uppercase font-bold tracking-widest mb-1">Versão API</div>
                                <div className="text-sm text-white font-mono">v2.0.0 (FastAPI + SQL)</div>
                            </div>
                        </div>
                    </section>
                </div>
            )}

            {activeTab === "ialocal" && (
                <div className="space-y-6 animate-fade-in">
                    {/* Ollama Model Generation */}
                    <section className="glass-card p-8 border-l-4 border-l-indigo-500">
                        <div className="flex justify-between items-start mb-6">
                            <div>
                                <h3 className="text-xl font-semibold text-white flex items-center gap-2">
                                    <span>🤖 Cérebro Local (Propriedade Privada)</span>
                                </h3>
                                <p className="text-sm text-slate-400 mt-1">Crie um modelo Ollama especializado com as regras do PO.AUT.002</p>
                            </div>
                            <button 
                                onClick={async () => {
                                    setIaGenerating(true);
                                    try {
                                        await fetch(`${API_BASE}/api/config/local-ai/generate`, { method: "POST" });
                                        showToast("Processo de geração iniciado! Verifique o console do servidor.");
                                    } catch {
                                        showToast("Erro ao iniciar geração", "error");
                                    } finally {
                                        setIaGenerating(false);
                                    }
                                }}
                                disabled={iaGenerating}
                                className={`px-6 py-2.5 rounded-xl font-bold transition-all ${iaGenerating ? "bg-slate-700 text-slate-500" : "bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/20"}`}
                            >
                                {iaGenerating ? "⚙️ Gerando..." : "🚀 Gerar Cérebro Auditor-TA"}
                            </button>
                        </div>
                        
                        <div className="bg-indigo-500/5 border border-indigo-500/20 rounded-2xl p-4 text-xs text-indigo-300 leading-relaxed">
                            <p><strong>Nota:</strong> Este processo exige o Ollama instalado. Ele criará o modelo <code>auditoria-ta</code> baseado no Llama3, injetando todo o regimento oficial e aprendizados passados para análise 100% offline.</p>
                        </div>
                    </section>

                    {/* Knowledge Base */}
                    <section className="glass-card p-8">
                        <div className="flex justify-between items-center mb-6">
                            <h3 className="text-xl font-semibold text-white flex items-center gap-2">
                                <span>📚 Base de Conhecimento (RAG)</span>
                            </h3>
                            <button 
                                onClick={async () => {
                                    showToast("Re-indexando arquivos...");
                                    await fetch(`${API_BASE}/api/config/knowledge/reindex`, { method: "POST" });
                                    setTimeout(loadData, 2000);
                                }}
                                className="text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 px-3 py-1.5 rounded-lg border border-slate-700 transition-all"
                            >
                                🔄 Re-indexar Pasta Local
                            </button>
                        </div>

                        <div className="space-y-3 max-h-[400px] overflow-y-auto pr-2 custom-scrollbar">
                            {knowledge.length === 0 ? (
                                <div className="text-center py-12 border-2 border-dashed border-slate-800 rounded-2xl">
                                    <p className="text-slate-500 text-sm">Nenhum documento técnico indexado.</p>
                                    <p className="text-[10px] text-slate-600 mt-2">Coloque PDFs ou TXTs em <code>C:\AuditoriaTA\base_conhecimento</code> e clique em Re-indexar.</p>
                                </div>
                            ) : (
                                knowledge.map((kb, idx) => (
                                    <div key={idx} className="bg-slate-900/40 border border-slate-800/50 p-4 rounded-xl hover:border-slate-700 transition-all">
                                        <div className="flex justify-between items-start mb-1">
                                            <span className="text-sm font-semibold text-slate-200">{kb.titulo}</span>
                                            <span className="text-[10px] bg-slate-800 text-slate-400 px-2 py-0.5 rounded uppercase">{kb.tag}</span>
                                        </div>
                                        <p className="text-[11px] text-slate-500 line-clamp-2 italic">"{kb.conteudo.substring(0, 150)}..."</p>
                                        <div className="text-[9px] text-slate-600 mt-2 flex justify-between">
                                            <span>Fonte: {kb.fonte}</span>
                                            <span>{new Date(kb.data_criacao).toLocaleDateString()}</span>
                                        </div>
                                    </div>
                                ))
                            )}
                        </div>
                    </section>

                    {/* Learning Stats */}
                    <section className="grid grid-cols-3 gap-4">
                        <div className="glass-card p-4 text-center">
                            <div className="text-2xl mb-1">🧠</div>
                            <div className="text-xl font-bold text-white">{knowledge.length}</div>
                            <div className="text-[10px] text-slate-500 uppercase tracking-wider">Documentos Técnicos</div>
                        </div>
                        <div className="glass-card p-4 text-center border-b-4 border-b-amber-500">
                            <div className="text-2xl mb-1">💡</div>
                            <div className="text-xl font-bold text-white">Ativa</div>
                            <div className="text-[10px] text-slate-500 uppercase tracking-wider">Memória de Curto Prazo</div>
                        </div>
                        <div className="glass-card p-4 text-center">
                            <div className="text-2xl mb-1">🛡️</div>
                            <div className="text-xl font-bold text-white">Privado</div>
                            <div className="text-[10px] text-slate-500 uppercase tracking-wider">Segurança de Dados</div>
                        </div>
                    </section>
                </div>
            )}

            {activeTab === "auditoria" && (
                <div className="space-y-6">
                    <div className="glass-card p-6">
                        <label className="text-sm text-slate-300 block mb-3 font-medium">Selecione a auditoria para configurar:</label>
                        <select 
                            value={selectedId ?? ""} 
                            onChange={e => setSelectedId(Number(e.target.value))}
                            className="w-full bg-slate-900/50 border border-slate-700 focus:border-blue-500 rounded-xl px-4 py-3 text-white transition-all outline-none"
                        >
                            {auditorias.map(a => (
                                <option key={a.id} value={a.id}>{a.unidade} — {a.area} ({a.ciclo})</option>
                            ))}
                        </select>
                    </div>

                    {selectedId && (
                        <div className="glass-card p-8 space-y-6 border-t-4 border-t-blue-500">
                            <div className="grid grid-cols-2 gap-6">
                                <div>
                                    <label className="block text-sm font-medium text-slate-300 mb-2">📄 Arquivo Assessment (.xlsx)</label>
                                    <input 
                                        type="text" 
                                        value={auditConfig.assessment_file_path} 
                                        onChange={e => setAuditConfig({ ...auditConfig, assessment_file_path: e.target.value })}
                                        className="w-full bg-slate-900/50 border border-slate-700 focus:border-blue-500 rounded-xl px-4 py-3 text-white text-sm transition-all"
                                        placeholder="C:\..." 
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-slate-300 mb-2">📁 Pasta de Evidências</label>
                                    <input 
                                        type="text" 
                                        value={auditConfig.evidence_folder_path} 
                                        onChange={e => setAuditConfig({ ...auditConfig, evidence_folder_path: e.target.value })}
                                        className="w-full bg-slate-900/50 border border-slate-700 focus:border-blue-500 rounded-xl px-4 py-3 text-white text-sm transition-all"
                                        placeholder="C:\..." 
                                    />
                                </div>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-slate-300 mb-2">
                                    🔑 Chave API específica <span className="text-[10px] text-slate-500 font-normal ml-2">(Opcional)</span>
                                </label>
                                <input 
                                    type="password" 
                                    value={auditConfig.openai_api_key} 
                                    onChange={e => setAuditConfig({ ...auditConfig, openai_api_key: e.target.value })}
                                    className="w-full bg-slate-900/50 border border-slate-700 focus:border-blue-500 rounded-xl px-4 py-3 text-white text-sm transition-all"
                                    placeholder="Deixe vazio para usar a chave global" 
                                />
                            </div>

                            <div className="grid grid-cols-2 gap-6">
                                <div>
                                    <label className="block text-sm font-medium text-slate-300 mb-2">🤖 Provedor de IA (Específico)</label>
                                    <select 
                                        value={auditConfig.ai_provider}
                                        onChange={e => setAuditConfig({ ...auditConfig, ai_provider: e.target.value as any })}
                                        className="w-full bg-slate-900/50 border border-slate-700 focus:border-blue-500 rounded-xl px-4 py-3 text-white text-sm transition-all outline-none"
                                    >
                                        <option value="">Usar Configuração Global Padrão</option>
                                        <option value="interno">Sistema Interno (Sem API Externas)</option>
                                        <option value="openai">OpenAI</option>
                                        <option value="ollama">Ollama (Local)</option>
                                        <option value="gemini">Google Gemini</option>
                                        <option value="anthropic">Anthropic Claude</option>
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-slate-300 mb-2">Endpoint / Base URL (Específico)</label>
                                    <input 
                                        type="text" 
                                        value={auditConfig.ai_base_url} 
                                        onChange={e => setAuditConfig({ ...auditConfig, ai_base_url: e.target.value })}
                                        disabled={auditConfig.ai_provider === "" || auditConfig.ai_provider === "openai" || auditConfig.ai_provider === "interno"}
                                        className="w-full bg-slate-900/50 border border-slate-700 focus:border-blue-500 rounded-xl px-4 py-3 text-white text-sm transition-all disabled:opacity-50"
                                        placeholder="Deixe vazio para usar o Global" 
                                    />
                                </div>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-slate-300 mb-2">📝 Observações</label>
                                <textarea 
                                    value={auditConfig.observacoes} 
                                    onChange={e => setAuditConfig({ ...auditConfig, observacoes: e.target.value })}
                                    className="w-full bg-slate-900/50 border border-slate-700 focus:border-blue-500 rounded-xl px-4 py-3 text-white text-sm resize-none transition-all h-24"
                                    placeholder="Notas de contexto para o auditor..." 
                                />
                            </div>

                            <div className="h-px bg-slate-800/50 w-full" />

                            <div className="space-y-4">
                                <label className="flex items-center text-sm font-semibold text-slate-300 ml-1">
                                    <span className="mr-2">🧠</span> Modo de Análise (Para esta auditoria)
                                </label>
                                
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    {/* Completo */}
                                    <div 
                                        onClick={() => setAuditConfig({ ...auditConfig, modo_analise: "completo" })}
                                        className={`relative overflow-hidden cursor-pointer group p-5 rounded-2xl border-2 transition-all duration-300 ${
                                            auditConfig.modo_analise === "completo" 
                                            ? "border-blue-500 bg-blue-500/10 shadow-[0_0_20px_rgba(59,130,246,0.1)]" 
                                            : "border-slate-800 bg-slate-900/30 hover:border-slate-700"
                                        }`}
                                    >
                                        <div className="flex items-center justify-between mb-2">
                                            <h3 className={`font-bold text-sm ${auditConfig.modo_analise === "completo" ? "text-blue-400" : "text-white"}`}>
                                                Modo Completo
                                            </h3>
                                            <span className="bg-blue-500/20 text-blue-400 text-[8px] px-2 py-0.5 rounded-full font-bold uppercase tracking-wider">
                                                GPT-4o
                                            </span>
                                        </div>
                                        <p className="text-[10px] text-slate-400 leading-relaxed">Alta qualidade, todos os docs lidos, ideal para revisão final.</p>
                                    </div>

                                    {/* Econômico */}
                                    <div 
                                        onClick={() => setAuditConfig({ ...auditConfig, modo_analise: "economico" })}
                                        className={`relative overflow-hidden cursor-pointer group p-5 rounded-2xl border-2 transition-all duration-300 ${
                                            auditConfig.modo_analise === "economico" 
                                            ? "border-emerald-500 bg-emerald-500/10 shadow-[0_0_20px_rgba(16,185,129,0.1)]" 
                                            : "border-slate-800 bg-slate-900/30 hover:border-slate-700"
                                        }`}
                                    >
                                        <div className="flex items-center justify-between mb-2">
                                            <h3 className={`font-bold text-sm ${auditConfig.modo_analise === "economico" ? "text-emerald-400" : "text-white"}`}>
                                                Modo Econômico
                                            </h3>
                                            <span className="bg-emerald-500/20 text-emerald-400 text-[8px] px-2 py-0.5 rounded-full font-bold uppercase tracking-wider">
                                                GPT-4o-mini
                                            </span>
                                        </div>
                                        <p className="text-[10px] text-slate-400 leading-relaxed">Rápido e ~10x mais barato. Ideal para análise inicial.</p>
                                    </div>
                                </div>
                            </div>

                            <div className="flex gap-4 pt-4">
                                <button 
                                    onClick={handleSaveAudit} 
                                    disabled={saving}
                                    className="flex-1 py-3.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded-xl font-semibold transition-all shadow-lg"
                                >
                                    {saving ? "Salvando..." : "💾 Salvar Auditoria"}
                                </button>
                                <button 
                                    onClick={handleDeleteAudit}
                                    className="px-6 py-3.5 bg-red-500/10 hover:bg-red-500 text-red-500 hover:text-white border border-red-500/20 rounded-xl font-semibold transition-all"
                                    title="Excluir Auditoria"
                                >
                                    🗑️ Excluir
                                </button>
                            </div>
                        </div>
                    )}
                </div>
            )}

            {toast && (
                <div className={`fixed bottom-8 right-8 px-6 py-3 rounded-xl text-white shadow-2xl animate-bounce-in flex items-center gap-3 backdrop-blur-xl border ${toast.type === "success" ? "bg-green-600/90 border-green-500" : "bg-red-600/90 border-red-500"}`}>
                    <span className="text-xl">{toast.type === "success" ? "✅" : "❌"}</span>
                    <span className="font-medium text-sm">{toast.msg}</span>
                </div>
            )}
        </div>
    );
}
