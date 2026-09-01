// Schedula `callback` sul prossimo multiplo di `ms` dall'epoch (Date.now()),
// non da quando viene chiamata questa funzione: due poller con lo stesso
// intervallo ma avviati in istanti diversi (es. la barra "Totale" e la barra
// di una singola card, entrambe montate in momenti diversi della pagina)
// altrimenti restano sfasati per sempre tra loro, pur scattando entrambe
// ogni `ms` millisecondi. Ritorna una funzione di cleanup.
export function scheduleAligned(callback, ms) {
  let interval;
  const delay = ms - (Date.now() % ms);

  const timeout = setTimeout(() => {
    callback();
    interval = setInterval(callback, ms);
  }, delay);

  return () => {
    clearTimeout(timeout);
    clearInterval(interval);
  };
}
