export default function UsageBar({ label, percent, tail }) {
  // percent null = niente su cui misurare una percentuale (nessun limite
  // configurato): niente barra piena all'apparenza "ferma" a 0%, solo il
  // numero grezzo (che comunque si aggiorna ad ogni poll) accanto a un
  // binario vuoto, cosi' non sembra bloccata quando in realta' e' solo
  // senza tetto.
  const hasPercent = percent != null;
  const pct = hasPercent ? Math.max(0, Math.min(100, percent)) : 0;
  const tone = pct > 90 ? "bg-red-500" : pct > 70 ? "bg-amber-500" : "bg-emerald-500";
  return (
    <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
      <span className="w-8 shrink-0">{label}</span>
      <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
        {hasPercent && <div className={`h-full ${tone} transition-all`} style={{ width: `${pct}%` }} />}
      </div>
      <span className="shrink-0 text-right font-mono text-[11px]">{tail}</span>
    </div>
  );
}
