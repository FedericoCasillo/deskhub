import { useEffect, useRef, useState } from "react";

import { wsUrl } from "../api";
import Modal from "./Modal";

const RECONNECT_DELAY_MS = 1500;
const MAX_RECONNECT_ATTEMPTS = 5;

export default function ActionProgressModal({ title, jobId, onDone }) {
  const [lines, setLines] = useState([]);
  const [finalStatus, setFinalStatus] = useState(null);
  const [finalMessage, setFinalMessage] = useState("");
  const logRef = useRef(null);

  useEffect(() => {
    let socket;
    let reconnectTimer;
    let unmounted = false;
    let gotFinal = false;
    let attempts = 0;

    const connect = () => {
      socket = new WebSocket(wsUrl(`ws/jobs/${jobId}`));

      socket.onmessage = (event) => {
        const message = JSON.parse(event.data);
        if (message.status === "progress") {
          setLines((prev) => [...prev, message.message]);
        } else {
          gotFinal = true;
          setFinalStatus(message.status);
          setFinalMessage(message.message);
        }
      };

      socket.onclose = () => {
        if (unmounted || gotFinal) return;
        // Connessione persa prima dell'esito: il popup non e' chiudibile
        // finche' non arriva uno stato finale (per non perdere di vista
        // un'operazione ancora in corso), quindi senza riprovare l'utente
        // restava bloccato per sempre su "In corso...". Il job continua a
        // girare lato backend a prescindere dalla connessione, quindi ci si
        // riconnette e si riprende da dove si era rimasti; solo se anche i
        // tentativi falliscono si smette di bloccare l'interfaccia.
        attempts += 1;
        if (attempts > MAX_RECONNECT_ATTEMPTS) {
          gotFinal = true;
          setFinalStatus("error");
          setFinalMessage(
            "Connessione con il server persa: impossibile seguire l'esito dell'operazione. Controlla lo stato del desktop dalla lista."
          );
          return;
        }
        reconnectTimer = setTimeout(connect, RECONNECT_DELAY_MS);
      };
    };

    connect();

    return () => {
      unmounted = true;
      clearTimeout(reconnectTimer);
      socket?.close();
    };
  }, [jobId]);

  useEffect(() => {
    logRef.current?.scrollTo(0, logRef.current.scrollHeight);
  }, [lines]);

  return (
    <Modal title={title} onClose={finalStatus ? onDone : () => {}}>
      <div
        ref={logRef}
        className="h-40 space-y-1 overflow-y-auto rounded-lg border border-slate-800 bg-slate-950 p-3 font-mono text-xs text-slate-300"
      >
        {lines.map((line, index) => (
          <div key={index}>{line}</div>
        ))}
        {!finalStatus && <div className="animate-pulse text-slate-500">In corso...</div>}
      </div>

      {finalStatus && (
        <div
          className={`mt-3 whitespace-pre-wrap rounded-lg p-3 text-sm ${
            finalStatus === "success" ? "bg-emerald-500/10 text-emerald-300" : "bg-red-500/10 text-red-300"
          }`}
        >
          {finalMessage}
        </div>
      )}

      <div className="mt-4 flex justify-end">
        <button
          onClick={onDone}
          disabled={!finalStatus}
          className="rounded-lg bg-slate-800 px-4 py-2 text-sm hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Chiudi
        </button>
      </div>
    </Modal>
  );
}
