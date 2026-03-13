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
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
          {auditorias.map((aud) => {
            const status = STATUS_CONFIG[aud.status] || STATUS_CONFIG.em_andamento;
            const progress = aud.total_subitens > 0
              ? Math.round((aud.subitens_avaliados / aud.total_subitens) * 100) : 0;

            return (
              <Link key={aud.id} href={`/auditar/${aud.id}`}>
                <div className="glass-card p-6 hover:border-blue-500/50 transition-all duration-300 cursor-pointer group hover:scale-[1.02]">
                  {/* Header */}
                  <div className="flex items-start justify-between mb-4">
                    <div>
                      <h3 className="font-bold text-white text-lg group-hover:text-blue-300 transition-colors">
                        {aud.area}
                      </h3>
                      <p className="text-slate-400 text-sm">📍 {aud.unidade}</p>
                    </div>
                    <span className="text-xs px-3 py-1 rounded-full font-medium"
                      style={{ background: `${status.color}20`, color: status.color, border: `1px solid ${status.color}40` }}>
                      {status.icon} {status.label}
                    </span>
                  </div>

                  {/* Ciclo */}
                  <div className="text-sm text-slate-400 mb-4">
                    🔄 Ciclo <span className="text-white font-medium">{aud.ciclo}</span>
                  </div>

                  {/* Progress */}
                  <div className="mb-4">
                    <div className="flex justify-between text-xs text-slate-400 mb-1">
                      <span>Progresso</span>
                      <span className="text-white font-medium">
                        {aud.subitens_avaliados}/{aud.total_subitens} ({progress}%)
                      </span>
                    </div>
                    <div className="w-full bg-slate-700 rounded-full h-2">
                      <div className="h-2 rounded-full transition-all duration-500"
                        style={{
                          width: `${progress}%`,
                          background: progress === 100
                            ? "linear-gradient(90deg, #22c55e, #16a34a)"
                            : "linear-gradient(90deg, #3b82f6, #2563eb)"
                        }} />
                    </div>
                  </div>

                  {/* Stats */}
                  <div className="flex items-center gap-4 text-xs text-slate-400">
                    {aud.media_nota_final != null && (
                      <span>📊 Média: <span className="text-white font-medium">
                        {aud.media_nota_final.toFixed(1)}
                      </span></span>
                    )}
                    {aud.ia_analisados > 0 && (
                      <span>🤖 IA: <span className="text-white font-medium">
                        {aud.ia_analisados}
                      </span></span>
                    )}
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
