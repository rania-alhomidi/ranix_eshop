# auth.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
import sqlite3

auth_bp = Blueprint('auth', __name__)

def get_db_connection():
    conn = sqlite3.connect('database/Eshop.db')
    conn.row_factory = sqlite3.Row
    return conn

@auth_bp.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        conn = get_db_connection()
        user = conn.execute('''
            SELECT au.*, ar.name AS role_name
            FROM admin_users AS au
            JOIN admin_roles AS ar ON au.role_id = ar.id
            WHERE au.email = ?
        ''', (email,)).fetchone()
        conn.close()

        if user and user['password'] == password:
            session['admin_logged_in'] = True
            session['admin_id'] = user['id']
            
            # This is the corrected line
            try:
                session['admin_username'] = user['name']
            except KeyError:
                session['admin_username'] = email

            session['admin_role'] = user['role_name']
            flash('تم تسجيل الدخول بنجاح!', 'success')
            return redirect(url_for('admin.home'))
        else:
            flash('خطأ في البريد الإلكتروني أو كلمة المرور.', 'danger')

    return render_template('admin/admin_login.html')
@auth_bp.route('/admin-logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    session.pop('admin_id', None)
    session.pop('admin_username', None)
    session.pop('admin_role', None)
    flash('تم تسجيل الخروج بنجاح', 'info')
    return redirect(url_for('auth.admin_login'))