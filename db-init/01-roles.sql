-- Runs once, as the postgres superuser, against the firmdb database on first
-- container init. Sets up the pgvector extension and the two least-privilege roles.
--
-- Keep these passwords in sync with .env / .env.example.

-- pgvector extension (used only when RETRIEVAL_MODE=true).
CREATE EXTENSION IF NOT EXISTS vector;

-- ---- Admin role: owns the schema, runs DDL + seeding (scripts/init_db.py) ----
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'texttosql_admin') THEN
    CREATE ROLE texttosql_admin LOGIN PASSWORD 'admin_pw';
  END IF;
END $$;

ALTER DATABASE firmdb OWNER TO texttosql_admin;
GRANT CREATE, USAGE ON SCHEMA public TO texttosql_admin;

-- ---- Read-only role: the ONLY role the agent uses at query time ----
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'texttosql_readonly') THEN
    CREATE ROLE texttosql_readonly LOGIN PASSWORD 'readonly_pw';
  END IF;
END $$;

-- Hard read-only + a per-statement safety timeout at the role level.
ALTER ROLE texttosql_readonly SET default_transaction_read_only = on;
ALTER ROLE texttosql_readonly SET statement_timeout = '15s';

GRANT USAGE ON SCHEMA public TO texttosql_readonly;

-- Auto-grant SELECT on every table the admin creates later (init_db.py).
ALTER DEFAULT PRIVILEGES FOR ROLE texttosql_admin IN SCHEMA public
  GRANT SELECT ON TABLES TO texttosql_readonly;
