"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
    { href: "/", icon: "🏠", label: "Auditorias" },
    { href: "/dashboard", icon: "📊", label: "Dashboard" },
    { href: "/nova", icon: "➕", label: "Nova Auditoria" },
    { href: "/diario", icon: "📔", label: "Diário" },
    { href: "/relatorios", icon: "📄", label: "Relatórios" },
    { href: "/dados", icon: "💾", label: "Dados & Histórico" },
    { href: "/config", icon: "⚙️", label: "Configurações" },
];

export default function Sidebar() {
    const pathname = usePathname();

    return (
        <aside className="fixed left-0 top-0 bottom-0 w-64 flex flex-col"
            style={{ background: "linear-gradient(180deg, #0f172a 0%, #1a2744 100%)" }}
        >
            {/* Logo */}
            <div className="p-6 text-center border-b border-slate-700/50">
                <div className="text-4xl mb-1">🤖</div>
                <h1 className="text-lg font-bold text-blue-300">Auditoria TA</h1>
                <p className="text-xs text-slate-400 mt-1">Sistema de Auditoria · IA</p>
            </div>

            {/* Navigation */}
            <nav className="flex-1 p-4 space-y-1">
                {NAV_ITEMS.map((item) => {
                    const isActive = pathname === item.href ||
                        (item.href !== "/" && pathname.startsWith(item.href));
                    return (
                        <Link
                            key={item.href}
                            href={item.href}
                            className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 text-sm font-medium
                ${isActive
                                    ? "bg-blue-600/20 text-blue-300 border border-blue-500/30"
                                    : "text-slate-300 hover:bg-slate-700/50 hover:text-white"
                                }`}
                        >
                            <span className="text-lg">{item.icon}</span>
                            {item.label}
                        </Link>
                    );
                })}
            </nav>

            {/* Footer */}
            <div className="p-4 border-t border-slate-700/50">
                <div className="text-xs text-slate-500 text-center">
                    v2.0 — Next.js + FastAPI
                </div>
            </div>
        </aside>
    );
}
