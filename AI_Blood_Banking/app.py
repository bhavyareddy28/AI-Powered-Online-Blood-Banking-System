from flask import Flask, render_template, request, redirect, session
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash

from ml.donor_matching import rank_donors
from ml.demand_prediction import predict_demand
from ml.notifications import create_notification_message


app = Flask(__name__)

# Secret key for login sessions
app.secret_key = "ai_blood_banking_secret_key"


# -----------------------------
# MySQL Database Connection
# -----------------------------
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Bhavya@28",
        database="blood_bank"
    )


# -----------------------------
# Admin Access Protection
# -----------------------------
def is_admin():

    # User must be logged in
    if "user_id" not in session:
        return False

    db = None
    cursor = None

    try:
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        cursor.execute("""
            SELECT role
            FROM users
            WHERE id = %s
            LIMIT 1
        """, (session.get("user_id"),))

        user = cursor.fetchone()

        if user and user["role"] == "admin":
            return True

        return False

    except Exception as e:
        print("Admin access verification error:", e)
        return False

    finally:
        if cursor:
            cursor.close()

        if db:
            db.close()


# -----------------------------
# User Login Protection
# -----------------------------
def is_logged_in():
    return "user_id" in session


# -----------------------------
# Home Page
# -----------------------------
@app.route("/")
def home():
    return render_template("index.html")


# -----------------------------
# Login
# -----------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    error = ""

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        db = None
        cursor = None
        user = None
        login_successful = False

        try:
            db = get_db_connection()
            cursor = db.cursor(dictionary=True)

            # Fetch the stored password so it can be verified securely.
            cursor.execute("""
                SELECT id, name, email, role, password
                FROM users
                WHERE email = %s
                LIMIT 1
            """, (email,))

            user = cursor.fetchone()

            if user:
                stored_password = user["password"] or ""

                # Werkzeug hashes normally begin with "scrypt:" or "pbkdf2:".
                # Support both hashed accounts and old plaintext accounts.
                if stored_password.startswith(("scrypt:", "pbkdf2:")):
                    login_successful = check_password_hash(
                        stored_password, password
                    )
                elif stored_password == password:
                    # Successful legacy login: upgrade plaintext to a hash.
                    new_hash = generate_password_hash(password)
                    cursor.execute("""
                        UPDATE users
                        SET password = %s
                        WHERE id = %s
                    """, (new_hash, user["id"]))
                    db.commit()
                    login_successful = True

        except Exception as e:
            if db:
                try:
                    db.rollback()
                except Exception:
                    pass
            print("Login error:", e)
            error = "Unable to log in right now. Please try again."

        finally:
            if cursor:
                cursor.close()
            if db:
                db.close()

        if login_successful and user:
            # Clear any old session data before creating a fresh login session.
            session.clear()
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["user_email"] = user["email"]
            session["user_role"] = user["role"]

            if user["role"] == "admin":
                return redirect("/admin/dashboard")
            return redirect("/user/dashboard")

        if not error:
            error = "Invalid email or password."

    return render_template("login.html", error=error)

# -----------------------------
# Logout
# -----------------------------
@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")


# -----------------------------
# User Dashboard
# -----------------------------
@app.route("/user/dashboard")
def user_dashboard():

    if not is_logged_in():
        return redirect("/login")

    user_email = session.get("user_email")

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    # Get donor information
    cursor.execute("""
        SELECT
            name,
            age,
            gender,
            blood_group,
            phone,
            email,
            city,
            available,
            last_donation_date
        FROM donors
        WHERE email = %s
        LIMIT 1
    """, (user_email,))

    donor = cursor.fetchone()

    # Get notifications for logged-in user
    cursor.execute("""
        SELECT
            id,
            donor_name,
            blood_group,
            city,
            message,
            status,
            created_at
        FROM notifications
        WHERE donor_email = %s
        ORDER BY created_at DESC
    """, (user_email,))

    user_notifications = cursor.fetchall()

    # Get blood requests submitted using the user's email/phone
    user_requests = []

    if donor:

        cursor.execute("""
            SELECT
                id,
                patient_name,
                blood_group,
                units_required,
                hospital_name,
                city,
                phone,
                request_date,
                status
            FROM blood_requests
            WHERE phone = %s
            ORDER BY request_date DESC
        """, (donor["phone"],))

        user_requests = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "user_dashboard.html",
        donor=donor,
        notifications=user_notifications,
        requests=user_requests
    )


