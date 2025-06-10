import streamlit as st
import sqlite3
from datetime import datetime, timedelta
from fpdf import FPDF
import os

# Initialize DB
def init_db():
    conn = sqlite3.connect("pharmacy.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT, password TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS inventory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    batch_no TEXT,
                    expiry_date TEXT,
                    quantity INTEGER,
                    price REAL,
                    purchase_price REAL
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS sales (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT,
                    medicine_name TEXT,
                    quantity INTEGER,
                    price_per_unit REAL,
                    total_price REAL,
                    buyer_name TEXT
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS purchases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT,
                    medicine_name TEXT,
                    batch_no TEXT,
                    expiry_date TEXT,
                    quantity INTEGER,
                    purchase_price REAL,
                    supplier TEXT
                )''')
    # Default login user
    c.execute("SELECT * FROM users WHERE username='admin'")
    if not c.fetchone():
        c.execute("INSERT INTO users VALUES (?, ?)", ('admin', 'admin123'))
    conn.commit()
    conn.close()

def login(username, password):
    conn = sqlite3.connect("pharmacy.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
    result = c.fetchone()
    conn.close()
    return result

def add_medicine(name, batch, expiry, qty, price, purchase_price):
    conn = sqlite3.connect("pharmacy.db")
    c = conn.cursor()
    c.execute("INSERT INTO inventory (name, batch_no, expiry_date, quantity, price, purchase_price) VALUES (?, ?, ?, ?, ?, ?)",
              (name, batch, expiry, qty, price, purchase_price))
    conn.commit()
    conn.close()

def update_quantity(med_id, qty_change):
    conn = sqlite3.connect("pharmacy.db")
    c = conn.cursor()
    c.execute("SELECT quantity FROM inventory WHERE id=?", (med_id,))
    current_qty = c.fetchone()[0]
    new_qty = current_qty + qty_change
    c.execute("UPDATE inventory SET quantity=? WHERE id=?", (new_qty, med_id))
    conn.commit()
    conn.close()

def record_sale(date, name, qty, unit_price, total, buyer):
    conn = sqlite3.connect("pharmacy.db")
    c = conn.cursor()
    c.execute("INSERT INTO sales (date, medicine_name, quantity, price_per_unit, total_price, buyer_name) VALUES (?, ?, ?, ?, ?, ?)",
              (date, name, qty, unit_price, total, buyer))
    conn.commit()
    conn.close()

def record_purchase(date, name, batch, expiry, qty, price, supplier):
    conn = sqlite3.connect("pharmacy.db")
    c = conn.cursor()
    c.execute("INSERT INTO purchases (date, medicine_name, batch_no, expiry_date, quantity, purchase_price, supplier) VALUES (?, ?, ?, ?, ?, ?, ?)",
              (date, name, batch, expiry, qty, price, supplier))
    conn.commit()
    conn.close()

def generate_invoice(buyer, items, total):
    if not os.path.exists("invoices"):
        os.makedirs("invoices")

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, f"Pharmacy Invoice", ln=True, align='C')
    pdf.cell(200, 10, f"Buyer: {buyer} - Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True)

    pdf.ln(10)
    pdf.set_font("Arial", size=10)
    pdf.cell(40, 10, "Medicine", 1)
    pdf.cell(30, 10, "Qty", 1)
    pdf.cell(30, 10, "Unit Price", 1)
    pdf.cell(40, 10, "Total", 1)
    pdf.ln()

    for item in items:
        pdf.cell(40, 10, item["name"], 1)
        pdf.cell(30, 10, str(item["qty"]), 1)
        pdf.cell(30, 10, f"{item['price']:.2f}", 1)
        pdf.cell(40, 10, f"{item['qty'] * item['price']:.2f}", 1)
        pdf.ln()

    pdf.cell(140, 10, "Total:", 1)
    pdf.cell(40, 10, f"{total:.2f}", 1)

    filename = f"invoices/invoice_{buyer}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
    pdf.output(filename)
    return filename

# ----------------- STREAMLIT UI -------------------

st.set_page_config(page_title="Pharmacy App", layout="centered")
init_db()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# ---------------- Login ----------------
if not st.session_state.logged_in:
    st.title("🔐 Pharmacy Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if login(username, password):
            st.success("Login successful!")
            st.session_state.logged_in = True
        else:
            st.error("Invalid credentials")

# ---------------- App ----------------
else:
    menu = st.sidebar.selectbox("📋 Menu", ["Dashboard", "Inventory", "Purchase", "Sell", "Expiry Tracker", "Reports", "Logout"])

    if menu == "Logout":
        st.session_state.logged_in = False
        st.experimental_rerun()

    elif menu == "Dashboard":
        st.title("📊 Dashboard")
        conn = sqlite3.connect("pharmacy.db")
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM inventory")
        total_meds = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM sales WHERE date=?", (datetime.today().strftime('%Y-%m-%d'),))
        today_sales = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM inventory WHERE expiry_date <= ?", ((datetime.today() + timedelta(days=30)).strftime('%Y-%m-%d'),))
        expiring_soon = c.fetchone()[0]
        conn.close()

        st.metric("🧪 Total Medicines", total_meds)
        st.metric("🧾 Sales Today", today_sales)
        st.metric("⏰ Expiring in 30 Days", expiring_soon)

    elif menu == "Inventory":
        st.title("📦 Inventory")
        with st.form("Add Medicine"):
            name = st.text_input("Medicine Name")
            batch = st.text_input("Batch No.")
            expiry = st.date_input("Expiry Date")
            qty = st.number_input("Quantity", min_value=1)
            price = st.number_input("Selling Price (per unit)")
            purchase_price = st.number_input("Purchase Price (per unit)")
            submitted = st.form_submit_button("Add")
            if submitted:
                add_medicine(name, batch, expiry.strftime('%Y-%m-%d'), qty, price, purchase_price)
                st.success("Medicine added!")

        st.subheader("📋 Current Inventory")
        conn = sqlite3.connect("pharmacy.db")
        df = conn.execute("SELECT * FROM inventory").fetchall()
        conn.close()
        for row in df:
            st.write(f"🧪 **{row[1]}** | Batch: {row[2]} | Expiry: {row[3]} | Qty: {row[4]} | ₹{row[5]}")

    elif menu == "Purchase":
        st.title("📥 Record Purchase")
        with st.form("purchase_form"):
            name = st.text_input("Medicine Name")
            batch = st.text_input("Batch No.")
            expiry = st.date_input("Expiry Date")
            qty = st.number_input("Quantity", min_value=1)
            purchase_price = st.number_input("Purchase Price")
            supplier = st.text_input("Supplier")
            submit = st.form_submit_button("Add Stock")
            if submit:
                add_medicine(name, batch, expiry.strftime('%Y-%m-%d'), qty, 0, purchase_price)
                record_purchase(datetime.today().strftime('%Y-%m-%d'), name, batch, expiry.strftime('%Y-%m-%d'), qty, purchase_price, supplier)
                st.success("Stock updated!")

    elif menu == "Sell":
        st.title("🛒 Sell Medicine")
        buyer = st.text_input("Buyer's Name")
        conn = sqlite3.connect("pharmacy.db")
        meds = conn.execute("SELECT id, name, quantity, price FROM inventory").fetchall()
        conn.close()

        cart = []
        for med in meds:
            qty_to_sell = st.number_input(f"{med[1]} (Stock: {med[2]})", min_value=0, max_value=med[2], key=f"sell_{med[0]}")
            if qty_to_sell > 0:
                cart.append({"id": med[0], "name": med[1], "qty": qty_to_sell, "price": med[3]})

        if st.button("Complete Sale"):
            if buyer and cart:
                total = sum(item["qty"] * item["price"] for item in cart)
                for item in cart:
                    update_quantity(item["id"], -item["qty"])
                    record_sale(datetime.today().strftime('%Y-%m-%d'), item["name"], item["qty"], item["price"], item["qty"] * item["price"], buyer)
                pdf_file = generate_invoice(buyer, cart, total)
                st.success("Sale recorded!")
                st.download_button("📥 Download Invoice", data=open(pdf_file, "rb").read(), file_name=os.path.basename(pdf_file))
            else:
                st.error("Please fill buyer name and select at least 1 item.")

    elif menu == "Expiry Tracker":
        st.title("⏰ Expiry Tracker")
        today = datetime.today()
        limit = today + timedelta(days=90)
        conn = sqlite3.connect("pharmacy.db")
        data = conn.execute("SELECT * FROM inventory WHERE expiry_date <= ?", (limit.strftime('%Y-%m-%d'),)).fetchall()
        conn.close()
        for row in data:
            exp_date = datetime.strptime(row[3], '%Y-%m-%d')
            color = "🔴" if exp_date < today else "🟠"
            st.write(f"{color} **{row[1]}** | Expiry: {row[3]} | Qty: {row[4]}")

    elif menu == "Reports":
        st.title("📑 Sales Report")
        conn = sqlite3.connect("pharmacy.db")
        rows = conn.execute("SELECT * FROM sales ORDER BY date DESC LIMIT 30").fetchall()
        conn.close()
        for r in rows:
            st.write(f"{r[1]} | {r[2]} x {r[3]} = ₹{r[5]} | Buyer: {r[6]}")
    elif menu == "User Management":
        st.title("👥 User Management")

        # Add User
        st.subheader("➕ Add New User")
        new_user = st.text_input("New Username")
        new_pass = st.text_input("New Password", type="password")
        if st.button("Add User"):
            if new_user and new_pass:
                conn = sqlite3.connect("pharmacy.db")
                c = conn.cursor()
                c.execute("SELECT * FROM users WHERE username=?", (new_user,))
                if c.fetchone():
                    st.warning("Username already exists!")
                else:
                    c.execute("INSERT INTO users VALUES (?, ?)", (new_user, new_pass))
                    conn.commit()
                    st.success("User added successfully!")
                conn.close()
            else:
                st.warning("Please enter both username and password.")

        # Existing Users
        st.subheader("📋 Existing Users")
        conn = sqlite3.connect("pharmacy.db")
        c = conn.cursor()
        users = c.execute("SELECT username FROM users").fetchall()
        conn.close()

        for user in users:
            if user[0] != "admin":
                col1, col2 = st.columns([3, 1])
                col1.write(user[0])
                if col2.button("Delete", key=user[0]):
                    conn = sqlite3.connect("pharmacy.db")
                    c = conn.cursor()
                    c.execute("DELETE FROM users WHERE username=?", (user[0],))
                    conn.commit()
                    conn.close()
                    st.success(f"Deleted user {user[0]}")
                    st.experimental_rerun()
