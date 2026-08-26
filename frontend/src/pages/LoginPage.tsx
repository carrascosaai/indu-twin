import { useQuery } from "@tanstack/react-query";
import { AlertCircle, ChevronDown, Factory, Loader2 } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { fetchSetupStatus, forgotPassword, registerFirstAdmin } from "../api/client";
import { useAuth } from "../context/AuthContext";

const DEMO_ACCOUNTS = [
  { email: "admin@indutwin.com", password: "admin123", label: "Administrador" },
  { email: "viewer@indutwin.com", password: "viewer123", label: "Operario" },
];

function errorMessage(err: unknown, fallback: string): string {
  const status = (err as { response?: { status?: number; data?: { detail?: string } } })
    ?.response;
  if (status?.status === 429) {
    return "Demasiados intentos fallidos. Espera unos minutos antes de volver a intentarlo.";
  }
  return status?.data?.detail ?? fallback;
}

function SetupForm({ onDone }: { onDone: () => void }) {
  const { applyToken } = useAuth();
  const navigate = useNavigate();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const { access_token } = await registerFirstAdmin({
        email,
        password,
        full_name: fullName,
      });
      applyToken(access_token);
      navigate("/", { replace: true });
    } catch (err) {
      setError(errorMessage(err, "No se pudo crear la cuenta"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <h1 className="mb-1 text-lg font-semibold text-white">Configura tu cuenta</h1>
      <p className="mb-6 text-sm text-slate-400">
        Esta instancia de INDU-TWIN todavía no tiene ninguna cuenta. Crea la tuya para
        empezar — serás el administrador.
      </p>
      <form onSubmit={handleSubmit} className="space-y-3">
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-400">Nombre completo</label>
          <input
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            className="w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white outline-none transition focus:border-blue-400"
            required
          />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-400">Email</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white outline-none transition focus:border-blue-400"
            required
          />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-400">Contraseña</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            minLength={8}
            className="w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white outline-none transition focus:border-blue-400"
            required
          />
          <p className="mt-1 text-[11px] text-slate-500">Mínimo 8 caracteres.</p>
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
          {loading ? "Creando cuenta..." : "Crear cuenta y entrar"}
        </button>
      </form>

      <button
        onClick={onDone}
        className="mt-4 w-full text-center text-xs font-medium text-slate-400 transition hover:text-slate-300"
      >
        ¿Ya tienes cuenta? Inicia sesión
      </button>
    </>
  );
}

function ForgotPasswordForm({ onDone }: { onDone: () => void }) {
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await forgotPassword(email);
      setMessage(res.message);
    } catch (err) {
      setError(errorMessage(err, "No se pudo procesar la solicitud"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <h1 className="mb-1 text-lg font-semibold text-white">Recuperar contraseña</h1>
      <p className="mb-6 text-sm text-slate-400">
        Te mandamos un enlace a tu email para crear una contraseña nueva.
      </p>

      {message ? (
        <p className="rounded-md border border-slate-800 bg-slate-950 p-3 text-sm text-slate-300">
          {message}
        </p>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-400">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
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
            {loading ? "Enviando..." : "Enviar enlace"}
          </button>
        </form>
      )}

      <button
        onClick={onDone}
        className="mt-4 w-full text-center text-xs font-medium text-slate-400 transition hover:text-slate-300"
      >
        Volver a iniciar sesión
      </button>
    </>
  );
}

export default function LoginPage() {
  const { login, token } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [showDemoAccounts, setShowDemoAccounts] = useState(false);
  const [forceLoginView, setForceLoginView] = useState(false);
  const [showForgotPassword, setShowForgotPassword] = useState(false);

  const { data: setupStatus } = useQuery({
    queryKey: ["setup-status"],
    queryFn: fetchSetupStatus,
    staleTime: 60_000,
  });

  if (token) {
    const from = (location.state as { from?: string })?.from ?? "/";
    return <Navigate to={from} replace />;
  }

  const showSetup = setupStatus?.needs_setup && !forceLoginView;

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(email, password);
      navigate("/", { replace: true });
    } catch (err) {
      setError(errorMessage(err, "Email o contraseña incorrectos"));
    } finally {
      setLoading(false);
    }
  };

  const useDemoAccount = (demoEmail: string, demoPassword: string) => {
    setEmail(demoEmail);
    setPassword(demoPassword);
    setError(null);
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

        {showSetup ? (
          <SetupForm onDone={() => setForceLoginView(true)} />
        ) : showForgotPassword ? (
          <ForgotPasswordForm onDone={() => setShowForgotPassword(false)} />
        ) : (
          <>
            <h1 className="mb-1 text-lg font-semibold text-white">Iniciar sesión</h1>
            <p className="mb-6 text-sm text-slate-400">Accede a tu panel de polígonos industriales.</p>

            <form onSubmit={handleSubmit} className="space-y-3">
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-400">Email</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white outline-none transition focus:border-blue-400"
                  required
                />
              </div>
              <div>
                <div className="mb-1 flex items-center justify-between">
                  <label className="block text-xs font-medium text-slate-400">Contraseña</label>
                  <button
                    type="button"
                    onClick={() => setShowForgotPassword(true)}
                    className="text-[11px] font-medium text-blue-400 transition hover:text-blue-300"
                  >
                    ¿Olvidaste tu contraseña?
                  </button>
                </div>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
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
                {loading ? "Entrando..." : "Entrar"}
              </button>
            </form>

            <div className="mt-5 border-t border-slate-800 pt-4">
              <button
                onClick={() => setShowDemoAccounts((v) => !v)}
                className="flex w-full items-center justify-between text-xs font-medium text-slate-400 transition hover:text-slate-300"
              >
                Cuentas de demostración
                <ChevronDown
                  size={14}
                  strokeWidth={2}
                  className={`transition-transform ${showDemoAccounts ? "rotate-180" : ""}`}
                />
              </button>
              {showDemoAccounts && (
                <div className="mt-2 space-y-1.5">
                  {DEMO_ACCOUNTS.map((acc) => (
                    <button
                      key={acc.email}
                      type="button"
                      onClick={() => useDemoAccount(acc.email, acc.password)}
                      className="flex w-full items-center justify-between rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-left text-xs transition hover:border-blue-800"
                    >
                      <span className="text-slate-400">{acc.email}</span>
                      <span className="rounded-full bg-slate-800 px-1.5 py-0.5 text-[10px] font-medium text-slate-300">
                        {acc.label}
                      </span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
