"use client";

import { useEffect, useState, useCallback } from "react";
import { cleanTitle } from "@/lib/utils";
import { api, Auditoria, ComparativoItem, AuditLogEntry } from "@/lib/api";

type TabKey = "historico" | "comparativo" | "acoes" | "auditlog";

const TABS: { key: TabKey; icon: string; label: string }[] = [
    { key: "historico", icon: "📋", label: "Histórico de Ciclos" },
    { key: "comparativo", icon: "📊", label: "Comparativo entre Ciclos" },
    { key: "acoes", icon: "⚡", label: "Ações Rápidas" },
    { key: "auditlog", icon: "📝", label: "Audit Log" },
];

const STATUS_OPTIONS = [
    { value: "em_andamento", label: "Em Andamento", color: "#3b82f6" },
    { value: "concluida", label: "Concluída", color: "#16a34a" },
    { value: "em_revisao", label: "Em Revisão", color: "#f59e0b" },
    { value: "aprovada", label: "Aprovada", color: "#8b5cf6" },
    { value: "arquivada", label: "Arquivada", color: "#6b7280" },
];

function StatusBadge({ status }: { status: string }) {
    const cfg = STATUS_OPTIONS.find(s => s.value === status) || { label: status, color: "#6b7280" };
    return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold"
            style={{ background: cfg.color + "22", color: cfg.color, border: `1px solid ${cfg.color}44` }}>
            <span className="w-1.5 h-1.5 rounded-full" style={{ background: cfg.color }} />
            {cfg.label}
        </span>
    );
}

function formatDate(d?: string) {
    if (!d) return "—";
    try {
        const dt = new Date(d);
        return dt.toLocaleDateString("pt-BR") + " " + dt.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
    } catch { return d; }
}

