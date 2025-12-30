-- Database initialization script for Data Agent V4

-- This script runs when the PostgreSQL container starts for the first time



-- Create extensions

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE EXTENSION IF NOT EXISTS "pg_trgm";



-- Create basic schemas for multi-tenant architecture

CREATE SCHEMA IF NOT EXISTS auth;

CREATE SCHEMA IF NOT EXISTS core;

CREATE SCHEMA IF NOT EXISTS tenant_data;



-- Set default permissions

ALTER DEFAULT PRIVILEGES IN SCHEMA auth GRANT ALL ON TABLES TO dataagent_user;

ALTER DEFAULT PRIVILEGES IN SCHEMA core GRANT ALL ON TABLES TO dataagent_user;

ALTER DEFAULT PRIVILEGES IN SCHEMA tenant_data GRANT ALL ON TABLES TO dataagent_user;



-- Create initial indexes for performance

-- These will be expanded as we add specific tables



-- Log successful initialization

DO $$

BEGIN

    RAISE NOTICE 'Data Agent V4 database initialized successfully';

END $$;