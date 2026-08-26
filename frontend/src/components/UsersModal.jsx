import { useEffect, useState } from "react";

import { api } from "../api";
import Modal from "./Modal";

const USER_RE = /^[a-z_][a-z0-9_-]*$/;
const inputClass =
  "w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm outline-none focus:border-emerald-500";

export default function UsersModal({ currentUsername, onClose }) {
  const [users, setUsers] = useState(null);
  const [error, setError] = useState("");

  const [newUsername, setNewUsername] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [newRole, setNewRole] = useState("user");

  function refresh() {
    api
      .listUsers()
      .then(setUsers)
      .catch((e) => setError(e.message));
  }

  useEffect(refresh, []);

  function handleCreate(event) {
    event.preventDefault();
    setError("");

    if (!USER_RE.test(newUsername)) {
      setError("Nome utente non valido (minuscolo, lettere/numeri/-/_).");
      return;
    }
    if (newPassword.length < 8) {
      setError("La password deve avere almeno 8 caratteri.");
      return;
    }

    api
      .createUser({ username: newUsername, password: newPassword, role: newRole })
      .then(() => {
        setNewUsername("");
        setNewPassword("");
        setNewRole("user");
        refresh();
      })
      .catch((e) => setError(e.message));
  }

  function handleResetPassword(username) {
    const password = window.prompt(`Nuova password per ${username} (minimo 8 caratteri):`);
    if (!password) return;
    if (password.length < 8) {
      setError("La password deve avere almeno 8 caratteri.");
      return;
    }
    api.setUserPassword(username, password).catch((e) => setError(e.message));
  }

  function handleDelete(username) {
    if (!window.confirm(`Eliminare l'utente ${username}?`)) return;
    api
      .deleteUser(username)
      .then(refresh)
      .catch((e) => setError(e.message));
  }

  return (
    <Modal title="Utenti" onClose={onClose}>
      <div className="flex flex-col gap-4">
        {error && <p className="text-sm text-red-400">{error}</p>}

        <div className="flex max-h-64 flex-col gap-2 overflow-y-auto">
          {users === null && <p className="text-sm text-slate-400">Caricamento...</p>}
          {users?.map((u) => (
            <div
              key={u.username}
              className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-800/50 px-3 py-2 text-sm"
            >
              <div>
                <span className="font-medium">{u.username}</span>{" "}
                <span className="text-xs text-slate-400">({u.role === "admin" ? "amministratore" : "utente"})</span>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => handleResetPassword(u.username)}
                  className="rounded-lg bg-slate-800 px-2 py-1 text-xs hover:bg-slate-700"
                >
                  Reset password
                </button>
                {u.username !== currentUsername && (
                  <button
                    onClick={() => handleDelete(u.username)}
                    className="rounded-lg bg-red-900/60 px-2 py-1 text-xs text-red-100 hover:bg-red-800"
                  >
                    Elimina
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>

        <form onSubmit={handleCreate} className="flex flex-col gap-3 border-t border-slate-800 pt-4">
          <p className="text-sm font-medium text-slate-300">Nuovo utente</p>
          <input
            placeholder="Nome utente"
            value={newUsername}
            onChange={(e) => setNewUsername(e.target.value)}
            className={inputClass}
          />
          <input
            type="password"
            placeholder="Password (minimo 8 caratteri)"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            className={inputClass}
          />
          <select value={newRole} onChange={(e) => setNewRole(e.target.value)} className={inputClass}>
            <option value="user">Utente (solo i propri desktop)</option>
            <option value="admin">Amministratore</option>
          </select>
          <button
            type="submit"
            className="rounded-lg bg-emerald-600 px-4 py-2 text-sm text-white hover:bg-emerald-500"
          >
            Crea utente
          </button>
        </form>

        <div className="flex justify-end">
          <button onClick={onClose} className="rounded-lg bg-slate-800 px-4 py-2 text-sm hover:bg-slate-700">
            Chiudi
          </button>
        </div>
      </div>
    </Modal>
  );
}
