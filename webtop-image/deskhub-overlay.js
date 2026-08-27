/*
 * Overlay DeskHub per la UI Selkies del desktop remoto: piccoli ritocchi di
 * testo che Selkies non espone come opzione configurabile (niente env var
 * per queste etichette). File nostro, separato dai sorgenti di Selkies
 * (MPL-2.0), caricato accanto via nginx sub_filter — non li modifichiamo,
 * vedi deskhub-overlay.css per il dettaglio della base legale.
 *
 * Tocca solo nodi di testo esistenti (mai la struttura del DOM), quindi non
 * rischia di collidere con i re-render di React come farebbe uno spostamento
 * di elementi tra un contenitore e l'altro.
 */
(function () {
  "use strict";

  var REPLACEMENTS = [
    ["Impostazioni Audio", "Impostazioni audio"],
    ["Input (Microfono):", "Input (microfono):"],
    ["Output (Altoparlante):", "Output (altoparlante):"],
  ];

  function fixTextNode(node) {
    var text = node.nodeValue;
    for (var i = 0; i < REPLACEMENTS.length; i++) {
      if (text === REPLACEMENTS[i][0]) {
        node.nodeValue = REPLACEMENTS[i][1];
        return;
      }
    }
  }

  function walk(root) {
    var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    var node;
    while ((node = walker.nextNode())) fixTextNode(node);
  }

  function start() {
    walk(document.body);
    new MutationObserver(function (mutations) {
      for (var i = 0; i < mutations.length; i++) {
        var m = mutations[i];
        if (m.type === "characterData") {
          fixTextNode(m.target);
        } else {
          for (var j = 0; j < m.addedNodes.length; j++) {
            var n = m.addedNodes[j];
            if (n.nodeType === Node.TEXT_NODE) fixTextNode(n);
            else if (n.nodeType === Node.ELEMENT_NODE) walk(n);
          }
        }
      }
    }).observe(document.body, { childList: true, subtree: true, characterData: true });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
