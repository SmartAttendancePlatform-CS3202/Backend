import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context
from dotenv import load_dotenv

# Add libs to sys.path so we can import shared_core
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'libs', 'shared-core')))

from shared_core.models.base import Base
import shared_core.models.identity
import shared_core.models.courses
import shared_core.models.attendance
import shared_core.models.vision
import shared_core.models.system

# Load env variables from attendance-service
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'services', 'attendance-service', '.env'))

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    url = os.getenv("DATABASE_URL") or config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    url = os.getenv("DATABASE_URL")
    if url:
        configuration["sqlalchemy.url"] = url
        
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
