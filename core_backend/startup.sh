#!/bin/bash
python -m alembic upgrade head
exec gunicorn -k uvicorn.workers.UvicornWorker -w 4 -b 0.0.0.0:8000 --preload main:app
#
