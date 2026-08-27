# Pinnata al digest risolto il 2026-08-25 per riproducibilita': il tag
# "ubuntu-kde" su LinuxServer.io puo' cambiare contenuto nel tempo, il digest
# no. Per aggiornare volontariamente all'ultima immagine upstream, sostituisci
# con FROM lscr.io/linuxserver/webtop:ubuntu-kde (senza digest) e ricostruisci.
FROM lscr.io/linuxserver/webtop@sha256:d91fb284794d554d89b4b210ebe56a538c755dfb2054a3741ed7471363cd5369

# La UI Selkies mostra favicon/apple-touch-icon/manifest da
# /usr/share/selkies/web/icon.png, MA quella cartella viene cancellata e
# rigenerata ad ogni avvio del container da /etc/s6-overlay/s6-rc.d/
# init-nginx/run (rm -Rf .../web + cp -a da .../$DASHBOARD, poi
# "cp /usr/share/selkies/www/icon.png" sia su web/icon.png che su
# web/favicon.ico). Scrivere direttamente in .../web quindi non serve a
# nulla: si perderebbe al primo avvio. La vera sorgente persistente e'
# /usr/share/selkies/www/icon.png, quella sostituiamo qui. Stessa identica
# immagine di frontend/public/icon.png: se la cambi, aggiorna entrambe le
# copie (contesti di build separati).
COPY deskhub-icon.png /usr/share/selkies/www/icon.png

# Overlay di branding/layout DeskHub sopra la UI Selkies (vedi
# deskhub-overlay.css per il perche' e' legale farlo senza toccare i file
# di Selkies, licenziati MPL-2.0). I due file finiscono nella cartella
# sorgente che init-nginx copia in .../web ad ogni avvio (stesso motivo per
# cui l'icona va in .../www, vedi sopra: .../web viene rigenerata ogni
# volta), cosi' sopravvivono ai riavvii. Il template nginx sostituisce
# /defaults/default.conf: aggiunge solo due "sub_filter" per iniettare
# <link>/<script> verso questi due file nella risposta HTML, il resto del
# file e' identico all'originale linuxserver/webtop.
COPY deskhub-overlay.css deskhub-overlay.js /usr/share/selkies/selkies-dashboard/
COPY nginx-default.conf /defaults/default.conf

# SELKIES_UI_TITLE e' il setting ufficiale di Selkies per il titolo nella
# sidebar (h2 accanto al logo): nessun hack, solo il nome dato all'opzione.
# TITLE invece e' una variabile del base image webtop (non di Selkies):
# alimenta il manifest.json generato da init-nginx e da li' il
# document.title della scheda del browser (era "Ubuntu KDE" di default).
# SELKIES_UI_SIDEBAR_SHOW_STATS nasconde le statistiche CPU/RAM di Selkies,
# ridondanti con quelle del manager DeskHub: resta solo la sezione audio.
# SELKIES_UI_SIDEBAR_SHOW_SOFT_BUTTONS nasconde la riga di tasti rapidi
# Ctrl/Alt/Win/Tab/Esc, non necessaria (tastiera fisica o a schermo bastano).
ENV TZ=Europe/Rome \
    LC_ALL=it_IT.UTF-8 \
    NO_GAMEPAD=True \
    SELKIES_UI_TITLE=DeskHub \
    TITLE=DeskHub \
    SELKIES_UI_SIDEBAR_SHOW_STATS=False|locked \
    SELKIES_UI_SIDEBAR_SHOW_SOFT_BUTTONS=False|locked \
    SELKIES_UI_SIDEBAR_SHOW_VIDEO_SETTINGS=False|locked \
    SELKIES_UI_SIDEBAR_SHOW_SCREEN_SETTINGS=False|locked \
    SELKIES_UI_SIDEBAR_SHOW_CLIPBOARD=False|locked \
    SELKIES_UI_SIDEBAR_SHOW_FILES=False|locked \
    SELKIES_UI_SIDEBAR_SHOW_APPS=False|locked \
    SELKIES_UI_SIDEBAR_SHOW_SHARING=False|locked \
    SELKIES_UI_SIDEBAR_SHOW_GAMEPADS=False|locked \
    SELKIES_UI_SIDEBAR_SHOW_FULLSCREEN=False|locked \
    SELKIES_UI_SIDEBAR_SHOW_GAMING_MODE=False|locked \
    SELKIES_UI_SIDEBAR_SHOW_TRACKPAD=False|locked \
    SELKIES_GAMEPAD_ENABLED=False|locked \
    SELKIES_CLIPBOARD_ENABLED=False|locked \
    SELKIES_FILE_TRANSFERS=none \
    SELKIES_SECOND_SCREEN=False|locked \
    SELKIES_ENABLE_SHARING=False|locked \
    SELKIES_ENABLE_COLLAB=False|locked \
    SELKIES_ENABLE_SHARED=False|locked \
    SELKIES_ENABLE_PLAYER2=False|locked \
    SELKIES_ENABLE_PLAYER3=False|locked \
    SELKIES_ENABLE_PLAYER4=False|locked
