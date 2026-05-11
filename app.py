import streamlit as st
import json
from pathlib import Path
from datetime import datetime, date
import uuid
import os
from dotenv import load_dotenv
from bot_logic import SalonContextStore, ChatLoggerStore, SalonAssistantBot

load_dotenv()

# Naming the website
st.set_page_config(
    page_title="Polished to Perfection",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Session State
# -----------------------------
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "user" not in st.session_state:
    st.session_state["user"] = None
if "role" not in st.session_state:
    st.session_state["role"] = None
if "page" not in st.session_state:
    st.session_state["page"] = "dashboard"
if "selected_appointment_id" not in st.session_state:
    st.session_state["selected_appointment_id"] = None
if "restock_item_id" not in st.session_state:
    st.session_state["restock_item_id"] = None
if "appointment_status_filter" not in st.session_state:
    st.session_state["appointment_status_filter"] = "All"
if "customer_history_filter" not in st.session_state:
    st.session_state["customer_history_filter"] = "All"
if "messages" not in st.session_state:
    st.session_state["messages"] = []
if "messages_loaded_for" not in st.session_state:
    st.session_state["messages_loaded_for"] = None

# Adding the files
# -----------------------------
users_file = Path("users.json")
appt_file = Path("appointments.json")
inventory_file = Path("inventory.json")
feedback_file = Path("feedback.json")
chat_logs_file = Path("chat_logs.json")


# Loading the data
# ------------------------------
if users_file.exists():
    with open(users_file, "r") as f:
        users = json.load(f)
else:
    users = []
    with open(users_file, "w") as f:
        json.dump(users, f, indent=4)

if appt_file.exists():
    with open(appt_file, "r") as f:
        appointments = json.load(f)
else:
    appointments = []
    with open(appt_file, "w") as f:
        json.dump(appointments, f, indent=4)

if inventory_file.exists():
    with open(inventory_file, "r") as f:
        inventory = json.load(f)
else:
    inventory = []
    with open(inventory_file, "w") as f:
        json.dump(inventory, f, indent=4)

if feedback_file.exists():
    with open(feedback_file, "r") as f:
        feedback_list = json.load(f)
else:
    feedback_list = []
    with open(feedback_file, "w") as f:
        json.dump(feedback_list, f, indent=4)

# Loading the chat logs
# -----------------------------
if chat_logs_file.exists():
    with open(chat_logs_file, "r") as f:
        chat_logs = json.load(f)
else:
    chat_logs = []
    with open(chat_logs_file, "w") as f:
        json.dump(chat_logs, f, indent=4)

# Pricing and tools needed
# -----------------------------
service_prices = {
    "Basic Manicure": 20,
    "Gel Manicure": 35,
    "Classic Pedicure": 30,
    "Acrylic Full Set": 50,
    "Nail Art Design": 15
}

service_inventory_map = {
    "Basic Manicure": ["Cuticle Oil", "Cotton Pads"],
    "Gel Manicure": ["Gel Polish", "Cuticle Oil", "Cotton Pads"],
    "Classic Pedicure": ["Cuticle Oil", "Cotton Pads"],
    "Acrylic Full Set": ["Acrylic Powder", "Nail Files", "Cotton Pads"],
    "Nail Art Design": ["Nail Files", "Cotton Pads"]
}

# Rewards Program and the points
reward_options = [
    {"name": "10% Off Next Service", "points": 50},
    {"name": "Free Nail Art Design", "points": 100},
    {"name": "Free Basic Manicure", "points": 250},
    {"name": "Free Gel Manicure", "points": 400}
]

# Employees name for booking availability
employee_names = ["Marissa", "Jackie", "Eesha Shahi"]

# Timing of the salon and bookings
all_times = [
    "9:00 AM",
    "10:00 AM",
    "11:00 AM",
    "12:00 PM",
    "1:00 PM",
    "2:00 PM",
    "3:00 PM",
    "4:00 PM",
    "5:00 PM"
]


# Save functions
# -----------------------------
def save_users():
    with open(users_file, "w") as f:
        json.dump(users, f, indent=4)


def save_appointments():
    with open(appt_file, "w") as f:
        json.dump(appointments, f, indent=4)


def save_inventory():
    with open(inventory_file, "w") as f:
        json.dump(inventory, f, indent=4)


def save_feedback():
    with open(feedback_file, "w") as f:
        json.dump(feedback_list, f, indent=4)


# Refresh the logged-in user data because it may change
def refresh_logged_in_user():
    if st.session_state["user"] is not None:
        for user in users:
            if user["id"] == st.session_state["user"]["id"]:
                st.session_state["user"] = user
                break


# Making sure each of the rewards have fields and they work
def ensure_user_reward_fields(user):
    updated = False
    if "reward_points" not in user:
        user["reward_points"] = 0
        updated = True
    if "reward_history" not in user:
        user["reward_history"] = []
        updated = True
    return updated


# Finding the next appointment id
def get_next_appointment_id():
    if len(appointments) == 0:
        return 1

    max_id = 0
    for appt in appointments:
        if appt["id"] > max_id:
            max_id = appt["id"]

    return max_id + 1


# Finding the next feedback id
def get_next_feedback_id():
    if len(feedback_list) == 0:
        return 1

    max_id = 0
    for feedback in feedback_list:
        if feedback["id"] > max_id:
            max_id = feedback["id"]

    return max_id + 1


# Calculate the 20% tip
def calculate_tip(price):
    return round(price * 0.20, 2)


# Calculate the total charge including the 20% tip
def calculate_total_charge(price):
    return round(price + calculate_tip(price), 2)


# Find one inventory item by its item name
def get_item_by_name(item_name):
    for item in inventory:
        if item["item_name"] == item_name:
            return item
    return None


# Check whether all needed inventory exists for a service
def has_inventory_for_service(service_name):
    required_items = service_inventory_map[service_name]

    for required_item in required_items:
        item = get_item_by_name(required_item)

        if item is None or item["quantity"] < 1:
            return False

    return True


# Add or subtract inventory when appointments are booked or canceled
def update_inventory_for_service(service_name, action):
    required_items = service_inventory_map[service_name]

    if action == "subtract":
        for required_item in required_items:
            item = get_item_by_name(required_item)

            if item is None or item["quantity"] < 1:
                return False

        for required_item in required_items:
            item = get_item_by_name(required_item)
            item["quantity"] -= 1

        return True

    if action == "add":
        for required_item in required_items:
            item = get_item_by_name(required_item)

            if item:
                item["quantity"] += 1

        return True

    return False


# Get only the appointments that belong to the logged-in customer
def get_user_appointments():
    user_appts = []

    for appt in appointments:
        if appt.get("client_email") == st.session_state["user"]["email"]:
            user_appts.append(appt)

    return user_appts


# Get only the appointments assigned to the logged-in employee
def get_employee_appointments():
    employee_appts = []

    for appt in appointments:
        if appt.get("employee") == st.session_state["user"]["full_name"]:
            employee_appts.append(appt)

    return employee_appts


# Check if an appointment time is already in the past
def is_past_appointment(appt):
    appointment_datetime = datetime.strptime(
        f"{appt['date']} {appt['time']}",
        "%Y-%m-%d %I:%M %p"  # used ai to help run this line of code
    )

    return appointment_datetime < datetime.now()


# Add reward points to a customer after a completed appointment
def add_reward_points_to_customer(customer_email, points_to_add):
    for user in users:
        if user["email"] == customer_email:
            ensure_user_reward_fields(user)
            user["reward_points"] += points_to_add
            break

    save_users()
    refresh_logged_in_user()


# Redeem a reward if the customer has enough points
def redeem_reward_for_customer(user_id, reward_name, reward_cost):
    for user in users:
        if user["id"] == user_id:
            ensure_user_reward_fields(user)

            if user["reward_points"] >= reward_cost:
                user["reward_points"] -= reward_cost

                user["reward_history"].append({
                    "reward_name": reward_name,
                    "points_used": reward_cost,
                    "redeemed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "status": "Available"
                })

                save_users()
                refresh_logged_in_user()

                return True

    return False


# Count how many inventory items are low on stock
def get_low_stock_count():
    count = 0

    for item in inventory:
        if item["quantity"] <= item["low_stock_limit"]:
            count += 1

    return count


# Revenue helpers
# -----------------------------
def get_completed_appointments():
    completed = []

    for appt in appointments:
        if appt.get("status") == "Completed":
            completed.append(appt)

    return completed


def get_appointment_basic_charge(appt):
    return round(appt.get("price", 0), 2)


def get_appointment_tip(appt):
    basic_charge = get_appointment_basic_charge(appt)
    return round(appt.get("tip_amount", calculate_tip(basic_charge)), 2)


def get_appointment_total_charge(appt):
    basic_charge = get_appointment_basic_charge(appt)
    return round(appt.get("total_charge", calculate_total_charge(basic_charge)), 2)


def get_employee_total_charge_with_tips():
    total = 0

    for appt in get_completed_appointments():
        if appt.get("employee") == st.session_state["user"]["full_name"]:
            total += get_appointment_total_charge(appt)

    return round(total, 2)


updated_users = False

for user in users:
    if ensure_user_reward_fields(user):  # USED AI to help us with this part because we were getting errors
        updated_users = True

if updated_users:
    save_users()

# Penny Chat Page
# -----------------------------
def show_penny_chat():
    st.title("Penny the Polish Pro")
    st.caption("Your AI salon assistant.")

    st.divider()

    st.info(
        "Ask Penny about appointments, booking, cancellations, services, rewards, feedback, nail tech information, inventory, and salon operations."
    )

    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        try:
            api_key = st.secrets.get("OPENAI_API_KEY", None)
        except Exception:
            api_key = None

    if not api_key:
        st.error("OPENAI_API_KEY was not found. Check your .env file or Streamlit Secrets.")
        st.stop()

    # 1. Setup the objects
    context_store = SalonContextStore(
        users_path="users.json",
        appointments_path="appointments.json",
        inventory_path="inventory.json",
        feedback_path="feedback.json"
    )

    logger = ChatLoggerStore("chat_logs.json")

    salon_context = context_store.get_salon_context_as_string(
        current_user=st.session_state["user"],
        role=st.session_state["role"],
        service_prices=service_prices,
        reward_options=reward_options,
        employee_names=employee_names
    )

    bot = SalonAssistantBot(
        api_key=api_key,
        context_data=salon_context,
        role=st.session_state["role"]
    )

    user_email = st.session_state["user"]["email"]

    # 2. Initialize visible chat history
    # st.session_state["messages"] is only for user-facing chat bubbles.
    # The hidden system prompt does not belong in this list.
    if "messages_loaded_for" not in st.session_state:
        st.session_state["messages_loaded_for"] = None

    if st.session_state["messages_loaded_for"] != user_email:
        st.session_state["messages"] = []

        logs = logger.load_logs_for_user(user_email)

        for log in logs:
            st.session_state["messages"].append({
                "role": "user",
                "content": log["user_message"]
            })

            st.session_state["messages"].append({
                "role": "assistant",
                "content": log["assistant_message"]
            })

        if len(st.session_state["messages"]) == 0:
            st.session_state["messages"].append({
                "role": "assistant",
                "content": "Hi! I’m Penny the Polish Pro. Ask me a question about Polished to Perfection."
            })

        st.session_state["messages_loaded_for"] = user_email

    col1, col2 = st.columns([1, 4])

    with col1:
        if st.button("Clear Chat", key="clear_penny_chat", type="primary"):
            st.session_state["messages"] = []
            logger.clear_logs_for_user(user_email)
            st.session_state["messages"].append({
                "role": "assistant",
                "content": "Chat cleared! Ask me a new question about Polished to Perfection."
            })
            st.rerun()

    # 3. Render previous chat history to the screen
    chat_container = st.container()

    with chat_container:
        for message in st.session_state["messages"]:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    # 4. Handle new user input
    user_input = st.chat_input(
        "Ask Penny the Polish Pro something...",
        key="penny_chat_input"
    )

    if user_input:
        # Update state and UI with user message
        st.session_state["messages"].append({
            "role": "user",
            "content": user_input
        })

        with chat_container.chat_message("user"):
            st.markdown(user_input)

        # Get and show AI response
        with chat_container.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response_text = bot.get_ai_response(
                    st.session_state["messages"]
                )

                st.markdown(response_text)

        # Update visible session state with AI response
        st.session_state["messages"].append({
            "role": "assistant",
            "content": response_text
        })

        # Save only the real interaction.
        # Do not save the hidden AI prompt.
        logger.append_log(
            user_email=user_email,
            user_message=user_input,
            assistant_message=response_text
        )

# Sidebar Navigation
# -----------------------------
if st.session_state["logged_in"]:
    refresh_logged_in_user()

    with st.sidebar:
        st.markdown("## Polished to Perfection")
        st.caption("Salon Management System")
        st.info("Book appointments, manage rewards, track revenue, and manage salon feedback.")

        st.write(f"Logged in as: {st.session_state['user']['full_name']}")
        st.write(f"Role: {st.session_state['role']}")

        st.divider()

        if st.session_state["role"] == "Customer":
            if st.button("Customer Dashboard", key="customer_dashboard_btn", type="primary", use_container_width=True):
                st.session_state["page"] = "dashboard"
                st.rerun()

            if st.button("Book Appointment", key="book_appointment_btn", type="primary", use_container_width=True):
                st.session_state["page"] = "book_appointment"
                st.rerun()

            if st.button("My Appointments", key="my_appointments_btn", type="primary", use_container_width=True):
                st.session_state["page"] = "my_appointments"
                st.rerun()

            if st.button("Rewards", key="rewards_btn", type="primary", use_container_width=True):
                st.session_state["page"] = "rewards"
                st.rerun()

            if st.button("Feedback Form", key="feedback_form_btn", type="primary", use_container_width=True):
                st.session_state["page"] = "feedback_form"
                st.rerun()

            if st.button("Penny the Polish Pro", key="penny_chat_btn", type="primary", use_container_width=True):
                st.session_state["page"] = "penny_chat"
                st.rerun()

        elif st.session_state["role"] == "Employee":
            if st.button("Employee Dashboard", key="employee_dashboard_btn", type="primary", use_container_width=True):
                st.session_state["page"] = "dashboard"
                st.rerun()

            if st.button("Manage Appointments", key="manage_appointments_btn", type="primary", use_container_width=True):
                st.session_state["page"] = "manage_appointments"
                st.rerun()

            if st.button("Inventory", key="inventory_btn", type="primary", use_container_width=True):
                st.session_state["page"] = "inventory"
                st.rerun()

            if st.button("Low Stock Alerts", key="low_stock_btn", type="primary", use_container_width=True):
                st.session_state["page"] = "low_stock"
                st.rerun()

            if st.button("Revenue Tracker", key="revenue_tracker_btn", type="primary", use_container_width=True):
                st.session_state["page"] = "revenue_tracker"
                st.rerun()

            if st.button("Review Feedback", key="review_feedback_btn", type="primary", use_container_width=True):
                st.session_state["page"] = "review_feedback"
                st.rerun()
           
            if st.button("Penny the Polish Pro", key="employee_penny_chat_btn", type="primary", use_container_width=True):
                st.session_state["page"] = "penny_chat"
                st.rerun()

        st.divider()

        if st.button("Logout", key="logout_btn", use_container_width=True):
            st.session_state["logged_in"] = False
            st.session_state["user"] = None
            st.session_state["role"] = None
            st.session_state["page"] = "dashboard"
            st.session_state["selected_appointment_id"] = None
            st.session_state["restock_item_id"] = None
            st.session_state["messages"] = []
            st.session_state["messages_loaded_for"] = None
            st.rerun()


# Authentication for log in
# -----------------------------
if not st.session_state["logged_in"]:
    st.title("Polished to Perfection")
    st.caption("Salon Management System")
    st.info("Welcome! Create an account or log in to manage appointments, rewards, feedback, revenue, and inventory.")

    st.divider()

    register_tab, login_tab = st.tabs(["Register", "Login"])

    with register_tab:
        st.subheader("Create Account")

        reg_email = st.text_input("Email", key="reg_email").strip().lower()
        reg_name = st.text_input("Full Name", key="reg_name").strip()
        reg_password = st.text_input("Password", type="password", key="reg_password")
        reg_role = st.selectbox("Role", ["Customer", "Employee"], key="reg_role")

        if st.button("Create Account", key="create_account_btn", type="primary", use_container_width=True):
            if not reg_email or not reg_name or not reg_password:
                st.error("Please fill in all fields.")

            elif "@" not in reg_email or "." not in reg_email:
                st.error("Please enter a valid email address.")

            elif len(reg_password) < 6:
                st.error("Password must be at least 6 characters long.")

            else:
                email_exists = False

                for user in users:
                    if user["email"].lower() == reg_email.lower():
                        email_exists = True
                        break

                if email_exists:
                    st.error("An account with that email already exists.")

                else:
                    with st.spinner("Recording..."):
                        new_user = {
                            "id": str(uuid.uuid4()),
                            "email": reg_email,
                            "full_name": reg_name,
                            "password": reg_password,
                            "role": reg_role,
                            "registered_at": str(datetime.now()),
                            "reward_points": 0,
                            "reward_history": []
                        }

                        users.append(new_user)
                        save_users()

                    st.success("Account created successfully. You can now log in.")

    with login_tab:
        st.subheader("Login")

        login_email = st.text_input("Email", key="login_email").strip().lower()
        login_password = st.text_input("Password", type="password", key="login_password")

        if st.button("Log In", key="login_btn", type="primary", use_container_width=True):
            user_found = None

            for user in users:
                if user["email"].lower() == login_email and user["password"] == login_password:
                    user_found = user
                    break

            if user_found:
                with st.spinner("Recording..."):
                    st.session_state["logged_in"] = True
                    st.session_state["user"] = user_found
                    st.session_state["role"] = user_found["role"]
                    st.session_state["page"] = "dashboard"
                    st.session_state["messages"] = []
                    st.session_state["messages_loaded_for"] = None

                st.success("Login successful!")
                st.rerun()

            else:
                st.error("Invalid credentials.")


# Logged-In Pages
# -----------------------------
else:
    if st.session_state["role"] == "Customer":
        user_appts = get_user_appointments()

        upcoming_count = 0
        old_count = 0
        canceled_count = 0
        customer_feedback_count = 0

        for appt in user_appts:
            if appt.get("status") == "Canceled":
                canceled_count += 1

            elif appt.get("status") == "Completed":
                old_count += 1

            elif is_past_appointment(appt):
                old_count += 1

            else:
                upcoming_count += 1

        for feedback in feedback_list:
            if feedback.get("customer_email") == st.session_state["user"]["email"]:
                customer_feedback_count += 1

        reward_points = st.session_state["user"].get("reward_points", 0)
        reward_history = st.session_state["user"].get("reward_history", [])

        # Customer Dashboard
        if st.session_state["page"] == "dashboard":
            st.title("Polished to Perfection")
            st.subheader("Customer Dashboard")

            st.divider()

            col1, col2, col3, col4, col5 = st.columns(5)

            with col1:
                with st.container(border=True):
                    st.success("Upcoming")
                    st.markdown(f"### {upcoming_count}")
                    st.caption("Scheduled")

            with col2:
                with st.container(border=True):
                    st.info("Old")
                    st.markdown(f"### {old_count}")
                    st.caption("Past")

            with col3:
                with st.container(border=True):
                    st.error("Canceled")
                    st.markdown(f"### {canceled_count}")
                    st.caption("Canceled visits")

            with col4:
                with st.container(border=True):
                    st.warning("Rewards")
                    st.markdown(f"### {reward_points}")
                    st.caption("Reward points")

            with col5:
                with st.container(border=True):
                    st.info("Feedback")
                    st.markdown(f"### {customer_feedback_count}")
                    st.caption("Submitted forms")

            st.divider()

            col1, col2 = st.columns([3, 2])

            with col1:
                with st.container(border=True):
                    st.markdown("### Quick Overview")

                    if len(user_appts) > 0:
                        for appt in user_appts:
                            st.markdown(
                                f"**{appt['service']}** | {appt['date']} at {appt['time']} | {appt.get('status', 'Scheduled')}"
                            )

                    else:
                        st.info("No appointments found.")

            with col2:
                with st.container(border=True):
                    st.markdown("### Customer Actions")
                    st.write("Earn 10 points for every completed appointment.")
                    st.write("A 20% tip is automatically added to every appointment.")
                    st.write("Submit feedback or complaints using the feedback form.")
                    st.write(f"Your current points: {reward_points}")

                    if st.button("Open Feedback Form", key="dashboard_feedback_btn", type="primary", use_container_width=True):
                        st.session_state["page"] = "feedback_form"
                        st.rerun()

        # Booking page
        elif st.session_state["page"] == "book_appointment":
            st.title("Book Appointment")
            st.caption("Choose your service, nail tech, date, and time.")

            st.divider()

            col1, col2, col3 = st.columns([1, 3, 1])

            with col2:
                with st.container(border=True):
                    nail_service = st.selectbox("Service", list(service_prices.keys()), key="service_select")
                    employee = st.selectbox("Employee Name", employee_names, key="employee_select")
                    selected_date = st.date_input("Date", key="date_select")

                    booked_times = []

                    for appt in appointments:
                        if (
                            appt["employee"] == employee
                            and appt["date"] == str(selected_date)
                            and appt.get("status") != "Canceled"
                        ):
                            booked_times.append(appt["time"])

                    available_times = []

                    for appt_time in all_times:
                        if appt_time not in booked_times:
                            available_times.append(appt_time)

                    if len(available_times) > 0:
                        selected_time = st.selectbox("Time", available_times, key="time_select")

                    else:
                        selected_time = None
                        st.warning("No available times for this employee on this date.")

                    basic_price = service_prices[nail_service]
                    tip_amount = calculate_tip(basic_price)
                    total_charge = calculate_total_charge(basic_price)

                    st.success(f"Basic Charge: ${basic_price}")
                    st.info(f"20% Tip: ${tip_amount}")
                    st.warning(f"Total Charge: ${total_charge}")

                    if st.button("Book Appointment", key="book_appointment_submit_btn", type="primary", use_container_width=True):
                        if selected_date < date.today():
                            st.error("You cannot book an appointment in the past.")

                        elif not selected_time:
                            st.error("Please choose a date with an available time.")

                        elif not has_inventory_for_service(nail_service):
                            st.error("Not enough inventory available to book this appointment.")

                        else:
                            subtract_success = False

                            with st.spinner("Recording..."):
                                new_appt = {
                                    "id": get_next_appointment_id(),
                                    "service": nail_service,
                                    "price": basic_price,
                                    "tip_amount": tip_amount,
                                    "total_charge": total_charge,
                                    "date": str(selected_date),
                                    "time": selected_time,
                                    "employee": employee,
                                    "client": st.session_state["user"]["full_name"],
                                    "client_email": st.session_state["user"]["email"],
                                    "status": "Scheduled",
                                    "created_at": str(datetime.now()),
                                    "canceled_at": ""
                                }

                                subtract_success = update_inventory_for_service(nail_service, "subtract")

                                if subtract_success:
                                    appointments.append(new_appt)
                                    save_appointments()
                                    save_inventory()

                            if not subtract_success:
                                st.error("Inventory could not be updated for this appointment.")

                            else:
                                st.success("Appointment booked successfully.")
                                st.session_state["page"] = "my_appointments"
                                st.rerun()

        # Appointment Page
        elif st.session_state["page"] == "my_appointments":
            st.title("My Appointments")
            st.caption("View upcoming, old, and canceled appointments.")

            st.divider()

            history_search = st.text_input("Search by service", key="customer_history_search")

            history_filter = st.selectbox(
                "Status",
                ["All", "Upcoming", "Old", "Canceled"],
                key="customer_history_filter_box"
            )

            st.session_state["customer_history_filter"] = history_filter

            upcoming_tab, old_tab, canceled_tab = st.tabs(["Upcoming", "Old", "Canceled"])

            with upcoming_tab:
                upcoming_appointments = []

                for appt in user_appts:
                    matches_search = history_search.lower() in appt["service"].lower()
                    is_upcoming = appt.get("status") not in ["Canceled", "Completed"] and not is_past_appointment(appt)
                    matches_filter = st.session_state["customer_history_filter"] in ["All", "Upcoming"]

                    if matches_search and is_upcoming and matches_filter:
                        upcoming_appointments.append(appt)

                col1, col2 = st.columns([3, 2])

                with col1:
                    with st.container(border=True):
                        st.markdown("### Appointment List")

                        if len(upcoming_appointments) > 0:
                            appointment_table = []

                            for appt in upcoming_appointments:
                                appointment_table.append({
                                    "Service": appt["service"],
                                    "Date": appt["date"],
                                    "Time": appt["time"],
                                    "Employee": appt["employee"],
                                    "Status": appt.get("status", "Scheduled"),
                                    "Basic Charge": get_appointment_basic_charge(appt),
                                    "20% Tip": get_appointment_tip(appt),
                                    "Total Charge": get_appointment_total_charge(appt)
                                })

                            st.dataframe(appointment_table, use_container_width=True)

                            selected_upcoming_appt = st.selectbox(
                                "Select Appointment",
                                upcoming_appointments,
                                format_func=lambda x: f"{x['service']} | {x['date']} {x['time']} | {x['employee']}",
                                key="customer_upcoming_selectbox"
                            )

                            if selected_upcoming_appt:
                                st.session_state["selected_appointment_id"] = selected_upcoming_appt["id"]

                        else:
                            st.info("No upcoming appointments found.")

                with col2:
                    with st.container(border=True):
                        st.markdown("### Appointment Details")

                        selected_appt = None

                        for appt in upcoming_appointments:
                            if appt["id"] == st.session_state["selected_appointment_id"]:
                                selected_appt = appt
                                break

                        if selected_appt:
                            st.markdown(f"**Service:** {selected_appt['service']}")
                            st.markdown(f"**Basic Charge:** ${get_appointment_basic_charge(selected_appt)}")
                            st.markdown(f"**20% Tip:** ${get_appointment_tip(selected_appt)}")
                            st.markdown(f"**Total Charge:** ${get_appointment_total_charge(selected_appt)}")
                            st.markdown(f"**Date:** {selected_appt['date']}")
                            st.markdown(f"**Time:** {selected_appt['time']}")
                            st.markdown(f"**Employee:** {selected_appt['employee']}")
                            st.markdown(f"**Status:** {selected_appt.get('status', 'Scheduled')}")

                            if is_past_appointment(selected_appt):
                                st.warning("This appointment has already passed and can no longer be canceled.")

                            else:
                                if st.button(
                                    "Cancel Appointment",
                                    key=f"cancel_appointment_{selected_appt['id']}",
                                    type="primary",
                                    use_container_width=True
                                ):
                                    with st.spinner("Recording..."):
                                        for appt in appointments:
                                            if appt["id"] == selected_appt["id"]:
                                                appt["status"] = "Canceled"
                                                appt["canceled_at"] = str(datetime.now())
                                                update_inventory_for_service(appt["service"], "add")
                                                break

                                        save_appointments()
                                        save_inventory()

                                    st.success("Appointment canceled successfully.")
                                    st.session_state["selected_appointment_id"] = None
                                    st.rerun()

                        else:
                            st.info("Select an appointment to view details.")

            with old_tab:
                old_appointments = []

                for appt in user_appts:
                    matches_search = history_search.lower() in appt["service"].lower()
                    is_old = appt.get("status") == "Completed" or (
                        is_past_appointment(appt)
                        and appt.get("status") != "Canceled"
                    )
                    matches_filter = st.session_state["customer_history_filter"] in ["All", "Old"]

                    if matches_search and is_old and matches_filter:
                        old_appointments.append(appt)

                if len(old_appointments) > 0:
                    old_table = []

                    for appt in old_appointments:
                        display_status = appt.get("status", "Scheduled")

                        if display_status == "Scheduled" and is_past_appointment(appt):
                            display_status = "Completed"

                        old_table.append({
                            "Service": appt["service"],
                            "Date": appt["date"],
                            "Time": appt["time"],
                            "Employee": appt["employee"],
                            "Status": display_status,
                            "Basic Charge": get_appointment_basic_charge(appt),
                            "20% Tip": get_appointment_tip(appt),
                            "Total Charge": get_appointment_total_charge(appt)
                        })

                    st.dataframe(old_table, use_container_width=True)

                else:
                    st.info("No old appointments found.")

            with canceled_tab:
                canceled_appointments = []

                for appt in user_appts:
                    matches_search = history_search.lower() in appt["service"].lower()
                    is_canceled = appt.get("status") == "Canceled"
                    matches_filter = st.session_state["customer_history_filter"] in ["All", "Canceled"]

                    if matches_search and is_canceled and matches_filter:
                        canceled_appointments.append(appt)

                if len(canceled_appointments) > 0:
                    canceled_table = []

                    for appt in canceled_appointments:
                        canceled_table.append({
                            "Service": appt["service"],
                            "Date": appt["date"],
                            "Time": appt["time"],
                            "Employee": appt["employee"],
                            "Status": appt.get("status", "Canceled"),
                            "Basic Charge": get_appointment_basic_charge(appt),
                            "20% Tip": get_appointment_tip(appt),
                            "Total Charge": get_appointment_total_charge(appt)
                        })

                    st.dataframe(canceled_table, use_container_width=True)

                else:
                    st.info("No canceled appointments found.")

        # Rewards Page
        elif st.session_state["page"] == "rewards":
            st.title("Rewards Program")
            st.caption("Redeem your points for salon rewards.")

            st.divider()

            redeem_tab, history_tab = st.tabs(["Redeem Reward", "Reward History"])

            with redeem_tab:
                col1, col2, col3 = st.columns([1, 3, 1])

                with col2:
                    with st.container(border=True):
                        st.markdown("### Available Rewards")
                        st.warning(f"Current Points: {reward_points}")

                        st.divider()

                        for reward in reward_options:
                            with st.container(border=True):
                                st.markdown(f"**Reward:** {reward['name']}")
                                st.markdown(f"**Points Required:** {reward['points']}")

                                if reward_points >= reward["points"]:
                                    if st.button(
                                        f"Redeem {reward['name']}",
                                        key=f"redeem_{reward['name']}",
                                        type="primary",
                                        use_container_width=True
                                    ):
                                        redeemed = False

                                        with st.spinner("Recording..."):
                                            redeemed = redeem_reward_for_customer(
                                                st.session_state["user"]["id"],
                                                reward["name"],
                                                reward["points"]
                                            )

                                        if redeemed:
                                            st.success(f"{reward['name']} redeemed successfully.")
                                            st.rerun()

                                else:
                                    st.warning("Not enough points for this reward.")

            with history_tab:
                col1, col2, col3 = st.columns([1, 3, 1])

                with col2:
                    with st.container(border=True):
                        st.markdown("### Reward History")

                        if len(reward_history) > 0:
                            for reward_item in reward_history:
                                with st.container(border=True):
                                    st.markdown(f"**Reward:** {reward_item['reward_name']}")
                                    st.markdown(f"**Points Used:** {reward_item['points_used']}")
                                    st.markdown(f"**Redeemed At:** {reward_item['redeemed_at']}")
                                    st.markdown(f"**Status:** {reward_item['status']}")

                        else:
                            st.info("No rewards redeemed yet.")

        # Feedback Form Page
        elif st.session_state["page"] == "feedback_form":
            st.title("Feedback Form")
            st.caption("Pick an appointment and submit feedback, complaints, or concerns about that visit.")

            st.divider()

            customer_appointments_for_feedback = []

            for appt in user_appts:
                if appt.get("status") != "Canceled":
                    customer_appointments_for_feedback.append(appt)

            col1, col2, col3 = st.columns([1, 3, 1])

            with col2:
                with st.container(border=True):
                    if len(customer_appointments_for_feedback) > 0:
                        selected_feedback_appt = st.selectbox(
                            "Choose Appointment for Feedback",
                            customer_appointments_for_feedback,
                            format_func=lambda x: f"{x['service']} | {x['date']} at {x['time']} | {x['employee']} | {x.get('status', 'Scheduled')}",
                            key="feedback_appointment_select"
                        )

                        st.markdown("### Appointment Selected")
                        st.markdown(f"**Service:** {selected_feedback_appt['service']}")
                        st.markdown(f"**Date:** {selected_feedback_appt['date']}")
                        st.markdown(f"**Time:** {selected_feedback_appt['time']}")
                        st.markdown(f"**Employee:** {selected_feedback_appt['employee']}")
                        st.markdown(f"**Status:** {selected_feedback_appt.get('status', 'Scheduled')}")

                        feedback_type = st.selectbox(
                            "Feedback Type",
                            ["General Feedback", "Complaint", "Service Issue", "Employee Compliment"],
                            key="feedback_type_select"
                        )

                        feedback_message = st.text_area(
                            "Write your feedback here",
                            key="feedback_message_input"
                        )

                        if st.button("Submit Feedback", key="submit_feedback_btn", type="primary", use_container_width=True):
                            if not feedback_message.strip():
                                st.error("Please write your feedback before submitting.")

                            else:
                                new_feedback = {
                                    "id": get_next_feedback_id(),
                                    "appointment_id": selected_feedback_appt["id"],
                                    "customer_name": st.session_state["user"]["full_name"],
                                    "customer_email": st.session_state["user"]["email"],
                                    "feedback_type": feedback_type,
                                    "message": feedback_message,
                                    "related_service": selected_feedback_appt["service"],
                                    "appointment_date": selected_feedback_appt["date"],
                                    "appointment_time": selected_feedback_appt["time"],
                                    "appointment_employee": selected_feedback_appt["employee"],
                                    "appointment_status": selected_feedback_appt.get("status", "Scheduled"),
                                    "status": "Pending",
                                    "submitted_at": str(datetime.now()),
                                    "reviewed_by": "",
                                    "reviewed_at": ""
                                }

                                feedback_list.append(new_feedback)
                                save_feedback()

                                st.success("Your feedback was submitted successfully.")
                                st.rerun()

                    else:
                        st.info("You do not have any appointments available for feedback yet.")

            st.divider()

            st.markdown("### My Submitted Feedback")

            user_feedback = []

            for feedback in feedback_list:
                if feedback.get("customer_email") == st.session_state["user"]["email"]:
                    user_feedback.append(feedback)

            if len(user_feedback) > 0:
                for feedback in user_feedback:
                    with st.container(border=True):
                        st.markdown(f"**Appointment:** {feedback.get('related_service', 'N/A')} | {feedback.get('appointment_date', 'N/A')} at {feedback.get('appointment_time', 'N/A')}")
                        st.markdown(f"**Employee:** {feedback.get('appointment_employee', 'N/A')}")
                        st.markdown(f"**Type:** {feedback['feedback_type']}")
                        st.markdown(f"**Message:** {feedback['message']}")
                        st.markdown(f"**Status:** {feedback['status']}")
                        st.caption(f"Submitted at: {feedback['submitted_at']}")
            else:
                st.info("You have not submitted any feedback yet.")

        # Penny Chat
        elif st.session_state["page"] == "penny_chat":
            show_penny_chat() 

    elif st.session_state["role"] == "Employee":
        employee_appts = get_employee_appointments()

        todays_appointments = 0
        scheduled_appointments = 0
        completed_appointments = 0

        for appt in employee_appts:
            if appt["date"] == str(date.today()) and appt.get("status") != "Canceled":
                todays_appointments += 1

            if appt.get("status") == "Scheduled":
                scheduled_appointments += 1

            if appt.get("status") == "Completed":
                completed_appointments += 1

        low_stock_count = get_low_stock_count()
        employee_total_charge = get_employee_total_charge_with_tips()

        pending_feedback_count = 0
        for feedback in feedback_list:
            if feedback.get("status") == "Pending":
                pending_feedback_count += 1

        # Penny Chat
        if st.session_state["page"] == "penny_chat":
            show_penny_chat()

        # Employee Dashboard
        elif st.session_state["page"] == "dashboard":
            st.title("Polished to Perfection")
            st.subheader("Employee Dashboard")

            st.divider()

            col1, col2, col3, col4, col5 = st.columns(5)

            with col1:
                with st.container(border=True):
                    st.success("Today's Appointments")
                    st.markdown(f"### {todays_appointments}")
                    st.caption("Scheduled today")

            with col2:
                with st.container(border=True):
                    st.info("Scheduled")
                    st.markdown(f"### {scheduled_appointments}")
                    st.caption("Upcoming")

            with col3:
                with st.container(border=True):
                    st.error("Completed")
                    st.markdown(f"### {completed_appointments}")
                    st.caption("Finished")

            with col4:
                with st.container(border=True):
                    st.warning("Low Stock")
                    st.markdown(f"### {low_stock_count}")
                    st.caption("Items to restock")

            with col5:
                with st.container(border=True):
                    st.success("Total Made")
                    st.markdown(f"### ${employee_total_charge}")
                    st.caption("Your services + tips")

            st.divider()

            col1, col2, col3 = st.columns([3, 2, 2])

            with col1:
                with st.container(border=True):
                    st.markdown("### Assigned Appointments")

                    active_employee_appts = []

                    for appt in employee_appts:
                        if appt.get("status") not in ["Completed", "Canceled"]:
                            active_employee_appts.append(appt)

                    if len(active_employee_appts) > 0:
                        for appt in active_employee_appts:
                            st.markdown(
                                f"**{appt['client']}** | {appt['service']} | {appt['date']} at {appt['time']} | {appt.get('status', 'Scheduled')}"
                            )

                    else:
                        st.info("No active appointments assigned yet.")

            with col2:
                with st.container(border=True):
                    st.markdown("### Inventory Alerts")

                    if low_stock_count > 0:
                        for item in inventory:
                            if item["quantity"] <= item["low_stock_limit"]:
                                st.warning(f"{item['item_name']} is low on stock")

                    else:
                        st.success("No low stock items right now.")

            with col3:
                with st.container(border=True):
                    st.markdown("### Feedback Alerts")
                    st.warning(f"Pending Feedback: {pending_feedback_count}")

                    if st.button("Review Feedback", key="dashboard_review_feedback_btn", type="primary", use_container_width=True):
                        st.session_state["page"] = "review_feedback"
                        st.rerun()

        # Manage Appointments
        elif st.session_state["page"] == "manage_appointments":
            st.title("Manage Appointments")
            st.caption("Search, review, and update appointment statuses.")

            st.divider()

            col1, col2 = st.columns([3, 2])

            with col1:
                with st.container(border=True):
                    search_name = st.text_input("Search by client name", key="appt_search_name")

                with st.container(border=True):
                    status_filter = st.selectbox(
                        "Status",
                        ["All", "Scheduled", "Completed", "Canceled"],
                        key="appointment_status_filter_box"
                    )

                st.session_state["appointment_status_filter"] = status_filter

                filtered_appts = []

                for appt in employee_appts:
                    matches_search = search_name.lower() in appt.get("client", "").lower()

                    matches_status = (
                        st.session_state["appointment_status_filter"] == "All"
                        or appt.get("status", "Scheduled") == st.session_state["appointment_status_filter"]
                    )

                    if matches_search and matches_status:
                        filtered_appts.append(appt)

                with st.container(border=True):
                    st.markdown("### Appointment List")

                    if len(filtered_appts) > 0:
                        appointment_table = []

                        for appt in filtered_appts:
                            appointment_table.append({
                                "Client": appt.get("client", "Unknown"),
                                "Service": appt["service"],
                                "Date": appt["date"],
                                "Time": appt["time"],
                                "Status": appt.get("status", "Scheduled"),
                                "Basic Charge": get_appointment_basic_charge(appt),
                                "20% Tip": get_appointment_tip(appt),
                                "Total Charge": get_appointment_total_charge(appt)
                            })

                        st.dataframe(appointment_table, use_container_width=True)

                        selected_appt_from_box = st.selectbox(
                            "Select Appointment",
                            filtered_appts,
                            format_func=lambda x: f"{x.get('client', 'Unknown')} | {x['service']} | {x['date']} {x['time']}",
                            key="manage_appt_selectbox"
                        )

                        if selected_appt_from_box:
                            st.session_state["selected_appointment_id"] = selected_appt_from_box["id"]

                    else:
                        st.info("No appointments assigned to you yet.")

            with col2:
                with st.container(border=True):
                    st.markdown("### Appointment Details")

                    selected_appt = None

                    for appt in employee_appts:
                        if appt["id"] == st.session_state["selected_appointment_id"]:
                            selected_appt = appt
                            break

                    if selected_appt:
                        st.markdown(f"**Client:** {selected_appt.get('client', 'Unknown')}")
                        st.markdown(f"**Client Email:** {selected_appt.get('client_email', 'N/A')}")
                        st.markdown(f"**Service:** {selected_appt['service']}")
                        st.markdown(f"**Basic Charge:** ${get_appointment_basic_charge(selected_appt)}")
                        st.markdown(f"**20% Tip:** ${get_appointment_tip(selected_appt)}")
                        st.markdown(f"**Total Charge:** ${get_appointment_total_charge(selected_appt)}")
                        st.markdown(f"**Date:** {selected_appt['date']}")
                        st.markdown(f"**Time:** {selected_appt['time']}")
                        st.markdown(f"**Status:** {selected_appt.get('status', 'Scheduled')}")

                        status_options = ["Scheduled", "Completed", "Canceled"]
                        current_status = selected_appt.get("status", "Scheduled")
                        current_status_index = status_options.index(current_status) if current_status in status_options else 0

                        selected_status = st.radio(
                            "Update Status",
                            status_options,
                            index=current_status_index,
                            key=f"status_radio_{selected_appt['id']}"
                        )

                        if st.button("Record Decision", key=f"save_status_{selected_appt['id']}", type="primary", use_container_width=True):
                            with st.spinner("Recording the decision..."):
                                for appt in appointments:
                                    if appt["id"] == selected_appt["id"]:
                                        old_status = appt.get("status", "Scheduled")

                                        if old_status != "Canceled" and selected_status == "Canceled":
                                            update_inventory_for_service(appt["service"], "add")
                                            appt["canceled_at"] = str(datetime.now())

                                        if old_status != "Completed" and selected_status == "Completed":
                                            add_reward_points_to_customer(appt["client_email"], 10)

                                        if "tip_amount" not in appt:
                                            appt["tip_amount"] = calculate_tip(appt.get("price", 0))

                                        if "total_charge" not in appt:
                                            appt["total_charge"] = calculate_total_charge(appt.get("price", 0))

                                        appt["status"] = selected_status
                                        break

                                save_appointments()
                                save_inventory()

                            st.success("Information recorded.")
                            st.rerun()

                    else:
                        st.info("Select an appointment to view details.")

        # Inventory Page
        elif st.session_state["page"] == "inventory":
            st.title("Salon Inventory")
            st.caption("View current stock and restock items.")

            st.divider()

            col1, col2 = st.columns([3, 2])

            with col1:
                with st.container(border=True):
                    inventory_table = []

                    for item in inventory:
                        inventory_table.append({
                            "Item": item["item_name"],
                            "Category": item["category"],
                            "Quantity": item["quantity"],
                            "Low Stock Limit": item["low_stock_limit"]
                        })

                    if len(inventory_table) > 0:
                        st.dataframe(inventory_table, use_container_width=True)

                        selected_inventory_item = st.selectbox(
                            "Select Inventory Item",
                            inventory,
                            format_func=lambda x: f"{x['item_name']} | Qty: {x['quantity']}",
                            key="inventory_selectbox"
                        )

                        if selected_inventory_item:
                            st.session_state["restock_item_id"] = selected_inventory_item["id"]

                    else:
                        st.info("No inventory items available.")

            with col2:
                with st.container(border=True):
                    st.markdown("### Restock Item")

                    selected_item = None

                    for item in inventory:
                        if item["id"] == st.session_state["restock_item_id"]:
                            selected_item = item
                            break

                    if selected_item:
                        st.markdown(f"**Item:** {selected_item['item_name']}")
                        st.markdown(f"**Current Quantity:** {selected_item['quantity']}")
                        st.markdown(f"**Supplier:** {selected_item['supplier']}")

                        restock_amount = st.number_input(
                            "Amount to Add",
                            min_value=1,
                            step=1,
                            key="restock_amount_input"
                        )

                        if st.button("Save Restock", key=f"save_restock_{selected_item['id']}", type="primary", use_container_width=True):
                            with st.spinner("Recording..."):
                                selected_item["quantity"] += restock_amount
                                save_inventory()

                            st.success("Inventory updated successfully.")
                            st.session_state["restock_item_id"] = None
                            st.rerun()

                    else:
                        st.info("Select an inventory item to restock.")

        # Low Stock Page
        elif st.session_state["page"] == "low_stock":
            st.title("Low Stock Alerts")
            st.caption("See which salon items need to be restocked soon.")

            st.divider()

            low_stock_items = []

            for item in inventory:
                if item["quantity"] <= item["low_stock_limit"]:
                    low_stock_items.append(item)

            if len(low_stock_items) > 0:
                for item in low_stock_items:
                    with st.container(border=True):
                        st.markdown(f"**Item:** {item['item_name']}")
                        st.markdown(f"**Quantity:** {item['quantity']}")
                        st.markdown(f"**Low Stock Limit:** {item['low_stock_limit']}")
                        st.markdown(f"**Supplier:** {item['supplier']}")
                        st.warning(f"{item['item_name']} needs to be restocked soon.")

            else:
                st.success("There are no low stock items right now.")

        # Revenue Tracker Page
        elif st.session_state["page"] == "revenue_tracker":
            st.title("Revenue Tracker")
            st.caption("Track basic service revenue, tips, and total revenue from completed appointments.")

            st.divider()

            completed_appts = get_completed_appointments()

            st.markdown("### Filters")

            employee_options = ["All Employees"] + sorted(list(set([appt.get("employee", "Unknown") for appt in completed_appts])))
            service_options = ["All Services"] + sorted(list(set([appt.get("service", "Unknown") for appt in completed_appts])))

            col1, col2, col3 = st.columns(3)

            with col1:
                employee_filter = st.selectbox(
                    "Employee",
                    employee_options,
                    key="revenue_employee_filter"
                )

            with col2:
                service_filter = st.selectbox(
                    "Service",
                    service_options,
                    key="revenue_service_filter"
                )

            with col3:
                date_filter = st.selectbox(
                    "Date Filter",
                    ["All Dates", "Today Only", "Past Dates Only"],
                    key="revenue_date_filter"
                )

            filtered_revenue_appts = []

            for appt in completed_appts:
                matches_employee = (
                    employee_filter == "All Employees"
                    or appt.get("employee", "Unknown") == employee_filter
                )

                matches_service = (
                    service_filter == "All Services"
                    or appt.get("service", "Unknown") == service_filter
                )

                matches_date = True

                if date_filter == "Today Only":
                    matches_date = appt.get("date") == str(date.today())

                elif date_filter == "Past Dates Only":
                    matches_date = appt.get("date") < str(date.today())

                if matches_employee and matches_service and matches_date:
                    filtered_revenue_appts.append(appt)

            basic_revenue = round(sum(get_appointment_basic_charge(appt) for appt in filtered_revenue_appts), 2)
            tip_revenue = round(sum(get_appointment_tip(appt) for appt in filtered_revenue_appts), 2)
            total_revenue = round(sum(get_appointment_total_charge(appt) for appt in filtered_revenue_appts), 2)

            st.divider()

            col1, col2, col3 = st.columns(3)

            with col1:
                with st.container(border=True):
                    st.info("Revenue from Basic Service")
                    st.markdown(f"## ${basic_revenue}")
                    st.caption("Service prices only")

            with col2:
                with st.container(border=True):
                    st.success("Revenue from Tips")
                    st.markdown(f"## ${tip_revenue}")
                    st.caption("20% tips")

            with col3:
                with st.container(border=True):
                    st.warning("Total Revenue")
                    st.markdown(f"## ${total_revenue}")
                    st.caption("Basic service revenue + tips")

            st.divider()

            st.markdown("### Completed Appointment Revenue")

            revenue_table = []

            for appt in filtered_revenue_appts:
                revenue_table.append({
                    "Client": appt.get("client", "Unknown"),
                    "Employee": appt.get("employee", "Unknown"),
                    "Service": appt.get("service", "Unknown"),
                    "Date": appt.get("date", ""),
                    "Time": appt.get("time", ""),
                    "Basic Service Revenue": get_appointment_basic_charge(appt),
                    "Tip Revenue": get_appointment_tip(appt),
                    "Total Revenue": get_appointment_total_charge(appt)
                })

            if len(revenue_table) > 0:
                st.dataframe(revenue_table, use_container_width=True)
            else:
                st.info("No completed appointment revenue found for these filters.")

        # Review Feedback Page
        elif st.session_state["page"] == "review_feedback":
            st.title("Review Feedback")
            st.caption("Review customer feedback and approve or reject submissions.")

            st.divider()

            feedback_status_filter = st.selectbox(
                "Filter by Status",
                ["All", "Pending", "Approved", "Rejected"],
                key="feedback_status_filter"
            )

            filtered_feedback = []

            for feedback in feedback_list:
                matches_status = (
                    feedback_status_filter == "All"
                    or feedback.get("status") == feedback_status_filter
                )

                if matches_status:
                    filtered_feedback.append(feedback)

            if len(filtered_feedback) > 0:
                for feedback in filtered_feedback:
                    with st.container(border=True):
                        st.markdown(f"### {feedback['feedback_type']}")
                        st.markdown(f"**Customer:** {feedback['customer_name']}")
                        st.markdown(f"**Email:** {feedback['customer_email']}")
                        st.markdown(f"**Appointment:** {feedback.get('related_service', 'N/A')} | {feedback.get('appointment_date', 'N/A')} at {feedback.get('appointment_time', 'N/A')}")
                        st.markdown(f"**Appointment Employee:** {feedback.get('appointment_employee', 'N/A')}")
                        st.markdown(f"**Message:** {feedback['message']}")
                        st.markdown(f"**Status:** {feedback['status']}")
                        st.caption(f"Submitted at: {feedback['submitted_at']}")

                        if feedback["status"] == "Pending":
                            col1, col2 = st.columns(2)

                            with col1:
                                if st.button(
                                    "Approve",
                                    key=f"approve_feedback_{feedback['id']}",
                                    type="primary",
                                    use_container_width=True
                                ):
                                    feedback["status"] = "Approved"
                                    feedback["reviewed_by"] = st.session_state["user"]["full_name"]
                                    feedback["reviewed_at"] = str(datetime.now())
                                    save_feedback()
                                    st.success("Feedback approved.")
                                    st.rerun()

                            with col2:
                                if st.button(
                                    "Reject",
                                    key=f"reject_feedback_{feedback['id']}",
                                    use_container_width=True
                                ):
                                    feedback["status"] = "Rejected"
                                    feedback["reviewed_by"] = st.session_state["user"]["full_name"]
                                    feedback["reviewed_at"] = str(datetime.now())
                                    save_feedback()
                                    st.warning("Feedback rejected.")
                                    st.rerun()

                        else:
                            st.info(
                                f"Reviewed by {feedback.get('reviewed_by', 'Unknown')} on {feedback.get('reviewed_at', '')}"
                            )

            else:
                st.info("No feedback found.")