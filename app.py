import streamlit as st
import pandas as pd
import sqlite3
import json
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

USERS = {
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

    conn.commit()
    conn.close()


initialise_database()


# =========================================================
# DATABASE HELPERS
# =========================================================

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
        last_number = row[0]
        sequence = int(last_number[-2:]) + 1

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

    add_audit_log(
        jv_id,
        jv_number,
        "JV_SUBMITTED",
        employee_no,
        employee_name,
        "PREPARER",
        "Submitted for approval."
    )

    return jv_id


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


def month_label(period_text):

    if not period_text:
        return ""

    dt = datetime.strptime(
        period_text,
        "%Y-%m"
    )

    return dt.strftime("%B %Y")


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

    c1.write(f"**Month**  \n{month_label(accounting_period)}")
    c2.write(f"**JV Type**  \n{jv_type}")
    c3.write(f"**Status**  \n{status}")
    c4.write(f"**Amount**  \nRM {total_debit:,.2f}")

    if remarks:
        st.write(f"**Description:** {remarks}")

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
        f"{submitted_at or '-'}"
    )

    if approved_name:

        st.write(
            f"**Approved by:** "
            f"{approved_name} ({approved_by})"
        )

        st.write(
            f"**Approval date:** "
            f"{approved_at or '-'}"
        )

    if reviewer_comments:

        st.write(
            f"**Reviewer comments:** "
            f"{reviewer_comments}"
        )

    if posted_by:

        st.write(
            f"**Posted by:** "
            f"{posted_by}"
        )

        st.write(
            f"**Posted date:** "
            f"{posted_at or '-'}"
        )

    try:
        attachments = json.loads(
            attachment_names or "[]"
        )
    except:
        attachments = []

    if attachments:

        st.write(
            "**Attachments:** "
            + ", ".join(attachments)
        )
    else:

        st.caption(
            "No supporting documents attached."
        )


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
    "dashboard_jv_id": None
}

for key, value in defaults.items():

    if key not in st.session_state:
        st.session_state[key] = value


# =========================================================
# LOGIN / LOGOUT
# =========================================================

def login(employee_no, password):

    user = USERS.get(employee_no)

    if user is None:
        return False

    if user["password"] != password:
        return False

    st.session_state.logged_in = True
    st.session_state.employee_no = employee_no
    st.session_state.user_name = user["name"]
    st.session_state.role = user["role"]
    st.session_state.page = "Dashboard"

    return True


