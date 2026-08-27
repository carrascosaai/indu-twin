import { useQueryClient } from "@tanstack/react-query";
import { Plus, Target, Trash2, TrendingDown } from "lucide-react";
import { useState } from "react";
import { deleteGoal } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import { useGoals } from "../hooks/useApi";
import type { Building } from "../types";
import NewGoalModal from "./NewGoalModal";

function daysLabel(days: number): string {
  if (days <= 0) return "Vence hoy";
  if (days === 1) return "Vence mañana";
  return `${days} días restantes`;
}

interface GoalsPanelProps {
  polygonId: number;
  buildings: Building[];
}

export default function GoalsPanel({ polygonId, buildings }: GoalsPanelProps) {
  const { user } = useAuth();
  const { showToast } = useToast();
  const queryClient = useQueryClient();
  const [showNewGoal, setShowNewGoal] = useState(false);
  const { data: goals, isLoading } = useGoals(polygonId);

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["goals", polygonId] });

  const handleDelete = async (goalId: number, title: string) => {
    if (!window.confirm(`¿Eliminar el objetivo "${title}"?`)) return;
    try {
      await deleteGoal(goalId);
      invalidate();
      showToast("Objetivo eliminado");
    } catch {
      showToast("No se pudo eliminar el objetivo", "error");
    }
  };

  const buildingName = (id: number | null) =>
    id === null ? "Todo el polígono" : buildings.find((b) => b.id === id)?.name ?? "Nave eliminada";

  return (
    <div className="card p-5">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="flex items-center gap-1.5 text-sm font-semibold text-slate-800 dark:text-slate-200">
          <Target size={15} strokeWidth={2} />
          Objetivos de consumo
        </h2>
        {user?.role === "admin" && (
          <button onClick={() => setShowNewGoal(true)} className="btn btn-secondary px-2.5 py-1 text-xs">
            <Plus size={12} strokeWidth={2} />
            Nuevo objetivo
          </button>
        )}
      </div>

      {showNewGoal && (
        <NewGoalModal
          polygonId={polygonId}
          buildings={buildings}
          onClose={() => setShowNewGoal(false)}
          onCreated={invalidate}
        />
      )}

      {isLoading ? (
        <div className="animate-shimmer h-20 rounded-lg" />
      ) : !goals || goals.length === 0 ? (
        <div className="flex flex-col items-center justify-center gap-1.5 rounded-lg border border-dashed border-slate-200 dark:border-white/10 py-8 text-center text-sm text-slate-400 dark:text-slate-500">
          <TrendingDown size={20} strokeWidth={1.5} />
          <p>Sin objetivos activos</p>
          {user?.role === "admin" && (
            <p className="text-xs">Crea uno para fijar una meta de reducción de consumo.</p>
          )}
        </div>
      ) : (
        <div className="space-y-4">
          {goals.map((goal) => (
            <div key={goal.id} className="rounded-lg border border-slate-100 dark:border-white/10 p-3.5">
              <div className="mb-1.5 flex items-start justify-between gap-2">
                <div>
                  <p className="text-sm font-medium text-slate-800 dark:text-slate-200">{goal.title}</p>
                  <p className="text-xs text-slate-400 dark:text-slate-500">
                    {buildingName(goal.building_id)} · −{goal.target_reduction_pct}% vs. línea base ·{" "}
                    {daysLabel(goal.days_remaining)}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <span
                    className="rounded-full px-2 py-0.5 text-[11px] font-medium"
                    style={
                      goal.is_on_track
                        ? { backgroundColor: "color-mix(in srgb, var(--color-normal) 16%, transparent)", color: "var(--color-normal)" }
                        : { backgroundColor: "color-mix(in srgb, var(--color-warning) 18%, transparent)", color: "var(--color-warning)" }
                    }
                  >
                    {goal.is_on_track ? "En objetivo" : "Por encima del objetivo"}
                  </span>
                  {user?.role === "admin" && (
                    <button
                      onClick={() => handleDelete(goal.id, goal.title)}
                      aria-label="Eliminar objetivo"
                      className="btn btn-ghost rounded-md p-1"
                    >
                      <Trash2 size={13} strokeWidth={2} />
                    </button>
                  )}
                </div>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-slate-100 dark:bg-white/10">
                <div
                  className="h-2 rounded-full transition-all"
                  style={{
                    width: `${Math.max(3, goal.progress_pct)}%`,
                    backgroundColor: goal.is_on_track ? "var(--color-normal)" : "var(--color-warning)",
                  }}
                />
              </div>
              <div className="mt-1 flex items-center justify-between text-xs text-slate-400 dark:text-slate-500">
                <span>
                  {goal.current_kwh.toFixed(0)} kWh consumidos de un presupuesto de{" "}
                  {goal.target_kwh.toFixed(0)} kWh hasta hoy
                </span>
                <span className="font-medium tabular-nums text-slate-600 dark:text-slate-300">
                  {goal.progress_pct.toFixed(0)}%
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
