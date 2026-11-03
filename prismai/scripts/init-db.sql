-- Role used by the application; NOSUPERUSER NOBYPASSRLS so RLS policies apply.
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'prismai_app') THEN
        CREATE ROLE prismai_app LOGIN PASSWORD 'prismai_app' NOSUPERUSER NOBYPASSRLS;
    END IF;
END
$$;

GRANT CONNECT ON DATABASE prismai TO prismai_app;
GRANT USAGE ON SCHEMA public TO prismai_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO prismai_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO prismai_app;
