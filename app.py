import streamlit as st
import sqlite3
import pandas as pd
import os
import bcrypt
from datetime import datetime

# --------------------
# DATABASE - Configurare
# --------------------
# Folosim check_same_thread=False pentru a permite accesul multi-utilizator în Streamlit
conn = sqlite3.connect("database.db", check_same_thread=False)
cursor = conn.cursor()

# Creare tabele dacă nu există
cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT,
    role TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS documents(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client TEXT,
    doc_type TEXT,
    month TEXT,
    file_path TEXT,
    upload_date TEXT
)
""")
conn.commit()

# --------------------
# FOLDER DOCUMENTE
# --------------------
os.makedirs("documents", exist_ok=True)

# --------------------
# FUNCTII LOGICĂ
# --------------------
def create_user(username, password, role):
    try:
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        cursor.execute(
            "INSERT INTO users(username, password, role) VALUES (?,?,?)",
            (username, hashed, role)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

def login(username, password):
    cursor.execute("SELECT * FROM users WHERE username=?", (username,))
    user = cursor.fetchone()
    if user:
        # Verificăm parola hashed
        if bcrypt.checkpw(password.encode('utf-8'), user[2]):
            return user
    return None

# --------------------
# SESSION STATE (Starea Sesiunii)
# --------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.role = ""

# --------------------
# INTERFAȚĂ: LOGIN / REGISTER
# --------------------
if not st.session_state.logged_in:
    menu = st.sidebar.selectbox("Navigare", ["Login", "Register"])

    if menu == "Register":
        st.title("📝 Creare cont nou")
        new_user = st.text_input("Username dorit")
        new_pass = st.text_input("Parolă", type="password")
        new_role = st.selectbox("Alege Rolul", ["client", "contabil"])

        if st.button("Înregistrare"):
            if new_user and new_pass:
                if create_user(new_user, new_pass, new_role):
                    st.success("Cont creat cu succes! Mergi la Login.")
                else:
                    st.error("Acest username există deja.")
            else:
                st.warning("Te rugăm să completezi toate câmpurile.")

    if menu == "Login":
        st.title("🔐 Portal Documente - Login")
        user_input = st.text_input("Username")
        pass_input = st.text_input("Parolă", type="password")

        if st.button("Autentificare"):
            user_data = login(user_input, pass_input)
            if user_data:
                st.session_state.logged_in = True
                st.session_state.username = user_data[1]
                st.session_state.role = user_data[3]
                st.rerun()  # CORECTAT: funcția nouă înlocuiește experimental_rerun
            else:
                st.error("Username sau parolă incorectă.")

# --------------------
# INTERFAȚĂ: APLICAȚIA PRINCIPALĂ
# --------------------
else:
    # Sidebar pentru Logout
    st.sidebar.info(f"Utilizator: **{st.session_state.username}**")
    st.sidebar.write(f"Rol: {st.session_state.role.capitalize()}")
    
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.role = ""
        st.rerun()  # CORECTAT

    # --- LOGICĂ CLIENT ---
    if st.session_state.role == "client":
        st.title("📤 Încărcare Documente")
        
        doc_type = st.selectbox("Tip document", ["Factură", "Bon", "Extras bancar", "Altul"])
        month = st.selectbox(
            "Luna aferentă",
            ["Ianuarie", "Februarie", "Martie", "Aprilie", "Mai", "Iunie", 
             "Iulie", "August", "Septembrie", "Octombrie", "Noiembrie", "Decembrie"]
        )

        uploaded_file = st.file_uploader("Alege fișierul", type=["pdf", "png", "jpg", "jpeg"])

        if st.button("Trimite Document"):
            if uploaded_file is not None:
                # Creare structură foldere: documents/username/luna/
                folder = os.path.join("documents", st.session_state.username, month)
                os.makedirs(folder, exist_ok=True)

                file_path = os.path.join(folder, uploaded_file.name)

                # Salvare fișier pe disk
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                # Salvare info în baza de date
                cursor.execute(
                    """INSERT INTO documents
                    (client, doc_type, month, file_path, upload_date)
                    VALUES (?,?,?,?,?)""",
                    (st.session_state.username, doc_type, month, file_path, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                )
                conn.commit()
                st.success(f"Fișierul '{uploaded_file.name}' a fost trimis către contabil!")
            else:
                st.error("Te rugăm să selectezi un fișier mai întâi.")

    # --- LOGICĂ CONTABIL ---
    elif st.session_state.role == "contabil":
        st.title("📊 Dashboard Contabilitate")
        
        # Citire date din DB
        df = pd.read_sql("SELECT * FROM documents", conn)

        if not df.empty:
            st.subheader("Filtrează documentele primite")
            client_list = ["Toți"] + list(df["client"].unique())
            selected_client = st.selectbox("Selectează Clientul", client_list)
            
            if selected_client != "Toți":
                df = df[df["client"] == selected_client]

            st.dataframe(df[["client", "doc_type", "month", "upload_date"]], use_container_width=True)

            st.subheader("📥 Descărcare documente")
            file_to_download = st.selectbox("Selectează fișierul pentru vizualizare", df["file_path"])
            
            if file_to_download:
                try:
                    with open(file_to_download, "rb") as f:
                        btn = st.download_button(
                            label="Download Fișier",
                            data=f,
                            file_name=os.path.basename(file_to_download)
                        )
                except FileNotFoundError:
                    st.error("Fișierul nu mai există pe server.")
        else:
            st.info("Momentan nu a fost încărcat niciun document.")
