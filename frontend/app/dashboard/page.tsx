"use client";

import { useEffect, useState } from "react";
import { api, Auditoria, ESCALA, DECISAO_CONFIG, API_BASE } from "@/lib/api";
import NotaBadge from "@/components/NotaBadge";
import Link from "next/link";

interface ResumoGeral {
    total_auditorias: number;
    total_subitens: number;
    avaliados: number;
    ia_analisados: number;
    media_geral: number | null;
}

interface DistItem { nota_final?: number; decisao?: string; count: number; }
interface PraticaMedia { pratica_num: number; pratica_nome: string; media_sa: number; media_final: number | null; total: number; avaliados: number; }

export default function DashboardPage() {
    const [auditorias, setAuditorias] = useState<Auditoria[]>([]);
    const [selectedId, setSelectedId] = useState<number | null>(null);
    const [resumo, setResumo] = useState<ResumoGeral | null>(null);
    const [distNotas, setDistNotas] = useState<DistItem[]>([]);
    const [distDecisoes, setDistDecisoes] = useState<DistItem[]>([]);
    const [praticaMedias, setPraticaMedias] = useState<PraticaMedia[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        Promise.all([
            api.listAuditorias(),
            fetch(`${API_BASE}/api/dashboard/resumo-geral`).then(r => r.json()),
        ]).then(([auds, res]) => {
            setAuditorias(auds);
            setResumo(res);
            if (auds.length > 0) setSelectedId(auds[0].id);
            setLoading(false);
        }).catch(() => setLoading(false));
    }, []);

    useEffect(() => {
        if (!selectedId) return;
        Promise.all([
            fetch(`${API_BASE}/api/dashboard/resumo-geral?auditoria_id=${selectedId}`).then(r => r.json()),
            fetch(`${API_BASE}/api/dashboard/distribuicao-notas/${selectedId}`).then(r => r.json()),
            fetch(`${API_BASE}/api/dashboard/distribuicao-decisoes/${selectedId}`).then(r => r.json()),
            fetch(`${API_BASE}/api/dashboard/media-por-pratica/${selectedId}`).then(r => r.json()),
        ]).then(([res, notas, decisoes, medias]) => {
            setResumo(res?.detail ? null : res);
            setDistNotas(Array.isArray(notas) ? notas : []);
            setDistDecisoes(Array.isArray(decisoes) ? decisoes : []);
            setPraticaMedias(Array.isArray(medias) ? medias : []);
        }).catch(console.error);
    }, [selectedId]);

    if (loading) return <div className="flex items-center justify-center h-64"><div className="text-4xl animate-pulse">📊</div></div>;

    const aud = auditorias.find(a => a.id === selectedId);
    
    const safeDistNotas = Array.isArray(distNotas) ? distNotas : [];
    const safeDistDecisoes = Array.isArray(distDecisoes) ? distDecisoes : [];
    const safePraticaMedias = Array.isArray(praticaMedias) ? praticaMedias : [];

    const maxNotaCount = Math.max(...safeDistNotas.map(d => d.count), 1);
    const maxDecCount = Math.max(...safeDistDecisoes.map(d => d.count), 1);

    return (
        <div className="animate-fade-in space-y-6">
            <div className="flex items-center justify-between">
                <h1 className="text-3xl font-bold text-white">📊 Dashboard</h1>
                <select value={selectedId ?? ""} onChange={e => setSelectedId(Number(e.target.value))}
                    className="bg-slate-700 border border-slate-600 rounded-xl px-4 py-2 text-sm text-white">
                    {auditorias.map(a => (
                        <option key={a.id} value={a.id}>{a.unidade} — {a.area} ({a.ciclo})</option>
                    ))}
                </select>
            </div>

            {/* Summary Cards */}
            {resumo && (
                <div className="grid grid-cols-5 gap-4">
                    {[
                        { label: "Auditorias", value: resumo.total_auditorias, icon: "📋", color: "#3b82f6" },
                        { label: "Total Subitens", value: resumo.total_subitens, icon: "📝", color: "#8b5cf6" },
                        { label: "Avaliados", value: resumo.avaliados, icon: "✅", color: "#22c55e" },
                        { label: "IA Analisados", value: resumo.ia_analisados, icon: "🤖", color: "#f59e0b" },
                        { label: "Média Geral", value: resumo.media_geral?.toFixed(1) ?? "—", icon: "📊", color: "#ec4899" },
                    ].map((card) => (
                        <div key={card.label} className="glass-card p-5 text-center">
                            <div className="text-3xl mb-2">{card.icon}</div>
                            <div className="text-2xl font-bold" style={{ color: card.color }}>{card.value}</div>
                            <div className="text-xs text-slate-400 mt-1">{card.label}</div>
                        </div>
                    ))}
                </div>
            )}

            <div className="grid grid-cols-2 gap-6">
                {/* Grade Distribution (visual bars) */}
                <div className="glass-card p-6">
                    <h3 className="text-lg font-semibold text-white mb-4">📊 Distribuição de Notas</h3>
                    <div className="space-y-3">
                        {[0, 1, 2, 3, 4].map(nota => {
                            const item = safeDistNotas.find(d => d.nota_final === nota);
                            const count = item?.count ?? 0;
                            const info = ESCALA[nota];
                            const pct = maxNotaCount > 0 ? (count / maxNotaCount) * 100 : 0;
                            return (
                                <div key={nota} className="flex items-center gap-3">
                                    <span className="w-8 text-center text-lg">{info.emoji}</span>
                                    <span className="w-20 text-sm text-slate-300">{nota} — {info.desc}</span>
                                    <div className="flex-1 bg-slate-700 rounded-full h-6 relative overflow-hidden">
                                        <div className="h-full rounded-full transition-all duration-700 flex items-center pl-3"
                                            style={{ width: `${Math.max(pct, 2)}%`, background: info.color }}>
                                            <span className="text-xs font-bold text-white">{count}</span>
                                        </div>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>

                {/* Decision Distribution */}
                <div className="glass-card p-6">
                    <h3 className="text-lg font-semibold text-white mb-4">📋 Distribuição de Decisões</h3>
                    <div className="space-y-3">
                        {Object.entries(DECISAO_CONFIG).map(([key, cfg]) => {
                            const item = safeDistDecisoes.find(d => d.decisao === key);
                            const count = item?.count ?? 0;
                            const pct = maxDecCount > 0 ? (count / maxDecCount) * 100 : 0;
                            return (
                                <div key={key} className="flex items-center gap-3">
                                    <span className="w-8 text-center text-lg">{cfg.icon}</span>
                                    <span className="w-32 text-sm text-slate-300">{cfg.label}</span>
                                    <div className="flex-1 bg-slate-700 rounded-full h-6 relative overflow-hidden">
                                        <div className="h-full rounded-full transition-all duration-700 flex items-center pl-3"
                                            style={{ width: `${Math.max(pct, 2)}%`, background: cfg.color }}>
                                            <span className="text-xs font-bold text-white">{count}</span>
                                        </div>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>
            </div>

            {/* Practice Averages Table */}
            <div className="glass-card p-6">
                <h3 className="text-lg font-semibold text-white mb-4">📋 Médias por Prática</h3>
                <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="border-b border-slate-700">
                                <th className="text-left py-3 px-4 text-slate-400">Prática</th>
                                <th className="text-center py-3 px-4 text-slate-400">Média SA</th>
                                <th className="text-center py-3 px-4 text-slate-400">Média Final</th>
                                <th className="text-center py-3 px-4 text-slate-400">Progresso</th>
                                <th className="text-right py-3 px-4 text-slate-400">Ação</th>
                            </tr>
                        </thead>
                        <tbody>
                            {safePraticaMedias.map(p => (
                                <tr key={p.pratica_num} className="border-b border-slate-700/50 hover:bg-slate-700/30 transition-colors">
                                    <td className="py-3 px-4 text-white font-medium">
                                        {p.pratica_num}. {p.pratica_nome}
                                    </td>
                                    <td className="py-3 px-4 text-center">
                                        <NotaBadge nota={Math.round(p.media_sa)} size="sm" showLabel={false} />
                                    </td>
                                    <td className="py-3 px-4 text-center">
                                        <NotaBadge nota={p.media_final != null ? Math.round(p.media_final) : null} size="sm" showLabel={false} />
                                    </td>
                                    <td className="py-3 px-4 text-center">
                                        <span className={`text-xs font-medium ${p.avaliados === p.total ? "text-green-400" : "text-slate-400"}`}>
                                            {p.avaliados}/{p.total}
                                        </span>
                                    </td>
                                    <td className="py-3 px-4 text-right">
                                        <Link href={`/auditar/${selectedId}`}
                                            className="text-xs text-blue-400 hover:text-blue-300 transition-colors">
                                            Ver →
                                        </Link>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}
