import streamlit as st
import pandas as pd
import sqlite3
import json
import hashlib
import os
import secrets
import uuid
import mimetypes
from pathlib import Path
from datetime import datetime, date


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="Electronic JV",
    page_icon="📘",
    layout="wide"
)


# =========================================================
# DEMO USERS
# =========================================================

DEMO_USERS = {
    "1001": {
        "password": "prep123",
        "name": "Demo Preparer",
        "role": "PREPARER"
    },
    "2001": {
        "password": "approve123",
        "name": "Demo Assistant Manager",
        "role": "APPROVER"
    },
    "9001": {
        "password": "audit123",
        "name": "Demo Auditor",
        "role": "AUDITOR"
    },
    "8001": {
        "password": "admin123",
        "name": "Demo Admin",
        "role": "ADMIN"
    }
}


# =========================================================
# G/L MASTER
# =========================================================

GL_MASTER = {
    "3101/003": {
        "description": "Cash at Bank - MBB",
        "category": "Asset"
    },
    "3102/003": {
        "description": "Repo - MBB",
        "category": "Investment"
    },
    "3102/006": {
        "description": "Short-term Investment - AmIncome",
        "category": "Investment"
    },
    "3103/000": {
        "description": "Repo - MBB",
        "category": "Investment"
    },
    "8005/001": {
        "description": "Interest Income - REPO MBB",
        "category": "Income"
    },
    "8005/008": {
        "description": "Interest Income - AmIncome",
        "category": "Income"
    },
    "4100/001": {
        "description": "Payroll Expense",
        "category": "Expense"
    },
    "4200/001": {
        "description": "Depreciation Expense",
        "category": "Expense"
    },
    "2200/001": {
        "description": "Accrued Expenses",
        "category": "Liability"
    },
    "4300/001": {
        "description": "Bank Charges",
        "category": "Expense"
    }
}


GL_OPTIONS = [
    f"{code} - {details['description']}"
    for code, details in GL_MASTER.items()
]


# =========================================================
# DATABASE
# =========================================================

DB_FILE = "ejv_demo.db"

# Prototype attachment storage.
# On Streamlit Community Cloud this local folder is NOT guaranteed permanent.
ATTACHMENT_ROOT = Path("attachment_store")
ATTACHMENT_ROOT.mkdir(parents=True, exist_ok=True)


def get_connection():
    return sqlite3.connect(
        DB_FILE,
        check_same_thread=False
    )


def initialise_database():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jv_headers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            jv_number TEXT UNIQUE NOT NULL,
            jv_type TEXT NOT NULL,
            accounting_period TEXT NOT NULL,
            remarks TEXT,
            status TEXT NOT NULL,
            total_debit REAL NOT NULL,
            total_credit REAL NOT NULL,
            prepared_by TEXT NOT NULL,
            prepared_name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            submitted_at TEXT,
            approved_by TEXT,
            approved_name TEXT,
            approved_at TEXT,
            reviewer_comments TEXT,
            posted_by TEXT,
            posted_at TEXT,
            attachment_names TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jv_lines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            jv_id INTEGER NOT NULL,
            line_no INTEGER NOT NULL,
            line_date TEXT NOT NULL,
            gl_code TEXT NOT NULL,
            gl_description TEXT,
            description TEXT NOT NULL,
            debit REAL NOT NULL DEFAULT 0,
            credit REAL NOT NULL DEFAULT 0,
            FOREIGN KEY(jv_id) REFERENCES jv_headers(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            jv_id INTEGER,
            jv_number TEXT,
            event_type TEXT NOT NULL,
            employee_no TEXT NOT NULL,
            employee_name TEXT NOT NULL,
            role TEXT NOT NULL,
            comments TEXT,
            event_timestamp TEXT NOT NULL
        )
    """)

    # Internal revision snapshots are retained for control purposes.
    # They are NOT displayed to the Auditor / Guest role.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jv_revisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            jv_id INTEGER NOT NULL,
            revision_no INTEGER NOT NULL,
            snapshot_json TEXT NOT NULL,
            created_by TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(jv_id) REFERENCES jv_headers(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS accounting_periods (
            entity TEXT NOT NULL,
            accounting_period TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'OPEN',
            updated_by TEXT,
            updated_at TEXT,
            PRIMARY KEY (entity, accounting_period)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS period_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity TEXT NOT NULL,
            accounting_period TEXT NOT NULL,
            old_status TEXT,
            new_status TEXT NOT NULL,
            changed_by TEXT NOT NULL,
            changed_name TEXT NOT NULL,
            changed_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            employee_no TEXT PRIMARY KEY,
            employee_name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            role TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'ACTIVE',
            entity TEXT NOT NULL DEFAULT 'JKPSD',
            created_at TEXT NOT NULL,
            created_by TEXT,
            deactivated_at TEXT,
            deactivated_by TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pic_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            requested_by TEXT NOT NULL,
            requested_by_name TEXT NOT NULL,
            new_employee_no TEXT NOT NULL,
            new_employee_name TEXT NOT NULL,
            requested_role TEXT NOT NULL,
            effective_date TEXT NOT NULL,
            reason TEXT NOT NULL,
            comments TEXT,
            status TEXT NOT NULL DEFAULT 'PENDING',
            requested_at TEXT NOT NULL,
            reviewed_by TEXT,
            reviewed_by_name TEXT,
            reviewed_at TEXT,
            review_comments TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jv_attachments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            jv_id INTEGER NOT NULL,
            jv_number TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            stored_filename TEXT NOT NULL,
            stored_path TEXT NOT NULL,
            mime_type TEXT,
            file_size INTEGER NOT NULL,
            sha256_hash TEXT NOT NULL,
            revision_no INTEGER NOT NULL DEFAULT 1,
            uploaded_by TEXT NOT NULL,
            uploaded_name TEXT NOT NULL,
            uploaded_at TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY(jv_id) REFERENCES jv_headers(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recipient_employee_no TEXT NOT NULL,
            jv_id INTEGER,
            jv_number TEXT,
            notification_type TEXT NOT NULL,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            is_read INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            read_at TEXT,
            FOREIGN KEY(jv_id) REFERENCES jv_headers(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gl_master (
            gl_code TEXT PRIMARY KEY,
            gl_description TEXT NOT NULL,
            account_category TEXT NOT NULL,
            normal_balance TEXT,
            status TEXT NOT NULL DEFAULT 'ACTIVE',
            effective_date TEXT,
            entity TEXT NOT NULL DEFAULT 'JKPSD',
            cost_centre_required INTEGER NOT NULL DEFAULT 0,
            validation_notes TEXT,
            created_by TEXT,
            created_at TEXT NOT NULL,
            updated_by TEXT,
            updated_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gl_master_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gl_code TEXT NOT NULL,
            action TEXT NOT NULL,
            snapshot_json TEXT NOT NULL,
            changed_by TEXT NOT NULL,
            changed_name TEXT NOT NULL,
            changed_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jv_type_master (
            jv_type TEXT PRIMARY KEY,
            status TEXT NOT NULL DEFAULT 'ACTIVE',
            attachment_rule TEXT NOT NULL DEFAULT 'OPTIONAL',
            supporting_document_notes TEXT,
            entity TEXT NOT NULL DEFAULT 'JKPSD',
            created_by TEXT,
            created_at TEXT NOT NULL,
            updated_by TEXT,
            updated_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jv_type_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            jv_type TEXT NOT NULL,
            action TEXT NOT NULL,
            snapshot_json TEXT NOT NULL,
            changed_by TEXT NOT NULL,
            changed_name TEXT NOT NULL,
            changed_at TEXT NOT NULL
        )
    """)

    # Safe migration for databases created by an earlier prototype version.
    header_columns = [
        row[1]
        for row in cursor.execute("PRAGMA table_info(jv_headers)").fetchall()
    ]

    if "revision_no" not in header_columns:
        cursor.execute(
            "ALTER TABLE jv_headers ADD COLUMN revision_no INTEGER NOT NULL DEFAULT 1"
        )

    conn.commit()
    conn.close()


initialise_database()


# =========================================================
# HELPERS
# =========================================================


def hash_password(password, salt=None):
    if salt is None:
        salt = os.urandom(16).hex()
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt),
        200_000
    ).hex()
    return digest, salt


def verify_password(password, stored_hash, salt):
    check_hash, _ = hash_password(password, salt)
    return secrets.compare_digest(check_hash, stored_hash)


def seed_demo_users():
    conn = get_connection()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for employee_no, details in DEMO_USERS.items():
        exists = conn.execute(
            "SELECT 1 FROM users WHERE employee_no = ?",
            (employee_no,)
        ).fetchone()
        if exists:
            continue
        password_hash, salt = hash_password(details["password"])
        conn.execute("""
            INSERT INTO users (
                employee_no, employee_name, password_hash, salt,
                role, status, entity, created_at, created_by
            )
            VALUES (?, ?, ?, ?, ?, 'ACTIVE', 'JKPSD', ?, 'SYSTEM')
        """, (
            employee_no,
            details["name"],
            password_hash,
            salt,
            details["role"],
            now
        ))
    conn.commit()
    conn.close()


def get_user(employee_no):
    conn = get_connection()
    row = conn.execute("""
        SELECT
            employee_no, employee_name, password_hash, salt,
            role, status, entity
        FROM users
        WHERE employee_no = ?
    """, (employee_no,)).fetchone()
    conn.close()
    return row


def create_user_account(employee_no, employee_name, role, temporary_password, created_by):
    role = role.upper()
    if role not in ("PREPARER", "APPROVER", "AUDITOR", "ADMIN"):
        raise ValueError("Invalid user role.")
    if not employee_no.strip():
        raise ValueError("Employee Number is required.")
    if not employee_name.strip():
        raise ValueError("Employee Name is required.")
    if len(temporary_password) < 8:
        raise ValueError("Temporary password must contain at least 8 characters.")

    conn = get_connection()
    exists = conn.execute(
        "SELECT 1 FROM users WHERE employee_no = ?",
        (employee_no.strip(),)
    ).fetchone()

    if exists:
        conn.close()
        raise ValueError("Employee Number already exists.")

    password_hash, salt = hash_password(temporary_password)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn.execute("""
        INSERT INTO users (
            employee_no, employee_name, password_hash, salt,
            role, status, entity, created_at, created_by
        )
        VALUES (?, ?, ?, ?, ?, 'ACTIVE', 'JKPSD', ?, ?)
    """, (
        employee_no.strip(),
        employee_name.strip(),
        password_hash,
        salt,
        role,
        now,
        created_by
    ))
    conn.commit()
    conn.close()


def set_user_status(employee_no, new_status, changed_by):
    new_status = new_status.upper()
    if new_status not in ("ACTIVE", "INACTIVE"):
        raise ValueError("Invalid user status.")
    if employee_no == changed_by and new_status == "INACTIVE":
        raise PermissionError("Admin cannot deactivate their own active account.")

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection()

    if new_status == "ACTIVE":
        conn.execute("""
            UPDATE users
            SET status = 'ACTIVE',
                deactivated_at = NULL,
                deactivated_by = NULL
            WHERE employee_no = ?
        """, (employee_no,))
    else:
        conn.execute("""
            UPDATE users
            SET status = 'INACTIVE',
                deactivated_at = ?,
                deactivated_by = ?
            WHERE employee_no = ?
        """, (now, changed_by, employee_no))

    conn.commit()
    conn.close()



def safe_extension(filename):
    suffix = Path(filename).suffix.lower()
    if len(suffix) > 10:
        return ""
    return suffix


def store_uploaded_files(
    jv_id,
    jv_number,
    uploaded_files,
    revision_no,
    employee_no,
    employee_name
):
    """Save uploaded file bytes and register controlled metadata."""
    if not uploaded_files:
        return []

    jv_folder = ATTACHMENT_ROOT / jv_number
    jv_folder.mkdir(parents=True, exist_ok=True)

    saved_names = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_connection()

    for uploaded_file in uploaded_files:
        original_name = Path(uploaded_file.name).name
        file_bytes = uploaded_file.getvalue()

        if not file_bytes:
            continue

        # A replacement with the same visible filename becomes the active copy.
        conn.execute("""
            UPDATE jv_attachments
            SET is_active = 0
            WHERE jv_id = ?
            AND original_filename = ?
            AND is_active = 1
        """, (
            jv_id,
            original_name
        ))

        stored_filename = (
            f"{uuid.uuid4().hex}"
            f"{safe_extension(original_name)}"
        )

        stored_path = jv_folder / stored_filename
        stored_path.write_bytes(file_bytes)

        sha256_hash = hashlib.sha256(file_bytes).hexdigest()

        mime_type = (
            getattr(uploaded_file, "type", None)
            or mimetypes.guess_type(original_name)[0]
            or "application/octet-stream"
        )

        conn.execute("""
            INSERT INTO jv_attachments (
                jv_id,
                jv_number,
                original_filename,
                stored_filename,
                stored_path,
                mime_type,
                file_size,
                sha256_hash,
                revision_no,
                uploaded_by,
                uploaded_name,
                uploaded_at,
                is_active
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        """, (
            jv_id,
            jv_number,
            original_name,
            stored_filename,
            str(stored_path),
            mime_type,
            len(file_bytes),
            sha256_hash,
            int(revision_no or 1),
            employee_no,
            employee_name,
            now
        ))

        saved_names.append(original_name)

    conn.commit()
    conn.close()

    return saved_names


def get_active_attachments(jv_id):
    conn = get_connection()

    rows = conn.execute("""
        SELECT
            id,
            original_filename,
            stored_path,
            mime_type,
            file_size,
            sha256_hash,
            revision_no,
            uploaded_by,
            uploaded_name,
            uploaded_at
        FROM jv_attachments
        WHERE jv_id = ?
        AND is_active = 1
        ORDER BY id
    """, (
        jv_id,
    )).fetchall()

    conn.close()
    return rows


def format_file_size(file_size):
    file_size = int(file_size or 0)

    if file_size < 1024:
        return f"{file_size} B"

    if file_size < 1024 * 1024:
        return f"{file_size / 1024:,.1f} KB"

    return f"{file_size / (1024 * 1024):,.1f} MB"


def render_attachments(jv_id, status, legacy_attachment_names=None):
    """Render only the current active supporting documents."""
    attachments = get_active_attachments(jv_id)

    # Auditor/Guest should only receive final/latest supporting documents.
    if role == "AUDITOR" and status not in ("APPROVED", "POSTED TO UBS"):
        return

    st.divider()
    st.subheader("Supporting Documents")

    if not attachments:
        # Existing prototype JVs may pre-date real attachment storage.
        try:
            legacy_names = json.loads(legacy_attachment_names or "[]")
        except:
            legacy_names = []

        if legacy_names:
            st.warning(
                "These files were uploaded before document storage was enabled. "
                "Only the filenames were retained in the earlier prototype."
            )
            for name in legacy_names:
                st.write(f"• {name}")
        else:
            st.caption("No supporting documents attached.")
        return

    for attachment in attachments:
        (
            attachment_id,
            original_filename,
            stored_path,
            mime_type,
            file_size,
            sha256_hash,
            revision_no,
            uploaded_by,
            uploaded_name,
            uploaded_at
        ) = attachment

        c1, c2 = st.columns([4, 1])

        with c1:
            st.write(f"**{original_filename}**")
            st.caption(
                f"{format_file_size(file_size)} | "
                f"Uploaded by {uploaded_name} ({uploaded_by}) | "
                f"{display_datetime(uploaded_at)}"
            )

            # Hide revision detail from Auditor to keep Guest view simple.
            if role != "AUDITOR":
                st.caption(
                    f"Revision {revision_no} | "
                    f"SHA-256: {sha256_hash[:16]}..."
                )

        with c2:
            path = Path(stored_path)

            if path.exists():
                st.download_button(
                    "Open / Download",
                    data=path.read_bytes(),
                    file_name=original_filename,
                    mime=mime_type or "application/octet-stream",
                    key=f"download_attachment_{attachment_id}",
                    use_container_width=True
                )
            else:
                st.error("File unavailable")


