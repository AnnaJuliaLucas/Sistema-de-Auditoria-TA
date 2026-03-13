"use client";

import { useEffect, useState } from "react";
import { api, Auditoria } from "@/lib/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function RelatoriosPage() {
    const [auditorias, setAuditorias] = useState<Auditoria[]>([]);
    const [selectedId, setSelectedId] = useState<number | null>(null);
    const [exporting, setExporting] = useState(false);
    const [stats, setStats] = useState<{ total: number; avaliados: number; ia_ok: number; media_final: number | null } | null>(null);

    useEffect(() => {
        api.listAuditorias().then(auds => {
            setAuditorias(auds);
            if (auds.length > 0) setSelectedId(auds[0].id);
        });
    }, []);

    useEffect(() => {
        if (!selectedId) return;
        api.getEstatisticas(selectedId).then(setStats);
    }, [selectedId]);

    async function handleExport() {
        if (!selectedId) return;
        setExporting(true);
        try {
            const res = await fetch(`${API_BASE}/api/auditorias/${selectedId}/exportar-excel`);
            if (!res.ok) throw new Error("Erro ao exportar");
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `Auditoria_${selectedId}.xlsx`;
            a.click();
            URL.revokeObjectURL(url);
        } catch (e: unknown) {
            alert(e instanceof Error ? e.message : "Erro ao exportar");
        } finally {
            setExporting(false);
        }
    }

    const aud = auditorias.find(a => a.id === selectedId);
    const progress = stats && stats.total > 0 ? Math.round((stats.avaliados / stats.total) * 100) : 0;

    return (
        <div className="animate-fade-in max-w-3xl">
            <h1 className="text-3xl font-bold text-white mb-2">📊 Relatórios</h1>
            <p className="text-slate-400 mb-8">Exporte e visualize dados da auditoria</p>

            <div className="glass-card p-6 mb-6">
                <label className="text-sm text-slate-300 block mb-2">Selecione a auditoria:</label>
                <select value={selectedId ?? ""} onChange={e => setSelectedId(Number(e.target.value))}
                    className="w-full bg-slate-700 border border-slate-600 rounded-xl px-4 py-3 text-white">
                    {auditorias.map(a => <option key={a.id} value={a.id}>{a.unidade} — {a.area} ({a.ciclo})</option>)}
                </select>
            </div>

            {aud && stats && (
                <div className="space-y-6">
                    {/* Summary */}
                    <div className="glass-card p-6">
                        <h3 className="text-lg font-semibold text-white mb-4">📋 Resumo da Auditoria</h3>
                        <div className="grid grid-cols-2 gap-4 text-sm">
                            <div className="flex justify-between py-2 border-b border-slate-700/50">
                                <span className="text-slate-400">Unidade</span>
                                <span className="text-white font-medium">{aud.unidade}</span>
                            </div>
                            <div className="flex justify-between py-2 border-b border-slate-700/50">
                                <span className="text-slate-400">Área</span>
                                <span className="text-white font-medium">{aud.area}</span>
                            </div>
                            <div className="flex justify-between py-2 border-b border-slate-700/50">
                                <span className="text-slate-400">Ciclo</span>
                                <span className="text-white font-medium">{aud.ciclo}</span>
                            </div>
                            <div className="flex justify-between py-2 border-b border-slate-700/50">
                                <span className="text-slate-400">Status</span>
                                <span className="text-white font-medium">{aud.status}</span>
                            </div>
                            <div className="flex justify-between py-2 border-b border-slate-700/50">
                                <span className="text-slate-400">Progresso</span>
                                <span className="text-white font-medium">{stats.avaliados}/{stats.total} ({progress}%)</span>
                            </div>
                            <div className="flex justify-between py-2 border-b border-slate-700/50">
                                <span className="text-slate-400">Média Final</span>
                                <span className="text-white font-medium">{stats.media_final?.toFixed(1) ?? "—"}</span>
                            </div>
                        </div>
                    </div>

                    {/* Export */}
                    <div className="glass-card p-6">
                        <h3 className="text-lg font-semibold text-white mb-4">📥 Exportar</h3>
                        <button onClick={handleExport} disabled={exporting}
                            className="w-full py-3.5 bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white rounded-xl font-semibold transition-all shadow-lg shadow-green-600/20 flex items-center justify-center gap-2">
                            {exporting ? "Exportando..." : "📥 Exportar para Excel (.xlsx)"}
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
