import sqlite3

# الاتصال بقاعدة البيانات
conn = sqlite3.connect('database/Eshop.db')
cursor = conn.cursor()

# # # إنشاء جدول الفئات (الأقسام)
# cursor.execute('''CREATE TABLE IF NOT EXISTS category (
#     id INTEGER PRIMARY KEY AUTOINCREMENT,
#     name TEXT NULL,
#     parent_id INTEGER,
#     image TEXT,
#     FOREIGN KEY (parent_id) REFERENCES category(id) ON DELETE SET NULL
# )''')


# # إنشاء جدول المنتجات
# cursor.execute('''CREATE TABLE IF NOT EXISTS product (
#     id INTEGER PRIMARY KEY AUTOINCREMENT,
#     name VARCHAR(255) NULL,
#     image VARCHAR(500),
#     description TEXT,
#     quantity INT NULL,
#     category_id INTEGER NOT NULL,  -- القسم الفرعي
#     seller_id INTEGER NOT NULL,  -- صاحب المنتج
#     address_id INTEGER NOT NULL,  -- عنوان صاحب المنتج
#     price_id INTEGER,
#     stock_id INTEGER,
#     FOREIGN KEY (category_id) REFERENCES category(id),
#     FOREIGN KEY (seller_id) REFERENCES sellers(id),
#     FOREIGN KEY (address_id) REFERENCES user_addresses(id),
#     FOREIGN KEY (price_id) REFERENCES prices(id)
#     FOREIGN KEY (stock_id) REFERENCES stock(id)
# )''')
# cursor.execute('''
# CREATE TABLE IF NOT EXISTS stock (
#     id INTEGER PRIMARY KEY AUTOINCREMENT,
#     product_id INTEGER NOT NULL,
#     quantity INT NOT NULL DEFAULT 0,
#     last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#     FOREIGN KEY (product_id) REFERENCES product(id) ON DELETE CASCADE
# );''')

# # إنشاء جدول أسعار المنتجات
# cursor.execute('''
# CREATE TABLE IF NOT EXISTS prices (
#     id INTEGER PRIMARY KEY AUTOINCREMENT,
#     product_id INTEGER,
#     original_price REAL,
#     profit_price REAL,
#     FOREIGN KEY (product_id) REFERENCES product(id) ON DELETE CASCADE
# );
# ''')
# # إنشاء جدول المستخدمين
# cursor.execute('''
# CREATE TABLE IF NOT EXISTS users (
#     id INTEGER PRIMARY KEY AUTOINCREMENT,
#     name TEXT,
#     num TEXT UNIQUE,
#     pass TEXT,
#     email TEXT UNIQUE,
#     activation_code TEXT,
#     account_status INTEGER DEFAULT 1,
#     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
# );
# ''')

# # إنشاء جدول عناوين المستخدمين
# cursor.execute('''
# CREATE TABLE IF NOT EXISTS user_addresses (
#     id INTEGER PRIMARY KEY AUTOINCREMENT,
#     user_id INTEGER,
#     latitude REAL,
#     longitude REAL,
#     address TEXT,
#     FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
# );
# ''')

# # إنشاء جدول رصيد المستخدمين
# cursor.execute('''
# CREATE TABLE IF NOT EXISTS user_balance (
#     id INTEGER PRIMARY KEY AUTOINCREMENT,
#     user_id INTEGER,
#     balance REAL DEFAULT 0.00,
#     FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
# );
# ''')

# # إنشاء جدول تتبع الرصيد للمدفوعات
# cursor.execute('''
# CREATE TABLE IF NOT EXISTS balance_tracking (
#     id INTEGER PRIMARY KEY AUTOINCREMENT,
#     user_id INTEGER,
#     payment_method TEXT,
#     amount REAL,
#     transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#     FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
# );
# ''')

# # إنشاء جدول البائعين
# cursor.execute('''
# CREATE TABLE IF NOT EXISTS sellers (
#     id INTEGER PRIMARY KEY AUTOINCREMENT,
#     name TEXT,
#     store_name TEXT,
#     store_image TEXT,
#     address TEXT,
#     phone_number TEXT,
#     password TEXT,
#     email TEXT,
#     commercial_record TEXT,
#     id_image TEXT,
#     documents TEXT,
#     product_type TEXT,
#     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
# );
# ''')



