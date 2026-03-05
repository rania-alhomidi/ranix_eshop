<<<<<<< HEAD
import sqlite3
from werkzeug.security import generate_password_hash

# ------------------ بيانات الموظف ------------------
# قم بتعديل هذه البيانات حسب ما تريد
employee_username = 'sagedah1'
employee_password = '1234'
employee_role = 'order_manager' 

# ------------------ عملية الإضافة ------------------
# تشفير كلمة المرور
hashed_password = generate_password_hash(employee_password, method='pbkdf2:sha256')

# الاتصال بقاعدة البيانات
conn = sqlite3.connect('database/Eshop.db')
cursor = conn.cursor()

try:
    # إدخال الموظف في جدول employees
    cursor.execute(
        "INSERT INTO employees (username, password_hash, role) VALUES (?, ?, ?)",
        (employee_username, hashed_password, employee_role)
    )
    conn.commit()
    print("✅ تم إضافة الموظف بنجاح!")
    print(f"اسم المستخدم: {employee_username}")
    print(f"كلمة المرور: {employee_password}")
    print(f"الدور: {employee_role}")

except sqlite3.IntegrityError:
    print(f"❌ خطأ: اسم المستخدم '{employee_username}' موجود بالفعل.")

finally:
=======
import sqlite3
from werkzeug.security import generate_password_hash

# ------------------ بيانات الموظف ------------------
# قم بتعديل هذه البيانات حسب ما تريد
employee_username = 'sagedah1'
employee_password = '1234'
employee_role = 'order_manager' 

# ------------------ عملية الإضافة ------------------
# تشفير كلمة المرور
hashed_password = generate_password_hash(employee_password, method='pbkdf2:sha256')

# الاتصال بقاعدة البيانات
conn = sqlite3.connect('database/Eshop.db')
cursor = conn.cursor()

try:
    # إدخال الموظف في جدول employees
    cursor.execute(
        "INSERT INTO employees (username, password_hash, role) VALUES (?, ?, ?)",
        (employee_username, hashed_password, employee_role)
    )
    conn.commit()
    print("✅ تم إضافة الموظف بنجاح!")
    print(f"اسم المستخدم: {employee_username}")
    print(f"كلمة المرور: {employee_password}")
    print(f"الدور: {employee_role}")

except sqlite3.IntegrityError:
    print(f"❌ خطأ: اسم المستخدم '{employee_username}' موجود بالفعل.")

finally:
>>>>>>> 4599de10fc9ce5b841b06e1a07fc9d42449f6463
    conn.close()