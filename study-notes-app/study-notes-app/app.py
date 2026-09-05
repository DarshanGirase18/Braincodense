import os
import uuid
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, send_from_directory, abort
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

import db
from extractor import process_pdf
from pdf_generator import build_notes_pdf

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR   = os.path.join(BASE_DIR, "uploads")
GENERATED_DIR = os.path.join(BASE_DIR, "generated")
AVATAR_DIR    = os.path.join(BASE_DIR, "static", "avatars")
os.makedirs(UPLOAD_DIR,    exist_ok=True)
os.makedirs(GENERATED_DIR, exist_ok=True)
os.makedirs(AVATAR_DIR,    exist_ok=True)

ALLOWED_IMAGE_EXT = {"png", "jpg", "jpeg", "gif", "webp"}

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # 20 MB upload limit

db.init_db()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "error")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def get_current_user():
    """Fetch the logged-in user row (or None)."""
    if "user_id" not in session:
        return None
    conn = db.get_conn()
    user = conn.execute(
        "SELECT * FROM users WHERE id = ?", (session["user_id"],)
    ).fetchone()
    conn.close()
    return user


def avatar_url_for(user):
    """Return the URL for a user's avatar, or None if not set."""
    if user and user["avatar_filename"]:
        return url_for("static", filename=f"avatars/{user['avatar_filename']}")
    return None


@app.context_processor
def inject_avatar():
    """Make g_avatar_url available in every template automatically."""
    user = get_current_user()
    return {"g_avatar_url": avatar_url_for(user)}


