"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

export default function LoginPage() {
  const [isRegister, setIsRegister] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const validatePassword = (pass: string) => {
    if (!isRegister) return null;
    const rules = [
      { check: pass.length >= 8, label: "Mínimo 8 caracteres" },
      { check: /[A-Z]/.test(pass), label: "Uma letra maiúscula" },
      { check: /[0-9]/.test(pass), label: "Um número" },
      { check: /[!@#$%^&*(),.?":{}|<>]/.test(pass), label: "Um caractere especial" }
    ];
    const failed = rules.find(r => !r.check);
    return failed ? failed.label : null;
  };

  const handleAction = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setMessage(null);

    const emailLower = email.toLowerCase().trim();
    if (!emailLower.endsWith("@automateasy.com.br")) {
      setError("Acesso restrito a e-mails @automateasy.com.br");
      return;
    }

    const passError = validatePassword(password);
    if (passError) {
      setError(`Segurança da Senha: ${passError}`);
      return;
    }

    setLoading(true);
    try {
      if (isRegister) {
        await api.register(emailLower, password);
        setMessage("Acesso configurado com sucesso! Agora você pode entrar.");
        setIsRegister(false);
        setPassword("");
      } else {
        const data = await api.login(emailLower, password);
        localStorage.setItem("audit_token", data.access_token);
        localStorage.setItem("audit_user", data.email);
        router.push("/");
      }
    } catch (err: any) {
      setError(err.message || "Erro ao processar solicitação");
    } finally {
      setLoading(false);
    }
  };

  const passwordRules = [
    { met: password.length >= 8, label: "8+ caracteres" },
    { met: /[A-Z]/.test(password), label: "Maiúscula" },
    { met: /[0-9]/.test(password), label: "Número" },
    { met: /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password), label: "Símbolo" }
  ];

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#0f172a] px-4 font-inter text-slate-200">
      <div className="w-full max-w-md animate-fade-in py-12">
        <div className="glass-card overflow-hidden rounded-[2.5rem] border border-slate-700/50 bg-slate-900/70 p-10 shadow-2xl shadow-blue-900/20 backdrop-blur-2xl">
          <div className="mb-10 text-center">
            <div className="inline-flex h-20 w-20 items-center justify-center rounded-3xl bg-blue-600/10 text-4xl mb-6 border border-blue-500/20 shadow-inner">
              🛡️
            </div>
            <h1 className="text-3xl font-black text-white tracking-tight uppercase">Audit System</h1>
            <p className="text-slate-400 mt-2 font-semibold tracking-wide text-sm">
              {isRegister ? "CONFIGURAR / REDEFINIR SENHA" : "PORTAL DE ACESSO RESTRITO"}
            </p>
          </div>

          <form onSubmit={handleAction} className="space-y-7">
            <div className="space-y-2">
              <label className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-500 ml-1">
                E-mail Corporativo
              </label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-2xl border border-slate-700 bg-slate-800/40 px-6 py-4 text-white transition-all focus:border-blue-500/60 focus:outline-none focus:ring-4 focus:ring-blue-500/10"
                placeholder="nome@automateasy.com.br"
              />
            </div>

            <div className="space-y-2">
              <label className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-500 ml-1">
                {isRegister ? "Nova Senha de Segurança" : "Senha Pessoal"}
              </label>
              <div className="relative group">
                <input
                  type={showPassword ? "text" : "password"}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full rounded-2xl border border-slate-700 bg-slate-800/40 px-6 py-4 text-white transition-all focus:border-blue-500/60 focus:outline-none focus:ring-4 focus:ring-blue-500/10 pr-14"
                  placeholder="••••••••"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-500 hover:text-white transition-colors p-2"
                >
                  {showPassword ? (
                    <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l18 18" />
                    </svg>
                  ) : (
                    <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                    </svg>
                  )}
                </button>
              </div>

              {isRegister && (
                <div className="flex flex-wrap gap-x-3 gap-y-1 mt-3 px-2">
                  {passwordRules.map((rule, idx) => (
                    <div key={idx} className={`text-[9px] font-bold uppercase flex items-center gap-1 transition-colors ${rule.met ? "text-green-400" : "text-slate-600"}`}>
                      <span className={`w-1 h-1 rounded-full ${rule.met ? "bg-green-400 shadow-[0_0_5px_rgba(74,222,128,0.5)]" : "bg-slate-700"}`} />
                      {rule.label}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {error && (
              <div className="rounded-2xl border border-red-500/20 bg-red-500/10 p-4 text-xs font-bold text-red-400 flex items-center gap-3 animate-shake">
                <span>⚠️</span> {error}
              </div>
            )}

            {message && (
              <div className="rounded-2xl border border-green-500/20 bg-green-500/10 p-4 text-xs font-bold text-green-400 flex items-center gap-3 animate-fade-in">
                <span>✅</span> {message}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="flex w-full items-center justify-center rounded-2xl bg-gradient-to-br from-blue-600 to-indigo-700 px-6 py-4.5 text-sm font-black uppercase tracking-widest text-white shadow-xl shadow-blue-900/30 transition-all hover:scale-[1.03] active:scale-[0.97] disabled:opacity-50 disabled:grayscale"
            >
              {loading ? (
                <div className="h-5 w-5 animate-spin rounded-full border-2 border-white/20 border-t-white" />
              ) : (
                isRegister ? "Ativar Acesso" : "Autenticar"
              )}
            </button>
          </form>

          <div className="mt-12 text-center">
            <button
              onClick={() => { setIsRegister(!isRegister); setError(null); setMessage(null); }}
              className="text-xs font-bold text-slate-500 hover:text-blue-400 transition-colors uppercase tracking-widest flex items-center justify-center gap-4 w-full"
            >
              <div className="h-[1px] flex-1 bg-slate-800" />
              {isRegister ? "Voltar ao Login" : "Primeiro Acesso / Redefinir Senha"}
              <div className="h-[1px] flex-1 bg-slate-800" />
            </button>
          </div>

          <div className="mt-10 flex items-center justify-center gap-6 opacity-30 grayscale">
            <span className="text-[10px] font-black tracking-widest">SSL SECURE</span>
            <span className="text-[10px] font-black tracking-widest">BCRYPT AES</span>
          </div>
        </div>

        <p className="mt-8 text-center text-[9px] font-black text-slate-600 uppercase tracking-[0.4em]">
          Automateasy Cyber Intelligence &bull; 2026
        </p>
      </div>
    </div>
  );
}
