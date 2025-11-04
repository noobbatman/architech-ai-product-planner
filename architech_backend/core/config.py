from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str
    GEMINI_API_KEY: str
    SUPABASE_URL: str
    SUPABASE_KEY: str
    TRELLO_API_KEY: str = "YOUR_TRELLO_API_KEY"
    TRELLO_API_TOKEN: str = "YOUR_TRELLO_API_TOKEN"

    class Config:
        env_file = ".env"

settings = Settings()