#! .venv/bin/python3
"""
醫師門診管理系統 - Flask 主程式
管理病患資料、用藥記錄、檢查項目等
"""

from flask import Flask, render_template, request, redirect, url_for, request as flask_request
from database import init_db, get_connection, validate_required_fields, safe_date, log_db_action, logger
from functools import wraps
from datetime import datetime, timedelta

# ===========================================================================
# 錯誤處理裝飾器
# ===========================================================================

def handle_errors(f):
    """通用錯誤處理裝飾器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except sqlite3.Error as e:
            print(f"[ database error ] {e}")
            return {"success": False, "message": "資料庫錯誤，請稍後再試"}, 500
        except Exception as e:
            print(f"[ error ] {e}")
            return {"success": False, "message": "發生錯誤，請稍後再試"}, 500
    return decorated_function


import sqlite3

# 初始化 Flask 應用
app = Flask(__name__)
app.jinja_env.add_extension('jinja2.ext.loopcontrols')

# 初始化資料庫
init_db()


# ===========================================================================
# 頁面路由 - 首頁與管理
# ===========================================================================

@app.route("/")
def home():
    """首頁 - 列出所有醫師"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM doctors ORDER BY id")
    doctors = cursor.fetchall()
    
    # 取得即將到期的回診提醒（3天內）
    today = datetime.now().strftime("%Y-%m-%d")
    three_days_later = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
    
    # 查詢所有病患的最新一筆記錄（先合併兩表，再取最新）
    cursor.execute("""
        SELECT 
            patient_id,
            name as medicine_name,
            followup_date,
            next_followup_date,
            type,
            remain_dose
        FROM (
            SELECT 
                patient_id,
                name,
                followup_date,
                next_followup_date,
                'traditional' as type,
                NULL as remain_dose
            FROM traditional_medicine_record
            UNION ALL
            SELECT 
                patient_id,
                name,
                followup_date,
                next_followup_date,
                'biological' as type,
                remain_dose
            FROM biological_medicine_record
        ) all_records
        ORDER BY followup_date DESC
    """)
    latest_records = cursor.fetchall()
    
    # 建立提醒資料（按病患分組，只取每個病患的第一筆記錄）
    patient_reminders = {}  # {patient_id: {patient_name, doctor_name, reminder_items, urgent_level}}
    processed_patients = set()  # 追蹤已處理的病患
    
    for record in latest_records:
        record_dict = dict(record)
        patient_id = record_dict['patient_id']
        
        # 跳過已處理過的病患（確保只取最新一筆記錄）
        if patient_id in processed_patients:
            continue
        processed_patients.add(patient_id)
        
        # 取得病患和醫師資訊
        cursor.execute("""
            SELECT p.name as patient_name, p.medical_record_number, p.status, d.name as doctor_name
            FROM patients p
            JOIN doctors d ON p.doctor_id = d.id
            WHERE p.id = ?
        """, (patient_id,))
        patient_info = cursor.fetchone()
        if patient_info:
            if patient_info["status"] == "下車":
                continue
            patient_reminders[patient_id] = {
                'patient_id': patient_id,
                'patient_name': patient_info['patient_name'],
                'medical_record_number': patient_info['medical_record_number'],
                'status': patient_info['status'],
                'doctor_name': patient_info['doctor_name'],
                'reminder_items': [],
                'urgent_level': 'yellow'
            }
        
        # 計算距離下次回診的天數
        days_left = (datetime.strptime(record_dict['next_followup_date'], '%Y-%m-%d') - datetime.now()).days if record_dict['next_followup_date'] else None
        
        # 檢查是否需要回診提醒（3天內）- 每病患只會有一個回診提醒
        if days_left is not None and days_left <= 3:
            patient_reminders[patient_id]['reminder_items'].append({
                'reminder_type': 'followup',
                'days_left': days_left,
                'next_followup_date': record_dict['next_followup_date']
            })
        
        # 檢查是否需要生物製劑針數不足提醒（<= 3 針）
        if record_dict['type'] == 'biological' and record_dict['remain_dose'] is not None and record_dict['remain_dose'] <= 3:
            patient_reminders[patient_id]['reminder_items'].append({
                'reminder_type': 'dose',
                'remain_dose': record_dict['remain_dose'],
                'medicine_name': record_dict['medicine_name']
            })
    
    # 計算緊急程度並排序
    reminders = []
    for patient_id, data in patient_reminders.items():
        # 如果沒有任何提醒項目，跳過
        if not data['reminder_items']:
            continue
            
        # 計算緊急程度
        max_urgent = 'yellow'
        for item in data['reminder_items']:
            # 回診 <= 1 天為紅燈
            if item['reminder_type'] == 'followup' and item['days_left'] <= 1:
                max_urgent = 'red'
                break
            # 針數為 0 為紅燈
            if item['reminder_type'] == 'dose' and item['remain_dose'] == 0:
                max_urgent = 'red'
                break
        
        data['urgent_level'] = max_urgent
        reminders.append(data)
    
    # 按緊急程度排序（紅燈優先）
    reminders.sort(key=lambda x: (0 if x['urgent_level'] == 'red' else 1))
    
    conn.close()
    return render_template("home.html", doctors=doctors, reminders=reminders)


@app.route("/management/doctors")
def management_doctors():
    """醫師管理頁面"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM doctors ORDER BY id")
    doctors = cursor.fetchall()
    conn.close()
    return render_template("management.html", type="doctors", items=doctors)


@app.route("/management/diseases")
def management_diseases():
    """疾病管理頁面"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM diseases ORDER BY id")
    diseases = cursor.fetchall()
    conn.close()
    return render_template("management.html", type="diseases", items=diseases)


@app.route("/management/examinations")
def management_examinations():
    """檢查項目管理頁面"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM examinations ORDER BY id")
    examinations = cursor.fetchall()
    conn.close()
    return render_template("management.html", type="examinations", items=examinations)


@app.route("/management/medicines")
def management_medicines():
    """藥物管理頁面"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM traditional_medicines ORDER BY id")
    traditional_medicines = cursor.fetchall()
    cursor.execute("SELECT * FROM biological_medicines ORDER BY id")
    biological_medicines = cursor.fetchall()
    conn.close()
    return render_template("management.html", type="medicines", items=traditional_medicines + biological_medicines)


@app.route("/pasi")
def pasi_score():
    """PASI分數試算頁面"""
    return render_template("pasi_score.html")


# ===========================================================================
# 頁面路由 - 醫師與病患
# ===========================================================================

@app.route("/doctor/<int:doctor_id>/disease/<int:disease_id>")
def doctor_patients(doctor_id, disease_id):
    """醫師的特定疾病病患列表頁面"""
    conn = get_connection()
    cursor = conn.cursor()

    # 取得該醫師該疾病的病患
    cursor.execute("SELECT * FROM patients WHERE doctor_id=? AND disease_id=? ORDER BY id", (doctor_id, disease_id))
    patients = cursor.fetchall()

    # 取得醫師資訊
    cursor.execute("SELECT * FROM doctors WHERE id=?", (doctor_id,))
    doctor = cursor.fetchone()

    # 取得疾病資訊
    cursor.execute("SELECT * FROM diseases WHERE id=?", (disease_id,))
    disease = cursor.fetchone()

    conn.close()
    return render_template("doctor_disease_patients.html", doctor=doctor, disease=disease, patients=patients)


