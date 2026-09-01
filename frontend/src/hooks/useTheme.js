import { useEffect, useState } from "react";

const STORAGE_KEY = "deskhub-theme";

function systemPrefersDark() {
  return typeof window.matchMedia === "function" && window.matchMedia("(prefers-color-scheme: dark)").matches;
}

// Senza una scelta esplicita gia' salvata (utente che non ha mai toccato lo
// switch), si eredita il tema del sistema operativo/browser invece di un
// default fisso: coerente con lo script inline in index.html, che applica
// la stessa logica prima del primo paint.
function readInitialTheme() {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === "light" || stored === "dark") return stored;
  } catch {
    // storage non disponibile (privato/bloccato): resta sul default di sistema
  }
  return systemPrefersDark() ? "dark" : "light";
}

// Applica subito la classe "dark" su <html> e il colore della scheda del
// browser (meta "theme-color"): coerente con lo script inline in index.html
// che li mette gia' prima del primo paint di React (evita il lampo del tema
// sbagliato), qui li si tiene solo sincronizzati ai cambi successivi (switch
// manuale). Senza questo, cambiando tema dallo switch il colore della
// scheda restava quello di prima — visibile su iPad/Safari, che tinge la
// barra del browser in base a questo meta.
export function useTheme() {
  const [theme, setTheme] = useState(readInitialTheme);

  useEffect(() => {
    const isDark = theme !== "light";
    document.documentElement.classList.toggle("dark", isDark);
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute("content", isDark ? "#020617" : "#f8fafc");
  }, [theme]);

  // Il salvataggio avviene solo qui, alla scelta esplicita dell'utente (mai
  // nell'effect sopra): finche' non tocca lo switch, ogni caricamento deve
  // continuare a rileggere il tema del sistema in quel momento (vedi
  // readInitialTheme), anche se nel frattempo e' cambiato — non "congelarlo"
  // gia' al primo giro solo perche' lo stato React e' stato inizializzato.
  function toggleTheme() {
    setTheme((current) => {
      const next = current === "light" ? "dark" : "light";
      try {
        localStorage.setItem(STORAGE_KEY, next);
      } catch {
        // storage non disponibile: il tema resta comunque applicato per questa sessione
      }
      return next;
    });
  }

  return { theme, toggleTheme };
}
