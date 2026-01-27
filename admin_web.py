# admin_web.py

from flask import Flask, render_template, request, redirect, session
from db import Database
from config import Config
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)

config = Config()
db = Database(config.SUPABASE_URL, config.SUPABASE_KEY)

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "change_me_please")

@app.route('/')
def index():
    if not session.get('logged_in'):
        return redirect('/login')
    
    stats = db.get_stats()
    subject_stats = db.get_subject_stats()
    
    return render_template('dashboard.html', 
                         stats=stats, 
                         subject_stats=subject_stats)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['password'] == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect('/')
        return "Неверный пароль"
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect('/login')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
