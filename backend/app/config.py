from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///slms.db"

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"

    access_token_expire_minutes: int = 15
    refresh_token_expire_hours: int = 8
    agent_token_expire_minutes: int = 15

    class Config:
        env_file = ".env"


settings = Settings()