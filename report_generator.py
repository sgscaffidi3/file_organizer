# ==============================================================================
# File: report_generator.py
# ------------------------------------------------------------------------------
_MAJOR_VERSION = 0
_MINOR_VERSION = 6
_CHANGELOG_ENTRIES = [
    "Initial implementation of ReportGenerator class.",
    "Refactored for database-agnostic reporting using DatabaseManager.",
    "Added Video Codec and Resolution (SD/HD/4K) breakdown reports.",
    "Added Space-savings and Duplicate Audit path reporting.",
    "Added Image Megapixel (MP) quality breakdown.",
    "Added Extremes (Largest/Smallest, Longest/Shortest) and Averages.",
    "Added Yearly Timeline distribution.",
    "FIX: Handle 'N/A' or non-integer strings in duration and bitrate.",
    "FEATURE: Added Audio Codec and Bitrate quality tiers.",
    "CONSOLIDATION: Merged all previous features into a single comprehensive report.",
    "UPDATE: Refactored Duplicate Audit to show top 10 largest (with --verbose toggle).",
    "FEATURE: Added Extraction Spot-Check for largest file of each type.",
    "FIX: Corrected get_top_duplicates query to use COUNT(*) instead of non-existent fpi.id.",
    "FIX: Added null-checks for extended_metadata in get_audio_summary to prevent TypeError.",
    "FIX: CLI Version check now exits before attempting to connect to the database (resolves OperationalError).",
    "FIX: Reordered __main__ block to ensure clean version exit without DB errors.",
    "FEATURE: Added 'Visual Duplicates' report using Perceptual Hash matches.",
    "UX: Added TQDM progress bars to Visual Duplicate and Extraction Sample queries to prevent 'stuck' appearance.",
    "PERFORMANCE: Replaced N+1 query loop in 'Visual Duplicates' with a single optimized JOIN for instant results."
]
_PATCH_VERSION = len(_CHANGELOG_ENTRIES)
# Version: 0.6.19
# ------------------------------------------------------------------------------
from pathlib import Path
from typing import Dict, Any, List
from collections import defaultdict
import argparse
import datetime
import sys
import json
from tqdm import tqdm
from database_manager import DatabaseManager

