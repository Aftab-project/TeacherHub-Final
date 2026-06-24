"""
Reproducible SQLite performance benchmark for Section 7.3.

This script executes the same seven operations in two modes:
- before: no optimization indexes + unpaginated retrieval/search patterns
- after: optimization indexes + paginated retrieval/search patterns

Outputs are written to tests/artifacts/performance/:
- raw_before.json / raw_after.json (all per-iteration timings)
- summary_before.csv / summary_after.csv (operation statistics)
- comparison.csv (before/after summary)
- performance_comparison.png (graph generated from measured data)

Run:
    python tests/performance_test.py
"""

from __future__ import annotations

import csv
import json
import random
import re
import sqlite3
import statistics
import string
import time
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Dict, List

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts" / "performance"


@dataclass
class OperationSpec:
    key: str
    label: str
    iterations: int
    runner: Callable[[sqlite3.Connection, bool, int], None]


def _now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _build_summary(texts: List[str], max_sentences: int = 6) -> str:
    """Extractive summary mirroring the in-app approach (frequency scoring)."""
    full_text = " ".join(texts).strip()
    if not full_text:
        return ""

    sentences = re.split(r"(?<=[.!?])\s+", full_text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 8]
    if not sentences:
        return full_text[:500]

    stopwords = {
        "the", "a", "an", "is", "it", "to", "of", "and", "in", "on", "at", "this", "that",
        "was", "for", "are", "with", "as", "by", "from", "or", "be", "been", "have", "has",
        "he", "she", "they", "we", "you", "i", "my", "me", "him", "her", "his", "their",
        "but", "so", "if", "not", "do", "did", "will", "would", "could", "should", "can",
        "just", "up", "about", "into", "like", "more", "what", "when", "how", "there",
    }
    words = re.findall(r"\b[a-z]{3,}\b", full_text.lower())
    freq = Counter(w for w in words if w not in stopwords)
    if not freq:
        return full_text[:500]

    max_freq = max(freq.values())
    norm = {w: v / max_freq for w, v in freq.items()}

    scored = []
    for sent in sentences:
        tokens = re.findall(r"\b[a-z]{3,}\b", sent.lower())
        score = sum(norm.get(t, 0.0) for t in tokens) / (len(tokens) + 1)
        scored.append((score, sent))

    scored.sort(key=lambda x: -x[0])
    top = {s for _, s in scored[:max_sentences]}
    ordered = [s for s in sentences if s in top]
    return " ".join(ordered)


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA temp_store=MEMORY")
    return conn


