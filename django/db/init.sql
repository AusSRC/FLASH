-- Enable dblink extension
CREATE EXTENSION IF NOT EXISTS dblink;

-- Create admin user if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'admin') THEN
        CREATE USER "admin" WITH PASSWORD 'password';
        ALTER USER "admin" WITH SUPERUSER;
    END IF;
END $$;

-- Create flash user if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'flash') THEN
        CREATE USER "flash" WITH PASSWORD 'password';
        ALTER USER "flash" WITH SUPERUSER;
    END IF;
END $$;

-- Create chad database if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'flashdb') THEN
        PERFORM dblink_exec('dbname=postgres', 'CREATE DATABASE flashdb WITH TEMPLATE = template0 ENCODING = ''UTF8'' LC_COLLATE = ''en_US.utf8'' LC_CTYPE = ''en_US.utf8''');
        PERFORM dblink_exec('dbname=postgres', 'ALTER DATABASE flashdb OWNER TO "admin"');
    END IF;
END $$;