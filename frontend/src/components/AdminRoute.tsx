import type { ReactNode } from "react";
import { useAuth } from "../context/AuthContext";
import StateMessage from "./StateMessage";

export default function AdminRoute({ children }: { children: ReactNode }) {
  const { user } = useAuth();

  if (user && user.role !== "admin") {
    return (
      <div className="flex h-full items-center justify-center p-8">
        <StateMessage
          variant="error"
          title="Acceso restringido"
          description="Esta sección es solo para administradores."
        />
      </div>
    );
  }

  return <>{children}</>;
}
