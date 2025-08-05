-- Initialize Keycloak database
-- This script creates the necessary databases for Keycloak

-- Create Keycloak database
CREATE DATABASE keycloak_dev;

-- Grant privileges to the devuser
GRANT ALL PRIVILEGES ON DATABASE keycloak_dev TO devuser;