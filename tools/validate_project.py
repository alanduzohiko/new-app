#!/usr/bin/env python3
"""Fast, deterministic checks for the Meshkhal Android source and bundled content."""
from __future__ import annotations

import json
import sqlite3
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "app" / "src" / "main" / "assets"


def fail(message: str) -> None:
    print(f"[FAIL] {message}", file=sys.stderr)
    raise SystemExit(1)


def require_file(path: Path) -> None:
    if not path.is_file() or path.stat().st_size == 0:
        fail(f"Required file is missing or empty: {path.relative_to(ROOT)}")


def load_json(path: Path):
    require_file(path)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"Invalid JSON in {path.relative_to(ROOT)}: {exc}")


def main() -> None:
    required = [
        ROOT / "settings.gradle.kts",
        ROOT / "build.gradle.kts",
        ROOT / "app" / "build.gradle.kts",
        ROOT / "app" / "src" / "main" / "AndroidManifest.xml",
        ROOT / "app" / "src" / "main" / "java" / "com" / "meshkhal" / "MainActivity.kt",
        ASSETS / "quran.db",
        ASSETS / "db_hadith.db",
        ASSETS / "prayertimes.db",
        ASSETS / "tafseer_sahih_international.db",
        ASSETS / "tafseeri_noor.db",
        ASSETS / "khira" / "mushaf" / "ayahs.bin",
        ASSETS / "khira" / "mushaf" / "tafsir.bin",
        ASSETS / "khira" / "data" / "surahs.json",
        ASSETS / "khira" / "data" / "athkar.json",
        ASSETS / "khira" / "data" / "duas.json",
        ASSETS / "khira" / "tafsir" / "catalog.json",
    ]
    for path in required:
        require_file(path)
    print(f"[OK] Required project files exist ({len(required)} files).")

    app_gradle = (ROOT / "app" / "build.gradle.kts").read_text(encoding="utf-8")
    if 'applicationId = "com.meshkhal.app"' not in app_gradle:
        fail("Unexpected or missing applicationId; expected com.meshkhal.app")
    if "compileSdk = 35" not in app_gradle:
        fail("Unexpected or missing compileSdk; expected API 35")
    print("[OK] Android application ID and compile SDK are consistent.")

    khira = ASSETS / "khira"
    try:
        ayahs = json.loads(zlib.decompress((khira / "mushaf" / "ayahs.bin").read_bytes()))
        tafsir = json.loads(zlib.decompress((khira / "mushaf" / "tafsir.bin").read_bytes()))
    except Exception as exc:
        fail(f"Could not decompress Quran/Tafsir content: {exc}")
    surahs = load_json(khira / "data" / "surahs.json")
    athkar_doc = load_json(khira / "data" / "athkar.json")
    duas_doc = load_json(khira / "data" / "duas.json")
    catalog = load_json(khira / "tafsir" / "catalog.json")
    if len(ayahs) != 6236:
        fail(f"Expected 6,236 Quran ayahs; found {len(ayahs)}")
    if len(surahs) != 114:
        fail(f"Expected 114 surah records; found {len(surahs)}")
    if not tafsir or not catalog:
        fail("Tafsir data or its catalog is empty")
    if not isinstance(athkar_doc.get("entries"), dict) or not athkar_doc["entries"]:
        fail("Athkar entries are missing")
    if not isinstance(duas_doc.get("entries"), dict) or not duas_doc["entries"]:
        fail("Dua entries are missing")
    print(f"[OK] Offline content: {len(surahs)} surahs, {len(ayahs)} ayahs, {len(tafsir)} tafsir records, {len(athkar_doc['entries'])} athkar entries, {len(duas_doc['entries'])} dua entries, {len(catalog)} tafsir catalog sources.")

    db_files = sorted(ASSETS.rglob("*.db"))
    if not db_files:
        fail("No SQLite .db assets were found")
    for db_path in db_files:
        try:
            uri = f"file:{db_path.resolve().as_posix()}?mode=ro"
            with sqlite3.connect(uri, uri=True, timeout=10) as con:
                result = con.execute("PRAGMA integrity_check").fetchone()
                if not result or result[0] != "ok":
                    fail(f"SQLite integrity check failed for {db_path.relative_to(ROOT)}: {result}")
        except sqlite3.DatabaseError as exc:
            fail(f"Cannot open SQLite database {db_path.relative_to(ROOT)}: {exc}")
    print(f"[OK] SQLite integrity check passed for {len(db_files)} .db assets.")

    with sqlite3.connect(f"file:{(ASSETS / 'quran.db').resolve().as_posix()}?mode=ro", uri=True) as con:
        surah_count = con.execute("SELECT COUNT(*) FROM surah_name").fetchone()[0]
        ayah_count = con.execute("SELECT COUNT(*) FROM quran").fetchone()[0]
    with sqlite3.connect(f"file:{(ASSETS / 'db_hadith.db').resolve().as_posix()}?mode=ro", uri=True) as con:
        hadith_count = con.execute("SELECT COUNT(*) FROM hadiths").fetchone()[0]
    with sqlite3.connect(f"file:{(ASSETS / 'prayertimes.db').resolve().as_posix()}?mode=ro", uri=True) as con:
        prayer_rows = con.execute("SELECT COUNT(*) FROM staticprayertimes").fetchone()[0]
    if surah_count != 114 or ayah_count != 6236:
        fail(f"Quran database counts mismatch: {surah_count} surahs, {ayah_count} ayahs")
    if hadith_count < 1 or prayer_rows < 1:
        fail("Hadith or prayer-time database is empty")
    print(f"[OK] Core database rows: {surah_count} surahs, {ayah_count} Quran verses, {hadith_count} hadith records, {prayer_rows} static prayer-time rows.")
    print("Validation finished successfully. This checks source/content consistency, not runtime behavior on a physical phone.")


if __name__ == "__main__":
    main()
