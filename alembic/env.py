import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from dotenv import load_dotenv
import importlib
from shared_models.database import Base  # Ajusta la importación de Base

# Forzar la carga de los modelos
importlib.import_module("shared_models.models")

# Cargar variables de entorno desde .env
load_dotenv()

# this is the Alembic Config object, which provides access to the values
# within the .ini file in use.
config = context.config

# Obtener DATABASE_URL desde las variables de entorno
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL no está configurado en el archivo .env")

# Sobrescribir sqlalchemy.url en alembic.ini
config.set_main_option("sqlalchemy.url", DATABASE_URL)

# Interpretar el archivo de configuración para Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Add your model's MetaData object here
# for 'autogenerate' support

target_metadata = Base.metadata


def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

print(f"Tablas registradas: {Base.metadata.tables.keys()}")
