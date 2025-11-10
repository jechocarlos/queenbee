# Database Migration: Adding Summarizer Agent Type

## Overview

This migration adds the `summarizer` value to the PostgreSQL `agent_type` enum to support the new SummarizerAgent that handles rolling summaries and final synthesis.

## Issue

When running QueenBee after the SummarizerAgent was added to the codebase, you may encounter:

```
psycopg.errors.InvalidTextRepresentation: invalid input value for enum agent_type: "summarizer"
```

This occurs because the database schema hasn't been updated to include the new agent type.

## Solution

### Option 1: Run Migration Script (Recommended)

If you have an existing database, apply only the new migration:

```bash
PGPASSWORD=your_password psql -h localhost -U queenbee -d queenbee -f migrations/002_add_summarizer_agent_type.sql
```

Replace `your_password` with your actual database password from `.env`.

### Option 2: Fresh Database Setup

If you're setting up a fresh database:

```bash
python scripts/migrate.py
```

This will run all migrations in order.

### Option 3: Docker Environment

If using Docker Compose, recreate the database container:

```bash
docker-compose -f docker-compose.local.yml down -v
docker-compose -f docker-compose.local.yml up -d
python scripts/migrate.py
```

## Verification

Verify the migration was successful:

```bash
PGPASSWORD=your_password psql -h localhost -U queenbee -d queenbee -c "SELECT unnest(enum_range(NULL::agent_type));"
```

You should see:

```
   unnest   
------------
 queen
 divergent
 convergent
 critical
 summarizer
(5 rows)
```

## What Changed

### Database Schema

The `agent_type` enum was extended to include:

```sql
ALTER TYPE agent_type ADD VALUE 'summarizer';
```

### Application Code

- `src/queenbee/db/models.py`: Added `SUMMARIZER = "summarizer"` to `AgentType` enum
- `src/queenbee/agents/summarizer.py`: New agent class for summarization tasks
- `src/queenbee/config/loader.py`: Added `summarizer: AgentPromptConfig` to configuration
- `config.yaml`: Added summarizer configuration section

## Troubleshooting

### "type 'agent_type' already exists"

This happens when running the full migration script on an existing database. Use Option 1 above to apply only the new migration.

### Connection refused

Ensure PostgreSQL is running:

```bash
docker ps | grep postgres
```

If not running:

```bash
docker-compose -f docker-compose.local.yml up -d postgres
```

### Permission denied

Ensure you have the correct database credentials in your `.env` file and that the database user has ALTER TYPE permissions.