@app.route("/doctor/<int:doctor_id>")
def doctor(doctor_id):
    """醫師詳細頁面 - 顯示該醫師負責的所有疾病"""
    conn = get_connection()
    cursor = conn.cursor()

    # 取得所有疾病
    cursor.execute("SELECT * FROM diseases ORDER BY id")
    diseases = cursor.fetchall()

    # 取得醫師資訊
    cursor.execute("SELECT * FROM doctors WHERE id=?", (doctor_id,))
    doctor = cursor.fetchone()

    conn.close()

    if doctor is None:
        return "醫師不存在", 404

    return render_template("doctor.html", doctor=doctor, diseases=diseases)


@app.route("/patient/<int:patient_id>")
def patient_detail(patient_id):
    """病患詳細資料頁面"""
    conn = get_connection()
    cursor = conn.cursor()

    # 取得病患基本資訊
    cursor.execute("SELECT * FROM patients WHERE id = ?", (patient_id,))
    patient_row = cursor.fetchone()
    if patient_row is None:
        conn.close()
        return "病人不存在", 404
    patient = dict(patient_row)
    
    # 安全解析生日
    birthday = safe_date(patient.get("birthday"))
    if birthday:
        patient["birthday"] = birthday

    # 計算年齡（格式：X歲Y個月Z天）
    if patient and patient['birthday']:
        try:
            birth_date = datetime.strptime(patient['birthday'], '%Y-%m-%d')
            today = datetime.now()
            
            # 計算年、月、日
            years = today.year - birth_date.year
            months = today.month - birth_date.month
            days = today.day - birth_date.day
            
            # 處理負的天數
            if days < 0:
                months -= 1
                # 取得上個月的最後一天
                import calendar
                last_month = today.month - 1 if today.month > 1 else 12
                year_for_month = today.year if today.month > 1 else today.year - 1
                days += calendar.monthrange(year_for_month, last_month)[1]
            
            # 處理負的月數
            if months < 0:
                years -= 1
                months += 12
            
            # 格式化年齡字串
            if years > 0:
                if months > 0 or days > 0:
                    patient['age'] = f"{years}歲 {months}個月 {days}天"
                else:
                    patient['age'] = f"{years}歲"
            elif months > 0:
                if days > 0:
                    patient['age'] = f"{months}個月 {days}天"
                else:
                    patient['age'] = f"{months}個月"
            else:
                patient['age'] = f"{days}天"
        except Exception:
            pass

    # 取得負責醫師名稱
    cursor.execute("SELECT * FROM doctors WHERE id = ?", (patient['doctor_id'],))
    doctor = cursor.fetchone()
    patient["doctor_name"] = doctor["name"] if doctor else "-"

    # 取得疾病名稱
    cursor.execute("SELECT * FROM diseases WHERE id = ?", (patient['disease_id'],))
    disease = cursor.fetchone()
    patient["disease_name"] = disease["name"] if disease else "-"

    # 取得最新傳統用藥記錄
    cursor.execute("""
        SELECT *
        FROM traditional_medicine_record
        WHERE patient_id = ?
        ORDER BY id DESC
    """, (patient_id,))
    traditional_medicine_record = cursor.fetchall()

    if traditional_medicine_record:
        last_traditional_medicine_record = dict(traditional_medicine_record[0])
        last_traditional_medicine_record["type"] = "traditional"
    else:
        last_traditional_medicine_record = None

    # 取得最新生物製劑記錄
    cursor.execute("""
        SELECT *
        FROM biological_medicine_record
        WHERE patient_id = ?
        ORDER BY id DESC
    """, (patient_id,))
    biological_medicine_record = cursor.fetchall()

    if biological_medicine_record:
        last_biological_medicine_record = dict(biological_medicine_record[0])
        last_biological_medicine_record["type"] = "biological"
    else:
        last_biological_medicine_record = None

    # 比較回診日期，決定要顯示哪一個
    last_traditional_medicine_record_date = datetime.strptime(
        last_traditional_medicine_record["followup_date"], '%Y-%m-%d') if last_traditional_medicine_record else None
    last_biological_medicine_record_date = datetime.strptime(
        last_biological_medicine_record["followup_date"], '%Y-%m-%d') if last_biological_medicine_record else None

    if last_traditional_medicine_record_date and last_biological_medicine_record_date:
        if last_traditional_medicine_record_date > last_biological_medicine_record_date:
            last_medicine_record = last_traditional_medicine_record
            cursor.execute("SELECT * FROM traditional_medicine_record WHERE record_id = ? AND patient_id = ? ORDER BY id DESC",
                          (last_medicine_record["record_id"], patient_id))
            medicine_record = cursor.fetchall()
        else:
            last_medicine_record = last_biological_medicine_record
            cursor.execute("SELECT * FROM biological_medicine_record WHERE record_id = ? AND patient_id = ? ORDER BY id DESC",
                          (last_medicine_record["record_id"], patient_id))
            medicine_record = cursor.fetchall()
    elif last_traditional_medicine_record_date:
        last_medicine_record = last_traditional_medicine_record
        cursor.execute("SELECT * FROM traditional_medicine_record WHERE record_id = ? AND patient_id = ? ORDER BY id DESC",
                       (last_medicine_record["record_id"], patient_id))
        medicine_record = cursor.fetchall()
    elif last_biological_medicine_record_date:
        last_medicine_record = last_biological_medicine_record
        cursor.execute("SELECT * FROM biological_medicine_record WHERE record_id = ? AND patient_id = ? ORDER BY id DESC",
                      (last_medicine_record["record_id"], patient_id))
        medicine_record = cursor.fetchall()
    else:
        last_medicine_record = None
        medicine_record = None

    # 取得檢查項目列表
    cursor.execute("SELECT * FROM examinations WHERE disable IS NULL OR disable = 0")
    examinations = cursor.fetchall()

    # 取得病患的檢查記錄
    cursor.execute("""
        SELECT *
        FROM examination_record
        WHERE patient_id = ?
        ORDER BY check_date DESC
    """, (patient_id,))
    examination_record = cursor.fetchall()

    # 將檢查記錄依項目名稱分組
    examination_record_dict = {}
    for record in examination_record:
        examination_record_dict.setdefault(record["name"], [])
        examination_record_dict[record["name"]].append(record)

    # 取得所有藥物列表（用於表單）
    cursor.execute("SELECT * FROM traditional_medicines ORDER BY id")
    traditional_medicines = cursor.fetchall()

    cursor.execute("SELECT * FROM biological_medicines ORDER BY id")
    biological_medicines = cursor.fetchall()

    conn.close()

    if patient is None:
        return "病人不存在", 404

    return render_template("patient_detail.html",
                           patient=patient,
                           last_medicine_record=last_medicine_record,
                           medicine_record=medicine_record,
                           examination_record=examination_record,
                           examination_record_dict=examination_record_dict,
                           examinations=examinations,
                           biological_medicines=biological_medicines,
                           traditional_medicines=traditional_medicines)


@app.route("/history/examination/<int:patient_id>")
def all_examination_record(patient_id):
    """病患檢查歷史紀錄頁面"""
    conn = get_connection()
    cursor = conn.cursor()

    # 取得病患資訊
    cursor.execute("SELECT * FROM patients WHERE id = ?", (patient_id,))
    patient = cursor.fetchone()

    # 取得檢查歷史記錄
    cursor.execute("""
        SELECT * FROM examination_record
        WHERE patient_id = ?
        ORDER BY check_date DESC, id DESC
    """, (patient_id,))
    examination_history = cursor.fetchall()

    conn.close()
    return render_template("examination_history.html", patient=patient, examination_history=examination_history)


