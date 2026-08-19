import streamlit as st

st.set_page_config(
    page_title="Electronic JV",
    page_icon="📘",
    layout="wide"
)

# --------------------------------------------------
# DEMO USER MASTER
# Prototype only - do not use real credentials here
# --------------------------------------------------

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

# --------------------------------------------------
# SESSION INITIALISATION
# --------------------------------------------------

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


# --------------------------------------------------
# LOGIN FUNCTION
# --------------------------------------------------

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


# --------------------------------------------------
# LOGOUT FUNCTION
# --------------------------------------------------

def logout():

    st.session_state.logged_in = False
    st.session_state.employee_no = None
    st.session_state.user_name = None
    st.session_state.role = None
    st.session_state.page = "Dashboard"

    st.rerun()


# --------------------------------------------------
# LOGIN PAGE
# --------------------------------------------------

if not st.session_state.logged_in:

    st.title("Electronic Journal Voucher System")

    st.subheader("JKPSD Pilot")

    st.write(
        "Controlled electronic workflow for preparation, "
        "review, approval and audit retrieval of Journal Vouchers."
    )

    st.divider()

    employee_no = st.text_input(
        "Employee Number"
    )

    password = st.text_input(
        "Password",
        type="password"
    )

    if st.button("Login"):

        if login(employee_no, password):
            st.success("Login successful.")
            st.rerun()

        else:
            st.error(
                "Invalid Employee Number or Password."
            )

    st.stop()


# --------------------------------------------------
# USER DETAILS
# --------------------------------------------------

employee_no = st.session_state.employee_no
user_name = st.session_state.user_name
role = st.session_state.role


# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------

with st.sidebar:

    st.title("E-JV")

    st.write(f"**{user_name}**")
    st.caption(f"Employee No: {employee_no}")
    st.caption(f"Role: {role}")

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
        menu_options = ["Dashboard"]

    selected_page = st.radio(
        "Navigation",
        menu_options
    )

    st.session_state.page = selected_page

    st.divider()

    if st.button("Logout"):
        logout()


# --------------------------------------------------
# MAIN HEADER
# --------------------------------------------------

st.title("Electronic Journal Voucher System")

st.caption("JKPSD Pilot")

st.write(
    f"Logged in as **{user_name}** "
    f"({employee_no}) — **{role}**"
)

st.divider()


# --------------------------------------------------
# DASHBOARD
# --------------------------------------------------

if st.session_state.page == "Dashboard":

    st.header("Dashboard")

    col1, col2, col3, col4 = st.columns(4)

    if role == "PREPARER":

        col1.metric("Draft", 0)
        col2.metric("Pending Approval", 0)
        col3.metric("Amendment Required", 0)
        col4.metric("Approved", 0)

        st.info(
            "You can create, edit and submit Journal Vouchers. "
            "You cannot approve Journal Vouchers."
        )

    elif role == "APPROVER":

        col1.metric("Pending Approval", 0)
        col2.metric("Resubmitted", 0)
        col3.metric("Approved Today", 0)
        col4.metric("Returned Today", 0)

        st.info(
            "You can review, approve or return Journal Vouchers. "
            "You cannot prepare Journal Vouchers."
        )

    elif role == "AUDITOR":

        col1.metric("Approved JVs", 0)
        col2.metric("Posted to UBS", 0)
        col3.metric("Cancelled", 0)
        col4.metric("Audit Records", 0)

        st.info(
            "Auditor / Guest access is read-only."
        )

    elif role == "ADMIN":

        col1.metric("Active Users", 4)
        col2.metric("Active G/L Codes", 0)
        col3.metric("Open Periods", 0)
        col4.metric("JV Types", 0)

        st.info(
            "Admin maintains master data and user access. "
            "Admin cannot prepare or approve Journal Vouchers."
        )


# --------------------------------------------------
# PREPARER PAGES
# --------------------------------------------------

