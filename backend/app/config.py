from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "SecureCounsel NY"
    environment: str = "development"

    frontend_origin: str = "http://localhost:3000"

    jwt_secret: str = "replace_me"
    jwt_algorithm: str = "HS256"

    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    cohere_api_key: str = ""
    cohere_rerank_model: str = "rerank-v3.5"

    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""
    qdrant_collection: str = "legal_chunks"

    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""

    ny_openleg_api_key: str = ""

    relevance_threshold: float = 0.75
    faithfulness_threshold: float = 0.85
    max_retrieval_attempts: int = 2

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()