@app.route("/history/medicine/<int:patient_id>")
def all_medicine_record(patient_id):
    """病患用藥歷史紀錄頁面"""
    conn = get_connection()
    cursor = conn.cursor()

    # 取得病患資訊
    cursor.execute("SELECT * FROM patients WHERE id = ?", (patient_id,))
    patient = cursor.fetchone()

    # 取得傳統用藥記錄
    cursor.execute("SELECT * FROM traditional_medicine_record WHERE patient_id = ? ORDER BY id ASC", (patient_id,))
    traditional_medicine_record = cursor.fetchall()

    # 取得生物製劑記錄
    cursor.execute("SELECT * FROM biological_medicine_record WHERE patient_id = ? ORDER BY id ASC", (patient_id,))
    biological_medicine_record = cursor.fetchall()

    # 合併並依日期排序
    history = []
    trad = dict(traditional_medicine_record.pop()) if traditional_medicine_record else None
    bio = dict(biological_medicine_record.pop()) if biological_medicine_record else None

    while trad or bio:
        trad_date = datetime.strptime(trad["followup_date"], '%Y-%m-%d') if trad else datetime(1911, 1, 1)
        bio_date = datetime.strptime(bio["followup_date"], '%Y-%m-%d') if bio else datetime(1911, 1, 1)
        if trad_date > bio_date:
            trad["type"] = "traditional"
            history.append(trad)
            trad = dict(traditional_medicine_record.pop()) if traditional_medicine_record else None
        else:
            bio["type"] = "biological"
            history.append(bio)
            bio = dict(biological_medicine_record.pop()) if biological_medicine_record else None

    conn.close()
    return render_template("history.html", patient=patient, history=history)


