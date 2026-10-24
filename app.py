# language: Python, file: app.py
import os
import psycopg2
from psycopg2.extras import DictCursor
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "winston_client_secret_key_2024"

# Получаем URL базы из переменных окружения (Render сам его подставит)
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db():
    # Подключаемся к PostgreSQL
    conn = psycopg2.connect(DATABASE_URL)
    return conn

def init_db():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    password VARCHAR(255) NOT NULL,
                    nickname VARCHAR(255) DEFAULT '',
                    avatar_icon VARCHAR(10) DEFAULT '🍕',
                    has_access INTEGER DEFAULT 0
                )
            ''')
        conn.commit()

PLANS = [
    {"name": "30 Days", "price": 200, "period": "30 дней"},
    {"name": "360 Days", "price": 700, "period": "365 дней"},
    {"name": "Lifetime", "price": 1000, "period": "бессрочно"}
]

@app.route('/')
def index():
    user = None
    if 'user_id' in session:
        conn = get_db()
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute('SELECT * FROM users WHERE id = %s', (session['user_id'],))
            user = cur.fetchone()
        conn.close()
    return render_template('index.html', plans=PLANS, user=user)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password']
        
        if not email or not password:
            flash('Заполните все поля.', 'error')
            return redirect(url_for('register'))
        
        conn = get_db()
        try:
            with conn.cursor() as cur:
                hashed = generate_password_hash(password)
                cur.execute('INSERT INTO users (email, password) VALUES (%s, %s)', (email, hashed))
            conn.commit()
            flash('Регистрация успешна! Войдите.', 'success')
            return redirect(url_for('login'))
        except psycopg2.IntegrityError:
            conn.rollback()
            flash('Этот email уже зарегистрирован.', 'error')
            return redirect(url_for('register'))
        finally:
            conn.close()
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password']
        
        conn = get_db()
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute('SELECT * FROM users WHERE email = %s', (email,))
            user = cur.fetchone()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            flash('Добро пожаловать!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Неверный email или пароль.', 'error')
            return redirect(url_for('login'))
    
    return render_template('login.html')

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db()
    
    if request.method == 'POST':
        nickname = request.form.get('nickname', '').strip()
        avatar_icon = request.form.get('avatar_icon', '🍕')
        
        with conn.cursor() as cur:
            cur.execute('UPDATE users SET nickname = %s, avatar_icon = %s WHERE id = %s', 
                        (nickname, avatar_icon, session['user_id']))
        conn.commit()
        flash('Профиль обновлён!', 'success')
        return redirect(url_for('dashboard'))
    
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute('SELECT * FROM users WHERE id = %s', (session['user_id'],))
        user = cur.fetchone()
    conn.close()
    
    return render_template('dashboard.html', user=user)

@app.route('/logout')
def logout():
    session.clear()
    flash('Вы вышли из аккаунта.', 'success')
    return redirect(url_for('index'))

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)