export default function DadosPage() {
    const [tab, setTab] = useState<TabKey>("historico");
    const [auditorias, setAuditorias] = useState<Auditoria[]>([]);
    const [loading, setLoading] = useState(true);

    const loadAuditorias = useCallback(async () => {
        setLoading(true);
        try {
            const auds = await api.listAuditorias();
            setAuditorias(auds);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { loadAuditorias(); }, [loadAuditorias]);

    return (
        <div className="animate-fade-in">
            <h1 className="text-3xl font-bold text-white mb-2">💾 Gestão de Dados & Histórico</h1>
            <p className="text-slate-400 mb-6">
                Gerencie o histórico de ciclos, compare auditorias entre anos e controle seus dados.
            </p>

            {/* Tabs */}
            <div className="flex flex-wrap gap-2 mb-6">
                {TABS.map(t => (
                    <button key={t.key} onClick={() => setTab(t.key)}
                        className={`px-4 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 flex items-center gap-2
                            ${tab === t.key
                                ? "bg-blue-600/20 text-blue-300 border border-blue-500/30 shadow-lg shadow-blue-500/10"
                                : "bg-slate-800/50 text-slate-400 border border-slate-700/50 hover:bg-slate-700/50 hover:text-white"
                            }`}>
                        <span>{t.icon}</span>{t.label}
                    </button>
                ))}
            </div>

            {/* Content */}
            {loading ? (
                <div className="glass-card p-12 text-center">
                    <div className="text-4xl mb-3 animate-pulse">⏳</div>
                    <p className="text-slate-400">Carregando dados...</p>
                </div>
            ) : (
                <>
                    {tab === "historico" && <HistoricoTab auditorias={auditorias} />}
                    {tab === "comparativo" && <ComparativoTab auditorias={auditorias} />}
                    {tab === "acoes" && <AcoesTab auditorias={auditorias} onRefresh={loadAuditorias} />}
                    {tab === "auditlog" && <AuditLogTab auditorias={auditorias} />}
                </>
            )}
        </div>
    );
}

/* ════════════════════════════════════════════════════════════════════════════
   TAB 1: HISTÓRICO DE CICLOS
   ════════════════════════════════════════════════════════════════════════════ */

function HistoricoTab({ auditorias }: { auditorias: Auditoria[] }) {
    return (
        <div className="glass-card overflow-hidden">
            <div className="p-5 border-b border-slate-700/50">
                <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                    📋 Todas as Auditorias por Ciclo
                </h3>
                <p className="text-sm text-slate-400 mt-1">{auditorias.length} auditoria(s) encontrada(s)</p>
            </div>
            <div className="overflow-x-auto">
                <table className="w-full text-sm">
                    <thead>
                        <tr className="border-b border-slate-700/50">
                            {["ID", "Unidade", "Área", "Ciclo", "Status", "Criação", "Atualização", "Total Sub", "Avaliados", "Média Final"].map(h => (
                                <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">{h}</th>
                            ))}
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-700/30">
                        {auditorias.map(a => (
                            <tr key={a.id} className="hover:bg-slate-700/20 transition-colors">
                                <td className="px-4 py-3 text-slate-300 font-mono">{a.id}</td>
                                <td className="px-4 py-3 text-white font-medium">{a.unidade}</td>
                                <td className="px-4 py-3 text-slate-300">{a.area}</td>
                                <td className="px-4 py-3 text-blue-300 font-semibold">{a.ciclo}</td>
                                <td className="px-4 py-3"><StatusBadge status={a.status} /></td>
                                <td className="px-4 py-3 text-slate-400 text-xs">{formatDate(a.data_criacao)}</td>
                                <td className="px-4 py-3 text-slate-400 text-xs">{formatDate(a.data_atualizacao)}</td>
                                <td className="px-4 py-3 text-slate-300 text-center">{a.total_subitens}</td>
                                <td className="px-4 py-3 text-slate-300 text-center">{a.subitens_avaliados}</td>
                                <td className="px-4 py-3 text-white font-semibold text-center">
                                    {a.media_nota_final != null ? Number(a.media_nota_final).toFixed(2) : "—"}
                                </td>
                            </tr>
                        ))}
                        {auditorias.length === 0 && (
                            <tr><td colSpan={10} className="px-4 py-8 text-center text-slate-500">Nenhuma auditoria encontrada</td></tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

/* ════════════════════════════════════════════════════════════════════════════
   TAB 2: COMPARATIVO ENTRE CICLOS
   ════════════════════════════════════════════════════════════════════════════ */

function ComparativoTab({ auditorias }: { auditorias: Auditoria[] }) {
    const [idA, setIdA] = useState<number | "">(auditorias[0]?.id ?? "");
    const [idB, setIdB] = useState<number | "">(auditorias[1]?.id ?? auditorias[0]?.id ?? "");
    const [result, setResult] = useState<ComparativoItem[] | null>(null);
    const [comparing, setComparing] = useState(false);
    const [info, setInfo] = useState<{ a?: { ciclo: string }; b?: { ciclo: string } }>({});

    async function handleCompare() {
        if (!idA || !idB) return;
        setComparing(true);
        try {
            const data = await api.getComparativo(Number(idA), Number(idB));
            setResult(data.comparativo);
            setInfo({ a: data.auditoria_a, b: data.auditoria_b });
        } catch (e: unknown) {
            alert(e instanceof Error ? e.message : "Erro no comparativo");
        } finally {
            setComparing(false);
        }
    }

    const audLabel = (a: Auditoria) => `[${a.id}] ${a.unidade} / ${a.area} — ${a.ciclo}`;

    return (
        <div className="space-y-6">
            <div className="glass-card p-6">
                <h3 className="text-lg font-semibold text-white mb-4">📊 Comparativo entre Ciclos</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                    <div>
                        <label className="text-sm text-slate-300 block mb-2">Base (Ciclo A)</label>
                        <select value={idA} onChange={e => setIdA(Number(e.target.value))}
                            className="w-full bg-slate-700 border border-slate-600 rounded-xl px-4 py-3 text-white">
                            {auditorias.map(a => <option key={a.id} value={a.id}>{audLabel(a)}</option>)}
                        </select>
                    </div>
                    <div>
                        <label className="text-sm text-slate-300 block mb-2">Comparação (Ciclo B)</label>
                        <select value={idB} onChange={e => setIdB(Number(e.target.value))}
                            className="w-full bg-slate-700 border border-slate-600 rounded-xl px-4 py-3 text-white">
                            {auditorias.map(a => <option key={a.id} value={a.id}>{audLabel(a)}</option>)}
                        </select>
                    </div>
                </div>
                <button onClick={handleCompare} disabled={comparing || !idA || !idB}
                    className="w-full py-3 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded-xl font-semibold transition-all">
                    {comparing ? "Comparando..." : "📊 Comparar Ciclos"}
                </button>
            </div>

            {result && (
                <div className="glass-card overflow-hidden">
                    <div className="p-5 border-b border-slate-700/50">
                        <h3 className="text-lg font-semibold text-white">
                            Resultado: {info.a?.ciclo || "A"} vs {info.b?.ciclo || "B"}
                        </h3>
                        <p className="text-sm text-slate-400 mt-1">{result.length} subiten(s) comparados</p>
                    </div>
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="border-b border-slate-700/50">
                                    {["Prática", "Subitem", `Nota A (${info.a?.ciclo || "A"})`, `Nota B (${info.b?.ciclo || "B"})`, "Delta", "Tendência"].map(h => (
                                        <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">{h}</th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-700/30">
                                {result.map((r, i) => (
                                    <tr key={i} className="hover:bg-slate-700/20 transition-colors">
                                        <td className="px-4 py-3 text-white">{r.pratica_num}. {cleanTitle(r.pratica_nome)}</td>
                                        <td className="px-4 py-3 text-slate-300">{r.pratica_num}.{(r.subitem_idx ?? 0) + 1} {cleanTitle(r.subitem_nome)}</td>
                                        <td className="px-4 py-3 text-slate-300 text-center">{r.nota_a ?? "—"}</td>
                                        <td className="px-4 py-3 text-slate-300 text-center">{r.nota_b ?? "—"}</td>
                                        <td className="px-4 py-3 text-center font-semibold" style={{
                                            color: r.delta != null ? (r.delta > 0 ? "#16a34a" : r.delta < 0 ? "#dc2626" : "#6b7280") : "#6b7280"
                                        }}>
                                            {r.delta != null ? (r.delta > 0 ? `+${r.delta}` : r.delta) : "—"}
                                        </td>
                                        <td className="px-4 py-3">{r.tendencia}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}
        </div>
    );
}

/* ════════════════════════════════════════════════════════════════════════════
   TAB 3: AÇÕES RÁPIDAS
   ════════════════════════════════════════════════════════════════════════════ */

function AcoesTab({ auditorias, onRefresh }: { auditorias: Auditoria[]; onRefresh: () => void }) {
    // Status change
    const [statusAudId, setStatusAudId] = useState<number>(auditorias[0]?.id ?? 0);
    const [newStatus, setNewStatus] = useState("em_andamento");
    const [statusMsg, setStatusMsg] = useState("");

    // Duplicate
    const [dupAudId, setDupAudId] = useState<number>(auditorias[0]?.id ?? 0);
    const [novoCiclo, setNovoCiclo] = useState(String(new Date().getFullYear()));
    const [dupMsg, setDupMsg] = useState("");

    // Delete
    const [delAudId, setDelAudId] = useState<number>(auditorias[0]?.id ?? 0);
    const [delConfirm, setDelConfirm] = useState(false);
    const [delMsg, setDelMsg] = useState("");

    const audLabel = (a: Auditoria) => `[${a.id}] ${a.unidade} / ${a.area} — ${a.ciclo}`;

    async function handleApplyStatus() {
        setStatusMsg("");
        try {
            await api.updateStatus(statusAudId, newStatus);
            setStatusMsg("✅ Status atualizado com sucesso!");
            onRefresh();
        } catch (e: unknown) {
            setStatusMsg("❌ " + (e instanceof Error ? e.message : "Erro"));
        }
    }

    async function handleDuplicate() {
        setDupMsg("");
        try {
            const res = await api.duplicarAuditoria(dupAudId, novoCiclo);
            setDupMsg(`✅ Auditoria duplicada! Novo ID: ${res.novo_id}, Ciclo: ${res.novo_ciclo}`);
            onRefresh();
        } catch (e: unknown) {
            setDupMsg("❌ " + (e instanceof Error ? e.message : "Erro"));
        }
    }

    async function handleDelete() {
        if (!delConfirm) return;
        setDelMsg("");
        try {
            await api.excluirAuditoria(delAudId);
            setDelMsg("✅ Auditoria excluída com sucesso!");
            setDelConfirm(false);
            onRefresh();
        } catch (e: unknown) {
            setDelMsg("❌ " + (e instanceof Error ? e.message : "Erro"));
        }
    }

    return (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Alterar Status */}
            <div className="glass-card p-6">
                <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                    🔄 Alterar Status
                </h3>
                <div className="space-y-3">
                    <div>
                        <label className="text-sm text-slate-300 block mb-1">Auditoria</label>
                        <select value={statusAudId} onChange={e => setStatusAudId(Number(e.target.value))}
                            className="w-full bg-slate-700 border border-slate-600 rounded-xl px-3 py-2.5 text-white text-sm">
                            {auditorias.map(a => <option key={a.id} value={a.id}>{audLabel(a)}</option>)}
                        </select>
                    </div>
                    <div>
                        <label className="text-sm text-slate-300 block mb-1">Novo Status</label>
                        <select value={newStatus} onChange={e => setNewStatus(e.target.value)}
                            className="w-full bg-slate-700 border border-slate-600 rounded-xl px-3 py-2.5 text-white text-sm">
                            {STATUS_OPTIONS.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
                        </select>
                    </div>
                    <button onClick={handleApplyStatus}
                        className="w-full py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-medium transition-all text-sm flex items-center justify-center gap-2">
                        ✅ Aplicar Status
                    </button>
                    {statusMsg && <p className="text-sm mt-1" style={{ color: statusMsg.startsWith("✅") ? "#16a34a" : "#dc2626" }}>{statusMsg}</p>}
                </div>
            </div>

            {/* Duplicar para Novo Ciclo */}
            <div className="glass-card p-6">
                <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                    📋 Iniciar Novo Ciclo (duplicar)
                </h3>
                <div className="space-y-3">
                    <div>
                        <label className="text-sm text-slate-300 block mb-1">Base</label>
                        <select value={dupAudId} onChange={e => setDupAudId(Number(e.target.value))}
                            className="w-full bg-slate-700 border border-slate-600 rounded-xl px-3 py-2.5 text-white text-sm">
                            {auditorias.map(a => <option key={a.id} value={a.id}>{audLabel(a)}</option>)}
                        </select>
                    </div>
                    <div>
                        <label className="text-sm text-slate-300 block mb-1">Nome do Novo Ciclo</label>
                        <input type="text" value={novoCiclo} onChange={e => setNovoCiclo(e.target.value)}
                            className="w-full bg-slate-700 border border-slate-600 rounded-xl px-3 py-2.5 text-white text-sm"
                            placeholder="Ex: 2026" />
                    </div>
                    <button onClick={handleDuplicate} disabled={!novoCiclo.trim()}
                        className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white rounded-xl font-medium transition-all text-sm flex items-center justify-center gap-2">
                        📋 Duplicar para Novo Ciclo
                    </button>
                    {dupMsg && <p className="text-sm mt-1" style={{ color: dupMsg.startsWith("✅") ? "#16a34a" : "#dc2626" }}>{dupMsg}</p>}
                </div>
            </div>

            {/* Excluir Auditoria */}
            <div className="glass-card p-6" style={{ borderColor: "#dc262644" }}>
                <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                    🗑️ Excluir Auditoria
                </h3>
                <div className="p-3 rounded-xl mb-3" style={{ background: "#fef3c720", border: "1px solid #f59e0b33" }}>
                    <p className="text-amber-400 text-xs flex items-center gap-1.5">
                        ⚠️ Operação irreversível. Um backup será criado automaticamente.
                    </p>
                </div>
                <div className="space-y-3">
                    <div>
                        <label className="text-sm text-slate-300 block mb-1">Auditoria a Excluir</label>
                        <select value={delAudId} onChange={e => { setDelAudId(Number(e.target.value)); setDelConfirm(false); }}
                            className="w-full bg-slate-700 border border-slate-600 rounded-xl px-3 py-2.5 text-white text-sm">
                            {auditorias.map(a => <option key={a.id} value={a.id}>{audLabel(a)}</option>)}
                        </select>
                    </div>
                    <label className="flex items-center gap-2 text-sm text-slate-300 cursor-pointer">
                        <input type="checkbox" checked={delConfirm} onChange={e => setDelConfirm(e.target.checked)}
                            className="rounded border-slate-600" />
                        Confirmo que desejo excluir
                    </label>
                    <button onClick={handleDelete} disabled={!delConfirm}
                        className="w-full py-2.5 bg-red-600 hover:bg-red-700 disabled:opacity-30 text-white rounded-xl font-medium transition-all text-sm flex items-center justify-center gap-2">
                        🗑️ Excluir
                    </button>
                    {delMsg && <p className="text-sm mt-1" style={{ color: delMsg.startsWith("✅") ? "#16a34a" : "#dc2626" }}>{delMsg}</p>}
                </div>
            </div>
        </div>
    );
}

/* ════════════════════════════════════════════════════════════════════════════
   TAB 4: AUDIT LOG
   ════════════════════════════════════════════════════════════════════════════ */

function AuditLogTab({ auditorias }: { auditorias: Auditoria[] }) {
    const [filterId, setFilterId] = useState<number | "">(""); 
    const [entries, setEntries] = useState<AuditLogEntry[]>([]);
    const [loading, setLoading] = useState(false);

    async function loadLog() {
        setLoading(true);
        try {
            const data = await api.getAuditLog(filterId ? Number(filterId) : undefined);
            setEntries(data);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    }

    useEffect(() => { loadLog(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

    const audLabel = (a: Auditoria) => `[${a.id}] ${a.unidade} / ${a.area} — ${a.ciclo}`;

    return (
        <div className="space-y-6">
            <div className="glass-card p-6">
                <h3 className="text-lg font-semibold text-white mb-4">📝 Log de Alterações</h3>
                <div className="flex flex-col sm:flex-row gap-3">
                    <div className="flex-1">
                        <select value={filterId} onChange={e => setFilterId(e.target.value ? Number(e.target.value) : "")}
                            className="w-full bg-slate-700 border border-slate-600 rounded-xl px-4 py-3 text-white text-sm">
                            <option value="">Todas as auditorias</option>
                            {auditorias.map(a => <option key={a.id} value={a.id}>{audLabel(a)}</option>)}
                        </select>
                    </div>
                    <button onClick={loadLog} disabled={loading}
                        className="px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded-xl font-medium transition-all text-sm">
                        {loading ? "Carregando..." : "🔍 Filtrar"}
                    </button>
                </div>
            </div>

            <div className="glass-card overflow-hidden">
                <div className="p-5 border-b border-slate-700/50">
                    <p className="text-sm text-slate-400">{entries.length} registro(s) encontrado(s)</p>
                </div>
                <div className="overflow-x-auto max-h-[500px] overflow-y-auto">
                    <table className="w-full text-sm">
                        <thead className="sticky top-0 bg-slate-800/95 backdrop-blur-sm">
                            <tr className="border-b border-slate-700/50">
                                {["Timestamp", "Aud. ID", "Prática", "Sub", "Campo", "Antes", "Depois", "Usuário"].map(h => (
                                    <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">{h}</th>
                                ))}
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-700/30">
                            {entries.map(e => (
                                <tr key={e.id} className="hover:bg-slate-700/20 transition-colors">
                                    <td className="px-4 py-2.5 text-slate-400 text-xs font-mono whitespace-nowrap">{formatDate(e.timestamp)}</td>
                                    <td className="px-4 py-2.5 text-slate-300">{e.auditoria_id}</td>
                                    <td className="px-4 py-2.5 text-slate-300">{e.pratica_num ?? "—"}</td>
                                    <td className="px-4 py-2.5 text-slate-300">{e.subitem_idx != null ? e.subitem_idx + 1 : "—"}</td>
                                    <td className="px-4 py-2.5 text-blue-300 font-medium">{e.campo}</td>
                                    <td className="px-4 py-2.5 text-red-400 text-xs max-w-[150px] truncate">{e.valor_antes || "—"}</td>
                                    <td className="px-4 py-2.5 text-green-400 text-xs max-w-[150px] truncate">{e.valor_depois || "—"}</td>
                                    <td className="px-4 py-2.5 text-slate-400">{e.usuario}</td>
                                </tr>
                            ))}
                            {entries.length === 0 && (
                                <tr><td colSpan={8} className="px-4 py-8 text-center text-slate-500">Nenhum registro encontrado</td></tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}
