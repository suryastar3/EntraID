from flask import Flask, redirect, url_for, session, render_template
import msal
import mysql.connector
from flask_session import Session

app = Flask(__name__)
app.secret_key = "supersecretkey"
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

# Microsoft Entra ID Config
CLIENT_ID = "1b9ef77e-4bf8-4347-b41c-8d4cc41fdfb2"
CLIENT_SECRET = "lYP8Q~XME-bbUgDYNmZDb3Rnz5H97O4th1WacaEc"
TENANT_ID = "e150b6c8-44ed-4831-b9e4-66b7754b057a"
AUTHORITY = f"https://login.microsoftonline.com/e150b6c8-44ed-4831-b9e4-66b7754b057a"
REDIRECT_URI = "http://127.0.0.1:5000/auth/callback"
SCOPE = ["User.Read"]

# Database Configuration
db = mysql.connector.connect(host="127.0.0.1", user="root", password="", database="mywebapp_db")
cursor = db.cursor(dictionary=True)

# Microsoft Authentication
def get_msal_app():
    return msal.PublicClientApplication(CLIENT_ID, authority=AUTHORITY)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login")
def login():
    msal_app = msal.ConfidentialClientApplication(CLIENT_ID, CLIENT_SECRET, authority=AUTHORITY)
    auth_url = msal_app.get_authorization_request_url(SCOPE, redirect_uri=REDIRECT_URI)
    return redirect(auth_url)

@app.route("/auth/callback")
def auth_callback():
    if "code" in session:
        return redirect(url_for("dashboard"))

    msal_app = msal.ConfidentialClientApplication(CLIENT_ID, CLIENT_SECRET, authority=AUTHORITY)
    auth_response = msal_app.acquire_token_by_authorization_code(
        request.args["code"], scopes=SCOPE, redirect_uri=REDIRECT_URI
    )

    if "id_token_claims" in auth_response:
        user_data = auth_response["id_token_claims"]
        session["user"] = {"name": user_data["name"], "email": user_data["preferred_username"]}

        # Check user role in database
        cursor.execute("SELECT role FROM users WHERE email = %s", (user_data["preferred_username"],))
        user = cursor.fetchone()

        if not user:
            cursor.execute("INSERT INTO users (name, email, role) VALUES (%s, %s, 'pending')",
                           (user_data["name"], user_data["preferred_username"]))
            db.commit()
            session["role"] = "pending"
        else:
            session["role"] = user["role"]

        return redirect(url_for("dashboard"))

    return "Login failed", 401

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("login"))

    role = session.get("role", "pending")
    return render_template("dashboard.html", user=session["user"], role=role)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)