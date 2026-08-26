import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, ShieldCheck, Trash2, Users as UsersIcon, X } from "lucide-react";
import { useState } from "react";
import { createUser, deleteUser, fetchAllBuildings, fetchUsers, updateUser } from "../api/client";
import StateMessage from "../components/StateMessage";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import type { UserRole } from "../types";

const ROLE_LABELS: Record<UserRole, string> = {
  viewer: "Operario",
  admin: "Administrador",
  tenant: "Empresa (nave)",
};

export default function UsersPage() {
  const { user: currentUser } = useAuth();
  const { showToast } = useToast();
  const queryClient = useQueryClient();
  const { data: users, isLoading, isError, refetch } = useQuery({
    queryKey: ["users"],
    queryFn: fetchUsers,
  });
  const { data: buildings } = useQuery({
    queryKey: ["all-buildings"],
    queryFn: fetchAllBuildings,
  });

  const [showForm, setShowForm] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [role, setRole] = useState<UserRole>("viewer");
  const [buildingId, setBuildingId] = useState<number | "">("");
  const [isCreating, setIsCreating] = useState(false);
  // Fila que se está convirtiendo a "empresa": esperando que se elija una nave.
  const [pendingTenantRow, setPendingTenantRow] = useState<number | null>(null);

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["users"] });

  const handleCreate = async () => {
    if (!email.trim() || !password.trim() || !fullName.trim()) return;
    if (role === "tenant" && !buildingId) {
      showToast("Elige la nave de esta empresa", "error");
      return;
    }
    setIsCreating(true);
    try {
      await createUser({
        email,
        password,
        full_name: fullName,
        role,
        building_id: role === "tenant" ? (buildingId as number) : null,
      });
      setEmail("");
      setPassword("");
      setFullName("");
      setRole("viewer");
      setBuildingId("");
      setShowForm(false);
      invalidate();
      showToast("Usuario creado");
    } catch (err) {
      const response = (err as { response?: { status?: number; data?: { detail?: string } } })
        ?.response;
      const message =
        response?.status === 409
          ? "Ya existe un usuario con ese email"
          : (response?.data?.detail ?? "No se pudo crear el usuario");
      showToast(message, "error");
    } finally {
      setIsCreating(false);
    }
  };

  const handleRoleChange = (userId: number, newRole: UserRole) => {
    if (newRole === "tenant") {
      // No se guarda todavia: primero hay que elegir la nave.
      setPendingTenantRow(userId);
      return;
    }
    setPendingTenantRow(null);
    updateUser(userId, { role: newRole })
      .then(() => {
        invalidate();
        showToast("Rol actualizado");
      })
      .catch(() => showToast("No se pudo cambiar el rol", "error"));
  };

  const handleAssignBuilding = async (userId: number, newBuildingId: number) => {
    try {
      await updateUser(userId, { role: "tenant", building_id: newBuildingId });
      setPendingTenantRow(null);
      invalidate();
      showToast("Nave asignada");
    } catch {
      showToast("No se pudo asignar la nave", "error");
    }
  };

  const handleDelete = async (userId: number, name: string) => {
    if (!window.confirm(`¿Eliminar a ${name}? Esta acción no se puede deshacer.`)) return;
    try {
      await deleteUser(userId);
      invalidate();
      showToast("Usuario eliminado");
    } catch {
      showToast("No se pudo eliminar el usuario", "error");
    }
  };

  return (
    <div className="flex flex-1 flex-col overflow-y-auto">
      <header className="app-header px-4 py-4 sm:px-8 sm:py-5">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="flex items-center gap-2 text-lg font-semibold text-slate-900 dark:text-slate-50">
              <UsersIcon size={18} strokeWidth={2} className="text-slate-400 dark:text-slate-500" />
              Usuarios
            </h1>
            <p className="text-sm text-slate-500 dark:text-slate-400">Gestiona quién puede acceder a INDU-TWIN.</p>
          </div>
          <button
            onClick={() => setShowForm((v) => !v)}
            className="btn btn-primary self-start px-3 py-1.5 text-xs sm:self-auto"
          >
            {showForm ? <X size={13} strokeWidth={2} /> : <Plus size={13} strokeWidth={2} />}
            {showForm ? "Cancelar" : "Nuevo usuario"}
          </button>
        </div>
      </header>

      <main className="flex-1 space-y-6 p-4 sm:p-8">
        {showForm && (
          <div className="card p-5">
            <h2 className="mb-3 text-sm font-semibold text-slate-800 dark:text-slate-200">Crear usuario</h2>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <input
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="Nombre completo"
                className="input w-full"
              />
              <input
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                type="email"
                placeholder="Email"
                className="input w-full"
              />
              <input
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                type="password"
                placeholder="Contraseña"
                className="input w-full"
              />
              <select
                value={role}
                onChange={(e) => {
                  setRole(e.target.value as UserRole);
                  setBuildingId("");
                }}
                className="input w-full"
              >
                <option value="viewer">Operario (viewer)</option>
                <option value="admin">Administrador</option>
                <option value="tenant">Empresa (solo ve su nave)</option>
              </select>
              {role === "tenant" && (
                <select
                  value={buildingId}
                  onChange={(e) => setBuildingId(e.target.value ? Number(e.target.value) : "")}
                  className="input w-full sm:col-span-2"
                >
                  <option value="">Selecciona la nave de esta empresa...</option>
                  {(buildings ?? []).map((b) => (
                    <option key={b.id} value={b.id}>
                      {b.polygon_name} · {b.code} - {b.name}
                    </option>
                  ))}
                </select>
              )}
            </div>
            <button
              onClick={handleCreate}
              disabled={isCreating}
              className="btn btn-primary mt-3 px-3 py-1.5 text-xs disabled:opacity-60"
            >
              {isCreating ? "Creando..." : "Crear usuario"}
            </button>
          </div>
        )}

        <div className="card">
          {isError ? (
            <div className="p-5">
              <StateMessage
                variant="error"
                title="No se pudieron cargar los usuarios"
                action={{ label: "Reintentar", onClick: () => refetch() }}
              />
            </div>
          ) : isLoading ? (
            <p className="p-8 text-center text-sm text-slate-400 dark:text-slate-500">Cargando...</p>
          ) : (
            <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-100 dark:border-white/5 text-xs uppercase tracking-wide text-slate-400 dark:text-slate-500">
                  <th className="px-5 py-3 font-medium">Nombre</th>
                  <th className="px-5 py-3 font-medium">Email</th>
                  <th className="px-5 py-3 font-medium">Rol</th>
                  <th className="px-5 py-3 font-medium">Nave</th>
                  <th className="px-5 py-3 font-medium">Alta</th>
                  <th className="px-5 py-3 font-medium"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-white/5">
                {(users ?? []).map((u) => {
                  const isTenantRow = u.role === "tenant" || pendingTenantRow === u.id;
                  const currentBuilding = buildings?.find((b) => b.id === u.building_id);
                  return (
                    <tr key={u.id} className="transition hover:bg-slate-50/80 dark:hover:bg-white/5">
                      <td className="px-5 py-3 font-medium text-slate-800 dark:text-slate-200">
                        <span className="inline-flex items-center gap-2.5">
                          <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-slate-200 to-slate-300 text-[11px] font-semibold text-slate-600 dark:text-slate-300">
                            {u.full_name.charAt(0).toUpperCase()}
                          </span>
                          {u.full_name}
                          {u.id === currentUser?.id && (
                            <span className="rounded-full bg-slate-100 dark:bg-white/10 px-1.5 py-0.5 text-[10px] font-medium text-slate-500 dark:text-slate-400">
                              Tú
                            </span>
                          )}
                        </span>
                      </td>
                      <td className="px-5 py-3 text-slate-500 dark:text-slate-400">{u.email}</td>
                      <td className="px-5 py-3">
                        <select
                          value={pendingTenantRow === u.id ? "tenant" : u.role}
                          onChange={(e) => handleRoleChange(u.id, e.target.value as UserRole)}
                          disabled={u.id === currentUser?.id}
                          className="input py-1 text-xs disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          <option value="viewer">{ROLE_LABELS.viewer}</option>
                          <option value="admin">{ROLE_LABELS.admin}</option>
                          <option value="tenant">{ROLE_LABELS.tenant}</option>
                        </select>
                      </td>
                      <td className="px-5 py-3">
                        {isTenantRow ? (
                          <select
                            value={pendingTenantRow === u.id ? "" : (u.building_id ?? "")}
                            onChange={(e) => {
                              const id = Number(e.target.value);
                              if (id) handleAssignBuilding(u.id, id);
                            }}
                            className="input py-1 text-xs"
                          >
                            <option value="">
                              {pendingTenantRow === u.id ? "Elige una nave..." : "Sin nave"}
                            </option>
                            {(buildings ?? []).map((b) => (
                              <option key={b.id} value={b.id}>
                                {b.polygon_name} · {b.code}
                              </option>
                            ))}
                          </select>
                        ) : (
                          <span className="text-slate-300 dark:text-slate-600">—</span>
                        )}
                        {isTenantRow && currentBuilding && pendingTenantRow !== u.id && (
                          <p className="mt-0.5 text-[10px] text-slate-400 dark:text-slate-500">
                            {currentBuilding.name}
                          </p>
                        )}
                      </td>
                      <td className="px-5 py-3 text-slate-400 dark:text-slate-500">
                        {new Date(u.created_at).toLocaleDateString("es-ES")}
                      </td>
                      <td className="px-5 py-3 text-right">
                        <button
                          onClick={() => handleDelete(u.id, u.full_name)}
                          disabled={u.id === currentUser?.id}
                          title={u.id === currentUser?.id ? "No puedes eliminar tu propia cuenta" : "Eliminar"}
                          className="rounded-md p-1.5 text-slate-400 dark:text-slate-500 transition hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-500/10 dark:hover:text-red-400 disabled:cursor-not-allowed disabled:opacity-30 disabled:hover:bg-transparent disabled:hover:text-slate-400"
                        >
                          <Trash2 size={14} strokeWidth={2} />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            </div>
          )}
        </div>

        <div className="flex items-start gap-2 rounded-lg border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-white/5 p-3 text-xs text-slate-500 dark:text-slate-400">
          <ShieldCheck size={14} strokeWidth={2} className="mt-0.5 shrink-0" />
          Los administradores pueden crear polígonos y naves, y gestionar usuarios. Los operarios
          pueden resolver alertas y gestionar incidencias, pero no crear estructura ni usuarios. Las
          cuentas de empresa solo ven los datos de su propia nave.
        </div>
      </main>
    </div>
  );
}
