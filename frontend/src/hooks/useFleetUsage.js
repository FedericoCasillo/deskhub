import { useEffect, useState } from "react";

import { api } from "../api";
import { scheduleAligned } from "../pollAlign";

const POLL_MS = 5000;

// Un solo poll condiviso di /desktops/usage, non uno per la barra "Totale" e
// uno per ogni card: entrambi leggerebbero lo stesso dato ma con due
// richieste indipendenti, che anche allineate sulla stessa griglia possono
// restare sfasate di qualche secondo l'una dall'altra (visto dal vivo).
// Qui invece e' sempre esattamente lo stesso oggetto per tutti.
export function useFleetUsage(enabled) {
  const [usage, setUsage] = useState(null);

  useEffect(() => {
    if (!enabled) {
      setUsage(null);
      return undefined;
    }

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
    const cancelSchedule = scheduleAligned(poll, POLL_MS);
    return () => {
      cancelled = true;
      cancelSchedule();
    };
  }, [enabled]);

  return usage;
}
