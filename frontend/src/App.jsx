import { useCallback, useEffect, useRef, useState } from "react";

import { api } from "./api";
import ActionProgressModal from "./components/ActionProgressModal";
import ConfirmDialog from "./components/ConfirmDialog";
import CreateDesktopModal from "./components/CreateDesktopModal";
import DesktopList from "./components/DesktopList";
import FleetUsageBars from "./components/FleetUsageBars";
import { IconBox, IconGear, IconPlay, IconPlus, IconSquare, IconUsers } from "./components/icons";
import InfoDrawer from "./components/InfoDrawer";
import LoginPage from "./components/LoginPage";
import LogsDrawer from "./components/LogsDrawer";
import SettingsModal from "./components/SettingsModal";
import ThemeToggle from "./components/ThemeToggle";
import UsersModal from "./components/UsersModal";
import { useFleetUsage } from "./hooks/useFleetUsage";

// Solo il tono base qui: l'hover si applica a parte, e solo se l'elemento e'
// davvero cliccabile (RUN/STOP/ORPH sono indicatori, non azioni — su mobile
// un tap su un elemento con hover: lo "accende" comunque anche se non fa
// nulla, dando l'impressione sbagliata che sia un bottone).
const TOOLBAR_TONES = {
  default: "bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-slate-100",
  primary: "bg-emerald-600 text-white",
  run: "bg-emerald-500/10 text-emerald-400",
  stop: "bg-amber-500/10 text-amber-400",
  orph: "bg-slate-500/10 text-slate-500 dark:text-slate-400",
};

const TOOLBAR_HOVER = {
  default: "hover:bg-slate-200 dark:hover:bg-slate-700",
  primary: "hover:bg-emerald-500",
};

function ToolbarItem({ icon, value, tone = "default", label, onClick }) {
  const clickable = typeof onClick === "function";
  const Tag = clickable ? "button" : "div";
  const hoverClass = clickable ? TOOLBAR_HOVER[tone] ?? "" : "";
  return (
    <Tag
      onClick={onClick}
      aria-label={label}
      title={label}
      className={`flex flex-1 items-center justify-center gap-1.5 rounded-lg px-2 py-2.5 text-sm font-medium transition-colors ${TOOLBAR_TONES[tone]} ${hoverClass}`}
    >
      {icon}
      {value != null && <span className="font-mono text-xs">{value}</span>}
    </Tag>
  );
}

