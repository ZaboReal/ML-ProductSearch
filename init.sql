-- Initialize the hinthint database with pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Grant permissions to the postgres user
GRANT ALL PRIVILEGES ON DATABASE hinthint TO postgres;

-- Create the products table (will be created by the application but this ensures schema)
-- This is mainly for documentation purposes as the Python code handles table creation