elif st.session_state.page == "Create New JV":

    if role != "PREPARER":
        st.error("Access denied.")
        st.stop()

    st.header("Create New Journal Voucher")

    # ----------------------------------------------
    # DEMO JV NUMBER
    # Prototype only
    # ----------------------------------------------

    from datetime import datetime

    current_period = datetime.now().strftime("%y%m")

    if "demo_jv_sequence" not in st.session_state:
        st.session_state.demo_jv_sequence = 1

    jv_number = (
        f"JV{current_period}"
        f"{st.session_state.demo_jv_sequence:02d}"
    )

    st.info(
        f"System Generated JV Number: **{jv_number}**"
    )

    st.caption(
        "Prototype numbering only. "
        "A database-controlled sequence will be added later."
    )

    st.divider()

    # ----------------------------------------------
    # JV HEADER
    # ----------------------------------------------

    st.subheader("JV Header")

    col1, col2 = st.columns(2)

    with col1:
        jv_date = st.date_input(
            "JV Date"
        )

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
        accounting_month = st.selectbox(
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

        accounting_year = st.number_input(
            "Accounting Year",
            min_value=2024,
            max_value=2035,
            value=datetime.now().year,
            step=1
        )

    description = st.text_area(
        "JV Description"
    )

    st.divider()

    # ----------------------------------------------
    # CONTROLLED G/L MASTER
    # Demo only
    # ----------------------------------------------

    st.subheader("Journal Lines")

    GL_MASTER = {
        "110001": {
            "description": "Cash at Bank",
            "category": "Asset"
        },
        "120001": {
            "description": "Accounts Receivable",
            "category": "Asset"
        },
        "210001": {
            "description": "Accounts Payable",
            "category": "Liability"
        },
        "220001": {
            "description": "Accrued Expenses",
            "category": "Liability"
        },
        "410001": {
            "description": "Payroll Expense",
            "category": "Expense"
        },
        "420001": {
            "description": "Depreciation Expense",
            "category": "Expense"
        },
        "430001": {
            "description": "Bank Charges",
            "category": "Expense"
        }
    }

    gl_options = [
        f"{code} - {details['description']}"
        for code, details in GL_MASTER.items()
    ]

    # ----------------------------------------------
    # LINE 1
    # ----------------------------------------------

    st.markdown("### Line 1")

    line1_gl = st.selectbox(
        "G/L Code - Line 1",
        gl_options,
        key="line1_gl"
    )

    line1_description = st.text_input(
        "Line Description - Line 1",
        key="line1_description"
    )

    col1, col2 = st.columns(2)

    with col1:
        line1_debit = st.number_input(
            "Debit - Line 1",
            min_value=0.00,
            value=0.00,
            step=100.00,
            format="%.2f",
            key="line1_debit"
        )

    with col2:
        line1_credit = st.number_input(
            "Credit - Line 1",
            min_value=0.00,
            value=0.00,
            step=100.00,
            format="%.2f",
            key="line1_credit"
        )

    st.divider()

    # ----------------------------------------------
    # LINE 2
    # ----------------------------------------------

    st.markdown("### Line 2")

    line2_gl = st.selectbox(
        "G/L Code - Line 2",
        gl_options,
        key="line2_gl"
    )

    line2_description = st.text_input(
        "Line Description - Line 2",
        key="line2_description"
    )

    col1, col2 = st.columns(2)

    with col1:
        line2_debit = st.number_input(
            "Debit - Line 2",
            min_value=0.00,
            value=0.00,
            step=100.00,
            format="%.2f",
            key="line2_debit"
        )

    with col2:
        line2_credit = st.number_input(
            "Credit - Line 2",
            min_value=0.00,
            value=0.00,
            step=100.00,
            format="%.2f",
            key="line2_credit"
        )

    # ----------------------------------------------
    # TOTALS
    # ----------------------------------------------

    total_debit = (
        line1_debit +
        line2_debit
    )

    total_credit = (
        line1_credit +
        line2_credit
    )

    st.divider()

    st.subheader("JV Validation")

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Total Debit",
        f"RM {total_debit:,.2f}"
    )

    col2.metric(
        "Total Credit",
        f"RM {total_credit:,.2f}"
    )

    difference = total_debit - total_credit

    col3.metric(
        "Difference",
        f"RM {difference:,.2f}"
    )

    # ----------------------------------------------
    # VALIDATION RULES
    # ----------------------------------------------

    errors = []

    if not description.strip():
        errors.append(
            "JV Description is required."
        )

    if not line1_description.strip():
        errors.append(
            "Line 1 description is required."
        )

    if not line2_description.strip():
        errors.append(
            "Line 2 description is required."
        )

    if line1_debit > 0 and line1_credit > 0:
        errors.append(
            "Line 1 cannot contain both debit and credit."
        )

    if line2_debit > 0 and line2_credit > 0:
        errors.append(
            "Line 2 cannot contain both debit and credit."
        )

    if line1_debit == 0 and line1_credit == 0:
        errors.append(
            "Line 1 requires a debit or credit amount."
        )

    if line2_debit == 0 and line2_credit == 0:
        errors.append(
            "Line 2 requires a debit or credit amount."
        )

    if total_debit == 0:
        errors.append(
            "JV total cannot be zero."
        )

    if total_debit != total_credit:
        errors.append(
            f"Submission is not allowed because the "
            f"total debit of RM{total_debit:,.2f} "
            f"does not match the total credit of "
            f"RM{total_credit:,.2f}."
        )

    # ----------------------------------------------
    # SUPPORTING DOCUMENT
    # ----------------------------------------------

    st.divider()

    st.subheader("Supporting Documents")

    uploaded_files = st.file_uploader(
        "Upload Supporting Documents",
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

    if not uploaded_files:
        errors.append(
            "At least one supporting document is required."
        )

    # ----------------------------------------------
    # DISPLAY VALIDATION
    # ----------------------------------------------

    st.divider()

    if errors:

        st.error(
            "JV validation is not complete."
        )

        for error in errors:
            st.write(f"- {error}")

        submit_disabled = True

    else:

        st.success(
            "JV validation completed successfully."
        )

        submit_disabled = False

    # ----------------------------------------------
    # SUBMIT
    # ----------------------------------------------

    if st.button(
        "Submit for Approval",
        disabled=submit_disabled
    ):

        st.success(
            f"{jv_number} submitted successfully "
            f"for approval."
        )

        st.session_state.demo_jv_sequence += 1

        st.warning(
            "Prototype only: this JV is not yet saved "
            "to a database."
        )


elif st.session_state.page == "My JVs":

    if role != "PREPARER":
        st.error("Access denied.")
        st.stop()

    st.header("My Journal Vouchers")

    st.info(
        "Your Draft, Pending Approval, Amendment Required "
        "and Approved JVs will appear here."
    )


# --------------------------------------------------
# APPROVER PAGES
# --------------------------------------------------

elif st.session_state.page == "Approval Inbox":

    if role != "APPROVER":
        st.error("Access denied.")
        st.stop()

    st.header("Approval Inbox")

    st.info(
        "Journal Vouchers awaiting your review will appear here."
    )


# --------------------------------------------------
# SHARED SEARCH PAGE
# --------------------------------------------------

elif st.session_state.page == "Search JVs":

    if role not in ["APPROVER", "AUDITOR"]:
        st.error("Access denied.")
        st.stop()

    st.header("Search Journal Vouchers")

    st.info(
        "JV search and audit retrieval will be built later."
    )


# --------------------------------------------------
# AUDITOR PAGE
# --------------------------------------------------

elif st.session_state.page == "Audit Trail":

    if role != "AUDITOR":
        st.error("Access denied.")
        st.stop()

    st.header("Audit Trail")

    st.warning(
        "Read-only access."
    )

    st.info(
        "Complete JV activity history will appear here."
    )


# --------------------------------------------------
# NEW PIC REQUEST
# --------------------------------------------------

elif st.session_state.page == "New PIC Request":

    if role not in ["PREPARER", "APPROVER"]:
        st.error("Access denied.")
        st.stop()

    st.header("New PIC / User Change Request")

    st.write(
        "Use this form to request a change of Finance PIC. "
        "Submission does not automatically create or activate an account."
    )

    new_employee_no = st.text_input(
        "New Employee Number"
    )

    new_employee_name = st.text_input(
        "New Employee Name"
    )

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

    if st.button("Submit PIC Request"):

        if not new_employee_no:
            st.error(
                "New Employee Number is required."
            )

        elif not new_employee_name:
            st.error(
                "New Employee Name is required."
            )

        else:
            st.success(
                "PIC request submitted for administrator review."
            )

            st.warning(
                "Prototype only: the request is not yet saved "
                "to a database."
            )


# --------------------------------------------------
# ADMIN PAGES
# --------------------------------------------------

elif st.session_state.page == "User Management":

    if role != "ADMIN":
        st.error("Access denied.")
        st.stop()

    st.header("User Management")

    st.info(
        "Admin will manage user activation, deactivation "
        "and role assignment here."
    )


elif st.session_state.page == "G/L Master":

    if role != "ADMIN":
        st.error("Access denied.")
        st.stop()

    st.header("G/L Master")

    st.info(
        "Controlled G/L Master maintenance will be built here."
    )


elif st.session_state.page == "JV Type Master":

    if role != "ADMIN":
        st.error("Access denied.")
        st.stop()

    st.header("JV Type Master")

    st.info(
        "JV Type and supporting-document requirements "
        "will be maintained here."
    )


elif st.session_state.page == "Period Control":

    if role != "ADMIN":
        st.error("Access denied.")
        st.stop()

    st.header("Accounting Period Control")

    st.info(
        "Open and closed accounting periods will be managed here."
    )