@app.route("/add_patient", methods=["GET", "POST"])
def add_patient():
    """新增病患頁面"""
    doctor_id = request.args.get("doctor_id")
    disease_id = request.args.get("disease_id")
    conn = get_connection()
    cursor = conn.cursor()

    # 取得醫師列表
    cursor.execute("SELECT * FROM doctors ORDER BY id")
    doctors = cursor.fetchall()

    # 取得疾病列表
    cursor.execute("SELECT * FROM diseases ORDER BY id")
    diseases = cursor.fetchall()

    if request.method == "POST":
        data = request.form
        name = data["name"]
        id_number = data["id_number"]
        gender = data["gender"]
        birthday = datetime.strptime(data["birthday"].replace("/", "-"), "%Y-%m-%d").strftime("%Y-%m-%d")
        medical_record_number = data["medical_record_number"]
        doctor_id = data["doctor_id"]
        disease_id = data["disease_id"]
        phone = data["phone"]
        mobile = data["mobile"]
        city = data["city"]
        district = data["district"]
        address = data["address"]
        status = data["status"]
        remark = data.get("remark", "")

        # 檢查病患是否已存在
        cursor.execute("SELECT id FROM patients WHERE id_number = ?", (id_number,))
        exists = cursor.fetchone() is not None
        if exists:
            return render_template("add_patient.html",
                                   doctors=doctors,
                                   diseases=diseases,
                                   doctor_id=int(doctor_id) if doctor_id else None,
                                   disease_id=int(disease_id) if disease_id else None,
                                   error="此病人已經存在資料庫中")

        # 新增病患資料
        new_patient_data = {
            "name": name, "gender": gender, "birthday": birthday, "phone": phone, 
            "mobile": mobile, "medical_record_number": medical_record_number, 
            "id_number": id_number, "city": city, "district": district, "address": address,
            "doctor_id": doctor_id, "disease_id": disease_id, "status": status, "remark": remark
        }
        cursor.execute("""INSERT INTO patients
        (name, gender, birthday, phone, mobile, medical_record_number, id_number, city, district, address, doctor_id, disease_id, status, remark) VALUES
        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                      (name, gender, birthday, phone, mobile, medical_record_number, id_number, city, district, address, doctor_id, disease_id, status, remark))
        record_id = cursor.lastrowid
        new_patient_data["id"] = record_id
        conn.commit()
        
        # 記錄審計日誌
        log_db_action(
            cursor,
            action="INSERT",
            table_name="patients",
            record_id=record_id,
            old_data=None,
            new_data=new_patient_data,
            sql_statement="INSERT INTO patients ...",
            operator="web",
            ip_address=flask_request.remote_addr
        )
        conn.commit()

        # 取得醫師、疾病與病患列表
        cursor.execute("SELECT * FROM doctors WHERE id = ?", (doctor_id,))
        doctor = cursor.fetchone()

        cursor.execute("SELECT * FROM diseases WHERE id = ?", (disease_id,))
        disease = cursor.fetchone()

        cursor.execute("SELECT * FROM patients WHERE doctor_id = ? AND disease_id = ? ORDER BY id", (doctor_id, disease_id))
        patients = cursor.fetchall()

        return render_template("doctor_disease_patients.html", doctor=doctor, disease=disease, patients=patients)

    conn.close()
    return render_template("add_patient.html",
                           doctors=doctors,
                           diseases=diseases,
                           doctor_id=int(doctor_id) if doctor_id else None,
                           disease_id=int(disease_id) if disease_id else None)


# ===========================================================================
# API 路由 - 新增操作
# ===========================================================================

@app.route("/api/add/doctors", methods=["POST"])
def api_add_doctors():
    """新增醫師 API"""
    data = request.get_json()
    name = data.get("inputName")
    
    # 必填欄位驗證
    if not name or not name.strip():
        return {"success": False, "message": "請輸入醫師名稱"}, 400

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("INSERT INTO doctors (name) VALUES (?)", (name.strip(),))
    record_id = cursor.lastrowid
    conn.commit()
    
    # 記錄審計日誌
    log_db_action(
        cursor,
        action="INSERT",
        table_name="doctors",
        record_id=record_id,
        old_data=None,
        new_data={"id": record_id, "name": name.strip()},
        sql_statement=f"INSERT INTO doctors (name) VALUES ('{name.strip()}')",
        operator="api",
        ip_address=flask_request.remote_addr
    )
    conn.commit()
    conn.close()

    logger.info(f"新增醫師: id={record_id}, name={name}")
    return {"success": True}


@app.route("/api/add/diseases", methods=["POST"])
def api_add_diseases():
    """新增疾病 API"""
    data = request.get_json()
    name = data.get("inputName")
    
    # 必填欄位驗證
    if not name or not name.strip():
        return {"success": False, "message": "請輸入疾病名稱"}, 400

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("INSERT INTO diseases (name) VALUES (?)", (name.strip(),))
    record_id = cursor.lastrowid
    conn.commit()
    
    # 記錄審計日誌
    log_db_action(
        cursor,
        action="INSERT",
        table_name="diseases",
        record_id=record_id,
        old_data=None,
        new_data={"id": record_id, "name": name.strip()},
        sql_statement=f"INSERT INTO diseases (name) VALUES ('{name.strip()}')",
        operator="api",
        ip_address=flask_request.remote_addr
    )
    conn.commit()
    conn.close()

    logger.info(f"新增疾病: id={record_id}, name={name}")
    return {"success": True}


@app.route("/api/add/examinations", methods=["POST"])
def api_add_examinations():
    """新增檢查項目 API"""
    data = request.get_json()
    name = data.get("inputName")
    interval = data.get("inputInterval")
    
    # 必填欄位驗證
    if not name or not name.strip():
        return {"success": False, "message": "請輸入檢查項目名稱"}, 400
    if not interval or not interval.strip():
        return {"success": False, "message": "請輸入檢查間隔週數"}, 400
    try:
        interval_int = int(interval)
        if interval_int <= 0:
            return {"success": False, "message": "檢查間隔必須大於0"}, 400
    except ValueError:
        return {"success": False, "message": "檢查間隔必須為數字"}, 400

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("INSERT INTO examinations (name, interval) VALUES (?, ?)", (name.strip(), interval_int))
    record_id = cursor.lastrowid
    conn.commit()
    
    # 記錄審計日誌
    log_db_action(
        cursor,
        action="INSERT",
        table_name="examinations",
        record_id=record_id,
        old_data=None,
        new_data={"id": record_id, "name": name.strip(), "interval": interval_int},
        sql_statement=f"INSERT INTO examinations (name, interval) VALUES ('{name.strip()}', {interval_int})",
        operator="api",
        ip_address=flask_request.remote_addr
    )
    conn.commit()
    conn.close()

    logger.info(f"新增檢查項目: id={record_id}, name={name}")
    return {"success": True}


@app.route("/api/add/medicines", methods=["POST"])
def api_add_medicines():
    """新增藥物 API"""
    data = request.get_json()
    name = data.get("inputName")
    mtype = data.get("selectMedicineType")
    followup_interval = data.get("inputInterval")
    first_apply_dose = data.get("firstApplyDose")
    continue_apply_dose = data.get("continueApplyDose")

    # 必填欄位驗證
    if not name or not name.strip():
        return {"success": False, "message": "請輸入藥物名稱"}, 400
    if not mtype:
        return {"success": False, "message": "請選擇藥物類型"}, 400
    
    # 類型驗證 - 使用白名單
    if mtype not in ("傳統用藥", "生物製劑"):
        return {"success": False, "message": "無效的藥物類型"}, 400

    conn = get_connection()
    cursor = conn.cursor()

    if mtype == "傳統用藥":
        if not followup_interval or not followup_interval.strip():
            conn.close()
            return {"success": False, "message": "請輸入回診間隔週數"}, 400
        try:
            interval_int = int(followup_interval)
        except ValueError:
            conn.close()
            return {"success": False, "message": "回診間隔必須為數字"}, 400
        cursor.execute("INSERT INTO traditional_medicines (name, followup_interval, type) VALUES (?, ?, ?)",
                      (name.strip(), interval_int, mtype))
        record_id = cursor.lastrowid
        table_name = "traditional_medicines"
        new_data = {"id": record_id, "name": name.strip(), "followup_interval": interval_int, "type": mtype}
    elif mtype == "生物製劑":
        if not first_apply_dose or not continue_apply_dose:
            conn.close()
            return {"success": False, "message": "請輸入申請針數"}, 400
        try:
            first_dose = int(first_apply_dose)
            continue_dose = int(continue_apply_dose)
        except ValueError:
            conn.close()
            return {"success": False, "message": "申請針數必須為數字"}, 400
        cursor.execute("INSERT INTO biological_medicines (name, first_apply_dose, continue_apply_dose, type) VALUES (?, ?, ?, ?)",
                      (name.strip(), first_dose, continue_dose, mtype))
        record_id = cursor.lastrowid
        table_name = "biological_medicines"
        new_data = {"id": record_id, "name": name.strip(), "first_apply_dose": first_dose, "continue_apply_dose": continue_dose, "type": mtype}

    conn.commit()
    
    # 記錄審計日誌
    log_db_action(
        cursor,
        action="INSERT",
        table_name=table_name,
        record_id=record_id,
        old_data=None,
        new_data=new_data,
        sql_statement=f"INSERT INTO {table_name} ...",  # 簡化 SQL
        operator="api",
        ip_address=flask_request.remote_addr
    )
    conn.commit()
    conn.close()

    logger.info(f"新增藥物: table={table_name}, id={record_id}, name={name}")
    return {"success": True}


@app.route("/api/add/medicine_record", methods=["POST"])
def api_add_medicine_record():
    """新增用藥記錄 API"""
    data = request.form
    patient_id = data.get("patient-id")
    medicine_name = data.get("medicine-name")
    medicine_type = data.get("medicine-type")
    apply_type = data.get("apply-type")
    last_followup_date = data.get("last-followup-date")
    next_followup_date = data.get("next-followup-date")
    dose = data.get("dose")
    remark = data.get("remark")
    additional_medicine = data.get("additional-medicine")

    conn = get_connection()
    cursor = conn.cursor()

    # 檢查病患是否存在
    cursor.execute("SELECT id FROM patients WHERE id = ?", (patient_id,))
    if cursor.fetchone() is None:
        conn.close()
        return {"success": False, "message": "病人不存在"}

    # 檢查是否有現有記錄，否則建立新的 record_id
    cursor.execute("SELECT record_id FROM traditional_medicine_record WHERE patient_id = ? ORDER BY id DESC", (patient_id,))
    last_traditional_record = cursor.fetchone()

    cursor.execute("SELECT record_id FROM biological_medicine_record WHERE patient_id = ? ORDER BY id DESC", (patient_id,))
    last_biological_record = cursor.fetchone()

    last_record_id = max(
        last_traditional_record["record_id"] if last_traditional_record else 0,
        last_biological_record["record_id"] if last_biological_record else 0
    )
    record_id = last_record_id + 1

    table_name = ""
    new_data = {}
    if medicine_type == "traditional":
        cursor.execute("""
            INSERT INTO traditional_medicine_record (record_id, patient_id, name, followup_date, next_followup_date, remark, additional_medicine)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (record_id, patient_id, medicine_name, last_followup_date, next_followup_date, remark, additional_medicine or ""))
        table_name = "traditional_medicine_record"
        new_data = {"record_id": record_id, "patient_id": patient_id, "name": medicine_name, 
                   "followup_date": last_followup_date, "next_followup_date": next_followup_date, "remark": remark, "additional_medicine": additional_medicine or ""}

    elif medicine_type == "biological":
        # 取得初始針數 - 使用白名單驗證欄位名稱
        if apply_type not in ("first", "continue"):
            conn.close()
            return {"success": False, "message": "無效的申請類型"}
        apply_column = "first_apply_dose" if apply_type == "first" else "continue_apply_dose"
        cursor.execute(f"SELECT {apply_column} AS apply_dose FROM biological_medicines WHERE name = ?", (medicine_name,))
        biological_medicine = cursor.fetchone()
        
        if biological_medicine is None:
            conn.close()
            return {"success": False, "message": "找不到指定的藥物"}

        cursor.execute("""
            INSERT INTO biological_medicine_record (record_id, patient_id, name, apply_type, remain_dose, followup_date, next_followup_date, remark, additional_medicine)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (record_id, patient_id, medicine_name, apply_type, biological_medicine["apply_dose"], last_followup_date, next_followup_date, remark, additional_medicine or ""))
        table_name = "biological_medicine_record"
        new_data = {"record_id": record_id, "patient_id": patient_id, "name": medicine_name,
                   "apply_type": apply_type, "remain_dose": biological_medicine["apply_dose"],
                   "followup_date": last_followup_date, "next_followup_date": next_followup_date, "remark": remark, "additional_medicine": additional_medicine or ""}

    record_id_db = cursor.lastrowid
    new_data["id"] = record_id_db
    conn.commit()
    
    # 記錄審計日誌
    log_db_action(
        cursor,
        action="INSERT",
        table_name=table_name,
        record_id=record_id_db,
        old_data=None,
        new_data=new_data,
        sql_statement=f"INSERT INTO {table_name} ...",
        operator="api",
        ip_address=flask_request.remote_addr
    )
    conn.commit()
    conn.close()
    return {"success": True}


@app.route("/api/add/followup_record", methods=["POST"])
def api_add_followup_record():
    """新增回診記錄 API"""
    data = request.form
    patient_id = data.get("patient-id")
    record_id = data.get("record-id")
    name = data.get("name")
    followup_date = data.get("followup-date")
    next_followup_date = data.get("next-followup-date")
    remark = data.get("remark")
    medicine_type = data.get("medicine-type")
    remain_dose = data.get("remain-dose")
    additional_medicine = data.get("additional-medicine")

    # 必填欄位驗證
    if not all([patient_id, record_id, name, followup_date, next_followup_date, medicine_type]):
        return {"success": False, "message": "缺少必要欄位"}, 400
    
    # 類型驗證 - 使用白名單防止 SQL 注入
    if medicine_type not in ("biological", "traditional"):
        return {"success": False, "message": "無效的藥物類型"}, 400

    conn = get_connection()
    cursor = conn.cursor()

    table_name = ""
    new_data = {}
    if medicine_type == "biological":
        cursor.execute("""
            INSERT INTO biological_medicine_record (record_id, patient_id, name, remain_dose, followup_date, next_followup_date, remark, additional_medicine)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (record_id, patient_id, name, remain_dose, followup_date, next_followup_date, remark or "", additional_medicine or ""))
        table_name = "biological_medicine_record"
        new_data = {"record_id": record_id, "patient_id": patient_id, "name": name,
                   "remain_dose": remain_dose, "followup_date": followup_date, 
                   "next_followup_date": next_followup_date, "remark": remark or "", "additional_medicine": additional_medicine or ""}
    else:
        cursor.execute("""
            INSERT INTO traditional_medicine_record (record_id, patient_id, name, followup_date, next_followup_date, remark, additional_medicine)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (record_id, patient_id, name, followup_date, next_followup_date, remark or "", additional_medicine or ""))
        table_name = "traditional_medicine_record"
        new_data = {"record_id": record_id, "patient_id": patient_id, "name": name,
                   "followup_date": followup_date, "next_followup_date": next_followup_date, "remark": remark or "", "additional_medicine": additional_medicine or ""}

    record_id_db = cursor.lastrowid
    new_data["id"] = record_id_db
    conn.commit()
    
    # 記錄審計日誌
    log_db_action(
        cursor,
        action="INSERT",
        table_name=table_name,
        record_id=record_id_db,
        old_data=None,
        new_data=new_data,
        sql_statement=f"INSERT INTO {table_name} ...",
        operator="api",
        ip_address=flask_request.remote_addr
    )
    conn.commit()
    conn.close()
    return {"success": True}


@app.route("/api/add/exam_record", methods=["POST"])
def api_add_exam_record():
    """新增檢查記錄 API"""
    form = request.form
    exam_date = form.get("exam-date")
    exam_result = form.get("exam-result")
    exam_remark = form.get("exam-remark")
    exam_name = form.get("exam-name")
    patient_id = form.get("patient-id")

    # 必填欄位驗證
    if not exam_date:
        return {"success": False, "message": "請選擇檢查日期"}, 400
    if not exam_result:
        return {"success": False, "message": "請選擇檢查結果"}, 400
    if not exam_name:
        return {"success": False, "message": "檢查項目名稱錯誤"}, 400
    if not patient_id:
        return {"success": False, "message": "病患ID錯誤"}, 400

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO examination_record (patient_id, name, check_date, result, remark)
        VALUES (?, ?, ?, ?, ?)
    """, (patient_id, exam_name, exam_date, exam_result, exam_remark or ""))
    record_id = cursor.lastrowid
    new_data = {"patient_id": patient_id, "name": exam_name, "check_date": exam_date,
                "result": exam_result, "remark": exam_remark or ""}
    new_data["id"] = record_id
    conn.commit()
    
    # 記錄審計日誌
    log_db_action(
        cursor,
        action="INSERT",
        table_name="examination_record",
        record_id=record_id,
        old_data=None,
        new_data=new_data,
        sql_statement=f"INSERT INTO examination_record ...",
        operator="api",
        ip_address=flask_request.remote_addr
    )
    conn.commit()
    conn.close()

    return {"success": True}, 200


