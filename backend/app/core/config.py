from functools import lru_cache
from urllib.parse import quote, unquote, urlsplit, urlunsplit

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    app_name: str = "College RAG Assistant"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "postgresql+psycopg://postgres:password@localhost:5432/college_rag"
    supabase_url: str = ""
    supabase_publishable_key: str = ""
    supabase_secret_key: str = ""
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    upload_dir: str = "./data/uploads"
    chroma_persist_directory: str = "./data/chroma"
    chroma_collection_name: str = "college_documents"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    llm_provider: str = "CHANGE_ME"
    llm_model: str = "CHANGE_ME"
    llm_api_key: str = "CHANGE_ME"
    jwt_secret_key: str = "CHANGE_ME"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    top_k: int = 5
    min_relevance_score: str = "CHANGE_ME"
    max_file_size_mb: int = 20
    allowed_file_types: str = "application/pdf"

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            value_str = value.strip()
            if value_str.startswith("[") and value_str.endswith("]"):
                try:
                    import json
                    parsed = json.loads(value_str)
                    if isinstance(parsed, list):
                        return [str(o).strip() for o in parsed if str(o).strip()]
                except Exception:
                    pass
            return [origin.strip() for origin in value_str.split(",") if origin.strip()]
        return value

    @field_validator("database_url", mode="before")
    @classmethod
    def use_psycopg_driver(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        if value.startswith(("postgresql://", "postgres://")):
            value = "postgresql+psycopg://" + value.split("://", 1)[1]
        scheme, separator, remainder = value.partition("://")
        if not separator or "@" not in remainder:
            return value
        user_info, at, host_and_path = remainder.rpartition("@")
        username, colon, password = user_info.partition(":")
        if not colon:
            return value
        parsed_host = urlsplit(f"{scheme}://{host_and_path}")
        authority = f"{quote(unquote(username), safe='')}:{quote(unquote(password), safe='')}@{parsed_host.netloc}"
        return urlunsplit((scheme, authority, parsed_host.path, parsed_host.query, parsed_host.fragment))


@lru_cache
def get_settings() -> Settings:
    return Settings()
