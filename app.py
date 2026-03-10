import streamlit as st
import sqlite3
import pandas as pd
import os
import bcrypt
from datetime import datetime

# --------------------
# DATABASE
# --------------------

conn = sqlite3.connect("database.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
id INTEGER PRIMARY KEY AUTOINCREMENT,
username TEXT,
password TEXT,
role TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS documents(
id INTEGER PRIMARY KEY AUTOINCREMENT,
client TEXT,
doc_type TEXT,
year TEXT,
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
# FUNCTII
# --------------------

def create_user(username,password,role):

    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

    cursor.execute(
        "INSERT INTO users(username,password,role) VALUES (?,?,?)",
        (username,hashed,role)
    )

    conn.commit()


def login(username,password):

    cursor.execute("SELECT * FROM users WHERE username=?",(username,))
    user = cursor.fetchone()

    if user:

        if bcrypt.checkpw(password.encode(), user[2]):
            return user

    return None


# --------------------
# SESSION
# --------------------

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False


# --------------------
# LOGIN / REGISTER
# --------------------

if not st.session_state.logged_in:

    menu = st.sidebar.selectbox("Menu",["Login","Register"])

    if menu == "Register":

        st.title("Creare cont")

        username = st.text_input("Username")
        password = st.text_input("Password",type="password")

        role = st.selectbox("Rol",["client","contabil"])

        if st.button("Register"):

            if username and password:

                create_user(username,password,role)

                st.success("Cont creat. Poți face login.")

            else:

                st.error("Completează toate câmpurile")


    if menu == "Login":

        st.title("Login portal documente")

        username = st.text_input("Username")
        password = st.text_input("Password",type="password")

        if st.button("Login"):

            user = login(username,password)

            if user:

                st.session_state.logged_in = True
                st.session_state.username = user[1]
                st.session_state.role = user[3]

                st.rerun()

            else:

                st.error("Login invalid")


# --------------------
# MAIN APP
# --------------------

else:

    st.sidebar.write(
        f"Logat ca: {st.session_state.username} ({st.session_state.role})"
    )

    if st.sidebar.button("Logout"):

        st.session_state.logged_in = False
        st.rerun()


# --------------------
# CLIENT PAGE
# --------------------

    if st.session_state.role == "client":

        st.title("📤 Upload documente")

        doc_type = st.selectbox(
            "Tip document",
            ["Factura","Bon","Extras bancar"]
        )

        month = st.selectbox(
            "Luna",
            ["Ianuarie","Februarie","Martie","Aprilie","Mai",
             "Iunie","Iulie","August","Septembrie","Octombrie",
             "Noiembrie","Decembrie"]
        )

        uploaded_file = st.file_uploader(
            "Încarcă document",
            type=["pdf","png","jpg"]
        )

        if uploaded_file:

            year = datetime.now().year

            folder = os.path.join(
                "documents",
                st.session_state.username,
                str(year),
                month
            )

            os.makedirs(folder,exist_ok=True)

            file_path = os.path.join(folder,uploaded_file.name)

            with open(file_path,"wb") as f:
                f.write(uploaded_file.getbuffer())

            cursor.execute(
                """INSERT INTO documents
                (client,doc_type,year,month,file_path,upload_date)
                VALUES (?,?,?,?,?,?)""",
                (
                    st.session_state.username,
                    doc_type,
                    str(year),
                    month,
                    file_path,
                    str(datetime.now())
                )
            )

            conn.commit()

            st.success("Document încărcat cu succes")


# --------------------
# CONTABIL DASHBOARD
# --------------------

    if st.session_state.role == "contabil":

        st.title("📊 Dashboard contabil")

        df = pd.read_sql("SELECT * FROM documents",conn)

        if not df.empty:

            col1,col2,col3 = st.columns(3)

            col1.metric("Total documente",len(df))
            col2.metric("Total clienți",df["client"].nunique())
            col3.metric("Ani disponibili",df["year"].nunique())

            st.divider()

            clients = st.selectbox(
                "Filtru client",
                ["Toți"] + list(df["client"].unique())
            )

            if clients != "Toți":

                df = df[df["client"] == clients]

            st.dataframe(df)

            st.divider()

            st.subheader("Preview document")

            file_to_open = st.selectbox(
                "Selectează document",
                df["file_path"]
            )

            if file_to_open:

                if file_to_open.endswith(".pdf"):

                    with open(file_to_open,"rb") as f:

                        st.download_button(
                            "Download document",
                            f,
                            file_name=os.path.basename(file_to_open)
                        )

                        st.write("Preview PDF:")
                        st.markdown(
                            f'<iframe src="{file_to_open}" width="700" height="800"></iframe>',
                            unsafe_allow_html=True
                        )

                else:

                    st.image(file_to_open)

        else:

            st.info("Nu există documente încă.")
