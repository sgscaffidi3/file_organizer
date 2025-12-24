# ==============================================================================
# File: report_generator.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 3
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
    "CONSOLIDATION: Merged all previous features into a single comprehensive report."
]
_PATCH_VERSION = len(_CHANGELOG_ENTRIES)
# ------------------------------------------------------------------------------
from pathlib import Path
from typing import Dict, Any, List
import argparse
import datetime
import sys
import json
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

    def get_duplicate_list(self) -> Dict[str, List[str]]:
        query = "SELECT content_hash, COUNT(*) as c FROM FilePathInstances GROUP BY content_hash HAVING c > 1"
        dupes = self.db.execute_query(query)
        report = {}
        for (h, c) in dupes:
            paths = self.db.execute_query("SELECT path FROM FilePathInstances WHERE content_hash = ?", (h,))
            report[h] = [p[0] for p in paths]
        return report

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
        codecs, tiers = {}, {"Lossless (>500k)": 0, "High (256-500k)": 0, "Standard (128-256k)": 0, "Low (<128k)": 0, "Unknown": 0}
        rows = self.db.execute_query("SELECT extended_metadata FROM MediaContent WHERE file_type_group = 'AUDIO'")
        for (m_str,) in rows:
            m = json.loads(m_str)
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

    def print_full_report(self):
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
            print(f"  - Codec {str(c):<12}: {count:>4} files")

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
        total_p = self.db.execute_query("SELECT COUNT(*) FROM FilePathInstances")[0][0]
        unique_a = self.db.execute_query("SELECT COUNT(*) FROM MediaContent")[0][0]
        foot_res = self.db.execute_query("SELECT SUM(m.size) FROM FilePathInstances f JOIN MediaContent m ON f.content_hash = m.content_hash")[0][0] or 0
        uniq_res = self.db.execute_query("SELECT SUM(size) FROM MediaContent")[0][0] or 0
        
        print(f"\n[STORAGE & DEDUPLICATION]")
        print(f"  Unique Assets:   {unique_a:,} ({self._format_size(uniq_res)})")
        print(f"  Redundant Paths: {total_p - unique_a:,} ({self._format_size(foot_res - uniq_res)})")

        dupe_map = self.get_duplicate_list()
        if dupe_map:
            print("\n[DUPLICATE PATH AUDIT]")
            for h, paths in dupe_map.items():
                print(f"  Hash: {h[:16]}...")
                for p in paths: print(f"    - {p}")

        print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--version', action='store_true')
    parser.add_argument('--db', type=str, default="demo/metadata.sqlite")
    args = parser.parse_args()
    if args.version:
        print(f"Report Generator v{_MAJOR_VERSION}.{_MINOR_VERSION}.{_PATCH_VERSION}")
        sys.exit(0)
    db = DatabaseManager(args.db)
    with db:
        ReportGenerator(db).print_full_report()