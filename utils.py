<<<<<<< HEAD
# utils.py
from functools import wraps
from flask import request, redirect, url_for, flash, make_response
import sqlite3

def get_db_connection():
    conn = sqlite3.connect('database/Eshop.db')
    conn.row_factory = sqlite3.Row
    return conn

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = request.cookies.get('user_auth')

        if not user_id:
            flash('يجب تسجيل الدخول للوصول إلى هذه الصفحة', 'warning')
            return redirect(url_for('user.login', next=request.url))

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM user WHERE id = ?", (user_id,))
        fetched_user = cursor.fetchone()
        conn.close()

        if not fetched_user:
            response = make_response(redirect(url_for('user.login')))
            response.delete_cookie('user_auth')
            response.delete_cookie('user_name')
            flash('جلسة العمل منتهية، يرجى تسجيل الدخول مرة أخرى', 'warning')
            return response

        # أضف معرف المستخدم إلى request.user_id ليكون متاحًا في الدوال المزينة
        request.user_id = user_id

        return f(*args, **kwargs)
    return decorated_function

# انقل الدوال المساعدة الأخرى هنا لتجنب المشاكل في المستقبل
def get_user_addresses_and_default(user_id):
    conn = get_db_connection()
    recipient_address_obj = {
        'id': None,
        'address_type': "عام",
        'full_address_description': "لا يوجد عنوان محدد",
        'region': "",
        'city': "",
        'recipient_name': "غير محدد",
        'recipient_phone': "لا يوجد رقم",
        'is_default': False
    }
    all_addresses_list = []

    try:
        all_addresses_rows = conn.execute(
            "SELECT * FROM cust_addresses WHERE user_id = ? ORDER BY is_default DESC, id ASC", 
            (user_id,)
        ).fetchall()
        all_addresses_list = [dict(row) for row in all_addresses_rows]

        if all_addresses_list:
            default_address_found = False
            for addr in all_addresses_list:
                if addr['is_default'] == 1:
                    recipient_address_obj = addr
                    default_address_found = True
                    break
            
            if not default_address_found:
                recipient_address_obj = all_addresses_list[0]
        
        user_info_row = conn.execute("SELECT phone_number FROM users WHERE id = ?", (user_id,)).fetchone()
        if user_info_row and user_info_row['phone_number'] is not None:
            if recipient_address_obj.get('recipient_phone') in [None, "لا يوجد رقم", ""]:
                recipient_address_obj['recipient_phone'] = user_info_row['phone_number']

    except Exception as e:
        print(f"Error fetching user addresses/info for user_id {user_id}: {e}")
    finally:
        conn.close()
    
=======
# utils.py
from functools import wraps
from flask import request, redirect, url_for, flash, make_response
import sqlite3

def get_db_connection():
    conn = sqlite3.connect('database/Eshop.db')
    conn.row_factory = sqlite3.Row
    return conn

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = request.cookies.get('user_auth')

        if not user_id:
            flash('يجب تسجيل الدخول للوصول إلى هذه الصفحة', 'warning')
            return redirect(url_for('user.login', next=request.url))

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM user WHERE id = ?", (user_id,))
        fetched_user = cursor.fetchone()
        conn.close()

        if not fetched_user:
            response = make_response(redirect(url_for('user.login')))
            response.delete_cookie('user_auth')
            response.delete_cookie('user_name')
            flash('جلسة العمل منتهية، يرجى تسجيل الدخول مرة أخرى', 'warning')
            return response

        # أضف معرف المستخدم إلى request.user_id ليكون متاحًا في الدوال المزينة
        request.user_id = user_id

        return f(*args, **kwargs)
    return decorated_function

# انقل الدوال المساعدة الأخرى هنا لتجنب المشاكل في المستقبل
def get_user_addresses_and_default(user_id):
    conn = get_db_connection()
    recipient_address_obj = {
        'id': None,
        'address_type': "عام",
        'full_address_description': "لا يوجد عنوان محدد",
        'region': "",
        'city': "",
        'recipient_name': "غير محدد",
        'recipient_phone': "لا يوجد رقم",
        'is_default': False
    }
    all_addresses_list = []

    try:
        all_addresses_rows = conn.execute(
            "SELECT * FROM cust_addresses WHERE user_id = ? ORDER BY is_default DESC, id ASC", 
            (user_id,)
        ).fetchall()
        all_addresses_list = [dict(row) for row in all_addresses_rows]

        if all_addresses_list:
            default_address_found = False
            for addr in all_addresses_list:
                if addr['is_default'] == 1:
                    recipient_address_obj = addr
                    default_address_found = True
                    break
            
            if not default_address_found:
                recipient_address_obj = all_addresses_list[0]
        
        user_info_row = conn.execute("SELECT phone_number FROM users WHERE id = ?", (user_id,)).fetchone()
        if user_info_row and user_info_row['phone_number'] is not None:
            if recipient_address_obj.get('recipient_phone') in [None, "لا يوجد رقم", ""]:
                recipient_address_obj['recipient_phone'] = user_info_row['phone_number']

    except Exception as e:
        print(f"Error fetching user addresses/info for user_id {user_id}: {e}")
    finally:
        conn.close()
    
>>>>>>> 4599de10fc9ce5b841b06e1a07fc9d42449f6463
    return recipient_address_obj, all_addresses_list