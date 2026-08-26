import { useEffect, useRef, useState } from "react";

import { wsUrl } from "../api";
import { useBodyScrollLock } from "../hooks/useBodyScrollLock";

const RECONNECT_DELAY_MS = 2000;

export default function LogsDrawer({ id, name, status, onClose }) {
  const [text, setText] = useState("");
  const logRef = useRef(null);

  useBodyScrollLock();

  useEffect(() => {
    setText("");
    let socket;
    let reconnectTimer;
    let unmounted = false;

    const connect = () => {
      socket = new WebSocket(wsUrl(`ws/desktops/${id}/logs`));
      socket.onmessage = (event) => setText((prev) => prev + event.data);
      socket.onclose = (event) => {
        // Codice 1000 = chiusura pulita: il backend ha gia' mandato tutto
        // quello che c'era (desktop fermo, niente altro da seguire).
        // Riconnettersi comunque duplicherebbe lo stesso storico ogni
        // RECONNECT_DELAY_MS all'infinito. Ci si riconnette da soli solo se
        // la chiusura e' anomala (rete, backend riavviato): quando invece e'
        // lo stato del desktop a cambiare (es. viene riavviato mentre il
        // pannello e' aperto), la dipendenza da `status` qui sotto rimonta
        // l'effetto e apre una connessione nuova.
        if (!unmounted && event.code !== 1000) {
          reconnectTimer = setTimeout(connect, RECONNECT_DELAY_MS);
        }
      };
    };

    connect();

    return () => {
      unmounted = true;
      clearTimeout(reconnectTimer);
      socket?.close();
    };
  }, [id, status]);

  useEffect(() => {
    logRef.current?.scrollTo(0, logRef.current.scrollHeight);
  }, [text]);

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/60 p-4 sm:items-center">
      <div className="flex h-[70vh] w-full max-w-3xl flex-col rounded-xl border border-slate-800 bg-slate-900 shadow-xl">
        <div className="flex items-center justify-between border-b border-slate-800 p-4">
          <h2 className="text-lg font-semibold">Log {name || id}</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-200" aria-label="Chiudi">
            ×
          </button>
        </div>
        <pre ref={logRef} className="flex-1 overflow-y-auto whitespace-pre-wrap p-4 font-mono text-xs text-slate-300">
          {text || "In attesa di log..."}
        </pre>
      </div>
    </div>
  );
}