def logout():

    st.session_state.logged_in = False
    st.session_state.employee_no = None
    st.session_state.user_name = None
    st.session_state.role = None
    st.session_state.page = "Dashboard"
    st.session_state.dashboard_status = None
    st.session_state.dashboard_month = None
    st.session_state.dashboard_jv_id = None

    st.rerun()


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
            "New PIC Request"
        ]

    elif role == "APPROVER":

        menu_options = [
            "Dashboard",
            "Approval Inbox",
            "Search JVs",
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

    selected_page = st.radio(
        "Navigation",
        menu_options
    )

    if selected_page != st.session_state.page:

        st.session_state.page = selected_page
        st.session_state.dashboard_status = None
        st.session_state.dashboard_month = None
        st.session_state.dashboard_jv_id = None

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


    # -----------------------------------------------------
    # PREPARER DASHBOARD
    # -----------------------------------------------------

    if role == "PREPARER":

        status_groups = {
            "DRAFT": [
                "DRAFT"
            ],
            "PENDING": [
                "PENDING APPROVAL",
                "RESUBMITTED"
            ],
            "AMENDMENT": [
                "AMENDMENT REQUIRED"
            ],
            "APPROVED": [
                "APPROVED",
                "POSTED TO UBS"
            ]
        }

        counts = {}

        for label, statuses in status_groups.items():

            placeholders = ",".join(
                "?"
                for _ in statuses
            )

            query = f"""
                SELECT COUNT(*)
                FROM jv_headers
                WHERE prepared_by = ?
                AND status IN ({placeholders})
            """

            params = [
                employee_no
            ] + statuses

            counts[label] = conn.execute(
                query,
                params
            ).fetchone()[0]

        c1, c2, c3, c4 = st.columns(4)

        with c1:
            if st.button(
                f"Draft\n\n{counts['DRAFT']}",
                use_container_width=True
            ):
                st.session_state.dashboard_status = "DRAFT"
                st.session_state.dashboard_month = None
                st.session_state.dashboard_jv_id = None
                st.rerun()

        with c2:
            if st.button(
                f"Pending Approval\n\n{counts['PENDING']}",
                use_container_width=True
            ):
                st.session_state.dashboard_status = "PENDING"
                st.session_state.dashboard_month = None
                st.session_state.dashboard_jv_id = None
                st.rerun()

        with c3:
            if st.button(
                f"Amendment Required\n\n{counts['AMENDMENT']}",
                use_container_width=True
            ):
                st.session_state.dashboard_status = "AMENDMENT"
                st.session_state.dashboard_month = None
                st.session_state.dashboard_jv_id = None
                st.rerun()

        with c4:
            if st.button(
                f"Approved\n\n{counts['APPROVED']}",
                use_container_width=True
            ):
                st.session_state.dashboard_status = "APPROVED"
                st.session_state.dashboard_month = None
                st.session_state.dashboard_jv_id = None
                st.rerun()


    # -----------------------------------------------------
    # APPROVER DASHBOARD
    # -----------------------------------------------------

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
            SELECT COUNT(*)
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
                st.session_state.dashboard_month = None
                st.session_state.dashboard_jv_id = None
                st.rerun()

        with c2:

            if st.button(
                f"Approved\n\n{approved_count}",
                use_container_width=True
            ):

                st.session_state.dashboard_status = "APPROVED"
                st.session_state.dashboard_month = None
                st.session_state.dashboard_jv_id = None
                st.rerun()

        with c3:

            if st.button(
                f"Returned\n\n{returned_count}",
                use_container_width=True
            ):

                st.session_state.dashboard_status = "RETURNED"
                st.session_state.dashboard_month = None
                st.session_state.dashboard_jv_id = None
                st.rerun()


    # -----------------------------------------------------
    # AUDITOR DASHBOARD
    # -----------------------------------------------------

    elif role == "AUDITOR":

        total_count = conn.execute("""
            SELECT COUNT(*)
            FROM jv_headers
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
                st.session_state.dashboard_month = None
                st.session_state.dashboard_jv_id = None
                st.rerun()

        with c2:

            if st.button(
                f"Approved\n\n{approved_count}",
                use_container_width=True
            ):

                st.session_state.dashboard_status = "APPROVED"
                st.session_state.dashboard_month = None
                st.session_state.dashboard_jv_id = None
                st.rerun()

        with c3:

            if st.button(
                f"Posted to UBS\n\n{posted_count}",
                use_container_width=True
            ):

                st.session_state.dashboard_status = "POSTED"
                st.session_state.dashboard_month = None
                st.session_state.dashboard_jv_id = None
                st.rerun()

        with c4:

            st.metric(
                "Audit Records",
                audit_count
            )


    # -----------------------------------------------------
    # ADMIN DASHBOARD
    # -----------------------------------------------------

    elif role == "ADMIN":

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "Active Users",
            4
        )

        c2.metric(
            "Active G/L Codes",
            len(GL_MASTER)
        )

        c3.metric(
            "Open Periods",
            0
        )

        c4.metric(
            "JV Types",
            7
        )

    conn.close()


    # =====================================================
    # DASHBOARD DRILL-DOWN
    # =====================================================

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


        # -------------------------------------------------
        # LEVEL 3 - JV DETAIL
        # -------------------------------------------------

        if st.session_state.dashboard_jv_id:

            show_jv_detail(
                st.session_state.dashboard_jv_id
            )


        # -------------------------------------------------
        # LEVEL 2 - JV LIST FOR MONTH
        # -------------------------------------------------

        elif st.session_state.dashboard_month:

            selected_month = (
                st.session_state.dashboard_month
            )

            st.subheader(
                month_label(selected_month)
            )

            if st.button(
                "← Back to Months"
            ):

                st.session_state.dashboard_month = None
                st.session_state.dashboard_jv_id = None
                st.rerun()

            conn = get_connection()

            query = """
                SELECT
                    id,
                    jv_number,
                    jv_type,
                    total_debit,
                    status,
                    prepared_name,
                    approved_name
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

                if selected_status == "APPROVED":

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
                        preparer,
                        approver
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
                            key=f"open_{jv_id}"
                        ):

                            st.session_state.dashboard_jv_id = jv_id
                            st.rerun()

                    st.caption(
                        f"{status} | "
                        f"Preparer: {preparer}"
                    )

                    st.divider()


        # -------------------------------------------------
        # LEVEL 1 - MONTH SUMMARY
        # -------------------------------------------------

        else:

            st.subheader(
                "Select Accounting Month"
            )

            conn = get_connection()

            query = """
                SELECT
                    accounting_period,
                    COUNT(*) AS total
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

                if selected_status == "APPROVED":

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


            if not month_rows:

                st.info(
                    "No JV records found."
                )


            else:

                for accounting_period, total in month_rows:

                    c1, c2 = st.columns(
                        [4, 1]
                    )

                    c1.write(
                        f"### {month_label(accounting_period)}"
                    )

                    with c2:

                        if st.button(
                            f"{total} JV",
                            key=f"month_{accounting_period}"
                        ):

                            st.session_state.dashboard_month = (
                                accounting_period
                            )

                            st.session_state.dashboard_jv_id = None
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

    with col2:

        st.markdown(
            "### JV No."
        )

        st.markdown(
            f"## {jv_number}"
        )

    c1, c2 = st.columns(2)

    with c1:

        jv_type = st.selectbox(
            "JV Type",
            [
                "Depreciation",
                "Payroll",
                "AmIncome Placement",
                "Bank",
                "Accrual",
                "Provision",
                "Other"
            ]
        )

    remarks = st.text_input(
        "JV Description / Remarks"
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
                options=GL_OPTIONS
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

    uploaded_files = st.file_uploader(
        "Supporting Documents (Optional)",
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
# MY JVs
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

        selected_month = st.selectbox(
            "Accounting Month",
            [
                period
                for period, _
                in month_rows
            ],
            format_func=month_label
        )

        conn = get_connection()

        my_jvs = pd.read_sql_query("""
            SELECT
                id,
                jv_number AS "JV No.",
                jv_type AS "JV Type",
                total_debit AS "Amount",
                status AS "Status",
                reviewer_comments AS "Reviewer Comments"
            FROM jv_headers
            WHERE prepared_by = ?
            AND accounting_period = ?
            ORDER BY id DESC
        """, conn, params=(
            employee_no,
            selected_month
        ))

        conn.close()

        st.dataframe(
            my_jvs.drop(
                columns=["id"]
            ),
            use_container_width=True,
            hide_index=True
        )

        if not my_jvs.empty:

            selected_jv = st.selectbox(
                "Open JV",
                my_jvs["JV No."].tolist()
            )

            selected_id = int(
                my_jvs[
                    my_jvs["JV No."]
                    == selected_jv
                ]["id"].iloc[0]
            )

            show_jv_detail(
                selected_id
            )


# =========================================================
# APPROVAL INBOX
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

        selected_month = st.selectbox(
            "Accounting Month",
            [
                period
                for period, _
                in month_rows
            ],
            format_func=lambda x:
                f"{month_label(x)}"
        )

        conn = get_connection()

        pending_df = pd.read_sql_query("""
            SELECT
                id,
                jv_number AS "JV No.",
                jv_type AS "JV Type",
                remarks AS "Description",
                total_debit AS "Amount",
                prepared_name AS "Preparer",
                submitted_at AS "Submitted",
                status AS "Status"
            FROM jv_headers
            WHERE status IN (
                'PENDING APPROVAL',
                'RESUBMITTED'
            )
            AND accounting_period = ?
            ORDER BY id DESC
        """, conn, params=(
            selected_month,
        ))

        conn.close()

        st.dataframe(
            pending_df.drop(
                columns=["id"]
            ),
            use_container_width=True,
            hide_index=True
        )

        selected_jv_number = st.selectbox(
            "Open JV",
            pending_df["JV No."].tolist()
        )

        selected_row = pending_df[
            pending_df["JV No."]
            == selected_jv_number
        ].iloc[0]

        selected_jv_id = int(
            selected_row["id"]
        )

        st.divider()

        show_jv_detail(
            selected_jv_id
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

                if not comments.strip():

                    st.error(
                        "Reviewer comments are required."
                    )

                else:

                    conn = get_connection()

                    preparer = conn.execute("""
                        SELECT prepared_by
                        FROM jv_headers
                        WHERE id = ?
                    """, (
                        selected_jv_id,
                    )).fetchone()

                    if preparer and preparer[0] == employee_no:

                        conn.close()

                        st.error(
                            "Segregation of duties violation."
                        )

                        st.stop()

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

                    st.success(
                        f"{selected_jv_number} returned."
                    )

                    st.rerun()

        with c2:

            if st.button(
                "Approve",
                type="primary",
                use_container_width=True
            ):

                conn = get_connection()

                preparer = conn.execute("""
                    SELECT prepared_by
                    FROM jv_headers
                    WHERE id = ?
                """, (
                    selected_jv_id,
                )).fetchone()

                if preparer and preparer[0] == employee_no:

                    conn.close()

                    st.error(
                        "Segregation of duties violation."
                    )

                    st.stop()

                now = datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )

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

                st.success(
                    f"{selected_jv_number} approved."
                )

                st.rerun()


# =========================================================
# SEARCH JVs
# =========================================================

elif st.session_state.page == "Search JVs":

    if role not in [
        "APPROVER",
        "AUDITOR"
    ]:

        st.error(
            "Access denied."
        )

        st.stop()

    st.header(
        "Search JVs"
    )

    conn = get_connection()

    month_rows = conn.execute("""
        SELECT DISTINCT
            accounting_period
        FROM jv_headers
        ORDER BY accounting_period DESC
    """).fetchall()

    conn.close()

    months = [
        row[0]
        for row in month_rows
    ]

    if not months:

        st.info(
            "No JV records."
        )

    else:

        selected_month = st.selectbox(
            "Accounting Month",
            months,
            format_func=month_label
        )

        c1, c2 = st.columns(2)

        with c1:

            search_jv = st.text_input(
                "JV Number"
            )

        with c2:

            search_status = st.selectbox(
                "Status",
                [
                    "All",
                    "PENDING APPROVAL",
                    "AMENDMENT REQUIRED",
                    "RESUBMITTED",
                    "APPROVED",
                    "POSTED TO UBS",
                    "CANCELLED"
                ]
            )

        conn = get_connection()

        query = """
            SELECT
                id,
                jv_number AS "JV No.",
                jv_type AS "JV Type",
                total_debit AS "Amount",
                prepared_name AS "Preparer",
                approved_name AS "Approver",
                approved_at AS "Approval Date",
                status AS "Status"
            FROM jv_headers
            WHERE accounting_period = ?
        """

        params = [
            selected_month
        ]

        if search_jv:

            query += """
                AND jv_number LIKE ?
            """

            params.append(
                f"%{search_jv}%"
            )

        if search_status != "All":

            query += """
                AND status = ?
            """

            params.append(
                search_status
            )

        query += """
            ORDER BY id DESC
        """

        result = pd.read_sql_query(
            query,
            conn,
            params=params
        )

        conn.close()

        st.dataframe(
            result.drop(
                columns=["id"]
            ),
            use_container_width=True,
            hide_index=True
        )

        if not result.empty:

            selected_jv = st.selectbox(
                "Open JV",
                result["JV No."].tolist()
            )

            selected_id = int(
                result[
                    result["JV No."]
                    == selected_jv
                ]["id"].iloc[0]
            )

            show_jv_detail(
                selected_id
            )


# =========================================================
# AUDIT TRAIL
# =========================================================

elif st.session_state.page == "Audit Trail":

    if role != "AUDITOR":

        st.error(
            "Access denied."
        )

        st.stop()

    st.header(
        "Audit Trail"
    )

    st.caption(
        "Read-only"
    )

    conn = get_connection()

    audit_df = pd.read_sql_query("""
        SELECT
            jv_number AS "JV No.",
            event_type AS "Action",
            employee_no AS "Employee No.",
            employee_name AS "Employee",
            role AS "Role",
            comments AS "Comments",
            event_timestamp AS "Date / Time"
        FROM audit_log
        ORDER BY id DESC
    """, conn)

    conn.close()

    st.dataframe(
        audit_df,
        use_container_width=True,
        hide_index=True
    )


# =========================================================
# NEW PIC REQUEST
# =========================================================

elif st.session_state.page == "New PIC Request":

    if role not in [
        "PREPARER",
        "APPROVER"
    ]:

        st.error(
            "Access denied."
        )

        st.stop()

    st.header(
        "New PIC / User Change Request"
    )

    c1, c2 = st.columns(2)

    with c1:

        new_employee_no = st.text_input(
            "New Employee Number"
        )

        new_employee_name = st.text_input(
            "New Employee Name"
        )

    with c2:

        requested_role = st.selectbox(
            "Requested Role",
            [
                "PREPARER",
                "APPROVER"
            ]
        )

        effective_date = st.date_input(
            "Effective Date"
        )

    reason = st.selectbox(
        "Reason",
        [
            "Replacement of Existing PIC",
            "Staff Transfer",
            "New Finance PIC",
            "Other"
        ]
    )

    comments = st.text_area(
        "Comments"
    )

    if st.button(
        "Submit PIC Request"
    ):

        st.success(
            "PIC request submitted for Admin review."
        )


# =========================================================
# ADMIN
# =========================================================

elif st.session_state.page == "User Management":

    if role != "ADMIN":

        st.error(
            "Access denied."
        )

        st.stop()

    st.header(
        "User Management"
    )

    user_df = pd.DataFrame([
        {
            "Employee No": "1001",
            "Name": "Demo Preparer",
            "Role": "PREPARER",
            "Status": "ACTIVE"
        },
        {
            "Employee No": "2001",
            "Name": "Demo Assistant Manager",
            "Role": "APPROVER",
            "Status": "ACTIVE"
        },
        {
            "Employee No": "9001",
            "Name": "Demo Auditor",
            "Role": "AUDITOR",
            "Status": "ACTIVE"
        },
        {
            "Employee No": "8001",
            "Name": "Demo Admin",
            "Role": "ADMIN",
            "Status": "ACTIVE"
        }
    ])

    st.dataframe(
        user_df,
        use_container_width=True,
        hide_index=True
    )


elif st.session_state.page == "G/L Master":

    if role != "ADMIN":

        st.error(
            "Access denied."
        )

        st.stop()

    st.header(
        "G/L Master"
    )

    gl_rows = []

    for code, details in GL_MASTER.items():

        gl_rows.append({
            "A/C Code": code,
            "Description": details["description"],
            "Category": details["category"],
            "Status": "ACTIVE"
        })

    st.dataframe(
        pd.DataFrame(gl_rows),
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

    type_df = pd.DataFrame([
        {
            "JV Type": "Depreciation",
            "Attachment": "Optional"
        },
        {
            "JV Type": "Payroll",
            "Attachment": "Optional"
        },
        {
            "JV Type": "AmIncome Placement",
            "Attachment": "Optional"
        },
        {
            "JV Type": "Bank",
            "Attachment": "Optional"
        },
        {
            "JV Type": "Accrual",
            "Attachment": "Optional"
        },
        {
            "JV Type": "Provision",
            "Attachment": "Optional"
        },
        {
            "JV Type": "Other",
            "Attachment": "Optional"
        }
    ])

    st.dataframe(
        type_df,
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

    year = st.selectbox(
        "Year",
        [
            2025,
            2026,
            2027
        ],
        index=1
    )

    month = st.selectbox(
        "Month",
        [
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
    )

    period_status = st.radio(
        "Status",
        [
            "OPEN",
            "CLOSED"
        ],
        horizontal=True
    )

    if st.button(
        "Update Period"
    ):

        st.success(
            f"{month} {year} set to {period_status}."
        )