# ===========================================================================
# API 路由 - 查詢操作
# ===========================================================================

@app.route("/api/get/medicine_intervals", methods=["POST"])
def api_get_medicine_intervals():
    """取得藥物回診間隔 API"""
    conn = get_connection()
    cursor = conn.cursor()
    medicine_name = request.get_json().get("medicine_name")
    if not medicine_name:
        conn.close()
        return {"success": False, "message": "請提供藥物名稱"}, 400
    
    cursor.execute("SELECT followup_interval FROM traditional_medicines WHERE name = ?",
                   (medicine_name,))
    traditional_medicine = cursor.fetchone()
    conn.close()
    
    if traditional_medicine is None:
        return {"success": False, "message": "找不到指定的藥物"}, 404
    return {"success": True, "intervals": traditional_medicine["followup_interval"]}

@app.route("/api/get/dose_count", methods=["POST"])
def api_get_dose_count():
    data = request.get_json()
    medicine_name = data.get("medicineName")
    apply_type = data.get("applyType")
    conn = get_connection()
    cursor = conn.cursor()
    if not medicine_name or apply_type not in ("first", "continue"):
        conn.close()
        return {"success": False, "message": "請提供藥物名稱"}, 400
    if apply_type == "first":
        column = "first_apply_dose"
    else:
        column = "continue_apply_dose"
    cursor.execute("SELECT {column} FROM biological_medicines WHERE name = ?".format(column=column), (medicine_name,))
    dose_count = cursor.fetchone()
    return {"success": True, "dose_count": dose_count[column]}

# ===========================================================================
# API 路由 - 更新操作
# ===========================================================================

@app.route("/api/update/patient_info", methods=["POST"])
def api_update_patient_info():
    """更新病患資訊 API"""
    data = request.form
    patient_id = data.get("patient_id")
    name = data.get("name")
    birthday = data.get("birthday")
    phone = data.get("phone")
    mobile = data.get("mobile")
    medical_record_number = data.get("medical_record_number")
    id_number = data.get("id_number")
    city = data.get("city")
    district = data.get("district")
    address = data.get("address")
    doctor = data.get("doctor")
    disease = data.get("disease")
    status = data.get("status")
    remark = data.get("remark")

    # 必填欄位驗證
    if not patient_id:
        return {"success": False, "message": "缺少病患ID"}, 400

    conn = get_connection()
    cursor = conn.cursor()

    # 取得舊資料
    cursor.execute("SELECT * FROM patients WHERE id = ?", (patient_id,))
    patient_row = cursor.fetchone()
    if patient_row is None:
        conn.close()
        return {"success": False, "message": "找不到病患"}, 404
    old_data = dict(patient_row)

    # 取得醫師 ID
    cursor.execute("SELECT * FROM doctors WHERE name = ?", (doctor,))
    doctor_row = cursor.fetchone()
    if doctor_row is None:
        conn.close()
        return {"success": False, "message": "找不到指定的醫師"}, 404
    doctor_id = doctor_row["id"]

    # 取得疾病 ID
    cursor.execute("SELECT * FROM diseases WHERE name = ?", (disease,))
    disease_row = cursor.fetchone()
    if disease_row is None:
        conn.close()
        return {"success": False, "message": "找不到指定的疾病"}, 404
    disease_id = disease_row["id"]

    # 安全解析生日
    birthday_formatted = safe_date(birthday) if birthday else None

    # 準備新資料
    new_data = {
        "id": patient_id, "name": name, "birthday": birthday_formatted, "phone": phone, "mobile": mobile,
        "medical_record_number": medical_record_number, "id_number": id_number, "city": city,
        "district": district, "address": address, "doctor_id": doctor_id, "disease_id": disease_id, "status": status, "remark": remark
    }

    # 更新病患資料
    cursor.execute("""
        UPDATE patients
        SET name = ?, birthday = ?, phone = ?, mobile = ?, medical_record_number = ?, id_number = ?,
            city = ?, district = ?, address = ?, doctor_id = ?, disease_id = ?, status = ?, remark = ?
        WHERE id = ?
    """, (name, birthday_formatted, phone, mobile, medical_record_number, id_number, city, district, address,
          doctor_id, disease_id, status, remark, patient_id))
    conn.commit()
    
    # 記錄審計日誌
    log_db_action(
        cursor,
        action="UPDATE",
        table_name="patients",
        record_id=patient_id,
        old_data=old_data,
        new_data=new_data,
        sql_statement=f"UPDATE patients WHERE id = {patient_id}",
        operator="api",
        ip_address=flask_request.remote_addr
    )
    conn.commit()
    conn.close()
    return {"success": True}


