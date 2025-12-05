#!/usr/bin/env python3
"""
Automated database backup script for PostgreSQL.

Supports local backups and cloud storage (S3, GCS).
"""

import os
import sys
import logging
import subprocess
import gzip
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DatabaseBackup:
    """Automated database backup manager."""
    
    def __init__(
        self,
        connection_string: Optional[str] = None,
        backup_dir: str = "backups",
        retention_days: int = 7,
        compress: bool = True
    ):
        """
        Initialize backup manager.
        
        Args:
            connection_string: PostgreSQL connection string
            backup_dir: Directory to store backups
            retention_days: Number of days to retain backups
            compress: Whether to compress backups with gzip
        """
        self.connection_string = connection_string or os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:postgres@localhost:5432/rag_brain"
        )
        self.backup_dir = Path(backup_dir)
        self.retention_days = retention_days
        self.compress = compress
        
        # Parse connection string
        self._parse_connection_string()
        
        # Create backup directory if it doesn't exist
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def _parse_connection_string(self):
        """Parse PostgreSQL connection string."""
        from urllib.parse import urlparse, parse_qs
        
        parsed = urlparse(self.connection_string)
        self.db_host = parsed.hostname
        self.db_port = parsed.port or 5432
        self.db_user = parsed.username
        self.db_password = parsed.password
        self.db_name = parsed.path.lstrip('/')
        
        # Parse query parameters
        query_params = parse_qs(parsed.query)
        self.sslmode = query_params.get('sslmode', ['prefer'])[0]
    
    def create_backup(self, backup_type: str = "full") -> str:
        """
        Create a database backup.
        
        Args:
            backup_type: Type of backup (full, schema_only, data_only)
            
        Returns:
            Path to the backup file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{self.db_name}_{backup_type}_{timestamp}"
        
        if self.compress:
            backup_file = self.backup_dir / f"{backup_name}.sql.gz"
        else:
            backup_file = self.backup_dir / f"{backup_name}.sql"
        
        logger.info(f"Creating {backup_type} backup: {backup_file}")
        
        # Build pg_dump command
        pg_dump_cmd = [
            "pg_dump",
            "-h", str(self.db_host),
            "-p", str(self.db_port),
            "-U", str(self.db_user),
            "-d", str(self.db_name),
            "--verbose",
            "--no-password",
        ]
        
        # Add backup type specific flags
        if backup_type == "schema_only":
            pg_dump_cmd.append("--schema-only")
        elif backup_type == "data_only":
            pg_dump_cmd.append("--data-only")
        elif backup_type == "full":
            # Include everything
            pg_dump_cmd.extend(["--create", "--clean", "--if-exists"])
        
        # Set environment for password
        env = os.environ.copy()
        env["PGPASSWORD"] = str(self.db_password) if self.db_password else ""
        
        try:
            if self.compress:
                # Pipe through gzip
                with gzip.open(backup_file, "wb") as gz_file:
                    process = subprocess.Popen(
                        pg_dump_cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        env=env
                    )
                    
                    # Stream output to gzip file
                    for chunk in iter(lambda: process.stdout.read(8192), b''):
                        gz_file.write(chunk)
                    
                    # Wait for process to complete
                    returncode = process.wait()
                    
                    if returncode != 0:
                        stderr = process.stderr.read().decode()
                        raise RuntimeError(f"pg_dump failed: {stderr}")
            else:
                # Direct output to file
                with open(backup_file, "w") as sql_file:
                    result = subprocess.run(
                        pg_dump_cmd,
                        stdout=sql_file,
                        stderr=subprocess.PIPE,
                        env=env,
                        check=True
                    )
            
            # Get file size
            file_size = backup_file.stat().st_size
            logger.info(f"Backup completed: {backup_file} ({self._format_size(file_size)})")
            
            return str(backup_file)
        
        except subprocess.CalledProcessError as e:
            logger.error(f"Backup failed: {e.stderr.decode() if e.stderr else str(e)}")
            # Clean up partial backup
            if backup_file.exists():
                backup_file.unlink()
            raise
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            # Clean up partial backup
            if backup_file.exists():
                backup_file.unlink()
            raise
    
    def restore_backup(self, backup_file: str, target_db: Optional[str] = None):
        """
        Restore a database backup.
        
        Args:
            backup_file: Path to the backup file
            target_db: Target database name (uses original if None)
        """
        backup_path = Path(backup_file)
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_file}")
        
        target_db = target_db or self.db_name
        logger.info(f"Restoring backup to database: {target_db}")
        
        # Build psql command
        psql_cmd = [
            "psql",
            "-h", str(self.db_host),
            "-p", str(self.db_port),
            "-U", str(self.db_user),
            "-d", target_db,
            "--no-password",
        ]
        
        # Set environment for password
        env = os.environ.copy()
        env["PGPASSWORD"] = str(self.db_password) if self.db_password else ""
        
        try:
            if backup_path.suffix == ".gz":
                # Decompress and restore
                with gzip.open(backup_path, "rb") as gz_file:
                    process = subprocess.Popen(
                        psql_cmd,
                        stdin=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        env=env
                    )
                    
                    # Stream decompressed data to psql
                    for chunk in iter(lambda: gz_file.read(8192), b''):
                        process.stdin.write(chunk)
                    
                    process.stdin.close()
                    returncode = process.wait()
                    
                    if returncode != 0:
                        stderr = process.stderr.read().decode()
                        raise RuntimeError(f"psql failed: {stderr}")
            else:
                # Direct restore from SQL file
                with open(backup_path, "r") as sql_file:
                    result = subprocess.run(
                        psql_cmd,
                        stdin=sql_file,
                        stderr=subprocess.PIPE,
                        env=env,
                        check=True
                    )
            
            logger.info(f"Restore completed successfully")
        
        except subprocess.CalledProcessError as e:
            logger.error(f"Restore failed: {e.stderr.decode() if e.stderr else str(e)}")
            raise
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            raise
    
    def cleanup_old_backups(self):
        """Remove backups older than retention period."""
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)
        
        logger.info(f"Cleaning up backups older than {cutoff_date.date()}")
        
        removed_count = 0
        removed_size = 0
        
        for backup_file in self.backup_dir.glob("*.sql*"):
            # Get file modification time
            mtime = datetime.fromtimestamp(backup_file.stat().st_mtime)
            
            if mtime < cutoff_date:
                file_size = backup_file.stat().st_size
                logger.info(f"Removing old backup: {backup_file.name}")
                backup_file.unlink()
                removed_count += 1
                removed_size += file_size
        
        if removed_count > 0:
            logger.info(f"Removed {removed_count} old backups ({self._format_size(removed_size)})")
        else:
            logger.info("No old backups to remove")
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """List available backups."""
        backups = []
        
        for backup_file in sorted(self.backup_dir.glob("*.sql*"), reverse=True):
            stat = backup_file.stat()
            backups.append({
                "name": backup_file.name,
                "path": str(backup_file),
                "size": stat.st_size,
                "size_formatted": self._format_size(stat.st_size),
                "created": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "compressed": backup_file.suffix == ".gz"
            })
        
        return backups
    
    def upload_to_s3(self, backup_file: str, s3_bucket: str, s3_key: Optional[str] = None):
        """
        Upload backup to Amazon S3.
        
        Args:
            backup_file: Path to backup file
            s3_bucket: S3 bucket name
            s3_key: S3 key (uses filename if None)
        """
        try:
            import boto3
        except ImportError:
            logger.error("boto3 not installed. Run: pip install boto3")
            raise
        
        backup_path = Path(backup_file)
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_file}")
        
        s3_key = s3_key or f"database-backups/{backup_path.name}"
        
        logger.info(f"Uploading backup to S3: s3://{s3_bucket}/{s3_key}")
        
        s3_client = boto3.client('s3')
        
        try:
            with open(backup_path, 'rb') as f:
                s3_client.upload_fileobj(f, s3_bucket, s3_key)
            logger.info("Upload completed successfully")
        except Exception as e:
            logger.error(f"S3 upload failed: {e}")
            raise
    
    def _format_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"


def main():
    """Main entry point for CLI."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Database backup utility")
    parser.add_argument(
        "action",
        choices=["backup", "restore", "list", "cleanup", "schedule"],
        help="Action to perform"
    )
    parser.add_argument(
        "--type",
        choices=["full", "schema_only", "data_only"],
        default="full",
        help="Backup type (default: full)"
    )
    parser.add_argument(
        "--file",
        help="Backup file for restore"
    )
    parser.add_argument(
        "--backup-dir",
        default="backups",
        help="Backup directory (default: backups)"
    )
    parser.add_argument(
        "--retention-days",
        type=int,
        default=7,
        help="Days to retain backups (default: 7)"
    )
    parser.add_argument(
        "--compress",
        action="store_true",
        default=True,
        help="Compress backups with gzip (default: true)"
    )
    parser.add_argument(
        "--no-compress",
        action="store_true",
        help="Don't compress backups"
    )
    parser.add_argument(
        "--s3-bucket",
        help="Upload backup to S3 bucket"
    )
    parser.add_argument(
        "--database-url",
        help="Database URL (overrides environment)"
    )
    
    args = parser.parse_args()
    
    # Initialize backup manager
    backup_manager = DatabaseBackup(
        connection_string=args.database_url,
        backup_dir=args.backup_dir,
        retention_days=args.retention_days,
        compress=not args.no_compress
    )
    
    try:
        if args.action == "backup":
            backup_file = backup_manager.create_backup(args.type)
            
            # Upload to S3 if specified
            if args.s3_bucket:
                backup_manager.upload_to_s3(backup_file, args.s3_bucket)
            
            # Clean up old backups
            backup_manager.cleanup_old_backups()
        
        elif args.action == "restore":
            if not args.file:
                logger.error("--file required for restore")
                sys.exit(1)
            backup_manager.restore_backup(args.file)
        
        elif args.action == "list":
            backups = backup_manager.list_backups()
            if not backups:
                print("No backups found")
            else:
                print(f"Found {len(backups)} backup(s):")
                for backup in backups:
                    print(f"  - {backup['name']} ({backup['size_formatted']}, {backup['created']})")
        
        elif args.action == "cleanup":
            backup_manager.cleanup_old_backups()
        
        elif args.action == "schedule":
            print("To schedule automated backups, add to crontab:")
            print(f"0 2 * * * {sys.executable} {__file__} backup --type full")
            print(f"0 */6 * * * {sys.executable} {__file__} backup --type data_only")
    
    except Exception as e:
        logger.error(f"Operation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()


