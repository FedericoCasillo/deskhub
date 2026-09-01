import DesktopCard from "./DesktopCard";

export default function DesktopList({ desktops, isAdmin, fleetUsage, onStart, onStop, onRestart, onDelete, onLogs, onInfo }) {
  if (desktops.length === 0) {
    return <p className="py-16 text-center text-slate-500 dark:text-slate-400">Nessuna risorsa disponibile.</p>;
  }

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
      {desktops.map((desktop) => (
        <DesktopCard
          key={desktop.id}
          desktop={desktop}
          isAdmin={isAdmin}
          sharedUsage={fleetUsage?.per_desktop?.[desktop.id]}
          onStart={() => onStart(desktop)}
          onStop={() => onStop(desktop)}
          onRestart={() => onRestart(desktop)}
          onDelete={() => onDelete(desktop)}
          onLogs={() => onLogs(desktop.id)}
          onInfo={() => onInfo(desktop.id)}
        />
      ))}
    </div>
  );
}
