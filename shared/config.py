from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = "postgresql+asyncpg://dstn:dstn@localhost:5432/dstn"
    canadabuys_base_url: str = "https://canadabuys.canada.ca/openapi/v1"
    open_gov_dataset_url: str = "https://open.canada.ca/data/en/datastore/dump/d8f85d91-7dec-4fd1-8055-483b77225d8b"
    issuer_agent_admin_url: str = "http://localhost:8021"
    issuer_agent_api_key: str = "change-me"
    sync_interval_minutes: int = 60
    # Portal settings (used in Part 3)
    portal_secret_key: str = "change-me-32-chars-minimum"
    portal_rp_id: str = "localhost"
    portal_rp_name: str = "DSTN Supplier Portal"
    portal_origin: str = "http://localhost:3000"
    admin_api_key: str = "change-admin-key"
    # Stratos settings (used in Part 2)
    stratos_api_url: str = "https://stratos-api.thestratos.org/api/v1"
    stratos_api_key: str = "change-me"
    issuer_did: str = ""
    issuer_schema_id: str = ""
    issuer_cred_def_id: str = ""
    issuer_rev_reg_id: str = ""

settings = Settings()
