from bcc import BPF
import sqlite3
from datetime import datetime

DB_PATH = "/home/naroshh/ebpf-lab/events.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)

    # Better performance for frequent writes
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            pid INTEGER,
            process TEXT,
            filename TEXT
        )
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_pid
        ON events(pid)
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_process
        ON events(process)
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_filename
        ON events(filename)
    """)

    conn.commit()
    return conn


program = r"""
#include <uapi/linux/ptrace.h>

BPF_PERF_OUTPUT(events);

struct data_t {
    u32 pid;
    char comm[16];
    char fname[256];
};

TRACEPOINT_PROBE(syscalls, sys_enter_openat) {
    struct data_t data = {};

    data.pid = bpf_get_current_pid_tgid() >> 32;

    bpf_get_current_comm(data.comm, sizeof(data.comm));

    bpf_probe_read_user_str(
        data.fname,
        sizeof(data.fname),
        args->filename
    );

    events.perf_submit(args, &data, sizeof(data));

    return 0;
}
"""


db = init_db()
event_count = 0

b = BPF(text=program)

print("Watching file opens... Ctrl+C to stop\n")


def print_event(cpu, data, size):
    global event_count

    event = b["events"].event(data)

    comm = event.comm.decode("utf-8", errors="replace").rstrip("\x00")
    fname = event.fname.decode("utf-8", errors="replace").rstrip("\x00")

    timestamp = datetime.now().isoformat()

    print(
        f"PID: {event.pid:6} | "
        f"PROC: {comm:16} | "
        f"FILE: {fname}"
    )

    db.execute(
        """
        INSERT INTO events
        (timestamp, pid, process, filename)
        VALUES (?, ?, ?, ?)
        """,
        (timestamp, event.pid, comm, fname)
    )

    event_count += 1

    # Commit every 100 events instead of every event
    if event_count % 100 == 0:
        db.commit()


b["events"].open_perf_buffer(print_event)

try:
    while True:
        b.perf_buffer_poll()

except KeyboardInterrupt:
    print("\nExiting...")

finally:
    db.commit()
    db.close()