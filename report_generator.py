# ==============================================================================
# File: report_generator.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 6
_CHANGELOG_ENTRIES = [
    "Initial implementation of ReportGenerator class.",
    "Added --db argument to run reports against arbitrary databases.",
    "Updated size formatting to use KiB/MiB/GiB binary scaling.",
    "Added Video Codec and Resolution Breakdown reports.",
    "RESTORED: Space-savings calculations comparing total footprint vs unique assets.",
    "FIX: Restored --version argument handling in CLI."
]
_PATCH_VERSION = len(_CHANGELOG_ENTRIES)
# ------------------------------------------------------------------------------
from pathlib import Path
from typing import Dict, Any, List
import argparse
import datetime
import sys
from database_manager import DatabaseManager

class ReportGenerator:
    """
    Analyzes database content to provide high-level summaries, 
    video-specific metrics, and deduplication space-savings.
    """
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def _format_size(self, size_bytes: int) -> str:
        """Converts bytes to human-readable KiB, MiB, GiB using binary scaling."""
        if not size_bytes: return "0 B"
        if size_bytes < 1024: return f"{size_bytes} B"
        for unit in ['KiB', 'MiB', 'GiB', 'TiB']:
            size_bytes /= 1024.0
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
        return f"{size_bytes:.2f} PiB"

    def get_detailed_stats(self) -> Dict[str, Any]:
        """Calculates core library metrics including space savings."""
        total_footprint_query = """
            SELECT SUM(m.size) 
            FROM FilePathInstances f
            JOIN MediaContent m ON f.content_hash = m.content_hash
        """
        unique_size_query = "SELECT SUM(size) FROM MediaContent"
        path_count = self.db.execute_query("SELECT COUNT(*) FROM FilePathInstances")[0][0]
        unique_count = self.db.execute_query("SELECT COUNT(*) FROM MediaContent")[0][0]

        raw_total_size = self.db.execute_query(total_footprint_query)[0][0] or 0
        raw_unique_size = self.db.execute_query(unique_size_query)[0][0] or 0
        
        saved_bytes = raw_total_size - raw_unique_size
        savings_pct = (saved_bytes / raw_total_size * 100) if raw_total_size > 0 else 0

        return {
            "total_paths": path_count,
            "unique_assets": unique_count,
            "duplicate_count": path_count - unique_count,
            "total_footprint": raw_total_size,
            "unique_size": raw_unique_size,
            "saved_size": saved_bytes,
            "savings_percent": savings_pct
        }

    def get_codec_distribution(self) -> List[tuple]:
        return self.db.execute_query("""
            SELECT video_codec, COUNT(*), SUM(size) 
            FROM MediaContent 
            WHERE file_type_group = 'VIDEO' 
            GROUP BY video_codec 
            ORDER BY COUNT(*) DESC
        """)

    def get_resolution_breakdown(self) -> Dict[str, int]:
        res = {"4K+": 0, "1080p": 0, "720p": 0, "SD": 0, "Unknown": 0}
        rows = self.db.execute_query("SELECT height FROM MediaContent WHERE file_type_group = 'VIDEO'")
        for (h,) in rows:
            if not h: res["Unknown"] += 1
            elif h >= 2160: res["4K+"] += 1
            elif h >= 1080: res["1080p"] += 1
            elif h >= 720: res["720p"] += 1
            else: res["SD"] += 1
        return res

    def print_full_report(self):
        stats = self.get_detailed_stats()
        
        print("\n" + "="*60)
        print(f" MEDIA LIBRARY ANALYSIS & SPACE SAVINGS")
        print(f" Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print("="*60)

        print(f"\n[DEDUPLICATION SUMMARY]")
        print(f"  Total Files Scanned:   {stats['total_paths']:,}")
        print(f"  Unique Media Assets:   {stats['unique_assets']:,}")
        print(f"  Duplicate Instances:   {stats['duplicate_count']:,}")
        
        print(f"\n[STORAGE IMPACT]")
        print(f"  Current Footprint:     {self._format_size(stats['total_footprint'])}")
        print(f"  Unique Library Size:   {self._format_size(stats['unique_size'])}")
        print(f"  RECLAIMABLE SPACE:     {self._format_size(stats['saved_size'])} ({stats['savings_percent']:.1f}%)")

        print(f"\n[VIDEO CODEC DISTRIBUTION]")
        codecs = self.get_codec_distribution()
        if codecs:
            for name, count, size in codecs:
                print(f"  {str(name):<15}: {count:>4} files ({self._format_size(size or 0)})")
        else:
            print("  No video data found.")

        print(f"\n[RESOLUTION BREAKDOWN]")
        res = self.get_resolution_breakdown()
        for label, count in res.items():
            if count > 0:
                print(f"  {label:<10}: {count:>4} files")
        
        print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generates statistical library reports.")
    parser.add_argument('-v', '--version', action='store_true', help='Show version info.')
    parser.add_argument('--report', action='store_true', default=True, help='Generate and print summary report.')
    parser.add_argument('--db', type=str, default="demo/metadata.sqlite", help="Path to SQLite database")
    args = parser.parse_args()

    if args.version:
        print(f"Report Generator v{_MAJOR_VERSION}.{_MINOR_VERSION}.{_PATCH_VERSION}")
        sys.exit(0)

    if not Path(args.db).exists():
        print(f"Error: Database file not found at {args.db}")
        sys.exit(1)

    db = DatabaseManager(args.db)
    with db:
        ReportGenerator(db).print_full_report()