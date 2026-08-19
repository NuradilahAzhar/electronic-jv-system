import streamlit as st
import pandas as pd
from datetime import datetime


# ==================================================
# PAGE CONFIGURATION
# ==================================================

st.set_page_config(
    page_title="Electronic JV",
    page_icon="📘",
    layout="wide"
)


# ==================================================
# DEMO USER MASTER
# Prototype only
# DO NOT use real employee passwords here
# ==================================================

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


# ==================================================
# DEMO G/L MASTER
# Prototype only
# ==================================================

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


# ==================================================
# SESSION INITIALISATION
# ==================================================

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "employee_no" not in st.session_state:
    st.session_state.employee_no = None

if "user_name" not in st.session_state:
    st.session_state.user_name = None

if "role" not in st.session_state:
    st.session_state.role = None

if "page" not in st.session_state:
    st.session_state.page = "Dashboard"

if "demo_jv_sequence" not in st.session_state:
    st.session_state.demo_jv_sequence = 1


# ==================================================
# LOGIN
# ==================================================

def login(employee_no, password):

    if not employee_no or not password:
        return False

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


# ==================================================
# LOGOUT
# ==================================================

def logout():

    st.session_state.logged_in = False
    st.session_state.employee_no = None
    st.session_state.user_name = None
    st.session_state.role = None
    st.session_state.page = "Dashboard"

    st.rerun()


# ==================================================
# LOGIN SCREEN
# ==================================================

if not st.session_state.logged_in:

    st.title("Electronic Journal Voucher System")

    st.caption("JKPSD Pilot")

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

        if login(employee_no, password):

            st.success(
                "Login successful."
            )

            st.rerun()

        else:

            st.error(
                "Invalid Employee Number or Password."
            )

    st.stop()


# ==================================================
# CURRENT USER
# ==================================================

employee_no = st.session_state.employee_no
user_name = st.session_state.user_name
role = st.session_state.role


# ==================================================
# SIDEBAR
# ==================================================

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


    # PREPARER MENU

    if role == "PREPARER":

        menu_options = [
            "Dashboard",
            "Create New JV",
            "My JVs",
            "New PIC Request"
        ]


    # APPROVER MENU

    elif role == "APPROVER":

        menu_options = [
            "Dashboard",
            "Approval Inbox",
            "Search JVs",
            "New PIC Request"
        ]


    # AUDITOR MENU

    elif role == "AUDITOR":

        menu_options = [
            "Dashboard",
            "Search JVs",
            "Audit Trail"
        ]


    # ADMIN MENU

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

    st.session_state.page = selected_page

    st.divider()

    if st.button("Logout"):

        logout()


# ==================================================
# MAIN HEADER
# ==================================================

st.title(
    "Electronic Journal Voucher System"
)

st.caption(
    "JKPSD Pilot"
)

st.divider()


# ==================================================
# DASHBOARD
# ==================================================

if st.session_state.page == "Dashboard":

    st.header("Dashboard")


    # PREPARER DASHBOARD

    if role == "PREPARER":

        col1, col2, col3, col4 = st.columns(4)

        col1.metric(
            "Draft",
            0
        )

        col2.metric(
            "Pending Approval",
            0
        )

        col3.metric(
            "Amendment Required",
            0
        )

        col4.metric(
            "Approved",
            0
        )

        st.info(
            "Prepare and submit JVs. Approval access is restricted."
        )


    # APPROVER DASHBOARD

    elif role == "APPROVER":

        col1, col2, col3, col4 = st.columns(4)

        col1.metric(
            "Pending Approval",
            0
        )

        col2.metric(
            "Resubmitted",
            0
        )

        col3.metric(
            "Approved Today",
            0
        )

        col4.metric(
            "Returned Today",
            0
        )

        st.info(
            "Review, approve or return submitted JVs."
        )


    # AUDITOR DASHBOARD

    elif role == "AUDITOR":

        col1, col2, col3, col4 = st.columns(4)

        col1.metric(
            "Approved JVs",
            0
        )

        col2.metric(
            "Posted to UBS",
            0
        )

        col3.metric(
            "Cancelled",
            0
        )

        col4.metric(
            "Audit Records",
            0
        )

        st.info(
            "Read-only Guest / Auditor access."
        )


    # ADMIN DASHBOARD

    elif role == "ADMIN":

        col1, col2, col3, col4 = st.columns(4)

        col1.metric(
            "Active Users",
            4
        )

        col2.metric(
            "Active G/L Codes",
            len(GL_MASTER)
        )

        col3.metric(
            "Open Periods",
            0
        )

        col4.metric(
            "JV Types",
            7
        )

        st.info(
            "Master data and access administration."
        )


