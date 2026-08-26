import { AlertCircle, CheckCircle2, Factory, Loader2 } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { resetPassword } from "../api/client";

export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") ?? "";
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    if (password !== confirmPassword) {
      setError("Las contraseñas no coinciden");
      return;
    }
    setLoading(true);
    try {
      await resetPassword(token, password);
      setDone(true);
    } catch (err) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data
        ?.detail;
      setError(detail ?? "No se pudo restablecer la contraseña");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-slate-950 px-4">
      <div
        className="pointer-events-none absolute inset-0 opacity-40"
        style={{
          background:
            "radial-gradient(600px circle at 20% 20%, rgba(59,130,246,0.15), transparent 60%), radial-gradient(500px circle at 80% 80%, rgba(59,130,246,0.1), transparent 60%)",
        }}
      />
      <div className="relative w-full max-w-sm rounded-2xl border border-slate-800 bg-slate-900 p-8 shadow-2xl shadow-black/40">
        <div className="mb-6 flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-blue-400 to-blue-600 text-white shadow-sm shadow-blue-900/40">
            <Factory size={18} strokeWidth={2.25} />
          </div>
          <div>
            <p className="text-sm font-semibold text-white">INDU-TWIN</p>
            <p className="text-[11px] text-slate-400">Digital Twin SaaS</p>
          </div>
        </div>

        {!token ? (
          <p className="flex items-center gap-1.5 text-sm text-red-400">
            <AlertCircle size={14} strokeWidth={2} />
            Enlace inválido: falta el token.
          </p>
        ) : done ? (
          <>
            <p className="flex items-center gap-1.5 text-sm text-emerald-400">
              <CheckCircle2 size={16} strokeWidth={2} />
              Contraseña actualizada.
            </p>
            <Link
              to="/login"
              className="mt-4 flex w-full items-center justify-center rounded-md bg-blue-600 py-2 text-sm font-medium text-white transition hover:bg-blue-700"
            >
              Iniciar sesión
            </Link>
          </>
        ) : (
          <>
            <h1 className="mb-1 text-lg font-semibold text-white">Nueva contraseña</h1>
            <p className="mb-6 text-sm text-slate-400">Elige una contraseña nueva para tu cuenta.</p>

            <form onSubmit={handleSubmit} className="space-y-3">
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-400">Contraseña nueva</label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  minLength={8}
                  className="w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white outline-none transition focus:border-blue-400"
                  required
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-400">Repite la contraseña</label>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  minLength={8}
                  className="w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white outline-none transition focus:border-blue-400"
                  required
                />
              </div>

              {error && (
                <p className="flex items-center gap-1.5 text-xs text-red-400">
                  <AlertCircle size={13} strokeWidth={2} />
                  {error}
                </p>
              )}

              <button
                type="submit"
                disabled={loading}
                className="flex w-full items-center justify-center gap-2 rounded-md bg-blue-600 py-2 text-sm font-medium text-white transition hover:bg-blue-700 disabled:opacity-60"
              >
                {loading && <Loader2 size={14} className="animate-spin" />}
                {loading ? "Guardando..." : "Guardar contraseña"}
              </button>
            </form>
          </>
        )}
      </div>
    </div>
  );
}
