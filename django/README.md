# Getting Started

# Local App Start (fill local_envs with values for your local db)
uv sync
set -a                                                                         
source local_envs.env
set +a
python flashdb/manage.py runserver

In a browser navigate to localhost:8000

# Local App in Docker + Gunicorn + Nginx (80) Start (fill local_envs with values for your local db but leave db_host alone)
docker-compose -f docker-compose-local.yml up --build
In a browser navigate to localhost:80

# Deployed App in VM Docker + Nginx (443) Start (set secrets on ansible build and let the CI do it)