def add_notification(
    recipient_employee_no,
    title,
    message,
    notification_type,
    jv_id=None,
    jv_number=None
):
    conn = get_connection()

    conn.execute("""
        INSERT INTO notifications (
            recipient_employee_no,
            jv_id,
            jv_number,
            notification_type,
            title,
            message,
            is_read,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, 0, ?)
    """, (
        recipient_employee_no,
        jv_id,
        jv_number,
        notification_type,
        title,
        message,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()


def notify_active_role(
    role_name,
    title,
    message,
    notification_type,
    jv_id=None,
    jv_number=None,
    exclude_employee_no=None
):
    conn = get_connection()

    rows = conn.execute("""
        SELECT employee_no
        FROM users
        WHERE role = ?
        AND status = 'ACTIVE'
    """, (
        role_name,
    )).fetchall()

    conn.close()

    for row in rows:
        recipient = row[0]

        if exclude_employee_no and recipient == exclude_employee_no:
            continue

        add_notification(
            recipient,
            title,
            message,
            notification_type,
            jv_id,
            jv_number
        )


def unread_notification_count(employee_no):
    conn = get_connection()

    count = conn.execute("""
        SELECT COUNT(*)
        FROM notifications
        WHERE recipient_employee_no = ?
        AND is_read = 0
    """, (
        employee_no,
    )).fetchone()[0]

    conn.close()
    return count


def mark_notification_read(notification_id, employee_no):
    conn = get_connection()

    conn.execute("""
        UPDATE notifications
        SET
            is_read = 1,
            read_at = ?
        WHERE id = ?
        AND recipient_employee_no = ?
    """, (
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        notification_id,
        employee_no
    ))

    conn.commit()
    conn.close()


def mark_all_notifications_read(employee_no):
    conn = get_connection()

    conn.execute("""
        UPDATE notifications
        SET
            is_read = 1,
            read_at = ?
        WHERE recipient_employee_no = ?
        AND is_read = 0
    """, (
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        employee_no
    ))

    conn.commit()
    conn.close()



def seed_gl_master():
    """Seed current prototype G/Ls only when the database master is empty."""
    conn = get_connection()

    count = conn.execute(
        "SELECT COUNT(*) FROM gl_master"
    ).fetchone()[0]

    if count == 0:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for code, details in GL_MASTER.items():
            category = details.get("category", "Other")

            normal_balance = (
                "DEBIT"
                if category in ("Asset", "Expense", "Investment")
                else "CREDIT"
            )

            conn.execute("""
                INSERT INTO gl_master (
                    gl_code,
                    gl_description,
                    account_category,
                    normal_balance,
                    status,
                    effective_date,
                    entity,
                    cost_centre_required,
                    validation_notes,
                    created_by,
                    created_at,
                    updated_by,
                    updated_at
                )
                VALUES (?, ?, ?, ?, 'ACTIVE', ?, 'JKPSD', 0, '', 'SYSTEM', ?, 'SYSTEM', ?)
            """, (
                code,
                details["description"],
                category,
                normal_balance,
                date.today().strftime("%Y-%m-%d"),
                now,
                now
            ))

    conn.commit()
    conn.close()


def get_gl_options(include_inactive=False):
    conn = get_connection()

    if include_inactive:
        rows = conn.execute("""
            SELECT gl_code, gl_description, status
            FROM gl_master
            WHERE entity = 'JKPSD'
            ORDER BY gl_code
        """).fetchall()
    else:
        rows = conn.execute("""
            SELECT gl_code, gl_description, status
            FROM gl_master
            WHERE entity = 'JKPSD'
            AND status = 'ACTIVE'
            ORDER BY gl_code
        """).fetchall()

    conn.close()

    options = []

    for gl_code, description, status in rows:
        label = f"{gl_code} - {description}"

        if include_inactive and status != "ACTIVE":
            label += " [INACTIVE]"

        options.append(label)

    return options


def parse_gl_code(selected_value):
    if selected_value is None or pd.isna(selected_value):
        return ""

    value = str(selected_value)

    if " - " in value:
        return value.split(" - ", 1)[0].strip()

    return value.replace(" [INACTIVE]", "").strip()


def gl_is_active(selected_value):
    gl_code = parse_gl_code(selected_value)

    if not gl_code:
        return False

    conn = get_connection()

    row = conn.execute("""
        SELECT status
        FROM gl_master
        WHERE gl_code = ?
        AND entity = 'JKPSD'
    """, (
        gl_code,
    )).fetchone()

    conn.close()

    return bool(row and row[0] == "ACTIVE")


def log_gl_history(gl_code, action, employee_no, employee_name):
    conn = get_connection()

    row = conn.execute("""
        SELECT
            gl_code,
            gl_description,
            account_category,
            normal_balance,
            status,
            effective_date,
            entity,
            cost_centre_required,
            validation_notes,
            created_by,
            created_at,
            updated_by,
            updated_at
        FROM gl_master
        WHERE gl_code = ?
    """, (
        gl_code,
    )).fetchone()

    if row:
        snapshot = {
            "gl_code": row[0],
            "gl_description": row[1],
            "account_category": row[2],
            "normal_balance": row[3],
            "status": row[4],
            "effective_date": row[5],
            "entity": row[6],
            "cost_centre_required": row[7],
            "validation_notes": row[8],
            "created_by": row[9],
            "created_at": row[10],
            "updated_by": row[11],
            "updated_at": row[12]
        }

        conn.execute("""
            INSERT INTO gl_master_history (
                gl_code,
                action,
                snapshot_json,
                changed_by,
                changed_name,
                changed_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            gl_code,
            action,
            json.dumps(snapshot),
            employee_no,
            employee_name,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))

        conn.commit()

    conn.close()



def seed_jv_types():
    """Seed the original prototype JV types only when master is empty."""
    defaults = [
        "Depreciation",
        "Payroll",
        "AmIncome Placement",
        "Bank",
        "Accrual",
        "Provision",
        "Other"
    ]

    conn = get_connection()
    count = conn.execute(
        "SELECT COUNT(*) FROM jv_type_master"
    ).fetchone()[0]

    if count == 0:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for jv_type in defaults:
            conn.execute("""
                INSERT INTO jv_type_master (
                    jv_type,
                    status,
                    attachment_rule,
                    supporting_document_notes,
                    entity,
                    created_by,
                    created_at,
                    updated_by,
                    updated_at
                )
                VALUES (?, 'ACTIVE', 'OPTIONAL', '', 'JKPSD', 'SYSTEM', ?, 'SYSTEM', ?)
            """, (
                jv_type,
                now,
                now
            ))

    conn.commit()
    conn.close()


def get_jv_type_options(include_inactive=False):
    conn = get_connection()

    if include_inactive:
        rows = conn.execute("""
            SELECT jv_type, status
            FROM jv_type_master
            WHERE entity = 'JKPSD'
            ORDER BY jv_type
        """).fetchall()
    else:
        rows = conn.execute("""
            SELECT jv_type, status
            FROM jv_type_master
            WHERE entity = 'JKPSD'
            AND status = 'ACTIVE'
            ORDER BY jv_type
        """).fetchall()

    conn.close()

    options = []

    for jv_type, status in rows:
        label = jv_type

        if include_inactive and status != "ACTIVE":
            label += " [INACTIVE]"

        options.append(label)

    return options


def clean_jv_type_label(value):
    if value is None:
        return ""

    value = str(value)

    if value.endswith(" [INACTIVE]"):
        return value[:-11]

    return value


def get_jv_type_rule(jv_type):
    clean_type = clean_jv_type_label(jv_type)

    conn = get_connection()

    row = conn.execute("""
        SELECT
            status,
            attachment_rule,
            supporting_document_notes
        FROM jv_type_master
        WHERE jv_type = ?
        AND entity = 'JKPSD'
    """, (
        clean_type,
    )).fetchone()

    conn.close()

    if not row:
        return None

    return {
        "status": row[0],
        "attachment_rule": row[1],
        "notes": row[2] or ""
    }


def jv_type_is_active(jv_type):
    rule = get_jv_type_rule(jv_type)
    return bool(rule and rule["status"] == "ACTIVE")


def log_jv_type_history(jv_type, action, employee_no, employee_name):
    conn = get_connection()

    row = conn.execute("""
        SELECT
            jv_type,
            status,
            attachment_rule,
            supporting_document_notes,
            entity,
            created_by,
            created_at,
            updated_by,
            updated_at
        FROM jv_type_master
        WHERE jv_type = ?
    """, (
        jv_type,
    )).fetchone()

    if row:
        snapshot = {
            "jv_type": row[0],
            "status": row[1],
            "attachment_rule": row[2],
            "supporting_document_notes": row[3],
            "entity": row[4],
            "created_by": row[5],
            "created_at": row[6],
            "updated_by": row[7],
            "updated_at": row[8]
        }

        conn.execute("""
            INSERT INTO jv_type_history (
                jv_type,
                action,
                snapshot_json,
                changed_by,
                changed_name,
                changed_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            jv_type,
            action,
            json.dumps(snapshot),
            employee_no,
            employee_name,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))

        conn.commit()

    conn.close()


def display_date(value):

    if not value:
        return "-"

    try:
        return datetime.strptime(
            str(value)[:10],
            "%Y-%m-%d"
        ).strftime("%d/%m/%Y")
    except:
        return str(value)


def display_datetime(value):

    if not value:
        return "-"

    try:
        return datetime.strptime(
            value,
            "%Y-%m-%d %H:%M:%S"
        ).strftime("%d/%m/%Y %H:%M:%S")
    except:
        return str(value)


def month_label(period_text):

    if not period_text:
        return ""

    dt = datetime.strptime(
        period_text,
        "%Y-%m"
    )

    return dt.strftime("%B %Y")



def period_key(value):
    """Return YYYY-MM from a date, datetime or existing period string."""
    if isinstance(value, (date, datetime)):
        return value.strftime("%Y-%m")

    value = str(value)

    if len(value) >= 7:
        return value[:7]

    return value


def get_period_status(accounting_period, entity="JKPSD"):
    """Periods are OPEN by default until Admin explicitly closes them."""
    key = period_key(accounting_period)

    conn = get_connection()
    row = conn.execute("""
        SELECT status
        FROM accounting_periods
        WHERE entity = ?
        AND accounting_period = ?
    """, (entity, key)).fetchone()
    conn.close()

    return row[0] if row else "OPEN"


def is_period_open(accounting_period, entity="JKPSD"):
    return get_period_status(accounting_period, entity) == "OPEN"


def get_period_outstanding_count(accounting_period):
    """Count JVs that are not yet finalised for the accounting month."""
    key = period_key(accounting_period)

    conn = get_connection()
    count = conn.execute("""
        SELECT COUNT(*)
        FROM jv_headers
        WHERE accounting_period = ?
        AND status NOT IN (
            'POSTED TO UBS',
            'CANCELLED'
        )
    """, (key,)).fetchone()[0]
    conn.close()

    return count


def set_period_status(
    accounting_period,
    new_status,
    employee_no,
    employee_name,
    entity="JKPSD"
):
    key = period_key(accounting_period)
    new_status = new_status.upper()

    if new_status not in ("OPEN", "CLOSED"):
        raise ValueError("Invalid accounting period status.")

    if new_status == "CLOSED":
        outstanding = get_period_outstanding_count(key)

        if outstanding > 0:
            raise PermissionError(
                f"Period cannot be closed because {outstanding} JV(s) "
                f"are not yet Posted to UBS or Cancelled."
            )

    old_status = get_period_status(key, entity)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_connection()

    conn.execute("""
        INSERT INTO accounting_periods (
            entity,
            accounting_period,
            status,
            updated_by,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(entity, accounting_period)
        DO UPDATE SET
            status = excluded.status,
            updated_by = excluded.updated_by,
            updated_at = excluded.updated_at
    """, (
        entity,
        key,
        new_status,
        employee_no,
        now
    ))

    conn.execute("""
        INSERT INTO period_history (
            entity,
            accounting_period,
            old_status,
            new_status,
            changed_by,
            changed_name,
            changed_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        entity,
        key,
        old_status,
        new_status,
        employee_no,
        employee_name,
        now
    ))

    conn.commit()
    conn.close()


def add_audit_log(
    jv_id,
    jv_number,
    event_type,
    employee_no,
    employee_name,
    role,
    comments=""
):

    conn = get_connection()

    conn.execute("""
        INSERT INTO audit_log (
            jv_id,
            jv_number,
            event_type,
            employee_no,
            employee_name,
            role,
            comments,
            event_timestamp
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        jv_id,
        jv_number,
        event_type,
        employee_no,
        employee_name,
        role,
        comments,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()


def generate_jv_number(accounting_period):

    period = accounting_period.strftime("%y%m")

    conn = get_connection()

    row = conn.execute("""
        SELECT jv_number
        FROM jv_headers
        WHERE jv_number LIKE ?
        ORDER BY jv_number DESC
        LIMIT 1
    """, (f"JV{period}%",)).fetchone()

    conn.close()

    if row is None:
        sequence = 1
    else:
        sequence = int(row[0][-2:]) + 1

    return f"JV{period}{sequence:02d}"


def save_jv(
    jv_number,
    jv_type,
    accounting_period,
    remarks,
    journal_df,
    total_debit,
    total_credit,
    uploaded_files,
    employee_no,
    employee_name
):

    attachment_names = []

    if uploaded_files:
        attachment_names = [
            file.name
            for file in uploaded_files
        ]

    conn = get_connection()
    cursor = conn.cursor()

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        INSERT INTO jv_headers (
            jv_number,
            jv_type,
            accounting_period,
            remarks,
            status,
            total_debit,
            total_credit,
            prepared_by,
            prepared_name,
            created_at,
            submitted_at,
            attachment_names
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        jv_number,
        jv_type,
        accounting_period.strftime("%Y-%m"),
        remarks,
        "PENDING APPROVAL",
        total_debit,
        total_credit,
        employee_no,
        employee_name,
        now,
        now,
        json.dumps(attachment_names)
    ))

    jv_id = cursor.lastrowid
    line_no = 1

    for _, row in journal_df.iterrows():

        debit = float(
            pd.to_numeric(
                row["Dr"],
                errors="coerce"
            )
            if pd.notna(row["Dr"])
            else 0
        )

        credit = float(
            pd.to_numeric(
                row["Cr"],
                errors="coerce"
            )
            if pd.notna(row["Cr"])
            else 0
        )

        has_data = (
            pd.notna(row["Date"])
            or pd.notna(row["A/C Code"])
            or str(row["Description"]).strip() != ""
            or debit > 0
            or credit > 0
        )

        if not has_data:
            continue

        selected_gl = row["A/C Code"]

        gl_code = ""
        gl_description = ""

        if pd.notna(selected_gl):

            selected_gl = str(selected_gl)

            gl_code = selected_gl.split(
                " - ",
                1
            )[0]

            if " - " in selected_gl:
                gl_description = selected_gl.split(
                    " - ",
                    1
                )[1]

        line_date = row["Date"]

        if hasattr(line_date, "strftime"):
            line_date = line_date.strftime("%Y-%m-%d")

        cursor.execute("""
            INSERT INTO jv_lines (
                jv_id,
                line_no,
                line_date,
                gl_code,
                gl_description,
                description,
                debit,
                credit
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            jv_id,
            line_no,
            str(line_date),
            gl_code,
            gl_description,
            str(row["Description"]),
            debit,
            credit
        ))

        line_no += 1

    conn.commit()
    conn.close()

    store_uploaded_files(
        jv_id,
        jv_number,
        uploaded_files,
        1,
        employee_no,
        employee_name
    )

    add_audit_log(
        jv_id,
        jv_number,
        "JV_SUBMITTED",
        employee_no,
        employee_name,
        "PREPARER",
        "Submitted for approval."
    )

    notify_active_role(
        "APPROVER",
        f"JV awaiting approval: {jv_number}",
        f"{employee_name} submitted {jv_number} for approval.",
        "JV_SUBMITTED",
        jv_id,
        jv_number,
        exclude_employee_no=employee_no
    )

    return jv_id


def get_jv_lines_for_edit(jv_id):

    conn = get_connection()

    rows = conn.execute("""
        SELECT
            line_date,
            gl_code,
            gl_description,
            description,
            debit,
            credit
        FROM jv_lines
        WHERE jv_id = ?
        ORDER BY line_no
    """, (jv_id,)).fetchall()

    conn.close()

    data = []

    for (
        line_date,
        gl_code,
        gl_description,
        description,
        debit,
        credit
    ) in rows:

        try:
            edit_date = datetime.strptime(
                str(line_date)[:10],
                "%Y-%m-%d"
            ).date()
        except:
            edit_date = None

        gl_value = gl_code

        if gl_description:
            gl_value = f"{gl_code} - {gl_description}"

        data.append({
            "Date": edit_date,
            "A/C Code": gl_value,
            "Description": description,
            "Dr": float(debit or 0),
            "Cr": float(credit or 0)
        })

    return pd.DataFrame(data)


def save_revision_snapshot(jv_id, employee_no):

    conn = get_connection()
    cursor = conn.cursor()

    header = cursor.execute("""
        SELECT
            jv_number,
            jv_type,
            accounting_period,
            remarks,
            status,
            total_debit,
            total_credit,
            prepared_by,
            prepared_name,
            submitted_at,
            approved_by,
            approved_name,
            approved_at,
            reviewer_comments,
            posted_by,
            posted_at,
            attachment_names,
            revision_no
        FROM jv_headers
        WHERE id = ?
    """, (jv_id,)).fetchone()

    if not header:
        conn.close()
        return

    lines = cursor.execute("""
        SELECT
            line_no,
            line_date,
            gl_code,
            gl_description,
            description,
            debit,
            credit
        FROM jv_lines
        WHERE jv_id = ?
        ORDER BY line_no
    """, (jv_id,)).fetchall()

    snapshot = {
        "header": list(header),
        "lines": [list(row) for row in lines]
    }

    cursor.execute("""
        INSERT INTO jv_revisions (
            jv_id,
            revision_no,
            snapshot_json,
            created_by,
            created_at
        )
        VALUES (?, ?, ?, ?, ?)
    """, (
        jv_id,
        int(header[-1] or 1),
        json.dumps(snapshot),
        employee_no,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()


def validate_journal(journal_df):

    errors = []

    if journal_df is None or journal_df.empty:
        return ["Minimum two journal lines required."], 0.0, 0.0

    debit_series = pd.to_numeric(
        journal_df["Dr"],
        errors="coerce"
    ).fillna(0)

    credit_series = pd.to_numeric(
        journal_df["Cr"],
        errors="coerce"
    ).fillna(0)

    total_debit = round(float(debit_series.sum()), 2)
    total_credit = round(float(credit_series.sum()), 2)

    active_rows = []

    for index, row in journal_df.iterrows():

        debit = float(debit_series.loc[index])
        credit = float(credit_series.loc[index])

        has_data = (
            pd.notna(row["Date"])
            or pd.notna(row["A/C Code"])
            or str(row["Description"]).strip() != ""
            or debit > 0
            or credit > 0
        )

        if has_data:
            active_rows.append(index)

    if len(active_rows) < 2:
        errors.append("Minimum two journal lines required.")

    for position, index in enumerate(active_rows, start=1):

        row = journal_df.loc[index]
        debit = float(debit_series.loc[index])
        credit = float(credit_series.loc[index])

        if pd.isna(row["Date"]):
            errors.append(f"Line {position}: Date required.")

        if pd.isna(row["A/C Code"]):
            errors.append(f"Line {position}: A/C Code required.")

        elif not gl_is_active(row["A/C Code"]):
            errors.append(
                f"Line {position}: A/C Code is inactive or invalid."
            )

        if str(row["Description"]).strip() == "":
            errors.append(f"Line {position}: Description required.")

        if debit > 0 and credit > 0:
            errors.append(f"Line {position}: Enter Dr or Cr only.")

        if debit == 0 and credit == 0:
            errors.append(f"Line {position}: Amount required.")

    if total_debit == 0:
        errors.append("JV total cannot be zero.")

    if total_debit != total_credit:
        errors.append(
            f"Dr RM{total_debit:,.2f} does not match "
            f"Cr RM{total_credit:,.2f}."
        )

    return errors, total_debit, total_credit



def validate_journal_dates_against_period(journal_df, accounting_period):
    """Submission control: every populated journal line date must match accounting month."""
    errors = []

    if journal_df is None or journal_df.empty:
        return errors

    period = period_key(accounting_period)

    for position, (_, row) in enumerate(journal_df.iterrows(), start=1):
        debit = float(pd.to_numeric(row.get("Dr"), errors="coerce") or 0)
        credit = float(pd.to_numeric(row.get("Cr"), errors="coerce") or 0)

        has_data = (
            pd.notna(row.get("Date"))
            or pd.notna(row.get("A/C Code"))
            or str(row.get("Description", "")).strip() != ""
            or debit > 0
            or credit > 0
        )

        if not has_data or pd.isna(row.get("Date")):
            continue

        line_date = row.get("Date")

        if hasattr(line_date, "strftime"):
            line_period = line_date.strftime("%Y-%m")
        else:
            try:
                line_period = datetime.strptime(
                    str(line_date)[:10],
                    "%Y-%m-%d"
                ).strftime("%Y-%m")
            except:
                continue

        if line_period != period:
            errors.append(
                f"Line {position}: Date must fall within "
                f"{month_label(period)}."
            )

    return errors


def write_jv_lines(cursor, jv_id, journal_df):
    """Replace JV lines while allowing incomplete rows for Draft status."""
    cursor.execute(
        "DELETE FROM jv_lines WHERE jv_id = ?",
        (jv_id,)
    )

    line_no = 1

    if journal_df is None:
        return

    for _, row in journal_df.iterrows():

        debit = float(
            pd.to_numeric(
                row.get("Dr"),
                errors="coerce"
            )
            if pd.notna(row.get("Dr"))
            else 0
        )

        credit = float(
            pd.to_numeric(
                row.get("Cr"),
                errors="coerce"
            )
            if pd.notna(row.get("Cr"))
            else 0
        )

        has_data = (
            pd.notna(row.get("Date"))
            or pd.notna(row.get("A/C Code"))
            or str(row.get("Description", "")).strip() != ""
            or debit > 0
            or credit > 0
        )

        if not has_data:
            continue

        selected_gl = row.get("A/C Code")
        gl_code = ""
        gl_description = ""

        if pd.notna(selected_gl):
            selected_gl = str(selected_gl)
            gl_code = parse_gl_code(selected_gl)

            if " - " in selected_gl:
                gl_description = selected_gl.split(
                    " - ",
                    1
                )[1].replace(" [INACTIVE]", "").strip()

        line_date = row.get("Date")

        if hasattr(line_date, "strftime"):
            line_date = line_date.strftime("%Y-%m-%d")
        elif pd.isna(line_date):
            line_date = ""
        else:
            line_date = str(line_date)

        cursor.execute("""
            INSERT INTO jv_lines (
                jv_id,
                line_no,
                line_date,
                gl_code,
                gl_description,
                description,
                debit,
                credit
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            jv_id,
            line_no,
            line_date,
            gl_code,
            gl_description,
            str(row.get("Description", "") or ""),
            debit,
            credit
        ))

        line_no += 1


def save_new_draft(
    jv_number,
    jv_type,
    accounting_period,
    remarks,
    journal_df,
    total_debit,
    total_credit,
    uploaded_files,
    employee_no,
    employee_name
):
    if not is_period_open(accounting_period):
        raise PermissionError(
            f"{month_label(period_key(accounting_period))} is CLOSED."
        )

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    attachment_names = [
        file.name
        for file in (uploaded_files or [])
    ]

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO jv_headers (
            jv_number,
            jv_type,
            accounting_period,
            remarks,
            status,
            total_debit,
            total_credit,
            prepared_by,
            prepared_name,
            created_at,
            submitted_at,
            attachment_names
        )
        VALUES (?, ?, ?, ?, 'DRAFT', ?, ?, ?, ?, ?, NULL, ?)
    """, (
        jv_number,
        jv_type,
        period_key(accounting_period),
        remarks,
        float(total_debit or 0),
        float(total_credit or 0),
        employee_no,
        employee_name,
        now,
        json.dumps(attachment_names)
    ))

    jv_id = cursor.lastrowid

    write_jv_lines(
        cursor,
        jv_id,
        journal_df
    )

    conn.commit()
    conn.close()

    store_uploaded_files(
        jv_id,
        jv_number,
        uploaded_files,
        1,
        employee_no,
        employee_name
    )

    add_audit_log(
        jv_id,
        jv_number,
        "JV_DRAFT_SAVED",
        employee_no,
        employee_name,
        "PREPARER",
        "Draft saved."
    )

    return jv_id


def update_existing_draft(
    jv_id,
    jv_type,
    remarks,
    journal_df,
    total_debit,
    total_credit,
    uploaded_files,
    employee_no,
    employee_name
):
    conn = get_connection()

    row = conn.execute("""
        SELECT
            jv_number,
            accounting_period,
            prepared_by,
            status,
            attachment_names
        FROM jv_headers
        WHERE id = ?
    """, (
        jv_id,
    )).fetchone()

    conn.close()

    if not row:
        raise ValueError("JV not found.")

    (
        jv_number,
        accounting_period,
        prepared_by,
        status,
        attachment_names
    ) = row

    if prepared_by != employee_no:
        raise PermissionError(
            "Only the original preparer can update this Draft."
        )

    if status != "DRAFT":
        raise PermissionError(
            "This JV is no longer a Draft."
        )

    if not is_period_open(accounting_period):
        raise PermissionError(
            f"{month_label(accounting_period)} is CLOSED."
        )

    try:
        names = json.loads(attachment_names or "[]")
    except:
        names = []

    for file in (uploaded_files or []):
        if file.name not in names:
            names.append(file.name)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE jv_headers
        SET
            jv_type = ?,
            remarks = ?,
            total_debit = ?,
            total_credit = ?,
            attachment_names = ?
        WHERE id = ?
    """, (
        jv_type,
        remarks,
        float(total_debit or 0),
        float(total_credit or 0),
        json.dumps(names),
        jv_id
    ))

    write_jv_lines(
        cursor,
        jv_id,
        journal_df
    )

    conn.commit()
    conn.close()

    store_uploaded_files(
        jv_id,
        jv_number,
        uploaded_files,
        1,
        employee_no,
        employee_name
    )

    add_audit_log(
        jv_id,
        jv_number,
        "JV_DRAFT_UPDATED",
        employee_no,
        employee_name,
        "PREPARER",
        "Draft updated."
    )


def submit_existing_draft(
    jv_id,
    jv_type,
    remarks,
    journal_df,
    total_debit,
    total_credit,
    uploaded_files,
    employee_no,
    employee_name
):
    update_existing_draft(
        jv_id,
        jv_type,
        remarks,
        journal_df,
        total_debit,
        total_credit,
        uploaded_files,
        employee_no,
        employee_name
    )

    conn = get_connection()

    row = conn.execute("""
        SELECT
            jv_number,
            accounting_period
        FROM jv_headers
        WHERE id = ?
    """, (
        jv_id,
    )).fetchone()

    if not row:
        conn.close()
        raise ValueError("JV not found.")

    jv_number, accounting_period = row

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn.execute("""
        UPDATE jv_headers
        SET
            status = 'PENDING APPROVAL',
            submitted_at = ?
        WHERE id = ?
        AND status = 'DRAFT'
    """, (
        now,
        jv_id
    ))

    conn.commit()
    conn.close()

    add_audit_log(
        jv_id,
        jv_number,
        "JV_SUBMITTED",
        employee_no,
        employee_name,
        "PREPARER",
        "Draft submitted for approval."
    )

    notify_active_role(
        "APPROVER",
        f"JV awaiting approval: {jv_number}",
        f"{employee_name} submitted {jv_number} for approval.",
        "JV_SUBMITTED",
        jv_id,
        jv_number,
        exclude_employee_no=employee_no
    )


def cancel_draft(jv_id, employee_no, employee_name):
    conn = get_connection()

    row = conn.execute("""
        SELECT
            jv_number,
            prepared_by,
            status
        FROM jv_headers
        WHERE id = ?
    """, (
        jv_id,
    )).fetchone()

    if not row:
        conn.close()
        raise ValueError("JV not found.")

    jv_number, prepared_by, status = row

    if prepared_by != employee_no:
        conn.close()
        raise PermissionError(
            "Only the original preparer can cancel this Draft."
        )

    if status != "DRAFT":
        conn.close()
        raise PermissionError(
            "Only Draft JVs can be cancelled."
        )

    conn.execute("""
        UPDATE jv_headers
        SET status = 'CANCELLED'
        WHERE id = ?
    """, (
        jv_id,
    ))

    conn.commit()
    conn.close()

    add_audit_log(
        jv_id,
        jv_number,
        "JV_CANCELLED",
        employee_no,
        employee_name,
        "PREPARER",
        "Draft cancelled."
    )


def render_draft_controls(jv_id, employee_no, employee_name):
    if role != "PREPARER":
        return

    conn = get_connection()

    header = conn.execute("""
        SELECT
            jv_number,
            jv_type,
            accounting_period,
            remarks,
            status,
            prepared_by
        FROM jv_headers
        WHERE id = ?
    """, (
        jv_id,
    )).fetchone()

    conn.close()

    if not header:
        return

    (
        jv_number,
        current_type,
        accounting_period,
        current_remarks,
        status,
        prepared_by
    ) = header

    if status != "DRAFT" or prepared_by != employee_no:
        return

    st.divider()
    st.subheader("Continue Draft")

    if not is_period_open(accounting_period):
        st.error(
            f"{month_label(accounting_period)} is CLOSED. "
            "This Draft is locked."
        )
        return

    type_options = get_jv_type_options(
        include_inactive=True
    )

    current_label = current_type

    if not jv_type_is_active(current_type):
        current_label = f"{current_type} [INACTIVE]"

    if current_label not in type_options:
        type_options.insert(0, current_label)

    selected_type_display = st.selectbox(
        "JV Type",
        type_options,
        index=type_options.index(current_label),
        key=f"draft_type_{jv_id}"
    )

    selected_type = clean_jv_type_label(
        selected_type_display
    )

    type_rule = get_jv_type_rule(
        selected_type
    )

    draft_remarks = st.text_input(
        "JV Description / Remarks",
        value=current_remarks or "",
        key=f"draft_remarks_{jv_id}"
    )

    edit_df = get_jv_lines_for_edit(jv_id)

    if edit_df.empty:
        edit_df = pd.DataFrame([
            {
                "Date": None,
                "A/C Code": None,
                "Description": "",
                "Dr": 0.00,
                "Cr": 0.00
            },
            {
                "Date": None,
                "A/C Code": None,
                "Description": "",
                "Dr": 0.00,
                "Cr": 0.00
            }
        ])

    draft_df = st.data_editor(
        edit_df,
        num_rows="dynamic",
        hide_index=True,
        use_container_width=True,
        column_config={
            "Date": st.column_config.DateColumn(
                "Date",
                format="DD/MM/YYYY"
            ),
            "A/C Code": st.column_config.SelectboxColumn(
                "A/C Code",
                options=get_gl_options(include_inactive=True)
            ),
            "Description": st.column_config.TextColumn(
                "Description",
                width="large"
            ),
            "Dr": st.column_config.NumberColumn(
                "Dr",
                min_value=0.00,
                format="%.2f"
            ),
            "Cr": st.column_config.NumberColumn(
                "Cr",
                min_value=0.00,
                format="%.2f"
            )
        },
        key=f"draft_editor_{jv_id}"
    )

    draft_files = st.file_uploader(
        "Add Supporting Documents",
        type=[
            "pdf",
            "xlsx",
            "xls",
            "docx",
            "jpg",
            "jpeg",
            "png"
        ],
        accept_multiple_files=True,
        key=f"draft_files_{jv_id}"
    )

    debit_series = pd.to_numeric(
        draft_df["Dr"],
        errors="coerce"
    ).fillna(0)

    credit_series = pd.to_numeric(
        draft_df["Cr"],
        errors="coerce"
    ).fillna(0)

    total_debit = round(
        float(debit_series.sum()),
        2
    )

    total_credit = round(
        float(credit_series.sum()),
        2
    )

    submit_errors, _, _ = validate_journal(
        draft_df
    )

    submit_errors.extend(
        validate_journal_dates_against_period(
            draft_df,
            accounting_period
        )
    )

    if not jv_type_is_active(selected_type):
        submit_errors.append(
            "Selected JV Type is inactive or invalid."
        )

    if (
        type_rule
        and type_rule["attachment_rule"] == "REQUIRED"
        and not get_active_attachments(jv_id)
        and not draft_files
    ):
        submit_errors.append(
            f"Supporting document is required for JV Type: {selected_type}."
        )

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Total Dr",
        f"RM {total_debit:,.2f}"
    )

    c2.metric(
        "Total Cr",
        f"RM {total_credit:,.2f}"
    )

    c3.metric(
        "Difference",
        f"RM {total_debit-total_credit:,.2f}"
    )

    if submit_errors:
        with st.expander(
            "Submission validation"
        ):
            for error in submit_errors:
                st.write(f"• {error}")
    else:
        st.success(
            "Ready for submission ✓"
        )

    c1, c2, c3 = st.columns(3)

    with c1:
        if st.button(
            "Save Draft Changes",
            use_container_width=True,
            key=f"save_draft_changes_{jv_id}"
        ):
            update_existing_draft(
                jv_id,
                selected_type,
                draft_remarks,
                draft_df,
                total_debit,
                total_credit,
                draft_files,
                employee_no,
                employee_name
            )

            st.success(
                f"{jv_number} draft updated."
            )
            st.rerun()

    with c2:
        if st.button(
            "Submit for Approval",
            type="primary",
            use_container_width=True,
            disabled=bool(submit_errors),
            key=f"submit_draft_{jv_id}"
        ):
            submit_existing_draft(
                jv_id,
                selected_type,
                draft_remarks,
                draft_df,
                total_debit,
                total_credit,
                draft_files,
                employee_no,
                employee_name
            )

            st.session_state.myjv_jv_id = None
            st.session_state.dashboard_jv_id = None

            st.success(
                f"{jv_number} submitted for approval."
            )
            st.rerun()

    with c3:
        confirm_cancel = st.checkbox(
            "Confirm cancel",
            key=f"confirm_cancel_draft_{jv_id}"
        )

        if st.button(
            "Cancel JV",
            use_container_width=True,
            disabled=not confirm_cancel,
            key=f"cancel_draft_{jv_id}"
        ):
            cancel_draft(
                jv_id,
                employee_no,
                employee_name
            )

            st.session_state.myjv_jv_id = None
            st.session_state.dashboard_jv_id = None

            st.success(
                f"{jv_number} cancelled."
            )
            st.rerun()


def update_and_resubmit_jv(
    jv_id,
    jv_type,
    remarks,
    journal_df,
    total_debit,
    total_credit,
    uploaded_files,
    employee_no,
    employee_name
):

    conn = get_connection()

    header = conn.execute("""
        SELECT
            jv_number,
            prepared_by,
            status,
            attachment_names,
            revision_no
        FROM jv_headers
        WHERE id = ?
    """, (jv_id,)).fetchone()

    conn.close()

    if not header:
        raise ValueError("JV not found.")

    jv_number, prepared_by, status, attachment_names, revision_no = header

    period_row_conn = get_connection()
    period_row = period_row_conn.execute(
        "SELECT accounting_period FROM jv_headers WHERE id = ?",
        (jv_id,)
    ).fetchone()
    period_row_conn.close()

    if period_row and not is_period_open(period_row[0]):
        raise PermissionError(
            f"{month_label(period_row[0])} is CLOSED. "
            "This JV cannot be amended or resubmitted."
        )

    if prepared_by != employee_no:
        raise PermissionError("Only the original preparer can amend this JV.")

    if status != "AMENDMENT REQUIRED":
        raise PermissionError("This JV is not available for amendment.")

    # Retain the previous version internally before replacing the live record.
    save_revision_snapshot(jv_id, employee_no)

    try:
        existing_attachments = json.loads(attachment_names or "[]")
    except:
        existing_attachments = []

    if uploaded_files:
        for uploaded_file in uploaded_files:
            if uploaded_file.name not in existing_attachments:
                existing_attachments.append(uploaded_file.name)

    new_revision = int(revision_no or 1) + 1
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM jv_lines WHERE jv_id = ?",
        (jv_id,)
    )

    cursor.execute("""
        UPDATE jv_headers
        SET
            jv_type = ?,
            remarks = ?,
            status = 'RESUBMITTED',
            total_debit = ?,
            total_credit = ?,
            submitted_at = ?,
            approved_by = NULL,
            approved_name = NULL,
            approved_at = NULL,
            attachment_names = ?,
            revision_no = ?
        WHERE id = ?
    """, (
        jv_type,
        remarks,
        total_debit,
        total_credit,
        now,
        json.dumps(existing_attachments),
        new_revision,
        jv_id
    ))

    line_no = 1

    for _, row in journal_df.iterrows():

        debit = float(
            pd.to_numeric(row["Dr"], errors="coerce")
            if pd.notna(row["Dr"])
            else 0
        )

        credit = float(
            pd.to_numeric(row["Cr"], errors="coerce")
            if pd.notna(row["Cr"])
            else 0
        )

        has_data = (
            pd.notna(row["Date"])
            or pd.notna(row["A/C Code"])
            or str(row["Description"]).strip() != ""
            or debit > 0
            or credit > 0
        )

        if not has_data:
            continue

        selected_gl = row["A/C Code"]
        gl_code = ""
        gl_description = ""

        if pd.notna(selected_gl):
            selected_gl = str(selected_gl)
            gl_code = selected_gl.split(" - ", 1)[0]

            if " - " in selected_gl:
                gl_description = selected_gl.split(" - ", 1)[1]

        line_date = row["Date"]

        if hasattr(line_date, "strftime"):
            line_date = line_date.strftime("%Y-%m-%d")

        cursor.execute("""
            INSERT INTO jv_lines (
                jv_id,
                line_no,
                line_date,
                gl_code,
                gl_description,
                description,
                debit,
                credit
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            jv_id,
            line_no,
            str(line_date),
            gl_code,
            gl_description,
            str(row["Description"]),
            debit,
            credit
        ))

        line_no += 1

    conn.commit()
    conn.close()

    store_uploaded_files(
        jv_id,
        jv_number,
        uploaded_files,
        new_revision,
        employee_no,
        employee_name
    )

    add_audit_log(
        jv_id,
        jv_number,
        "JV_RESUBMITTED",
        employee_no,
        employee_name,
        "PREPARER",
        f"Amended and resubmitted. Revision {new_revision}."
    )

    notify_active_role(
        "APPROVER",
        f"JV resubmitted: {jv_number}",
        f"{employee_name} amended and resubmitted {jv_number}.",
        "JV_RESUBMITTED",
        jv_id,
        jv_number,
        exclude_employee_no=employee_no
    )

    return new_revision


def render_amendment_controls(jv_id, employee_no, employee_name):

    if role != "PREPARER":
        return

    conn = get_connection()

    header = conn.execute("""
        SELECT
            jv_number,
            jv_type,
            accounting_period,
            remarks,
            status,
            prepared_by,
            reviewer_comments,
            revision_no
        FROM jv_headers
        WHERE id = ?
    """, (jv_id,)).fetchone()

    conn.close()

    if not header:
        return

    (
        jv_number,
        current_type,
        accounting_period,
        current_remarks,
        status,
        prepared_by,
        reviewer_comments,
        revision_no
    ) = header

    if status != "AMENDMENT REQUIRED":
        return

    if prepared_by != employee_no:
        return

    if not is_period_open(accounting_period):
        st.divider()
        st.error(
            f"{month_label(accounting_period)} is CLOSED. "
            "Amendment and resubmission are locked."
        )
        return

    st.divider()
    st.warning("Amendment required")

    if reviewer_comments:
        st.write(f"**Reviewer comments:** {reviewer_comments}")

    if st.session_state.amend_jv_id != jv_id:

        if st.button(
            "Amend JV",
            type="primary",
            key=f"start_amend_{jv_id}"
        ):
            st.session_state.amend_jv_id = jv_id
            st.rerun()

        return

    st.subheader("Amend & Resubmit")

    st.caption(
        f"JV No. {jv_number} remains unchanged. "
        f"Accounting month: {month_label(accounting_period)}. "
        f"Current revision: {int(revision_no or 1)}"
    )

    type_options = get_jv_type_options(
        include_inactive=True
    )

    current_type_label = current_type

    if not jv_type_is_active(current_type):
        current_type_label = f"{current_type} [INACTIVE]"

    if current_type_label not in type_options:
        type_options.insert(
            0,
            current_type_label
        )

    type_index = (
        type_options.index(current_type_label)
        if current_type_label in type_options
        else 0
    )

    amended_type_display = st.selectbox(
        "JV Type",
        type_options,
        index=type_index,
        key=f"amend_type_{jv_id}"
    )

    amended_type = clean_jv_type_label(
        amended_type_display
    )

    amended_type_rule = get_jv_type_rule(
        amended_type
    )

    if amended_type_rule:
        attachment_rule_text = amended_type_rule["attachment_rule"].title()

        st.caption(
            f"Supporting document rule: {attachment_rule_text}"
        )

        if amended_type_rule["notes"]:
            st.caption(
                amended_type_rule["notes"]
            )

    amended_remarks = st.text_input(
        "JV Description / Remarks",
        value=current_remarks or "",
        key=f"amend_remarks_{jv_id}"
    )

    edit_df = get_jv_lines_for_edit(jv_id)

    amended_df = st.data_editor(
        edit_df,
        num_rows="dynamic",
        hide_index=True,
        use_container_width=True,
        column_config={
            "Date": st.column_config.DateColumn(
                "Date",
                format="DD/MM/YYYY"
            ),
            "A/C Code": st.column_config.SelectboxColumn(
                "A/C Code",
                options=get_gl_options(include_inactive=True)
            ),
            "Description": st.column_config.TextColumn(
                "Description",
                width="large"
            ),
            "Dr": st.column_config.NumberColumn(
                "Dr",
                min_value=0.00,
                format="%.2f"
            ),
            "Cr": st.column_config.NumberColumn(
                "Cr",
                min_value=0.00,
                format="%.2f"
            )
        },
        key=f"amend_editor_{jv_id}"
    )

    amendment_files = st.file_uploader(
        "Add Supporting Documents (Optional)",
        type=[
            "pdf",
            "xlsx",
            "xls",
            "docx",
            "jpg",
            "jpeg",
            "png"
        ],
        accept_multiple_files=True,
        key=f"amend_files_{jv_id}"
    )

    st.caption(
        "A file with the same filename will replace the current active copy. "
        "The previous copy remains retained internally."
    )

    errors, total_debit, total_credit = validate_journal(amended_df)

    errors.extend(
        validate_journal_dates_against_period(
            amended_df,
            accounting_period
        )
    )

    if not jv_type_is_active(amended_type):
        errors.append(
            "Selected JV Type is inactive or invalid."
        )

    if (
        amended_type_rule
        and amended_type_rule["attachment_rule"] == "REQUIRED"
    ):
        existing_active_attachments = get_active_attachments(jv_id)

        if not existing_active_attachments and not amendment_files:
            errors.append(
                f"Supporting document is required for JV Type: {amended_type}."
            )

    c1, c2, c3 = st.columns(3)

    c1.metric("Total Dr", f"RM {total_debit:,.2f}")
    c2.metric("Total Cr", f"RM {total_credit:,.2f}")
    c3.metric(
        "Difference",
        f"RM {total_debit - total_credit:,.2f}"
    )

    if errors:

        st.error("JV not ready for resubmission.")

        with st.expander("Validation issues"):
            for error in errors:
                st.write(f"• {error}")

        resubmit_disabled = True

    else:
        st.success("Balanced ✓")
        resubmit_disabled = False

    c1, c2 = st.columns(2)

    with c1:
        if st.button(
            "Cancel Amendment",
            use_container_width=True,
            key=f"cancel_amend_{jv_id}"
        ):
            st.session_state.amend_jv_id = None
            st.rerun()

    with c2:
        if st.button(
            "Resubmit for Approval",
            type="primary",
            disabled=resubmit_disabled,
            use_container_width=True,
            key=f"resubmit_{jv_id}"
        ):

            new_revision = update_and_resubmit_jv(
                jv_id,
                amended_type,
                amended_remarks,
                amended_df,
                total_debit,
                total_credit,
                amendment_files,
                employee_no,
                employee_name
            )

            st.session_state.amend_jv_id = None
            st.session_state.myjv_jv_id = None
            st.session_state.dashboard_jv_id = None

            st.success(
                f"{jv_number} resubmitted successfully "
                f"as Revision {new_revision}."
            )

            st.rerun()


def get_jv_lines(jv_id):

    conn = get_connection()

    df = pd.read_sql_query("""
        SELECT
            line_no AS "Line",
            line_date AS "Date",
            gl_code AS "A/C Code",
            description AS "Description",
            debit AS "Dr",
            credit AS "Cr"
        FROM jv_lines
        WHERE jv_id = ?
        ORDER BY line_no
    """, conn, params=(jv_id,))

    conn.close()

    if not df.empty:
        df["Date"] = df["Date"].apply(display_date)

    return df


def get_jv_header(jv_id):

    conn = get_connection()

    row = conn.execute("""
        SELECT
            id,
            jv_number,
            jv_type,
            accounting_period,
            remarks,
            status,
            total_debit,
            total_credit,
            prepared_by,
            prepared_name,
            submitted_at,
            approved_by,
            approved_name,
            approved_at,
            reviewer_comments,
            posted_by,
            posted_at,
            attachment_names
        FROM jv_headers
        WHERE id = ?
    """, (jv_id,)).fetchone()

    conn.close()

    return row


def show_jv_detail(jv_id):

    header = get_jv_header(jv_id)

    if not header:
        st.error("JV not found.")
        return

    (
        _,
        jv_number,
        jv_type,
        accounting_period,
        remarks,
        status,
        total_debit,
        total_credit,
        prepared_by,
        prepared_name,
        submitted_at,
        approved_by,
        approved_name,
        approved_at,
        reviewer_comments,
        posted_by,
        posted_at,
        attachment_names
    ) = header

    st.subheader(jv_number)

    c1, c2, c3, c4 = st.columns(4)

    c1.write(
        f"**Month**  \n{month_label(accounting_period)}"
    )

    c2.write(
        f"**JV Type**  \n{jv_type}"
    )

    c3.write(
        f"**Status**  \n{status}"
    )

    c4.write(
        f"**Amount**  \nRM {total_debit:,.2f}"
    )

    if remarks:
        st.write(
            f"**Description:** {remarks}"
        )

    line_df = get_jv_lines(jv_id)

    st.dataframe(
        line_df,
        use_container_width=True,
        hide_index=True
    )

    c1, c2 = st.columns(2)

    c1.metric(
        "Total Dr",
        f"RM {total_debit:,.2f}"
    )

    c2.metric(
        "Total Cr",
        f"RM {total_credit:,.2f}"
    )

    st.divider()

    st.write(
        f"**Prepared by:** "
        f"{prepared_name} ({prepared_by})"
    )

    st.write(
        f"**Submitted:** "
        f"{display_datetime(submitted_at)}"
    )

    if approved_name:

        st.write(
            f"**Approved by:** "
            f"{approved_name} ({approved_by})"
        )

        st.write(
            f"**Approval date:** "
            f"{display_datetime(approved_at)}"
        )

    if reviewer_comments and role != "AUDITOR":

        st.write(
            f"**Reviewer comments:** "
            f"{reviewer_comments}"
        )

    if role != "AUDITOR":

        conn = get_connection()
        revision_row = conn.execute(
            "SELECT revision_no FROM jv_headers WHERE id = ?",
            (jv_id,)
        ).fetchone()
        conn.close()

        if revision_row:
            st.write(
                f"**Current revision:** "
                f"{int(revision_row[0] or 1)}"
            )

    if posted_by:

        st.write(
            f"**Posted by:** "
            f"{posted_by}"
        )

        st.write(
            f"**Posted date:** "
            f"{display_datetime(posted_at)}"
        )

    render_attachments(
        jv_id,
        status,
        attachment_names
    )



def render_post_to_ubs_control(jv_id, employee_no, employee_name):
    """Allow only the original preparer to mark an approved JV as posted."""
    conn = get_connection()
    row = conn.execute("""
        SELECT
            jv_number,
            status,
            prepared_by,
            posted_by,
            posted_at
        FROM jv_headers
        WHERE id = ?
    """, (jv_id,)).fetchone()
    conn.close()

    if not row:
        return

    jv_number, status, prepared_by, posted_by, posted_at = row

    # Segregation / ownership control: only the JV's preparer can post it.
    if prepared_by != employee_no:
        return

    if status == "POSTED TO UBS":
        st.success(
            f"Finalised: {jv_number} was posted to UBS by "
            f"{posted_by or employee_no} on {display_datetime(posted_at)}."
        )
        st.caption(
            "This JV is locked. No further amendment or approval action is allowed."
        )
        return

    if status != "APPROVED":
        return

    period_conn = get_connection()
    period_row = period_conn.execute(
        "SELECT accounting_period FROM jv_headers WHERE id = ?",
        (jv_id,)
    ).fetchone()
    period_conn.close()

    if period_row and not is_period_open(period_row[0]):
        st.divider()
        st.error(
            f"{month_label(period_row[0])} is CLOSED. "
            "UBS posting confirmation is locked."
        )
        return

    st.divider()
    st.subheader("UBS Posting")

    st.info(
        "After the approved JV has been manually posted into UBS, "
        "confirm the posting here. This action finalises and locks the JV."
    )

    confirm = st.checkbox(
        "I confirm that this approved JV has been posted into UBS.",
        key=f"confirm_ubs_{jv_id}"
    )

    if st.button(
        "Mark as Posted to UBS",
        type="primary",
        use_container_width=True,
        disabled=not confirm,
        key=f"post_ubs_{jv_id}"
    ):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn = get_connection()

        # Re-check status at the moment of update to prevent an invalid transition.
        current = conn.execute("""
            SELECT status, prepared_by
            FROM jv_headers
            WHERE id = ?
        """, (jv_id,)).fetchone()

        if not current:
            conn.close()
            st.error("JV not found.")
            return

        current_status, current_preparer = current

        if current_preparer != employee_no:
            conn.close()
            st.error("Only the JV preparer can confirm UBS posting.")
            return

        if current_status != "APPROVED":
            conn.close()
            st.error(
                "Only an APPROVED JV can be marked as Posted to UBS."
            )
            return

        cursor = conn.execute("""
            UPDATE jv_headers
            SET
                status = 'POSTED TO UBS',
                posted_by = ?,
                posted_at = ?
            WHERE id = ?
            AND status = 'APPROVED'
            AND prepared_by = ?
        """, (
            employee_no,
            now,
            jv_id,
            employee_no
        ))

        conn.commit()
        changed = cursor.rowcount
        conn.close()

        if changed != 1:
            st.error(
                "The JV status changed before posting could be recorded. "
                "Please refresh and check the JV."
            )
            return

        add_audit_log(
            jv_id,
            jv_number,
            "JV_POSTED_TO_UBS",
            employee_no,
            employee_name,
            "PREPARER",
            "Approved JV manually posted to UBS and finalised."
        )

        st.success(
            f"{jv_number} marked as Posted to UBS and locked."
        )
        st.rerun()


def show_month_list(
    title,
    month_rows,
    session_key
):

    st.subheader(title)

    if not month_rows:

        st.info(
            "No records found."
        )
        return

    for period, total in month_rows:

        c1, c2 = st.columns(
            [4, 1]
        )

        c1.write(
            f"### {month_label(period)}"
        )

        with c2:

            if st.button(
                f"{total} JV",
                key=f"{session_key}_{period}"
            ):

                st.session_state[session_key] = period
                st.rerun()

        st.divider()


# =========================================================
# SESSION STATE
# =========================================================

defaults = {
    "logged_in": False,
    "employee_no": None,
    "user_name": None,
    "role": None,
    "page": "Dashboard",

    "dashboard_status": None,
    "dashboard_month": None,
    "dashboard_jv_id": None,

    "myjv_month": None,
    "myjv_jv_id": None,

    "approval_month": None,
    "approval_jv_id": None,

    "search_month": None,
    "search_jv_id": None,

    "audit_month": None,
    "amend_jv_id": None
}

for key, value in defaults.items():

    if key not in st.session_state:
        st.session_state[key] = value


# =========================================================
# LOGIN / LOGOUT
# =========================================================

def login(employee_no, password):
    row = get_user(employee_no)
    if not row:
        return False

    (
        db_employee_no,
        employee_name,
        password_hash,
        salt,
        user_role,
        user_status,
        entity
    ) = row

    if user_status != "ACTIVE":
        return False

    if not verify_password(password, password_hash, salt):
        return False

    st.session_state.logged_in = True
    st.session_state.employee_no = db_employee_no
    st.session_state.user_name = employee_name
    st.session_state.role = user_role
    st.session_state.page = "Dashboard"
    return True


def reset_drilldowns():

    keys = [
        "dashboard_status",
        "dashboard_month",
        "dashboard_jv_id",
        "myjv_month",
        "myjv_jv_id",
        "approval_month",
        "approval_jv_id",
        "search_month",
        "search_jv_id",
        "audit_month",
        "amend_jv_id"
    ]

    for key in keys:
        st.session_state[key] = None


def logout():

    st.session_state.logged_in = False
    st.session_state.employee_no = None
    st.session_state.user_name = None
    st.session_state.role = None
    st.session_state.page = "Dashboard"

    reset_drilldowns()

    st.rerun()


seed_demo_users()


seed_gl_master()
seed_jv_types()


# =========================================================
# LOGIN SCREEN
# =========================================================

if not st.session_state.logged_in:

    st.title(
        "Electronic Journal Voucher System"
    )

    st.caption(
        "JKPSD Pilot"
    )

    employee_no = st.text_input(
        "Employee Number"
    )

    password = st.text_input(
        "Password",
        type="password"
    )

    if st.button(
        "Login",
        type="primary"
    ):

        if login(
            employee_no,
            password
        ):

            st.rerun()

        else:

            st.error(
                "Invalid Employee Number or Password."
            )

    st.stop()


employee_no = st.session_state.employee_no
user_name = st.session_state.user_name
role = st.session_state.role


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    st.title("E-JV")

    st.write(
        f"**{user_name}**"
    )

    st.caption(
        f"Employee No: {employee_no}"
    )

    st.caption(
        f"Role: {role}"
    )

    st.divider()

    if role == "PREPARER":

        menu_options = [
            "Dashboard",
            "Create New JV",
            "My JVs",
            "Notifications",
            "New PIC Request"
        ]

    elif role == "APPROVER":

        menu_options = [
            "Dashboard",
            "Approval Inbox",
            "Search JVs",
            "Notifications",
            "New PIC Request"
        ]

    elif role == "AUDITOR":

        menu_options = [
            "Dashboard",
            "Search JVs",
            "Audit Trail"
        ]

    elif role == "ADMIN":

        menu_options = [
            "Dashboard",
            "User Management",
            "G/L Master",
            "JV Type Master",
            "Period Control"
        ]

    else:

        menu_options = [
            "Dashboard"
        ]

    if role in ["PREPARER", "APPROVER"]:
        unread_count = unread_notification_count(employee_no)

        if unread_count > 0:
            st.caption(
                f"🔔 {unread_count} unread notification"
                f"{'s' if unread_count != 1 else ''}"
            )

    selected_page = st.radio(
        "Navigation",
        menu_options
    )

    if selected_page != st.session_state.page:

        st.session_state.page = selected_page
        reset_drilldowns()

    st.divider()

    if st.button("Logout"):
        logout()


# =========================================================
# HEADER
# =========================================================

st.title(
    "Electronic Journal Voucher System"
)

st.caption(
    "JKPSD Pilot"
)

st.divider()


# =========================================================
# DASHBOARD
# =========================================================

if st.session_state.page == "Dashboard":

    st.header(
        "Dashboard"
    )

    conn = get_connection()


    # PREPARER
    if role == "PREPARER":

        draft_count = conn.execute("""
            SELECT COUNT(*)
            FROM jv_headers
            WHERE prepared_by = ?
            AND status = 'DRAFT'
        """, (
            employee_no,
        )).fetchone()[0]

        pending_count = conn.execute("""
            SELECT COUNT(*)
            FROM jv_headers
            WHERE prepared_by = ?
            AND status IN (
                'PENDING APPROVAL',
                'RESUBMITTED'
            )
        """, (
            employee_no,
        )).fetchone()[0]

        amendment_count = conn.execute("""
            SELECT COUNT(*)
            FROM jv_headers
            WHERE prepared_by = ?
            AND status = 'AMENDMENT REQUIRED'
        """, (
            employee_no,
        )).fetchone()[0]

        approved_count = conn.execute("""
            SELECT COUNT(*)
            FROM jv_headers
            WHERE prepared_by = ?
            AND status IN (
                'APPROVED',
                'POSTED TO UBS'
            )
        """, (
            employee_no,
        )).fetchone()[0]

        c1, c2, c3, c4 = st.columns(4)

        with c1:

            if st.button(
                f"Draft\n\n{draft_count}",
                use_container_width=True
            ):

                st.session_state.dashboard_status = "DRAFT"
                st.rerun()

        with c2:

            if st.button(
                f"Pending Approval\n\n{pending_count}",
                use_container_width=True
            ):

                st.session_state.dashboard_status = "PENDING"
                st.rerun()

        with c3:

            if st.button(
                f"Amendment Required\n\n{amendment_count}",
                use_container_width=True
            ):

                st.session_state.dashboard_status = "AMENDMENT"
                st.rerun()

        with c4:

            if st.button(
                f"Approved\n\n{approved_count}",
                use_container_width=True
            ):

                st.session_state.dashboard_status = "APPROVED"
                st.rerun()


    # APPROVER
    elif role == "APPROVER":

        pending_count = conn.execute("""
            SELECT COUNT(*)
            FROM jv_headers
            WHERE status IN (
                'PENDING APPROVAL',
                'RESUBMITTED'
            )
        """).fetchone()[0]

        approved_count = conn.execute("""
            SELECT COUNT(*)
            FROM jv_headers
            WHERE approved_by = ?
            AND status IN (
                'APPROVED',
                'POSTED TO UBS'
            )
        """, (
            employee_no,
        )).fetchone()[0]

        returned_count = conn.execute("""
            SELECT COUNT(DISTINCT jv_id)
            FROM audit_log
            WHERE employee_no = ?
            AND event_type = 'JV_RETURNED'
        """, (
            employee_no,
        )).fetchone()[0]

        c1, c2, c3 = st.columns(3)

        with c1:

            if st.button(
                f"Pending Approval\n\n{pending_count}",
                use_container_width=True
            ):

                st.session_state.dashboard_status = "PENDING"
                st.rerun()

        with c2:

            if st.button(
                f"Approved\n\n{approved_count}",
                use_container_width=True
            ):

                st.session_state.dashboard_status = "APPROVED"
                st.rerun()

        with c3:

            if st.button(
                f"Returned\n\n{returned_count}",
                use_container_width=True
            ):

                st.session_state.dashboard_status = "RETURNED"
                st.rerun()


    # AUDITOR
    elif role == "AUDITOR":

        total_count = conn.execute("""
            SELECT COUNT(*)
            FROM jv_headers
            WHERE status IN (
                'APPROVED',
                'POSTED TO UBS'
            )
        """).fetchone()[0]

        approved_count = conn.execute("""
            SELECT COUNT(*)
            FROM jv_headers
            WHERE status = 'APPROVED'
        """).fetchone()[0]

        posted_count = conn.execute("""
            SELECT COUNT(*)
            FROM jv_headers
            WHERE status = 'POSTED TO UBS'
        """).fetchone()[0]

        audit_count = conn.execute("""
            SELECT COUNT(*)
            FROM audit_log
        """).fetchone()[0]

        c1, c2, c3, c4 = st.columns(4)

        with c1:

            if st.button(
                f"All JV Records\n\n{total_count}",
                use_container_width=True
            ):

                st.session_state.dashboard_status = "ALL"
                st.rerun()

        with c2:

            if st.button(
                f"Approved\n\n{approved_count}",
                use_container_width=True
            ):

                st.session_state.dashboard_status = "APPROVED"
                st.rerun()

        with c3:

            if st.button(
                f"Posted to UBS\n\n{posted_count}",
                use_container_width=True
            ):

                st.session_state.dashboard_status = "POSTED"
                st.rerun()

        with c4:

            st.metric(
                "Audit Records",
                audit_count
            )


    # ADMIN
    elif role == "ADMIN":

        c1, c2, c3, c4 = st.columns(4)

        active_user_count = conn.execute("""
            SELECT COUNT(*)
            FROM users
            WHERE status = 'ACTIVE'
        """).fetchone()[0]

        c1.metric(
            "Active Users",
            active_user_count
        )

        active_gl_count = conn.execute("""
            SELECT COUNT(*)
            FROM gl_master
            WHERE entity = 'JKPSD'
            AND status = 'ACTIVE'
        """).fetchone()[0]

        c2.metric(
            "Active G/L Codes",
            active_gl_count
        )

        configured_open_periods = conn.execute("""
            SELECT COUNT(*)
            FROM accounting_periods
            WHERE entity = 'JKPSD'
            AND status = 'OPEN'
        """).fetchone()[0]

        c3.metric(
            "Open Periods",
            configured_open_periods
        )

        active_jv_type_count = conn.execute("""
            SELECT COUNT(*)
            FROM jv_type_master
            WHERE entity = 'JKPSD'
            AND status = 'ACTIVE'
        """).fetchone()[0]

        c4.metric(
            "JV Types",
            active_jv_type_count
        )

    conn.close()


    # -----------------------------------------------------
    # DASHBOARD DRILLDOWN
    # -----------------------------------------------------

    selected_status = st.session_state.dashboard_status

    if selected_status:

        st.divider()

        if st.button(
            "← Back to Dashboard"
        ):

            st.session_state.dashboard_status = None
            st.session_state.dashboard_month = None
            st.session_state.dashboard_jv_id = None
            st.rerun()


        # DETAIL
        if st.session_state.dashboard_jv_id:

            if st.button(
                "← Back to JV List"
            ):

                st.session_state.dashboard_jv_id = None
                st.rerun()

            show_jv_detail(
                st.session_state.dashboard_jv_id
            )

            if role == "PREPARER":
                render_draft_controls(
                    st.session_state.dashboard_jv_id,
                    employee_no,
                    user_name
                )

                render_post_to_ubs_control(
                    st.session_state.dashboard_jv_id,
                    employee_no,
                    user_name
                )

                render_amendment_controls(
                    st.session_state.dashboard_jv_id,
                    employee_no,
                    user_name
                )


        # JV LIST
        elif st.session_state.dashboard_month:

            selected_month = (
                st.session_state.dashboard_month
            )

            if st.button(
                "← Back to Months"
            ):

                st.session_state.dashboard_month = None
                st.rerun()

            st.subheader(
                month_label(selected_month)
            )

            conn = get_connection()

            query = """
                SELECT
                    id,
                    jv_number,
                    jv_type,
                    total_debit,
                    status,
                    prepared_name
                FROM jv_headers
                WHERE accounting_period = ?
            """

            params = [
                selected_month
            ]

            if role == "PREPARER":

                query += """
                    AND prepared_by = ?
                """

                params.append(
                    employee_no
                )

                if selected_status == "DRAFT":

                    query += """
                        AND status = 'DRAFT'
                    """

                elif selected_status == "PENDING":

                    query += """
                        AND status IN (
                            'PENDING APPROVAL',
                            'RESUBMITTED'
                        )
                    """

                elif selected_status == "AMENDMENT":

                    query += """
                        AND status = 'AMENDMENT REQUIRED'
                    """

                elif selected_status == "APPROVED":

                    query += """
                        AND status IN (
                            'APPROVED',
                            'POSTED TO UBS'
                        )
                    """

            elif role == "APPROVER":

                if selected_status == "PENDING":

                    query += """
                        AND status IN (
                            'PENDING APPROVAL',
                            'RESUBMITTED'
                        )
                    """

                elif selected_status == "APPROVED":

                    query += """
                        AND approved_by = ?
                        AND status IN (
                            'APPROVED',
                            'POSTED TO UBS'
                        )
                    """

                    params.append(
                        employee_no
                    )

                elif selected_status == "RETURNED":

                    query += """
                        AND id IN (
                            SELECT jv_id
                            FROM audit_log
                            WHERE employee_no = ?
                            AND event_type = 'JV_RETURNED'
                        )
                    """

                    params.append(
                        employee_no
                    )

            elif role == "AUDITOR":

                if selected_status == "ALL":

                    query += """
                        AND status IN (
                            'APPROVED',
                            'POSTED TO UBS'
                        )
                    """

                elif selected_status == "APPROVED":

                    query += """
                        AND status = 'APPROVED'
                    """

                elif selected_status == "POSTED":

                    query += """
                        AND status = 'POSTED TO UBS'
                    """

            query += """
                ORDER BY id DESC
            """

            result = conn.execute(
                query,
                params
            ).fetchall()

            conn.close()

            if not result:

                st.info(
                    "No JV records for this month."
                )

            else:

                for row in result:

                    (
                        jv_id,
                        jv_number,
                        jv_type,
                        amount,
                        status,
                        preparer
                    ) = row

                    c1, c2, c3, c4 = st.columns(
                        [2, 2, 2, 1]
                    )

                    c1.write(
                        f"**{jv_number}**"
                    )

                    c2.write(
                        jv_type
                    )

                    c3.write(
                        f"RM {amount:,.2f}"
                    )

                    with c4:

                        if st.button(
                            "Open",
                            key=f"dash_open_{jv_id}"
                        ):

                            st.session_state.dashboard_jv_id = jv_id
                            st.rerun()

                    st.caption(
                        f"{status} | Preparer: {preparer}"
                    )

                    st.divider()


        # MONTH LIST
        else:

            conn = get_connection()

            query = """
                SELECT
                    accounting_period,
                    COUNT(*)
                FROM jv_headers
                WHERE 1 = 1
            """

            params = []

            if role == "PREPARER":

                query += """
                    AND prepared_by = ?
                """

                params.append(
                    employee_no
                )

                if selected_status == "DRAFT":

                    query += """
                        AND status = 'DRAFT'
                    """

                elif selected_status == "PENDING":

                    query += """
                        AND status IN (
                            'PENDING APPROVAL',
                            'RESUBMITTED'
                        )
                    """

                elif selected_status == "AMENDMENT":

                    query += """
                        AND status = 'AMENDMENT REQUIRED'
                    """

                elif selected_status == "APPROVED":

                    query += """
                        AND status IN (
                            'APPROVED',
                            'POSTED TO UBS'
                        )
                    """

            elif role == "APPROVER":

                if selected_status == "PENDING":

                    query += """
                        AND status IN (
                            'PENDING APPROVAL',
                            'RESUBMITTED'
                        )
                    """

                elif selected_status == "APPROVED":

                    query += """
                        AND approved_by = ?
                        AND status IN (
                            'APPROVED',
                            'POSTED TO UBS'
                        )
                    """

                    params.append(
                        employee_no
                    )

                elif selected_status == "RETURNED":

                    query += """
                        AND id IN (
                            SELECT jv_id
                            FROM audit_log
                            WHERE employee_no = ?
                            AND event_type = 'JV_RETURNED'
                        )
                    """

                    params.append(
                        employee_no
                    )

            elif role == "AUDITOR":

                if selected_status == "ALL":

                    query += """
                        AND status IN (
                            'APPROVED',
                            'POSTED TO UBS'
                        )
                    """

                elif selected_status == "APPROVED":

                    query += """
                        AND status = 'APPROVED'
                    """

                elif selected_status == "POSTED":

                    query += """
                        AND status = 'POSTED TO UBS'
                    """

            query += """
                GROUP BY accounting_period
                ORDER BY accounting_period DESC
            """

            month_rows = conn.execute(
                query,
                params
            ).fetchall()

            conn.close()

            st.subheader(
                "Select Accounting Month"
            )

            if not month_rows:

                st.info(
                    "No JV records found."
                )

            else:

                for period, total in month_rows:

                    c1, c2 = st.columns(
                        [4, 1]
                    )

                    c1.write(
                        f"### {month_label(period)}"
                    )

                    with c2:

                        if st.button(
                            f"{total} JV",
                            key=f"dash_month_{period}"
                        ):

                            st.session_state.dashboard_month = period
                            st.rerun()

                    st.divider()


# =========================================================
# CREATE NEW JV
# =========================================================

elif st.session_state.page == "Create New JV":

    if role != "PREPARER":

        st.error(
            "Access denied."
        )

        st.stop()

    col1, col2 = st.columns(
        [3, 1]
    )

    with col1:

        st.markdown(
            "### JK PSD SDN BHD"
        )

        st.markdown(
            "## JOURNAL VOUCHER"
        )

    accounting_period = st.date_input(
        "Accounting Month",
        value=date.today()
    )

    jv_number = generate_jv_number(
        accounting_period
    )

    selected_period_status = get_period_status(
        accounting_period
    )

    with col2:

        st.markdown(
            "### JV No."
        )

        st.markdown(
            f"## {jv_number}"
        )

    c1, c2 = st.columns(2)

    with c1:

        active_jv_types = get_jv_type_options(
            include_inactive=False
        )

        jv_type = st.selectbox(
            "JV Type",
            active_jv_types
        )

        selected_jv_type_rule = get_jv_type_rule(
            jv_type
        )

        if selected_jv_type_rule:
            st.caption(
                "Supporting document: "
                f"{selected_jv_type_rule['attachment_rule'].title()}"
            )

            if selected_jv_type_rule["notes"]:
                st.caption(
                    selected_jv_type_rule["notes"]
                )

    remarks = st.text_input(
        "JV Description / Remarks"
    )

    if selected_period_status == "CLOSED":
        st.error(
            f"{month_label(accounting_period.strftime('%Y-%m'))} is CLOSED. "
            "New JVs cannot be submitted for this accounting month."
        )
    else:
        st.caption(
            f"Accounting period status: {selected_period_status}"
        )

    st.divider()

    st.subheader(
        "Journal Entries"
    )

    initial_journal = pd.DataFrame(
        [
            {
                "Date": None,
                "A/C Code": None,
                "Description": "",
                "Dr": 0.00,
                "Cr": 0.00
            },
            {
                "Date": None,
                "A/C Code": None,
                "Description": "",
                "Dr": 0.00,
                "Cr": 0.00
            }
        ]
    )

    journal_df = st.data_editor(
        initial_journal,
        num_rows="dynamic",
        hide_index=True,
        use_container_width=True,
        column_config={
            "Date": st.column_config.DateColumn(
                "Date",
                format="DD/MM/YYYY"
            ),
            "A/C Code": st.column_config.SelectboxColumn(
                "A/C Code",
                options=get_gl_options(include_inactive=False)
            ),
            "Description": st.column_config.TextColumn(
                "Description",
                width="large"
            ),
            "Dr": st.column_config.NumberColumn(
                "Dr",
                min_value=0.00,
                format="%.2f"
            ),
            "Cr": st.column_config.NumberColumn(
                "Cr",
                min_value=0.00,
                format="%.2f"
            )
        },
        key="journal_editor"
    )

    debit_series = pd.to_numeric(
        journal_df["Dr"],
        errors="coerce"
    ).fillna(0)

    credit_series = pd.to_numeric(
        journal_df["Cr"],
        errors="coerce"
    ).fillna(0)

    total_debit = round(
        float(debit_series.sum()),
        2
    )

    total_credit = round(
        float(credit_series.sum()),
        2
    )

    difference = round(
        total_debit - total_credit,
        2
    )

    st.divider()

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Total Dr",
        f"RM {total_debit:,.2f}"
    )

    c2.metric(
        "Total Cr",
        f"RM {total_credit:,.2f}"
    )

    c3.metric(
        "Difference",
        f"RM {difference:,.2f}"
    )

    st.divider()

    attachment_label = "Supporting Documents"

    if (
        selected_jv_type_rule
        and selected_jv_type_rule["attachment_rule"] == "REQUIRED"
    ):
        attachment_label += " (Required)"
    else:
        attachment_label += " (Optional)"

    uploaded_files = st.file_uploader(
        attachment_label,
        type=[
            "pdf",
            "xlsx",
            "xls",
            "docx",
            "jpg",
            "jpeg",
            "png"
        ],
        accept_multiple_files=True
    )

    st.caption(
        "Files uploaded here will be linked to this JV. "
        "Multiple documents are allowed."
    )

    errors = []
    active_rows = []

    for index, row in journal_df.iterrows():

        debit = float(
            debit_series.iloc[index]
        )

        credit = float(
            credit_series.iloc[index]
        )

        has_data = (
            pd.notna(row["Date"])
            or pd.notna(row["A/C Code"])
            or str(row["Description"]).strip() != ""
            or debit > 0
            or credit > 0
        )

        if has_data:
            active_rows.append(index)

    if len(active_rows) < 2:

        errors.append(
            "Minimum two journal lines required."
        )

    for index in active_rows:

        row = journal_df.iloc[index]

        debit = float(
            debit_series.iloc[index]
        )

        credit = float(
            credit_series.iloc[index]
        )

        line_no = index + 1

        if pd.isna(row["Date"]):

            errors.append(
                f"Line {line_no}: Date required."
            )

        if pd.isna(row["A/C Code"]):

            errors.append(
                f"Line {line_no}: A/C Code required."
            )

        elif not gl_is_active(row["A/C Code"]):

            errors.append(
                f"Line {line_no}: A/C Code is inactive or invalid."
            )

        if str(
            row["Description"]
        ).strip() == "":

            errors.append(
                f"Line {line_no}: Description required."
            )

        if debit > 0 and credit > 0:

            errors.append(
                f"Line {line_no}: Enter Dr or Cr only."
            )

        if debit == 0 and credit == 0:

            errors.append(
                f"Line {line_no}: Amount required."
            )

    if total_debit == 0:

        errors.append(
            "JV total cannot be zero."
        )

    if total_debit != total_credit:

        errors.append(
            f"Dr RM{total_debit:,.2f} "
            f"does not match "
            f"Cr RM{total_credit:,.2f}."
        )

    errors.extend(
        validate_journal_dates_against_period(
            journal_df,
            accounting_period
        )
    )

    if not jv_type_is_active(jv_type):
        errors.append(
            "Selected JV Type is inactive or invalid."
        )

    if (
        selected_jv_type_rule
        and selected_jv_type_rule["attachment_rule"] == "REQUIRED"
        and not uploaded_files
    ):
        errors.append(
            f"Supporting document is required for JV Type: {jv_type}."
        )

    if selected_period_status == "CLOSED":
        errors.append(
            "Submission is not allowed because the accounting period is CLOSED."
        )

    if errors:

        st.error(
            "JV not ready."
        )

        with st.expander(
            "Validation issues"
        ):

            for error in errors:

                st.write(
                    f"• {error}"
                )

        submit_disabled = True

    else:

        st.success(
            "Balanced ✓"
        )

        submit_disabled = False

    c1, c2 = st.columns(2)

    with c1:

        if st.button(
            "Save Draft",
            use_container_width=True,
            disabled=selected_period_status == "CLOSED"
        ):

            draft_id = save_new_draft(
                jv_number,
                jv_type,
                accounting_period,
                remarks,
                journal_df,
                total_debit,
                total_credit,
                uploaded_files,
                employee_no,
                user_name
            )

            st.success(
                f"{jv_number} saved as Draft."
            )

            st.info(
                "Open My JVs to continue or submit this Draft."
            )

            st.rerun()

    with c2:

        if st.button(
            "Submit for Approval",
            type="primary",
            disabled=submit_disabled,
            use_container_width=True
        ):

            save_jv(
                jv_number,
                jv_type,
                accounting_period,
                remarks,
                journal_df,
                total_debit,
                total_credit,
                uploaded_files,
                employee_no,
                user_name
            )

            st.success(
                f"{jv_number} submitted successfully."
            )

            st.info(
                "Available in Approver's Approval Inbox."
            )


# =========================================================
# PREPARER - MY JVs
# =========================================================

elif st.session_state.page == "My JVs":

    if role != "PREPARER":

        st.error(
            "Access denied."
        )

        st.stop()

    st.header(
        "My JVs"
    )


    # JV DETAIL
    if st.session_state.myjv_jv_id:

        if st.button(
            "← Back to JV List"
        ):

            st.session_state.myjv_jv_id = None
            st.rerun()

        show_jv_detail(
            st.session_state.myjv_jv_id
        )

        render_draft_controls(
            st.session_state.myjv_jv_id,
            employee_no,
            user_name
        )

        render_amendment_controls(
            st.session_state.myjv_jv_id,
            employee_no,
            user_name
        )

        render_post_to_ubs_control(
            st.session_state.myjv_jv_id,
            employee_no,
            user_name
        )


    # JV LIST
    elif st.session_state.myjv_month:

        if st.button(
            "← Back to Months"
        ):

            st.session_state.myjv_month = None
            st.rerun()

        selected_month = (
            st.session_state.myjv_month
        )

        st.subheader(
            month_label(selected_month)
        )

        conn = get_connection()

        rows = conn.execute("""
            SELECT
                id,
                jv_number,
                jv_type,
                total_debit,
                status
            FROM jv_headers
            WHERE prepared_by = ?
            AND accounting_period = ?
            ORDER BY id DESC
        """, (
            employee_no,
            selected_month
        )).fetchall()

        conn.close()

        if not rows:

            st.info(
                "No JV records."
            )

        else:

            for row in rows:

                (
                    jv_id,
                    jv_number,
                    jv_type,
                    amount,
                    status
                ) = row

                c1, c2, c3, c4 = st.columns(
                    [2, 2, 2, 1]
                )

                c1.write(
                    f"**{jv_number}**"
                )

                c2.write(
                    jv_type
                )

                c3.write(
                    f"RM {amount:,.2f}"
                )

                with c4:

                    if st.button(
                        "Open",
                        key=f"myjv_open_{jv_id}"
                    ):

                        st.session_state.myjv_jv_id = jv_id
                        st.rerun()

                st.caption(
                    status
                )

                st.divider()


    # MONTH LIST
    else:

        conn = get_connection()

        month_rows = conn.execute("""
            SELECT
                accounting_period,
                COUNT(*)
            FROM jv_headers
            WHERE prepared_by = ?
            GROUP BY accounting_period
            ORDER BY accounting_period DESC
        """, (
            employee_no,
        )).fetchall()

        conn.close()

        if not month_rows:

            st.info(
                "No JV records."
            )

        else:

            for period, total in month_rows:

                c1, c2 = st.columns(
                    [4, 1]
                )

                c1.write(
                    f"### {month_label(period)}"
                )

                with c2:

                    if st.button(
                        f"{total} JV",
                        key=f"myjv_month_{period}"
                    ):

                        st.session_state.myjv_month = period
                        st.rerun()

                st.divider()


# =========================================================
# APPROVER - APPROVAL INBOX
# =========================================================

elif st.session_state.page == "Approval Inbox":

    if role != "APPROVER":

        st.error(
            "Access denied."
        )

        st.stop()

    st.header(
        "Approval Inbox"
    )


    # DETAIL + APPROVAL ACTION
    if st.session_state.approval_jv_id:

        if st.button(
            "← Back to JV List"
        ):

            st.session_state.approval_jv_id = None
            st.rerun()

        selected_jv_id = (
            st.session_state.approval_jv_id
        )

        show_jv_detail(
            selected_jv_id
        )

        conn = get_connection()

        selected_row = conn.execute("""
            SELECT
                jv_number,
                prepared_by,
                accounting_period
            FROM jv_headers
            WHERE id = ?
        """, (
            selected_jv_id,
        )).fetchone()

        conn.close()

        selected_jv_number = selected_row[0]
        preparer_no = selected_row[1]
        selected_accounting_period = selected_row[2]
        approval_period_open = is_period_open(selected_accounting_period)

        if not approval_period_open:
            st.error(
                f"{month_label(selected_accounting_period)} is CLOSED. "
                "Approval and return actions are locked."
            )

        comments = st.text_area(
            "Reviewer Comments"
        )

        c1, c2 = st.columns(2)

        with c1:

            if st.button(
                "Return for Amendment",
                use_container_width=True
            ):

                if not approval_period_open:

                    st.error(
                        "This accounting period is CLOSED."
                    )

                elif not comments.strip():

                    st.error(
                        "Reviewer comments are required."
                    )

                elif preparer_no == employee_no:

                    st.error(
                        "Segregation of duties violation."
                    )

                else:

                    conn = get_connection()

                    conn.execute("""
                        UPDATE jv_headers
                        SET
                            status = 'AMENDMENT REQUIRED',
                            reviewer_comments = ?,
                            approved_by = NULL,
                            approved_name = NULL,
                            approved_at = NULL
                        WHERE id = ?
                    """, (
                        comments,
                        selected_jv_id
                    ))

                    conn.commit()
                    conn.close()

                    add_audit_log(
                        selected_jv_id,
                        selected_jv_number,
                        "JV_RETURNED",
                        employee_no,
                        user_name,
                        role,
                        comments
                    )

                    add_notification(
                        preparer_no,
                        f"Amendment required: {selected_jv_number}",
                        f"{selected_jv_number} was returned by {user_name}. "
                        f"Reviewer comment: {comments}",
                        "JV_RETURNED",
                        selected_jv_id,
                        selected_jv_number
                    )

                    st.success(
                        f"{selected_jv_number} returned."
                    )

                    st.session_state.approval_jv_id = None
                    st.rerun()

        with c2:

            if st.button(
                "Approve",
                type="primary",
                use_container_width=True
            ):

                if not approval_period_open:

                    st.error(
                        "This accounting period is CLOSED."
                    )

                elif preparer_no == employee_no:

                    st.error(
                        "Segregation of duties violation."
                    )

                else:

                    now = datetime.now().strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )

                    conn = get_connection()

                    conn.execute("""
                        UPDATE jv_headers
                        SET
                            status = 'APPROVED',
                            approved_by = ?,
                            approved_name = ?,
                            approved_at = ?,
                            reviewer_comments = ?
                        WHERE id = ?
                    """, (
                        employee_no,
                        user_name,
                        now,
                        comments,
                        selected_jv_id
                    ))

                    conn.commit()
                    conn.close()

                    add_audit_log(
                        selected_jv_id,
                        selected_jv_number,
                        "JV_APPROVED",
                        employee_no,
                        user_name,
                        role,
                        comments
                    )

                    add_notification(
                        preparer_no,
                        f"JV approved: {selected_jv_number}",
                        f"{selected_jv_number} was approved by {user_name}.",
                        "JV_APPROVED",
                        selected_jv_id,
                        selected_jv_number
                    )

                    st.success(
                        f"{selected_jv_number} approved."
                    )

                    st.session_state.approval_jv_id = None
                    st.rerun()


    # JV LIST
    elif st.session_state.approval_month:

        if st.button(
            "← Back to Months"
        ):

            st.session_state.approval_month = None
            st.rerun()

        selected_month = (
            st.session_state.approval_month
        )

        st.subheader(
            month_label(selected_month)
        )

        conn = get_connection()

        rows = conn.execute("""
            SELECT
                id,
                jv_number,
                jv_type,
                total_debit,
                prepared_name,
                status
            FROM jv_headers
            WHERE accounting_period = ?
            AND status IN (
                'PENDING APPROVAL',
                'RESUBMITTED'
            )
            ORDER BY id DESC
        """, (
            selected_month,
        )).fetchall()

        conn.close()

        if not rows:

            st.info(
                "No pending JVs."
            )

        else:

            for row in rows:

                (
                    jv_id,
                    jv_number,
                    jv_type,
                    amount,
                    preparer,
                    status
                ) = row

                c1, c2, c3, c4 = st.columns(
                    [2, 2, 2, 1]
                )

                c1.write(
                    f"**{jv_number}**"
                )

                c2.write(
                    jv_type
                )

                c3.write(
                    f"RM {amount:,.2f}"
                )

                with c4:

                    if st.button(
                        "Open",
                        key=f"approval_open_{jv_id}"
                    ):

                        st.session_state.approval_jv_id = jv_id
                        st.rerun()

                st.caption(
                    f"{status} | Preparer: {preparer}"
                )

                st.divider()


    # MONTH LIST
    else:

        conn = get_connection()

        month_rows = conn.execute("""
            SELECT
                accounting_period,
                COUNT(*)
            FROM jv_headers
            WHERE status IN (
                'PENDING APPROVAL',
                'RESUBMITTED'
            )
            GROUP BY accounting_period
            ORDER BY accounting_period DESC
        """).fetchall()

        conn.close()

        if not month_rows:

            st.info(
                "No JVs awaiting approval."
            )

        else:

            for period, total in month_rows:

                c1, c2 = st.columns(
                    [4, 1]
                )

                c1.write(
                    f"### {month_label(period)}"
                )

                with c2:

                    if st.button(
                        f"{total} JV",
                        key=f"approval_month_{period}"
                    ):

                        st.session_state.approval_month = period
                        st.rerun()

                st.divider()


# =========================================================
# SEARCH JVs - APPROVER / AUDITOR
# =========================================================

elif st.session_state.page == "Search JVs":

    if role not in [
        "APPROVER",
        "AUDITOR"
    ]:
        st.error("Access denied.")
        st.stop()

    st.header("Search JVs")

    if role == "AUDITOR":
        st.caption(
            "Read-only search. Auditor view shows approved/final JVs only."
        )
    else:
        st.caption(
            "Search Journal Vouchers using one or more filters."
        )

    # -----------------------------------------------------
    # JV DETAIL
    # -----------------------------------------------------
    if st.session_state.search_jv_id:

        if st.button("← Back to Search Results"):
            st.session_state.search_jv_id = None
            st.rerun()

        show_jv_detail(
            st.session_state.search_jv_id
        )

    else:

        # -------------------------------------------------
        # FILTERS
        # -------------------------------------------------
        c1, c2, c3 = st.columns(3)

        with c1:
            search_jv_no = st.text_input(
                "JV Number",
                placeholder="e.g. JV260901"
            )

            search_year = st.selectbox(
                "Year",
                ["ALL"] + [
                    str(year)
                    for year in range(2025, 2031)
                ]
            )

            search_status_options = [
                "ALL",
                "PENDING APPROVAL",
                "AMENDMENT REQUIRED",
                "RESUBMITTED",
                "APPROVED",
                "POSTED TO UBS",
                "CANCELLED"
            ]

            if role == "AUDITOR":
                search_status_options = [
                    "ALL",
                    "APPROVED",
                    "POSTED TO UBS"
                ]

            search_status = st.selectbox(
                "Status",
                search_status_options
            )

        with c2:
            month_names_search = [
                "ALL",
                "January",
                "February",
                "March",
                "April",
                "May",
                "June",
                "July",
                "August",
                "September",
                "October",
                "November",
                "December"
            ]

            search_month_name = st.selectbox(
                "Month",
                month_names_search
            )

            search_type = st.selectbox(
                "JV Type",
                ["ALL"] + get_jv_type_options(
                    include_inactive=True
                )
            )

            search_gl = st.text_input(
                "G/L Code",
                placeholder="e.g. 4100/001"
            )

        with c3:
            search_preparer = st.text_input(
                "Preparer",
                placeholder="Name or Employee No."
            )

            search_approver = st.text_input(
                "Approver",
                placeholder="Name or Employee No."
            )

            amount_from = st.number_input(
                "Amount From (RM)",
                min_value=0.0,
                value=0.0,
                step=100.0
            )

            amount_to = st.number_input(
                "Amount To (RM)",
                min_value=0.0,
                value=0.0,
                step=100.0,
                help="Leave at 0 for no upper limit."
            )

        use_approval_date = st.checkbox(
            "Filter by Approval Date"
        )

        approval_date_from = None
        approval_date_to = None

        if use_approval_date:
            d1, d2 = st.columns(2)

            with d1:
                approval_date_from = st.date_input(
                    "Approval Date From"
                )

            with d2:
                approval_date_to = st.date_input(
                    "Approval Date To"
                )

        # -------------------------------------------------
        # QUERY
        # -------------------------------------------------
        query = """
            SELECT DISTINCT
                j.id,
                j.jv_number,
                j.accounting_period,
                j.jv_type,
                j.total_debit,
                j.status,
                j.prepared_by,
                j.prepared_name,
                j.approved_by,
                j.approved_name,
                j.approved_at
            FROM jv_headers j
            LEFT JOIN jv_lines l
                ON j.id = l.jv_id
            WHERE 1 = 1
        """

        params = []

        if role == "AUDITOR":
            query += """
                AND j.status IN (
                    'APPROVED',
                    'POSTED TO UBS'
                )
            """

        if search_jv_no.strip():
            query += " AND UPPER(j.jv_number) LIKE UPPER(?)"
            params.append(
                f"%{search_jv_no.strip()}%"
            )

        if search_year != "ALL":
            query += " AND substr(j.accounting_period, 1, 4) = ?"
            params.append(search_year)

        if search_month_name != "ALL":
            month_number = (
                month_names_search.index(
                    search_month_name
                )
            )
            query += " AND substr(j.accounting_period, 6, 2) = ?"
            params.append(
                f"{month_number:02d}"
            )

        if search_status != "ALL":
            query += " AND j.status = ?"
            params.append(search_status)

        if search_type != "ALL":
            query += " AND j.jv_type = ?"
            params.append(
                clean_jv_type_label(search_type)
            )

        if search_gl.strip():
            query += " AND UPPER(l.gl_code) LIKE UPPER(?)"
            params.append(
                f"%{search_gl.strip()}%"
            )

        if search_preparer.strip():
            query += """
                AND (
                    UPPER(j.prepared_name) LIKE UPPER(?)
                    OR UPPER(j.prepared_by) LIKE UPPER(?)
                )
            """
            value = f"%{search_preparer.strip()}%"
            params.extend([value, value])

        if search_approver.strip():
            query += """
                AND (
                    UPPER(COALESCE(j.approved_name, '')) LIKE UPPER(?)
                    OR UPPER(COALESCE(j.approved_by, '')) LIKE UPPER(?)
                )
            """
            value = f"%{search_approver.strip()}%"
            params.extend([value, value])

        if amount_from > 0:
            query += " AND j.total_debit >= ?"
            params.append(float(amount_from))

        if amount_to > 0:
            query += " AND j.total_debit <= ?"
            params.append(float(amount_to))

        if use_approval_date:
            query += """
                AND date(j.approved_at) >= date(?)
                AND date(j.approved_at) <= date(?)
            """
            params.extend([
                approval_date_from.strftime("%Y-%m-%d"),
                approval_date_to.strftime("%Y-%m-%d")
            ])

        query += " ORDER BY j.accounting_period DESC, j.id DESC"

        conn = get_connection()

        rows = conn.execute(
            query,
            params
        ).fetchall()

        conn.close()

        st.divider()

        # -------------------------------------------------
        # RESULTS
        # -------------------------------------------------
        st.subheader(
            f"Search Results ({len(rows)})"
        )

        if not rows:
            st.info(
                "No JV records match the selected filters."
            )

        else:
            for row in rows:

                (
                    jv_id,
                    jv_number,
                    accounting_period,
                    jv_type,
                    amount,
                    status,
                    prepared_by,
                    prepared_name,
                    approved_by,
                    approved_name,
                    approved_at
                ) = row

                c1, c2, c3, c4 = st.columns(
                    [2, 2, 2, 1]
                )

                c1.write(
                    f"**{jv_number}**"
                )

                c2.write(
                    f"{month_label(accounting_period)}  \n{jv_type}"
                )

                c3.write(
                    f"**RM {amount:,.2f}**  \n{status}"
                )

                with c4:
                    if st.button(
                        "Open",
                        key=f"advanced_search_open_{jv_id}",
                        use_container_width=True
                    ):
                        st.session_state.search_jv_id = jv_id
                        st.rerun()

                details = (
                    f"Preparer: {prepared_name} ({prepared_by})"
                )

                if approved_name:
                    details += (
                        f" | Approver: {approved_name} ({approved_by})"
                    )

                if approved_at:
                    details += (
                        f" | Approved: {display_datetime(approved_at)}"
                    )

                st.caption(details)
                st.divider()


# =========================================================
# AUDIT TRAIL - MONTH DRILLDOWN
# =========================================================

elif st.session_state.page == "Audit Trail":

    if role != "AUDITOR":
        st.error("Access denied.")
        st.stop()

    st.header("Audit Trail")
    st.caption(
        "Read-only final audit activities. Amendment and resubmission history "
        "is not displayed in the Auditor view."
    )

    c1, c2, c3 = st.columns(3)

    with c1:
        audit_jv_search = st.text_input(
            "JV Number",
            key="audit_jv_search"
        )

    with c2:
        audit_year = st.selectbox(
            "Year",
            ["ALL"] + [
                str(year)
                for year in range(2025, 2031)
            ],
            key="audit_year_filter"
        )

    with c3:
        audit_action = st.selectbox(
            "Action",
            [
                "ALL",
                "JV_SUBMITTED",
                "JV_APPROVED",
                "JV_POSTED_TO_UBS"
            ],
            key="audit_action_filter"
        )

    audit_query = """
        SELECT
            a.jv_number AS "JV No.",
            j.accounting_period AS "Period",
            a.event_type AS "Action",
            a.employee_no AS "Employee No.",
            a.employee_name AS "Employee",
            a.role AS "Role",
            a.comments AS "Comments",
            a.event_timestamp AS "Date / Time"
        FROM audit_log a
        JOIN jv_headers j
            ON a.jv_id = j.id
        WHERE j.status IN (
            'APPROVED',
            'POSTED TO UBS'
        )
        AND a.event_type IN (
            'JV_SUBMITTED',
            'JV_APPROVED',
            'JV_POSTED_TO_UBS'
        )
    """

    audit_params = []

    if audit_jv_search.strip():
        audit_query += """
            AND UPPER(a.jv_number) LIKE UPPER(?)
        """
        audit_params.append(
            f"%{audit_jv_search.strip()}%"
        )

    if audit_year != "ALL":
        audit_query += """
            AND substr(j.accounting_period, 1, 4) = ?
        """
        audit_params.append(audit_year)

    if audit_action != "ALL":
        audit_query += " AND a.event_type = ?"
        audit_params.append(audit_action)

    audit_query += """
        ORDER BY j.accounting_period DESC, a.id DESC
    """

    conn = get_connection()

    audit_df = pd.read_sql_query(
        audit_query,
        conn,
        params=audit_params
    )

    conn.close()

    if not audit_df.empty:
        audit_df["Period"] = audit_df["Period"].apply(
            month_label
        )
        audit_df["Date / Time"] = audit_df["Date / Time"].apply(
            display_datetime
        )

    st.subheader(
        f"Audit Records ({len(audit_df)})"
    )

    if audit_df.empty:
        st.info(
            "No audit records match the selected filters."
        )
    else:
        st.dataframe(
            audit_df,
            use_container_width=True,
            hide_index=True
        )


# =========================================================
# NOTIFICATIONS
# =========================================================

elif st.session_state.page == "Notifications":

    if role not in [
        "PREPARER",
        "APPROVER"
    ]:
        st.error(
            "Access denied."
        )
        st.stop()

    st.header(
        "Notifications"
    )

    conn = get_connection()

    notification_rows = conn.execute("""
        SELECT
            id,
            jv_number,
            notification_type,
            title,
            message,
            is_read,
            created_at
        FROM notifications
        WHERE recipient_employee_no = ?
        ORDER BY id DESC
        LIMIT 100
    """, (
        employee_no,
    )).fetchall()

    conn.close()

    unread_count = sum(
        1
        for row in notification_rows
        if row[5] == 0
    )

    c1, c2 = st.columns(
        [3, 1]
    )

    c1.write(
        f"**Unread: {unread_count}**"
    )

    with c2:

        if st.button(
            "Mark all as read",
            use_container_width=True,
            disabled=unread_count == 0
        ):
            mark_all_notifications_read(
                employee_no
            )
            st.rerun()

    st.divider()

    if not notification_rows:

        st.info(
            "No notifications yet."
        )

    else:

        for row in notification_rows:

            (
                notification_id,
                jv_number,
                notification_type,
                title,
                message,
                is_read,
                created_at
            ) = row

            icon = "🔵" if not is_read else "⚪"

            c1, c2 = st.columns(
                [5, 1]
            )

            with c1:

                st.write(
                    f"{icon} **{title}**"
                )

                st.write(
                    message
                )

                st.caption(
                    display_datetime(created_at)
                )

            with c2:

                if not is_read:

                    if st.button(
                        "Mark read",
                        key=f"read_notification_{notification_id}",
                        use_container_width=True
                    ):

                        mark_notification_read(
                            notification_id,
                            employee_no
                        )

                        st.rerun()

            st.divider()


# =========================================================
# NEW PIC REQUEST
# =========================================================

elif st.session_state.page == "New PIC Request":

    if role not in ["PREPARER", "APPROVER"]:
        st.error("Access denied.")
        st.stop()

    st.header("New PIC / User Change Request")
    st.caption(
        "Submitting this request does not create access immediately. "
        "Admin must review and approve the request."
    )

    c1, c2 = st.columns(2)

    with c1:
        new_employee_no = st.text_input("New Employee Number")
        new_employee_name = st.text_input("New Employee Name")

    with c2:
        requested_role = st.selectbox(
            "Requested Role",
            ["PREPARER", "APPROVER"]
        )
        effective_date = st.date_input("Effective Date")

    reason = st.selectbox(
        "Reason",
        [
            "Replacement of Existing PIC",
            "Staff Transfer",
            "New Finance PIC",
            "Other"
        ]
    )

    comments = st.text_area("Comments")

    if st.button("Submit PIC Request", type="primary"):

        if not new_employee_no.strip():
            st.error("New Employee Number is required.")

        elif not new_employee_name.strip():
            st.error("New Employee Name is required.")

        else:
            conn = get_connection()

            duplicate_user = conn.execute(
                "SELECT 1 FROM users WHERE employee_no = ?",
                (new_employee_no.strip(),)
            ).fetchone()

            duplicate_request = conn.execute("""
                SELECT 1
                FROM pic_requests
                WHERE new_employee_no = ?
                AND status = 'PENDING'
            """, (new_employee_no.strip(),)).fetchone()

            if duplicate_user:
                conn.close()
                st.error("This Employee Number already has a user account.")

            elif duplicate_request:
                conn.close()
                st.error("A pending PIC request already exists for this Employee Number.")

            else:
                conn.execute("""
                    INSERT INTO pic_requests (
                        requested_by, requested_by_name,
                        new_employee_no, new_employee_name,
                        requested_role, effective_date,
                        reason, comments, status, requested_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'PENDING', ?)
                """, (
                    employee_no,
                    user_name,
                    new_employee_no.strip(),
                    new_employee_name.strip(),
                    requested_role,
                    effective_date.strftime("%Y-%m-%d"),
                    reason,
                    comments.strip(),
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ))

                conn.commit()
                conn.close()
                st.success("PIC request submitted for Admin review.")

    st.divider()
    st.subheader("My Requests")

    conn = get_connection()
    request_df = pd.read_sql_query("""
        SELECT
            new_employee_no AS "Employee No.",
            new_employee_name AS "New PIC",
            requested_role AS "Role",
            effective_date AS "Effective Date",
            reason AS "Reason",
            status AS "Status",
            requested_at AS "Requested At",
            review_comments AS "Admin Comments"
        FROM pic_requests
        WHERE requested_by = ?
        ORDER BY id DESC
    """, conn, params=(employee_no,))
    conn.close()

    if request_df.empty:
        st.caption("No PIC requests submitted yet.")
    else:
        request_df["Effective Date"] = request_df["Effective Date"].apply(display_date)
        request_df["Requested At"] = request_df["Requested At"].apply(display_datetime)

        st.dataframe(
            request_df,
            use_container_width=True,
            hide_index=True
        )


# =========================================================
# ADMIN
# =========================================================

elif st.session_state.page == "User Management":

    if role != "ADMIN":
        st.error("Access denied.")
        st.stop()

    st.header("User Management")

    tab1, tab2, tab3 = st.tabs(
        ["PIC Requests", "User Master", "Create User"]
    )

    with tab1:
        conn = get_connection()
        requests = conn.execute("""
            SELECT
                id, requested_by, requested_by_name,
                new_employee_no, new_employee_name,
                requested_role, effective_date,
                reason, comments, requested_at
            FROM pic_requests
            WHERE status = 'PENDING'
            ORDER BY id
        """).fetchall()
        conn.close()

        if not requests:
            st.info("No pending PIC requests.")
        else:
            for request in requests:
                (
                    request_id,
                    requested_by,
                    requested_by_name,
                    new_employee_no,
                    new_employee_name,
                    requested_role,
                    effective_date,
                    reason,
                    request_comments,
                    requested_at
                ) = request

                st.subheader(f"{new_employee_name} ({new_employee_no})")

                c1, c2, c3 = st.columns(3)
                c1.write(f"**Role:** {requested_role}")
                c2.write(f"**Effective:** {display_date(effective_date)}")
                c3.write(f"**Requested by:** {requested_by_name} ({requested_by})")

                st.write(f"**Reason:** {reason}")
                if request_comments:
                    st.write(f"**Request comments:** {request_comments}")

                temporary_password = st.text_input(
                    "Temporary Password",
                    type="password",
                    key=f"temp_password_{request_id}",
                    help="Minimum 8 characters."
                )

                admin_comment = st.text_input(
                    "Admin Comment",
                    key=f"admin_comment_{request_id}"
                )

                c1, c2 = st.columns(2)

                with c1:
                    if st.button(
                        "Reject",
                        key=f"reject_pic_{request_id}",
                        use_container_width=True
                    ):
                        conn = get_connection()
                        conn.execute("""
                            UPDATE pic_requests
                            SET status = 'REJECTED',
                                reviewed_by = ?,
                                reviewed_by_name = ?,
                                reviewed_at = ?,
                                review_comments = ?
                            WHERE id = ?
                            AND status = 'PENDING'
                        """, (
                            employee_no,
                            user_name,
                            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            admin_comment.strip(),
                            request_id
                        ))
                        conn.commit()
                        conn.close()
                        st.success("PIC request rejected.")
                        st.rerun()

                with c2:
                    if st.button(
                        "Approve & Create Account",
                        type="primary",
                        key=f"approve_pic_{request_id}",
                        use_container_width=True
                    ):
                        try:
                            create_user_account(
                                new_employee_no,
                                new_employee_name,
                                requested_role,
                                temporary_password,
                                employee_no
                            )

                            conn = get_connection()
                            conn.execute("""
                                UPDATE pic_requests
                                SET status = 'APPROVED',
                                    reviewed_by = ?,
                                    reviewed_by_name = ?,
                                    reviewed_at = ?,
                                    review_comments = ?
                                WHERE id = ?
                                AND status = 'PENDING'
                            """, (
                                employee_no,
                                user_name,
                                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                admin_comment.strip(),
                                request_id
                            ))
                            conn.commit()
                            conn.close()

                            st.success(
                                f"Account {new_employee_no} created and activated."
                            )
                            st.rerun()

                        except Exception as exc:
                            st.error(str(exc))

                st.divider()

    with tab2:
        conn = get_connection()
        user_df = pd.read_sql_query("""
            SELECT
                employee_no AS "Employee No.",
                employee_name AS "Name",
                role AS "Role",
                status AS "Status",
                entity AS "Entity",
                created_at AS "Created At",
                created_by AS "Created By"
            FROM users
            ORDER BY
                CASE status
                    WHEN 'ACTIVE' THEN 0
                    ELSE 1
                END,
                employee_name
        """, conn)
        conn.close()

        if not user_df.empty:
            user_df["Created At"] = user_df["Created At"].apply(display_datetime)

        st.dataframe(
            user_df,
            use_container_width=True,
            hide_index=True
        )

        if not user_df.empty:
            selected_employee = st.selectbox(
                "Select User",
                user_df["Employee No."].tolist()
            )

            selected_status = user_df.loc[
                user_df["Employee No."] == selected_employee,
                "Status"
            ].iloc[0]

            if selected_status == "ACTIVE":
                if st.button("Deactivate Selected User"):
                    try:
                        set_user_status(
                            selected_employee,
                            "INACTIVE",
                            employee_no
                        )
                        st.success(f"{selected_employee} deactivated.")
                        st.rerun()
                    except Exception as exc:
                        st.error(str(exc))
            else:
                if st.button("Reactivate Selected User"):
                    set_user_status(
                        selected_employee,
                        "ACTIVE",
                        employee_no
                    )
                    st.success(f"{selected_employee} reactivated.")
                    st.rerun()

    with tab3:
        st.caption(
            "For exceptional cases only. Normal Preparer/Approver replacement "
            "should use the PIC Request workflow."
        )

        new_no = st.text_input(
            "Employee Number",
            key="admin_new_employee_no"
        )
        new_name = st.text_input(
            "Employee Name",
            key="admin_new_employee_name"
        )
        new_role = st.selectbox(
            "Role",
            ["PREPARER", "APPROVER", "AUDITOR", "ADMIN"],
            key="admin_new_role"
        )
        new_password = st.text_input(
            "Temporary Password",
            type="password",
            key="admin_new_password"
        )

        if st.button("Create User Account", type="primary"):
            try:
                create_user_account(
                    new_no,
                    new_name,
                    new_role,
                    new_password,
                    employee_no
                )
                st.success(f"User {new_no} created.")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))


elif st.session_state.page == "G/L Master":

    if role != "ADMIN":

        st.error(
            "Access denied."
        )

        st.stop()

    st.header(
        "G/L Master"
    )

    st.caption(
        "Only ACTIVE G/L codes are available for new Journal Vouchers."
    )

    tab1, tab2, tab3 = st.tabs(
        [
            "G/L List",
            "Add / Update G/L",
            "Change History"
        ]
    )

    # -----------------------------------------------------
    # G/L LIST
    # -----------------------------------------------------

    with tab1:

        c1, c2 = st.columns(2)

        with c1:

            status_filter = st.selectbox(
                "Status",
                [
                    "ALL",
                    "ACTIVE",
                    "INACTIVE"
                ],
                key="gl_status_filter"
            )

        with c2:

            search_gl = st.text_input(
                "Search Code / Description",
                key="gl_search"
            )

        conn = get_connection()

        query = """
            SELECT
                gl_code AS "G/L Code",
                gl_description AS "G/L Description",
                account_category AS "Account Category",
                normal_balance AS "Normal Balance",
                status AS "Status",
                effective_date AS "Effective Date",
                entity AS "Entity",
                CASE
                    WHEN cost_centre_required = 1 THEN 'Yes'
                    ELSE 'No'
                END AS "Cost Centre Required",
                validation_notes AS "Validation Notes"
            FROM gl_master
            WHERE entity = 'JKPSD'
        """

        params = []

        if status_filter != "ALL":
            query += " AND status = ?"
            params.append(status_filter)

        if search_gl.strip():
            query += """
                AND (
                    gl_code LIKE ?
                    OR gl_description LIKE ?
                )
            """
            search_value = f"%{search_gl.strip()}%"
            params.extend([
                search_value,
                search_value
            ])

        query += " ORDER BY gl_code"

        gl_df = pd.read_sql_query(
            query,
            conn,
            params=params
        )

        conn.close()

        if not gl_df.empty:
            gl_df["Effective Date"] = gl_df["Effective Date"].apply(
                display_date
            )

        st.dataframe(
            gl_df,
            use_container_width=True,
            hide_index=True
        )

    # -----------------------------------------------------
    # ADD / UPDATE
    # -----------------------------------------------------

    with tab2:

        mode = st.radio(
            "Action",
            [
                "Add New G/L",
                "Update Existing G/L"
            ],
            horizontal=True
        )

        categories = [
            "Asset",
            "Liability",
            "Equity",
            "Income",
            "Expense",
            "Investment",
            "Other"
        ]

        if mode == "Add New G/L":

            gl_code = st.text_input(
                "G/L Code",
                key="new_gl_code"
            )

            gl_description = st.text_input(
                "G/L Description",
                key="new_gl_description"
            )

            c1, c2 = st.columns(2)

            with c1:

                category = st.selectbox(
                    "Account Category",
                    categories,
                    key="new_gl_category"
                )

                normal_balance = st.selectbox(
                    "Debit / Credit Classification",
                    [
                        "DEBIT",
                        "CREDIT"
                    ],
                    key="new_gl_balance"
                )

            with c2:

                effective_date = st.date_input(
                    "Effective Date",
                    key="new_gl_effective"
                )

                cost_centre_required = st.checkbox(
                    "Cost Centre Required",
                    key="new_gl_cc"
                )

            validation_notes = st.text_area(
                "Additional Validation Notes",
                key="new_gl_notes"
            )

            if st.button(
                "Add G/L",
                type="primary",
                key="add_gl_button"
            ):

                clean_code = gl_code.strip()
                clean_description = gl_description.strip()

                if not clean_code:

                    st.error(
                        "G/L Code is required."
                    )

                elif not clean_description:

                    st.error(
                        "G/L Description is required."
                    )

                else:

                    conn = get_connection()

                    exists = conn.execute(
                        "SELECT 1 FROM gl_master WHERE gl_code = ?",
                        (clean_code,)
                    ).fetchone()

                    if exists:

                        conn.close()

                        st.error(
                            "This G/L Code already exists."
                        )

                    else:

                        now = datetime.now().strftime(
                            "%Y-%m-%d %H:%M:%S"
                        )

                        conn.execute("""
                            INSERT INTO gl_master (
                                gl_code,
                                gl_description,
                                account_category,
                                normal_balance,
                                status,
                                effective_date,
                                entity,
                                cost_centre_required,
                                validation_notes,
                                created_by,
                                created_at,
                                updated_by,
                                updated_at
                            )
                            VALUES (?, ?, ?, ?, 'ACTIVE', ?, 'JKPSD', ?, ?, ?, ?, ?, ?)
                        """, (
                            clean_code,
                            clean_description,
                            category,
                            normal_balance,
                            effective_date.strftime("%Y-%m-%d"),
                            1 if cost_centre_required else 0,
                            validation_notes.strip(),
                            employee_no,
                            now,
                            employee_no,
                            now
                        ))

                        conn.commit()
                        conn.close()

                        log_gl_history(
                            clean_code,
                            "CREATED",
                            employee_no,
                            user_name
                        )

                        st.success(
                            f"G/L {clean_code} created and activated."
                        )

                        st.rerun()

        else:

            conn = get_connection()

            existing_rows = conn.execute("""
                SELECT
                    gl_code,
                    gl_description,
                    account_category,
                    normal_balance,
                    status,
                    effective_date,
                    cost_centre_required,
                    validation_notes
                FROM gl_master
                WHERE entity = 'JKPSD'
                ORDER BY gl_code
            """).fetchall()

            conn.close()

            if not existing_rows:

                st.info(
                    "No G/L records available."
                )

            else:

                selected_code = st.selectbox(
                    "Select G/L",
                    [
                        row[0]
                        for row in existing_rows
                    ],
                    key="edit_gl_select"
                )

                selected = next(
                    row
                    for row in existing_rows
                    if row[0] == selected_code
                )

                (
                    _,
                    current_description,
                    current_category,
                    current_balance,
                    current_status,
                    current_effective_date,
                    current_cc_required,
                    current_notes
                ) = selected

                try:
                    effective_default = datetime.strptime(
                        current_effective_date,
                        "%Y-%m-%d"
                    ).date()
                except:
                    effective_default = date.today()

                gl_description = st.text_input(
                    "G/L Description",
                    value=current_description,
                    key=f"edit_gl_desc_{selected_code}"
                )

                c1, c2 = st.columns(2)

                with c1:

                    category_index = (
                        categories.index(current_category)
                        if current_category in categories
                        else len(categories) - 1
                    )

                    category = st.selectbox(
                        "Account Category",
                        categories,
                        index=category_index,
                        key=f"edit_gl_category_{selected_code}"
                    )

                    balance_options = [
                        "DEBIT",
                        "CREDIT"
                    ]

                    balance_index = (
                        balance_options.index(current_balance)
                        if current_balance in balance_options
                        else 0
                    )

                    normal_balance = st.selectbox(
                        "Debit / Credit Classification",
                        balance_options,
                        index=balance_index,
                        key=f"edit_gl_balance_{selected_code}"
                    )

                with c2:

                    effective_date = st.date_input(
                        "Effective Date",
                        value=effective_default,
                        key=f"edit_gl_effective_{selected_code}"
                    )

                    status = st.selectbox(
                        "Status",
                        [
                            "ACTIVE",
                            "INACTIVE"
                        ],
                        index=0 if current_status == "ACTIVE" else 1,
                        key=f"edit_gl_status_{selected_code}"
                    )

                    cost_centre_required = st.checkbox(
                        "Cost Centre Required",
                        value=bool(current_cc_required),
                        key=f"edit_gl_cc_{selected_code}"
                    )

                validation_notes = st.text_area(
                    "Additional Validation Notes",
                    value=current_notes or "",
                    key=f"edit_gl_notes_{selected_code}"
                )

                if st.button(
                    "Save G/L Changes",
                    type="primary",
                    key=f"save_gl_{selected_code}"
                ):

                    if not gl_description.strip():

                        st.error(
                            "G/L Description is required."
                        )

                    else:

                        log_gl_history(
                            selected_code,
                            "BEFORE_UPDATE",
                            employee_no,
                            user_name
                        )

                        now = datetime.now().strftime(
                            "%Y-%m-%d %H:%M:%S"
                        )

                        conn = get_connection()

                        conn.execute("""
                            UPDATE gl_master
                            SET
                                gl_description = ?,
                                account_category = ?,
                                normal_balance = ?,
                                status = ?,
                                effective_date = ?,
                                cost_centre_required = ?,
                                validation_notes = ?,
                                updated_by = ?,
                                updated_at = ?
                            WHERE gl_code = ?
                        """, (
                            gl_description.strip(),
                            category,
                            normal_balance,
                            status,
                            effective_date.strftime("%Y-%m-%d"),
                            1 if cost_centre_required else 0,
                            validation_notes.strip(),
                            employee_no,
                            now,
                            selected_code
                        ))

                        conn.commit()
                        conn.close()

                        log_gl_history(
                            selected_code,
                            "AFTER_UPDATE",
                            employee_no,
                            user_name
                        )

                        st.success(
                            f"G/L {selected_code} updated."
                        )

                        st.rerun()

    # -----------------------------------------------------
    # HISTORY
    # -----------------------------------------------------

    with tab3:

        conn = get_connection()

        history_df = pd.read_sql_query("""
            SELECT
                gl_code AS "G/L Code",
                action AS "Action",
                changed_by AS "Employee No.",
                changed_name AS "Changed By",
                changed_at AS "Changed At"
            FROM gl_master_history
            ORDER BY id DESC
            LIMIT 100
        """, conn)

        conn.close()

        if history_df.empty:

            st.info(
                "No G/L Master changes recorded yet."
            )

        else:

            history_df["Changed At"] = history_df["Changed At"].apply(
                display_datetime
            )

            st.dataframe(
                history_df,
                use_container_width=True,
                hide_index=True
            )


elif st.session_state.page == "JV Type Master":

    if role != "ADMIN":

        st.error(
            "Access denied."
        )

        st.stop()

    st.header(
        "JV Type Master"
    )

    st.caption(
        "Only ACTIVE JV Types can be selected for new Journal Vouchers."
    )

    tab1, tab2, tab3 = st.tabs(
        [
            "JV Type List",
            "Add / Update",
            "Change History"
        ]
    )

    # -----------------------------------------------------
    # JV TYPE LIST
    # -----------------------------------------------------

    with tab1:

        status_filter = st.selectbox(
            "Status",
            [
                "ALL",
                "ACTIVE",
                "INACTIVE"
            ],
            key="jv_type_status_filter"
        )

        conn = get_connection()

        query = """
            SELECT
                jv_type AS "JV Type",
                status AS "Status",
                attachment_rule AS "Supporting Document",
                supporting_document_notes AS "Document Notes",
                entity AS "Entity",
                updated_by AS "Updated By",
                updated_at AS "Updated At"
            FROM jv_type_master
            WHERE entity = 'JKPSD'
        """

        params = []

        if status_filter != "ALL":
            query += " AND status = ?"
            params.append(status_filter)

        query += " ORDER BY jv_type"

        type_df = pd.read_sql_query(
            query,
            conn,
            params=params
        )

        conn.close()

        if not type_df.empty:
            type_df["Updated At"] = type_df["Updated At"].apply(
                display_datetime
            )

        st.dataframe(
            type_df,
            use_container_width=True,
            hide_index=True
        )

    # -----------------------------------------------------
    # ADD / UPDATE
    # -----------------------------------------------------

    with tab2:

        mode = st.radio(
            "Action",
            [
                "Add New JV Type",
                "Update Existing JV Type"
            ],
            horizontal=True
        )

        if mode == "Add New JV Type":

            new_type = st.text_input(
                "JV Type Name",
                key="new_jv_type_name"
            )

            attachment_rule = st.selectbox(
                "Supporting Document Requirement",
                [
                    "OPTIONAL",
                    "REQUIRED"
                ],
                key="new_jv_type_attachment"
            )

            document_notes = st.text_area(
                "Supporting Document Notes",
                key="new_jv_type_notes",
                placeholder=(
                    "Example: Attach payroll summary and approved payroll schedule."
                )
            )

            if st.button(
                "Add JV Type",
                type="primary",
                key="add_jv_type_button"
            ):

                clean_type = new_type.strip()

                if not clean_type:

                    st.error(
                        "JV Type Name is required."
                    )

                else:

                    conn = get_connection()

                    exists = conn.execute(
                        "SELECT 1 FROM jv_type_master WHERE jv_type = ?",
                        (clean_type,)
                    ).fetchone()

                    if exists:

                        conn.close()

                        st.error(
                            "This JV Type already exists."
                        )

                    else:

                        now = datetime.now().strftime(
                            "%Y-%m-%d %H:%M:%S"
                        )

                        conn.execute("""
                            INSERT INTO jv_type_master (
                                jv_type,
                                status,
                                attachment_rule,
                                supporting_document_notes,
                                entity,
                                created_by,
                                created_at,
                                updated_by,
                                updated_at
                            )
                            VALUES (?, 'ACTIVE', ?, ?, 'JKPSD', ?, ?, ?, ?)
                        """, (
                            clean_type,
                            attachment_rule,
                            document_notes.strip(),
                            employee_no,
                            now,
                            employee_no,
                            now
                        ))

                        conn.commit()
                        conn.close()

                        log_jv_type_history(
                            clean_type,
                            "CREATED",
                            employee_no,
                            user_name
                        )

                        st.success(
                            f"JV Type '{clean_type}' created and activated."
                        )

                        st.rerun()

        else:

            conn = get_connection()

            existing_types = conn.execute("""
                SELECT
                    jv_type,
                    status,
                    attachment_rule,
                    supporting_document_notes
                FROM jv_type_master
                WHERE entity = 'JKPSD'
                ORDER BY jv_type
            """).fetchall()

            conn.close()

            if not existing_types:

                st.info(
                    "No JV Types available."
                )

            else:

                selected_type = st.selectbox(
                    "Select JV Type",
                    [
                        row[0]
                        for row in existing_types
                    ],
                    key="edit_jv_type_select"
                )

                selected = next(
                    row
                    for row in existing_types
                    if row[0] == selected_type
                )

                (
                    _,
                    current_status,
                    current_attachment_rule,
                    current_notes
                ) = selected

                status = st.selectbox(
                    "Status",
                    [
                        "ACTIVE",
                        "INACTIVE"
                    ],
                    index=0 if current_status == "ACTIVE" else 1,
                    key=f"jv_type_status_{selected_type}"
                )

                rule_options = [
                    "OPTIONAL",
                    "REQUIRED"
                ]

                attachment_rule = st.selectbox(
                    "Supporting Document Requirement",
                    rule_options,
                    index=(
                        rule_options.index(current_attachment_rule)
                        if current_attachment_rule in rule_options
                        else 0
                    ),
                    key=f"jv_type_rule_{selected_type}"
                )

                document_notes = st.text_area(
                    "Supporting Document Notes",
                    value=current_notes or "",
                    key=f"jv_type_notes_{selected_type}"
                )

                if st.button(
                    "Save JV Type Changes",
                    type="primary",
                    key=f"save_jv_type_{selected_type}"
                ):

                    log_jv_type_history(
                        selected_type,
                        "BEFORE_UPDATE",
                        employee_no,
                        user_name
                    )

                    now = datetime.now().strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )

                    conn = get_connection()

                    conn.execute("""
                        UPDATE jv_type_master
                        SET
                            status = ?,
                            attachment_rule = ?,
                            supporting_document_notes = ?,
                            updated_by = ?,
                            updated_at = ?
                        WHERE jv_type = ?
                    """, (
                        status,
                        attachment_rule,
                        document_notes.strip(),
                        employee_no,
                        now,
                        selected_type
                    ))

                    conn.commit()
                    conn.close()

                    log_jv_type_history(
                        selected_type,
                        "AFTER_UPDATE",
                        employee_no,
                        user_name
                    )

                    st.success(
                        f"JV Type '{selected_type}' updated."
                    )

                    st.rerun()

    # -----------------------------------------------------
    # HISTORY
    # -----------------------------------------------------

    with tab3:

        conn = get_connection()

        history_df = pd.read_sql_query("""
            SELECT
                jv_type AS "JV Type",
                action AS "Action",
                changed_by AS "Employee No.",
                changed_name AS "Changed By",
                changed_at AS "Changed At"
            FROM jv_type_history
            ORDER BY id DESC
            LIMIT 100
        """, conn)

        conn.close()

        if history_df.empty:

            st.info(
                "No JV Type changes recorded yet."
            )

        else:

            history_df["Changed At"] = history_df["Changed At"].apply(
                display_datetime
            )

            st.dataframe(
                history_df,
                use_container_width=True,
                hide_index=True
            )


elif st.session_state.page == "Period Control":

    if role != "ADMIN":

        st.error(
            "Access denied."
        )

        st.stop()

    st.header(
        "Period Control"
    )

    st.caption(
        "Closing a month locks new JV submission, amendment, "
        "resubmission, approval/return and UBS posting confirmation."
    )

    year = st.selectbox(
        "Year",
        [
            2025,
            2026,
            2027,
            2028,
            2029,
            2030
        ],
        index=1
    )

    month_names = [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December"
    ]

    month = st.selectbox(
        "Month",
        month_names
    )

    month_no = month_names.index(month) + 1
    selected_period = f"{year}-{month_no:02d}"
    current_status = get_period_status(selected_period)
    outstanding_count = get_period_outstanding_count(selected_period)

    c1, c2 = st.columns(2)

    c1.metric(
        "Current Status",
        current_status
    )

    c2.metric(
        "JV Not Finalised",
        outstanding_count
    )

    if outstanding_count > 0:
        st.warning(
            f"{outstanding_count} JV(s) are not yet Posted to UBS or Cancelled. "
            "The month cannot be closed until they are finalised."
        )
    else:
        st.success(
            "No outstanding JV prevents period closing."
        )

    desired_status = st.radio(
        "Set Period Status",
        [
            "OPEN",
            "CLOSED"
        ],
        index=0 if current_status == "OPEN" else 1,
        horizontal=True
    )

    if st.button(
        "Update Period",
        type="primary"
    ):

        try:

            set_period_status(
                selected_period,
                desired_status,
                employee_no,
                user_name
            )

            st.success(
                f"{month} {year} set to {desired_status}."
            )

            st.rerun()

        except PermissionError as exc:

            st.error(
                str(exc)
            )

    st.divider()
    st.subheader(
        "Configured Periods"
    )

    conn = get_connection()

    period_df = pd.read_sql_query("""
        SELECT
            accounting_period AS "Period",
            status AS "Status",
            updated_by AS "Updated By",
            updated_at AS "Updated At"
        FROM accounting_periods
        WHERE entity = 'JKPSD'
        ORDER BY accounting_period DESC
    """, conn)

    history_df = pd.read_sql_query("""
        SELECT
            accounting_period AS "Period",
            old_status AS "Previous",
            new_status AS "New Status",
            changed_by AS "Employee No.",
            changed_name AS "Changed By",
            changed_at AS "Changed At"
        FROM period_history
        WHERE entity = 'JKPSD'
        ORDER BY id DESC
        LIMIT 20
    """, conn)

    conn.close()

    if period_df.empty:

        st.info(
            "No period status has been explicitly configured yet. "
            "Unconfigured periods are treated as OPEN."
        )

    else:

        period_df["Period"] = period_df["Period"].apply(month_label)
        period_df["Updated At"] = period_df["Updated At"].apply(display_datetime)

        st.dataframe(
            period_df,
            use_container_width=True,
            hide_index=True
        )

    with st.expander(
        "Period Change History"
    ):

        if history_df.empty:

            st.caption(
                "No period changes recorded yet."
            )

        else:

            history_df["Period"] = history_df["Period"].apply(month_label)
            history_df["Changed At"] = history_df["Changed At"].apply(
                display_datetime
            )

            st.dataframe(
                history_df,
                use_container_width=True,
                hide_index=True
            )

