from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, make_response # 🟢 إزالة session من هنا
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

user_bp = Blueprint('user', __name__)

def get_db_connection():
    conn = sqlite3.connect('database/Eshop.db')
    conn.row_factory = sqlite3.Row
    return conn

@user_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'GET':
        return render_template('signup.html')

    if request.method == 'POST':
        try:
            name = request.form['name']
            phone = request.form['phone_number']
            password = generate_password_hash(request.form['password'])
            email = request.form['email']
            latitude = request.form['latitude']
            longitude = request.form['longitude']
            address = request.form['addressDisplay']

            conn = get_db_connection()
            cursor = conn.cursor()

            # إضافة العنوان
            cursor.execute("INSERT INTO user_addresses (latitude, longitude, address) VALUES (?, ?, ?)",
                            (latitude, longitude, address))
            address_id = cursor.lastrowid

            # إضافة المستخدم
            cursor.execute("INSERT INTO user (name, num, pass, email, ud_ia) VALUES (?, ?, ?, ?, ?)",
                            (name, phone, password, email, address_id))
            user_id = cursor.lastrowid # معرف المستخدم الجديد
            conn.commit()

            flash('تم إنشاء الحساب وتسجيل الدخول بنجاح!', 'success')

            # 🟢 تصحيح: تعيين الكوكيز هنا
            response = make_response(redirect(url_for('product.index'))) # 🟢 التوجيه لصفحة المنتجات الرئيسية
            response.set_cookie(
                'user_auth',
                value=str(user_id),
                max_age=60*60*24*30, # 30 يوم
                secure=True,       # استخدم True في HTTPS
                httponly=True,     # يمنع الوصول من JavaScript
                samesite='Lax'
            )
            response.set_cookie(
                'user_name',
                value=name,
                max_age=60*60*24*30,
                secure=True,
                httponly=False,    # السماح بالوصول من JavaScript إذا لزم الأمر
                samesite='Lax'
            )
            return response

        except sqlite3.IntegrityError as e:
            flash('البريد الإلكتروني أو رقم الهاتف مسجل مسبقًا.', 'danger')
            return redirect(url_for('user.signup'))

        except Exception as e:
            print(f"خطأ في إنشاء الحساب: {e}") # لطباعة الخطأ للمساعدة في التصحيح
            flash('حدث خطأ أثناء إنشاء الحساب. الرجاء المحاولة مرة أخرى.', 'danger')
            return redirect(url_for('user.signup'))

        finally:
            if 'conn' in locals() and conn: # التأكد من أن الاتصال موجود ومفتوح قبل الإغلاق
                conn.close()

@user_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('signin.html')

    if request.method == 'POST':
        name = request.form['name']
        password = request.form['password']

        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM user WHERE name = ?", (name,))
        user = cursor.fetchone()
        conn.close()

        if user is None:
            flash('اسم المستخدم غير موجود.', 'danger')
            return redirect(url_for('user.login'))

        stored_password = user['pass']
        if check_password_hash(stored_password, password):
            flash('تم تسجيل الدخول بنجاح.', 'success')
            # 🟢 تصحيح: تعيين الكوكيز هنا
            response = make_response(redirect(url_for('product.index'))) # 🟢 التوجيه لصفحة المنتجات الرئيسية
            response.set_cookie(
                'user_auth',
                value=str(user['id']),
                max_age=60*60*24*7, # 7 أيام
                secure=True,
                httponly=True,
                samesite='Lax'
            )
            response.set_cookie(
                'user_name',
                value=user['name'],
                max_age=60*60*24*7,
                secure=True,
                httponly=False,
                samesite='Lax'
            )
            return response
        else:
            flash('كلمة المرور غير صحيحة.', 'danger')
            return redirect(url_for('user.login'))

# 🟢 تسجيل الخروج
@user_bp.route('/logout')
def logout():
    flash('تم تسجيل الخروج بنجاح.', 'success')
    # 🟢 تصحيح: حذف الكوكيز هنا
    response = make_response(redirect(url_for('product.index'))) # 🟢 التوجيه لصفحة عامة (الرئيسية)
    response.delete_cookie('user_auth')
    response.delete_cookie('user_name') # إذا كنت تستخدم هذا الكوكي
    return response

