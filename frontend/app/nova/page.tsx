"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { upload } from '@vercel/blob/client';

export default function NovaAuditoriaPage() {
    const router = useRouter();
    const [unidadesAreas, setUnidadesAreas] = useState<Record<string, string[]>>({});
    const [unidade, setUnidade] = useState("");
    const [area, setArea] = useState("");
    const [ciclo, setCiclo] = useState(new Date().getFullYear().toString());
    const [assessmentFile, setAssessmentFile] = useState<File | null>(null);
    const [evidenceFile, setEvidenceFile] = useState<File | null>(null);
    const [evidenceUrl, setEvidenceUrl] = useState("");
    const [modoAnalise, setModoAnalise] = useState<"completo" | "economico">("completo");
    const [creating, setCreating] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        api.getUnidadesAreas().then(setUnidadesAreas).catch(console.error);
    }, []);

    const areas = unidade ? (unidadesAreas[unidade] || []) : [];

    async function handleCreate() {
        if (!unidade || !area || !ciclo) {
            setError("Preencha todos os campos obrigatórios");
            return;
        }

        setCreating(true);
        setError(null);
        try {
            let finalEvidenceUrl = evidenceUrl;
            let finalAssessmentUrl = "";

            const smartUpload = async (file: File, type: "evidence" | "assessment") => {
                const uniqueId = Math.random().toString(36).substring(2, 8);
                const safeName = `${uniqueId}_${file.name.normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/[^a-zA-Z0-9.\-_]/g, "_")}`;
                
                // Tenta Vercel Blob apenas se não houver erro crítico conhecido
                const skipVercel = localStorage.getItem("skip_vercel_blob") === "true";
                
                if (!skipVercel) {
                    try {
                        console.log(`Tentando Vercel Blob para ${file.name}...`);
                        const blob = await upload(safeName, file, {
                            access: 'public',
                            handleUploadUrl: `${window.location.origin}/upload-token`,
                        });
                        return blob.url;
                    } catch (err: any) {
                        console.error("Erro no Vercel Blob:", err);
                        if (err.message?.includes("suspended") || err.message?.includes("forbidden")) {
                            localStorage.setItem("skip_vercel_blob", "true");
                        }
                        // Continue para fallback
                    }
                }

                console.log(`Usando upload direto para o Railway (fallback) para ${file.name}...`);
                const result = await api.uploadDirect(file, type);
                return result.url;
            };

            if (evidenceFile) {
                finalEvidenceUrl = await smartUpload(evidenceFile, "evidence");
            }

            if (assessmentFile) {
                finalAssessmentUrl = await smartUpload(assessmentFile, "assessment");
            }

            const formData = new FormData();
            formData.append("unidade", unidade);
            formData.append("area", area);
            formData.append("ciclo", ciclo);
            formData.append("modo_analise", modoAnalise);
            
            if (finalAssessmentUrl) {
                formData.append("assessment_url", finalAssessmentUrl);
            }
            if (finalEvidenceUrl) {
                formData.append("evidence_url", finalEvidenceUrl);
            }

            const data = await api.criarAuditoria(formData);
            if (data.ok && data.id) {
                router.push(`/auditar/${data.id}`);
            }
        } catch (e: unknown) {
            setError(e instanceof Error ? e.message : "Erro ao enviar arquivos pesados para a nuvem");
        } finally {
            setCreating(false);
        }
    }

    return (
        <div className="animate-fade-in max-w-3xl pb-20">
            <h1 className="text-4xl font-extrabold text-white mb-2 bg-gradient-to-r from-blue-400 to-indigo-400 bg-clip-text text-transparent">
                ➕ Nova Auditoria
            </h1>
            <p className="text-slate-400 mb-10 text-lg">Configure uma nova auditoria de automação industrial</p>

            <div className="glass-card p-10 space-y-8 shadow-2xl border-white/5">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                    {/* Unidade */}
                    <div className="space-y-2">
                        <label className="flex items-center text-sm font-semibold text-slate-300 ml-1">
                            <span className="mr-2">📍</span> Unidade *
                        </label>
                        <select value={unidade} onChange={e => { setUnidade(e.target.value); setArea(""); }}
                            className="w-full bg-slate-800/50 border border-slate-700/50 rounded-2xl px-5 py-4 text-white focus:ring-2 focus:ring-blue-500/50 outline-none transition-all appearance-none cursor-pointer hover:bg-slate-800">
                            <option value="">Selecione a unidade...</option>
                            {Object.keys(unidadesAreas).map(u => <option key={u} value={u}>{u}</option>)}
                        </select>
                    </div>

                    {/* Área */}
                    <div className="space-y-2">
                        <label className="flex items-center text-sm font-semibold text-slate-300 ml-1">
                            <span className="mr-2">🏭</span> Área *
                        </label>
                        <select value={area} onChange={e => setArea(e.target.value)} disabled={!unidade}
                            className="w-full bg-slate-800/50 border border-slate-700/50 rounded-2xl px-5 py-4 text-white focus:ring-2 focus:ring-blue-500/50 outline-none transition-all appearance-none disabled:opacity-30 cursor-pointer hover:bg-slate-800">
                            <option value="">Selecione a área...</option>
                            {areas.map(a => <option key={a} value={a}>{a}</option>)}
                        </select>
                    </div>
                </div>

                {/* Ciclo */}
                <div className="space-y-2">
                    <label className="flex items-center text-sm font-semibold text-slate-300 ml-1">
                        <span className="mr-2">🔄</span> Ciclo *
                    </label>
                    <input type="text" value={ciclo} onChange={e => setCiclo(e.target.value)}
                        className="w-full bg-slate-800/50 border border-slate-700/50 rounded-2xl px-5 py-4 text-white focus:ring-2 focus:ring-blue-500/50 outline-none transition-all hover:bg-slate-800"
                        placeholder="Ex: 2026" />
                </div>

                <div className="h-px bg-slate-800/50 w-full" />

                {/* Assessment File */}
                <div className="space-y-2">
                    <label className="flex items-center text-sm font-semibold text-slate-300 ml-1">
                        <span className="mr-2">📄</span> Arquivo de Assessment (Excel)
                    </label>
                    <div className="flex gap-3">
                        <input type="file" accept=".xlsx,.xls" onChange={e => {
                                const file = e.target.files?.[0];
                                if (file) setAssessmentFile(file);
                            }}
                            className="flex-1 bg-slate-800/50 border border-slate-700/50 rounded-2xl px-5 py-3 text-white text-sm focus:ring-2 focus:ring-blue-500/50 outline-none transition-all file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-sm file:font-semibold file:bg-slate-700 file:text-white hover:file:bg-slate-600"
                        />
                    </div>
                </div>

                {/* Evidence Zip */}
                <div className="space-y-2">
                    <label className="flex items-center text-sm font-semibold text-slate-300 ml-1">
                        <span className="mr-2">📦</span> Pasta de Evidências (Arquivo .ZIP)
                    </label>
                    <div className="flex gap-3">
                        <input type="file" accept=".zip" onChange={e => {
                                const file = e.target.files?.[0];
                                if (file) setEvidenceFile(file);
                            }}
                            className="flex-1 bg-slate-800/50 border border-slate-700/50 rounded-2xl px-5 py-3 text-white text-sm focus:ring-2 focus:ring-blue-500/50 outline-none transition-all file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-sm file:font-semibold file:bg-slate-700 file:text-white hover:file:bg-slate-600"
                        />
                    </div>
                </div>

                {/* Evidence URL Backup */}
                <div className="space-y-2">
                    <label className="flex items-center text-xs font-semibold text-slate-500 ml-1">
                        ...ou informe um Link do Drive (opcional)
                    </label>
                    <div className="flex gap-3">
                        <input type="url" value={evidenceUrl} onChange={e => setEvidenceUrl(e.target.value)}
                            className="flex-1 bg-slate-800/50 border border-slate-700/50 rounded-2xl px-5 py-4 text-white text-sm focus:ring-2 focus:ring-blue-500/50 outline-none transition-all hover:bg-slate-800"
                            placeholder="https://sua-empresa.sharepoint.com/..."
                        />
                    </div>
                </div>

                {/* Opção de Emergência */}
                <div className="flex items-center gap-3 p-4 rounded-xl bg-blue-900/10 border border-blue-700/20">
                    <input 
                        type="checkbox" 
                        id="forceDirect"
                        checked={localStorage.getItem("skip_vercel_blob") === "true"}
                        onChange={(e) => {
                            localStorage.setItem("skip_vercel_blob", e.target.checked ? "true" : "false");
                            // Forçar re-render
                            setCreating(false); 
                        }}
                        className="w-5 h-5 rounded border-slate-700 bg-slate-800 text-blue-500 focus:ring-blue-500/50"
                    />
                    <label htmlFor="forceDirect" className="text-sm text-slate-400 cursor-pointer select-none">
                        🚀 <strong>Modo de Emergência:</strong> Ignorar Vercel Blob e usar servidor Railway (Use se o erro "suspended" persistir)
                    </label>
                </div>

                {error && (
                    <div className="p-5 rounded-2xl bg-red-900/20 border border-red-700/30 text-red-300 text-sm flex items-center animate-shake">
                        <span className="mr-3 text-lg">⚠️</span> {error}
                    </div>
                )}

                <button onClick={handleCreate} disabled={creating}
                    className="w-full py-5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 disabled:opacity-50 text-white rounded-2xl font-bold text-lg transition-all shadow-xl shadow-blue-900/20 hover:scale-[1.01] active:scale-[0.99] flex items-center justify-center gap-2 group">
                    {creating ? (
                        <>
                            <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                            Criando...
                        </>
                    ) : (
                        <>
                            <span>🚀 Criar Auditoria</span>
                            <span className="group-hover:translate-x-1 transition-transform">→</span>
                        </>
                    )}
                </button>
            </div>
        </div>
    );
}
