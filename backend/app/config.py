from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./indu_twin.db"
    cors_origins: str = "http://localhost:5173"
    simulation_interval_seconds: int = 15
    mqtt_enabled: bool = False
    mqtt_broker_host: str = "localhost"
    mqtt_broker_port: int = 1883
    jwt_secret_key: str = "dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24

    # Notificaciones por email de alertas criticas. Si smtp_host esta vacio,
    # las notificaciones se desactivan silenciosamente (no rompe nada, solo
    # no manda correos) - util en desarrollo o mientras no se configuren.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_use_tls: bool = True
    app_base_url: str = "http://localhost:5173"

    # Alertas criticas tambien por Telegram (ademas de email), mas rapido de
    # configurar que WhatsApp Business API y sin coste. Se crea un bot con
    # @BotFather en Telegram y se pone aqui su token; si esta vacio, esta
    # via de notificacion se desactiva silenciosamente igual que el email.
    telegram_bot_token: str = ""

    # Plan comercial de esta instancia: free / pro / business. Determina los
    # limites de poligonos, naves y usuarios (ver app/services/plans.py).
    plan: str = "free"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
