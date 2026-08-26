import { X } from "lucide-react";
import { useEffect, type ReactNode } from "react";

interface ModalProps {
  title: string;
  onClose: () => void;
  children: ReactNode;
}

export default function Modal({ title, onClose, children }: ModalProps) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div
        className="absolute inset-0 bg-slate-900/40 backdrop-blur-[2px]"
        onClick={onClose}
      />
      <div
        className="relative w-full max-w-md rounded-2xl p-6"
        style={{ backgroundColor: "var(--surface)", boxShadow: "var(--shadow-float)" }}
      >
        <div className="mb-4 flex items-center justify-between">
          <h2 className="font-display text-base font-semibold text-slate-900 dark:text-slate-50">{title}</h2>
          <button
            onClick={onClose}
            className="btn btn-ghost rounded-md p-1"
          >
            <X size={16} strokeWidth={2} />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
