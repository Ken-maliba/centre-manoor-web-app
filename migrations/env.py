# A generic, single database configuration.

[alembic]
# Path to migration scripts
script_location = migrations

# Template used to generate migration files
# file_template = %%(rev)s_%%(slug)s
# set to "true" to run the environment.py as a package
# sqlalchemy.dialect = postgresql

# Logging configuration
# Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL
# logging_level = INFO
# Logging file
# log_file = alembic.log

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stdout,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s

# ====================================================
# DATABASE CONNECTION
# ====================================================
# Pour Render : PostgreSQL
# Tu peux choisir Internal ou External URL selon ton contexte

# --- URL interne (si l'application est hébergée sur Render) ---
sqlalchemy.url = postgresql://manoor_db_user:s6H9dQhbCbLEtH9pC7QaRhHdS11S6G4h@dpg-d4m5b7k9c44c73frj7ng-a:5432/manoor_db

# --- URL externe (si tu veux te connecter depuis ton PC local) ---
# sqlalchemy.url = postgresql://manoor_db_user:s6H9dQhbCbLEtH9pC7QaRhHdS11S6G4h@dpg-d4m5b7k9c44c73frj7ng-a.oregon-postgres.render.com:5432/manoor_db
