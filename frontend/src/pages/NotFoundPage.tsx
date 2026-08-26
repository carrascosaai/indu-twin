import { Compass } from "lucide-react";
import { Link } from "react-router-dom";

export default function NotFoundPage() {
  return (
    <div className="flex h-full flex-1 items-center justify-center p-8">
      <div className="text-center">
        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-slate-100 dark:bg-white/10 text-slate-400 dark:text-slate-500">
          <Compass size={22} strokeWidth={2} />
        </div>
        <p className="font-display text-2xl font-semibold text-slate-900 dark:text-slate-50">404</p>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">Esta página no existe o se ha movido.</p>
        <Link to="/" className="btn btn-primary mt-4 inline-flex px-4 py-2 text-sm">
          Volver al dashboard
        </Link>
      </div>
    </div>
  );
}
