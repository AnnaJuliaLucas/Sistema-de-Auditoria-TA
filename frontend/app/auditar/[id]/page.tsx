"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import { api, Auditoria, Pratica } from "@/lib/api";
import Link from "next/link";
import SubitemCard from "@/components/SubitemCard";
import NotaBadge from "@/components/NotaBadge";
import { cleanTitle } from "@/lib/utils";

export default function AuditarPage() {
    const { id } = useParams<{ id: string }>();
    const auditoriaId = Number(id);

    const [auditoria, setAuditoria] = useState<Auditoria | null>(null);
    const [praticas, setPraticas] = useState<Pratica[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [expandedPraticas, setExpandedPraticas] = useState<Set<number>>(new Set());
    const [stats, setStats] = useState<{ total: number; avaliados: number; ia_ok: number; media_final: number | null; media_sa: number | null } | null>(null);
    const [evidenceMap, setEvidenceMap] = useState<Record<string, any>>({});
    const [criteriaMap, setCriteriaMap] = useState<Record<string, any>>({});
    const [batchAnalyzing, setBatchAnalyzing] = useState<number | null>(null);
    const [agentProgress, setAgentProgress] = useState<{ current: number; total: number; message?: string } | null>(null);

    const loadData = useCallback(async () => {
        try {
            setLoading(true);
            const [aud, pratics, st, evMap, critMap] = await Promise.all([
                api.getAuditoria(auditoriaId),
                api.listAvaliacoes(auditoriaId),
                api.getEstatisticas(auditoriaId),
                api.getAllEvidences(auditoriaId),
                api.getAllCriterios(),
            ]);
            setAuditoria(aud);
            setPraticas(pratics);
            setStats(st);
            setEvidenceMap(evMap);
            setCriteriaMap(critMap);
        } catch (e: unknown) {
            setError(e instanceof Error ? e.message : "Erro ao carregar");
        } finally {
            setLoading(false);
        }
    }, [auditoriaId]);

    async function handleUpdateStatus(status: string) {
        try {
            await api.updateStatus(auditoriaId, status);
            await loadData();
        } catch (e: unknown) {
            alert(e instanceof Error ? e.message : "Erro ao atualizar status");
        }
    }

    useEffect(() => {
        loadData();
    }, [loadData]);

    async function handleAnalyzePractice(pratica: Pratica) {
        if (!auditoria) return;
        const subitensParaAnalisar = pratica.subitens; 
        if (subitensParaAnalisar.length === 0) {
            alert("Não há subitens nesta prática.");
            return;
        }

        const msgOriginal = `Deseja analisar os ${subitensParaAnalisar.length} subitens desta prática com IA?`;
        const msgReanalise = `Deseja RE-ANALISAR os ${subitensParaAnalisar.length} subitens desta prática com IA?\n(As notas e comentários da IA serão atualizados)`;
        
        const temJaAnalisados = subitensParaAnalisar.some(s => s.decisao !== 'pendente');
        if (!confirm(temJaAnalisados ? msgReanalise : msgOriginal)) return;

        setBatchAnalyzing(pratica.pratica_num);
        setAgentProgress({ current: 0, total: subitensParaAnalisar.length, message: `Iniciando análise da prática ${pratica.pratica_num}...` });

        try {
            const response = await api.runAgentSelection(auditoriaId, {
                selecionados: subitensParaAnalisar.map(s => s.id),
                provider: auditoria.ai_provider || "",
                base_url: auditoria.ai_base_url || "",
                economico: auditoria.modo_analise === 'economico'
            });

            const { job_id } = response;
            if (!job_id) {
                // Already all done (edge case)
                await loadData();
                return;
            }

            // Polling loop with 10-minute timeout
            let finished = false;
            const deadline = Date.now() + 10 * 60 * 1000;
            while (!finished) {
                if (Date.now() > deadline) {
                    throw new Error("Tempo limite de 10 minutos excedido. A análise pode ainda estar rodando em segundo plano.");
                }
                await new Promise(r => setTimeout(r, 2000));
                
                const job = await api.getAgentJobStatus(job_id);
                
                if (job.status === 'done') {
                    finished = true;
                    setAgentProgress({ current: subitensParaAnalisar.length, total: subitensParaAnalisar.length, message: "Finalizando e verificando resultados..." });
                    
                    try {
                        const resultResponse = await api.getAgentJobResult(job_id);
                        const finalResult = resultResponse.resultado;
                        
                        if (finalResult && finalResult.erros > 0) {
                            const firstErr = finalResult.detalhes_erros?.[0]?.erro || "Erro desconhecido";
                            throw new Error(`A análise terminou com ${finalResult.erros} erro(s). Primeiro erro: ${firstErr}`);
                        } else {
                            setAgentProgress({ current: subitensParaAnalisar.length, total: subitensParaAnalisar.length, message: "Concluído com sucesso!" });
                        }
                    } catch (resultErr: any) {
                        throw new Error(resultErr.message || "Erro ao obter o resultado final da análise.");
                    }
                } else if (job.status === 'error') {
                    throw new Error(job.erro || "Erro na análise do agente");
                } else if (job.status === 'running' && job.progresso) {
                    setAgentProgress({
                        current: job.progresso.current,
                        total: job.progresso.total,
                        message: `Analisando ${job.progresso.current}/${job.progresso.total}...`
                    });
                }
            }
            
            await loadData();
        } catch (e: any) {
            console.error(`Erro ao analisar prática ${pratica.pratica_num}:`, e);
            alert(`⚠️ Erro na análise da prática: ${e.message}`);
        } finally {
            setBatchAnalyzing(null);
            setAgentProgress(null);
        }
    }

    async function handleRunGlobalAgent() {
        const subitensParaAnalisar = praticas.flatMap(p => p.subitens);
        if (subitensParaAnalisar.length === 0) {
            alert("Não há subitens nesta auditoria.");
            return;
        }

        const temJaAnalisados = subitensParaAnalisar.some(s => s.decisao !== 'pendente');
        const msg = temJaAnalisados 
            ? `🚀 RE-INICIAR Agente Auditor?\n\nEle re-analisará TODOS os ${subitensParaAnalisar.length} subitens da auditoria.\n\nContinuar?`
            : `🚀 Iniciar Agente Auditor?\n\nEle analisará automaticamente os ${subitensParaAnalisar.length} subitens de forma autônoma no servidor.\n\nContinuar?`;

        if (!confirm(msg)) return;
        if (!auditoria) return;

        setBatchAnalyzing(-1); // -1 means global
        setAgentProgress({ current: 0, total: subitensParaAnalisar.length, message: "Iniciando agente..." });
        
        try {
            const response = await api.runAgentBatch(auditoriaId, {
                provider: auditoria.ai_provider || "",
                base_url: auditoria.ai_base_url || "",
                economico: auditoria.modo_analise === 'economico'
            });

            const { job_id } = response;
            if (!job_id) {
                await loadData();
                alert("✨ Todos os subitens já foram analisados.");
                return;
            }

            // Polling loop with 10-minute timeout
            let finished = false;
            const deadline = Date.now() + 10 * 60 * 1000;
            while (!finished) {
                if (Date.now() > deadline) {
                    throw new Error("Tempo limite de 10 minutos excedido. A análise pode ainda estar rodando em segundo plano.");
                }
                await new Promise(r => setTimeout(r, 3000));
                
                const job = await api.getAgentJobStatus(job_id);
                
                if (job.status === 'done') {
                    finished = true;
                    setAgentProgress({ current: subitensParaAnalisar.length, total: subitensParaAnalisar.length, message: "Finalizando e verificando resultados..." });
                    
                    try {
                        const resultResponse = await api.getAgentJobResult(job_id);
                        const finalResult = resultResponse.resultado;
                        
                        if (finalResult && finalResult.erros > 0) {
                            const firstErr = finalResult.detalhes_erros?.[0]?.erro || "Erro desconhecido";
                            throw new Error(`A análise terminou com ${finalResult.erros} erro(s). Primeiro erro: ${firstErr}`);
                        } else {
                            setAgentProgress({ current: subitensParaAnalisar.length, total: subitensParaAnalisar.length, message: "Concluído com sucesso!" });
                            alert("✨ Missão cumprida! O Agente Auditor concluiu todas as análises pendentes com sucesso.");
                        }
                    } catch (resultErr: any) {
                        throw new Error(resultErr.message || "Erro ao obter o resultado final da análise.");
                    }
                } else if (job.status === 'error') {
                    throw new Error(job.erro || "Erro na análise do agente");
                } else if (job.status === 'running' && job.progresso) {
                    setAgentProgress({
                        current: job.progresso.current,
                        total: job.progresso.total,
                        message: `Analisando item ${job.progresso.current} de ${job.progresso.total}...`
                    });
                }
            }
            
            await loadData();
        } catch (e: any) {
            console.error("Erro no Agente Auditor:", e);
            alert(`⚠️ Erro no Agente: ${e.message}`);
        } finally {
            setBatchAnalyzing(null);
            setAgentProgress(null);
        }
    }

    function togglePratica(num: number) {
        setExpandedPraticas((prev) => {
            const next = new Set(prev);
            if (next.has(num)) next.delete(num);
            else next.add(num);
            return next;
        });
    }

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="text-center">
                    <div className="text-5xl mb-4 animate-pulse">🔄</div>
                    <p className="text-slate-400 text-lg">Carregando auditoria...</p>
                </div>
            </div>
        );
    }

    if (error || !auditoria) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="glass-card p-8 text-center">
                    <div className="text-4xl mb-4">⚠️</div>
                    <p className="text-red-400 mb-3">{error || "Auditoria não encontrada"}</p>
                    <button onClick={loadData} className="px-6 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-white">
                        Tentar novamente
                    </button>
                </div>
            </div>
        );
    }

    const progress = stats ? (stats.total > 0 ? Math.round((stats.avaliados / stats.total) * 100) : 0) : 0;

    return (
        <div className="animate-fade-in">
            {/* Back Button */}
            <div className="mb-6">
                <Link href="/" className="inline-flex items-center gap-2 text-slate-400 hover:text-blue-400 transition-colors text-sm font-medium group">
                    <span className="text-lg group-hover:-translate-x-1 transition-transform">←</span>
                    Voltar para Auditorias
                </Link>
            </div>

            {/* Header */}
            <div className="glass-card p-6 mb-6">
                <div className="flex items-start justify-between mb-4">
                    <div>
                        <div className="flex items-center gap-3 mb-1">
                            <h1 className="text-2xl font-bold text-white">
                                🏭 {auditoria.area}
                            </h1>
                            <span className="text-[10px] px-2 py-0.5 rounded-full font-bold uppercase tracking-wider"
                                style={{ 
                                    background: auditoria.status === 'aprovada' ? '#a855f720' : auditoria.status === 'concluida' ? '#22c55e20' : '#3b82f620',
                                    color: auditoria.status === 'aprovada' ? '#c084fc' : auditoria.status === 'concluida' ? '#4ade80' : '#60a5fa',
                                    border: `1px solid ${auditoria.status === 'aprovada' ? '#a855f740' : auditoria.status === 'concluida' ? '#22c55e40' : '#3b82f640'}` 
                                }}>
                                {auditoria.status.replace('_', ' ')}
                            </span>
                        </div>
                        <p className="text-slate-400">
                            📍 {auditoria.unidade} · 🔄 Ciclo {auditoria.ciclo}
                        </p>
                    </div>
                    <div className="flex flex-col items-end gap-3">
                        {stats?.media_final != null && (
                            <NotaBadge nota={Math.round(stats.media_final)} size="lg" />
                        )}
                        
                        <div className="flex gap-2">
                            {(
                                <button
                                    onClick={handleRunGlobalAgent}
                                    disabled={batchAnalyzing !== null}
                                    className="px-4 py-2 bg-purple-600/30 hover:bg-purple-600/50 text-purple-300 border border-purple-600/40 rounded-xl text-xs font-bold transition-all shadow-glow-purple flex items-center gap-2 group"
                                >
                                    {batchAnalyzing === -1 ? (
                                        <>
                                            <span className="animate-spin text-sm">🤖</span>
                                            {agentProgress 
                                                ? `${Math.round((agentProgress.current / agentProgress.total) * 100)}% ANALISANDO...`
                                                : "PREPARANDO AGENTE..."
                                            }
                                        </>
                                    ) : (
                                        <>
                                            <span className="group-hover:scale-125 transition-transform">🚀</span>
                                            INICIAR AGENTE AUDITOR
                                        </>
                                    )}
                                </button>
                            )}

                            {auditoria.status !== "concluida" && auditoria.status !== "aprovada" && (
                                <button
                                    onClick={() => handleUpdateStatus("concluida")}
                                    className="px-4 py-2 bg-green-600/20 hover:bg-green-600/40 text-green-400 border border-green-600/30 rounded-xl text-xs font-bold transition-all shadow-sm"
                                >
                                    ✅ Concluir Auditoria
                                </button>
                            )}
                            {auditoria.status === "concluida" && (
                                <button
                                    onClick={() => handleUpdateStatus("aprovada")}
                                    className="px-4 py-2 bg-purple-600/20 hover:bg-purple-700/40 text-purple-400 border border-purple-600/30 rounded-xl text-xs font-bold transition-all shadow-sm"
                                >
                                    🏆 Aprovar Auditoria
                                </button>
                            )}
                        </div>
                    </div>
                </div>

                {/* Stats bar */}
                {stats && (
                    <div className="grid grid-cols-4 gap-4">
                        <div className="text-center p-3 rounded-xl bg-slate-800/50">
                            <div className="text-2xl font-bold text-white">{stats.avaliados}/{stats.total}</div>
                            <div className="text-xs text-slate-400 mt-1">Avaliados</div>
                        </div>
                        <div className="text-center p-3 rounded-xl bg-slate-800/50">
                            <div className="text-2xl font-bold text-blue-400">{progress}%</div>
                            <div className="text-xs text-slate-400 mt-1">Progresso</div>
                        </div>
                        <div className="text-center p-3 rounded-xl bg-slate-800/50">
                            <div className="text-2xl font-bold text-purple-400">{stats.ia_ok}</div>
                            <div className="text-xs text-slate-400 mt-1">🤖 IA</div>
                        </div>
                        <div className="text-center p-3 rounded-xl bg-slate-800/50">
                            <div className="text-2xl font-bold text-green-400">
                                {stats.media_final != null ? stats.media_final.toFixed(1) : "—"}
                            </div>
                            <div className="text-xs text-slate-400 mt-1">Média Final</div>
                        </div>
                    </div>
                )}

                {/* Progress bar */}
                <div className="mt-4">
                    <div className="w-full bg-slate-700 rounded-full h-2.5">
                        <div className="h-2.5 rounded-full transition-all duration-700 ease-out"
                            style={{
                                width: `${progress}%`,
                                background: progress === 100
                                    ? "linear-gradient(90deg, #22c55e, #16a34a)"
                                    : "linear-gradient(90deg, #3b82f6, #8b5cf6)"
                            }} />
                    </div>
                </div>
            </div>

            {/* Práticas */}
            <div className="space-y-4">
                {praticas.map((pratica) => {
                    const isExpanded = expandedPraticas.has(pratica.pratica_num);
                    const allDone = pratica.pendentes === 0 && pratica.total > 0;

                    return (
                        <div key={pratica.pratica_num} className="glass-card">
                            {/* Practice header */}
                            <div
                                onClick={() => togglePratica(pratica.pratica_num)}
                                onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); togglePratica(pratica.pratica_num); } }}
                                role="button"
                                tabIndex={0}
                                className="w-full flex items-center justify-between p-5 hover:bg-slate-700/30 transition-colors text-left cursor-pointer outline-none focus:bg-slate-700/50"
                            >
                                <div className="flex items-center gap-3">
                                    <span className={`text-2xl ${allDone ? "" : "opacity-80"}`}>
                                        {allDone ? "✅" : "📋"}
                                    </span>
                                    <div>
                                        <h3 className="font-bold text-white">
                                            {pratica.pratica_num}. {cleanTitle(pratica.pratica_nome)}
                                        </h3>
                                        <p className="text-xs text-slate-400 mt-0.5">
                                            SA: {pratica.media_sa} → Final: {pratica.media_final?.toFixed(1) ?? "⏳"}
                                            {" · "}
                                            {pratica.pendentes > 0
                                                ? `⏳ ${pratica.pendentes} pendente(s)`
                                                : "✅ Concluída"}
                                            {pratica.ia_ok > 0 && ` · 🤖 ${pratica.ia_ok} IA`}
                                        </p>
                                    </div>
                                </div>
                                 <div className="flex items-center gap-4">
                                    <div className="flex flex-col items-end">
                                        <span className="text-sm text-slate-400">
                                            {pratica.avaliados}/{pratica.total}
                                        </span>
                                        {pratica.total > 0 && (
                                            <button 
                                                onClick={(e) => { e.stopPropagation(); handleAnalyzePractice(pratica); }}
                                                disabled={batchAnalyzing !== null}
                                                className="text-[10px] font-bold text-purple-400 hover:text-purple-300 transition-colors uppercase tracking-tighter flex items-center gap-1"
                                            >
                                                {batchAnalyzing === pratica.pratica_num ? (
                                                    <>
                                                        <span className="animate-spin text-[8px]">🤖</span>
                                                        {agentProgress 
                                                            ? `${Math.round((agentProgress.current / agentProgress.total) * 100)}%`
                                                            : "..."}
                                                    </>
                                                ) : "🤖 Analisar Tudo"}
                                            </button>
                                        )}
                                    </div>
                                    <span className={`text-slate-400 transition-transform duration-200 ${isExpanded ? "rotate-180" : ""}`}>
                                        ▼
                                    </span>
                                </div>
                            </div>

                            {/* Subitems */}
                            {isExpanded && (
                                <div className="border-t border-slate-700/50 p-4 space-y-2 animate-fade-in">
                                    {pratica.subitens.map((sub) => (
                                         <SubitemCard
                                            key={sub.id}
                                            avaliacao={sub}
                                            onSaved={loadData}
                                            apiKey={auditoria?.openai_api_key || ""}
                                            initialEvidence={evidenceMap[`${sub.pratica_num}.${sub.subitem_idx}`]}
                                            initialCriteria={criteriaMap[`${sub.pratica_num}.${sub.subitem_idx}`]}
                                            modoAnalise={auditoria?.modo_analise}
                                            aiProvider={auditoria?.ai_provider}
                                            aiBaseUrl={auditoria?.ai_base_url}
                                        />
                                    ))}
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
