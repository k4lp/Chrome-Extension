#!/usr/bin/env python3
"""Database migration script - migrates to new schema (Tasks, Memory, Goals, Datavault).

⚠️ WARNING: This will DELETE ALL existing data!

This script will:
1. Create a backup of your current database
2. Drop all existing tables (Notes, Projects, old Tasks, etc.)
3. Create new tables (Tasks, Memory, Goals, Datavault)

Usage:
    python migrate_db.py [--yes]

Options:
    --yes    Skip confirmation prompt (dangerous!)
"""

import sys
from pathlib import Path
from shutil import copy
from datetime import datetime
from loguru import logger

# Setup logging
logger.remove()
logger.add(sys.stderr, level="INFO")


def migrate_database(skip_confirmation: bool = False) -> bool:
    """Migrate database to new schema.

    Args:
        skip_confirmation: Skip confirmation prompt

    Returns:
        True if migration successful, False otherwise
    """
    # Import GemBrain modules
    from gembrain.config.manager import get_config_manager
    from gembrain.core.db import close_db, recreate_db

    # Load config
    config_manager = get_config_manager()
    settings = config_manager.load()
    db_path = settings.storage.db_path
    backup_dir = Path(settings.storage.backup_dir)

    logger.info("=" * 80)
    logger.info("GemBrain Database Migration")
    logger.info("=" * 80)
    logger.info(f"Database: {db_path}")

    # Check if database exists
    if not Path(db_path).exists():
        logger.error(f"Database not found at {db_path}")
        logger.info("Creating new database with new schema...")
        recreate_db(db_path)
        logger.success("✓ New database created successfully!")
        return True

    # Show warning
    logger.warning("")
    logger.warning("⚠️  WARNING: This will DELETE ALL existing data!")
    logger.warning("")
    logger.warning("This migration will:")
    logger.warning("  1. Create a backup of your current database")
    logger.warning("  2. Drop all existing tables (Notes, Projects, old Tasks, etc.)")
    logger.warning("  3. Create new tables (Tasks, Memory, Goals, Datavault)")
    logger.warning("")
    logger.warning("ALL YOUR CURRENT DATA WILL BE LOST!")
    logger.warning("")

    # Confirmation
    if not skip_confirmation:
        response = input("Do you want to proceed? (type 'yes' to confirm): ")
        if response.lower() != 'yes':
            logger.info("Migration cancelled.")
            return False

    try:
        # Step 1: Create backup
        backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"gembrain_pre_migration_{timestamp}.db"

        logger.info("")
        logger.info("Step 1: Creating backup...")
        copy(db_path, backup_path)
        logger.success(f"✓ Backup created: {backup_path}")

        # Step 2: Close any existing connections
        logger.info("")
        logger.info("Step 2: Closing database connections...")
        close_db()
        logger.success("✓ Database connections closed")

        # Step 3: Recreate database with new schema
        logger.info("")
        logger.info("Step 3: Recreating database with new schema...")
        recreate_db(db_path)
        logger.success("✓ Database recreated with new schema")

        logger.info("")
        logger.info("=" * 80)
        logger.success("✓ Migration completed successfully!")
        logger.info("=" * 80)
        logger.info("")
        logger.info(f"Backup saved to: {backup_path}")
        logger.info("")
        logger.info("New data structures available:")
        logger.info("  - Tasks: Decomposed work items with status tracking")
        logger.info("  - Memory: Small hints, clues, and insights")
        logger.info("  - Goals: Expected outcomes for verification")
        logger.info("  - Datavault: Large data storage (code, text, outputs)")
        logger.info("")
        logger.info("You can now start GemBrain with the new schema!")
        logger.info("")

        return True

    except Exception as e:
        logger.error("")
        logger.error(f"✗ Migration failed: {e}")
        logger.error("")
        logger.error("Your original database should still be intact.")
        logger.error(f"Backup location: {backup_path if 'backup_path' in locals() else 'N/A'}")
        logger.error("")
        return False


def main():
    """Main entry point."""
    # Check for --yes flag
    skip_confirmation = '--yes' in sys.argv or '-y' in sys.argv

    # Show help
    if '--help' in sys.argv or '-h' in sys.argv:
        print(__doc__)
        return 0

    # Run migration
    success = migrate_database(skip_confirmation)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
