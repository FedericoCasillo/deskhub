import { useEffect, useState } from "react";

import { api } from "../api";
import { scheduleAligned } from "../pollAlign";

// Come la cache del manager: una miniatura nuova al massimo ogni 10 secondi.
const THUMBNAIL_POLL_MS = 10000;

// Miniatura dello schermo nella card. Il riquadro ha sempre la stessa forma
// (le card della griglia restano allineate); dentro, l'immagine sta intera e
// centrata qualunque sia la forma dello schermo del desktop, che cambia con
// il dispositivo da cui e' aperto (orizzontale da PC, verticale da telefono).
// La nuova immagine sostituisce la vecchia solo quando e' gia' scaricata:
// niente lampeggi. In pausa quando la scheda del browser non e' visibile.
export default function DesktopThumbnail({ id, status, available, isAdmin, onOpen, opening }) {
  const [src, setSrc] = useState(null);
  const [failed, setFailed] = useState(false);
  const active = status === "RUNNING" && available;

  useEffect(() => {
    setSrc(null);
    setFailed(false);
    if (!active) return undefined;

    let cancelled = false;
    function load() {
      if (document.hidden) return;
      const url = api.thumbnailUrl(id);
      const img = new Image();
      img.onload = () => {
        if (!cancelled) {
          setSrc(url);
          setFailed(false);
        }
      };
      img.onerror = () => {
        if (!cancelled) setFailed(true);
      };
      img.src = url;
    }

    load();
    const cancelSchedule = scheduleAligned(load, THUMBNAIL_POLL_MS);
    document.addEventListener("visibilitychange", load);
    return () => {
      cancelled = true;
      cancelSchedule();
      document.removeEventListener("visibilitychange", load);
    };
  }, [id, active]);

  let message = null;
  if (status === "STOPPED") message = "Spento";
  else if (status === "ORPHAN") message = "Senza container";
  else if (!available) message = isAdmin ? "Anteprima non disponibile: ricrea il desktop da Dettagli" : "Anteprima non disponibile";
  else if (!src) message = failed ? "Anteprima in arrivo..." : "Caricamento anteprima...";

  const box = "relative flex aspect-[16/10] w-full items-center justify-center overflow-hidden rounded-lg bg-slate-200 dark:bg-slate-950";

  if (message) {
    return (
      <div className={box}>
        <span className="px-4 text-center text-xs text-slate-500 dark:text-slate-400">{message}</span>
      </div>
    );
  }

  return (
    <button
      type="button"
      onClick={onOpen}
      disabled={opening}
      title="Apri il desktop"
      className={`${box} group cursor-pointer ring-emerald-500 transition hover:ring-2 disabled:cursor-wait`}
    >
      <img src={src} alt="Anteprima dello schermo" className="h-full w-full object-contain" draggable="false" />
    </button>
  );
}