# ==================================================
# CREATE NEW JV
# ==================================================

elif st.session_state.page == "Create New JV":

    # ----------------------------------------------
    # ACCESS CONTROL
    # ----------------------------------------------

    if role != "PREPARER":

        st.error(
            "Access denied."
        )

        st.stop()


    # ----------------------------------------------
    # AUTOMATIC JV NUMBER
    # ----------------------------------------------

    current_period = datetime.now().strftime("%y%m")

    jv_number = (
        f"JV{current_period}"
        f"{st.session_state.demo_jv_sequence:02d}"
    )


    # ----------------------------------------------
    # JV HEADER
    # ----------------------------------------------

    col_title, col_number = st.columns(
        [3, 1]
    )


    with col_title:

        st.markdown(
            "### JK PSD SDN BHD"
        )

        st.markdown(
            "## JOURNAL VOUCHER"
        )


    with col_number:

        st.markdown(
            "### JV No."
        )

        st.markdown(
            f"## {jv_number}"
        )


    st.divider()


    # ----------------------------------------------
    # BASIC JV DETAILS
    # ----------------------------------------------

    col1, col2 = st.columns(2)


    with col1:

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


    with col2:

        accounting_period = st.date_input(
            "Accounting Month",
            value=datetime.now().date()
        )


    remarks = st.text_input(
        "JV Description / Remarks"
    )


    st.divider()


    # ----------------------------------------------
    # JOURNAL ENTRY TABLE
    # ----------------------------------------------

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
                format="DD/MM/YYYY",
                required=False
            ),

            "A/C Code": st.column_config.SelectboxColumn(
                "A/C Code",
                options=GL_OPTIONS,
                required=False
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


    # ----------------------------------------------
    # CONVERT AMOUNTS
    # ----------------------------------------------

    debit_series = pd.to_numeric(
        journal_df["Dr"],
        errors="coerce"
    ).fillna(0)


    credit_series = pd.to_numeric(
        journal_df["Cr"],
        errors="coerce"
    ).fillna(0)


    total_debit = debit_series.sum()

    total_credit = credit_series.sum()

    difference = total_debit - total_credit


    # ----------------------------------------------
    # TOTALS
    # ----------------------------------------------

    st.divider()

    col1, col2, col3 = st.columns(3)


    col1.metric(
        "Total Dr",
        f"RM {total_debit:,.2f}"
    )


    col2.metric(
        "Total Cr",
        f"RM {total_credit:,.2f}"
    )


    col3.metric(
        "Difference",
        f"RM {difference:,.2f}"
    )


    # ----------------------------------------------
    # SUPPORTING DOCUMENTS
    # OPTIONAL
    # ----------------------------------------------

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


    # ----------------------------------------------
    # VALIDATION
    # ----------------------------------------------

    errors = []


    # Identify rows that user actually used

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

            active_rows.append(
                index
            )


    # At least two accounting lines

    if len(active_rows) < 2:

        errors.append(
            "Minimum two journal lines are required."
        )


    # Validate individual rows

    for index in active_rows:

        row = journal_df.iloc[index]

        debit = float(
            debit_series.iloc[index]
        )

        credit = float(
            credit_series.iloc[index]
        )


        line_no = index + 1


        if pd.isna(
            row["Date"]
        ):

            errors.append(
                f"Line {line_no}: Date is required."
            )


        if pd.isna(
            row["A/C Code"]
        ):

            errors.append(
                f"Line {line_no}: A/C Code is required."
            )


        if (
            str(
                row["Description"]
            ).strip() == ""
        ):

            errors.append(
                f"Line {line_no}: Description is required."
            )


        if (
            debit > 0
            and credit > 0
        ):

            errors.append(
                f"Line {line_no}: "
                "Enter either Dr or Cr, not both."
            )


        if (
            debit == 0
            and credit == 0
        ):

            errors.append(
                f"Line {line_no}: "
                "Dr or Cr amount is required."
            )


    # Overall JV validations

    if total_debit == 0:

        errors.append(
            "JV total cannot be zero."
        )


    if round(
        total_debit,
        2
    ) != round(
        total_credit,
        2
    ):

        errors.append(

            f"Total Dr RM{total_debit:,.2f} "
            f"does not match "
            f"Total Cr RM{total_credit:,.2f}."
        )


    # ----------------------------------------------
    # VALIDATION RESULT
    # ----------------------------------------------

    st.divider()


    if errors:

        st.error(
            "JV not ready for submission."
        )


        with st.expander(
            "View validation issues"
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


    # ----------------------------------------------
    # BUTTONS
    # ----------------------------------------------

    col1, col2 = st.columns(
        [1, 1]
    )


    with col1:

        if st.button(
            "Save Draft",
            use_container_width=True
        ):

            st.success(
                f"{jv_number} saved as Draft."
            )

            st.warning(
                "Prototype only - database storage "
                "will be added next."
            )


    with col2:

        if st.button(
            "Submit for Approval",
            type="primary",
            disabled=submit_disabled,
            use_container_width=True
        ):

            st.success(
                f"{jv_number} submitted for approval."
            )

            st.session_state.demo_jv_sequence += 1

            st.warning(
                "Prototype only - database workflow "
                "will be added next."
            )


# ==================================================
# MY JVs
# ==================================================

elif st.session_state.page == "My JVs":

    if role != "PREPARER":

        st.error(
            "Access denied."
        )

        st.stop()


    st.header(
        "My Journal Vouchers"
    )


    st.info(
        "Draft, Pending Approval, Amendment Required "
        "and Approved JVs will appear here."
    )


# ==================================================
# APPROVAL INBOX
# ==================================================

elif st.session_state.page == "Approval Inbox":

    if role != "APPROVER":

        st.error(
            "Access denied."
        )

        st.stop()


    st.header(
        "Approval Inbox"
    )


    st.info(
        "JVs awaiting review will appear here."
    )


# ==================================================
# SEARCH JVs
# ==================================================

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
        "Search Journal Vouchers"
    )


    col1, col2, col3 = st.columns(3)


    with col1:

        st.text_input(
            "JV Number"
        )


    with col2:

        st.selectbox(
            "Status",
            [
                "All",
                "Draft",
                "Pending Approval",
                "Amendment Required",
                "Resubmitted",
                "Approved",
                "Posted to UBS",
                "Cancelled"
            ]
        )


    with col3:

        st.selectbox(
            "JV Type",
            [
                "All",
                "Depreciation",
                "Payroll",
                "AmIncome Placement",
                "Bank",
                "Accrual",
                "Provision",
                "Other"
            ]
        )


    st.info(
        "JV database search will be connected later."
    )


# ==================================================
# AUDIT TRAIL
# ==================================================

elif st.session_state.page == "Audit Trail":

    if role != "AUDITOR":

        st.error(
            "Access denied."
        )

        st.stop()


    st.header(
        "Audit Trail"
    )


    st.warning(
        "Read-only access."
    )


    st.info(
        "JV activity history will appear here."
    )


# ==================================================
# NEW PIC REQUEST
# ==================================================

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


    col1, col2 = st.columns(2)


    with col1:

        new_employee_no = st.text_input(
            "New Employee Number"
        )


        new_employee_name = st.text_input(
            "New Employee Name"
        )


    with col2:

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
        "Submit PIC Request",
        type="primary"
    ):

        if not new_employee_no:

            st.error(
                "Employee Number is required."
            )


        elif not new_employee_name:

            st.error(
                "Employee Name is required."
            )


        else:

            st.success(
                "PIC request submitted for Admin review."
            )


