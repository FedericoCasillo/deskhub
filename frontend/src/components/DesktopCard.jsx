import { useEffect, useState } from "react";

import { api } from "../api";
import { IconInfo, IconList, IconPlay, IconRefresh, IconSquare, IconTrash } from "./icons";
import UsageBar from "./UsageBar";

const STATUS_STYLES = {
  RUNNING: "bg-emerald-500/15 text-emerald-400 ring-1 ring-emerald-500/30",
  STOPPED: "bg-amber-500/15 text-amber-400 ring-1 ring-amber-500/30",
  ORPHAN: "bg-slate-500/15 text-slate-400 ring-1 ring-slate-500/30",
};

const BUTTON_TONES = {
  default: "bg-slate-800 hover:bg-slate-700 text-slate-100",
  primary: "bg-emerald-600 hover:bg-emerald-500 text-white",
  danger: "bg-red-900/60 hover:bg-red-800 text-red-100",
};

const USAGE_POLL_MS = 8000;

// Etichetta nascosta sotto "sm": sulla card, in una sola colonna su mobile,
// lo spazio manca; da "sm" in su (anche nella griglia a piu' colonne) resta
// abbastanza per testo + icona insieme.
function ActionButton({ icon, label, onClick, tone = "default", disabled = false }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      title={label}
      className={`flex min-w-0 items-center justify-center gap-1 rounded-lg px-1.5 py-2 text-xs transition-colors disabled:opacity-50 sm:gap-1.5 sm:px-2 sm:text-sm ${BUTTON_TONES[tone]}`}
    >
      {icon}
      <span className="hidden truncate sm:inline">{label}</span>
    </button>
  );
}

