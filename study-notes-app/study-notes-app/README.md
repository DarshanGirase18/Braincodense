# ⚡ BrainCondense

> **Study Less. Understand More.**

BrainCondense is a Flask web app that transforms lengthy lecture PDFs into clean, concise **Smart Notes** — using heading & keyword extraction. No AI API key required.

**Developed & Designed by Darshan Girase**

---

## ✨ Features

- 📄 **PDF Upload** — Upload any lecture PDF (up to 20 MB)
- ✨ **Smart Notes** — Automatic topic, heading & keyword extraction
- 📥 **Download** — Get a clean, condensed PDF ready for revision
- 👤 **User Profiles** — Upload a display picture, edit username & email
- 📚 **Notes History** — All your generated notes in one place
- 🔐 **Auth** — Register, login, and secure sessions

---

## 🚀 Local Setup

### 1. Clone the repo
```bash
git clone https://github.com/YOUR_USERNAME/braincondense.git
cd braincondense
```

### 2. Create a virtual environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Set environment variables
```bash
# Copy the example file
cp .env.example .env
# Then edit .env and set a real SECRET_KEY
```

### 5. Run the dev server
```bash
python app.py
```

Visit **http://127.0.0.1:5000** 🎉

---

## ☁️ Deploy to Render (Free)

1. Push your code to GitHub
2. Go to [render.com](https://render.com) → **New → Web Service**
3. Connect your GitHub repo
4. Set these values:

| Setting | Value |
|---|---|
| **Environment** | Python 3 |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `gunicorn app:app` |

5. Add an **Environment Variable**:
   - `SECRET_KEY` → a long random string

   Generate one with:
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

6. Click **Deploy** ✅

> **⚠️ Note:** Render's free tier has an **ephemeral disk** — uploaded PDFs and the SQLite database reset on each deploy. For persistent storage, upgrade to a paid plan or use an external PostgreSQL database.

---

## 📁 Project Structure

```
braincondense/
├── app.py              # Flask routes & app config
├── db.py               # SQLite database setup & migration
├── extractor.py        # PDF heading & keyword extractor
├── pdf_generator.py    # Smart Notes PDF builder
├── requirements.txt    # Python dependencies
├── Procfile            # For Render / Heroku deployment
├── runtime.txt         # Python version pin
├── .env.example        # Environment variable template
├── static/
│   ├── style.css       # Full design system (Ocean Blue theme)
│   └── avatars/        # User profile pictures
├── templates/
│   ├── base.html       # Navbar + footer layout
│   ├── index.html      # Landing page + welcome modal
│   ├── dashboard.html  # Upload + notes history
│   ├── profile.html    # Profile & avatar settings
│   ├── login.html      # Sign in
│   └── register.html   # Request access / Sign up
├── uploads/            # Temp PDF uploads (gitignored)
└── generated/          # Generated Smart Note PDFs (gitignored)
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python + Flask |
| Database | SQLite (`sqlite3`) |
| PDF Extraction | `pdfplumber` + `pdfminer.six` |
| PDF Generation | `reportlab` |
| Frontend | Vanilla HTML + CSS |
| Fonts | Google Fonts — Playfair Display + Inter |
| Production Server | Gunicorn |

---

## 🔒 Security Notes

- Passwords hashed with `werkzeug.security` (PBKDF2-SHA256)
- Sessions signed with `SECRET_KEY` — **always set a strong key in production**
- File uploads validated by extension + `MAX_CONTENT_LENGTH`
- All DB queries scoped by `user_id`

---

## 📄 License

MIT — free to use, modify, and distribute.

---

*Built for students, one PDF at a time.*
**— Darshan Girase**