export default function App() {
  const [me, setMe] = useState(undefined); // undefined = ancora da controllare, null = non loggato
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [showUsers, setShowUsers] = useState(false);
  const [job, setJob] = useState(null);
  const [logsId, setLogsId] = useState(null);
  const [infoId, setInfoId] = useState(null);
  const [confirm, setConfirm] = useState(null);

  // Chiamato sempre (mai dopo un return condizionale, vedi regole degli
  // hook): "enabled" resta false finche' non sappiamo ancora se l'utente e'
  // admin (me non ancora caricato/non loggato).
  const fleetUsage = useFleetUsage(me?.role === "admin");

  useEffect(() => {
    api
      .me()
      .then(setMe)
      .catch(() => setMe(null));
  }, []);

  // Il passaggio da login a dashboard (o viceversa) sostituisce il contenuto
  // della stessa pagina senza un vero cambio di rotta: lo scroll residuo di
  // prima altrimenti resta li'. Non basta farlo una volta sola al cambio di
  // "me": l'header cresce parecchio (badge admin, barre risorse) appena
  // arrivano i primi dati, e quella crescita puo' da sola spostare lo scroll
  // di nuovo — per questo si azzera anche al primo caricamento dei dati, ma
  // solo quella prima volta (mai sui refresh successivi, altrimenti si
  // strapperebbe la pagina in cima ad ogni poll mentre si sta guardando
  // qualcos'altro piu' in basso).
  const scrolledAfterLoadRef = useRef(false);

  useEffect(() => {
    scrolledAfterLoadRef.current = false;
    window.scrollTo(0, 0);
  }, [me]);

  useEffect(() => {
    if (data && !scrolledAfterLoadRef.current) {
      scrolledAfterLoadRef.current = true;
      window.scrollTo(0, 0);
    }
  }, [data]);

  const refresh = useCallback(() => {
    api
      .listDesktops()
      .then((result) => {
        setData(result);
        setError("");
      })
      .catch((e) => {
        if (e.status === 401) {
          setMe(null);
          return;
        }
        setError(e.message);
      });
  }, []);

  useEffect(() => {
    if (!me) return undefined;
    refresh();
    const interval = setInterval(refresh, 5000);
    return () => clearInterval(interval);
  }, [me, refresh]);

  function runJob(title, promise) {
    promise.then((r) => setJob({ title, id: r.job_id })).catch((e) => setError(e.message));
  }

  function handleJobDone() {
    setJob(null);
    refresh();
  }

  function handleStart({ id, name }) {
    runJob(`Avvio ${name}`, api.startDesktop(id));
  }

  function handleStop({ id, name }) {
    setConfirm({
      title: `Ferma ${name}`,
      message: "Il desktop verra' fermato.",
      onConfirm: () => runJob(`Arresto ${name}`, api.stopDesktop(id)),
    });
  }

  function handleRestart({ id, name }) {
    setConfirm({
      title: `Riavvia ${name}`,
      message: "Il desktop verra' riavviato.",
      onConfirm: () => runJob(`Riavvio ${name}`, api.restartDesktop(id)),
    });
  }

  function handleDelete({ id, name, has_config: hasConfig, status }) {
    if (status === "ORPHAN") {
      // Nessun container da rimuovere: l'unica cosa che puo' ancora esistere
      // e' la configurazione rimasta su disco. Chiedere di nuovo "eliminare
      // il desktop o no" qui non avrebbe senso (non c'e' piu' nessun
      // container) e lasciare la scelta come checkbox smarcata di default
      // produce un conferma che in pratica non fa nulla, da capo ogni volta:
      // si va dritti a chiedere se eliminare i dati residui.
      setConfirm({
        title: `Elimina dati ${name}`,
        message: "Il desktop e' orfano (nessun processo attivo).\nVerra' eliminata definitivamente la configurazione rimasta.",
        danger: true,
        onConfirm: () => runJob(`Eliminazione dati ${name}`, api.deleteDesktop(id, true)),
      });
      return;
    }

    setConfirm({
      title: `Elimina ${name}`,
      message: "Il desktop verra' eliminato.",
      danger: true,
      askRemoveConfig: hasConfig,
      onConfirm: (removeConfig) => runJob(`Eliminazione ${name}`, api.deleteDesktop(id, removeConfig)),
    });
  }

  function handleCreate(payload) {
    setShowCreate(false);
    runJob("Creazione nuovo desktop", api.createDesktop(payload));
  }

  function handleLogout() {
    api.logout().finally(() => {
      setMe(null);
      setData(null);
    });
  }

  if (me === undefined) {
    return <div className="min-h-screen bg-slate-50 dark:bg-slate-950" />;
  }

  if (me === null) {
    return <LoginPage onLogin={setMe} />;
  }

  const isAdmin = me.role === "admin";

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100">
      <header className="border-b border-slate-200 dark:border-slate-800 bg-white/70 dark:bg-slate-900/60">
        <div className="mx-auto flex max-w-6xl flex-col gap-3 px-4 py-4">
          <div className="flex items-center justify-between">
            <h1 className="text-xl font-semibold">DeskHub</h1>
            <div className="flex items-center gap-2">
              <span className="text-sm text-slate-500 dark:text-slate-400">{me.username}</span>
              <ThemeToggle />
              <button
                onClick={handleLogout}
                className="rounded-lg bg-slate-100 dark:bg-slate-800 px-3 py-2 text-sm hover:bg-slate-200 dark:hover:bg-slate-700"
              >
                Esci
              </button>
            </div>
          </div>

          {isAdmin && (
            <div className="flex w-full gap-2">
              <ToolbarItem icon={<IconUsers className="h-5 w-5" />} label="Utenti" onClick={() => setShowUsers(true)} />
              <ToolbarItem icon={<IconGear className="h-5 w-5" />} label="Impostazioni" onClick={() => setShowSettings(true)} />
              <ToolbarItem
                icon={<IconPlus className="h-5 w-5" />}
                label="Nuovo desktop"
                tone="primary"
                onClick={() => setShowCreate(true)}
              />
              {data && (
                <>
                  <ToolbarItem icon={<IconPlay className="h-5 w-5" />} value={data.running} tone="run" label={`${data.running} in esecuzione`} />
                  <ToolbarItem icon={<IconSquare className="h-5 w-5" />} value={data.stopped} tone="stop" label={`${data.stopped} fermi`} />
                  <ToolbarItem icon={<IconBox className="h-5 w-5" />} value={data.orphan} tone="orph" label={`${data.orphan} orfani`} />
                </>
              )}
            </div>
          )}

          {isAdmin && <FleetUsageBars usage={fleetUsage} />}
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-6">
        {error && (
          <div className="mb-4 rounded-lg border border-red-900 bg-red-950/60 px-4 py-3 text-sm text-red-300">
            {error}
          </div>
        )}

        {data ? (
          <DesktopList
            desktops={data.desktops}
            isAdmin={isAdmin}
            fleetUsage={fleetUsage}
            onStart={handleStart}
            onStop={handleStop}
            onRestart={handleRestart}
            onDelete={handleDelete}
            onLogs={setLogsId}
            onInfo={setInfoId}
          />
        ) : (
          !error && <p className="py-16 text-center text-slate-500 dark:text-slate-400">Caricamento...</p>
        )}
      </main>

      {showCreate && <CreateDesktopModal onClose={() => setShowCreate(false)} onSubmit={handleCreate} />}

      {showSettings && <SettingsModal onClose={() => setShowSettings(false)} />}

      {showUsers && <UsersModal currentUsername={me.username} onClose={() => setShowUsers(false)} />}

      {job && <ActionProgressModal title={job.title} jobId={job.id} onDone={handleJobDone} />}

      {logsId && (
        <LogsDrawer
          id={logsId}
          name={data?.desktops.find((d) => d.id === logsId)?.name}
          status={data?.desktops.find((d) => d.id === logsId)?.status}
          onClose={() => setLogsId(null)}
        />
      )}

      {infoId && <InfoDrawer id={infoId} onClose={() => setInfoId(null)} />}

      {confirm && (
        <ConfirmDialog
          {...confirm}
          onCancel={() => setConfirm(null)}
          onConfirm={(removeConfig) => {
            confirm.onConfirm(removeConfig);
            setConfirm(null);
          }}
        />
      )}
    </div>
  );
}
