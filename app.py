from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, make_response
import sqlite3
import os
import json
from datetime import datetime, timedelta
import random
import redis

from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

# استيراد Blueprints
from admin_routes import admin_bp
from user_routes import user_bp
from product_routes import product_bp
from cart_routes import cart_bp
from seller_routes import seller_bp
from general_routes import general_bp
from order import order_bp # تأكد أن هذا الاستيراد صحيح
from ads_routes import ads_bp # تأكد أن هذا الاستيراد صحيح
from search_routes import search_bp

app = Flask(__name__)
redis_client = redis.StrictRedis(host='localhost', port=6379, db=0, decode_responses=True)

# 🟢 التعديل 1: تعريف مجلد رفع عام ومجلد رفع خاص بالإعلانات
# مجلد الرفع العام للملفات الأخرى (مثل صور المنتجات إذا كانت تستخدمه)
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER # هذا للملفات العامة

# مجلد الرفع الخاص بالإعلانات
app.config['UPLOAD_FOLDER_ADS'] = 'static/uploads/ads' # مسار مخصص لصور وفيديوهات الإعلانات
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf','mp4', 'avi', 'mov'} # أنواع الملفات المسموح بها

# تأكد من إنشاء المجلدات إذا لم تكن موجودة
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
if not os.path.exists(app.config['UPLOAD_FOLDER_ADS']): # إنشاء مجلد الإعلانات
    os.makedirs(app.config['UPLOAD_FOLDER_ADS'])


# 🟢 تصحيح: تعيين المفتاح السري مرة واحدة وبشكل صحيح
app.config['SECRET_KEY'] = 'f2d9e8a0b7c6d1e6f3a8c4b8d9e2f6a4_very_long_and_secret_key' # اجعل المفتاح أطول وأكثر تعقيدًا في الإنتاج


# 🟢 ملاحظة: يفضل وضع مسار قاعدة البيانات في app.config أيضاً
# app.config['DATABASE'] = 'database/Eshop.db'
def get_db_connection():
    conn = sqlite3.connect('database/Eshop.db') # أو sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn

# تسجيل Blueprints في التطبيق
app.register_blueprint(admin_bp)
app.register_blueprint(user_bp)
app.register_blueprint(product_bp)
app.register_blueprint(cart_bp)
app.register_blueprint(seller_bp)
app.register_blueprint(general_bp)
app.register_blueprint(order_bp) # تسجيل الـ Blueprint الخاص بالطلبات
app.register_blueprint(search_bp) # تسجيل الـ Blueprint الخاص بالطلبات

# 🟢 التعديل 2: تسجيل Blueprint الإعلانات مع بادئة URL
# هذا ضروري لكي يعمل مسار تتبع النقرات في JavaScript (fetch('/ads/track_click/...'))
# وهذا يعني أن جميع مسارات ads_bp ستكون تحت /ads/ (مثال: /ads/management, /ads/add)
app.register_blueprint(ads_bp, url_prefix='/ads')


@app.context_processor
def inject_categories():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT id, name, parent_id, image
            FROM category
            WHERE parent_id IS NULL
            ORDER BY name
        """)
        main_categories = cursor.fetchall()

        cursor.execute("SELECT id, name, parent_id, image FROM category ORDER BY name")
        all_categories = cursor.fetchall()

        return {
            'main_categories': main_categories,
            'all_categories': all_categories
        }
    finally:
        conn.close()

# ضع هذه الدالة في ملف الـ Blueprint الخاص بالمستخدمين أو في app.py
# def get_main_categories():
#     conn = get_db_connection()
#     # جلب الأقسام الرئيسية (التي ليس لها parent_id)
#     categories = conn.execute("SELECT id, name FROM category WHERE parent_id IS NULL ORDER BY name ASC").fetchall()
#     conn.close()
#     return categories

@app.context_processor
def inject_sellers():
    conn = get_db_connection()
    sellers = conn.execute('SELECT id, store_name FROM sellers').fetchall()
    conn.close()
    return dict(sellers=sellers)

# *** Context Processor الرئيسي لضمان اتساق حالة تسجيل الدخول وعدد المنتجات في السلة ***
@app.context_processor
def inject_user_data_and_cart_count():
    """
    هذه الدالة تعمل قبل كل طلب (request) وتجعل متغيرات مثل 'logged_in',
    'user_name', و 'total_items_count' متاحة لكل القوالب.
    """
    user_id = request.cookies.get('user_auth') # كوكي يدل على أن المستخدم مسجل دخول
    current_user_name = None 
    total_items_in_cart = 0 

    if user_id:
        try:
            current_user_name = request.cookies.get('user_name') 
            
            conn = get_db_connection()
            cart_item_count_row = conn.execute(
                "SELECT SUM(quantity) AS total FROM cart_items WHERE user_id = ?",
                (user_id,)
            ).fetchone()
            conn.close()
            
            if cart_item_count_row and cart_item_count_row['total']:
                total_items_in_cart = int(cart_item_count_row['total'])

        except Exception as e:
            print(f"Error in inject_user_data_and_cart_count context processor: {e}")
            current_user_name = None 
            total_items_in_cart = 0
    
    return dict(
        user_name=current_user_name, # اسم المستخدم (أو None)
        logged_in=bool(user_id), # True إذا كان user_id موجوداً (أي مسجل دخول)
        total_items_count=total_items_in_cart # العدد الكلي للمنتجات في السلة
    )

# *** التعامل مع الأخطاء (مثال: صفحة 404 غير موجودة) ***
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404 # تأكد أن لديك قالب 404.html

@app.template_filter('handle_product_image')
def handle_product_image(image_path):
    if not image_path:
        return 'uploads/products/default_product.jpg'
    return image_path.replace('static/', '')


if __name__ == '__main__':
    app.run(debug=True) # 🟢 تشغيل وضع التصحيح مفيد أثناء التطوير