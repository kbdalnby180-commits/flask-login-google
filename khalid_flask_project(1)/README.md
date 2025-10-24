# Khalid Flask Project (Google OAuth + Auth)

**Features**
- Register/login with username & password (passwords stored hashed)
- Login with Google (OAuth): when signing in with Google the app:
  - creates a user if not exists
  - generates a random password (stored hashed)
  - uses Google name as username (if available) — makes unique by appending number if taken
  - downloads Google profile picture and saves it in static/uploads/
- Session-based login
- `api/online` endpoint shows currently active users (based on last activity)
- Profile page where user can upload/change their profile picture

**Environment variables (set in Render/Railway or locally)**
- `SECRET_KEY` - Flask secret key
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `OAUTHLIB_INSECURE_TRANSPORT=1` (only for local development without HTTPS)

**Run locally**
```bash
pip install -r requirements.txt
export FLASK_APP=app.py
export FLASK_ENV=development
export OAUTHLIB_INSECURE_TRANSPORT=1
export GOOGLE_CLIENT_ID=your-client-id
export GOOGLE_CLIENT_SECRET=your-client-secret
export SECRET_KEY=change_this_secret
flask run
```

**Notes**
- This project uses `users.json` and `online.json` for simplicity. For production use a database.
- Keep secrets out of the repo; set them as environment variables.
