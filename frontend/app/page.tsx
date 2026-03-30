"use client";

import { useEffect, useState } from "react";
import { api, Auditoria } from "@/lib/api";
import Link from "next/link";

const STATUS_CONFIG: Record<string, { icon: string; label: string; color: string }> = {
  em_andamento: { icon: "🔄", label: "Em Andamento", color: "#3b82f6" },
  concluida: { icon: "✅", label: "Concluída", color: "#22c55e" },
  em_revisao: { icon: "🔍", label: "Em Revisão", color: "#f59e0b" },
  aprovada: { icon: "🏆", label: "Aprovada", color: "#a855f7" },
  arquivada: { icon: "📁", label: "Arquivada", color: "#6b7280" },
};

/** Extract a friendly display name from an email like anna@automateasy.com.br → Anna */
function formatUserName(email: string): string {
  const name = email.split("@")[0];
  return name.charAt(0).toUpperCase() + name.slice(1);
}

/** Format a comma-separated list of emails into friendly names */
function formatUserNames(emails: string): string {
  return emails
    .split(",")
    .map((e) => e.trim())
    .filter(Boolean)
    .map(formatUserName)
    .join(" e ");
}

export default function HomePage() {
  const [auditorias, setAuditorias] = useState<Auditoria[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadAuditorias();
  }, []);

  async function loadAuditorias() {
    try {
      setLoading(true);
      const data = await api.listAuditorias();
      setAuditorias(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Erro ao carregar auditorias");
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="text-4xl mb-4 animate-pulse">🔄</div>
          <p className="text-slate-400">Carregando auditorias...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center glass-card p-8">
          <div className="text-4xl mb-4">⚠️</div>
          <p className="text-red-400 mb-4">{error}</p>
          <p className="text-slate-400 text-sm mb-4">
            Verifique se o backend FastAPI está rodando em <code className="text-blue-400">http://localhost:8000</code>
          </p>
          <button onClick={loadAuditorias}
            className="px-6 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors text-white">
            Tentar novamente
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="animate-fade-in">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white mb-2">🏠 Auditorias</h1>
        <p className="text-slate-400">Selecione uma auditoria para continuar</p>
      </div>

      {auditorias.length === 0 ? (
        <div className="glass-card p-12 text-center">
          <div className="text-5xl mb-4">📋</div>
          <h3 className="text-xl font-semibold text-white mb-2">Nenhuma auditoria encontrada</h3>
          <p className="text-slate-400">Crie uma nova auditoria para começar.</p>
        </div>
      ) : (
        <div className="space-y-12">
          {Object.entries(
            auditorias
              .filter(a => a.status !== "arquivada")
              .reduce((acc, aud) => {
                if (!acc[aud.unidade]) acc[aud.unidade] = [];
                acc[aud.unidade].push(aud);
                return acc;
              }, {} as Record<string, Auditoria[]>)
          )
          .sort(([unitA], [unitB]) => unitA.localeCompare(unitB))
          .map(([unidade, unitAuds]) => {
            // Sort audits within unit: em_andamento -> concluida -> aprovada -> em_revisao
            const sortedAuds = [...unitAuds].sort((a, b) => {
              const priority: Record<string, number> = {
                em_andamento: 1,
                concluida: 2,
                aprovada: 3,
                em_revisao: 4
              };
              return (priority[a.status] || 99) - (priority[b.status] || 99);
            });

            return (
              <div key={unidade} className="animate-slide-up">
                <div className="flex items-center gap-4 mb-6">
                  <div className="h-px bg-slate-800 flex-1" />
                  <h2 className="text-xl font-bold text-slate-400 flex items-center gap-2 whitespace-nowrap">
                    <span className="text-blue-500">📍</span> {unidade}
                    <span className="bg-slate-800 text-[10px] px-2 py-0.5 rounded-full text-slate-500">
                      {sortedAuds.length} {sortedAuds.length === 1 ? 'Auditoria' : 'Auditorias'}
                    </span>
                  </h2>
                  <div className="h-px bg-slate-800 flex-1" />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
                  {sortedAuds.map((aud) => {
                    const status = STATUS_CONFIG[aud.status] || STATUS_CONFIG.em_andamento;
                    const progress = aud.total_subitens > 0
                      ? Math.round((aud.subitens_avaliados / aud.total_subitens) * 100) : 0;

                    return (
                      <Link key={aud.id} href={`/auditar/${aud.id}`}>
                        <div className="glass-card p-6 hover:border-blue-500/50 transition-all duration-300 cursor-pointer group hover:scale-[1.02] flex flex-col h-full bg-slate-900/40 backdrop-blur-sm">
                          {/* Header */}
                          <div className="flex items-start justify-between mb-4">
                            <div>
                              <h3 className="font-bold text-white text-lg group-hover:text-blue-400 transition-colors leading-tight">
                                {aud.area}
                              </h3>
                              <p className="text-slate-500 text-xs mt-1 font-medium tracking-wide">ID #{aud.id}</p>
                            </div>
                            <span className="text-[10px] px-2.5 py-1 rounded-full font-bold uppercase tracking-wider"
                              style={{ background: `${status.color}15`, color: status.color, border: `1px solid ${status.color}30` }}>
                              {status.icon} {status.label}
                            </span>
                          </div>

                          {/* Ciclo */}
                          <div className="flex items-center gap-2 text-sm text-slate-400 mb-6 bg-slate-800/30 w-fit px-3 py-1 rounded-lg border border-slate-700/30">
                            <span className="opacity-70">🔄 Ciclo</span>
                            <span className="text-white font-bold">{aud.ciclo}</span>
                          </div>

                          <div className="flex-1" />

                          {/* Progress */}
                          <div className="mb-6">
                            <div className="flex justify-between text-[11px] text-slate-400 mb-2">
                              <span className="font-medium uppercase tracking-tighter opacity-60">Status da Avaliação</span>
                              <span className="text-white font-bold">
                                {aud.subitens_avaliados}/{aud.total_subitens} ({progress}%)
                              </span>
                            </div>
                            <div className="w-full bg-slate-800/80 rounded-full h-2.5 p-0.5 border border-slate-700/30">
                              <div className="h-full rounded-full transition-all duration-700 shadow-[0_0_8px_rgba(59,130,246,0.3)]"
                                style={{
                                  width: `${progress}%`,
                                  background: progress === 100
                                    ? "linear-gradient(90deg, #22c55e, #16a34a)"
                                    : "linear-gradient(90deg, #3b82f6, #2563eb)"
                                }} />
                            </div>
                          </div>

                          {/* Stats */}
                          <div className="flex items-center justify-between py-3 border-y border-slate-800/50 mb-4">
                            <div className="flex items-center gap-4 text-[11px] text-slate-500">
                              {aud.media_nota_final != null && (
                                <div className="flex flex-col">
                                  <span className="uppercase text-[9px] opacity-60 mb-0.5">Média Final</span>
                                  <span className="text-white font-bold text-sm">
                                    {aud.media_nota_final.toFixed(1)}
                                  </span>
                                </div>
                              )}
                              {aud.ia_analisados > 0 && (
                                <div className="flex flex-col">
                                  <span className="uppercase text-[9px] opacity-60 mb-0.5">I.A. Insights</span>
                                  <span className="text-blue-400 font-bold text-sm">
                                    {aud.ia_analisados}
                                  </span>
                                </div>
                              )}
                            </div>
                            
                            <div className="p-2 rounded-xl bg-slate-800 group-hover:bg-blue-600 transition-colors">
                              <svg className="w-4 h-4 text-slate-400 group-hover:text-white transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                              </svg>
                            </div>
                          </div>

                          {/* Responsibility Labels */}
                          {(aud.auditado_por || aud.revisado_por) && (
                            <div className="flex flex-col gap-1.5 px-1">
                              {aud.auditado_por && (
                                <div className="flex items-center gap-2 text-[10px] text-slate-400">
                                  <span className="w-1.5 h-1.5 rounded-full bg-blue-500" />
                                  <span className="opacity-60">Auditado:</span>
                                  <span className="text-white font-semibold truncate max-w-[120px]">{formatUserNames(aud.auditado_por)}</span>
                                </div>
                              )}
                              {aud.revisado_por && (
                                <div className="flex items-center gap-2 text-[10px] text-slate-400">
                                  <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
                                  <span className="opacity-60">Revisado:</span>
                                  <span className="text-amber-200/90 font-semibold truncate max-w-[120px]">{formatUserNames(aud.revisado_por)}</span>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      </Link>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
