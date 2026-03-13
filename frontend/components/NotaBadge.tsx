"use client";

import { ESCALA } from "@/lib/api";

interface NotaBadgeProps {
    nota: number | null | undefined;
    size?: "sm" | "md" | "lg";
    showLabel?: boolean;
}

export default function NotaBadge({ nota, size = "md", showLabel = true }: NotaBadgeProps) {
    if (nota == null) {
        return (
            <span className={`nota-badge ${sizeClass(size)}`}
                style={{ background: "#475569", color: "white" }}>
                ⏳ {showLabel && "Pendente"}
            </span>
        );
    }

    const info = ESCALA[nota] || { emoji: "❔", desc: "?", color: "#6b7280" };

    return (
        <span className={`nota-badge ${sizeClass(size)}`}
            style={{ background: info.color, color: "white" }}>
            {info.emoji} {nota} {showLabel && `— ${info.desc}`}
        </span>
    );
}

function sizeClass(size: string) {
    switch (size) {
        case "sm": return "text-xs py-0.5 px-2";
        case "lg": return "text-base py-2 px-5";
        default: return "";
    }
}
