import { useEffect, useState } from "react";

import { api } from "../api";
import UsageBar from "./UsageBar";

const POLL_MS = 8000;

export default function FleetUsageBars() {
  const [usage, setUsage] = useState(null);

  useEffect(() => {
    let cancelled = false;
    function poll() {
      api
        .fleetUsage()
        .then((u) => {
          if (!cancelled) setUsage(u);
        })
        .catch(() => {
          if (!cancelled) setUsage(null);
        });
    }

    poll();
    const interval = setInterval(poll, POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  // Sempre le barre, mai un testo al posto loro: prima del primo poll (o se
  // non c'e' nessun desktop acceso) restano semplicemente ferme a zero,
  // stesso trattamento visivo di una card che aspetta i suoi dati.
  const runningCount = usage?.running_count ?? 0;
  const cpuPercent = usage?.cpu_percent ?? null;
  const maxCpus = usage?.max_cpus ?? 0;
  // cpu_percent e' la somma dei cpu_percent dei singoli desktop, ognuno
  // relativo a un core intero (Docker): con 2 desktop assegnati a 1 core
  // ciascuno e all'80% a testa il totale e' 160%. Per la barra va rapportato
  // a maxCpus (somma dei core assegnati), altrimenti supera sempre 100 non
  // appena gira piu' di un desktop e la barra sembra sempre piena/rossa
  // anche quando la flotta e' ben sotto il suo budget totale.
  const cpuBarPercent = cpuPercent != null && maxCpus > 0 ? cpuPercent / maxCpus : cpuPercent;
  const cpuTail =
    cpuPercent == null ? "—" : `${Math.round(cpuPercent)}%${maxCpus > 0 ? ` / ${maxCpus}` : ""}`;

  const memUsedMb = usage?.mem_used_mb ?? null;
  const maxRamMb = usage?.max_ram_mb ?? 0;
  const memPercent = memUsedMb != null && maxRamMb > 0 ? (memUsedMb / maxRamMb) * 100 : null;
  const memTail = memUsedMb == null ? "—" : `${Math.round(memUsedMb)}${maxRamMb > 0 ? `/${maxRamMb}` : ""}MB`;

  return (
    <div className="flex flex-col gap-2 rounded-xl border border-slate-800 bg-slate-900 px-3 py-2.5 sm:flex-row sm:items-center sm:gap-3">
      <span className="shrink-0 text-xs text-slate-500">Totale ({runningCount})</span>
      <div className="flex flex-col gap-1.5 sm:min-w-0 sm:flex-1 sm:flex-row sm:items-center sm:gap-3">
        <div className="min-w-0 sm:flex-1">
          <UsageBar label="CPU" percent={cpuBarPercent} tail={cpuTail} />
        </div>
        <div className="min-w-0 sm:flex-1">
          <UsageBar label="RAM" percent={memPercent} tail={memTail} />
        </div>
      </div>
    </div>
  );
}
