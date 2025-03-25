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

# cursor.execute('''
# CREATE TABLE IF NOT EXISTS stock (
#     id INTEGER PRIMARY KEY AUTOINCREMENT,
#     product_id INTEGER NOT NULL,
#     quantity INT NOT NULL DEFAULT 0,
#     last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
# );''')

# # إنشاء جدول أسعار المنتجات
# cursor.execute('''
# CREATE TABLE IF NOT EXISTS prices (
#     id INTEGER PRIMARY KEY AUTOINCREMENT,
#     product_id INTEGER,
#     original_price REAL,
#     profit_price REAL
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
#     ud_ia INTEGER,
#     activation_code TEXT,
#     account_status INTEGER DEFAULT 1,
#     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#     FOREIGN KEY (ud_ia) REFERENCES user_addresses(id) ON DELETE CASCADE
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

# cursor.execute(''' 
# CREATE TABLE IF NOT EXISTS sellers (
#     id INTEGER PRIMARY KEY AUTOINCREMENT,
#     name TEXT,
#     store_name TEXT,
#     store_image TEXT,
#     commercial_record TEXT,
#     id_image TEXT,
#     documents TEXT,
#     SAddress_id INTEGER,
#     num_id INTEGER,
#     created_at TIMESTAMP,
#     FOREIGN KEY (SAddress_id) REFERENCES seller_address(id) ON DELETE CASCADE,
#     FOREIGN KEY (num_id) REFERENCES numbers(id) ON DELETE CASCADE
# );
# ''')

# cursor.execute('''
# CREATE TABLE IF NOT EXISTS seller_address(
#     id INTEGER PRIMARY KEY AUTOINCREMENT,
#     latitude REAL,
#     longitude REAL,
#     address TEXT );
# ''')

# # إنشاء جدول الطلبات
# cursor.execute('''
# CREATE TABLE IF NOT EXISTS orders (
#     id INTEGER PRIMARY KEY AUTOINCREMENT,
#     user_id INTEGER,
#     pro_id INTEGER,
#     status TEXT DEFAULT 'قيد التنفيذ',
#     total_amount REAL,
#     quantity INTEGER,
#     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#     expected_delivery TIMESTAMP,
#     FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
#     FOREIGN KEY (pro_id) REFERENCES product(id) ON DELETE SET NULL
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




# # إنشاء جدول المنتجات
# cursor.execute('''CREATE TABLE IF NOT EXISTS product (
#     id INTEGER PRIMARY KEY AUTOINCREMENT,
#     name VARCHAR(255) NULL,
#     image VARCHAR(500),
#     description TEXT,
#     category_id INTEGER NOT NULL,  -- القسم الفرعي
#     seller_id INTEGER NOT NULL,  -- صاحب المنتج
#     address_id INTEGER NOT NULL,  -- عنوان صاحب المنتج
#     price_id INTEGER,
#     stock_id INTEGER,
#     FOREIGN KEY (category_id) REFERENCES category(id),
#     FOREIGN KEY (seller_id) REFERENCES sellers(id),
#     FOREIGN KEY (address_id) REFERENCES seller_address(id),
#     FOREIGN KEY (price_id) REFERENCES prices(id),
#     FOREIGN KEY (stock_id) REFERENCES stock(id)
# )''')
# ارقام البيائعين
# cursor.execute('''CREATE TABLE IF NOT EXISTS numbers (
#     id INTEGER PRIMARY KEY AUTOINCREMENT,
#     number1 INTEGER NOT NULL,
#     number2 INTEGER NOT NULL
# );''')


# cursor.execute('''CREATE TABLE orders1 (
#     id INTEGER PRIMARY KEY AUTOINCREMENT,
#     user_id INTEGER NOT NULL,
#     total_price REAL NOT NULL,
#     status TEXT CHECK(status IN ('pending', 'processing', 'shipped', 'delivered', 'cancelled')) DEFAULT 'pending',
#     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#     updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
# );''')

# cursor.execute('''
#     CREATE TABLE Order_Items (
#     id INTEGER PRIMARY KEY AUTOINCREMENT,
#     order_id INTEGER NOT NULL,
#     product_id INTEGER NOT NULL,
#     quantity INTEGER NOT NULL CHECK(quantity > 0),
#     price REAL NOT NULL,
#     FOREIGN KEY (order_id) REFERENCES orders1(id) ON DELETE CASCADE,
#     FOREIGN KEY (product_id) REFERENCES product(id) ON DELETE CASCADE
# );''')


conn.commit()

# # استعلام لاستعراض الجداول الموجودة في قاعدة البيانات

cursor.execute("SELECT * FROM orders1 ")  # استعلام عن كل البيانات
rows = cursor.fetchall()  # جلب جميع الصفوف
print("البيانات الموجودة في قاعدة البيانات:", rows)

for row in rows:
    print(row)

cursor.execute("SELECT * FROM Order_Items ")  # استعلام عن كل البيانات
rows = cursor.fetchall()  # جلب جميع الصفوف
print("البيانات الموجودة في قاعدة البيانات:", rows)

for row in rows:
    print(row)

# cursor.execute('''ALTER TABLE product ADD COLUMN featured BOOLEAN DEFAULT 0;''')
# cursor.execute('''INSERT INTO product (name, image, description, quantity, category_id, seller_id, address_id, price_id, stock_id)
# VALUES 
# ('منتج 1', 'static/uploads\\51ada2ee49fccfda68f0114966161bcd.jpg', '  nice and buteaful', 7, 1, 3, 1, 1, 1);''')
# cursor.execute('DROP TABLE IF EXISTS Order_Items')  # استبدل 'table_name' باسم الجدول الذي تريد حذفه
# cursor.execute("ALTER TABLE sellers RENAME COLUMN id TO seller_id;")

# cursor.execute('''SELECT name FROM sqlite_master WHERE type='table';''')
# tables = cursor.fetchall()  # جلب النتائج
# print("الجداول الموجودة في قاعدة البيانات:", tables)

# cursor.execute("PRAGMA table_info(sellers);")
# columns = cursor.fetchall()

# for col in columns:
#     print(col[1])  # col[1] يحتوي على اسم العمود

# إغلاق الاتصال
conn.commit()
conn.close()

