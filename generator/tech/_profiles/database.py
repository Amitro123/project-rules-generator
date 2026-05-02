"""Database TechProfile entries."""

from typing import List

from generator.tech.profile import TechProfile

DATABASE: List[TechProfile] = [
    TechProfile(
        name="sqlalchemy",
        display_name="SQLAlchemy",
        category="database",
        skill_name="sqlalchemy-models",
        packages=["sqlalchemy"],
        readme_keywords=["sqlalchemy"],
        tools=["alembic", "pytest"],
        rules={
            "high": [
                "Use async SQLAlchemy for async frameworks",
                "Always use sessions properly (with context manager)",
                "Define relationships with lazy='selectin' to avoid N+1",
            ],
            "medium": [
                "Use Alembic for database migrations",
                "Add indexes on frequently queried columns",
                "Implement soft deletes for critical data",
            ],
        },
    ),
    TechProfile(
        name="redis",
        display_name="Redis",
        category="database",
        skill_name="redis-caching",
        packages=["redis"],
        readme_keywords=["redis"],
        tools=["redis-cli"],
    ),
    TechProfile(
        name="mongodb",
        display_name="MongoDB",
        category="database",
        skill_name="mongodb-queries",
        packages=["pymongo", "motor"],
        readme_keywords=["mongodb", "mongo"],
    ),
    TechProfile(
        name="postgresql",
        display_name="PostgreSQL",
        category="database",
        skill_name="postgresql-queries",
        packages=["psycopg2", "psycopg2-binary", "asyncpg"],
        readme_keywords=["postgresql", "postgres"],
        tools=["psql", "pg_dump"],
    ),
    TechProfile(
        name="mysql",
        display_name="MySQL",
        category="database",
        skill_name="",
        packages=["mysql-connector-python", "pymysql", "mysqlclient"],
        readme_keywords=["mysql"],
    ),
    TechProfile(
        name="supabase",
        display_name="Supabase",
        category="database",
        skill_name="supabase-auth-storage",
        packages=["supabase"],
        readme_keywords=["supabase"],
    ),
    TechProfile(
        name="chromadb",
        display_name="ChromaDB",
        category="database",
        skill_name="chromadb-rag",
        packages=["chromadb"],
        readme_keywords=["chromadb", "chroma", "vector store", "vector database"],
        rules={
            "high": [
                "Use persistent client (chromadb.PersistentClient) in production — never in-memory for data that must survive restarts",
                "Always specify the embedding function explicitly; don't rely on the default",
                "Use collection.get() to check for existing documents before upserting to avoid duplicates",
            ],
            "medium": [
                "Prefer upsert() over add() when document IDs may already exist",
                "Set n_results to a small value (3-10) and filter by distance threshold before returning to LLM",
                "Index on metadata fields used in where= filters for large collections",
            ],
        },
    ),
    TechProfile(
        name="qdrant",
        display_name="Qdrant",
        category="database",
        skill_name="qdrant-vector-search",
        packages=["qdrant-client"],
        readme_keywords=["qdrant", "vector search"],
        rules={
            "high": [
                "Create collections with explicit vector size matching your embedding model output dimension",
                "Use payload filtering in search() to narrow results before vector scoring",
                "Handle QdrantException with retry logic — Qdrant Cloud may throttle on cold starts",
            ],
            "medium": [
                "Batch upsert payloads in chunks of 100-500 for large datasets",
                "Use named vectors when storing multiple embedding types per document",
                "Store the source document ID and chunk index in payload for retrieval traceability",
            ],
        },
    ),
]