@app.route("/api/update/history", methods=["POST"])
def api_update_history():
    """更新用藥歷史記錄 API"""
    data = request.form
    record_id = data.get("record_id")
    patient_id = data.get("patient_id")
    id_ = data.get("id")
    type_ = data.get("type")
    followup_date = data.get("followup_date")
    remain_dose = data.get("remain_dose")
    remark = data.get("remark")

    conn = get_connection()
    cursor = conn.cursor()

    table_name = "traditional_medicine_record" if type_ != "biological" else "biological_medicine_record"
    
    # 取得舊資料
    cursor.execute(f"SELECT * FROM {table_name} WHERE id = ? AND patient_id = ? AND record_id = ?", (id_, patient_id, record_id))
    old_data_row = cursor.fetchone()
    print(id_, patient_id, record_id)
    if old_data_row is None:
        conn.close()
        return {"success": False, "message": "找不到記錄"}, 404
    old_data = dict(old_data_row)

    # 準備新資料
    new_data = dict(old_data)
    if type_ == "biological":
        new_data["remain_dose"] = remain_dose
    new_data["followup_date"] = followup_date
    new_data["remark"] = remark

    # 執行更新
    if type_ == "biological":
        query = "UPDATE biological_medicine_record SET followup_date = ?, remain_dose = ?, remark = ? WHERE id = ? AND patient_id = ? AND record_id = ?"
        cursor.execute(query, (followup_date, remain_dose, remark, id_, patient_id, record_id))
    else:
        query = "UPDATE traditional_medicine_record SET followup_date = ?, remark = ? WHERE id = ? AND patient_id = ? AND record_id = ?"
        cursor.execute(query, (followup_date, remark, id_, patient_id, record_id))

    conn.commit()
    
    # 記錄審計日誌
    log_db_action(
        cursor,
        action="UPDATE",
        table_name=table_name,
        record_id=id_,
        old_data=old_data,
        new_data=new_data,
        sql_statement=f"UPDATE {table_name} WHERE id = {id_}",
        operator="api",
        ip_address=flask_request.remote_addr
    )
    conn.commit()
    conn.close()
    return {"success": True}


@app.route("/api/update/followup_record", methods=["POST"])
def api_update_followup_record():
    """更新回診記錄 API"""
    data = request.form
    record_id = data.get("record-id")
    patient_id = data.get("patient-id")
    medicine_type = data.get("medicine-type")
    followup_date = data.get("followup-date")
    next_followup_date = data.get("next-followup-date")
    remain_dose = data.get("remain-dose")
    remark = data.get("remark")

    # 必填欄位驗證
    if not record_id:
        return {"success": False, "message": "缺少記錄ID"}, 400
    if not patient_id:
        return {"success": False, "message": "缺少病患ID"}, 400
    if not medicine_type:
        return {"success": False, "message": "缺少藥物類型"}, 400

    # 類型驗證 - 白名單
    if medicine_type not in ("biological", "traditional"):
        return {"success": False, "message": "無效的藥物類型"}, 400

    conn = get_connection()
    cursor = conn.cursor()

    table_name = "biological_medicine_record" if medicine_type == "biological" else "traditional_medicine_record"

    # 取得舊資料
    cursor.execute(f"SELECT * FROM {table_name} WHERE id = ? AND patient_id = ?", (record_id, patient_id))
    old_data_row = cursor.fetchone()
    if old_data_row is None:
        conn.close()
        return {"success": False, "message": "找不到記錄"}, 404
    old_data = dict(old_data_row)

    # 準備新資料
    new_data = dict(old_data)
    new_data["followup_date"] = followup_date if followup_date else old_data.get("followup_date")
    new_data["next_followup_date"] = next_followup_date if next_followup_date else old_data.get("next_followup_date")
    new_data["remark"] = remark if remark is not None else old_data.get("remark")

    # 執行更新
    if medicine_type == "biological":
        new_data["remain_dose"] = remain_dose if remain_dose is not None else old_data.get("remain_dose")
        cursor.execute("""
            UPDATE biological_medicine_record
            SET followup_date = ?, next_followup_date = ?, remain_dose = ?, remark = ?
            WHERE id = ? AND patient_id = ?
        """, (new_data["followup_date"], new_data["next_followup_date"], new_data["remain_dose"], new_data["remark"], record_id, patient_id))
    else:
        cursor.execute("""
            UPDATE traditional_medicine_record
            SET followup_date = ?, next_followup_date = ?, remark = ?
            WHERE id = ? AND patient_id = ?
        """, (new_data["followup_date"], new_data["next_followup_date"], new_data["remark"], record_id, patient_id))

    conn.commit()

    # 記錄審計日誌
    log_db_action(
        cursor,
        action="UPDATE",
        table_name=table_name,
        record_id=record_id,
        old_data=old_data,
        new_data=new_data,
        sql_statement=f"UPDATE {table_name} WHERE id = {record_id}",
        operator="api",
        ip_address=flask_request.remote_addr
    )
    conn.commit()
    conn.close()
    return {"success": True}


# ===========================================================================
# API 路由 - 刪除操作
# ===========================================================================

@app.route("/api/delete/doctor", methods=["DELETE"])
def api_delete_doctor():
    """刪除醫師 API（軟刪除）"""
    data = request.get_json()
    id_ = data.get("id")

    conn = get_connection()
    cursor = conn.cursor()
    
    # 取得舊資料
    cursor.execute("SELECT * FROM doctors WHERE id = ?", (id_,))
    old_data_row = cursor.fetchone()
    if old_data_row is None:
        conn.close()
        return {"success": False, "message": "找不到醫師"}, 404
    old_data = dict(old_data_row)
    
    cursor.execute("UPDATE doctors SET disable = ? WHERE id = ?", (1, id_))
    
    # 記錄審計日誌
    new_data = dict(old_data)
    new_data["disable"] = 1
    log_db_action(
        cursor,
        action="UPDATE",
        table_name="doctors",
        record_id=id_,
        old_data=old_data,
        new_data=new_data,
        sql_statement=f"UPDATE doctors SET disable=1 WHERE id={id_}",
        operator="api",
        ip_address=flask_request.remote_addr
    )
    conn.commit()
    conn.close()
    return {"success": True}


