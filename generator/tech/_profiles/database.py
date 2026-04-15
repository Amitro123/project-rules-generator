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
]
