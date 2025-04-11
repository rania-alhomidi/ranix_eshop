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

app = Flask(__name__)
redis_client = redis.StrictRedis(host='localhost', port=6379, db=0, decode_responses=True)

# إعداد مسار رفع الصور
UPLOAD_FOLDER = 'static/uploads'
app.secret_key = 'f2d9e8a0b7c6d1e6f3a8c4b8d9e2f6a4'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['SECRET_KEY'] = 'your_secret_key'

def get_db_connection():
    conn = sqlite3.connect('database/Eshop.db')
    conn.row_factory = sqlite3.Row
    return conn

# تسجيل Blueprints في التطبيق
app.register_blueprint(admin_bp)
app.register_blueprint(user_bp)
app.register_blueprint(product_bp)
app.register_blueprint(cart_bp)
app.register_blueprint(seller_bp)
app.register_blueprint(general_bp)


@app.context_processor
def inject_categories():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # جلب الأقسام الرئيسية فقط (التي ليس لها parent_id)
        cursor.execute("""
            SELECT id, name, parent_id, image
            FROM category
            WHERE parent_id IS NULL
            ORDER BY name
        """)
        main_categories = cursor.fetchall()

        # جلب جميع الأقسام لاستخدامها في أماكن أخرى
        cursor.execute("SELECT id, name, parent_id, image FROM category ORDER BY name")
        all_categories = cursor.fetchall()

        return {
            'main_categories': main_categories,
            'all_categories': all_categories
        }
    finally:
        conn.close()

@app.context_processor
def inject_sellers():
    conn = get_db_connection()
    sellers = conn.execute('SELECT id, store_name FROM sellers').fetchall()
    conn.close()
    return dict(sellers=sellers)


if __name__ == '__main__':
    app.run()