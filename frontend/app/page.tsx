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
  const [selectedUnit, setSelectedUnit] = useState<string>("Todas");

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
      <div className="flex items-center justify-center h-screen -mt-20">
        <div className="text-center relative">
          <div className="w-20 h-20 border-4 border-blue-500/10 border-t-blue-500 rounded-full animate-spin mb-6 mx-auto" />
          <p className="text-slate-400 font-medium animate-pulse">Carregando Auditorias...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center glass-card p-10 border-red-500/20 max-w-md">
          <div className="text-5xl mb-6">⚠️</div>
          <p className="text-red-400 font-bold mb-2">Ops! Algo deu errado</p>
          <p className="text-slate-400 text-sm mb-8 leading-relaxed">
            {error}. Verifique a conexão com o servidor.
          </p>
          <button onClick={loadAuditorias}
            className="w-full py-3 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 rounded-xl transition-all text-white font-bold shadow-lg shadow-blue-900/40">
            Tentar Novamente
          </button>
        </div>
      </div>
    );
  }

  const activeAuds = auditorias.filter(a => a.status !== "arquivada");
  const units = ["Todas", ...Array.from(new Set(activeAuds.map(a => a.unidade))).sort()];
  
  const grouped = activeAuds.reduce((acc, aud) => {
    if (!acc[aud.unidade]) acc[aud.unidade] = [];
    acc[aud.unidade].push(aud);
    return acc;
  }, {} as Record<string, Auditoria[]>);

  const displayedUnits = selectedUnit === "Todas" 
    ? Object.keys(grouped).sort() 
    : [selectedUnit];

  return (
    <div className="animate-fade-in pb-20">
      {/* Premium Header */}
      <div className="relative mb-12">
        <div className="absolute -top-24 -left-24 w-64 h-64 bg-blue-600/10 blur-[100px] rounded-full" />
        <div className="absolute -top-12 -right-12 w-48 h-48 bg-indigo-600/10 blur-[80px] rounded-full" />
        
        <h1 className="text-5xl font-black text-white mb-3 tracking-tight">
          🏠 Dashboard <span className="text-blue-500 text-4xl">.</span>
        </h1>
        <p className="text-slate-500 text-lg font-medium">Gestão Inteligente de Auditorias Industriais</p>
      </div>

      {/* Unit Navigation Tabs */}
      <div className="flex flex-wrap items-center gap-2 mb-12 p-1.5 bg-slate-900/50 backdrop-blur-md border border-white/5 rounded-2xl w-fit">
        {units.map(u => (
          <button 
            key={u}
            onClick={() => setSelectedUnit(u)}
            className={`px-6 py-2.5 rounded-xl text-sm font-bold transition-all ${
              selectedUnit === u 
                ? "bg-blue-600 text-white shadow-lg shadow-blue-900/40" 
                : "text-slate-400 hover:text-white hover:bg-white/5"
            }`}
          >
            {u}
          </button>
        ))}
      </div>

      {activeAuds.length === 0 ? (
        <div className="glass-card p-20 text-center border-dashed border-slate-800">
          <div className="w-24 h-24 bg-slate-800/50 rounded-3xl flex items-center justify-center mx-auto mb-6 text-5xl">📋</div>
          <h3 className="text-2xl font-black text-white mb-2">Ambiente Pronto</h3>
          <p className="text-slate-500 text-lg">Crie sua primeira auditoria para começar a monitorar.</p>
          <Link href="/nova" className="inline-block mt-8 px-8 py-3 bg-white text-slate-900 font-bold rounded-xl hover:bg-slate-200 transition-all">
            Criar Agora
          </Link>
        </div>
      ) : (
        <div className="space-y-20">
          {displayedUnits.map(unidade => {
            const unitAuds = grouped[unidade] || [];
            // Sub-metrics
            const inProgress = unitAuds.filter(a => a.status === "em_andamento").length;
            const completed = unitAuds.filter(a => a.status === "concluida" || a.status === "em_revisao").length;
            const approved = unitAuds.filter(a => a.status === "aprovada").length;
            const avgScore = unitAuds.reduce((sum, a) => sum + (a.media_nota_final || 0), 0) / (unitAuds.filter(a => a.media_nota_final != null).length || 1);

            // Sorting within unit
            const sorted = [...unitAuds].sort((a, b) => {
              const p: any = { em_andamento: 1, concluida: 2, aprovada: 3, em_revisao: 4 };
              return (p[a.status] || 99) - (p[b.status] || 99);
            });

            return (
              <div key={unidade} className="animate-slide-up group/unit">
                {/* Unit Hero Card */}
                <div className="mb-8 p-8 rounded-[32px] bg-gradient-to-br from-slate-900/80 to-slate-900/40 border border-white/5 relative overflow-hidden">
                  <div className="absolute top-0 right-0 p-12 opacity-[0.03] group-hover/unit:opacity-[0.07] transition-opacity pointer-events-none">
                    <span className="text-9xl font-black">{unidade.charAt(0)}</span>
                  </div>
                  
                  <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
                    <div>
                      <div className="flex items-center gap-3 mb-2">
                        <span className="p-2.5 bg-blue-600/20 text-blue-500 rounded-xl text-xl">📍</span>
                        <h2 className="text-3xl font-black text-white tracking-tight">{unidade}</h2>
                      </div>
                      <p className="text-slate-500 font-medium ml-12">Monitorando {unitAuds.length} áreas industriais</p>
                    </div>

                    <div className="flex flex-wrap items-center gap-4 ml-12 md:ml-0">
                      <div className="px-5 py-3 bg-slate-800/40 rounded-2xl border border-white/5 text-center min-w-[90px]">
                        <div className="text-blue-400 font-black text-xl">{inProgress}</div>
                        <div className="text-[10px] text-slate-500 font-bold uppercase tracking-widest">Ativas</div>
                      </div>
                      <div className="px-5 py-3 bg-slate-800/40 rounded-2xl border border-white/5 text-center min-w-[90px]">
                        <div className="text-green-400 font-black text-xl">{completed}</div>
                        <div className="text-[10px] text-slate-500 font-bold uppercase tracking-widest">Prontas</div>
                      </div>
                      <div className="px-5 py-3 bg-slate-800/40 rounded-2xl border border-white/5 text-center min-w-[90px]">
                        <div className="text-purple-400 font-black text-xl">{approved}</div>
                        <div className="text-[10px] text-slate-500 font-bold uppercase tracking-widest">Aprovadas</div>
                      </div>
                      <div className="px-5 py-3 bg-slate-800/40 rounded-2xl border border-white/5 text-center min-w-[90px]">
                        <div className="text-pink-400 font-black text-xl">{avgScore > 0 ? avgScore.toFixed(1) : "—"}</div>
                        <div className="text-[10px] text-slate-500 font-bold uppercase tracking-widest">Média</div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Audit Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 px-4">
                  {sorted.map((aud) => {
                    const status = STATUS_CONFIG[aud.status] || STATUS_CONFIG.em_andamento;
                    const progress = aud.total_subitens > 0
                      ? Math.round((aud.subitens_avaliados / aud.total_subitens) * 100) : 0;

                    return (
                      <Link key={aud.id} href={`/auditar/${aud.id}`} className="block h-full group/card">
                        <div className="relative h-full bg-slate-900/60 backdrop-blur-xl border border-white/5 rounded-[24px] p-7 transition-all duration-500 hover:border-blue-500/40 hover:translate-y-[-4px] hover:shadow-[0_20px_40px_-20px_rgba(0,0,0,0.5)]">
                          
                          {/* Status Badge Top Right */}
                          <div className="absolute top-6 right-6">
                            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full text-[10px] font-black uppercase tracking-widest"
                              style={{ background: `${status.color}15`, color: status.color, border: `1px solid ${status.color}30` }}>
                              <span className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ backgroundColor: status.color }} />
                              {status.label}
                            </div>
                          </div>

                          <div className="mb-6">
                            <h3 className="text-xl font-black text-white group-hover/card:text-blue-400 transition-colors leading-tight mb-2">
                              {aud.area}
                            </h3>
                            <div className="flex items-center gap-3">
                              <span className="text-[10px] font-bold text-slate-500 bg-slate-800 px-2 py-0.5 rounded-md">ID #{aud.id}</span>
                              <div className="flex items-center gap-1.5 text-xs text-slate-400 font-medium">
                                <span className="opacity-50">🔄 Ciclo</span>
                                <span className="text-white">{aud.ciclo}</span>
                              </div>
                            </div>
                          </div>

                          {/* Professional Progress Section */}
                          <div className="mb-8">
                            <div className="flex justify-between items-end mb-3">
                              <div className="flex flex-col">
                                <span className="text-[9px] font-black text-slate-500 uppercase tracking-widest mb-0.5">Execução</span>
                                <span className="text-white text-xs font-bold">{aud.subitens_avaliados} itens</span>
                              </div>
                              <span className="text-2xl font-black text-white italic opacity-20">{progress}%</span>
                            </div>
                            <div className="w-full h-3 bg-slate-800/50 rounded-full p-0.5 border border-white/5">
                              <div className="h-full rounded-full transition-all duration-1000 relative shadow-[0_0_15px_-3px_rgba(59,130,246,0.5)]"
                                style={{
                                  width: `${progress}%`,
                                  background: progress === 100
                                    ? "linear-gradient(90deg, #10b981, #059669)"
                                    : "linear-gradient(90deg, #60a5fa, #2563eb)"
                                }}>
                                <div className="absolute inset-0 bg-white/20 animate-pulse rounded-full" />
                              </div>
                            </div>
                          </div>

                          {/* Stats Footer */}
                          <div className="flex items-center justify-between pt-6 border-t border-white/5">
                            <div className="flex gap-4">
                              {aud.media_nota_final != null && (
                                <div className="flex flex-col">
                                  <span className="text-[9px] font-bold text-slate-500 uppercase tracking-tighter">Média Final</span>
                                  <span className="text-white font-black text-lg">{aud.media_nota_final.toFixed(1)}</span>
                                </div>
                              )}
                              {aud.ia_analisados > 0 && (
                                <div className="flex flex-col">
                                  <span className="text-[9px] font-bold text-blue-500/60 uppercase tracking-tighter">I.A. Insights</span>
                                  <span className="text-blue-400 font-black text-lg">{aud.ia_analisados}</span>
                                </div>
                              )}
                            </div>
                            
                            <div className="w-10 h-10 rounded-2xl bg-white/5 flex items-center justify-center group-hover/card:bg-blue-600 transition-all duration-300">
                              <svg className="w-5 h-5 text-slate-500 group-hover/card:text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                              </svg>
                            </div>
                          </div>

                          {/* Team Info */}
                          {(aud.auditado_por || aud.revisado_por) && (
                            <div className="mt-6 flex flex-col gap-2">
                              {aud.auditado_por && (
                                <div className="flex items-center gap-3">
                                  <div className="w-6 h-6 rounded-lg bg-blue-600/10 flex items-center justify-center text-[10px] font-bold text-blue-500">A</div>
                                  <span className="text-[10px] font-bold text-slate-400 truncate tracking-tight">
                                    <span className="opacity-50">Por: </span>{formatUserNames(aud.auditado_por)}
                                  </span>
                                </div>
                              )}
                              {aud.revisado_por && (
                                <div className="flex items-center gap-3">
                                  <div className="w-6 h-6 rounded-lg bg-amber-600/10 flex items-center justify-center text-[10px] font-bold text-amber-500">R</div>
                                  <span className="text-[10px] font-bold text-amber-200/60 truncate tracking-tight">
                                    <span className="opacity-50 text-slate-400">Revisado: </span>{formatUserNames(aud.revisado_por)}
                                  </span>
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
