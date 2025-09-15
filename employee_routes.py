# employee_routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

# تعريف Blueprint للموظفين
employee_bp = Blueprint('employee', __name__, url_prefix='/employee')

# ----------------- الديكورات المخصصة للحماية -----------------
def get_db_connection():
    conn = sqlite3.connect('database/Eshop.db')
    conn.row_factory = sqlite3.Row
    return conn

def login_required_employee(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'employee_role' not in session:
            return redirect(url_for('employee.login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required_employee(allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if session.get('employee_role') not in allowed_roles:
                flash('Access Denied', 'danger')
                return redirect(url_for('employee.dashboard')) # إعادة توجيه إلى لوحة التحكم بدلاً من رسالة خطأ
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# ----------------- مسار تسجيل الدخول -----------------
@employee_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = sqlite3.connect('database/Eshop.db')
        conn.row_factory = sqlite3.Row
        employee = conn.execute('SELECT * FROM employees WHERE username = ?', (username,)).fetchone()
        conn.close()

        if employee and check_password_hash(employee['password_hash'], password):
            session['employee_id'] = employee['id']
            session['employee_username'] = employee['username']
            session['employee_role'] = employee['role']
            flash('تم تسجيل الدخول بنجاح!', 'success')
            return redirect(url_for('employee.dashboard'))
        else:
            flash('اسم المستخدم أو كلمة المرور غير صحيحة.', 'danger')
            return render_template('employee/login.html')
        
    return render_template('employee/login.html')

# ----------------- مسار الخروج -----------------
@employee_bp.route('/logout')
def logout():
    session.pop('employee_id', None)
    session.pop('employee_username', None)
    session.pop('employee_role', None)
    flash('تم تسجيل الخروج بنجاح.', 'info')
    return redirect(url_for('employee.login'))

# ----------------- صفحة لوحة التحكم (مثال) -----------------
@employee_bp.route('/dashboard')
@login_required_employee
def dashboard():
    conn = sqlite3.connect('database/Eshop.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    total_purchases = cursor.execute('SELECT SUM(total_price) FROM orders').fetchone()[0] or 0
    total_products = cursor.execute('SELECT COUNT(*) FROM product').fetchone()[0] or 0
    total_users = cursor.execute('SELECT COUNT(*) FROM users').fetchone()[0] or 0

    conn.close()

    return render_template(
        'admin/index.html',
        user_type='employee',
        user_role=session.get('employee_role'), # أضف هذا المتغير
        total_purchases=total_purchases,
        total_products=total_products,
        total_users=total_users,
        current_page='dashboard'
    )

# ----------------- مسار إضافة منتج -----------------
@employee_bp.route('/add_product', methods=['GET', 'POST'])
@login_required_employee
@role_required_employee(['super_admin', 'product_and_ads_manager'])
def add_product():
    conn = get_db_connection()
    categories = conn.execute('SELECT id, name, parent_id FROM category WHERE parent_id IS NOT NULL').fetchall()
    sellers = conn.execute('SELECT id, name FROM sellers').fetchall()
    conn.close()
    
    if request.method == 'POST':
        # ... (باقي كود إضافة المنتج) ...
        # (لا حاجة للتعديل هنا، المنطق صحيح)
        pass # placeholder

    # تمرير المتغيرات المطلوبة للقالب
    return render_template('admin/add_product.html',
        categories=categories,
        sellers=sellers,
        current_page='add_product',
        user_type='employee', # ⬅️  **تأكد من وجود هذا السطر**
        user_role=session.get('employee_role') # ⬅️  **أضف هذا السطر**
    )

# ----------------- مسار إضافة موظف -----------------
@employee_bp.route('/add_employee', methods=['GET', 'POST'])
@login_required_employee
@role_required_employee(['super_admin', 'seller_manager'])
def add_employee():
    conn = None
    try:
        conn = sqlite3.connect('database/Eshop.db')
        cursor = conn.cursor()

        if request.method == 'POST':
            # ... (باقي كود إضافة الموظف) ...
            pass # placeholder

        # عند طلب الصفحة بمتصفح (GET)
        return render_template('employee/add_employee.html',
            user_type='employee', # ⬅️  **تأكد من وجود هذا السطر**
            user_role=session.get('employee_role') # ⬅️  **أضف هذا السطر**
        )

    except sqlite3.IntegrityError:
        # ...
        pass # placeholder

    finally:
        if conn:
            conn.close()
            
    # يجب أن يكون لديك `return` هنا في حالة POST
    # يمكنك وضع redirect(...)
    
    # تأكد من إعادة توجيه المستخدم بعد العملية
    return redirect(url_for('employee.dashboard'))