@app.route("/api/delete/disease", methods=["DELETE"])
def api_delete_disease():
    """刪除疾病 API（軟刪除）"""
    data = request.get_json()
    id_ = data.get("id")

    conn = get_connection()
    cursor = conn.cursor()
    
    # 取得舊資料
    cursor.execute("SELECT * FROM diseases WHERE id = ?", (id_,))
    old_data_row = cursor.fetchone()
    if old_data_row is None:
        conn.close()
        return {"success": False, "message": "找不到疾病"}, 404
    old_data = dict(old_data_row)
    
    cursor.execute("UPDATE diseases SET disable = ? WHERE id = ?", (1, id_))
    
    # 記錄審計日誌
    new_data = dict(old_data)
    new_data["disable"] = 1
    log_db_action(
        cursor,
        action="UPDATE",
        table_name="diseases",
        record_id=id_,
        old_data=old_data,
        new_data=new_data,
        sql_statement=f"UPDATE diseases SET disable=1 WHERE id={id_}",
        operator="api",
        ip_address=flask_request.remote_addr
    )
    conn.commit()
    conn.close()
    return {"success": True}


@app.route("/api/delete/examination", methods=["DELETE"])
def api_delete_examination():
    """刪除檢查項目 API（軟刪除）"""
    data = request.get_json()
    id_ = data.get("id")

    conn = get_connection()
    cursor = conn.cursor()
    
    # 取得舊資料
    cursor.execute("SELECT * FROM examinations WHERE id = ?", (id_,))
    old_data_row = cursor.fetchone()
    if old_data_row is None:
        conn.close()
        return {"success": False, "message": "找不到檢查項目"}, 404
    old_data = dict(old_data_row)
    
    cursor.execute("UPDATE examinations SET disable = ? WHERE id = ?", (1, id_))
    
    # 記錄審計日誌
    new_data = dict(old_data)
    new_data["disable"] = 1
    log_db_action(
        cursor,
        action="UPDATE",
        table_name="examinations",
        record_id=id_,
        old_data=old_data,
        new_data=new_data,
        sql_statement=f"UPDATE examinations SET disable=1 WHERE id={id_}",
        operator="api",
        ip_address=flask_request.remote_addr
    )
    conn.commit()
    conn.close()
    return {"success": True}


@app.route("/api/delete/medicine", methods=["DELETE"])
def api_delete_medicine():
    """刪除藥物 API（軟刪除）"""
    data = request.get_json()
    id_ = data.get("id")
    type_ = data.get("type")

    # 類型驗證 - 白名單
    if type_ not in ("tradmedicines", "biomedicines"):
        return {"success": False, "message": "無效的藥物類型"}, 400

    conn = get_connection()
    cursor = conn.cursor()

    table_name = "traditional_medicines" if type_ == "tradmedicines" else "biological_medicines"
    
    # 取得舊資料
    cursor.execute(f"SELECT * FROM {table_name} WHERE id = ?", (id_,))
    old_data_row = cursor.fetchone()
    if old_data_row is None:
        conn.close()
        return {"success": False, "message": "找不到藥物"}, 404
    old_data = dict(old_data_row)

    if type_ == "tradmedicines":
        cursor.execute("UPDATE traditional_medicines SET disable = ? WHERE id = ?", (1, id_))
    elif type_ == "biomedicines":
        cursor.execute("UPDATE biological_medicines SET disable = ? WHERE id = ?", (1, id_))
    
    # 記錄審計日誌
    new_data = dict(old_data)
    new_data["disable"] = 1
    log_db_action(
        cursor,
        action="UPDATE",
        table_name=table_name,
        record_id=id_,
        old_data=old_data,
        new_data=new_data,
        sql_statement=f"UPDATE {table_name} SET disable=1 WHERE id={id_}",
        operator="api",
        ip_address=flask_request.remote_addr
    )
    conn.commit()
    conn.close()
    return {"success": True}


@app.route("/api/update/examination_history", methods=["POST"])
def api_update_examination_history():
    """更新檢查歷史記錄 API"""
    data = request.form
    id_ = data.get("id")
    check_date = data.get("check_date")
    result = data.get("result")
    remark = data.get("remark")

    # 必填欄位驗證
    if not id_:
        return {"success": False, "message": "缺少記錄ID"}, 400

    conn = get_connection()
    cursor = conn.cursor()

    # 取得舊資料
    cursor.execute("SELECT * FROM examination_record WHERE id = ?", (id_,))
    old_data_row = cursor.fetchone()
    if old_data_row is None:
        conn.close()
        return {"success": False, "message": "找不到記錄"}, 404
    old_data = dict(old_data_row)

    # 準備新資料
    new_data = dict(old_data)
    new_data["check_date"] = check_date if check_date else old_data["check_date"]
    new_data["result"] = result if result else old_data["result"]
    new_data["remark"] = remark if remark else old_data["remark"]

    # 執行更新
    cursor.execute("""
        UPDATE examination_record
        SET check_date = ?, result = ?, remark = ?
        WHERE id = ?
    """, (new_data["check_date"], new_data["result"], new_data["remark"], id_))

    conn.commit()

    # 記錄審計日誌
    log_db_action(
        cursor,
        action="UPDATE",
        table_name="examination_record",
        record_id=id_,
        old_data=old_data,
        new_data=new_data,
        sql_statement=f"UPDATE examination_record WHERE id = {id_}",
        operator="api",
        ip_address=flask_request.remote_addr
    )
    conn.commit()
    conn.close()
    return {"success": True}


@app.route("/api/delete/examination_history", methods=["DELETE"])
def api_delete_examination_history():
    """刪除檢查歷史記錄 API"""
    data = request.form
    id_ = data.get("id")

    # 驗證 ID 格式
    try:
        int(id_)
    except Exception:
        return {"success": False, "message": "無效的ID格式"}

    conn = get_connection()
    cursor = conn.cursor()

    # 取得舊資料
    cursor.execute("SELECT * FROM examination_record WHERE id = ?", (id_,))
    old_data_row = cursor.fetchone()
    if old_data_row is None:
        conn.close()
        return {"success": False, "message": "找不到記錄"}, 404
    old_data = dict(old_data_row)

    cursor.execute("DELETE FROM examination_record WHERE id = ?", (id_,))

    # 記錄審計日誌
    log_db_action(
        cursor,
        action="DELETE",
        table_name="examination_record",
        record_id=id_,
        old_data=old_data,
        new_data=None,
        sql_statement=f"DELETE FROM examination_record WHERE id = {id_}",
        operator="api",
        ip_address=flask_request.remote_addr
    )
    conn.commit()
    conn.close()
    return {"success": True}