class ReportGenerator:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def _format_size(self, size_bytes: float) -> str:
        if not size_bytes or size_bytes == 0: return "0 B"
        for unit in ['B', 'KiB', 'MiB', 'GiB', 'TiB']:
            if abs(size_bytes) < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PiB"

    def _format_duration(self, seconds: Any) -> str:
        try:
            if seconds is None or str(seconds).strip().upper() == 'N/A':
                return "Unknown"
            return str(datetime.timedelta(seconds=int(float(seconds))))
        except (ValueError, TypeError):
            return "Unknown"

    def get_type_distribution(self) -> List[Dict]:
        query = "SELECT file_type_group, COUNT(*), SUM(size), AVG(size) FROM MediaContent GROUP BY file_type_group"
        rows = self.db.execute_query(query)
        return [{"group": r[0], "count": r[1], "total": r[2], "avg": r[3]} for r in rows]

    def get_yearly_distribution(self) -> List[tuple]:
        return self.db.execute_query("""
            SELECT substr(date_modified, 1, 4) as year, COUNT(*) 
            FROM FilePathInstances GROUP BY year ORDER BY year DESC
        """)

    def get_extremes(self, group: str) -> Dict:
        res = self.db.execute_query("""
            SELECT MIN(size), MAX(size), MIN(duration), MAX(duration)
            FROM MediaContent WHERE file_type_group = ?
        """, (group,))[0]
        return {"min_size": res[0], "max_size": res[1], "min_dur": res[2], "max_dur": res[3]}

    def get_top_duplicates(self, limit: int = None) -> List[Dict]:
        """Finds duplicate groups, sorted by size descending."""
        query = """
            SELECT mc.content_hash, mc.size, COUNT(*) as c 
            FROM MediaContent mc
            JOIN FilePathInstances fpi ON mc.content_hash = fpi.content_hash
            GROUP BY mc.content_hash 
            HAVING c > 1
            ORDER BY mc.size DESC
        """
        if limit:
            query += f" LIMIT {limit}"
        
        dupes = self.db.execute_query(query)
        report = []
        for (h, size, c) in dupes:
            paths = self.db.execute_query("SELECT original_relative_path FROM FilePathInstances WHERE content_hash = ?", (h,))
            report.append({
                "hash": h,
                "size": size,
                "count": c,
                "paths": [p[0] for p in paths]
            })
        return report
        
    def get_visual_duplicates(self) -> List[Dict]:
        """Finds images that look the same (Exact Phash Match) but are different files."""
        print("  > Analyzing visual hashes (Optimized)...")
        
        # Single Query Strategy: Get all files that belong to a hash group with > 1 member
        query = """
        SELECT mc.perceptual_hash, mc.content_hash, mc.size, fpi.original_relative_path 
        FROM MediaContent mc
        JOIN FilePathInstances fpi ON mc.content_hash = fpi.content_hash
        WHERE mc.perceptual_hash IN (
            SELECT perceptual_hash FROM MediaContent 
            WHERE perceptual_hash IS NOT NULL 
            GROUP BY perceptual_hash 
            HAVING COUNT(*) > 1
        ) AND fpi.is_primary = 1
        ORDER BY mc.perceptual_hash
        """
        
        rows = self.db.execute_query(query)
        
        # Group in Python
        grouped = defaultdict(list)
        for phash, chash, size, path in rows:
            grouped[phash].append((chash, size, path))
            
        results = []
        for phash, files in grouped.items():
            results.append({"phash": phash, "count": len(files), "files": files})
            
        return results

    def get_extraction_samples(self) -> List[Dict]:
        """Gets the largest file of each type to spot-check metadata extraction."""
        print("  > Sampling metadata...")
        query = """
            SELECT file_type_group, content_hash, MAX(size), extended_metadata
            FROM MediaContent
            GROUP BY file_type_group
        """
        rows = self.db.execute_query(query)
        samples = []
        for group, h, size, meta_json in tqdm(rows, desc="    Fetching Samples", unit="type", leave=False):
            path_res = self.db.execute_query("SELECT original_relative_path FROM FilePathInstances WHERE content_hash = ? LIMIT 1", (h,))
            try:
                meta_dict = json.loads(meta_json) if meta_json else {}
            except json.JSONDecodeError:
                meta_dict = {"Error": "Corrupt JSON in DB"}

            samples.append({
                "group": group,
                "hash": h,
                "size": size,
                "path": path_res[0][0] if path_res else "Unknown",
                "metadata": meta_dict
            })
        return samples

    def get_video_res_summary(self) -> Dict[str, int]:
        res = {"4K+": 0, "1080p": 0, "720p": 0, "SD": 0}
        rows = self.db.execute_query("SELECT height FROM MediaContent WHERE file_type_group = 'VIDEO'")
        for (h,) in rows:
            if not h or h == 0: continue
            if h >= 2160: res["4K+"] += 1
            elif h >= 1080: res["1080p"] += 1
            elif h >= 720: res["720p"] += 1
            else: res["SD"] += 1
        return res

    def get_image_quality(self) -> Dict[str, int]:
        res = {"Pro (>20MP)": 0, "High (10-20MP)": 0, "Mid (2-10MP)": 0, "Low (<2MP)": 0}
        rows = self.db.execute_query("SELECT width, height FROM MediaContent WHERE file_type_group = 'IMAGE'")
        for w, h in rows:
            if not (w and h): continue
            mp = (w * h) / 1000000
            if mp >= 20: res["Pro (>20MP)"] += 1
            elif mp >= 10: res["High (10-20MP)"] += 1
            elif mp >= 2: res["Mid (2-10MP)"] += 1
            else: res["Low (<2MP)"] += 1
        return res

    def get_audio_summary(self) -> Dict[str, Any]:
        codecs, tiers = {"Unknown": 0}, {"Lossless (>500k)": 0, "High (256-500k)": 0, "Standard (128-256k)": 0, "Low (<128k)": 0, "Unknown": 0}
        rows = self.db.execute_query("SELECT extended_metadata FROM MediaContent WHERE file_type_group = 'AUDIO'")
        for (m_str,) in rows:
            if not m_str: # Check for None or empty string
                continue
            try:
                m = json.loads(m_str)
            except json.JSONDecodeError:
                continue

            c = m.get('Audio_Codec_List') or m.get('Format') or 'Unknown'
            codecs[c] = codecs.get(c, 0) + 1
            br = m.get('Bit_Rate') or m.get('Overall_Bit_Rate')
            try:
                kbps = int(float(br)) / 1000
                if kbps >= 500: tiers["Lossless (>500k)"] += 1
                elif kbps >= 256: tiers["High (256-500k)"] += 1
                elif kbps >= 128: tiers["Standard (128-256k)"] += 1
                else: tiers["Low (<128k)"] += 1
            except: tiers["Unknown"] += 1
        return {"codecs": codecs, "bitrates": tiers}

    def print_full_report(self, verbose_dupes: bool = False):
        print("\n" + "="*80)
        print(f" FULL MEDIA LIBRARY AUDIT (v{_MAJOR_VERSION}.{_MINOR_VERSION}.{_PATCH_VERSION})")
        print(f" Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print("="*80)

        # 1. Distribution & Timeline
        print(f"\n[FILE TYPE DISTRIBUTION]")
        for i in self.get_type_distribution():
            print(f"  {i['group']:<10}: {i['count']:>4} files | Total: {self._format_size(i['total']):>10} | Avg: {self._format_size(i['avg'])}")
        
        print(f"\n[YEARLY TIMELINE]")
        for y, c in self.get_yearly_distribution():
            print(f"  Year {y}: {c:>4} files")

        # 2. Detailed Media Analysis
        print(f"\n[VIDEO ANALYSIS]")
        v_res = self.get_video_res_summary()
        for label, count in v_res.items():
            if count > 0: print(f"  - Resolution {label:<7}: {count:>4} files")
        v_codecs = self.db.execute_query("SELECT video_codec, COUNT(*) FROM MediaContent WHERE file_type_group='VIDEO' GROUP BY video_codec")
        for c, count in v_codecs:
            if c: print(f"  - Codec {str(c):<12}: {count:>4} files")

        print(f"\n[IMAGE ANALYSIS]")
        for label, count in self.get_image_quality().items():
            if count > 0: print(f"  - {label:<15}: {count:>4} files")

        audio = self.get_audio_summary()
        if audio['codecs']:
            print(f"\n[AUDIO ANALYSIS]")
            for label, count in audio['bitrates'].items():
                if count > 0: print(f"  - Bitrate {label:<12}: {count:>4} files")

        # 3. Extremes
        print(f"\n[FILE EXTREMES]")
        for g in ["VIDEO", "IMAGE", "AUDIO"]:
            ext = self.get_extremes(g)
            if ext['max_size']:
                print(f"  {g:<10} Largest: {self._format_size(ext['max_size']):<10} | Smallest: {self._format_size(ext['min_size'])}")
                if g in ["VIDEO", "AUDIO"]:
                    print(f"             Longest: {self._format_duration(ext['max_dur']):<10} | Shortest: {self._format_duration(ext['min_dur'])}")

        # 4. Storage & Duplicates
        unique_a = self.db.execute_query("SELECT COUNT(*) FROM MediaContent")[0][0]
        total_p = self.db.execute_query("SELECT COUNT(*) FROM FilePathInstances")[0][0]
        foot_res = self.db.execute_query("SELECT SUM(m.size) FROM FilePathInstances f JOIN MediaContent m ON f.content_hash = m.content_hash")[0][0] or 0
        uniq_res = self.db.execute_query("SELECT SUM(size) FROM MediaContent")[0][0] or 0
        
        print(f"\n[STORAGE & DEDUPLICATION]")
        print(f"  Unique Assets:   {unique_a:,} ({self._format_size(uniq_res)})")
        print(f"  Redundant Paths: {total_p - unique_a:,} ({self._format_size(foot_res - uniq_res)})")

        limit = None if verbose_dupes else 10
        dupe_list = self.get_top_duplicates(limit=limit)
        
        if dupe_list:
            header = "\n[DUPLICATE PATH AUDIT]" if verbose_dupes else f"\n[DUPLICATE PATH AUDIT - TOP 10 LARGEST]"
            print(header)
            for item in dupe_list:
                print(f"  Hash: {item['hash'][:16]}... | Size: {self._format_size(item['size'])}")
                for p in item['paths']: print(f"    - {p}")
                
        # 5. Visual Duplicates
        print("\n[VISUAL DUPLICATES (Near-Match / Resized)]")
        vis_dupes = self.get_visual_duplicates()
        if vis_dupes:
            for item in vis_dupes[:5]: # Top 5
                print(f"  Perceptual Hash: {item['phash']} (Count: {item['count']})")
                for f in item['files']:
                    print(f"    - {self._format_size(f[1])}: {f[2]}")
        else:
            print("  None found (Note: Run --meta to generate Perceptual Hashes)")

        # 6. Extraction Spot-Check
        print("\n" + "="*80)
        print(f"{'METADATA EXTRACTION SPOT-CHECK (Largest per Group)':^80}")
        print("="*80)
        for sample in self.get_extraction_samples():
            print(f"\n--- Group: {sample['group']} ---")
            print(f"  Path: {sample['path']}")
            print(f"  Size: {self._format_size(sample['size'])}")
            print(f"  JSON Data:")
            print(json.dumps(sample['metadata'], indent=6))

        print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--version', action='store_true')
    parser.add_argument('-vdb', '--verbose', action='store_true', help="Print all duplicates instead of top 10")
    parser.add_argument('--db', type=str, default="demo/metadata.sqlite")
    args = parser.parse_args()
    
    if args.version:
        print(f"Version: {_MAJOR_VERSION}.{_MINOR_VERSION}.{_PATCH_VERSION}")
        sys.exit(0)
        
    db = DatabaseManager(args.db)
    with db:
        ReportGenerator(db).print_full_report(verbose_dupes=args.verbose)