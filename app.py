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

    st.info(
        "This module will be built in the next stage."
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
