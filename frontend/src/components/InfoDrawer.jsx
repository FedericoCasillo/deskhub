import { useEffect, useState } from "react";

import { api } from "../api";
import Modal from "./Modal";

function Row({ label, value }) {
  return (
    <div className="flex justify-between gap-4 border-b border-slate-800 pb-2">
      <dt className="text-slate-400">{label}</dt>
      <dd className="break-all text-right font-mono">{value}</dd>
    </div>
  );
}

const inputClass =
  "w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm outline-none focus:border-emerald-500";

export default function InfoDrawer({ id, onClose }) {
  const [info, setInfo] = useState(null);
  const [error, setError] = useState("");
  const [maxRamMb, setMaxRamMb] = useState("");
  const [maxCpus, setMaxCpus] = useState("");
  const [saving, setSaving] = useState(false);

  function refresh() {
    api
      .desktopInfo(id)
      .then((data) => {
        setInfo(data);
        setMaxRamMb(String(data.max_ram_mb));
        setMaxCpus(String(data.max_cpus));
      })
      .catch((e) => setError(e.message));
  }

  useEffect(refresh, [id]);

  function handleSaveLimits(event) {
    event.preventDefault();
    setError("");
    setSaving(true);
    api
      .setDesktopLimits(id, { max_ram_mb: Number(maxRamMb), max_cpus: Number(maxCpus) })
      .then(refresh)
      .catch((e) => setError(e.message))
      .finally(() => setSaving(false));
  }

  return (
    <Modal title={`Dettagli ${info?.name ?? id}`} onClose={onClose}>
      {error && <p className="mb-3 text-sm text-red-400">{error}</p>}
      {!info && !error && <p className="text-sm text-slate-400">Caricamento...</p>}
      {info && (
        <div className="flex flex-col gap-4">
          <dl className="space-y-2 text-sm">
            <Row label="Nome" value={info.name} />
            <Row label="Id" value={info.id} />
            <Row label="Stato" value={info.status} />
            <Row label="Proprietario" value={info.owner ?? "—"} />
            <Row label="Container" value={info.container_name} />
            <Row label="Container presente" value={info.container_present ? "Si" : "No"} />
            <Row label="Configurazione" value={info.config_dir} />
            <Row label="Configurazione presente" value={info.config_present ? "Si" : "No"} />
            <Row label="Rete proxy" value={info.network_present ? "Presente" : "Assente"} />
          </dl>

          <form onSubmit={handleSaveLimits} className="flex flex-col gap-3 border-t border-slate-800 pt-4">
            <p className="text-sm font-medium text-slate-300">Limiti risorse</p>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="mb-1 block text-xs text-slate-400">RAM max (MB)</label>
                <input
                  type="number"
                  min="1"
                  value={maxRamMb}
                  onChange={(e) => setMaxRamMb(e.target.value)}
                  className={inputClass}
                />
              </div>
              <div>
                <label className="mb-1 block text-xs text-slate-400">CPU max (core)</label>
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
            <div className="flex justify-end">
              <button
                type="submit"
                disabled={saving}
                className="rounded-lg bg-emerald-600 px-4 py-2 text-sm text-white hover:bg-emerald-500 disabled:opacity-50"
              >
                Salva limiti
              </button>
            </div>
          </form>
        </div>
      )}
    </Modal>
  );
}
