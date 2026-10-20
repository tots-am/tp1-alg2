from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Restaurant:
    establishment_id: str
    name: str
    cnae_description: str
    address: str
    neighborhood: str
    latitude: float
    longitude: float
    aliases: tuple[str, ...] = ()

    @property
    def search_text(self) -> str:
        return " ".join(
            (
                self.name,
                self.address,
                self.neighborhood,
                self.establishment_id,
                *self.aliases,
            )
        ).casefold()

    @property
    def label(self) -> str:
        location = ", ".join(part for part in (self.address, self.neighborhood) if part)
        return f"{self.name} — {location} (ID {self.establishment_id})"


@dataclass(frozen=True, slots=True)
class Courier:
    courier_id: str
    latitude: float
    longitude: float


@dataclass(frozen=True, slots=True)
class NearbyCourier:
    courier: Courier
    distance_km: float

    def eta_minutes(self, speed_kmh: float) -> float:
        if speed_kmh <= 0:
            raise ValueError("velocidade deve ser positiva")
        return self.distance_km / speed_kmh * 60
