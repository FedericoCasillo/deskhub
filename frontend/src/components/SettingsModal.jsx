import { useEffect, useState } from "react";

import { api } from "../api";
import Modal from "./Modal";

const inputClass =
  "w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-100 dark:bg-slate-800 px-3 py-2 text-sm outline-none focus:border-emerald-500";

export default function SettingsModal({ onClose }) {
  const [minutes, setMinutes] = useState(0);
  const [maxRamMb, setMaxRamMb] = useState(0);
  const [maxCpus, setMaxCpus] = useState(0);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .getSettings()
      .then((s) => {
        setMinutes(s.idle_timeout_minutes);
        setMaxRamMb(s.default_max_ram_mb);
        setMaxCpus(s.default_max_cpus);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  function handleSave(event) {
    event.preventDefault();
    setSaving(true);
    setError("");
    api
      .updateSettings({
        idle_timeout_minutes: Number(minutes),
        default_max_ram_mb: Number(maxRamMb),
        default_max_cpus: Number(maxCpus),
      })
      .then(onClose)
      .catch((e) => setError(e.message))
      .finally(() => setSaving(false));
  }

  return (
    <Modal title="Impostazioni" onClose={onClose}>
      {loading ? (
        <p className="text-sm text-slate-500 dark:text-slate-400">Caricamento...</p>
      ) : (
        <form onSubmit={handleSave} className="flex flex-col gap-4">
          <p className="text-xs text-slate-600 dark:text-slate-500">
            Default per i nuovi desktop, sempre modificabili anche dopo per singolo desktop da
            "Dettagli".
          </p>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-xs text-slate-500 dark:text-slate-400">RAM max predefinita (MB)</label>
              <input
                type="number"
                min="1"
                value={maxRamMb}
                onChange={(e) => setMaxRamMb(e.target.value)}
                className={inputClass}
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-slate-500 dark:text-slate-400">CPU max predefinita (core)</label>
              <input
                type="number"
                min="0.5"
                step="0.5"
                value={maxCpus}
                onChange={(e) => setMaxCpus(e.target.value)}
                className={inputClass}
              />
            </div>
          </div>

          <div>
            <label className="mb-1 block text-xs text-slate-500 dark:text-slate-400">
              Spegnimento automatico predefinito dopo N minuti (0 = disabilitato)
            </label>
            <input
              type="number"
              min="0"
              max="1440"
              value={minutes}
              onChange={(e) => setMinutes(e.target.value)}
              className={inputClass}
            />
          </div>

          {error && <p className="text-sm text-red-400">{error}</p>}

          <div className="mt-2 flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg bg-slate-100 dark:bg-slate-800 px-4 py-2 text-sm hover:bg-slate-200 dark:hover:bg-slate-700"
            >
              Annulla
            </button>
            <button
              type="submit"
              disabled={saving}
              className="rounded-lg bg-emerald-600 px-4 py-2 text-sm text-white hover:bg-emerald-500 disabled:opacity-50"
            >
              Salva
            </button>
          </div>
        </form>
      )}
    </Modal>
  );
}
