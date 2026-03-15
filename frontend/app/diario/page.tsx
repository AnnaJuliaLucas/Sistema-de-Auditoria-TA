"use client";

import { useEffect, useState } from "react";
import { api, Auditoria, API_BASE } from "@/lib/api";

interface DiarioEntry {
    id: number;
    auditoria_id: number;
    data_entrada: string;
    tipo: string;
    titulo: string;
    conteudo: string;
    pratica_ref: string;
    prioridade: string;
    resolvido: number;
}

const TIPO_CONFIG: Record<string, { icon: string; label: string; color: string }> = {
    observacao: { icon: "📝", label: "Observação", color: "#3b82f6" },
    problema: { icon: "⚠️", label: "Problema", color: "#f59e0b" },
    acao: { icon: "🎯", label: "Ação", color: "#8b5cf6" },
    decisao: { icon: "⚖️", label: "Decisão", color: "#22c55e" },
};

const PRIORIDADE_CONFIG: Record<string, { icon: string; color: string }> = {
    baixa: { icon: "🟢", color: "#22c55e" },
    normal: { icon: "🔵", color: "#3b82f6" },
    alta: { icon: "🟠", color: "#f59e0b" },
    urgente: { icon: "🔴", color: "#ef4444" },
};

export default function DiarioPage() {
    const [auditorias, setAuditorias] = useState<Auditoria[]>([]);
    const [selectedId, setSelectedId] = useState<number | null>(null);
    const [entries, setEntries] = useState<DiarioEntry[]>([]);
    const [loading, setLoading] = useState(true);
    const [showForm, setShowForm] = useState(false);
    const [formData, setFormData] = useState({ conteudo: "", tipo: "observacao", titulo: "", pratica_ref: "", prioridade: "normal" });

    useEffect(() => {
        api.listAuditorias().then(auds => {
            setAuditorias(auds);
            if (auds.length > 0) setSelectedId(auds[0].id);
            setLoading(false);
        });
    }, []);

    useEffect(() => {
        if (!selectedId) return;
        fetch(`${API_BASE}/api/diario/${selectedId}`).then(r => r.json()).then(setEntries);
    }, [selectedId]);

    async function loadEntries() {
        if (!selectedId) return;
        const data = await fetch(`${API_BASE}/api/diario/${selectedId}`).then(r => r.json());
        setEntries(data);
    }

    async function handleCreate() {
        if (!selectedId || !formData.conteudo) return;
        await fetch(`${API_BASE}/api/diario/${selectedId}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(formData),
        });
        setFormData({ conteudo: "", tipo: "observacao", titulo: "", pratica_ref: "", prioridade: "normal" });
        setShowForm(false);
        loadEntries();
    }

    async function toggleResolved(id: number) {
        await fetch(`${API_BASE}/api/diario/${id}/resolver`, { method: "PUT" });
        loadEntries();
    }

    async function deleteEntry(id: number) {
        if (!confirm("Excluir esta entrada?")) return;
        await fetch(`${API_BASE}/api/diario/${id}`, { method: "DELETE" });
        loadEntries();
    }

    if (loading) return <div className="flex items-center justify-center h-64"><div className="text-4xl animate-pulse">📔</div></div>;

    return (
        <div className="animate-fade-in max-w-4xl">
            <div className="flex items-center justify-between mb-6">
                <div>
                    <h1 className="text-3xl font-bold text-white">📔 Diário de Auditoria</h1>
                    <p className="text-slate-400 mt-1">Observações, decisões e ações pendentes</p>
                </div>
                <div className="flex items-center gap-3">
                    <select value={selectedId ?? ""} onChange={e => setSelectedId(Number(e.target.value))}
                        className="bg-slate-700 border border-slate-600 rounded-xl px-4 py-2 text-sm text-white">
                        {auditorias.map(a => <option key={a.id} value={a.id}>{a.area} ({a.ciclo})</option>)}
                    </select>
                    <button onClick={() => setShowForm(!showForm)}
                        className="px-5 py-2 bg-blue-600 hover:bg-blue-700 rounded-xl text-white text-sm font-medium transition-all">
                        ➕ Nova Entrada
                    </button>
                </div>
            </div>

            {/* New Entry Form */}
            {showForm && (
                <div className="glass-card p-6 mb-6 animate-fade-in space-y-4">
                    <div className="grid grid-cols-3 gap-4">
                        <div>
                            <label className="text-xs text-slate-400 block mb-1">Tipo</label>
                            <select value={formData.tipo} onChange={e => setFormData({ ...formData, tipo: e.target.value })}
                                className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white">
                                {Object.entries(TIPO_CONFIG).map(([k, v]) => <option key={k} value={k}>{v.icon} {v.label}</option>)}
                            </select>
                        </div>
                        <div>
                            <label className="text-xs text-slate-400 block mb-1">Prioridade</label>
                            <select value={formData.prioridade} onChange={e => setFormData({ ...formData, prioridade: e.target.value })}
                                className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white">
                                {Object.entries(PRIORIDADE_CONFIG).map(([k, v]) => <option key={k} value={k}>{v.icon} {k}</option>)}
                            </select>
                        </div>
                        <div>
                            <label className="text-xs text-slate-400 block mb-1">Prática (ref)</label>
                            <input type="text" value={formData.pratica_ref} onChange={e => setFormData({ ...formData, pratica_ref: e.target.value })}
                                className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white" placeholder="Ex: 8.3" />
                        </div>
                    </div>
                    <input type="text" value={formData.titulo} onChange={e => setFormData({ ...formData, titulo: e.target.value })}
                        className="w-full bg-slate-700 border border-slate-600 rounded-xl px-4 py-2.5 text-white" placeholder="Título (opcional)" />
                    <textarea value={formData.conteudo} onChange={e => setFormData({ ...formData, conteudo: e.target.value })}
                        className="w-full bg-slate-700 border border-slate-600 rounded-xl px-4 py-3 text-white text-sm resize-none" rows={3} placeholder="Conteúdo da anotação..." />
                    <div className="flex gap-3">
                        <button onClick={handleCreate} className="px-6 py-2 bg-blue-600 hover:bg-blue-700 rounded-xl text-white text-sm font-medium">💾 Salvar</button>
                        <button onClick={() => setShowForm(false)} className="px-6 py-2 bg-slate-600 hover:bg-slate-700 rounded-xl text-white text-sm">Cancelar</button>
                    </div>
                </div>
            )}

            {/* Entries List */}
            <div className="space-y-3">
                {entries.length === 0 ? (
                    <div className="glass-card p-12 text-center">
                        <div className="text-4xl mb-3">📝</div>
                        <p className="text-slate-400">Nenhuma entrada no diário. Crie a primeira!</p>
                    </div>
                ) : entries.map(entry => {
                    const tipo = TIPO_CONFIG[entry.tipo] || TIPO_CONFIG.observacao;
                    const prio = PRIORIDADE_CONFIG[entry.prioridade] || PRIORIDADE_CONFIG.normal;
                    return (
                        <div key={entry.id} className={`glass-card p-5 transition-all ${entry.resolvido ? "opacity-60" : ""}`}>
                            <div className="flex items-start justify-between">
                                <div className="flex-1">
                                    <div className="flex items-center gap-2 mb-2">
                                        <span className="text-lg">{tipo.icon}</span>
                                        <span className="text-xs px-2 py-0.5 rounded-full font-medium"
                                            style={{ background: `${tipo.color}20`, color: tipo.color }}>{tipo.label}</span>
                                        <span className="text-xs">{prio.icon}</span>
                                        {entry.pratica_ref && <span className="text-xs text-slate-500">Prática {entry.pratica_ref}</span>}
                                        <span className="text-xs text-slate-500">{entry.data_entrada}</span>
                                    </div>
                                    {entry.titulo && <h4 className={`font-medium text-white mb-1 ${entry.resolvido ? "line-through" : ""}`}>{entry.titulo}</h4>}
                                    <p className="text-sm text-slate-300">{entry.conteudo}</p>
                                </div>
                                <div className="flex items-center gap-2 ml-4">
                                    <button onClick={() => toggleResolved(entry.id)} className="text-xs px-3 py-1 rounded-lg bg-slate-700 hover:bg-slate-600 text-slate-300">
                                        {entry.resolvido ? "↩️ Reabrir" : "✅ Resolver"}
                                    </button>
                                    <button onClick={() => deleteEntry(entry.id)} className="text-xs px-3 py-1 rounded-lg bg-red-900/30 hover:bg-red-900/50 text-red-400">
                                        🗑️
                                    </button>
                                </div>
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
