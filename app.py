import streamlit as st

st.set_page_config(
    page_title="Electronic JV",
    page_icon="📘",
    layout="wide"
)

st.title("Electronic Journal Voucher System")

st.subheader("JKPSD Pilot")

st.write("Welcome to the Electronic Journal Voucher Workflow System.")

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
    else:
        st.success("Login information received.")
