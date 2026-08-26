# Pinnata al digest risolto il 2026-08-25 per riproducibilita': il tag
# "ubuntu-kde" su LinuxServer.io puo' cambiare contenuto nel tempo, il digest
# no. Per aggiornare volontariamente all'ultima immagine upstream, sostituisci
# con FROM lscr.io/linuxserver/webtop:ubuntu-kde (senza digest) e ricostruisci.
FROM lscr.io/linuxserver/webtop@sha256:d91fb284794d554d89b4b210ebe56a538c755dfb2054a3741ed7471363cd5369

ENV TZ=Europe/Rome \
    LC_ALL=it_IT.UTF-8 \
    NO_GAMEPAD=True \
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
