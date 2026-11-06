/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {},
  },
  plugins: [],
  // hover: solo dove c'e' un puntatore vero (mouse, touchpad). Su telefono e
  // tablet il browser lascia "sotto il dito" l'ultimo elemento toccato: il
  // play, toccato per aprire un desktop, restava del verde dell'hover al
  // ritorno sulla scheda del manager finche' non si toccava altrove.
  future: {
    hoverOnlyWhenSupported: true,
  },
};