# -----------------------------
# Donor Registration
# -----------------------------
@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"].strip()
        age = request.form["age"]
        gender = request.form["gender"]
        blood_group = request.form["blood_group"].strip().upper()
        phone = request.form["phone"].strip()
        email = request.form["email"].strip()
        city = request.form["city"].strip()

        # New donor availability fields
        available = request.form["available"]
        last_donation_date = request.form.get("last_donation_date") or None

        db = get_db_connection()
        cursor = db.cursor()

        query = """
        INSERT INTO donors
        (
            name,
            age,
            gender,
            blood_group,
            phone,
            email,
            city,
            available,
            last_donation_date
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        values = (
            name,
            age,
            gender,
            blood_group,
            phone,
            email,
            city,
            available,
            last_donation_date
        )

        cursor.execute(query, values)
        db.commit()

        cursor.close()
        db.close()

        return redirect("/")

    return render_template("register.html")


# -----------------------------
# Blood Request
# -----------------------------
@app.route("/request-blood", methods=["GET", "POST"])
def request_blood():

    if request.method == "POST":

        patient_name = request.form["patient_name"].strip()
        blood_group = request.form["blood_group"].strip().upper()
        units_required = int(request.form["units_required"])
        hospital_name = request.form["hospital_name"].strip()
        city = request.form["city"].strip()
        phone = request.form["phone"].strip()

        db = get_db_connection()
        cursor = db.cursor()

        try:

            # ---------------------------------
            # STEP 1: Save the blood request
            # ---------------------------------
            request_query = """
            INSERT INTO blood_requests
            (
                patient_name,
                blood_group,
                units_required,
                hospital_name,
                city,
                phone
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            """

            request_values = (
                patient_name,
                blood_group,
                units_required,
                hospital_name,
                city,
                phone
            )

            cursor.execute(request_query, request_values)

            # Commit the request immediately.
            # This prevents a notification error from
            # deleting the blood request.
            db.commit()

            # ---------------------------------
            # STEP 2: Find matching donors
            # ---------------------------------
            donor_query = """
            SELECT
                name,
                email,
                blood_group,
                city
            FROM donors
            WHERE UPPER(TRIM(blood_group)) = UPPER(TRIM(%s))
            AND LOWER(TRIM(city)) = LOWER(TRIM(%s))
            AND available = TRUE
            """

            cursor.execute(
                donor_query,
                (blood_group, city)
            )

            matching_donors = cursor.fetchall()

            # ---------------------------------
            # STEP 3: Create notifications
            # ---------------------------------
            notification_query = """
            INSERT INTO notifications
            (
                donor_email,
                donor_name,
                blood_group,
                city,
                message
            )
            VALUES (%s, %s, %s, %s, %s)
            """

            for donor in matching_donors:

                donor_name = donor[0]
                donor_email = donor[1]
                donor_blood_group = donor[2]
                donor_city = donor[3]

                message = create_notification_message(
                    donor_name,
                    donor_blood_group,
                    donor_city
                )

                cursor.execute(
                    notification_query,
                    (
                        donor_email,
                        donor_name,
                        donor_blood_group,
                        donor_city,
                        message
                    )
                )

            # Commit notifications separately.
            db.commit()

            print("Blood request submitted successfully.")

        except Exception as e:

            # Roll back only the current unfinished transaction.
            db.rollback()

            print(
                "Error while processing blood request:",
                e
            )

        finally:

            cursor.close()
            db.close()

        # Return to the user dashboard after submission.
        return redirect("/user/dashboard")

    return render_template("blood_request.html")


# -----------------------------
# Smart Donor Matching
# -----------------------------
@app.route("/matches", methods=["GET", "POST"])
def matches():

    matched_donors = []

    if request.method == "POST":

        blood_group = request.form["blood_group"].strip().upper()
        city = request.form["city"].strip()

        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        query = """
        SELECT
            name,
            age,
            gender,
            blood_group,
            phone,
            email,
            city,
            available,
            last_donation_date
        FROM donors
        """

        cursor.execute(query)

        donors = cursor.fetchall()

        cursor.close()
        db.close()

        # Rank donors using smart matching
        matched_donors = rank_donors(
            donors,
            blood_group,
            city
        )

    return render_template(
        "matches.html",
        donors=matched_donors
    )


# -----------------------------
# Blood Demand Prediction
# -----------------------------
@app.route("/demand-prediction", methods=["GET", "POST"])
def demand_prediction():

    prediction = None
    selected_blood_group = ""
    selected_date = ""

    if request.method == "POST":

        selected_blood_group = request.form[
            "blood_group"
        ].strip().upper()

        selected_date = request.form[
            "prediction_date"
        ]

        prediction = predict_demand(
            selected_blood_group,
            selected_date
        )

    return render_template(
        "demand_prediction.html",
        prediction=prediction,
        selected_blood_group=selected_blood_group,
        selected_date=selected_date
    )


# -----------------------------
# Notifications
# -----------------------------
@app.route("/notifications")
def notifications():

    if not is_logged_in():
        return redirect("/login")

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    # Normal users see their own notifications
    if session.get("user_role") == "user":

        query = """
        SELECT
            id,
            donor_name,
            donor_email,
            blood_group,
            city,
            message,
            status,
            created_at
        FROM notifications
        WHERE donor_email = %s
        ORDER BY created_at DESC
        """

        cursor.execute(
            query,
            (session.get("user_email"),)
        )

    # Admin can see all notifications
    else:

        query = """
        SELECT
            id,
            donor_name,
            donor_email,
            blood_group,
            city,
            message,
            status,
            created_at
        FROM notifications
        ORDER BY created_at DESC
        """

        cursor.execute(query)

    notification_data = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "notifications.html",
        notifications=notification_data
    )


# -----------------------------
# Admin Dashboard
# -----------------------------
@app.route("/admin/dashboard")
def admin_dashboard():

    if not is_admin():
        return redirect("/login")

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    # Total donors
    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM donors
    """)

    total_donors = cursor.fetchone()["total"]

    # Total blood requests
    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM blood_requests
    """)

    total_requests = cursor.fetchone()["total"]

    # Total notifications
    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM notifications
    """)

    total_notifications = cursor.fetchone()["total"]

    # Total available blood units
    cursor.execute("""
        SELECT COALESCE(SUM(units_available), 0) AS total
        FROM blood_inventory
    """)

    total_units = cursor.fetchone()["total"]

    # Blood inventory
    cursor.execute("""
        SELECT
            blood_group,
            units_available
        FROM blood_inventory
        ORDER BY
            CASE blood_group
                WHEN 'A+' THEN 1
                WHEN 'A-' THEN 2
                WHEN 'B+' THEN 3
                WHEN 'B-' THEN 4
                WHEN 'AB+' THEN 5
                WHEN 'AB-' THEN 6
                WHEN 'O+' THEN 7
                WHEN 'O-' THEN 8
            END
    """)

    inventory_data = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "admin_dashboard.html",
        total_donors=total_donors,
        total_requests=total_requests,
        total_notifications=total_notifications,
        total_units=total_units,
        inventory=inventory_data
    )