@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not username or not email or not password:
            flash("All fields are required.", "error")
            return redirect(url_for("register"))
        if len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
            return redirect(url_for("register"))

        conn = db.get_conn()
        existing = conn.execute(
            "SELECT id FROM users WHERE username = ? OR email = ?", (username, email)
        ).fetchone()
        if existing:
            conn.close()
            flash("Username or email already taken.", "error")
            return redirect(url_for("register"))

        conn.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
            (username, email, generate_password_hash(password)),
        )
        conn.commit()
        conn.close()
        flash("Account created! Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        identifier = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        conn = db.get_conn()
        user = conn.execute(
            "SELECT * FROM users WHERE username = ? OR email = ?", (identifier, identifier.lower())
        ).fetchone()
        conn.close()

        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect(url_for("dashboard"))

        flash("Invalid username/email or password.", "error")
        return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out.", "success")
    return redirect(url_for("index"))


@app.route("/dashboard")
@login_required
def dashboard():
    user = get_current_user()
    conn = db.get_conn()
    notes = conn.execute(
        "SELECT * FROM notes WHERE user_id = ? ORDER BY created_at DESC",
        (session["user_id"],),
    ).fetchall()
    conn.close()
    return render_template(
        "dashboard.html",
        notes=notes,
        username=session.get("username"),
        user=user,
        avatar_url=avatar_url_for(user),
    )


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user = get_current_user()

    if request.method == "POST":
        # ── Update display name / email ───────────────────────────
        new_username = request.form.get("username", "").strip()
        new_email    = request.form.get("email", "").strip().lower()

        # ── Remove avatar ──────────────────────────────────────────
        if request.form.get("remove_avatar"):
            if user["avatar_filename"]:
                old_path = os.path.join(AVATAR_DIR, user["avatar_filename"])
                if os.path.exists(old_path):
                    os.remove(old_path)
            conn = db.get_conn()
            conn.execute(
                "UPDATE users SET avatar_filename = NULL WHERE id = ?",
                (session["user_id"],),
            )
            conn.commit()
            conn.close()
            flash("Display picture removed.", "success")
            return redirect(url_for("profile"))

        # ── Avatar upload ─────────────────────────────────────────
        avatar_file = request.files.get("avatar")
        new_avatar_filename = user["avatar_filename"]  # keep existing by default

        if avatar_file and avatar_file.filename:
            ext = avatar_file.filename.rsplit(".", 1)[-1].lower()
            if ext not in ALLOWED_IMAGE_EXT:
                flash("Only PNG, JPG, GIF, or WEBP images are allowed.", "error")
                return redirect(url_for("profile"))

            # Delete old avatar file if it exists
            if user["avatar_filename"]:
                old_path = os.path.join(AVATAR_DIR, user["avatar_filename"])
                if os.path.exists(old_path):
                    os.remove(old_path)

            new_avatar_filename = f"{uuid.uuid4().hex}.{ext}"
            avatar_file.save(os.path.join(AVATAR_DIR, new_avatar_filename))

        # Validate new username/email uniqueness
        if new_username and new_email:
            conn = db.get_conn()
            clash = conn.execute(
                "SELECT id FROM users WHERE (username = ? OR email = ?) AND id != ?",
                (new_username, new_email, session["user_id"]),
            ).fetchone()
            if clash:
                conn.close()
                flash("That username or email is already taken.", "error")
                return redirect(url_for("profile"))

            conn.execute(
                "UPDATE users SET username = ?, email = ?, avatar_filename = ? WHERE id = ?",
                (new_username, new_email, new_avatar_filename, session["user_id"]),
            )
            conn.commit()
            conn.close()
            session["username"] = new_username  # keep session in sync
            flash("Profile updated successfully.", "success")
        else:
            # Only avatar changed
            conn = db.get_conn()
            conn.execute(
                "UPDATE users SET avatar_filename = ? WHERE id = ?",
                (new_avatar_filename, session["user_id"]),
            )
            conn.commit()
            conn.close()
            flash("Avatar updated.", "success")

        return redirect(url_for("profile"))

    # GET
    return render_template(
        "profile.html",
        user=user,
        avatar_url=avatar_url_for(user),
    )


@app.route("/upload", methods=["POST"])
@login_required
def upload():
    file = request.files.get("pdf_file")
    if not file or file.filename == "":
        flash("Please choose a PDF file to upload.", "error")
        return redirect(url_for("dashboard"))
    if not file.filename.lower().endswith(".pdf"):
        flash("Only PDF files are supported.", "error")
        return redirect(url_for("dashboard"))

    original_name = secure_filename(file.filename)
    unique_id = uuid.uuid4().hex[:10]
    saved_upload_path = os.path.join(UPLOAD_DIR, f"{unique_id}_{original_name}")
    file.save(saved_upload_path)

    try:
        data = process_pdf(saved_upload_path)
        generated_filename = f"smart_notes_{unique_id}.pdf"
        generated_path = os.path.join(GENERATED_DIR, generated_filename)
        build_notes_pdf(generated_path, original_name, data)
    except Exception as exc:  # keep it running even if one PDF misbehaves
        flash(f"Could not process that PDF: {exc}", "error")
        return redirect(url_for("dashboard"))
    finally:
        if os.path.exists(saved_upload_path):
            os.remove(saved_upload_path)

    conn = db.get_conn()
    conn.execute(
        """INSERT INTO notes (user_id, original_filename, generated_filename,
                               topic_count, page_count, topics_preview)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            session["user_id"], original_name, generated_filename,
            len(data["important_topics"]), data["page_count"],
            ", ".join(data["important_topics"][:6]),
        ),
    )
    conn.commit()
    conn.close()

    flash("Your smart notes are ready!", "success")
    return redirect(url_for("dashboard"))


@app.route("/download/<int:note_id>")
@login_required
def download(note_id):
    conn = db.get_conn()
    note = conn.execute(
        "SELECT * FROM notes WHERE id = ? AND user_id = ?", (note_id, session["user_id"])
    ).fetchone()
    conn.close()
    if not note:
        abort(404)
    return send_from_directory(
        GENERATED_DIR, note["generated_filename"],
        as_attachment=True,
        download_name=f"smart_notes_{note['original_filename']}",
    )


@app.route("/delete/<int:note_id>", methods=["POST"])
@login_required
def delete(note_id):
    conn = db.get_conn()
    note = conn.execute(
        "SELECT * FROM notes WHERE id = ? AND user_id = ?", (note_id, session["user_id"])
    ).fetchone()
    if note:
        gen_path = os.path.join(GENERATED_DIR, note["generated_filename"])
        if os.path.exists(gen_path):
            os.remove(gen_path)
        conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        conn.commit()
    conn.close()
    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
