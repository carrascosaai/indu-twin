import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import StateMessage from "./StateMessage";

/** Las cuentas de empresa (tenant) no tienen vista de polígono: cualquier
 * ruta a nivel de polígono las redirige directamente a su propia nave. */
export default function TenantRedirect({ children }: { children: ReactNode }) {
  const { user } = useAuth();

  if (user?.role !== "tenant") {
    return <>{children}</>;
  }

  if (!user.building_id) {
    return (
      <div className="flex h-full items-center justify-center p-8">
        <StateMessage
          variant="error"
          title="Tu cuenta no tiene ninguna nave asignada"
          description="Contacta con el administrador del polígono para que te asigne una."
        />
      </div>
    );
  }

  return <Navigate to={`/building/${user.building_id}`} replace />;
}
