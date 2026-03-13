"use client";

import { useState, useEffect, useRef } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface ChatMessage {
    id?: number;
    role: string;
    conteudo: string;
    timestamp?: string;
}

interface ChatPanelProps {
    avaliacaoId: number;
    auditoriaId: number;
    praticaNum: number;
    subitemIdx: number;
    apiKey: string;
}

export default function ChatPanel({ avaliacaoId, auditoriaId, praticaNum, subitemIdx, apiKey }: ChatPanelProps) {
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [input, setInput] = useState("");
    const [sending, setSending] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        loadMessages();
    }, []);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    async function loadMessages() {
        try {
            const res = await fetch(`${API_BASE}/api/chat/${auditoriaId}/${praticaNum}/${subitemIdx}`);
            const data = await res.json();
            setMessages(data);
        } catch { /* ignore */ }
    }

    async function handleSend() {
        if (!input.trim() || sending) return;
        const msg = input.trim();
        setInput("");
        setSending(true);

        // Optimistic UI
        setMessages(prev => [...prev, { role: "user", conteudo: msg }]);

        try {
            const res = await fetch(`${API_BASE}/api/chat/${avaliacaoId}`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ api_key: apiKey, message: msg, economico: false }),
            });
            const data = await res.json();
            if (data.ok) {
                setMessages(prev => [...prev, { role: "assistant", conteudo: data.response }]);
            } else {
                setMessages(prev => [...prev, { role: "sistema", conteudo: `Erro: ${data.detail || "Falha"}` }]);
            }
        } catch (e: unknown) {
            setMessages(prev => [...prev, { role: "sistema", conteudo: `Erro: ${e instanceof Error ? e.message : "Conexão falhou"}` }]);
        } finally {
            setSending(false);
        }
    }

    return (
        <div className="rounded-xl overflow-hidden" style={{ background: "rgba(30, 41, 59, 0.5)", border: "1px solid rgba(51, 65, 85, 0.5)" }}>
            {/* Header */}
            <div className="px-4 py-2.5 border-b border-slate-700/50 flex items-center gap-2">
                <span className="text-sm">💬</span>
                <span className="text-xs font-semibold text-slate-300">Chat com IA — Revisão Colaborativa</span>
            </div>

            {/* Messages */}
            <div className="max-h-64 overflow-y-auto p-3 space-y-2">
                {messages.length === 0 && (
                    <p className="text-xs text-slate-500 text-center py-4">
                        Converse com a IA para revisar esta avaliação
                    </p>
                )}
                {messages.map((msg, i) => (
                    <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                        <div className={`max-w-[80%] px-3 py-2 rounded-xl text-xs leading-relaxed ${msg.role === "user"
                                ? "bg-blue-600/30 text-blue-100 rounded-br-sm"
                                : msg.role === "assistant"
                                    ? "bg-slate-700/60 text-slate-200 rounded-bl-sm"
                                    : "bg-red-900/30 text-red-300 rounded-bl-sm"
                            }`}>
                            <div className="flex items-center gap-1.5 mb-0.5 opacity-70">
                                <span>{msg.role === "user" ? "👤" : msg.role === "assistant" ? "🤖" : "⚠️"}</span>
                                <span className="font-medium">{msg.role === "user" ? "Você" : msg.role === "assistant" ? "IA" : "Sistema"}</span>
                            </div>
                            <p className="whitespace-pre-wrap">{msg.conteudo}</p>
                        </div>
                    </div>
                ))}
                {sending && (
                    <div className="flex justify-start">
                        <div className="bg-slate-700/60 px-3 py-2 rounded-xl text-xs text-slate-400 animate-pulse">
                            🤖 Pensando...
                        </div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <div className="p-3 border-t border-slate-700/50 flex gap-2">
                <input
                    type="text"
                    value={input}
                    onChange={e => setInput(e.target.value)}
                    onKeyDown={e => e.key === "Enter" && handleSend()}
                    placeholder="Digite sua mensagem..."
                    className="flex-1 bg-slate-700/50 border border-slate-600 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:ring-1 focus:ring-blue-500"
                    disabled={sending}
                />
                <button onClick={handleSend} disabled={sending || !input.trim()}
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-40 rounded-lg text-xs text-white font-medium transition-all">
                    Enviar
                </button>
            </div>
        </div>
    );
}
