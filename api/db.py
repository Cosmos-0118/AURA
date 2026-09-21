"""Small PostgreSQL helpers for the single-process hackathon API."""

from contextlib import contextmanager
import os
from collections.abc import Iterator

import psycopg
from dotenv import load_dotenv
from psycopg import Connection
from psycopg.rows import dict_row

load_dotenv()


def database_url() -> str:
    value = os.getenv("DATABASE_URL")
    if not value:
        raise RuntimeError("DATABASE_URL is not configured")
    return value


@contextmanager
def get_connection() -> Iterator[Connection]:
    """Open one short-lived connection and commit on successful exit."""

    with psycopg.connect(database_url(), row_factory=dict_row) as connection:
        yield connection
