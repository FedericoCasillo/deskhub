import UsageBar from "./UsageBar";

// Riceve i dati gia' caricati dal genitore (App.jsx, un solo poll condiviso
// con le card dei singoli desktop, vedi useFleetUsage): niente polling
// proprio qui. Due poll indipendenti per lo stesso identico dato (totale
// flotta vs singola card) restano scollegati nel tempo — anche allineati
// sulla stessa griglia, due timer del browser possono comunque sfasarsi
// impercettibilmente e mostrare numeri diversi per finestre di piu' secondi.
// Un solo poll, un solo dato distribuito, elimina il problema alla radice.
export default function FleetUsageBars({ usage }) {
  // Sempre le barre, mai un testo al posto loro: prima del primo poll (o se
  // non c'e' nessun desktop acceso) restano semplicemente ferme a zero,
  // stesso trattamento visivo di una card che aspetta i suoi dati.
  const runningCount = usage?.running_count ?? 0;
  const cpuPercentRaw = usage?.cpu_percent ?? null;
  const maxCpus = usage?.max_cpus ?? 0;
  // cpu_percent (dal backend) e' la somma dei cpu_percent dei singoli
  // desktop, ognuno relativo a un core intero (Docker): con 2 desktop
  // assegnati a 1 core ciascuno e all'80% a testa il totale grezzo e' 160,
  // un numero senza senso se letto come percentuale. Sia barra che testo lo
  // rapportano a maxCpus (somma dei core assegnati alla flotta), come gia'
  // fa la RAM: altrimenti il testo mostrerebbe un numero (spesso > 100)
  // scollegato da quello che la barra disegna, e sommando desktop con tetti
  // diversi il risultato puo' sembrare incoerente (es. "100% / 3" quando in
  // realta' e' ~34% del budget totale).
  const cpuPercent = cpuPercentRaw != null && maxCpus > 0 ? cpuPercentRaw / maxCpus : cpuPercentRaw;
  const cpuTail = cpuPercent == null ? "—" : `${Math.round(cpuPercent)}%${maxCpus > 0 ? ` su ${maxCpus} core` : ""}`;

  const memUsedMb = usage?.mem_used_mb ?? null;
  const maxRamMb = usage?.max_ram_mb ?? 0;
  const memPercent = memUsedMb != null && maxRamMb > 0 ? (memUsedMb / maxRamMb) * 100 : null;
  const memTail = memUsedMb == null ? "—" : `${Math.round(memUsedMb)}${maxRamMb > 0 ? `/${maxRamMb}` : ""}MB`;

  return (
    <div className="flex flex-col gap-2 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 px-3 py-2.5 sm:flex-row sm:items-center sm:gap-3">
      <span className="shrink-0 text-xs text-slate-600 dark:text-slate-500">Totale ({runningCount})</span>
      <div className="flex flex-col gap-1.5 sm:min-w-0 sm:flex-1 sm:flex-row sm:items-center sm:gap-3">
        <div className="min-w-0 sm:flex-1">
          <UsageBar label="CPU" percent={cpuPercent} tail={cpuTail} />
        </div>
        <div className="min-w-0 sm:flex-1">
          <UsageBar label="RAM" percent={memPercent} tail={memTail} />
        </div>
      </div>
    </div>
  );
}
