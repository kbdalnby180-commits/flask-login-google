import os, json, time, requests, secrets
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_session import Session
from werkzeug.security import generate_password_hash, check_password_hash
from authlib.integrations.flask_client import OAuth
from urllib.parse import urljoin

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'change_this_secret')
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

USERS_FILE = 'users.json'
ONLINE_FILE = 'online.json'
ONLINE_TIMEOUT = 300

oauth = OAuth(app)
oauth.register(
    name='google',
    client_id=os.environ.get('GOOGLE_CLIENT_ID'),
    client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

def load_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except:
            return {}

def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_users():
    return load_json(USERS_FILE)
def save_users(users):
    save_json(USERS_FILE, users)

def mark_online(username):
    online = load_json(ONLINE_FILE)
    online[username] = int(time.time())
    save_json(ONLINE_FILE, online)
def mark_offline(username):
    online = load_json(ONLINE_FILE)
    if username in online:
        del online[username]
        save_json(ONLINE_FILE, online)
def clean_online():
    now = int(time.time())
    online = load_json(ONLINE_FILE)
    changed = False
    for u, ts in list(online.items()):
        if now - ts > ONLINE_TIMEOUT:
            del online[u]
            changed = True
    if changed:
        save_json(ONLINE_FILE, online)

@app.before_request
def before_request():
    if 'username' in session:
        mark_online(session['username'])
    clean_online()

@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('home'))
    return redirect(url_for('login'))

@app.route('/home')
def home():
    if 'username' not in session:
        return redirect(url_for('login'))
    username = session['username']
    users = load_users()
    profile = users.get(username, {}).get('avatar') or url_for('static', filename='default.png')
    return render_template('home.html', username=username, profile_url=profile)

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        uname = request.form['username'].strip()
        pwd = request.form['password']
        if not uname or not pwd:
            return render_template('register.html', error='أدخل اسم مستخدم وكلمة مرور')
        users = load_users()
        if uname in users:
            return render_template('register.html', error='اسم المستخدم موجود بالفعل')
        users[uname] = {'password_hash': generate_password_hash(pwd), 'avatar': None}
        save_users(users)
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        uname = request.form['username'].strip()
        pwd = request.form['password']
        users = load_users()
        if uname in users and check_password_hash(users[uname]['password_hash'], pwd):
            session['username'] = uname
            mark_online(uname)
            return redirect(url_for('home'))
        return render_template('login.html', error='اسم المستخدم أو كلمة المرور غير صحيحة')
    return render_template('login.html')

@app.route('/logout')
def logout():
    if 'username' in session:
        mark_offline(session['username'])
        session.pop('username', None)
    return redirect(url_for('login'))

# Google OAuth start
@app.route('/auth/google')
def google_login():
    redirect_uri = url_for('google_authorize', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

@app.route('/auth/google/callback')
def google_authorize():
    token = oauth.google.authorize_access_token()
    userinfo = oauth.google.parse_id_token(token)
    email = userinfo.get('email')
    name = userinfo.get('name') or email.split('@')[0]
    picture = userinfo.get('picture')

    users = load_users()
    base_name = ''.join(ch for ch in name if ch.isalnum())
    if not base_name:
        base_name = email.split('@')[0]
    uname = base_name
    i = 1
    while uname in users:
        uname = f"{base_name}{i}"
        i += 1
    random_pwd = secrets.token_urlsafe(12)
    users[uname] = {
        'email': email,
        'password_hash': generate_password_hash(random_pwd),
        'avatar': None
    }

    if picture:
        try:
            resp = requests.get(picture, timeout=5)
            if resp.status_code == 200:
                ext = 'jpg'
                fname = f"{uname}.{ext}"
                path = os.path.join(UPLOAD_FOLDER, fname)
                with open(path, 'wb') as f:
                    f.write(resp.content)
                users[uname]['avatar'] = urljoin('/static/uploads/', fname)
        except Exception as e:
            print('Could not download picture:', e)

    save_users(users)
    session['username'] = uname
    mark_online(uname)
    return redirect(url_for('profile'))

@app.route('/profile')
def profile():
    if 'username' not in session:
        return redirect(url_for('login'))
    username = session['username']
    users = load_users()
    user = users.get(username, {})
    avatar = user.get('avatar') or url_for('static', filename='default.png')
    return render_template('profile.html', username=username, profile_url=avatar)

@app.route('/upload-avatar', methods=['POST'])
def upload_avatar():
    if 'username' not in session:
        return redirect(url_for('login'))
    if 'avatar' not in request.files:
        return redirect(url_for('profile'))
    f = request.files['avatar']
    if f.filename == '':
        return redirect(url_for('profile'))
    ext = f.filename.rsplit('.', 1)[-1].lower()
    username = session['username']
    filename = f"{username}.{ext}"
    path = os.path.join(UPLOAD_FOLDER, filename)
    f.save(path)
    users = load_users()
    users[username]['avatar'] = urljoin('/static/uploads/', filename)
    save_users(users)
    return redirect(url_for('profile'))

@app.route('/api/online')
def api_online():
    clean_online()
    online = load_json(ONLINE_FILE)
    return jsonify(list(online.keys()))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)