function useDesktopUsage(id, status) {
  const [usage, setUsage] = useState(null);

  useEffect(() => {
    if (status !== "RUNNING") {
      setUsage(null);
      return undefined;
    }

    let cancelled = false;
    function poll() {
      api
        .desktopUsage(id)
        .then((u) => {
          if (!cancelled) setUsage(u);
        })
        .catch(() => {
          if (!cancelled) setUsage(null);
        });
    }

    poll();
    const interval = setInterval(poll, USAGE_POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [id, status]);

  return usage;
}

export default function DesktopCard({ desktop, isAdmin, onStart, onStop, onRestart, onDelete, onLogs, onInfo }) {
  const { id, name, status, owner, max_ram_mb, max_cpus } = desktop;
  const usage = useDesktopUsage(id, status);
  const [opening, setOpening] = useState(false);
  const [openError, setOpenError] = useState("");

  async function handleOpen() {
    setOpening(true);
    setOpenError("");
    // La finestra va aperta SUBITO, in modo sincrono dentro il click: se la
    // si apre dopo un await, i browser veri (non lo store del test) la
    // bloccano come popup. Ci si scrive dentro l'URL vero solo dopo aver
    // verificato che la rotta esista davvero (vedi sotto), tenendo un
    // riferimento alla finestra invece di navigarci alla cieca.
    const win = window.open("", "_blank");

    try {
      const { url } = await api.openDesktopSession(id);
      const fullUrl = `${window.location.origin}${url}`;

      // Il routing dinamico di Traefik per questa sessione e' generato dal
      // manager ma letto da Traefik a intervalli (poll HTTP provider):
      // aprire subito la pagina vera rischierebbe un 404 momentaneo se la
      // route non e' ancora stata ricaricata. Verifico che risponda prima
      // di navigarci, invece di indovinare un'attesa fissa.
      // res.ok (2xx), non solo "diverso da 404": mentre la route non e'
      // ancora caricata puo' arrivare anche un 502/503 dal backend (route
      // presente ma servizio non ancora raggiungibile) — trattarlo come
      // "pronto" navigherebbe su una pagina di errore invece di aspettare.
      // Fino a ~30s: su una macchina appena avviata (immagine appena
      // estratta, primo boot del desktop) i primi secondi possono essere
      // piu' lenti che su una macchina gia' calda.
      let ready = false;
      for (let attempt = 0; attempt < 60; attempt++) {
        try {
          const res = await fetch(fullUrl, { method: "HEAD", cache: "no-store" });
          if (res.ok) {
            ready = true;
            break;
          }
        } catch {
          // rete/TLS non ancora pronti, riprovo
        }
        await new Promise((resolve) => setTimeout(resolve, 500));
      }

      if (!ready) {
        throw new Error("Il desktop non ha risposto in tempo. Riprova tra qualche secondo.");
      }

      if (win) win.location.href = fullUrl;
    } catch (e) {
      setOpenError(e.message);
      // win.close() non e' garantito su tutti i browser (in particolare su
      // mobile puo' fallire in silenzio, lasciando una scheda bianca senza
      // nessun feedback visibile). Scrivo comunque un messaggio leggibile
      // nella scheda stessa, cosi' l'utente vede sempre qualcosa anche se
      // la chiusura non funziona.
      if (win) {
        try {
          win.document.write(
            `<p style="font-family:sans-serif;padding:2rem;color:#333">${e.message}<br><br>Puoi chiudere questa scheda e riprovare.</p>`
          );
        } catch {
          // documento gia' navigato altrove, niente da fare
        }
        win.close();
      }
    } finally {
      setOpening(false);
    }
  }

  const cpuPercent = usage?.cpu_percent ?? null;
  // cpu_percent di Docker e' relativo a un core intero (un desktop che usa
  // 2 core pieni mostra ~200%), non al limite assegnato al desktop: per la
  // barra (colore/riempimento) va rapportato a max_cpus, non usato grezzo,
  // altrimenti un limite > 1 core la fa apparire piena/rossa molto prima
  // del reale. Il testo invece mostra il valore grezzo apposta, e' quello
  // il dato utile da leggere.
  const cpuBarPercent = cpuPercent != null && max_cpus > 0 ? (cpuPercent / max_cpus) * 100 : cpuPercent;
  const cpuTail =
    cpuPercent == null ? "—" : max_cpus > 0 ? `${Math.round(cpuPercent)}% / ${max_cpus}` : `${Math.round(cpuPercent)}%`;

  const memPercent = usage?.mem_used_mb != null && max_ram_mb > 0 ? (usage.mem_used_mb / max_ram_mb) * 100 : null;
  const memTail =
    usage?.mem_used_mb == null
      ? "—"
      : `${Math.round(usage.mem_used_mb)}${max_ram_mb > 0 ? `/${max_ram_mb}` : ""}MB`;

  return (
    <div className="flex flex-col gap-3 rounded-xl border border-slate-800 bg-slate-900 p-4 shadow-sm">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">{name || id}</h3>
        <span className={`rounded-full px-2 py-1 text-xs font-medium ${STATUS_STYLES[status]}`}>
          {status}
        </span>
      </div>

      {isAdmin && owner && <p className="text-xs text-slate-500">Proprietario: {owner}</p>}

      {status === "RUNNING" && (
        <div className="flex flex-col gap-1.5">
          <UsageBar label="CPU" percent={cpuBarPercent} tail={cpuTail} />
          <UsageBar label="RAM" percent={memPercent} tail={memTail} />
        </div>
      )}

      {openError && <p className="text-xs text-red-400">{openError}</p>}

      {(status === "RUNNING" || status === "STOPPED" || isAdmin) && (
        <div className="mt-auto grid grid-cols-3 gap-2">
          {status === "RUNNING" && (
            <ActionButton
              icon={<IconPlay className="h-4 w-4 shrink-0" />}
              label={opening ? "Apertura..." : "Apri"}
              onClick={handleOpen}
              tone="primary"
              disabled={opening}
            />
          )}
          {status === "STOPPED" && (
            <ActionButton icon={<IconPlay className="h-4 w-4 shrink-0" />} label="Avvia" onClick={onStart} tone="primary" />
          )}
          {status === "RUNNING" && (
            <>
              <ActionButton icon={<IconRefresh className="h-4 w-4 shrink-0" />} label="Riavvia" onClick={onRestart} />
              <ActionButton icon={<IconSquare className="h-4 w-4 shrink-0" />} label="Ferma" onClick={onStop} />
            </>
          )}
          {isAdmin && status !== "ORPHAN" && (
            <ActionButton icon={<IconList className="h-4 w-4 shrink-0" />} label="Log" onClick={onLogs} />
          )}
          {isAdmin && <ActionButton icon={<IconInfo className="h-4 w-4 shrink-0" />} label="Dettagli" onClick={onInfo} />}
          {isAdmin && (
            <ActionButton icon={<IconTrash className="h-4 w-4 shrink-0" />} label="Elimina" onClick={onDelete} tone="danger" />
          )}
        </div>
      )}
    </div>
  );
}