# 🟢 تصحيح: استخدام الكوكيز في login_required
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = request.cookies.get('user_auth') # 🟢 الحصول من الكوكي

        if not user_id:
            flash('يجب تسجيل الدخول للوصول إلى هذه الصفحة', 'warning')
            return redirect(url_for('user.login', next=request.url))

        # تحقق من وجود المستخدم في DB (ضروري للتأكد من أن الكوكي لا يشير إلى مستخدم محذوف)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM user WHERE id = ?", (user_id,))
        fetched_user = cursor.fetchone()
        conn.close()

        if not fetched_user:
            # 🟢 إذا لم يتم العثور على المستخدم في DB، احذف الكوكيز وأعد التوجيه
            response = make_response(redirect(url_for('user.login')))
            response.delete_cookie('user_auth')
            response.delete_cookie('user_name')
            flash('جلسة العمل منتهية، يرجى تسجيل الدخول مرة أخرى', 'warning')
            return response

        return f(*args, **kwargs)
    return decorated_function

@user_bp.route('/profile')
@login_required # هذا الـ decorator سيتحقق الآن من الكوكيز
def profile():
    try:
        user_id = request.cookies.get('user_auth') # 🟢 الحصول من الكوكي
        print(f"قيمة الكوكي user_auth في البروفايل: {user_id}")

        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                u.id, u.name, u.num, u.email, u.ud_ia,
                a.address, a.latitude, a.longitude
            FROM user u
            LEFT JOIN user_addresses a ON u.ud_ia = a.id
            WHERE u.id = ?
        """, (user_id,))

        user_data = cursor.fetchone()
        conn.close()

        if not user_data:
            print("لم يتم العثور على مستخدم بهذا المعرف في البروفايل")
            # 🟢 إذا لم يتم العثور على بيانات المستخدم (على الرغم من login_required)، قد يكون هناك تناقض
            # يمكنك هنا إعادة توجيه المستخدم لصفحة تسجيل الدخول مرة أخرى
            flash("المستخدم غير موجود أو بياناته غير مكتملة. يرجى تسجيل الدخول مرة أخرى.", "error")
            response = make_response(redirect(url_for('user.login')))
            response.delete_cookie('user_auth')
            response.delete_cookie('user_name')
            return response


        print("بيانات المستخدم المسترجعة في البروفايل:", dict(user_data))

        user = {
            'id': user_data['id'],
            'name': user_data['name'] or 'غير محدد',
            'num': user_data['num'] or 'غير محدد',
            'email': user_data['email'] or 'غير محدد',
            'address': user_data['address'] or 'لم يتم إضافة عنوان',
            'latitude': user_data['latitude'],
            'longitude': user_data['longitude']
        }

        return render_template('profile.html', user=user)

    except Exception as e:
        print(f"خطأ مفاجئ في البروفايل: {str(e)}")
        flash(f"حدث خطأ في جلب بيانات البروفايل: {str(e)}", "error")
        return redirect(url_for('product.index')) # 🟢 توجيه لصفحة رئيسية عامة

@user_bp.route('/toggle_like/<int:product_id>', methods=['POST'])
def toggle_like(product_id):
    user_id = request.cookies.get('user_auth') # 🟢 الحصول من الكوكي

    if not user_id:
        return jsonify({
            'success': False,
            'message': 'يجب تسجيل الدخول أولاً',
            'is_authenticated': False
        }), 401

    conn = get_db_connection()
    try:
        like = conn.execute('SELECT * FROM likes WHERE user_id=? AND product_id=?',
                            (user_id, product_id)).fetchone() # 🟢 استخدام user_id

        if like:
            conn.execute('DELETE FROM likes WHERE user_id=? AND product_id=?',
                        (user_id, product_id)) # 🟢 استخدام user_id
            action = 'unliked'
        else:
            conn.execute('INSERT INTO likes (user_id, product_id) VALUES (?, ?)',
                        (user_id, product_id)) # 🟢 استخدام user_id
            action = 'liked'

        conn.commit()
        return jsonify({
            'success': True,
            'action': action,
            'is_authenticated': True
        })
    except Exception as e:
        print(f"خطأ في toggle_like: {e}")
        return jsonify({
            'success': False,
            'message': str(e),
            'is_authenticated': True
        }), 500
    finally:
        conn.close()

@user_bp.route('/wishlist')
def wishlist():
    user_id = request.cookies.get('user_auth') # 🟢 الحصول من الكوكي

    if not user_id:
        flash('يجب تسجيل الدخول لعرض المفضلة', 'warning')
        return redirect(url_for('user.login'))

    conn = get_db_connection()
    liked_products = conn.execute('''
        SELECT product.* FROM product
        JOIN likes ON product.id = likes.product_id
        WHERE likes.user_id = ?
    ''', (user_id,)).fetchall() # 🟢 استخدام user_id

    conn.close()

    return render_template('wishlist.html', products=liked_products)