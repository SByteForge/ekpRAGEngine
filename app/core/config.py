from pydantic_settings import BaseSettings, SettingsConfigDict
 
 
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
 
    database_url: str = "postgresql://ekp:ekp_local_dev@localhost:5432/ekp"
 
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = "ekp_chunks"
 
    ollama_base_url: str = "http://localhost:11434"
    ollama_gen_model: str = "mistral:latest"
    ollama_embed_model: str = "nomic-embed-text:latest"
    ollama_judge_model: str = "gemma4:latest"
 
    api_key_salt: str = "change_me_local_only"
    jwt_secret: str = "change_me_local_only"
    jwt_expire_minutes: int = 120
 
    chunk_size_tokens: int = 512
    chunk_overlap_tokens: int = 64
 
    retrieval_top_k_dense: int = 20
    retrieval_top_k_bm25: int = 20
    retrieval_top_k_final: int = 5
    rerank_model: str = "BAAI/bge-reranker-base"
 
 
settings = Settings()
