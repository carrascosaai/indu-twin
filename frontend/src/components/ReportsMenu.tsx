import { FileSpreadsheet, FileText, FileDown } from "lucide-react";
import { useState } from "react";
import { downloadPolygonReport, type ReportFormat, type ReportPeriod } from "../api/client";
import { useToast } from "../context/ToastContext";
import TabSwitcher from "./TabSwitcher";

const PERIODS: { value: ReportPeriod; label: string }[] = [
  { value: "daily", label: "Diario" },
  { value: "weekly", label: "Semanal" },
  { value: "monthly", label: "Mensual" },
];

export default function ReportsMenu({ polygonId }: { polygonId: number }) {
  const { showToast } = useToast();
  const [open, setOpen] = useState(false);
  const [period, setPeriod] = useState<ReportPeriod>("weekly");
  const [downloading, setDownloading] = useState<ReportFormat | null>(null);

  const handleDownload = async (format: ReportFormat) => {
    setDownloading(format);
    try {
      await downloadPolygonReport(polygonId, period, format);
      showToast("Informe generado");
      setOpen(false);
    } catch {
      showToast("No se pudo generar el informe", "error");
    } finally {
      setDownloading(null);
    }
  };

  return (
    <div className="relative">
      <button onClick={() => setOpen((v) => !v)} className="btn btn-secondary px-3 py-1.5 text-xs">
        <FileDown size={13} strokeWidth={2} />
        Informes
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-20" onClick={() => setOpen(false)} />
          <div
            className="absolute right-0 top-full z-30 mt-1.5 w-64 rounded-lg p-3.5"
            style={{ backgroundColor: "var(--surface)", boxShadow: "var(--shadow-float)" }}
          >
            <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-slate-400 dark:text-slate-500">
              Periodo
            </p>
            <TabSwitcher value={period} onChange={setPeriod} options={PERIODS} />

            <p className="mb-2 mt-3.5 text-[11px] font-semibold uppercase tracking-wide text-slate-400 dark:text-slate-500">
              Formato
            </p>
            <div className="space-y-1.5">
              <button
                onClick={() => handleDownload("pdf")}
                disabled={downloading !== null}
                className="flex w-full items-center gap-2.5 rounded-lg border border-slate-200 px-3 py-2 text-left text-xs font-medium text-slate-700 transition hover:border-blue-300 hover:bg-blue-50/50 disabled:opacity-50 dark:border-white/10 dark:text-slate-300 dark:hover:border-blue-800 dark:hover:bg-blue-500/10"
              >
                <FileText size={15} strokeWidth={2} className="shrink-0 text-red-500" />
                <span className="flex-1">
                  {downloading === "pdf" ? "Generando…" : "Informe PDF"}
                </span>
              </button>
              <button
                onClick={() => handleDownload("xlsx")}
                disabled={downloading !== null}
                className="flex w-full items-center gap-2.5 rounded-lg border border-slate-200 px-3 py-2 text-left text-xs font-medium text-slate-700 transition hover:border-blue-300 hover:bg-blue-50/50 disabled:opacity-50 dark:border-white/10 dark:text-slate-300 dark:hover:border-blue-800 dark:hover:bg-blue-500/10"
              >
                <FileSpreadsheet size={15} strokeWidth={2} className="shrink-0 text-emerald-600" />
                <span className="flex-1">
                  {downloading === "xlsx" ? "Generando…" : "Hoja de cálculo (Excel)"}
                </span>
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
