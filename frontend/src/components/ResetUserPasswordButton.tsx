import { KeyRound } from "lucide-react";
import { useState } from "react";
import { updateUser } from "../api/client";
import { useToast } from "../context/ToastContext";

/** Botón admin-only para poner una contraseña nueva a otro usuario, sin
 * depender del email de recuperación (util si SMTP no esta configurado,
 * o simplemente para rotar las contraseñas de las cuentas demo). */
export default function ResetUserPasswordButton({ userId }: { userId: number }) {
  const { showToast } = useToast();
  const [open, setOpen] = useState(false);
  const [password, setPassword] = useState("");
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    if (password.length < 8) {
      showToast("Mínimo 8 caracteres", "error");
      return;
    }
    setSaving(true);
    try {
      await updateUser(userId, { password });
      showToast("Contraseña actualizada");
      setPassword("");
      setOpen(false);
    } catch {
      showToast("No se pudo cambiar la contraseña", "error");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="relative inline-block">
      <button
        onClick={() => setOpen((v) => !v)}
        title="Cambiar contraseña"
        className="rounded-md p-1.5 text-slate-400 dark:text-slate-500 transition hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-white/10 dark:hover:text-slate-300"
      >
        <KeyRound size={14} strokeWidth={2} />
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-20" onClick={() => setOpen(false)} />
          <div
            className="absolute right-0 top-full z-30 mt-1 w-60 rounded-lg p-3 text-left"
            style={{ backgroundColor: "var(--surface)", boxShadow: "var(--shadow-float)" }}
          >
            <p className="mb-1.5 text-[11px] font-medium text-slate-500 dark:text-slate-400">
              Nueva contraseña
            </p>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Mínimo 8 caracteres"
              className="input w-full text-xs"
              autoFocus
              onKeyDown={(e) => e.key === "Enter" && handleSave()}
            />
            <button
              onClick={handleSave}
              disabled={saving}
              className="btn btn-primary mt-2 w-full py-1.5 text-xs disabled:opacity-60"
            >
              {saving ? "Guardando..." : "Guardar"}
            </button>
          </div>
        </>
      )}
    </div>
  );
}
