import { useState } from "react";

import Modal from "./Modal";

export default function ConfirmDialog({ title, message, danger, askRemoveConfig, onConfirm, onCancel }) {
  const [removeConfig, setRemoveConfig] = useState(false);

  return (
    <Modal title={title} onClose={onCancel}>
      <p className="whitespace-pre-wrap text-sm text-slate-600 dark:text-slate-300">{message}</p>

      {askRemoveConfig && (
        <label className="mt-4 flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
          <input
            type="checkbox"
            checked={removeConfig}
            onChange={(e) => setRemoveConfig(e.target.checked)}
            className="rounded"
          />
          Elimina anche la configurazione salvata
        </label>
      )}

      <div className="mt-5 flex justify-end gap-2">
        <button onClick={onCancel} className="rounded-lg bg-slate-100 dark:bg-slate-800 px-4 py-2 text-sm hover:bg-slate-200 dark:hover:bg-slate-700">
          Annulla
        </button>
        <button
          onClick={() => onConfirm(removeConfig)}
          className={`rounded-lg px-4 py-2 text-sm text-white ${
            danger ? "bg-red-700 hover:bg-red-600" : "bg-emerald-600 hover:bg-emerald-500"
          }`}
        >
          Conferma
        </button>
      </div>
    </Modal>
  );
}
