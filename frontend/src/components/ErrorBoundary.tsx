import { AlertTriangle } from "lucide-react";
import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  error: Error | null;
}

/** Red de seguridad: si algo revienta en el arbol de React, esto evita una
 * pantalla en blanco y ofrece recargar en vez de dejar la app inutilizable. */
export default class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("Error no controlado en la interfaz:", error, info.componentStack);
  }

  render() {
    if (this.state.error) {
      return (
        <div
          className="flex min-h-screen items-center justify-center p-8"
          style={{ backgroundColor: "var(--canvas)" }}
        >
          <div className="card max-w-sm p-6 text-center">
            <div className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-full bg-red-50 text-red-500 dark:bg-red-500/10">
              <AlertTriangle size={20} strokeWidth={2} />
            </div>
            <h1 className="font-display mb-1 text-base font-semibold text-slate-900 dark:text-slate-50">
              Algo ha ido mal
            </h1>
            <p className="mb-4 text-sm text-slate-500 dark:text-slate-400">
              Ha ocurrido un error inesperado en la interfaz. Recargar la página suele arreglarlo.
            </p>
            <button
              onClick={() => window.location.reload()}
              className="btn btn-primary w-full py-2 text-sm"
            >
              Recargar
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
