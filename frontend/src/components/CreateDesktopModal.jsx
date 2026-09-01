import { useEffect, useState } from "react";

import { api } from "../api";
import Modal from "./Modal";

function Field({ label, children }) {
  return (
    <div>
      <label className="mb-1 block text-sm text-slate-600 dark:text-slate-300">{label}</label>
      {children}
    </div>
  );
}

const inputClass =
  "w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-100 dark:bg-slate-800 px-3 py-2 text-sm outline-none focus:border-emerald-500";

export default function CreateDesktopModal({ onClose, onSubmit }) {
  const [orphans, setOrphans] = useState([]);
  const [reuseId, setReuseId] = useState("");
  const [name, setName] = useState("");
  const [users, setUsers] = useState([]);
  const [owner, setOwner] = useState("");
  const [defaults, setDefaults] = useState(null);
  const [maxRamMb, setMaxRamMb] = useState("");
  const [maxCpus, setMaxCpus] = useState("");
  const [idleTimeoutMinutes, setIdleTimeoutMinutes] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .orphanIds()
      .then(setOrphans)
      .catch(() => {});
    api
      .listUsers()
      .then((list) => {
        setUsers(list);
        if (list.length > 0) setOwner((current) => current || list[0].username);
      })
      .catch(() => {});
    api
      .getSettings()
      .then(setDefaults)
      .catch(() => {});
  }, []);

  const selectedOrphan = orphans.find((o) => o.id === reuseId);
  // Riusando una cartella di configurazione esistente il nome e' quello gia'
  // associato a quel desktop e non si puo' cambiare, altrimenti si perde il
  // legame tra l'identita' mostrata in dashboard e i dati che la cartella
  // porta con se'. Se per caso quella cartella non ha (ancora) un nome
  // tracciato, si ricade sull'input libero come per un desktop nuovo.
  const nameLocked = Boolean(selectedOrphan?.name);

  useEffect(() => {
    if (nameLocked) setName(selectedOrphan.name);
  }, [nameLocked, selectedOrphan?.name]);

  function handleSubmit(event) {
    event.preventDefault();

    if (!name.trim()) {
      setError("Assegna un nome al desktop.");
      return;
    }
    if (!owner) {
      setError("Seleziona a chi assegnare il desktop.");
      return;
    }

    onSubmit({
      name: name.trim(),
      owner,
      reuse_id: reuseId || null,
      max_ram_mb: maxRamMb === "" ? null : Number(maxRamMb),
      max_cpus: maxCpus === "" ? null : Number(maxCpus),
      idle_timeout_minutes: idleTimeoutMinutes === "" ? null : Number(idleTimeoutMinutes),
    });
  }

  return (
    <Modal title="Nuovo desktop" onClose={onClose}>
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        {orphans.length > 0 && (
          <Field label="Riusa una configurazione esistente (opzionale)">
            <select value={reuseId} onChange={(e) => setReuseId(e.target.value)} className={inputClass}>
              <option value="">Nuovo ID automatico</option>
              {orphans.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.warning ? "⚠ " : ""}
                  {o.name ? `${o.name} — ` : ""}ID {o.id}
                </option>
              ))}
            </select>
            {selectedOrphan?.warning && (
              <p className="mt-2 text-xs text-amber-400">
                ⚠ {selectedOrphan.warning} La creazione verra' rifiutata finche' non sistemi la
                cartella a mano.
              </p>
            )}
          </Field>
        )}

        <Field label="Assegna a">
          <select value={owner} onChange={(e) => setOwner(e.target.value)} className={inputClass}>
            {users.length === 0 && <option value="">Nessun utente disponibile</option>}
            {users.map((u) => (
              <option key={u.username} value={u.username}>
                {u.username} {u.role === "admin" ? "(amministratore)" : ""}
              </option>
            ))}
          </select>
        </Field>

        <Field label="Nome desktop">
          <input
            autoFocus
            placeholder='es. "web", "ufficio"'
            value={name}
            onChange={(e) => setName(e.target.value)}
            disabled={nameLocked}
            className={`${inputClass} ${nameLocked ? "cursor-not-allowed opacity-60" : ""}`}
          />
        </Field>

        <div className="grid grid-cols-2 gap-3">
          <Field label={`RAM max MB (default ${defaults?.default_max_ram_mb ?? "..."})`}>
            <input
              type="number"
              min="1"
              placeholder="usa il default"
              value={maxRamMb}
              onChange={(e) => setMaxRamMb(e.target.value)}
              className={inputClass}
            />
          </Field>
          <Field label={`CPU max core (default ${defaults?.default_max_cpus ?? "..."})`}>
            <input
              type="number"
              min="0.5"
              step="0.5"
              placeholder="usa il default"
              value={maxCpus}
              onChange={(e) => setMaxCpus(e.target.value)}
              className={inputClass}
            />
          </Field>
        </div>

        <Field label={`Spegnimento automatico dopo N minuti (default ${defaults?.idle_timeout_minutes ?? "..."})`}>
          <input
            type="number"
            min="0"
            max="1440"
            placeholder="usa il default"
            value={idleTimeoutMinutes}
            onChange={(e) => setIdleTimeoutMinutes(e.target.value)}
            className={inputClass}
          />
        </Field>

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
            className="rounded-lg bg-emerald-600 px-4 py-2 text-sm text-white hover:bg-emerald-500"
          >
            Crea e avvia
          </button>
        </div>
      </form>
    </Modal>
  );
}
