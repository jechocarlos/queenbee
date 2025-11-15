#!/usr/bin/env python3
"""Database migration runner."""

import argparse
import logging
import sys
from pathlib import Path

from queenbee.config.loader import load_config
from queenbee.db.connection import DatabaseManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def run_migrations(db: DatabaseManager, migrations_dir: Path) -> None:
    """Run all SQL migration files in order.
    
    Args:
        db: Database manager.
        migrations_dir: Directory containing migration files.
    """
    # Create migrations tracking table if it doesn't exist
    with db.get_cursor() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                migration_name VARCHAR(255) PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        logger.info("Ensured schema_migrations table exists")
    
    # Check what agent types already exist in the database
    existing_agent_types = set()
    with db.get_cursor() as cursor:
        try:
            cursor.execute("""
                SELECT enumlabel 
                FROM pg_enum 
                WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'agent_type')
            """)
            existing_agent_types = {row['enumlabel'] for row in cursor.fetchall()}
            logger.info(f"Found existing agent types in database: {sorted(existing_agent_types)}")
        except Exception as e:
            logger.info("No existing agent_type enum found (this is OK for fresh install)")
    
    # Get list of applied migrations from tracking table
    with db.get_cursor() as cursor:
        cursor.execute("SELECT migration_name FROM schema_migrations")
        applied_migrations = {row['migration_name'] for row in cursor.fetchall()}
    
    # If tracking table is empty but database has types, backfill the tracking
    if not applied_migrations and existing_agent_types:
        logger.info("Backfilling migration tracking for existing database...")
        migrations_to_mark = []
        
        # Mark migrations based on what exists in database
        if 'queen' in existing_agent_types and 'divergent' in existing_agent_types:
            migrations_to_mark.append('001_initial_schema.sql')
        if 'summarizer' in existing_agent_types:
            migrations_to_mark.append('002_add_summarizer_agent_type.sql')
        if 'web_searcher' in existing_agent_types:
            migrations_to_mark.append('003_add_web_searcher_agent_type.sql')
        if 'pragmatist' in existing_agent_types:
            migrations_to_mark.append('004_add_pragmatist_agent_type.sql')
        if 'user_proxy' in existing_agent_types:
            migrations_to_mark.append('005_add_user_proxy_agent_type.sql')
        if 'quantifier' in existing_agent_types:
            migrations_to_mark.append('006_add_quantifier_agent_type.sql')
        
        if migrations_to_mark:
            with db.get_cursor() as cursor:
                for migration_name in migrations_to_mark:
                    cursor.execute(
                        "INSERT INTO schema_migrations (migration_name) VALUES (%s) ON CONFLICT DO NOTHING",
                        (migration_name,)
                    )
            logger.info(f"✓ Marked {len(migrations_to_mark)} existing migrations as applied")
            applied_migrations = set(migrations_to_mark)
    
    migration_files = sorted(migrations_dir.glob("*.sql"))
    
    if not migration_files:
        logger.warning(f"No migration files found in {migrations_dir}")
        return
    
    pending_migrations = [
        mf for mf in migration_files 
        if mf.name not in applied_migrations
    ]
    
    if not pending_migrations:
        logger.info("✓ No pending migrations - database is up to date")
        return
    
    logger.info(f"Found {len(pending_migrations)} pending migration(s): {[m.name for m in pending_migrations]}")
    
    for migration_file in pending_migrations:
        logger.info(f"Running migration: {migration_file.name}")
        try:
            # Read and execute the migration
            with open(migration_file, 'r') as f:
                script = f.read()
            
            with db.get_cursor() as cursor:
                cursor.execute(script)
                # Record successful migration
                cursor.execute(
                    "INSERT INTO schema_migrations (migration_name) VALUES (%s) ON CONFLICT DO NOTHING",
                    (migration_file.name,)
                )
            
            logger.info(f"✓ Successfully applied {migration_file.name}")
        except Exception as e:
            logger.error(f"✗ Failed to apply {migration_file.name}: {e}")
            raise


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run database migrations")
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)"
    )
    parser.add_argument(
        "--migrations-dir",
        default="migrations",
        help="Path to migrations directory (default: migrations)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be executed without running"
    )
    
    args = parser.parse_args()
    
    try:
        # Load configuration
        logger.info(f"Loading configuration from {args.config}")
        config = load_config(args.config)
        
        # Set up database connection
        db = DatabaseManager(config.database)
        
        # Test connection
        try:
            db.connect()
            logger.info("✓ Database connection successful")
        except Exception as conn_err:
            logger.error(f"✗ Failed to connect to database: {conn_err}")
            logger.error("Please ensure:")
            logger.error("  1. PostgreSQL is running")
            logger.error("  2. Database credentials in config.yaml are correct")
            logger.error("  3. Database exists and is accessible")
            return 1
        
        migrations_dir = Path(args.migrations_dir)
        if not migrations_dir.exists():
            logger.error(f"Migrations directory not found: {migrations_dir}")
            return 1
        
        if args.dry_run:
            migration_files = sorted(migrations_dir.glob("*.sql"))
            logger.info("DRY RUN - Would execute:")
            for mf in migration_files:
                logger.info(f"  - {mf.name}")
            return 0
        
        # Run migrations
        with db:
            run_migrations(db, migrations_dir)
        
        logger.info("✓ All migrations completed successfully")
        return 0
        
    except KeyboardInterrupt:
        logger.info("\nMigration interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
