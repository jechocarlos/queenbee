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
    migration_files = sorted(migrations_dir.glob("*.sql"))
    
    if not migration_files:
        logger.warning(f"No migration files found in {migrations_dir}")
        return
    
    logger.info(f"Found {len(migration_files)} migration file(s)")
    
    for migration_file in migration_files:
        logger.info(f"Running migration: {migration_file.name}")
        try:
            db.execute_script(str(migration_file))
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
        
    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