def _create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        DROP TABLE IF EXISTS users;
        DROP TABLE IF EXISTS teams;
        DROP TABLE IF EXISTS channels;
        DROP TABLE IF EXISTS calls;
        DROP TABLE IF EXISTS call_transcripts;
        DROP TABLE IF EXISTS messages;
        DROP TABLE IF EXISTS notifications;

        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL,
            email TEXT NOT NULL
        );

        CREATE TABLE teams (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            owner_id INTEGER NOT NULL
        );

        CREATE TABLE channels (
            id INTEGER PRIMARY KEY,
            team_id INTEGER NOT NULL,
            name TEXT NOT NULL
        );

        CREATE TABLE calls (
            id INTEGER PRIMARY KEY,
            team_id INTEGER,
            caller_id INTEGER,
            callee_id INTEGER,
            call_type TEXT NOT NULL,
            status TEXT NOT NULL,
            call_token TEXT NOT NULL,
            created_at TEXT NOT NULL,
            summary TEXT
        );

        CREATE TABLE call_transcripts (
            id INTEGER PRIMARY KEY,
            call_id INTEGER NOT NULL,
            speaker_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            timestamp REAL NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE messages (
            id INTEGER PRIMARY KEY,
            content TEXT NOT NULL,
            channel_id INTEGER NOT NULL,
            sender_id INTEGER NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE notifications (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            title TEXT NOT NULL,
            message TEXT,
            is_read INTEGER NOT NULL,
            created_at TEXT NOT NULL
        );
        """
    )
    conn.commit()


def _create_indexes(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE INDEX IF NOT EXISTS ix_message_channel_created ON messages(channel_id, created_at);
        CREATE INDEX IF NOT EXISTS ix_message_sender_created ON messages(sender_id, created_at);
        CREATE INDEX IF NOT EXISTS ix_call_transcript_timestamp ON call_transcripts(call_id, timestamp);
        CREATE INDEX IF NOT EXISTS ix_call_transcript_speaker ON call_transcripts(speaker_id, created_at);
        CREATE INDEX IF NOT EXISTS ix_notification_user_created ON notifications(user_id, created_at);
        CREATE INDEX IF NOT EXISTS ix_calls_team_created ON calls(team_id, created_at);
        """
    )
    conn.commit()


def _seed_data(conn: sqlite3.Connection, seed: int = 42) -> None:
    random.seed(seed)
    now = datetime.utcnow()

    users = [(i, f"user{i}", f"user{i}@example.test") for i in range(1, 11)]
    conn.executemany("INSERT INTO users(id, username, email) VALUES(?, ?, ?)", users)

    teams = [(1, "Team A", 1), (2, "Team B", 2)]
    conn.executemany("INSERT INTO teams(id, name, owner_id) VALUES(?, ?, ?)", teams)

    channels = [(1, 1, "general"), (2, 1, "announcements"), (3, 2, "general")]
    conn.executemany("INSERT INTO channels(id, team_id, name) VALUES(?, ?, ?)", channels)

    calls = []
    for i in range(1, 61):
        created = (now - timedelta(minutes=i)).isoformat()
        calls.append((
            i,
            1 if i <= 45 else 2,
            (i % 10) + 1,
            ((i + 1) % 10) + 1,
            "1-to-1",
            "completed",
            f"seed-call-{i}",
            created,
            "",
        ))
    conn.executemany(
        """
        INSERT INTO calls(id, team_id, caller_id, callee_id, call_type, status, call_token, created_at, summary)
        VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        calls,
    )

    transcript_rows = []
    for i in range(1, 2001):
        call_id = 1 if i <= 1200 else random.randint(2, 60)
        speaker_id = (i % 10) + 1
        text = f"segment {i}. policy planning and attendance discussion for class operations."
        transcript_rows.append(
            (call_id, speaker_id, text, float(i), (now - timedelta(seconds=i)).isoformat())
        )
    conn.executemany(
        """
        INSERT INTO call_transcripts(call_id, speaker_id, text, timestamp, created_at)
        VALUES(?, ?, ?, ?, ?)
        """,
        transcript_rows,
    )

    vocab = ["lesson", "attendance", "policy", "assignment", "support", "meeting", "followup"]
    message_rows = []
    for i in range(1, 12001):
        token = "policy" if i % 5 == 0 else random.choice(vocab)
        message_rows.append(
            (
                f"message {i} about {token} and communication workflow",
                1 if i % 3 else 2,
                (i % 10) + 1,
                (now - timedelta(seconds=i)).isoformat(),
            )
        )
    conn.executemany(
        "INSERT INTO messages(content, channel_id, sender_id, created_at) VALUES(?, ?, ?, ?)",
        message_rows,
    )

    notification_rows = []
    for i in range(1, 2501):
        notification_rows.append(
            (
                (i % 10) + 1,
                "message",
                f"notification {i}",
                "new update",
                0,
                (now - timedelta(seconds=i)).isoformat(),
            )
        )
    conn.executemany(
        """
        INSERT INTO notifications(user_id, type, title, message, is_read, created_at)
        VALUES(?, ?, ?, ?, ?, ?)
        """,
        notification_rows,
    )

    conn.commit()


def _ms_since(start_ns: int) -> float:
    return (time.perf_counter_ns() - start_ns) / 1_000_000.0


def _op_transcript_insert(conn: sqlite3.Connection, _: bool, iteration: int) -> None:
    now = datetime.utcnow().isoformat()
    conn.execute(
        """
        INSERT INTO call_transcripts(call_id, speaker_id, text, timestamp, created_at)
        VALUES(1, ?, ?, ?, ?)
        """,
        ((iteration % 10) + 1, f"live segment {iteration}", 5000.0 + iteration, now),
    )
    conn.commit()


def _op_transcript_retrieve(conn: sqlite3.Connection, optimized: bool, _: int) -> None:
    if optimized:
        conn.execute(
            """
            SELECT id, speaker_id, text, timestamp
            FROM call_transcripts
            WHERE call_id = 1
            ORDER BY timestamp
            LIMIT 50 OFFSET 0
            """
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT id, speaker_id, text, timestamp
            FROM call_transcripts
            WHERE call_id = 1
            ORDER BY timestamp
            """
        ).fetchall()
        _ = rows[:50]


def _op_message_create(conn: sqlite3.Connection, _: bool, iteration: int) -> None:
    conn.execute(
        "INSERT INTO messages(content, channel_id, sender_id, created_at) VALUES(?, 1, ?, ?)",
        (f"new message {iteration} policy context", (iteration % 10) + 1, datetime.utcnow().isoformat()),
    )
    conn.commit()


def _op_message_search(conn: sqlite3.Connection, optimized: bool, _: int) -> None:
    if optimized:
        conn.execute(
            """
            SELECT id, content, created_at
            FROM messages
            WHERE channel_id = 1 AND content LIKE '%policy%'
            ORDER BY created_at DESC
            LIMIT 20 OFFSET 0
            """
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT id, content, created_at
            FROM messages
            WHERE channel_id = 1 AND content LIKE '%policy%'
            ORDER BY created_at DESC
            """
        ).fetchall()
        _ = rows[:20]


def _op_notification_create(conn: sqlite3.Connection, _: bool, iteration: int) -> None:
    conn.execute(
        """
        INSERT INTO notifications(user_id, type, title, message, is_read, created_at)
        VALUES(?, 'mentioned', ?, ?, 0, ?)
        """,
        ((iteration % 10) + 1, f"note {iteration}", "mention alert", datetime.utcnow().isoformat()),
    )
    conn.commit()


def _op_call_create(conn: sqlite3.Connection, _: bool, iteration: int) -> None:
    token = "bench-" + "".join(random.choices(string.ascii_lowercase + string.digits, k=12))
    conn.execute(
        """
        INSERT INTO calls(team_id, caller_id, callee_id, call_type, status, call_token, created_at, summary)
        VALUES(1, ?, ?, '1-to-1', 'completed', ?, ?, '')
        """,
        ((iteration % 10) + 1, ((iteration + 1) % 10) + 1, token, datetime.utcnow().isoformat()),
    )
    conn.commit()


def _op_summary_generation(conn: sqlite3.Connection, optimized: bool, _: int) -> None:
    if optimized:
        rows = conn.execute(
            """
            SELECT text
            FROM call_transcripts
            WHERE call_id = 1
            ORDER BY timestamp
            LIMIT 300
            """
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT text
            FROM call_transcripts
            WHERE call_id = 1
            ORDER BY timestamp
            """
        ).fetchall()

    summary = _build_summary([r[0] for r in rows])
    conn.execute("UPDATE calls SET summary = ? WHERE id = 1", (summary,))
    conn.commit()


OPERATIONS = [
    OperationSpec("transcript_insertion", "Transcript Insertion", 500, _op_transcript_insert),
    OperationSpec("transcript_retrieval", "Transcript Retrieval", 50, _op_transcript_retrieve),
    OperationSpec("message_creation", "Message Creation", 300, _op_message_create),
    OperationSpec("message_search", "Message Search", 60, _op_message_search),
    OperationSpec("notification_creation", "Notification Creation", 300, _op_notification_create),
    OperationSpec("call_creation", "Call Creation", 120, _op_call_create),
    OperationSpec("summary_generation", "Summary Generation", 40, _op_summary_generation),
]


def _stats(values: List[float]) -> Dict[str, float]:
    std = statistics.pstdev(values) if len(values) > 1 else 0.0
    return {
        "count": len(values),
        "mean_ms": statistics.fmean(values),
        "median_ms": statistics.median(values),
        "min_ms": min(values),
        "max_ms": max(values),
        "std_ms": std,
    }


def run_mode(mode: str) -> Dict[str, Dict[str, object]]:
    optimized = mode == "after"
    db_path = ARTIFACTS_DIR / f"benchmark_{mode}.sqlite"
    if db_path.exists():
        db_path.unlink()

    conn = _connect(db_path)
    _create_schema(conn)
    if optimized:
        _create_indexes(conn)
    _seed_data(conn)

    raw: Dict[str, Dict[str, object]] = {
        "metadata": {
            "mode": mode,
            "optimized": optimized,
            "generated_at_utc": _now_iso(),
            "database": str(db_path),
            "python_random_seed": 42,
        },
        "operations": {},
    }

    print(f"\n[{mode.upper()}] Running benchmark on {db_path}")
    for op in OPERATIONS:
        times: List[float] = []
        for i in range(op.iterations):
            start_ns = time.perf_counter_ns()
            op.runner(conn, optimized, i)
            times.append(_ms_since(start_ns))

        summary = _stats(times)
        raw["operations"][op.key] = {
            "label": op.label,
            "iterations": op.iterations,
            "timings_ms": times,
            "summary": summary,
        }
        print(f"  - {op.label}: {summary['mean_ms']:.3f} ms mean over {op.iterations} runs")

    conn.close()
    return raw


def write_raw_json(mode: str, raw: Dict[str, object]) -> Path:
    out = ARTIFACTS_DIR / f"raw_{mode}.json"
    with out.open("w", encoding="utf-8") as f:
        json.dump(raw, f, indent=2)
    return out


def write_summary_csv(mode: str, raw: Dict[str, object]) -> Path:
    out = ARTIFACTS_DIR / f"summary_{mode}.csv"
    with out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["operation", "label", "count", "mean_ms", "median_ms", "min_ms", "max_ms", "std_ms"])
        for op in OPERATIONS:
            stats = raw["operations"][op.key]["summary"]
            writer.writerow([
                op.key,
                op.label,
                stats["count"],
                f"{stats['mean_ms']:.6f}",
                f"{stats['median_ms']:.6f}",
                f"{stats['min_ms']:.6f}",
                f"{stats['max_ms']:.6f}",
                f"{stats['std_ms']:.6f}",
            ])
    return out


