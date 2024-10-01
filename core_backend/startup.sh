#!/bin/bash
python -m alembic upgrade head
python add_users_to_db.py
exec gunicorn -k main.Worker -w 4 -b 0.0.0.0:8000 --preload \
    -c gunicorn_hooks_config.py main:app
#
