from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+psycopg2://postgres:@/postgres?host=/tmp/transit-crowding-pg"

    # Clerk (auth): https://dashboard.clerk.com -> API Keys
    clerk_publishable_key: str = ""
    clerk_secret_key: str = ""
    # e.g. https://your-app.clerk.accounts.dev  (Clerk "Frontend API" host, used to derive the JWKS URL)
    clerk_issuer: str = ""

    frontend_origin: str = "http://localhost:3000"
    # Additional origins allowed alongside frontend_origin (comma-separated).
    # Flowcast's dev server runs on 5174 (see frontend/vite.config.js), and
    # the deployed demo needs to be allowed too once it's wired to a live backend.
    extra_cors_origins: str = "http://localhost:5174,https://flowcast-transit-ai.vercel.app"

    api_key_prefix: str = "tc"

    @property
    def clerk_jwks_url(self) -> str:
        return f"{self.clerk_issuer.rstrip('/')}/.well-known/jwks.json"


@lru_cache
def get_settings() -> Settings:
    return Settings()
