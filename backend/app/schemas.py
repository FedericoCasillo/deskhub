from typing import Literal, Optional

from pydantic import BaseModel, Field

Status = Literal["RUNNING", "STOPPED", "ORPHAN"]
Role = Literal["admin", "user"]


class DesktopSummary(BaseModel):
    id: str
    name: str
    status: Status
    has_config: bool
    owner: Optional[str] = None
    max_ram_mb: int = 0
    max_cpus: float = 0
    idle_timeout_minutes: int = 0


class DesktopListResponse(BaseModel):
    desktops: list[DesktopSummary]
    running: int
    stopped: int
    orphan: int


class DesktopInfo(BaseModel):
    id: str
    name: str
    status: Status
    container_name: str
    config_dir: str
    config_present: bool
    container_present: bool
    network_present: bool
    owner: Optional[str] = None
    max_ram_mb: int = 0
    max_cpus: float = 0
    idle_timeout_minutes: int = 0


class OrphanEntry(BaseModel):
    id: str
    name: Optional[str] = None
    warning: Optional[str] = None


class CreateDesktopRequest(BaseModel):
    # Nome scelto dall'amministratore per riconoscere il desktop (mostrato in
    # dashboard e usato per generare l'identificativo/cartella): niente piu'
    # "nome utente Linux" da chiedere, e' sempre "abc" dentro il container,
    # fisso lato backend (vedi docker_service.create_desktop).
    name: str = Field(min_length=1, max_length=60)
    owner: str
    reuse_id: Optional[str] = None
    # None = usa il default globale (Settings) al momento della creazione.
    # Nessuna risorsa illimitata: ogni desktop ha sempre un tetto RAM/CPU.
    max_ram_mb: Optional[int] = Field(default=None, gt=0, le=1_048_576)
    max_cpus: Optional[float] = Field(default=None, gt=0, le=256)
    # None = usa il default globale (Settings) al momento della creazione,
    # come max_ram_mb/max_cpus sopra. 0 = spegnimento automatico disabilitato
    # per questo desktop.
    idle_timeout_minutes: Optional[int] = Field(default=None, ge=0, le=1440)


class DesktopLimitsPayload(BaseModel):
    max_ram_mb: int = Field(gt=0, le=1_048_576)
    max_cpus: float = Field(gt=0, le=256)
    idle_timeout_minutes: int = Field(ge=0, le=1440)


class DesktopUsage(BaseModel):
    cpu_percent: Optional[float] = None
    mem_used_mb: Optional[float] = None


class FleetUsage(BaseModel):
    """Uso aggregato di tutti i desktop RUNNING insieme (CPU sommata tra i
    container, RAM sommata), per dare all'admin un indicatore complessivo
    oltre a quello per singolo desktop."""

    cpu_percent: Optional[float] = None
    mem_used_mb: Optional[float] = None
    max_ram_mb: int = 0
    max_cpus: float = 0
    running_count: int = 0
    # Stesso identico campione per-desktop usato per calcolare i totali sopra
    # (chiave = id del desktop): il frontend lo passa alle card al posto di
    # interrogare di nuovo /desktops/{id}/usage, cosi' totale e singole card
    # mostrano sempre lo stesso numero perche' sono letteralmente lo stesso
    # dato, non due polling indipendenti che possono sfasarsi nel tempo.
    per_desktop: dict[str, DesktopUsage] = {}


class DesktopSessionOut(BaseModel):
    url: str


class DeleteDesktopRequest(BaseModel):
    remove_config: bool = False


class JobStarted(BaseModel):
    job_id: str


class JobMessage(BaseModel):
    status: Literal["progress", "success", "error"]
    message: str
    log: Optional[str] = None
    result: Optional[dict] = None


class SettingsPayload(BaseModel):
    idle_timeout_minutes: int = Field(ge=0, le=1440)
    # Usati come default per i nuovi desktop quando non viene specificato un
    # override alla creazione. Nessuna risorsa illimitata: sempre un tetto.
    default_max_ram_mb: int = Field(gt=0, le=1_048_576)
    default_max_cpus: float = Field(gt=0, le=256)


class LoginRequest(BaseModel):
    username: str
    password: str = Field(min_length=1)


class UserOut(BaseModel):
    username: str
    role: Role


class MeOut(UserOut):
    pass


class CreateUserRequest(BaseModel):
    username: str = Field(pattern=r"^[a-z_][a-z0-9_-]*$")
    password: str = Field(min_length=8)
    role: Role = "user"


class SetPasswordRequest(BaseModel):
    password: str = Field(min_length=8)
