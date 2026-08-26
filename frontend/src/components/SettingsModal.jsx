import { useEffect, useState } from "react";

import { api } from "../api";
import Modal from "./Modal";

const inputClass =
  "w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm outline-none focus:border-emerald-500";

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
        <p className="text-sm text-slate-400">Caricamento...</p>
      ) : (
        <form onSubmit={handleSave} className="flex flex-col gap-4">
          <div>
            <label className="mb-1 block text-sm text-slate-300">
              Spegnimento automatico dopo N minuti di esecuzione
            </label>
            <input
              type="number"
              min="0"
              max="1440"
              value={minutes}
              onChange={(e) => setMinutes(e.target.value)}
              className={inputClass}
            />
            <p className="mt-2 text-xs text-slate-500">
              0 = disabilitato. Si applica a tutti i desktop, conta dal momento dell'avvio
              (non rileva l'inattivita' reale: nessun segnale disponibile lato desktop).
            </p>
          </div>

          <p className="text-xs text-slate-500">
            Usati per i nuovi desktop quando non si sceglie un valore diverso alla creazione; si
            possono cambiare anche dopo, per singolo desktop, da "Dettagli". Nessuna risorsa
            illimitata: ogni desktop ha sempre un tetto, sia RAM che CPU.
          </p>

          <div>
            <label className="mb-1 block text-sm text-slate-300">RAM massima predefinita (MB)</label>
            <input
              type="number"
              min="1"
              value={maxRamMb}
              onChange={(e) => setMaxRamMb(e.target.value)}
              className={inputClass}
            />
          </div>

          <div>
            <label className="mb-1 block text-sm text-slate-300">CPU massime predefinite (core)</label>
            <input
              type="number"
              min="0.5"
              step="0.5"
              value={maxCpus}
              onChange={(e) => setMaxCpus(e.target.value)}
              className={inputClass}
            />
            <p className="mt-2 text-xs text-slate-500">Anche frazionario (es. 1.5).</p>
          </div>

          {error && <p className="text-sm text-red-400">{error}</p>}

          <div className="mt-2 flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg bg-slate-800 px-4 py-2 text-sm hover:bg-slate-700"
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
