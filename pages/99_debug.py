import streamlit as st
import hashlib

st.title("Debug hash")
password = st.text_input("Contraseña a hashear", type="password")
if password:
    h = hashlib.sha256(password.encode()).hexdigest()
    st.code(h)
    st.write(f"Longitud: {len(h)}")