# ADD THE NEW ROUTE HERE
@app.route("/admin/requests")
def admin_requests():

    if not is_admin():
        return redirect("/login")

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            id,
            patient_name,
            blood_group,
            units_required,
            hospital_name,
            city,
            phone,
            request_date,
            status
        FROM blood_requests
        ORDER BY request_date DESC
    """)

    requests = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "admin_requests.html",
        requests=requests
    )
# -----------------------------
# Approve / Reject Blood Request
# -----------------------------
@app.route("/admin/request/<int:request_id>/<action>", methods=["POST"])
def update_blood_request(request_id, action):

    if not is_admin():
        return redirect("/login")

    if action not in ["approve", "reject"]:
        return redirect("/admin/requests")

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:

        # Get the blood request
        cursor.execute("""
            SELECT
                id,
                blood_group,
                units_required,
                status
            FROM blood_requests
            WHERE id = %s
        """, (request_id,))

        blood_request = cursor.fetchone()

        if not blood_request:
            return redirect("/admin/requests")

        # Only pending requests can be updated
        if blood_request["status"] != "Pending":
            return redirect("/admin/requests")

        # -------------------------
        # REJECT REQUEST
        # -------------------------

        if action == "reject":

            cursor.execute("""
                UPDATE blood_requests
                SET status = 'Rejected'
                WHERE id = %s
            """, (request_id,))

            db.commit()

            return redirect("/admin/requests")

        # -------------------------
        # APPROVE REQUEST
        # -------------------------

        blood_group = blood_request["blood_group"]
        units_required = blood_request["units_required"]

        # Get current inventory
        cursor.execute("""
            SELECT units_available
            FROM blood_inventory
            WHERE blood_group = %s
            FOR UPDATE
        """, (blood_group,))

        inventory = cursor.fetchone()

        # Blood group not found in inventory
        if not inventory:
            db.rollback()
            return redirect("/admin/requests")

        available_units = inventory["units_available"]

        # Not enough blood
        if available_units < units_required:
            db.rollback()
            return redirect("/admin/requests")

        # Reduce inventory
        cursor.execute("""
            UPDATE blood_inventory
            SET units_available = units_available - %s
            WHERE blood_group = %s
        """, (units_required, blood_group))

        # Update request status
        cursor.execute("""
            UPDATE blood_requests
            SET status = 'Approved'
            WHERE id = %s
        """, (request_id,))

        db.commit()

    except Exception as e:

        db.rollback()
        print("Error updating blood request:", e)

    finally:

        cursor.close()
        db.close()

    return redirect("/admin/requests")
# -----------------------------
# Blood Inventory
# -----------------------------
@app.route("/inventory")
def inventory():

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    query = """
    SELECT
        blood_group,
        units_available,
        last_updated
    FROM blood_inventory
    ORDER BY
        CASE blood_group
            WHEN 'A+' THEN 1
            WHEN 'A-' THEN 2
            WHEN 'B+' THEN 3
            WHEN 'B-' THEN 4
            WHEN 'AB+' THEN 5
            WHEN 'AB-' THEN 6
            WHEN 'O+' THEN 7
            WHEN 'O-' THEN 8
        END
    """

    cursor.execute(query)

    inventory_data = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "inventory.html",
        inventory=inventory_data
    )


# -----------------------------
# Admin - Update Blood Inventory
# -----------------------------
@app.route("/admin/inventory", methods=["GET", "POST"])
def admin_inventory():

    if not is_admin():
        return redirect("/login")

    message = ""

    if request.method == "POST":

        blood_group = request.form[
            "blood_group"
        ].strip().upper()

        units_available = int(
            request.form["units_available"]
        )

        db = get_db_connection()
        cursor = db.cursor()

        query = """
        UPDATE blood_inventory
        SET units_available = %s
        WHERE blood_group = %s
        """

        cursor.execute(
            query,
            (
                units_available,
                blood_group
            )
        )

        db.commit()

        cursor.close()
        db.close()

        message = "Inventory updated successfully!"

    # Get current inventory
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            blood_group,
            units_available
        FROM blood_inventory
        ORDER BY
            CASE blood_group
                WHEN 'A+' THEN 1
                WHEN 'A-' THEN 2
                WHEN 'B+' THEN 3
                WHEN 'B-' THEN 4
                WHEN 'AB+' THEN 5
                WHEN 'AB-' THEN 6
                WHEN 'O+' THEN 7
                WHEN 'O-' THEN 8
            END
    """)

    inventory_data = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "admin_inventory.html",
        inventory=inventory_data,
        message=message
    )



# -----------------------------
# Run Application
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)