@app.route("/api/delete/patient", methods=["DELETE"])
def api_delete_patient():
    """刪除病患 API（連動刪除所有相關記錄）"""
    data = request.get_json()
    patient_id = data.get("id")

    if not patient_id:
        return {"success": False, "message": "缺少病患ID"}, 400

    conn = get_connection()
    cursor = conn.cursor()
    
    # 取得舊資料
    cursor.execute("SELECT * FROM patients WHERE id = ?", (patient_id,))
    old_data_row = cursor.fetchone()
    if old_data_row is None:
        conn.close()
        return {"success": False, "message": "找不到病患"}, 404
    old_data = dict(old_data_row)
    
    # 1. 刪除檢查記錄 (examination_record)
    cursor.execute("SELECT * FROM examination_record WHERE patient_id = ?", (patient_id,))
    exam_records = cursor.fetchall()
    for record in exam_records:
        record_data = dict(record)
        cursor.execute("DELETE FROM examination_record WHERE id = ?", (record_data["id"],))
        log_db_action(
            cursor,
            action="DELETE",
            table_name="examination_record",
            record_id=record_data["id"],
            old_data=record_data,
            new_data=None,
            sql_statement=f"DELETE FROM examination_record WHERE id = {record_data['id']}",
            operator="web",
            ip_address=flask_request.remote_addr
        )
    
    # 2. 刪除傳統用藥記錄 (traditional_medicine_record)
    cursor.execute("SELECT * FROM traditional_medicine_record WHERE patient_id = ?", (patient_id,))
    trad_records = cursor.fetchall()
    for record in trad_records:
        record_data = dict(record)
        cursor.execute("DELETE FROM traditional_medicine_record WHERE id = ?", (record_data["id"],))
        log_db_action(
            cursor,
            action="DELETE",
            table_name="traditional_medicine_record",
            record_id=record_data["id"],
            old_data=record_data,
            new_data=None,
            sql_statement=f"DELETE FROM traditional_medicine_record WHERE id = {record_data['id']}",
            operator="web",
            ip_address=flask_request.remote_addr
        )
    
    # 3. 刪除生物製劑記錄 (biological_medicine_record)
    cursor.execute("SELECT * FROM biological_medicine_record WHERE patient_id = ?", (patient_id,))
    bio_records = cursor.fetchall()
    for record in bio_records:
        record_data = dict(record)
        cursor.execute("DELETE FROM biological_medicine_record WHERE id = ?", (record_data["id"],))
        log_db_action(
            cursor,
            action="DELETE",
            table_name="biological_medicine_record",
            record_id=record_data["id"],
            old_data=record_data,
            new_data=None,
            sql_statement=f"DELETE FROM biological_medicine_record WHERE id = {record_data['id']}",
            operator="web",
            ip_address=flask_request.remote_addr
        )
    
    # 4. 刪除病患本身
    cursor.execute("DELETE FROM patients WHERE id = ?", (patient_id,))
    
    # 記錄審計日誌
    log_db_action(
        cursor,
        action="DELETE",
        table_name="patients",
        record_id=patient_id,
        old_data=old_data,
        new_data=None,
        sql_statement=f"DELETE FROM patients WHERE id = {patient_id}",
        operator="web",
        ip_address=flask_request.remote_addr
    )
    conn.commit()
    conn.close()
    return {"success": True}


@app.route("/api/delete/history", methods=["DELETE"])
def api_delete_history():
    """刪除用藥歷史記錄 API"""
    data = request.form
    id_ = data.get("id")

    # 驗證 ID 格式
    try:
        int(id_)
    except Exception:
        return {"success": False}

    type_ = data.get("type")

    conn = get_connection()
    cursor = conn.cursor()

    table_name = "traditional_medicine_record" if type_ != "biological" else "biological_medicine_record"
    
    # 取得舊資料
    cursor.execute(f"SELECT * FROM {table_name} WHERE id = ?", (id_,))
    old_data_row = cursor.fetchone()
    if old_data_row is None:
        conn.close()
        return {"success": False, "message": "找不到記錄"}, 404
    old_data = dict(old_data_row)

    if type_ == "biological":
        query = "DELETE FROM biological_medicine_record WHERE id = ?"
    else:
        query = "DELETE FROM traditional_medicine_record WHERE id = ?"

    cursor.execute(query, (id_,))
    
    # 記錄審計日誌
    log_db_action(
        cursor,
        action="DELETE",
        table_name=table_name,
        record_id=id_,
        old_data=old_data,
        new_data=None,
        sql_statement=f"DELETE FROM {table_name} WHERE id = {id_}",
        operator="api",
        ip_address=flask_request.remote_addr
    )
    conn.commit()
    conn.close()
    return {"success": True}


# ===========================================================================
# API 路由 - PASI 分數儲存
# ===========================================================================

@app.route("/api/pasi/save", methods=["POST"])
def api_pasi_save():
    """儲存 PASI 分數記錄"""
    from werkzeug.utils import secure_filename
    import os
    import uuid
    import json
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # 先建立 PASI 記錄以取得 id
    pasi_score_val = request.form.get('pasi_score', 0, type=float)
    severity = request.form.get('severity', '')
    remark = request.form.get('remark', '')
    
    regions = ['head', 'upper', 'trunk', 'lower']
    record_data = {'pasi_score': pasi_score_val, 'severity': severity, 'remark': remark}
    
    for region in regions:
        record_data[f'erythema_{region}'] = request.form.get(f'erythema_{region}', 0, type=int)
        record_data[f'infiltrate_{region}'] = request.form.get(f'infiltrate_{region}', 0, type=int)
        record_data[f'desquamation_{region}'] = request.form.get(f'desquamation_{region}', 0, type=int)
        record_data[f'area_{region}'] = request.form.get(f'area_{region}', 0, type=int)
    
    # 先插入空白記錄取得 id
    cursor.execute("""
        INSERT INTO pasi_records (
            pasi_score, severity,
            erythema_head, infiltrate_head, desquamation_head, area_head,
            erythema_upper, infiltrate_upper, desquamation_upper, area_upper,
            erythema_trunk, infiltrate_trunk, desquamation_trunk, area_trunk,
            erythema_lower, infiltrate_lower, desquamation_lower, area_lower,
            image_path, remark
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        record_data['pasi_score'], record_data['severity'],
        record_data['erythema_head'], record_data['infiltrate_head'], record_data['desquamation_head'], record_data['area_head'],
        record_data['erythema_upper'], record_data['infiltrate_upper'], record_data['desquamation_upper'], record_data['area_upper'],
        record_data['erythema_trunk'], record_data['infiltrate_trunk'], record_data['desquamation_trunk'], record_data['area_trunk'],
        record_data['erythema_lower'], record_data['infiltrate_lower'], record_data['desquamation_lower'], record_data['area_lower'],
        None, record_data['remark']
    ))
    
    record_id = cursor.lastrowid
    
    # 處理多張圖片上傳 - 同一批放在同一資料夾
    image_files = request.files.getlist('images')
    image_paths = []
    
    if image_files:
        # 用 record_id 建立資料夾
        record_dir = f"pasi_record_{record_id}"
        upload_dir = os.path.join(os.path.dirname(__file__), "static", "uploads", "pasi", record_dir)
        os.makedirs(upload_dir, exist_ok=True)
        
        for idx, image_file in enumerate(image_files):
            if image_file and image_file.filename:
                filename = secure_filename(image_file.filename)
                ext = filename.rsplit('.', 1)[-1] if '.' in filename else 'jpg'
                unique_filename = f"img_{idx + 1}.{ext}"
                file_path = os.path.join(upload_dir, unique_filename)
                image_file.save(file_path)
                image_paths.append(f"uploads/pasi/{record_dir}/{unique_filename}")
    
    # 更新記錄的 image_path
    image_path_json = json.dumps(image_paths) if image_paths else None
    if image_paths:
        cursor.execute("UPDATE pasi_records SET image_path = ? WHERE id = ?", (image_path_json, record_id))
    
    record_data['image_path'] = image_path_json
    record_data['id'] = record_id
    
    log_db_action(
        cursor, action="INSERT", table_name="pasi_records", record_id=record_id,
        old_data=None, new_data=record_data, sql_statement="INSERT INTO pasi_records ...",
        operator="web", ip_address=flask_request.remote_addr
    )
    
    conn.commit()
    conn.close()
    
    logger.info(f"PASI 記錄已儲存: id={record_id}, score={pasi_score_val}")
    return {"success": True, "id": record_id}


# ===========================================================================
# 程式啟動
# ===========================================================================

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
