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
        "@sha256:7abfcc07c352058b1a3f72d8e525e62e3dd495ab2491224401f7129e79a38479"
    )

    proxy_network: str = "deskhub-proxy"
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


settings = Settings()