# ==================================================
# USER MANAGEMENT
# ==================================================

elif st.session_state.page == "User Management":

    if role != "ADMIN":

        st.error(
            "Access denied."
        )

        st.stop()


    st.header(
        "User Management"
    )


    user_data = pd.DataFrame(
        [
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
        ]
    )


    st.dataframe(
        user_data,
        use_container_width=True,
        hide_index=True
    )


    st.caption(
        "User activation/deactivation will be "
        "connected to the database later."
    )


# ==================================================
# G/L MASTER
# ==================================================

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

        gl_rows.append(
            {
                "A/C Code": code,
                "Description": details["description"],
                "Category": details["category"],
                "Status": "ACTIVE"
            }
        )


    gl_dataframe = pd.DataFrame(
        gl_rows
    )


    st.dataframe(
        gl_dataframe,
        use_container_width=True,
        hide_index=True
    )


# ==================================================
# JV TYPE MASTER
# ==================================================

elif st.session_state.page == "JV Type Master":

    if role != "ADMIN":

        st.error(
            "Access denied."
        )

        st.stop()


    st.header(
        "JV Type Master"
    )


    jv_type_data = pd.DataFrame(
        [
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
        ]
    )


    st.dataframe(
        jv_type_data,
        use_container_width=True,
        hide_index=True
    )


# ==================================================
# PERIOD CONTROL
# ==================================================

elif st.session_state.page == "Period Control":

    if role != "ADMIN":

        st.error(
            "Access denied."
        )

        st.stop()


    st.header(
        "Accounting Period Control"
    )


    st.selectbox(
        "Accounting Year",
        [
            2025,
            2026,
            2027
        ],
        index=1
    )


    st.selectbox(
        "Accounting Month",
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


    st.radio(
        "Period Status",
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
            "Prototype period status updated."
        )
