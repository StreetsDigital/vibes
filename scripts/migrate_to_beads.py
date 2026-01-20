#!/usr/bin/env python3
"""
Migrate Features from SQLite to Git-backed Beads
=================================================

This script migrates existing features from the SQLite database
to the Gastown-style git-backed Beads format.

Usage:
    python scripts/migrate_to_beads.py <project_dir>
    python scripts/migrate_to_beads.py .  # Current directory

What it does:
1. Reads all features from features.db (SQLite)
2. Creates Bead YAML files in .git/beads/
3. Commits each Bead to git for audit trail
4. Creates a backup of the original database

After migration:
- Set VIBES_USE_BEADS=true to use the new backend
- The original features.db is preserved as features.db.backup
"""

import sys
import json
import shutil
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "mcp_server"))

from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.orm import sessionmaker, declarative_base

from gastown_integration import BeadStore, Bead, migrate_feature_to_bead


Base = declarative_base()


class Feature(Base):
    """Feature model matching the SQLite schema."""
    __tablename__ = "features"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    test_cases = Column(Text)
    status = Column(String(50), default="pending")
    priority = Column(Integer, default=0)
    verification_status = Column(String(50), default="pending")
    verification_notes = Column(Text)
    created_at = Column(String(50))
    updated_at = Column(String(50))


def migrate_sqlite_to_beads(project_dir: Path, dry_run: bool = False) -> dict:
    """
    Migrate features from SQLite to Beads.

    Args:
        project_dir: Project directory containing features.db
        dry_run: If True, show what would be migrated without actually doing it

    Returns:
        Migration result dict
    """
    db_path = project_dir / "features.db"

    if not db_path.exists():
        return {
            "success": False,
            "error": f"Database not found: {db_path}",
            "migrated": 0
        }

    # Connect to SQLite
    engine = create_engine(f"sqlite:///{db_path}")
    Session = sessionmaker(bind=engine)
    session = Session()

    # Load all features
    features = session.query(Feature).all()

    if not features:
        return {
            "success": True,
            "message": "No features to migrate",
            "migrated": 0
        }

    print(f"Found {len(features)} features to migrate")

    if dry_run:
        print("\n=== DRY RUN - No changes will be made ===\n")
        for f in features:
            print(f"  [{f.status}] {f.id}: {f.name}")
        return {
            "success": True,
            "dry_run": True,
            "would_migrate": len(features)
        }

    # Initialize Bead store
    bead_store = BeadStore(project_dir, auto_commit=True)

    # Migrate each feature
    migrated = []
    errors = []

    for feature in features:
        try:
            # Convert to dict
            feature_dict = {
                "id": feature.id,
                "name": feature.name,
                "description": feature.description,
                "test_cases": feature.test_cases,
                "status": feature.status,
                "priority": feature.priority,
                "verification_status": feature.verification_status,
                "verification_notes": feature.verification_notes,
                "created_at": feature.created_at,
                "updated_at": feature.updated_at,
            }

            # Migrate to Bead
            bead = migrate_feature_to_bead(feature_dict, bead_store)
            migrated.append({
                "old_id": feature.id,
                "new_id": bead.id,
                "name": bead.name,
                "status": bead.status
            })
            print(f"  ✓ Migrated: {feature.id} -> {bead.id} ({feature.name})")

        except Exception as e:
            errors.append({
                "id": feature.id,
                "name": feature.name,
                "error": str(e)
            })
            print(f"  ✗ Failed: {feature.id} ({feature.name}): {e}")

    session.close()

    # Backup original database
    backup_path = project_dir / "features.db.backup"
    if not backup_path.exists():
        shutil.copy(db_path, backup_path)
        print(f"\nOriginal database backed up to: {backup_path}")

    return {
        "success": len(errors) == 0,
        "migrated": len(migrated),
        "errors": len(errors),
        "beads": migrated,
        "error_details": errors if errors else None,
        "beads_dir": str(bead_store.beads_dir)
    }


def verify_migration(project_dir: Path) -> dict:
    """
    Verify that migration was successful by comparing SQLite and Beads.

    Args:
        project_dir: Project directory

    Returns:
        Verification result dict
    """
    db_path = project_dir / "features.db"

    if not db_path.exists():
        return {"error": "SQLite database not found"}

    # Count SQLite features
    engine = create_engine(f"sqlite:///{db_path}")
    Session = sessionmaker(bind=engine)
    session = Session()
    sqlite_count = session.query(Feature).count()
    sqlite_by_status = {}
    for status in ["pending", "in_progress", "passing", "skipped", "needs_review"]:
        sqlite_by_status[status] = session.query(Feature).filter(Feature.status == status).count()
    session.close()

    # Count Beads
    bead_store = BeadStore(project_dir, auto_commit=False)
    beads = bead_store.load_all()
    bead_count = len(beads)
    beads_by_status = {}
    for bead in beads:
        status = bead.status
        beads_by_status[status] = beads_by_status.get(status, 0) + 1

    return {
        "sqlite": {
            "total": sqlite_count,
            "by_status": sqlite_by_status
        },
        "beads": {
            "total": bead_count,
            "by_status": beads_by_status
        },
        "match": sqlite_count == bead_count,
        "beads_dir": str(bead_store.beads_dir)
    }


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Migrate features from SQLite to git-backed Beads"
    )
    parser.add_argument(
        "project_dir",
        type=str,
        help="Project directory containing features.db"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be migrated without making changes"
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify migration by comparing SQLite and Beads"
    )

    args = parser.parse_args()
    project_dir = Path(args.project_dir).resolve()

    print(f"Project: {project_dir}")
    print(f"Database: {project_dir / 'features.db'}")
    print(f"Beads dir: {project_dir / '.git' / 'beads'}")
    print()

    if args.verify:
        print("=== Verifying Migration ===\n")
        result = verify_migration(project_dir)
        print(json.dumps(result, indent=2))
        if result.get("match"):
            print("\n✓ Migration verified: counts match")
        else:
            print("\n✗ Migration mismatch: counts differ")
    else:
        print("=== Migrating Features to Beads ===\n")
        result = migrate_sqlite_to_beads(project_dir, dry_run=args.dry_run)

        print("\n=== Result ===")
        print(json.dumps(result, indent=2))

        if result.get("success") and not args.dry_run:
            print("\n✓ Migration complete!")
            print("\nTo use the new Beads backend:")
            print("  export VIBES_USE_BEADS=true")
            print("  # Or add to your shell profile")


if __name__ == "__main__":
    main()
