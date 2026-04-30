# FLASH
FLASH software components for AusSRC implementation

# Getting Started (for Django App)

# Setup your local db
CREATE DATABASE flashdb;
CREATE USER flash WITH PASSWORD 'password';
GRANT ALL PRIVILEGES ON DATABASE flashdb TO flash;

# Make a new dev env 


# Install the package dependencies in 



# To set Django admin portal up for testing
export DJANGO_SUPERUSER_USERNAME=admin
export DJANGO_SUPERUSER_EMAIL=admin@example.com
export DJANGO_SUPERUSER_PASSWORD=admin123

# Make a local copy of the DB using either the Django App itself or
# (if you plan to copy in data from prod use the db_copy.py script)
cd django/flashdb/db_query/

# You will need to have the flash1 VM oracle key in .ssh
# Note the copy happens from production to your local DB and will leave some 
# csv and bin files locally that you should delete
python -m utils.db_copy