# # إنشاء جدول الطلبات
# cursor.execute('''
# CREATE TABLE IF NOT EXISTS orders (
#     id INTEGER PRIMARY KEY AUTOINCREMENT,
#     user_id INTEGER,
#     status TEXT DEFAULT 'قيد التنفيذ',
#     total_amount REAL,
#     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#     expected_delivery TIMESTAMP,
#     FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
# );
# ''')

# # إنشاء جدول بيانات التحليل
# cursor.execute('''
# CREATE TABLE IF NOT EXISTS AnalyticsData (
#     id INTEGER PRIMARY KEY AUTOINCREMENT,
#     user_id INTEGER,
#     action TEXT NOT NULL,
#     metadata TEXT NOT NULL,  -- يتم تخزين JSON كنص
#     timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
#     FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
# );
# ''')

# # إنشاء جدول تقارير المبيعات
# cursor.execute('''
# CREATE TABLE IF NOT EXISTS SalesReports (
#     id INTEGER PRIMARY KEY AUTOINCREMENT,
#     date DATE NOT NULL,
#     total_sales REAL NOT NULL,
#     total_revenue REAL NOT NULL,
#     currency TEXT NOT NULL
# );
# ''')

# # إنشاء جدول مشاهدات الصفحات
# cursor.execute('''
# CREATE TABLE IF NOT EXISTS PageViews (
#     id INTEGER PRIMARY KEY AUTOINCREMENT,
#     user_id INTEGER,
#     page_url TEXT NOT NULL,
#     referrer TEXT,
#     timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
#     FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
# );
# ''')

# # إنشاء جدول العروض الترويجية
# cursor.execute('''
# CREATE TABLE IF NOT EXISTS Promotions (
#     id INTEGER PRIMARY KEY AUTOINCREMENT,
#     title TEXT NOT NULL,
#     description TEXT,
#     discount REAL NOT NULL,
#     start_date DATETIME NOT NULL,
#     end_date DATETIME NOT NULL,
#     terms_conditions TEXT,
#     status TEXT NOT NULL CHECK (status IN ('active', 'expired', 'upcoming'))
# );
# ''')

# # إنشاء جدول اشتراكات النشرة البريدية
# cursor.execute('''
# CREATE TABLE IF NOT EXISTS NewsletterSubscriptions (
#     id INTEGER PRIMARY KEY AUTOINCREMENT,
#     email TEXT UNIQUE NOT NULL,
#     subscription_date DATETIME DEFAULT CURRENT_TIMESTAMP,
#     status TEXT NOT NULL CHECK (status IN ('subscribed', 'unsubscribed'))
# );
# ''')

# # إنشاء جدول الإعلانات (Banners)
# cursor.execute('''
# CREATE TABLE IF NOT EXISTS Banners (
#     id INTEGER PRIMARY KEY AUTOINCREMENT,
#     image_url TEXT NOT NULL,
#     alt_text TEXT,
#     redirect_url TEXT,
#     position TEXT,
#     start_date DATETIME NOT NULL,
#     end_date DATETIME NOT NULL,
#     status TEXT NOT NULL CHECK (status IN ('active', 'inactive'))
# );
# ''')

conn.commit()

# # استعلام لاستعراض الجداول الموجودة في قاعدة البيانات

cursor.execute("SELECT * FROM stock ")  # استعلام عن كل البيانات
rows = cursor.fetchall()  # جلب جميع الصفوف
print("الجداول الموجودة في قاعدة البيانات:", rows)

for row in rows:
    print(row)

# cursor.execute('DROP TABLE IF EXISTS product')  # استبدل 'table_name' باسم الجدول الذي تريد حذفه
# cursor.execute("ALTER TABLE sellers RENAME COLUMN id TO seller_id;")

# cursor.execute('''SELECT name FROM sqlite_master WHERE type='table';''')
# tables = cursor.fetchall()  # جلب النتائج
# print("الجداول الموجودة في قاعدة البيانات:", tables)

# cursor.execute("PRAGMA table_info(product);")
# columns = cursor.fetchall()

# for col in columns:
#     print(col[1])  # col[1] يحتوي على اسم العمود


# إغلاق الاتصال
conn.commit()
conn.close()