def write_comparison_csv(before: Dict[str, object], after: Dict[str, object]) -> Path:
    out = ARTIFACTS_DIR / "comparison.csv"
    with out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "operation",
            "label",
            "before_mean_ms",
            "after_mean_ms",
            "improvement_percent",
            "before_median_ms",
            "after_median_ms",
        ])
        for op in OPERATIONS:
            b = before["operations"][op.key]["summary"]
            a = after["operations"][op.key]["summary"]
            improvement = ((b["mean_ms"] - a["mean_ms"]) / b["mean_ms"] * 100.0) if b["mean_ms"] else 0.0
            writer.writerow([
                op.key,
                op.label,
                f"{b['mean_ms']:.6f}",
                f"{a['mean_ms']:.6f}",
                f"{improvement:.6f}",
                f"{b['median_ms']:.6f}",
                f"{a['median_ms']:.6f}",
            ])
    return out


def write_comparison_graph(before: Dict[str, object], after: Dict[str, object]) -> Path:
    out = ARTIFACTS_DIR / "performance_comparison.png"

    labels = [op.label for op in OPERATIONS]
    before_means = [before["operations"][op.key]["summary"]["mean_ms"] for op in OPERATIONS]
    after_means = [after["operations"][op.key]["summary"]["mean_ms"] for op in OPERATIONS]
    improvements = [
        ((b - a) / b * 100.0) if b else 0.0
        for b, a in zip(before_means, after_means)
    ]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), dpi=200)

    x = list(range(len(labels)))
    width = 0.38
    ax1.bar([i - width / 2 for i in x], before_means, width=width, label="Before", color="#c0392b")
    ax1.bar([i + width / 2 for i in x], after_means, width=width, label="After", color="#1e8449")
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, rotation=25, ha="right")
    ax1.set_ylabel("Mean time (ms)")
    ax1.set_title("SQLite Benchmark: Before vs After")
    ax1.legend()
    ax1.grid(axis="y", alpha=0.25)

    ax2.barh(labels, improvements, color=["#1e8449" if v >= 0 else "#c0392b" for v in improvements])
    ax2.set_xlabel("Improvement (%)")
    ax2.set_title("Mean-time Improvement")
    ax2.grid(axis="x", alpha=0.25)

    # Avoid layout paths that recurse deeply on some Python 3.14 + matplotlib builds.
    fig.subplots_adjust(left=0.10, right=0.98, top=0.93, bottom=0.12, hspace=0.35)
    fig.savefig(out)
    plt.close(fig)
    return out


def main() -> None:
    _ensure_dir(ARTIFACTS_DIR)

    before = run_mode("before")
    after = run_mode("after")

    raw_before_path = write_raw_json("before", before)
    raw_after_path = write_raw_json("after", after)
    summary_before_path = write_summary_csv("before", before)
    summary_after_path = write_summary_csv("after", after)
    comparison_csv_path = write_comparison_csv(before, after)
    graph_path = write_comparison_graph(before, after)

    print("\nArtifacts generated:")
    for path in [
        raw_before_path,
        raw_after_path,
        summary_before_path,
        summary_after_path,
        comparison_csv_path,
        graph_path,
    ]:
        print(f"  - {path}")


if __name__ == "__main__":
    main()
