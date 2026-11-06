from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Cartella dedicata (host) che contiene solo le config dei desktop, una
    # per sottocartella (nome = id del desktop, vedi config_dir_prefix sotto).
    # Deve essere impostata esplicitamente: niente default che punti a una
    # home directory specifica, per evitare che il manager veda file estranei
    # quando viene installato su un'altra macchina.
    data_dir: str

    # Contesto di build dell'immagine desktop: copiato dentro l'immagine del
    # manager in fase di build (vedi Dockerfile), non dipende da percorsi
    # dell'host.
    webtop_build_context: str = "/app/webtop-image"

    webtop_image: str = "deskhub-webtop:latest"

    # Fonte di default per l'immagine desktop: "pull" scarica uno snapshot
    # pinnato pubblicato dal progetto stesso (indipendente da eventuali
    # cambi futuri dell'immagine upstream); "build" ricostruisce sempre da
    # webtop-image/Dockerfile partendo dall'immagine upstream corrente.
    # Pinnato per digest (non per tag): un tag su un registry e' riscrivibile
    # (un push accidentale sotto lo stesso tag cambierebbe silenziosamente
    # cosa scaricano i client), un digest no. Per aggiornare, pubblicare una
    # nuova immagine e sostituire questo digest in un commit esplicito.
    webtop_source: str = "pull"
    webtop_pinned_image: str = (
        "ghcr.io/federicocasillo/deskhub-webtop"
        "@sha256:1594766070ed4fee7dd486e646bea8f79482307e1cf268d973977f91f8212170"
    )

    # Rete condivisa solo da manager e Traefik: i desktop NON ci stanno piu'.
    # Ogni desktop ha una rete bridge sua (desktop_network_prefix + id) a cui
    # e' collegato anche Traefik, e nient'altro: da un desktop non si
    # raggiungono ne' gli altri desktop (bridge diverse, isolate da Docker)
    # ne' il manager. Sulla rete comune un desktop esponeva a tutti gli altri
    # nginx (3000/3001) e il WebSocket di Selkies (8082) senza credenziali:
    # il token di sessione lo controlla solo Traefik.
    proxy_network: str = "deskhub-proxy"
    desktop_network_prefix: str = "deskhub-net-"
    # Da qui si ritaglia una /28 per ogni rete di desktop (bastano 3
    # indirizzi: gateway, desktop, Traefik): 4096 desktop, invece delle ~30
    # reti dei pool automatici di Docker. Deve non sovrapporsi alla LAN ne' a
    # reti raggiungibili dai desktop (VPN, altre sottoreti): altrimenti quegli
    # indirizzi, visti da un desktop, finirebbero sulla sua bridge.
    desktop_subnet_pool: str = "10.213.0.0/16"
    # Container di Traefik da collegare alla rete di ogni desktop (vedi
    # deploy/traefik/compose.yml). Con SKIP_TRAEFIK=1 mettere qui il nome del
    # proprio reverse proxy.
    traefik_container: str = "deskhub-traefik"
    container_name_prefix: str = "deskhub-desktop-"
    # Vuoto: la cartella di config si chiama esattamente come l'id del
    # desktop (slug "proprietario-nome", vedi docker_service.generate_slug),
    # non piu' "ubuntu-config-<id>". data_dir contiene solo config di
    # desktop (vedi commento sopra), quindi nessun rischio di confonderle
    # con altro.
    config_dir_prefix: str = ""
    static_dir: str = "/app/static"

    expected_puid: int = 1000
    expected_pgid: int = 1000

    # Bootstrap: se non esiste ancora nessun utente (primo avvio, o file
    # utenti perso), il manager crea questo admin all'avvio. Ignorate una
    # volta che almeno un utente esiste gia' — non servono piu' dopo il
    # primo bootstrap, ma lasciarle in .env non fa danno.
    manager_initial_admin_user: str | None = None
    manager_initial_admin_password: str | None = None

    # Segreto condiviso con Traefik (providers.http): protegge l'endpoint
    # interno che genera le route dinamiche per-sessione (contengono i token
    # in chiaro nelle regole PathPrefix, vanno protette da accesso pubblico).
    traefik_internal_secret: str | None = None
    # Indirizzo del manager visto da Traefik sulla rete comune (nome del
    # container, vedi compose.yml): ci punta il forwardAuth delle sessioni.
    manager_internal_url: str = "http://deskhub:8000"


settings = Settings()
