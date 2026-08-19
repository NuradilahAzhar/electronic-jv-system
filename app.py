import streamlit as st

st.set_page_config(
    page_title="Electronic JV",
    page_icon="📘",
    layout="wide"
)

# --------------------------------------------------
# DEMO USER MASTER
# Prototype only - do not use real passwords here
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
    }
}

# --------------------------------------------------
# LOGIN PAGE
# --------------------------------------------------

st.title("Electronic Journal Voucher System")
st.subheader("JKPSD Pilot")

st.write(
    "Controlled electronic workflow for preparation, "
    "review, approval and audit retrieval of Journal Vouchers."
)

st.divider()

employee_no = st.text_input("Employee Number")

password = st.text_input(
    "Password",
    type="password"
)

if st.button("Login"):

    if not employee_no:
        st.error("Please enter your employee number.")

    elif not password:
        st.error("Please enter your password.")

    elif employee_no not in USERS:
        st.error("Invalid Employee Number or Password.")

    elif USERS[employee_no]["password"] != password:
        st.error("Invalid Employee Number or Password.")

    else:
        user = USERS[employee_no]

        st.success("Login successful.")

        st.divider()

        st.write(f"**Employee:** {user['name']}")
        st.write(f"**Employee Number:** {employee_no}")
        st.write(f"**Role:** {user['role']}")

        if user["role"] == "PREPARER":
            st.info(
                "Preparer access: Create, edit and submit "
                "Journal Vouchers."
            )

        elif user["role"] == "APPROVER":
            st.info(
                "Approver access: Review, approve or return "
                "Journal Vouchers for amendment."
            )

        elif user["role"] == "AUDITOR":
            st.info(
                "Auditor access: Read-only access to approved "
                "Journal Voucher records and audit trails."
            )
