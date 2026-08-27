import { useState } from "react";
import { linkTelegram } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import Modal from "./Modal";

function errorMessage(err: unknown, fallback: string): string {
  return (
    (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? fallback
  );
}

interface TelegramLinkModalProps {
  onClose: () => void;
}

export default function TelegramLinkModal({ onClose }: TelegramLinkModalProps) {
  const { user, setUser } = useAuth();
  const { showToast } = useToast();
  const [chatId, setChatId] = useState(user?.telegram_chat_id ?? "");
  const [submitting, setSubmitting] = useState(false);

  const isLinked = !!user?.telegram_chat_id;

  const handleSave = async () => {
    setSubmitting(true);
    try {
      const updated = await linkTelegram(chatId.trim() || null);
      setUser(updated);
      showToast(chatId.trim() ? "Telegram vinculado" : "Telegram desvinculado");
      onClose();
    } catch (err) {
      showToast(errorMessage(err, "No se pudo guardar"), "error");
    } finally {
      setSubmitting(false);
    }
  };

  const handleUnlink = async () => {
    setSubmitting(true);
    try {
      const updated = await linkTelegram(null);
      setUser(updated);
      setChatId("");
      showToast("Telegram desvinculado");
    } catch {
      showToast("No se pudo desvincular", "error");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal title="Alertas por Telegram" onClose={onClose}>
      <div className="space-y-3">
        <p className="text-xs text-slate-500 dark:text-slate-400">
          Recibe un aviso instantáneo en Telegram cuando salte una alerta crítica en una nave,
          además del email (si está activado).
        </p>

        <ol className="list-decimal space-y-1.5 rounded-lg bg-slate-50 dark:bg-white/5 p-3 pl-6 text-xs text-slate-500 dark:text-slate-400">
          <li>Busca el bot de INDU-TWIN en Telegram y pulsa "Iniciar" (o envíale cualquier mensaje).</li>
          <li>
            Busca <span className="font-mono text-slate-700 dark:text-slate-300">@userinfobot</span> en
            Telegram y envíale un mensaje: te responde con tu <em>Id</em> numérico.
          </li>
          <li>Pega ese número aquí abajo.</li>
        </ol>

        <div>
          <label className="mb-1 block text-xs font-medium text-slate-500 dark:text-slate-400">
            Tu chat_id de Telegram
          </label>
          <input
            value={chatId}
            onChange={(e) => setChatId(e.target.value)}
            placeholder="123456789"
            inputMode="numeric"
            className="input w-full"
            autoFocus
          />
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleSave}
            disabled={submitting}
            className="btn btn-primary flex-1 py-2 text-sm disabled:opacity-50"
          >
            {submitting ? "Guardando..." : "Guardar"}
          </button>
          {isLinked && (
            <button
              onClick={handleUnlink}
              disabled={submitting}
              className="btn btn-secondary py-2 text-sm disabled:opacity-50"
            >
              Desvincular
            </button>
          )}
        </div>
      </div>
    </Modal>
  );
}
