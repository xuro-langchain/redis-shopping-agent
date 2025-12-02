import ast
import json
import os
import sqlite3
import requests
from pathlib import Path
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from redisvl.index import SearchIndex
from langchain_openai import ChatOpenAI
from langchain_community.utilities.sql_database import SQLDatabase


# ------------------------------------------------------------
# LLM Utilities
# ------------------------------------------------------------
# NOTE: Configure the LLM that you want to use
llm = ChatOpenAI(model_name="gpt-4.1", temperature=0)
# llm = ChatAnthropic(model_name="claude-3-5-sonnet-20240620", temperature=0)
# llm = ChatVertexAI(model_name="gemini-1.5-flash-002", temperature=0)

# ------------------------------------------------------------
# Redis Utilities
# ------------------------------------------------------------
def get_redis_url() -> str:
    """Get the Redis URL from environment variables."""
    return os.getenv("REDIS_URL", "redis://localhost:6379")


def get_redis_client():
    """Get a Redis client (uses REDIS_URL env var)."""
    from redis import Redis
    return Redis.from_url(get_redis_url())


# ------------------------------------------------------------
# Concert Index & Seeding
# ------------------------------------------------------------
SEED_DIR = Path(__file__).parent / "seed"
CONCERTS_JSON_PATH = SEED_DIR / "concerts.json"
CONCERT_INDEX_SCHEMA_PATH = SEED_DIR / "concert_index.yaml"

# Singleton for concert index
_concert_index: SearchIndex | None = None


def get_concert_index() -> SearchIndex:
    """
    Get a shared SearchIndex instance for concerts.
    Creates and connects the index on first call, then reuses it.
    """
    global _concert_index
    if _concert_index is None:
        _concert_index = SearchIndex.from_yaml(str(CONCERT_INDEX_SCHEMA_PATH))
        _concert_index.connect(get_redis_url())
    return _concert_index


def seed_concerts(force: bool = False) -> None:
    """
    Seed Redis with concerts from concerts.json.
    Creates index and loads data if not present.

    Args:
        force: If True, drop existing index and reseed all data.
    """
    index = get_concert_index()

    if force and index.exists():
        index.delete(drop=True)

    if not index.exists():
        index.create(overwrite=False)

        with open(CONCERTS_JSON_PATH, "r") as f:
            concerts = json.load(f)
        
        index.load(concerts, id_field="id")
        print(f"[Seed] Loaded {len(concerts)} concerts to Redis")


# ------------------------------------------------------------
# Database Utilities
# ------------------------------------------------------------
def get_engine_for_chinook_db():
    """Pull sql file, populate in-memory database, and create engine."""
    url = "https://raw.githubusercontent.com/lerocha/chinook-database/master/ChinookDatabase/DataSources/Chinook_Sqlite.sql"
    response = requests.get(url)
    sql_script = response.text

    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.executescript(sql_script)
    return create_engine(
        "sqlite://",
        creator=lambda: connection,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

engine = get_engine_for_chinook_db()
db = SQLDatabase(engine)

# ------------------------------------------------------------
# Node Helper Functions
# ------------------------------------------------------------
def get_customer_id_from_identifier(identifier: str) -> Optional[int]:
    """
    Retrieve Customer ID using an identifier, which can be a customer ID, email, or phone number.
    Args:
        identifier (str): The identifier can be customer ID, email, or phone.
    Returns:
        Optional[int]: The CustomerId if found, otherwise None.
    """
    if identifier.isdigit():
        return int(identifier)
    elif identifier[0] == "+":
        query = f"SELECT CustomerId FROM Customer WHERE Phone = '{identifier}';"
        result = db.run(query)
        formatted_result = ast.literal_eval(result)
        if formatted_result:
            return formatted_result[0][0]
    elif "@" in identifier:
        query = f"SELECT CustomerId FROM Customer WHERE Email = '{identifier}';"
        result = db.run(query)
        formatted_result = ast.literal_eval(result)
        if formatted_result:
            return formatted_result[0][0]
    return None 

def format_user_memory(user_data: dict) -> str:
    """Format user preferences from memory profile for display."""
    profile = user_data.get('memory', {})
    parts = []

    if profile.get('music_preferences'):
        parts.append(f"Music Preferences: {', '.join(profile['music_preferences'])}")
    if profile.get('preferred_location'):
        parts.append(f"Preferred Location: {profile['preferred_location']}")
    if profile.get('max_concert_budget'):
        parts.append(f"Max Concert Budget: ${profile['max_concert_budget']}")

    return "\n".join(parts)


# ------------------------------------------------------------
# Auto-seed concert data on module import
# ------------------------------------------------------------
seed_concerts()