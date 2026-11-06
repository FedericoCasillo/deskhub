import { useBodyScrollLock } from "../hooks/useBodyScrollLock";

export default function Modal({ title, children, onClose }) {
  useBodyScrollLock();

  return (
    // Dall'alto e scorrevole: una finestra piu' alta dello schermo (Dettagli,
    // Impostazioni su telefono) si legge tutta scorrendo, invece di restare
    // tagliata a meta'.
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/60 p-4 sm:py-10">
      <div className="w-full max-w-md rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 shadow-xl">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold">{title}</h2>
          <button
            onClick={onClose}
            className="text-slate-500 dark:text-slate-400 transition-colors hover:text-slate-700 dark:hover:text-slate-200"
            aria-label="Chiudi"
          >
            ×
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
