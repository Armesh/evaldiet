from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pydantic_settings import BaseSettings, SettingsError, SettingsConfigDict


# -------------------------------------------------------------------
# Settings (inlined config)
# -------------------------------------------------------------------

class Settings(BaseSettings):
    DATABASE_URL: str

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


try:
    settings = Settings()
except SettingsError as exc:
    raise RuntimeError("DATABASE_URL must be set in environment or .env") from exc

# -------------------------------------------------------------------
# Engine + Session
# -------------------------------------------------------------------

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)
