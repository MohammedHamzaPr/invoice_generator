from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from fpdf import FPDF
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from waitress import serve
import hashlib
import sqlite3
import os, tempfile, zipfile, io, traceback, re, smtplib


# محاولة استيراد openpyxl مع معالجة الخطأ
try:
    import openpyxl
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False
    print("Warning: openpyxl not installed. Please run: pip install openpyxl")

app = Flask(__name__)
app.secret_key = 'londonsky-secret-key-2024-ahmed-alnaemmy'

# إعدادات البريد الإلكتروني (يرجى تعديلها حسب إعداداتك)
EMAIL_ADDRESS = "your_email@gmail.com"
EMAIL_PASSWORD = "your_app_password"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# ========== إعداد نظام تسجيل الدخول ==========
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = '❌ الرجاء تسجيل الدخول أولاً'

# ========== إعداد قاعدة بيانات المستخدمين ==========
def init_db():
    """إنشاء قاعدة بيانات المستخدمين"""
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    # إنشاء جدول المستخدمين
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )''')
    
    # حذف المستخدم القديم إذا وجد
    c.execute("DELETE FROM users WHERE username = 'Ahmed Alnaemny'")
    
    # إضافة المستخدم الجديد: Ahmed Alnaemny / London1234
    hashed_password = hashlib.sha256('London1234'.encode()).hexdigest()
    c.execute("INSERT INTO users (username, password) VALUES (?, ?)",
              ('Ahmed Alnaemny', hashed_password))
    
    conn.commit()
    conn.close()
    print("✅ User created: Ahmed Alnaemny / London1234")

# فئة المستخدم
class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username

@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT id, username FROM users WHERE id = ?", (user_id,))
    user = c.fetchone()
    conn.close()
    if user:
        return User(user[0], user[1])
    return None

def check_login(username, password):
    """التحقق من صحة بيانات الدخول"""
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT id, username FROM users WHERE username = ? AND password = ?", 
              (username, hashed_password))
    user = c.fetchone()
    conn.close()
    return user

# تهيئة قاعدة البيانات
init_db()

# ========== Routes للمصادقة ==========

@app.route('/login', methods=['GET', 'POST'])
def login():
    """صفحة تسجيل الدخول"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = check_login(username, password)
        if user:
            user_obj = User(user[0], user[1])
            login_user(user_obj)
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='❌ اسم المستخدم أو كلمة المرور غير صحيحة')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """تسجيل الخروج"""
    logout_user()
    return redirect(url_for('login'))

def get_datetime_suffix():
    """إرجاع لاحقة التاريخ والوقت بصيغة: YYYY-MM-DD_HH-MM-SS"""
    now = datetime.now()
    return now.strftime("%Y-%m-%d_%H-%M-%S")

# دوال مساعدة
def clean_string(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value)

def clean_filename(value):
    if not value:
        return "INVOICE"
    value = str(value).strip()
    value = re.sub(r'[\\/*?:"<>|]', '', value)
    value = value.replace(' ', '_')
    return value

def clean_dict(data):
    if data is None:
        return {}
    if isinstance(data, dict):
        cleaned = {}
        for key, value in data.items():
            if isinstance(value, dict):
                cleaned[key] = clean_dict(value)
            elif isinstance(value, list):
                cleaned[key] = [clean_dict(item) if isinstance(item, dict) else clean_string(item) for item in value]
            else:
                cleaned[key] = clean_string(value)
        return cleaned
    elif isinstance(data, list):
        return [clean_dict(item) if isinstance(item, dict) else clean_string(item) for item in data]
    else:
        return clean_string(data)

def get_safe_filename(invoice_number):
    clean_number = clean_filename(invoice_number)
    return f"INV_{clean_number}"

def get_client_id_and_project_code(business_unit):
    """الحصول على Client ID و Project Code بناءً على Business Unit"""
    business_unit_str = clean_string(business_unit)
    if "Kentech Gulf Holdings Limited Iraq Branch" == business_unit_str:
        return "2947", "BGC 2475"
    elif "BGC-KIQ-KENTECH GULF HOLDINGS LIMITED IRAQ" == business_unit_str:
        return "4697", "BGC 2475"
    elif "PETROCHINA_BGC-KIQ-KENTECH GULF HOLDINGS LIMITED IRAQ BRANCH" == business_unit_str:
        return "PetroChina", "BGC 2475"
    else:
        return "", ""

def get_client_name(business_unit):
    """الحصول على Client Name بناءً على Business Unit"""
    business_unit_str = clean_string(business_unit)
    print(business_unit_str)
    return business_unit_str

def get_pax_name_fields(passenger_name):
    """
    تنسيق اسم المسافر إلى PAX First Name و PAX Last Name مع التحقق من صحة الإدخال
    الصيغة المتوقعة: LASTNAME/FIRSTNAME (مثال: MANSOURI/AHMED)
    """
    passenger_name = clean_string(passenger_name)
    if not passenger_name:
        return "", ""
    
    # إذا كان الاسم يحتوي على / (الصيغة المتوقعة: LAST/FIRST)
    if '/' in passenger_name:
        parts = passenger_name.split('/')
        if len(parts) >= 2:
            last_name = parts[0].strip()
            first_name = parts[1].strip()
            # التأكد من عدم وجود قيم فارغة
            if last_name and first_name:
                return first_name, last_name
            elif last_name and not first_name:
                return last_name, ""
            elif not last_name and first_name:
                return first_name, ""
            else:
                return passenger_name, ""
        else:
            # إذا كان هناك / ولكن التقسيم لم يعطِ جزئين
            return passenger_name, ""
    else:
        # إذا لم يكن هناك /، نعتبر الاسم كله first name و last name فارغ
        # ونعرض تحذير في console
        print(f"Warning: Passenger name '{passenger_name}' does not contain '/' separator. Expected format: LASTNAME/FIRSTNAME")
        return passenger_name, ""

def get_booking_type(data):
    """تحديد Booking Type بناءً على وجود Hotel أو Flight Segments"""
    has_hotel = data.get('hotel') and data.get('hotel', {}).get('hotel_name')
    has_segments = data.get('segments') and len(data.get('segments', [])) > 0
    
    # إذا كان هناك فندق فقط (بدون رحلات طيران)
    if has_hotel and not has_segments:
        return "HTL"
    # إذا كان هناك رحلات طيران فقط (بدون فندق)
    elif has_segments and not has_hotel:
        return "AIR"
    # إذا كان هناك كليهما، الأولوية للطيران
    elif has_hotel and has_segments:
        return "AIR"
    else:
        return "AIR"

def get_vendor_code(flight_code):
    """الحصول على Vendor Code (أول حرفين) و Vendor Name"""
    flight_code = clean_string(flight_code)
    if not flight_code:
        return "", ""
    
    # Vendor Code: أول حرفين من Flight Code
    vendor_code = flight_code[:2] if len(flight_code) >= 2 else flight_code

    return vendor_code

def parse_trip_reason(trip_reason_value):
    """تقسيم Trip Reason إلى Trip Reason و Travel Type"""
    trip_reason_value = clean_string(trip_reason_value)
    if not trip_reason_value:
        return "", ""
    
    # البحث عن النص قبل وبعد علامة -
    if ' - ' in trip_reason_value:
        parts = trip_reason_value.split(' - ', 1)
        return parts[0], parts[1]
    else:
        # إذا كانت القيمة Rotation (R&R)
        if "Rotation" in trip_reason_value or "R&R" in trip_reason_value:
            return "Rotation", "Rotational"
        # إذا كانت قيمة أخرى بدون علامة -
        return trip_reason_value, trip_reason_value

@app.route('/')
@login_required
def index():
    return render_template('index.html', user=current_user)

@app.route('/generate_pdf', methods=['POST'])
def generate_pdf():
    try:
        data = request.json
        data = clean_dict(data)
        
        # التحقق من صحة اسم الراكب
        passenger_name = data.get('passenger_name', '')
        if passenger_name and '/' not in passenger_name:
            print(f"Warning: PDF - Passenger name '{passenger_name}' does not contain '/' separator")
        
        invoice_number = data.get('invoice_number', '')
        safe_filename = get_safe_filename(invoice_number)
        
        pdf = FPDF('P', 'mm', 'A4')
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        
        # ========== إضافة الشعار (يسار) ومعلومات الشركة (يمين) ==========
        # logo_path = os.path.join('src', 'Logo.png')
        logo_path = 'src/Logo.png'
        
        # الشعار في أقصى اليسار
        if os.path.exists(logo_path):
            pdf.image(logo_path, x=10, y=8, w=70)
        
        # معلومات الشركة في أقصى اليمين
        pdf.set_y(8)
        pdf.set_x(145)
        pdf.set_font("Arial", 'B', 7)
        pdf.set_text_color(0, 0, 0)
        
        pdf.multi_cell(0, 4, txt="London Sky Company for selling Flight Tickets/Limited", align='R')
        pdf.set_font("Arial", size=7)
        pdf.multi_cell(0, 4, txt="London sky Building", align='R')
        pdf.multi_cell(0, 4, txt="Bakhtiari St. 98, 44001 - Erbil, Iraq", align='R')
        pdf.set_font("Arial", 'B', 7)
        pdf.multi_cell(0, 4, txt="Tel No.964 7518108782", align='R')
        # ========== عنوان التذكرة ==========
        pdf.set_y(35)
        pdf.set_font("Arial", 'B', 14)
        pdf.set_text_color(0, 51, 102)
        pdf.cell(190, 7, txt="AIRLINE TICKET INVOICE", ln=True, align='C')
        pdf.set_text_color(0, 0, 0)
        
        # خط فاصل
        pdf.set_draw_color(0, 51, 102)
        pdf.line(10, 45, 200, 45)
        pdf.ln(5)
        
        # ========== INVOICE DETAILS ==========
        pdf.set_font("Arial", 'B', 10)
        pdf.set_fill_color(230, 240, 255)
        pdf.cell(190, 6, txt="INVOICE DETAILS", ln=True, fill=True)
        
        pdf.set_font("Arial", size=8)
        
        # Invoice Number (سطر كامل)
        pdf.set_font("Arial", 'B', 8)
        pdf.cell(40, 5, txt="Invoice Number:", ln=0)
        pdf.set_font("Arial", size=8)
        pdf.cell(150, 5, txt=str(data.get('invoice_number', '-'))[:40], ln=1)
        
        # Invoice Date (سطر منفصل)
        pdf.set_font("Arial", 'B', 8)
        pdf.cell(40, 5, txt="Invoice Date:", ln=0)
        pdf.set_font("Arial", size=8)
        pdf.cell(150, 5, txt=str(data.get('invoice_date', '-'))[:20], ln=1)
        
        # Date of Supply (سطر منفصل)
        pdf.set_font("Arial", 'B', 8)
        pdf.cell(40, 5, txt="Date of Supply:", ln=0)
        pdf.set_font("Arial", size=8)
        pdf.cell(150, 5, txt=str(data.get('date_supply', '-'))[:20], ln=1)
        
        # Booked By (سطر منفصل)
        pdf.set_font("Arial", 'B', 8)
        pdf.cell(40, 5, txt="Booked By:", ln=0)
        pdf.set_font("Arial", size=8)
        pdf.cell(150, 5, txt=str(data.get('booked_by', '-'))[:20], ln=1)
        
        # ========== PASSENGER & BOOKING ==========
        pdf.set_font("Arial", 'B', 10)
        pdf.set_fill_color(230, 240, 255)
        pdf.cell(190, 6, txt="PASSENGER & BOOKING DETAILS", ln=True, fill=True)
        
        pdf.set_font("Arial", size=8)
        # صف 1
        pdf.set_font("Arial", 'B', 8)
        pdf.cell(40, 5, txt="Passenger Name:", ln=0)
        pdf.set_font("Arial", size=8)
        pdf.cell(55, 5, txt=str(data.get('passenger_name', '-'))[:25], ln=0)
        pdf.set_font("Arial", 'B', 8)
        pdf.cell(40, 5, txt="Employee ID:", ln=0)
        pdf.set_font("Arial", size=8)
        pdf.cell(55, 5, txt=str(data.get('employee_id', '-'))[:20], ln=1)
        
        # صف 2
        pdf.set_font("Arial", 'B', 8)
        pdf.cell(40, 5, txt="Type of Traveller:", ln=0)
        pdf.set_font("Arial", size=8)
        pdf.cell(55, 5, txt='Project Traveller', ln=0)
        pdf.set_font("Arial", 'B', 8)
        pdf.cell(40, 5, txt="Cost Center:", ln=0)
        pdf.set_font("Arial", size=8)
        pdf.cell(55, 5, txt=str(data.get('cost_center', '-'))[:20], ln=1)
        
        # صف 3
        pdf.set_font("Arial", 'B', 8)
        pdf.cell(40, 5, txt="Travel Type:", ln=0)
        pdf.set_font("Arial", size=8)
        pdf.cell(55, 5, txt='Rotational', ln=0)
        
        # 4 - Trip Reason
        pdf.set_font("Arial", 'B', 8)
        pdf.cell(40, 5, txt="Trip Reason:", ln=0)
        pdf.set_font("Arial", size=8)
        pdf.cell(150, 5, txt=str(data.get('trip_reason', '-'))[:45], ln=1)
        
        # صف 5 - Business Unit
        pdf.set_font("Arial", 'B', 8)
        pdf.cell(40, 5, txt="Business Unit:", ln=0)
        pdf.set_font("Arial", size=7)
        business_unit_text = str(data.get('business_unit', '-'))
        pdf.cell(150, 5, txt=business_unit_text[:60], ln=1)

        
        # ========== FINANCIALS ==========
        pdf.set_font("Arial", 'B', 10)
        pdf.set_fill_color(230, 240, 255)
        pdf.cell(190, 6, txt="FINANCIAL DETAILS", ln=True, fill=True)
        
        pdf.set_font("Arial", size=8)
        
        # صف 1
        pdf.set_font("Arial", 'B', 8)
        pdf.cell(55, 6, txt="Fare (Ex VAT):", border=1, ln=0)
        pdf.set_font("Arial", size=8)
        pdf.cell(40, 6, txt=f"{data.get('fare', '0')} USD", border=1, ln=0)
        pdf.set_font("Arial", 'B', 8)
        pdf.cell(55, 6, txt="LSK Fee / Commission:", border=1, ln=0)
        pdf.set_font("Arial", size=8)
        pdf.cell(40, 6, txt=f"{data.get('lsk_fee', '0')} USD", border=1, ln=1)
        
        # Total
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(55, 7, txt="TOTAL PAYABLE:", border=1, ln=0, fill=True)
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(135, 7, txt=f"{data.get('total', '0')} USD", border=1, ln=1, fill=True)
        pdf.ln(5)
        
        # ========== FLIGHT SEGMENTS ==========
        segments = data.get('segments', [])
        if segments and len(segments) > 0:
            pdf.set_font("Arial", 'B', 10)
            pdf.set_fill_color(230, 240, 255)
            pdf.cell(190, 6, txt="FLIGHT SEGMENTS", ln=True, fill=True)
            
            # رأس الجدول
            pdf.set_font("Arial", 'B', 7)
            pdf.set_fill_color(0, 51, 102)
            pdf.set_text_color(255, 255, 255)
            
            headers = ['Airline', 'Flight', 'From', 'To', 'Depart Date', 'Time', 'Arrival Date', 'Time', 'Cls']
            widths = [18, 18, 16, 16, 22, 16, 22, 16, 10]
            
            for i, header in enumerate(headers):
                pdf.cell(widths[i], 5, header, border=1, align='C', fill=True)
            pdf.ln()
            
            # بيانات الرحلات
            pdf.set_font("Arial", size=6.5)
            pdf.set_text_color(0, 0, 0)
            
            for seg in segments:
                pdf.cell(widths[0], 4, str(seg.get('airline_code', '-'))[:6], border=1)
                pdf.cell(widths[1], 4, str(seg.get('flight_number', '-'))[:10], border=1)
                pdf.cell(widths[2], 4, str(seg.get('origin', '-'))[:6], border=1)
                pdf.cell(widths[3], 4, str(seg.get('destination', '-'))[:6], border=1)
                pdf.cell(widths[4], 4, str(seg.get('depart_date', '-'))[:10], border=1)
                pdf.cell(widths[5], 4, str(seg.get('depart_time', '-'))[:5], border=1)
                pdf.cell(widths[6], 4, str(seg.get('arrival_date', '-'))[:10], border=1)
                pdf.cell(widths[7], 4, str(seg.get('arrival_time', '-'))[:5], border=1)
                pdf.cell(widths[8], 4, str(seg.get('class_name', '-'))[:2], border=1)
                pdf.ln()
            pdf.ln(5)
        
        # ========== HOTEL DETAILS ==========
        hotel = data.get('hotel', {})
        if hotel and hotel.get('hotel_name'):
            pdf.set_font("Arial", 'B', 10)
            pdf.set_fill_color(230, 240, 255)
            pdf.cell(190, 6, txt="HOTEL DETAILS", ln=True, fill=True)
            
            pdf.set_font("Arial", size=8)
            
            # حساب منتصف الصفحة
            mid_x = 105
            
            # الجهة اليسار: Check In, Check Out, Nights (واحد فوق الثاني)
            y_start = pdf.get_y()
            
            # Check In
            pdf.set_y(y_start)
            pdf.set_x(10)
            pdf.set_font("Arial", 'B', 8)
            pdf.cell(30, 5, txt="Check In:", ln=0)
            pdf.set_font("Arial", size=8)
            pdf.cell(40, 5, txt=str(hotel.get('check_in', '-'))[:12], ln=1)
            
            # Check Out
            pdf.set_font("Arial", 'B', 8)
            pdf.cell(30, 5, txt="Check Out:", ln=0)
            pdf.set_font("Arial", size=8)
            pdf.cell(40, 5, txt=str(hotel.get('check_out', '-'))[:12], ln=1)
            
            # Nights
            pdf.set_font("Arial", 'B', 8)
            pdf.cell(30, 5, txt="Nights:", ln=0)
            pdf.set_font("Arial", size=8)
            pdf.cell(40, 5, txt=str(hotel.get('nights', '-')), ln=1)
            
            # الجهة اليمين: Hotel Name, Location (واحد فوق الثاني) - نفس الموقع بالضبط
            pdf.set_y(y_start)
            pdf.set_x(mid_x)
            pdf.set_font("Arial", 'B', 8)
            pdf.cell(30, 5, txt="Hotel Name:", ln=0)
            pdf.set_font("Arial", size=8)
            # هنا بس غيرنا إلى multi_cell عشان النص الطويل
            hotel_name_text = str(hotel.get('hotel_name', '-'))
            pdf.multi_cell(50, 5, txt=hotel_name_text)
            
            pdf.set_y(pdf.get_y() + 2)
            pdf.set_x(mid_x)
            pdf.set_font("Arial", 'B', 8)
            pdf.cell(30, 5, txt="Location:", ln=0)
            pdf.set_font("Arial", size=8)
            location_text = str(hotel.get('location', '-'))
            pdf.multi_cell(50, 5, txt=location_text)
            
            pdf.ln(5)
        
        # ========== النص الطويل (Beneficiary & Bank Details) في الوسط ==========
        pdf.ln(5)
        pdf.set_font("Arial", size=7)
        pdf.set_text_color(0, 0, 0)
        
        # خط فاصل قبل النص
        pdf.set_draw_color(150, 150, 150)
        pdf.line(30, pdf.get_y(), 180, pdf.get_y())
        pdf.ln(3)
        
        # النص في الوسط (محاذاة للوسط)
        pdf.set_font("Arial", 'I', 7)
        pdf.cell(190, 4, txt="This is a computer-generated document, bears no signature.", ln=True, align='C')
        pdf.cell(190, 4, txt="Invoices must be paid as per agreed credit terms.", ln=True, align='C')
        pdf.cell(190, 4, txt="Any dispute must be notified within 14 days of invoice, if not the invoice will be treated as accepted/final", ln=True, align='C')
        pdf.ln(2)
        
        pdf.set_font("Arial", 'B', 7)
        pdf.cell(190, 4, txt="Beneficiary Name: LONDON SKY COMPANY FOR SELLING FLIGHT TICKETS/LIMITED", ln=True, align='C')
        pdf.set_font("Arial", size=7)
        pdf.cell(190, 4, txt="Bank Details: BBAC s.a.l. Erbil Branch, 60M Street, Erbil, Iraq", ln=True, align='C')
        pdf.set_font("Arial", 'B', 7)
        pdf.cell(190, 4, txt="IBAN: IQ74 BBAC 0013 6863 1202 010", ln=True, align='C')
        pdf.set_font("Arial", size=7)
        pdf.cell(190, 4, txt="ACCOUNT NO: 0368-631202-002     SWIFT Code: BBACIQBA", ln=True, align='C')
        pdf.set_font("Arial", 'B', 7)
        pdf.cell(190, 4, txt="All invoice related queries have to be mailed to: accounts@londonskyco.com", ln=True, align='C')
        
        pdf.ln(3)
        pdf.set_draw_color(150, 150, 150)
        pdf.line(30, pdf.get_y(), 180, pdf.get_y())
        
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        pdf.output(temp_file.name)
        
        return send_file(temp_file.name, as_attachment=True, download_name=f"{safe_filename}_{datetime.now().day}{datetime.now().hour}.pdf")
    except Exception as e:
        print(f"PDF Error: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/generate_excel', methods=['POST'])
def generate_excel():
    try:
        if not OPENPYXL_AVAILABLE:
            return jsonify({'error': 'openpyxl library is not installed. Please run: pip install openpyxl'}), 500
        
        data = request.json
        if data:
            data = clean_dict(data)
        else:
            data = {}
        
        print("Data received for Excel:", data)
        
        # ========== التحقق من صحة البيانات قبل المعالجة ==========
        passenger_name = data.get('passenger_name', '')
        if not passenger_name:
            return jsonify({'error': '⚠️ الرجاء إدخال اسم الراكب (Passenger Name)'}), 400
        
        if '/' not in passenger_name:
            return jsonify({
                'error': '⚠️ صيغة اسم الراكب غير صحيحة!\n\n'
                         'الرجاء استخدام الصيغة التالية:\n'
                         'الكنية/الاسم الأول\n\n'
                         'مثال: MANSOURI/AHMED'
            }), 400
        
        # التحقق من وجود رقم الفاتورة
        invoice_number = data.get('invoice_number', '')
        if not invoice_number:
            return jsonify({'error': '⚠️ الرجاء إدخال رقم الفاتورة (Invoice Number)'}), 400
        
        safe_filename = get_safe_filename(invoice_number)
        
        invoice_buffer = create_invoice_excel(data)
        segment_buffer = create_segment_excel(data)
        
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            invoice_filename = f"{safe_filename}_INVOICE.xlsx"
            segment_filename = f"{safe_filename}_SEGMENT.xlsx"
            zip_file.writestr(invoice_filename, invoice_buffer.getvalue())
            zip_file.writestr(segment_filename, segment_buffer.getvalue())
        
        
        zip_buffer.seek(0)
        datee = datetime.now()
        date = f'{datee.year}{datee.month}{datee.day}{datee.hour}{datee.minute}'
        return send_file(
            zip_buffer,
            as_attachment=True,
            download_name=f"{safe_filename}_TICKET_FILES_{date}.zip",
            mimetype='application/zip'
        )
    except Exception as e:
        print(f"Excel Error: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

def create_invoice_excel(data):
    """إنشاء ملف INVOICE Excel حسب المتطلبات الجديدة مع دعم بيانات الفندق"""
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    
    # تعريف الأنماط
    header_font = Font(bold=True, size=11, color="FFFFFF")
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    # عناوين الأعمدة المطلوبة
    headers = [
        "Record Key", "Sequence Number", "Client Id", "Client Name", "Invoice Date",
        "Booked Date", "Void Ind", "Salutation", "PAX First Name", "PAX Last Name",
        "Booking Type", "Document Number", "Record Locator (PNR)", "Vendor Code",
        "Vendor Name", "Outbound", "Depart Time", "Inbound", "Arrival time",
        "Service Category", "Currency Code", "LSK FEE", "Base Fare Amount",
        "Tax Amount", "Total Amount", "Exchange Indicator",
        "Original Exchange TicketNo", "Refund Indicator", "Booking Agent ID",
        "Form of Payment", "Origin Code", "Destination", "PASSENGER ID", "Trip reason",
        "Travel Type", "Type Of Ttaveller", "COST CENTER", "Project Code",
        "Other Trip Reason", "Ref_Travel Type", "Project Manager Email",
        "Travel Booker email ID", "Apprrover Line Manager Name", "Business Unit",
        "Booked By"
    ]
    
    # كتابة رؤوس الأعمدة
    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.border = border
    
    # تعيين عرض الأعمدة
    for col_idx in range(1, len(headers) + 1):
        column_letter = openpyxl.utils.get_column_letter(col_idx)
        ws.column_dimensions[column_letter].width = 20
    
    # التحقق من وجود بيانات فندق
    hotel = data.get('hotel', {})
    has_hotel = hotel and hotel.get('hotel_name')
    
    # التحقق من وجود Flight Segments
    segments = data.get('segments', [])
    has_segments = segments and len(segments) > 0
    
    # ========== جمع البيانات الأساسية ==========
    invoice_number = data.get('invoice_number', '')
    business_unit = data.get('business_unit', '')
    invoice_date = data.get('invoice_date', '')
    booked_date = data.get('date_supply', '')
    passenger_name = data.get('passenger_name', '')
    
    # معالجة ticket_number كنص لمنع التحويل إلى صيغة علمية
    ticket_number_raw = data.get('ticket_number', '')
    if ticket_number_raw:
        ticket_number = str(ticket_number_raw).strip()
    else:
        ticket_number = ''
    
    booking_number = data.get('booking_number', '')
    employee_id = data.get('employee_id', '')
    cost_center = data.get('cost_center', '0')
    pm_email = data.get('pm_email', '')
    booker_email = data.get('booker_email', '')
    approver = data.get('approver', '')
    booked_by = data.get('booked_by', '')
    trip_reason_value = data.get('trip_reason', '')
    
    # الحقول المالية
    try:
        lsk_fee = float(data.get('lsk_fee', 0) or 0)
        base_fare = float(data.get('base_fare', 0) or 0)
        fare = float(data.get('fare', 0) or 0)
        total_amount = fare + lsk_fee
    except (ValueError, TypeError):
        fare = lsk_fee = base_fare = total_amount = 0
    
    # Client ID و Project Code
    client_id, project_code = get_client_id_and_project_code(business_unit)
    client_name = get_client_name(business_unit)
    
    # PAX First Name و PAX Last Name (مع التحقق من الأخطاء)
    try:
        pax_first_name, pax_last_name = get_pax_name_fields(passenger_name)
        # التحقق من صحة البيانات
        if not pax_first_name and not pax_last_name and passenger_name:
            pax_first_name = passenger_name
            pax_last_name = ""
    except Exception as e:
        print(f"Warning: Failed to parse passenger name '{passenger_name}': {str(e)}")
        pax_first_name = passenger_name if passenger_name else ""
        pax_last_name = ""
    
    # Trip Reason و Travel Type
    trip_reason, travel_type = parse_trip_reason(trip_reason_value)
    
    # Form of Payment
    form_of_payment = "AR"
    
    # Type Of Traveller
    type_of_traveller = "Project Traveller"
    
    row_num = 2  # بداية كتابة البيانات من الصف الثاني
    
    # دالة مساعدة لكتابة الخلايا مع تنسيق النص للأرقام الطويلة
    def write_cell(row, col, value, is_text_column=False):
        cell = ws.cell(row=row, column=col, value=value)
        cell.border = border
        cell.alignment = Alignment(horizontal='left', vertical='center')
        if is_text_column:
            cell.number_format = '@'
        return cell
    
    # قائمة بأرقام الأعمدة التي تحتوي على أرقام طويلة
    text_columns = {12, 27}
    
    # ========== حالة وجود فندق فقط (بدون رحلات طيران) ==========
    if has_hotel and not has_segments:
        booking_type = "HTL"
        hotel_name = hotel.get('hotel_name', '')
        dest_code = hotel.get('dest_code', '') or hotel.get('location', '')
        check_in = hotel.get('check_in', '')
        check_out = hotel.get('check_out', '')
        
        row_data = [
            invoice_number,                          # Record Key (1)
            "1",                                     # Sequence Number (2)
            client_id,                               # Client Id (3)
            client_name,                             # Client Name (4)
            invoice_date,                            # Invoice Date (5)
            booked_date,                             # Booked Date (6)
            "N",                                     # Void Ind (7)
            "MR",                                    # Salutation (8)
            pax_first_name,                          # PAX First Name (9)
            pax_last_name,                           # PAX Last Name (10)
            booking_type,                            # Booking Type (11)
            ticket_number,                           # Document Number (12) - نص
            booking_number,                          # Record Locator (PNR) (13)
            "HTL",                                   # Vendor Code (14)
            hotel_name,                              # Vendor Name (15)
            check_in,                                # Outbound (16)
            "",                                      # Depart Time (17)
            check_out,                               # Inbound (18)
            "",                                      # Arrival time (19)
            "",                                      # Service Category (20)
            "USD",                                   # Currency Code (21)
            str(lsk_fee),                            # LSK FEE (22)
            str(base_fare),                          # Base Fare Amount (23)
            "0",                                     # Tax Amount (24)
            str(total_amount),                       # Total Amount (25)
            "N",                                     # Exchange Indicator (26)
            ticket_number,                           # Original Exchange TicketNo (27) - نص
            "N",                                     # Refund Indicator (28)
            "LONDON SKY",                            # Booking Agent ID (29)
            form_of_payment,                         # Form of Payment (30)
            "",                                      # Origin Code (31)
            dest_code,                               # Destination (32)
            employee_id,                             # PASSENGER ID (33)
            trip_reason,                             # Trip reason (34)
            travel_type,                             # Travel Type (35)
            type_of_traveller,                       # Type Of Ttaveller (36)
            cost_center,                             # COST CENTER (37)
            project_code,                            # Project Code (38)
            "N/A",                                   # Other Trip Reason (39)
            "N/A",                                   # Ref_Travel Type (40)
            pm_email,                                # Project Manager Email (41)
            booker_email,                            # Travel Booker email ID (42)
            approver,                                # Apprrover Line Manager Name (43)
            business_unit,                           # Business Unit (44)
            booked_by                                # Booked By (45)
        ]
        
        for col_idx, value in enumerate(row_data, 1):
            cell = ws.cell(row=row_num, column=col_idx, value=value)
            cell.border = border
            cell.alignment = Alignment(horizontal='left', vertical='center')
            if col_idx in text_columns:
                cell.number_format = '@'
    
    # ========== حالة وجود رحلات طيران فقط (بدون فندق) ==========
    elif has_segments and not has_hotel:
        for seg_idx, seg in enumerate(segments):
            flight_code = seg.get('airline_code', '')
            vendor_code = get_vendor_code(flight_code[:2] if len(flight_code) >= 2 else flight_code)
            
            airline_names = {
                'EK': 'EMIRATES AIRWAYS',
                'QR': 'QATAR AIRWAYS',
                'TK': 'TURKISH AIRLINE',
                'RJ': 'ROYAL JORDINAIN',
                'FZ': 'FLY DUBAI',
                'G9': 'AIR ARABIA',
            }
            vendor_name = airline_names.get(vendor_code, flight_code)
            
            depart_date = seg.get('depart_date', '')
            depart_time = seg.get('depart_time', '')
            arrival_date = seg.get('arrival_date', '')
            arrival_time = seg.get('arrival_time', '')
            origin_code = seg.get('origin', '')
            dest_code = seg.get('destination', '')
            service_category = seg.get('class_name', 'Y')
            
            row_data = [
                invoice_number,
                '1',
                client_id,
                client_name,
                invoice_date,
                booked_date,
                "N",
                "MR",
                pax_first_name,
                pax_last_name,
                "AIR",
                ticket_number,
                booking_number,
                vendor_code,
                vendor_name,
                depart_date,
                depart_time,
                arrival_date,
                arrival_time,
                service_category,
                "USD",
                str(lsk_fee) if seg_idx == 0 else "0",
                str(base_fare) if seg_idx == 0 else "0",
                "0",
                str(total_amount) if seg_idx == 0 else "0",
                "N",
                ticket_number,
                "N",
                "LONDON SKY",
                form_of_payment,
                origin_code,
                dest_code,
                employee_id,
                trip_reason,
                travel_type,
                type_of_traveller,
                cost_center,
                project_code,
                "N/A",
                "N/A",
                pm_email,
                booker_email,
                approver,
                business_unit,
                booked_by
            ]
            
            current_row = row_num + seg_idx
            for col_idx, value in enumerate(row_data, 1):
                cell = ws.cell(row=current_row, column=col_idx, value=value)
                cell.border = border
                cell.alignment = Alignment(horizontal='left', vertical='center')
                if col_idx in text_columns:
                    cell.number_format = '@'
    
    # ========== حالة وجود فندق ورحلات طيران معاً ==========
    elif has_hotel and has_segments:
        # إضافة صفوف الطيران أولاً
        for seg_idx, seg in enumerate(segments):
            flight_code = seg.get('airline_code', '')
            vendor_code = get_vendor_code(flight_code[:2] if len(flight_code) >= 2 else flight_code)
            
            airline_names = {
                'EK': 'EMIRATES AIRWAYS',
                'QR': 'QATAR AIRWAYS',
                'TK': 'TURKISH AIRLINE',
                'RJ': 'ROYAL JORDINAIN',
                'FZ': 'FLY DUBAI',
                'G9': 'AIR ARABIA',
            }
            vendor_name = airline_names.get(vendor_code, flight_code)
            
            depart_date = seg.get('depart_date', '')
            depart_time = seg.get('depart_time', '')
            arrival_date = seg.get('arrival_date', '')
            arrival_time = seg.get('arrival_time', '')
            origin_code = seg.get('origin', '')
            dest_code = seg.get('destination', '')
            service_category = seg.get('class_name', 'Y')
            
            row_data = [
                invoice_number,
                '1',
                client_id,
                client_name,
                invoice_date,
                booked_date,
                "N",
                "MR",
                pax_first_name,
                pax_last_name,
                "AIR",
                ticket_number,
                booking_number,
                vendor_code,
                vendor_name,
                depart_date,
                depart_time,
                arrival_date,
                arrival_time,
                service_category,
                "USD",
                str(lsk_fee) if seg_idx == 0 else "0",
                str(base_fare) if seg_idx == 0 else "0",
                "0",
                str(total_amount) if seg_idx == 0 else "0",
                "N",
                ticket_number,
                "N",
                "LONDON SKY",
                form_of_payment,
                origin_code,
                dest_code,
                employee_id,
                trip_reason,
                travel_type,
                type_of_traveller,
                cost_center,
                project_code,
                "N/A",
                "N/A",
                pm_email,
                booker_email,
                approver,
                business_unit,
                booked_by
            ]
            
            current_row = row_num + seg_idx
            for col_idx, value in enumerate(row_data, 1):
                cell = ws.cell(row=current_row, column=col_idx, value=value)
                cell.border = border
                cell.alignment = Alignment(horizontal='left', vertical='center')
                if col_idx in text_columns:
                    cell.number_format = '@'
        
        # إضافة صف الفندق بعد صفوف الطيران
        hotel_name = hotel.get('hotel_name', '')
        dest_code = hotel.get('dest_code', '') or hotel.get('location', '')
        check_in = hotel.get('check_in', '')
        check_out = hotel.get('check_out', '')
        
        hotel_row_num = row_num + len(segments)
        
        hotel_row_data = [
            invoice_number,
            '1',
            client_id,
            client_name,
            invoice_date,
            booked_date,
            "N",
            "MR",
            pax_first_name,
            pax_last_name,
            "HTL",
            ticket_number,
            booking_number,
            "HTL",
            hotel_name,
            check_in,
            "",
            check_out,
            "",
            "",
            "USD",
            "0",
            "0",
            "0",
            "0",
            "N",
            ticket_number,
            "N",
            "LONDON SKY",
            form_of_payment,
            "",
            dest_code,
            employee_id,
            trip_reason,
            travel_type,
            type_of_traveller,
            cost_center,
            project_code,
            "N/A",
            "N/A",
            pm_email,
            booker_email,
            approver,
            business_unit,
            booked_by
        ]
        
        for col_idx, value in enumerate(hotel_row_data, 1):
            cell = ws.cell(row=hotel_row_num, column=col_idx, value=value)
            cell.border = border
            cell.alignment = Alignment(horizontal='left', vertical='center')
            if col_idx in text_columns:
                cell.number_format = '@'
    
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer

def create_segment_excel(data):
    """إنشاء ملف SEGMENT Excel حسب الحقول المطلوبة"""
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    
    header_font = Font(bold=True, size=11, color="FFFFFF")
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    # العناوين المطلوبة حسب الطلب الجديد
    headers = [
        "Record Key", "Sequence Number", "Leg", "Airline Code", "Depart City Code",
        "Depart Date", "Depart Time", "Flight Number", "Arrive City Code", "Arrive Date", "Arrive Time", "CLASS"
    ]
    
    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.border = border
    
    segments = data.get('segments', [])
    row_num = 2
    
    if not segments or len(segments) == 0:
        ws.cell(row=row_num, column=1, value="No flight segments added. Please click 'Add Flight Segment' button to add segments.")
        ws.merge_cells(start_row=row_num, start_column=1, end_row=row_num, end_column=len(headers))
    else:
        leg_counter = 1
        for seg in segments:
            # Airline Code: أول حرفين من Flight Code (airline_code)
            flight_code = str(seg.get('airline_code', ''))
            airline_code_first_two = flight_code[:2] if len(flight_code) >= 2 else flight_code
            
            # Flight Number: يتم إزالة أول حرفين (Airline Code) من قيمة Flight Number
            flight_number_full = str(seg.get('airline_code', ''))
            if len(flight_number_full) >= 2:
                flight_number_only = flight_code[2:]  # تخطي أول حرفين
            else:
                flight_number_only = flight_number_full
            
            row_data = [
                str(data.get('invoice_number', '')),  # Record Key: Invoice Number
                "1",                                   # Sequence Number: 1
                str(leg_counter),                      # Leg: 1,2,3...
                airline_code_first_two,                # Airline Code: أول حرفين من Flight Code
                str(seg.get('origin', '')),            # Depart City Code: Origin
                str(seg.get('depart_date', '')),       # Depart Date: Depart Date
                str(seg.get('depart_time', '')),       # Depart Time: Depart Time
                flight_number_only,                    # Flight Number: بعد إزالة أول حرفين
                str(seg.get('destination', '')),       # Arrive City Code: destination
                str(seg.get('arrival_date', '')),      # Arrive Date: Arrive Date
                str(seg.get('arrival_time', '')),      # Arrive Time: Arrive Time
                str(seg.get('class_name', 'Y'))        # CLASS: CLASS
            ]
            
            for col_idx, value in enumerate(row_data, 1):
                cell = ws.cell(row=row_num, column=col_idx, value=value)
                cell.border = border
                cell.alignment = Alignment(horizontal='left', vertical='center')
            
            row_num += 1
            leg_counter += 1
    
    # ضبط عرض الأعمدة
    for col_idx in range(1, len(headers) + 1):
        column_letter = openpyxl.utils.get_column_letter(col_idx)
        ws.column_dimensions[column_letter].width = 18
    
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer

@app.route('/send_email', methods=['POST'])
def send_email():
    try:
        data = request.json
        if data:
            data = clean_dict(data)
        else:
            data = {}
        
        # ========== التحقق من صحة البيانات قبل الإرسال ==========
        passenger_name = data.get('passenger_name', '')
        if not passenger_name:
            return jsonify({'success': False, 'message': '⚠️ الرجاء إدخال اسم الراكب (Passenger Name)'}), 400
        
        if '/' not in passenger_name:
            return jsonify({
                'success': False, 
                'message': '⚠️ صيغة اسم الراكب غير صحيحة!\n\nالرجاء استخدام الصيغة: الكنية/الاسم الأول\nمثال: MANSOURI/AHMED'
            }), 400
        
        recipient_email = data.get('recipient_email', '') or data.get('booker_email', '')
        
        if not recipient_email:
            return jsonify({'success': False, 'message': 'No email address provided'}), 400
        
        invoice_number = data.get('invoice_number', '')
        safe_filename = get_safe_filename(invoice_number)
        
        msg = MIMEMultipart()
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = recipient_email
        msg['Subject'] = f"Airline Ticket - Invoice {data.get('invoice_number', '')}"
        
        body = f"""
        Dear {data.get('passenger_name', 'Customer')},
        
        Please find attached your airline ticket invoice.
        
        Ticket Details:
        - Invoice Number: {data.get('invoice_number', '')}
        - Passenger: {data.get('passenger_name', '')}
        - Booking Number: {data.get('booking_number', '')}
        - Total Amount: {data.get('total', '0')} USD
        
        Attached files:
        1. Ticket PDF
        2. INVOICE Excel File
        3. SEGMENT Excel File
        
        Thank you for choosing our services.
        
        Best regards,
        Airline Team
        """
        msg.attach(MIMEText(body, 'plain'))
        
        pdf_data = generate_pdf_internal(data)
        pdf_attachment = MIMEBase('application', 'octet-stream')
        pdf_attachment.set_payload(pdf_data)
        encoders.encode_base64(pdf_attachment)
        pdf_attachment.add_header('Content-Disposition', 'attachment', filename=f"{safe_filename}_{datetime.now().hour}.pdf")
        msg.attach(pdf_attachment)
        
        if OPENPYXL_AVAILABLE:
            invoice_buffer = create_invoice_excel(data)
            invoice_attachment = MIMEBase('application', 'octet-stream')
            invoice_attachment.set_payload(invoice_buffer.getvalue())
            encoders.encode_base64(invoice_attachment)
            invoice_attachment.add_header('Content-Disposition', 'attachment', filename=f"{safe_filename}_INVOICE.xlsx")
            msg.attach(invoice_attachment)
            
            segment_buffer = create_segment_excel(data)
            segment_attachment = MIMEBase('application', 'octet-stream')
            segment_attachment.set_payload(segment_buffer.getvalue())
            encoders.encode_base64(segment_attachment)
            segment_attachment.add_header('Content-Disposition', 'attachment', filename=f"{safe_filename}_SEGMENT.xlsx")
            msg.attach(segment_attachment)
        
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)
        
        return jsonify({'success': True, 'message': 'Email sent successfully'})
    except Exception as e:
        print(f"Email Error: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'success': False, 'message': str(e)}), 500

def generate_pdf_internal(data):
    from io import BytesIO
    
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=8)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(190, 6, txt="AIRLINE TICKET", ln=True, align='C')
    pdf.ln(3)
    
    pdf.set_font("Arial", 'B', 9)
    pdf.cell(190, 5, txt="INVOICE DETAILS", ln=True)
    pdf.set_font("Arial", size=7)
    pdf.cell(45, 4, txt=f"Invoice Number: {data.get('invoice_number', '-')}", ln=True)
    pdf.cell(45, 4, txt=f"Invoice Date: {data.get('invoice_date', '-')}", ln=True)
    pdf.cell(45, 4, txt=f"Date of Issue: {data.get('date_supply', '-')}", ln=True)
    pdf.ln(2)
    
    pdf.set_font("Arial", 'B', 9)
    pdf.cell(190, 5, txt="PASSENGER & BOOKING", ln=True)
    pdf.set_font("Arial", size=7)
    pdf.cell(45, 4, txt=f"Passenger Name: {data.get('passenger_name', '-')} MR", ln=True)
    pdf.cell(45, 4, txt=f"Employee ID: {data.get('employee_id', '-')}", ln=True)
    pdf.cell(45, 4, txt=f"Business Unit: {data.get('business_unit', '-')}", ln=True)
    pdf.cell(45, 4, txt=f"Cost Center: {data.get('cost_center', '-')}", ln=True)
    pdf.cell(45, 4, txt=f"Trip Reason: {data.get('trip_reason', '-')}", ln=True)
    pdf.cell(45, 4, txt=f"Booking Number: {data.get('booking_number', '-')}", ln=True)
    pdf.ln(2)
    output = BytesIO()
    pdf.output(output)
    return output.getvalue()

if __name__ == '__main__':
    print("Server Starting.....")
    # serve(app, host='0.0.0.0', port=80)
    app.run(host='0.0.0.0', port=80)
