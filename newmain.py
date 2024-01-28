from fastapi import FastAPI, Request,Header,Form,File, UploadFile, HTTPException
import sqlite3
import threading
import json
from datetime import datetime, date, time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time
import datetime
import random
import string
from PIL import Image
import base64
from io import BytesIO
from fastapi.responses import JSONResponse
import requests
from bs4 import BeautifulSoup
import re
import json
import os
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse




def generate_family_code():
    characters = string.ascii_letters + string.digits  
    random_string = ''.join(random.choice(characters) for _ in range(9))
    return random_string


def is_base64_image(data):
    try:
        # Base64 verisini çözerek bir bayt nesnesi elde et
        decoded_data = base64.b64decode(data)

        # BytesIO kullanarak bayt nesnesini bir resim olarak yükle
        image = Image.open(BytesIO(decoded_data))

        # Resim başarıyla yüklendiyse, base64 verisi bir resimdir
        return True
    except Exception as e:
        # Hata oluştuysa, base64 verisi bir resim değildir
        return False


expo_push_endpoint = 'https://exp.host/--/api/v2/push/send'
expo_receipts_endpoint = 'https://exp.host/--/api/v2/push/getReceipts'



def send_push_notification(expo_push_token, title, body):
    data = {
        'to': expo_push_token,
        'title': title,
        'body': body,
    }

    response = requests.post(expo_push_endpoint, json=data)
    return response.json()



def getKandilliData():
    try:
        array = []
        response = requests.get('http://www.koeri.boun.edu.tr/scripts/sondepremler.asp')

        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            data = soup.find_all('pre')
            data = str(data).strip().split('--------------')[2]

            data = data.split('\n')
            data.pop(0)
            data.pop()
            data.pop()
            for index in range(len(data)):
                element = str(data[index].rstrip())
                element = re.sub(r'\s\s\s', ' ', element)
                element = re.sub(r'\s\s\s\s', ' ', element)
                element = re.sub(r'\s\s', ' ', element)
                element = re.sub(r'\s\s', ' ', element)
                Args = element.split(' ')
                location = Args[8]+element.split(Args[8])[len(element.split(
                    Args[8])) - 1].split('İlksel')[0].split('REVIZE')[0]
                json_data = json.dumps({
                    "id": index+1,
                    "date": Args[0]+" "+Args[1],
                    "timestamp": int(datetime.datetime.strptime(Args[0]+" "+Args[1], "%Y.%m.%d %H:%M:%S").timestamp()),
                    "latitude": float(Args[2]),
                    "longitude": float(Args[3]),
                    "depth": float(Args[4]),
                    "mag" : float(Args[6].replace('-.-', '0')),

                    "size": {
                        "md": float(Args[5].replace('-.-', '0')),
                        "ml": float(Args[6].replace('-.-', '0')),
                        "mw": float(Args[7].replace('-.-', '0'))
                    },
                    "title": location.strip(),
                    "attribute": element.split(location)[1].split()[0]
                }, sort_keys=False)

                array.append(json.loads(json_data))
            return array
        else:
            return []
    except Exception as e:
        print(f"Hata: {e}")
        return []


def tc_kimlik_dogrula(value):
    value = str(value)
    if not len(value) == 11:
        return False
    if not value.isdigit():
        return False
    if int(value[0]) == 0:
        return False
    digits = [int(d) for d in str(value)]
    if not sum(digits[:10]) % 10 == digits[10]:
        return False
    if not (((7 * sum(digits[:9][-1::-2])) - sum(digits[:9][-2::-2])) % 10) == digits[9]:
        return False
    return True

with open('adres/sehir.json') as f:
    sehir_data = json.load(f)

with open('adres/ilce.json') as f:
    ilce_data = json.load(f)

with open('adres/mahalle.json') as f:
    mahalle_data = json.load(f)

with open('adres/sokak_cadde.json') as f:
    sokak_data = json.load(f)



def otpmailgönder(kod,email):
  smtp_server = 'smtp.gmail.com'
  smtp_port = 587
  sender_email = 'asenatechnology@gmail.com'
  receiver_email = email
  password = 'vszrjlpzeuydnoco'
  message = MIMEMultipart()
  message['From'] = sender_email
  message['To'] = receiver_email
  message['Subject'] = 'Yardim Dağitimi hk.'

  body = f"""
Merhaba,

kod {kod}

İyi günler.
"""
  message.attach(MIMEText(body, 'plain'))
  server = smtplib.SMTP(smtp_server, smtp_port)
  server.starttls()
  server.login(sender_email, password)
  server.sendmail(sender_email, receiver_email, message.as_string())
  server.quit()



def json_oku(dosya_adi):
  with open("./" + dosya_adi, encoding="utf-8") as dosya:
    return json.load(dosya)


def json_yaz(oyun, dosya_adi):
  with open("./" + dosya_adi, 'w', encoding="utf-8") as dosya:
    json.dump(oyun, dosya)


app = FastAPI()

local_data = threading.local()

def authenticate_user(email, password):
 connection = get_db_connection()
 cursor = connection.cursor()

 cursor.execute('SELECT * FROM users WHERE email = ? AND password = ?', (email, password))
 user = cursor.fetchone()
 close_db_connection()
 return user




def get_db_connection():
    if not hasattr(local_data, "connection"):
        local_data.connection = sqlite3.connect('veritabani.db')
    return local_data.connection


def close_db_connection():
    if hasattr(local_data, "connection"):
        local_data.connection.close()
        del local_data.connection

def init_db():
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS families (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    phone TEXT NOT NULL,
                    code TEXT NOT NULL,
                    users TEXT NOT NULL,
                    name TEXT NOT NULL,
                    childs TEXT NOT NULL,
                    binaplan TEXT NOT NULL,
                    adres TEXT NOT NULL,
                    binaname TEXT NOT NULL
                    )''')


    cursor.execute('''CREATE TABLE IF NOT EXISTS yardimlar (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    phone TEXT NOT NULL,
                    adres TEXT NOT NULL,
                    urun TEXT NOT NULL,
                    miktar TEXT NOT NULL,
                    tarih TEXT NOT NULL,
                    ip TEXT NOT NULL
                    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS usersinfo (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    phone TEXT NOT NULL,
                    rehber TEXT NOT NULL,
                    yardim TEXT NOT NULL,
                    durum TEXT NOT NULL,
                    durumtime TEXT NOT NULL,
                    ailecode TEXT,
                    photo TEXT NOT NULL,
                    notifications TEXT NOT NULL,
                    name TEXT NOT NULL,
                    surname TEXT NOT NULL,
                    tckimlik TEXT NOT NULL,
                    kangrup TEXT NOT NULL
                    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL,
                    konu TEXT NOT NULL,
                    mesaj TEXT NOT NULL

                    )''')



    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            surname TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            tcnumber TEXT NOT NULL,
            dogumyil TEXT NOT NULL,
            photo TEXT NOT NULL,
            kangrup TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            surname TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            tcnumber TEXT NOT NULL,
            dogumyil TEXT NOT NULL,
            photo TEXT NOT NULL,
            kangrup TEXT NOT NULL
        )
    ''')
    connection.commit()



def beniyiyimclear():
   
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM usersinfo")
    veriler = cursor.fetchall()

    for veri in veriler:
      try:
       veri_mevcut_zaman = veri[5]
       mevcut_saat = veri_mevcut_zaman.split(":")[1].replace("-", ":")
       mevcut_zaman = datetime.datetime.now()
       formatli_zaman = mevcut_zaman.strftime("%Y-%m-%d:%H-%M")
       mevcut_saat = formatli_zaman.split(":")[1].replace("-", ":")
       mevcut_tarih = formatli_zaman.split(":")[0]
       mevcut_tarih_dt = datetime.datetime.strptime(mevcut_tarih, "%Y-%m-%d")
       bir_gun_sonrasi = mevcut_tarih_dt + datetime.timedelta(days=1)
       if mevcut_saat == mevcut_saat and bir_gun_sonrasi.strftime("%Y-%m-%d") == mevcut_tarih:
        cursor.execute('UPDATE usersinfo SET durum = ? WHERE phone = ?', ("empty", veri[4]))
        connection.commit()
      except:
        pass









def phoneduzelt(phone):
    phone = phone.replace(" ", "")

    if not phone.startswith("+90") or not phone.startswith("90"):
        if phone.startswith("0"):
            chg = phone[1:]
            phone = "+90" + chg
        elif phone.startswith("90"):
            phone = "+" + phone
        elif phone.startswith("+90") or phone.startswith("+"):
           phone = phone
        else:
            phone = "+90" + phone

    return phone


origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Resim dosyalarını depolamak için bir klasör oluştur
upload_folder = "uploads"
os.makedirs(upload_folder, exist_ok=True)

# Ana dizine "uploads" klasörüne erişim sağlama
app.mount("/uploads", StaticFiles(directory=upload_folder), name="uploads")


def is_image(filename):
    # Desteklenen resim dosya uzantılarını kontrol etme
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions



@app.on_event("startup")
def startup_event():
    init_db()

@app.on_event("shutdown")
def shutdown_event():
    close_db_connection()

@app.get("/")
def root(request:Request):
 
    return {"message" : "Asena Technology Hoşgeldiniz. Sürüm v1.1"}

@app.post("/register")
async def register(request: Request):
    data = await request.json()

    seckey = "DKOEFE-232320-AWDWOP"
    key = data.get('key', None)
    phone = data.get('phone', None)
    name = data.get('name', None)
    surname = data.get('surname', None)
    email = data.get("email", None)
    password = data.get("password",None)
    tcnumber = data.get("tcnumber",None)
    dogumyil = data.get("dogumyil",None)
    kangrup = data.get("kangrup",None)
    profile = data.get("profile",None)

    name = name.title()
    surname = surname.title()



    if profile == None:
       profile = ""
    if key and phone and name and surname and email and password and tcnumber and dogumyil and kangrup is not None:
        if tc_kimlik_dogrula((tcnumber)):
          True
        else:
          return {"status" : "False" , "error": "Girilen tc kimlik numarası geçersiz." }

        phone = phoneduzelt(phone)
        if key == seckey:

            connection = get_db_connection()
            cursor = connection.cursor()

            cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
            user = cursor.fetchone()
            if user:
                return {"status": "False", "error": "Bu Mail Zaten Kullanılıyor!"}

            cursor.execute('SELECT * FROM users WHERE phone = ?', (phone,))
            user = cursor.fetchone()
            if user:
                return {"status": "False", "error": "Bu Telefon Numarası Zaten Kullanılıyor!"}
            cursor.execute('SELECT * FROM users WHERE tcnumber = ?', (tcnumber,))
            user = cursor.fetchone()
            if user:
                return {"status": "False", "error": "Bu Tc Kimlik Numarası Zaten Kullanılıyor!"}



            cursor.execute('''
                    INSERT INTO users (name, surname, email, phone, password,role,tcnumber,dogumyil,photo,kangrup)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?,?,?)
                    ''', (name, surname, email, phone, password, "user", tcnumber, dogumyil, profile,kangrup))

            cursor.execute('''
                INSERT INTO usersinfo (phone, rehber, yardim, durum, durumtime, ailecode,photo,notifications,name,surname,tckimlik,kangrup) 
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?,?,?)
''', (phone, json.dumps([]), json.dumps([]), "", "", None, profile , "",name,surname,tcnumber,kangrup))


            connection.commit()

            return {"status": "True", "message": "Kullanıcı başarıyla kaydedildi."}
        else:
            return {"status": "False", "error": "Access Denied"}
    else:
        return {"status": "False", "error": "Enter the required parameters."}

# 6 haneli random rakam oluşturan fonksiyon
def generate_random_number():
    return str(random.randint(100000, 999999))

# Uploads klasöründeki dosya isimlerini kontrol eden fonksiyon
def is_file_exists(file_path: str):
    return os.path.exists(file_path)

@app.post("/setphoto")
async def upload_file(
    username: str = Form(...),
    password: str = Form(...),
    file: UploadFile = File(...),
):
    if username and password is not None:
        user = authenticate_user(username, password)
        if user:
            connection = get_db_connection()
            cursor = connection.cursor()

            # Check if the user has an existing photo
            old_photo = user[9]  # Assuming the photo column is at index 9, adjust if needed
            
            if old_photo:
                old_photo_path = os.path.join(upload_folder, old_photo)
                
                # Remove the old photo from the uploads folder
                if os.path.exists(old_photo_path):
                    os.remove(old_photo_path)

            if not is_image(file.filename):
                raise HTTPException(status_code=400, detail="Sadece resim dosyaları desteklenmektedir.")

            # 6 haneli random rakamları oluştur
            random_number = generate_random_number()

            # Dosya adını oluştur
            nam = f"{user[1]}_{user[2]}_{random_number}.jpg"
            file_path = os.path.join(upload_folder, nam)

            # Eğer aynı isimde bir dosya varsa, random sayıyı güncelle
            while is_file_exists(file_path):
                random_number = generate_random_number()
                nam = f"{user[1]}_{user[2]}_{random_number}.jpg"
                file_path = os.path.join(upload_folder, nam)

            # Gelen resmi Pillow kullanarak JPG formatına çevir
            image = Image.open(file.file)
            image.save(file_path, "JPEG")

            cursor.execute('UPDATE users SET photo = ? WHERE phone = ?', (nam, user[4]))
            cursor.execute('UPDATE usersinfo SET photo = ? WHERE phone = ?', (nam, user[4]))
            connection.commit()

            return {"status": "True" , "photo" : nam}
        else:
            return {"status": "False", "error": "Giriş başarısız."}
    else:
        return {"status": "False", "error": "Enter the required parameters."}


def is_image(filename):
    # Desteklenen resim dosya uzantılarını kontrol etme
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions


@app.get("/profilephotos/{filename}")
async def read_file(filename: str):
    file_path = os.path.join(upload_folder, filename)

    # Check if the file exists
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="image/jpeg")
    else:
        # Return a default image if the file doesn't exist
        default_image_path = os.path.join(upload_folder, "default.jpeg")
        return FileResponse(default_image_path, media_type="image/jpeg")

@app.get("/login")
def login(request: Request):

    args = request.query_params
    email = args.get("email", None)
    password = args.get("password")
    photo = args.get("photo",False)
    notification = args.get("notification",None)
    if email and password is not None:
      user = authenticate_user(email, password)
      if user:
       if notification is not None:
         connection = get_db_connection()
         cursor = connection.cursor()
         cursor.execute('UPDATE usersinfo SET notifications = ? WHERE phone = ?', (notification, user[4]))
         connection.commit()

       if photo:
          data = {
        "status": "True",
        "message": "Giriş başarılı!",
        "id": user[0],
        "name": user[1],
        "surname": user[2],
        "phone": user[4],
        "role" : user[6],
        "tcnumber" : user[7],
        "dogumyil": user[8],
        "photo": user[9]
    } 
       else:
        data = {
        "status": "True",
        "message": "Giriş başarılı!",
        "id": user[0],
        "name": user[1],
        "surname": user[2],
        "phone": user[4],
        "role" : user[6],
        "tcnumber" : user[7],
        "dogumyil": user[8],
        "photo": user[9],

    }
      else:
       data = {
        "status": "False",
        "error": "Giriş başarısız! Kullanıcı adı veya şifre hatalı."
     }
      return (data)
    else:
        return {"status": "False", "error": "Lütfen gerekli parametreleri giriniz."}
@app.get("/searchuser")
def searchuser(request : Request):
   args = request.query_params
   username = args.get("email",None)
   password = args.get("password",None)
   userid = args.get("phone",None)
   userid = phoneduzelt(userid)
   if username and password and userid is not None:
      user = authenticate_user(username, password)
      if user:
       connection = get_db_connection()
       cursor = connection.cursor()
       cursor.execute('SELECT * FROM usersinfo WHERE phone = ?', (userid,))
       users = cursor.fetchone()
       if users:
        return {"status" : "True" , "photo" : users[7] , "kan" : users[12]}
       else:
          return {"status" : "False" , "error" : "Kullanıcı bulunamadı."}  
      else:
       return {"status": "False" , "error" : "Giriş başarısız."}
   else:
      return {"status": "False", "error": "Enter the required parameters."} 
   

@app.get("/addhelp")
def addhelp(request: Request):
  args = request.query_params
  sehir = args.get('sehir',None)
  ilce = args.get('ilce',None)
  mahalle = args.get('mahalle',None)
  sokak = args.get('sokak',None)
  urun = args.get('urun',None)
  miktar = args.get('miktar',None)
  email = args.get("email", None)
  password = args.get("password",None)
  import time
  if email and password and miktar and urun and sokak and mahalle and ilce and sehir != None:
       user = authenticate_user(email, password)
       connection = get_db_connection()
       cursor = connection.cursor()
       if user:
           cursor.execute(f"SELECT * FROM usersinfo WHERE phone = '{user[4]}'", )
           users = cursor.fetchone()
           yardimlist =  json.loads(users[3])
           json_data = {"phone": "", "adres": "", "urun": "", "miktar": ""}
           adres = f"{mahalle} mahallesi, {sokak} sokak, {ilce}/{sehir}"
           json_data['adres'] = adres
           json_data['phone'] = user[4]
           json_data['urun'] = urun
           json_data['miktar'] = miktar
           yardimlist.append(json_data)
           current_time = time.strftime('%Y-%m-%d %H:%M:%S')
           client_ip = request.client.host
           statjson = json_oku("stats.json")
           statjson['yardim'] =  int(statjson['yardim']) +1
           json_yaz(statjson,"stats.json")
           cursor.execute('UPDATE usersinfo SET yardim = ? WHERE phone = ?', (json.dumps(yardimlist), user[4]))
           cursor.execute('''INSERT INTO yardimlar (phone, adres, urun, miktar, tarih, ip) VALUES (?, ?, ?, ?, ?,?)''', (user[4], adres, urun, miktar,str(current_time),client_ip))
           connection.commit()
           close_db_connection()
           return yardimlist
       else:
           return {"status": "False" , "error" : "Kullanıcı adı veya şifre hatalı."}    

  else:
      return {"status" : "False" , "error" : "Lütfen gerekli parametreleri giriniz."}



@app.get("/myhelp")
def getmyhelp(request : Request):
 args = request.query_params
 username = args.get("username",None)
 password = args.get("password",None)
 if username and password != None:
   user = authenticate_user(username, password)
   if user:
    connection = get_db_connection() 
    cursor = connection.cursor()
    cursor.execute(f"SELECT * FROM usersinfo WHERE phone = '{user[4]}'", )
    users = cursor.fetchone()
    yardimlist =  json.loads(users[3])
    close_db_connection()
    return {"status": "True", "yardim": yardimlist}
   else:
     return {"status": "False" , "error" : "Kullanıcı adı veya şifre hatalı."}    
 else:
    return {"status" : "False" , "error" : "Lütfen gerekli parametreleri giriniz."}
@app.get("/removehelp")
def removehelp(request : Request):
 args = request.query_params
 username = args.get("username",None)
 password = args.get("password",None)
 urun = args.get("urun", None)
 miktar = args.get("miktar",None)

 if username and password != None:
   user = authenticate_user(username, password)
   if user:
    connection = get_db_connection() 
    cursor = connection.cursor()
    cursor.execute(f"SELECT * FROM usersinfo WHERE phone = '{user[4]}'", )
    users = cursor.fetchone()
    yardimlist =  json.loads(users[3])
    newlist = []
    for i in yardimlist:
       if i['urun'] == urun and i['miktar'] == miktar:
          continue
       newlist.append(i)
    cursor.execute('UPDATE usersinfo SET yardim = ? WHERE phone = ?', (json.dumps(newlist), user[4]))
    connection.commit()
    close_db_connection()
    return {"status": "True", "yardim" : newlist}
   else: 
     return {"status": "False" , "error" : "Kullanıcı adı veya şifre hatalı."}    
 else:
    return {"status" : "False" , "error" : "Lütfen gerekli parametreleri giriniz."}



@app.get("/helplist")
def yardimlist(request: Request):

    yardim_verileri = []
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute(f"SELECT * FROM usersinfo" )
    users = cursor.fetchall()

    for i in users:
     
       for item in json.loads(i[3]):
         yardim_verileri.append(item)
    data = {"status": "True", "data": yardim_verileri}
    close_db_connection()
    return data

@app.get("/addcontact")
def addcontact(request: Request):
    args = request.query_params
    name = args.get("name",None)
    surname = args.get("surname",None)
    phone2 = args.get("phone2",None)
    phone2 = phoneduzelt(phone2)
    email = args.get("email",None)
    username  = args.get("username")
    password = args.get("password")


    if phone2 and name and surname and email and username and password != None:
     user = authenticate_user(username,password)
     if user:
        if phone2 == user[4]:
           return {"status" : "False" , "error" : "Kendini ekleyemezsin.."}
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(f"SELECT * FROM USERS WHERE phone = '{phone2}'")

        check = cursor.fetchone()
        cursor.execute(f"SELECT * FROM usersinfo WHERE phone = '{phone2}'")
        notuser = cursor.fetchone() ##kullanıcının bilgilerini aldın
       

        if not check:
           return {"status" : "False" , "error" : "Kullanıcı halihazırda uygulamanın üyesi değil."}

        cursor.execute(f"SELECT * FROM usersinfo WHERE phone = '{user[4]}'", )
        users = cursor.fetchone()
        for i in json.loads(users[2]):
         if i['phone'] == phone2:
            close_db_connection()
            return {"status" : "False" , "error" : "Kullanıcı Zaten Kayıtlı."}


        data = {"phone": "", "email": "", "name": "", "surname": "" , "notification" : notuser[8]}
        data['phone'] = phone2
        data['email'] = email
        data['name'] = name
        data['surname'] = surname
        loaded = json.loads(users[2])
        loaded.append(data)




        cursor.execute('UPDATE usersinfo SET rehber = ? WHERE phone = ?', (json.dumps(loaded), user[4]))
        connection.commit()
        close_db_connection()
        return {"status":"True"}
     else:
        return {"status": "False" , "error" : "Kullanıcı adı veya şifre hatalı."}
    else:
     return {"status": "False", "error": "Lütfen gerekli parametreleri giriniz."}

"""@app.get("/getcontact")
def getcontact(request : Request):
 args = request.query_params
 username = args.get("username",None)
 password = args.get("password",None)
 if username and password != None:
    user = authenticate_user(username,password)
    if user:
       connection = get_db_connection()
       cursor = connection.cursor()
       cursor.execute(f"SELECT * FROM usersinfo WHERE phone = '{user[4]}'", )
       users = cursor.fetchone()
       loaded = json.loads(users[2])

       for i in loaded:
          cursor.execute(f"SELECT * FROM usersinfo WHERE phone = '{i['phone']}'")
          getuser = cursor.fetchone()
          i['status'] = getuser[4]


       close_db_connection()
       return {"status": "True", "rehber": loaded}
    else:
       return {"status": "False", "error": "Kullanıcı adı veya şifre hatalı."}
 else:
    return {"status": "False", "error": "Lütfen gerekli parametreleri giriniz."}"""
 

@app.post("/getcontact")
async def get_contact(request: Request):
    data = await request.json()
    username = data.get("username", None)
    password = data.get("password", None)
    phone = data.get("phone", None)

    if username and password and phone is not None:
        user = authenticate_user(username, password)
        if user:
            phone = json.loads(phone)
            phonenumbers = []

            connection = get_db_connection()
            cursor = connection.cursor()

            
            for i in phone:
                    iphone = phoneduzelt(i['phone'])
                    cursor.execute(f"SELECT * FROM usersinfo WHERE phone = '{iphone}'")
                    check = cursor.fetchone()

                    if check:
                        # Eğer aynı telefon numarası daha önce eklenmemişse listeye ekle
                        if iphone not in [item['phone'] for item in phonenumbers]:
                            phonenumbers.append({"name": i['name'], "phone": iphone , "status" : check[4], "photo" : check[7]})

                # Tüm kayıtları tek seferde güncelle
            cursor.execute('UPDATE usersinfo SET rehber = ? WHERE phone = ?', (json.dumps(phonenumbers), user[4]))
            connection.commit()

            return phonenumbers
            
                
        else:
            return {"status": "False", "error": "Kullanıcı adı veya şifre hatalı."}
    else:
        return {"status": "False", "error": "Lütfen gerekli parametreleri giriniz."}



@app.get("/removecontact")
def removecontact(request: Request):
 args = request.query_params
 username = args.get("username", None)
 password = args.get("password",None)
 phone = args.get("phone", None)
 phone = phoneduzelt(phone)
 if username and password and phone != None:
  user = authenticate_user(username,password)
  if user:
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute(f"SELECT * FROM usersinfo WHERE phone = '{user[4]}'", )
    users = cursor.fetchone()
    loaded = json.loads(users[2])
    my_list = [item for item in loaded if phone not in item['phone']]
    dumped = json.dumps(my_list)

    cursor.execute('UPDATE usersinfo SET rehber = ? WHERE phone = ?', (dumped, user[4]))
    connection.commit()
    close_db_connection()
    return {"status" :"True"}
  else:
     return {"status": "False", "error": "Kullanıcı adı veya şifre hatalı."}
 else:
    return {"status" : "False" , "error" : "Lütfen gerekli parametreleri giriniz."}


@app.get("/stats")
def getstat():
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute(f"SELECT * FROM users")
    user = cursor.fetchall()

    json_data = json_oku("stats.json")
    data = {"status" :"True" , "yardim": json_data['yardim'] , "users" : len(user)}
    return data


@app.get("/setstatus")
def setstatus(request : Request):
 args = request.query_params
 username = args.get("username",None)
 password = args.get("password",None)
 status = args.get("status",None)

 if username and password and status != None :
    user = authenticate_user(username,password)
    if user:
       connection = get_db_connection()
       cursor = connection.cursor()

       connection = get_db_connection()
       cursor = connection.cursor()
       cursor.execute(f"SELECT * FROM usersinfo WHERE phone = '{user[4]}'", )
       users = cursor.fetchone()
       loaded = users[2]
       notification_liste = []
       try:  
        for i in loaded:
          notification_liste.append(i['notification'])
       except:
        pass
       if status == "help" or status == "nice" or status == "empty" or status == "danger":

                if notification_liste:
                 if type(notification_liste) == list:

                   for i in notification_liste:
                    if status == "help":
                     send_push_notification(i,"❗ACİL DURUM UYARISI❗",user[1] + " " + user[2] + " " + "adlı kullanıcı enkaz altında olabilir lütfen sakinliğinizi koruyunuz.")
                    elif status == "danger":
                       send_push_notification(i,"❗ACİL DURUM UYARISI❗",user[1] + " " + user[2] + " " + "adlı kullanıcı tehlikede olabilir lütfen sakinliğinizi koruyunuz.")

                mevcut_zaman = datetime.datetime.now()
                formatli_zaman = mevcut_zaman.strftime("%Y-%m-%d:%H-%M")
                cursor.execute('UPDATE usersinfo SET durum = ? WHERE phone = ?', (status, user[4]))
                cursor.execute('UPDATE usersinfo SET durumtime = ? WHERE phone = ?', (str(formatli_zaman), user[4]))


                connection.commit()
                return {"status": "True", "durum": status}
       else:
        return {"status": "False", "error": "Yanlış parametre. help/empty/nice/danger"}      
    else:
       return {"status": "False", "error": "Kullanıcı adı veya şifre hatalı."}
 else:
    return {"status": "False", "error": "Lütfen gerekli parametreleri giriniz."}


@app.get("/getstatus")
def getstatus(request : Request):
 args = request.query_params
 username = args.get("username",None)
 password = args.get("password",None)
 if username and password != None:
    user = authenticate_user(username,password)
    if user:
     connection = get_db_connection()
     cursor = connection.cursor()
     cursor.execute(f"SELECT * FROM usersinfo WHERE phone = '{user[4]}'", )
     users = cursor.fetchone()
     close_db_connection()
     return {"status": "True", "durum": users[4]}
    else:
      return {"status": "False", "error": "Kullanıcı adı veya şifre hatalı."} 
 else:
    return {"status": "False", "error": "Lütfen gerekli parametreleri giriniz."}

@app.get("/changepassword")
def chgpassword(request: Request):
   args = request.query_params
   username = args.get("username",None)
   password = args.get("password",None)
   newpassword = args.get("newpassword",None)
   if username and password and newpassword != None:
      user = authenticate_user(username,password)
      if user:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute('UPDATE users SET password = ? WHERE phone = ?', (newpassword, user[4]))
        connection.commit()
        close_db_connection()
        return {"status" : "True"}
      else:
         return {"status": "False", "error": "Şifre hatalı."}     
   else:
      return {"status": "False", "error": "Lütfen gerekli parametreleri giriniz."}


@app.get('/news')   
def news():
    with open('news.json') as user_file:
        data = json.load(user_file)
        return {"status" : "True" , "data" : data['data']}






@app.get("/forgotpassword")
def forgotpassword(request : Request):
   args = request.query_params
   code = args.get("code",None)
   email = args.get("email",None)
   password = args.get("password",None)
   if email and password is not None:
       connection = get_db_connection()
       cursor = connection.cursor()
       cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
       user = cursor.fetchone()
       if user:
          jsondata = json_oku("forgot.json")
          for i in jsondata['data']:
             if email == i['email']:
                if i['access'] == "True":


                   cursor.execute('UPDATE users SET password = ? WHERE phone = ?', (password, user[4]))
                   connection.commit()

                   return {"status" : "True" , "message" : "Şifre Başarı ile değiştirildi!"}
                else:
                   return {"status" : "False" , "error" : "Doğrulama kodunu giriniz!"}
          return {"status" : "False" , "message" : "Bir hata oluştu."}
       else:
          return {"status" : "False" , "error" : "Kullanıcı bulunamadı!"}
   elif code and email is not None:
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
    user = cursor.fetchone()
    if user:
        jsondata = json_oku("forgot.json")
        for i in jsondata['data']:
          if i['email'] == email:
             if code == i['code']:
                i['access'] = "True"
                json_yaz(jsondata,"forgot.json")
                return {"status" : "True" , "message" : "Başarılı!"}
        return {"status" : "False", "error" : "Kod yanlış!"}          
    else:
       return {"status" : "False", "error" : "Kullanıcı bulunamadı!"}
   elif email is not None and code == None: 
       connection = get_db_connection()
       cursor = connection.cursor()
       cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
       user = cursor.fetchone()
       if user:
          code = generate_random_code()
          jsondata = json_oku("forgot.json")
          matching_items = [item for item in jsondata['data'] if item['email'] != email]
          datas = {"email" : email , "code" : code , "access" : "False"}
          matching_items.append(datas)
          jsondata['data'] = matching_items
          json_yaz(jsondata,"forgot.json")
          close_db_connection()

          otpmailgönder(code,email)
          return {"status" :"True" , "code" : code, "email" : email}
       else:
          return {"status" : "False", "error" : "Kullanıcı bulunamadı!"}

############################## FAMİLY #####################################
@app.get("/createfamily")
def createfamily(request: Request):
   args = request.query_params
   username = args.get("email",None)
   password = args.get("password",None)
   name = args.get("name",None)
   adres = args.get("adres",None)
   binaname = args.get("binaname",None)


   if username and password and name and adres and binaname != None:
      user = authenticate_user(username,password)
      if user:
         json_users = {
               "phone" : user[4],
               "name": user[1],
               "surname" : user[2],
               "tcnumber" : user[7],
               "dogumyil" : user[8]

            }
         connection = get_db_connection()
         cursor = connection.cursor()
         cursor.execute(f"SELECT * FROM usersinfo WHERE phone = '{user[4]}'", )
         users = cursor.fetchone()
         phonenum = user[4]
         close_db_connection()
         if users[6] == None:
            connection = get_db_connection()
            cursor = connection.cursor()
            cursor.execute(f"SELECT * FROM usersinfo WHERE phone = '{user[4]}'", )
            user = cursor.fetchone()
            cursor.execute(f"SELECT * FROM families" )
            users = cursor.fetchall()
            new_code = generate_family_code()  

            for i in users:

              #if phonenum in i[1]:
                #  return {"status" : "False" , "error" : "Zaten aile oluşturmuşsunuz."}
              if new_code in i[2]:
               new_code = generate_family_code()

            cursor.execute('''
                INSERT INTO families (phone,code, users, name,childs,binaplan,adres,binaname)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (phonenum,new_code,json.dumps([json_users]),name,json.dumps([]),"",adres,binaname))
            connection.commit()

            cursor.execute('UPDATE usersinfo SET ailecode = ? WHERE phone = ?', (new_code, phonenum))
            connection.commit()
            close_db_connection()
            return {"status" : "True" , "message": "Aile oluşturma başarılı." }
         else :
            return {"status" : "False" , "error" : "Zaten aile oluşturmuşsunuz."}
      else:
         return {"status": "False", "error": "Şifre hatalı."}     
   else:
      return {"status": "False", "error": "Lütfen gerekli parametreleri giriniz."}

@app.get("/joinfamily")
def joinfamily(request : Request):
   args = request.query_params
   username = args.get("email",None)
   password = args.get("password",None)
   code = args.get("code",None)
   if username and password and code != None:
      user = authenticate_user(username,password)
      if user:
         connection = get_db_connection()
         cursor = connection.cursor()
         cursor.execute("SELECT * FROM families WHERE code = ?", (code,))
         familylist = cursor.fetchone()
         if familylist:

            json_data = json.loads(familylist[3])
            for i in json_data:
               if i['phone'] == user[4]:
                  return {"status" : "False" , "error" : "Zaten halihazırda bu ailenin üyesisiniz."}

            cursor.execute(f"SELECT * FROM usersinfo WHERE phone = '{user[4]}'", )
            users = cursor.fetchone()

            if users[6] is not None:
               return {"status" : "False" , "error" : "Zaten halihazırda bir ailenin üyesisiniz önce ayrılmanız gerekmektedir."}


            json_users = {
               "phone" : user[4],
               "name": user[1],
               "surname" : user[2],
               "tcnumber" : user[7],
               "dogumyil" : user[8],
            
            }
            json_data.append(json_users)
            cursor.execute('UPDATE families SET users = ? WHERE code = ?', (json.dumps(json_data), code))
            connection.commit()
            cursor.execute('UPDATE usersinfo SET ailecode = ? WHERE phone = ?', (code, user[4]))
            connection.commit()

            return {"status" : "True" , "message" : "Başarılı"}


         else:
            return {"status" : "False", "error" : "Girilen aile kodu geçersiz."}
      else:
       return {"status": "False", "error": "Giriş başarısız."}      
   else:
      return {"status": "False", "error": "Lütfen gerekli parametreleri giriniz."}


@app.get("/myfamily")
def myfamily(request : Request):
   args = request.query_params
   username = args.get("email",None)
   password = args.get("password",None)
   if username and password != None:
      user = authenticate_user(username,password)
      if user:
         connection = get_db_connection()
         cursor = connection.cursor()
         cursor.execute(f"SELECT * FROM usersinfo WHERE phone = '{user[4]}'", )
         usersinfo = cursor.fetchone()
         ailecode = usersinfo[6]
         if ailecode is not None:
             cursor.execute("SELECT * FROM families WHERE code = ?", (ailecode,))
             familylist = cursor.fetchone()
             return {"status": "True", "code": ailecode,"data":json.loads(familylist[3]),"name": familylist[4] , "child" : json.loads(familylist[5]),"bina" : familylist[6] , "adres" : familylist[7], "binaname" : familylist[8]}
         else:
            return {"status" : "False", "error" : "Henüz bir ailede değilsiniz."}
      else:
         return {"status": "False", "error": "Giriş başarısız."}  
   else:
      return {"status": "False", "error": "Lütfen gerekli parametreleri giriniz."}

@app.get("/leavefamily")
def leavefamily(request : Request):
   args = request.query_params
   username = args.get("email",None)
   password = args.get("password",None)
   if username and password != None:
      user = authenticate_user(username,password)
      if user:
         connection = get_db_connection()
         cursor = connection.cursor()
         cursor.execute(f"SELECT * FROM usersinfo WHERE phone = '{user[4]}'", )
         usersinfo = cursor.fetchone()
         ailecode = usersinfo[6]
         if ailecode is not None:
             cursor.execute("SELECT * FROM families WHERE code = ?", (ailecode,))
             familylist = cursor.fetchone()
             json_data = json.loads(familylist[3])

             data = [item for item in json_data if int(item['tcnumber']) != int(user[7])]
             cursor.execute('UPDATE families SET users = ? WHERE code = ?', (json.dumps(data), ailecode))
             cursor.execute('UPDATE usersinfo SET ailecode = ? WHERE phone = ?', (None, user[4]))
             connection.commit()
             return {"status" : "True", "message": "Başarılı!"}
         else:
            return {"status" : "False", "error" : "Henüz bir ailede değilsiniz."}
      else:
         return {"status": "False", "error": "Giriş başarısız."}  
   else:
     return {"status": "False", "error": "Lütfen gerekli parametreleri giriniz."}



@app.get("/deletefamily")
def deletefamily(request: Request):
   args = request.query_params
   username = args.get("email",None)
   password = args.get("password",None)
   if username and password != None:
      user = authenticate_user(username,password)
      if user:
         connection = get_db_connection()
         cursor = connection.cursor()
         cursor.execute(f"SELECT * FROM usersinfo WHERE phone = '{user[4]}'", )
         usersinfo = cursor.fetchone()
         ailecode = usersinfo[6]
         if ailecode is not None:
             cursor.execute("SELECT * FROM families WHERE code = ?", (ailecode,))
             familylist = cursor.fetchone()
             json_data = json.loads(familylist[3])
             cursor.execute('DELETE FROM families WHERE code = ?;', (ailecode,))
             connection.commit()
             for i in json_data:
                try:
                 cursor.execute('UPDATE usersinfo SET ailecode = ? WHERE phone = ?', (None, i['phone']))
                 connection.commit()
                except:
                   pass
             return {"status" : "True", "message": "Başarılı!"}
         else:
            return {"status" : "False", "error" : "Henüz bir ailede değilsiniz."}
      else:
         return {"status": "False", "error": "Giriş başarısız."}  
   else:
     return {"status": "False", "error": "Lütfen gerekli parametreleri giriniz."}   

@app.post("/addchild")
async def addchild(request: Request):
    data = await request.json()
    photo = data.get("photo", None)
    email = data.get("email", None)
    password = data.get("password", None)
    tcnumber = data.get("tc", None)
    name = data.get("name", None)
    surname = data.get("surname", None)
    birthday = data.get("birthday", None)
    kangrup = data.get("kan",None)


    if email and password and tcnumber and name and surname and birthday and kangrup is not None:
        user = authenticate_user(email, password)
        if user:
            if tc_kimlik_dogrula(tcnumber):
                True
            else:
                return {"status": "False", "error": "Girilen tc kimlik numarası geçersiz."}

            connection = get_db_connection()
            cursor = connection.cursor()
            cursor.execute(f"SELECT * FROM users WHERE tcnumber = '{tcnumber}'",)
            child_tc = cursor.fetchone()

            if child_tc:
                return {"status": "False", "error": "Tc kimlik numarası ile zaten kayıt olunmuş. Lütfen davet linki gönderiniz."}

            cursor.execute(f"SELECT * FROM usersinfo WHERE phone = '{user[4]}'",)
            users_info = cursor.fetchone()
            family_code = users_info[6]

            if family_code is not None:
                cursor.execute("SELECT * FROM families WHERE code = ?", (family_code,))
                family_list = cursor.fetchone()
                json_data = json.loads(family_list[5])

                for i in json_data:
                    if tcnumber == i['tc']:
                        return {"status": "False", "error": "Kullanıcı zaten eklenmiş."}

                kanlar = ["Arh+","Arh-","Brh+","Brh-","ABrh+","ABrh-","0rh+","0rh-"]
                if kangrup not in kanlar:
                 return {"status" : "False" , "error" : "Lütfen geçerli kan grubu giriniz. "}

                jsonn_veri = {"tc": tcnumber, "name": name, "surname": surname, "birthday": birthday, "photo": photo, "kan" : kangrup}
                json_data.append(jsonn_veri)
                cursor.execute('UPDATE families SET childs = ? WHERE code = ?', (json.dumps(json_data), family_code))
                connection.commit()

                return {"status": "True", "message": "Başarılı!"}
            else:
                return {"status": "False", "error": "Henüz bir ailede değilsiniz."}
        else:
            return {"status": "False", "error": "Giriş başarısız."}
    else:
        return {"status": "False", "error": "Lütfen gerekli parametreleri giriniz."} 

@app.get("/removechild")
def removechild(request : Request):
   args = request.query_params
   username = args.get("email",None)
   password = args.get("password",None)
   tcnumber = args.get("tc",None)

   if username and password and tcnumber != None:

      user = authenticate_user(username,password)
      if user:
         if tc_kimlik_dogrula((tcnumber)):
          True
         else:
          return {"status" : "False" , "error": "Girilen tc kimlik numarası geçersiz." }
         connection = get_db_connection()
         cursor = connection.cursor()
         cursor.execute(f"SELECT * FROM users WHERE tcnumber = '{tcnumber}'", )
         childtc = cursor.fetchone()
         if childtc:
            return {"status" : "False" , "error" : "Tc kimlik numarası ile zaten kayıt olunmuş çocuk hesap kategorisine girmemektedir."}

         cursor.execute(f"SELECT * FROM usersinfo WHERE phone = '{user[4]}'", )
         usersinfo = cursor.fetchone()
         ailecode = usersinfo[6]
         if ailecode is not None:
             cursor.execute("SELECT * FROM families WHERE code = ?", (ailecode,))
             familylist = cursor.fetchone()
             json_data = json.loads(familylist[5])
             data = [item for item in json_data if int(item['tc']) != int(tcnumber)]
             cursor.execute('UPDATE families SET childs = ? WHERE code = ?', (json.dumps(data), ailecode))
             connection.commit()
             return {"status" : "True", "message": "Başarılı!"}
         else:
            return {"status" : "False", "error" : "Henüz bir ailede değilsiniz."}
      else:
         return {"status": "False", "error": "Giriş başarısız."}  
   else:
     return {"status": "False", "error": "Lütfen gerekli parametreleri giriniz."} 

@app.get("/removefamily")
def removefamily(request : Request):
   args = request.query_params
   username = args.get("email",None)
   password = args.get("password",None)
   tcnumber = args.get("tc",None)
   if username and password and tcnumber != None:
      user = authenticate_user(username,password)
      if user:
         if tc_kimlik_dogrula((tcnumber)):
          True
         else:
          return {"status" : "False" , "error": "Girilen tc kimlik numarası geçersiz." }
         if user[7] == tcnumber:
            return {"status" : "False" , "error" : "Kendinizi çıkartamazsınız onun yerine aileden ayrılmayı deneyin..."}
         connection = get_db_connection()
         cursor = connection.cursor()
         cursor.execute(f"SELECT * FROM users WHERE tcnumber = '{tcnumber}'", )
         childtc = cursor.fetchone()
         if childtc:
          cursor.execute(f"SELECT * FROM usersinfo WHERE phone = '{user[4]}'", )
          usersinfo = cursor.fetchone()
          ailecode = usersinfo[6]
          if ailecode is not None:
             cursor.execute("SELECT * FROM families WHERE code = ?", (ailecode,))
             familylist = cursor.fetchone()
             json_data = json.loads(familylist[3])
             data = [item for item in json_data if int(item['tcnumber']) != int(tcnumber)]
             cursor.execute('UPDATE families SET users = ? WHERE code = ?', (json.dumps(data), ailecode))
             cursor.execute('UPDATE usersinfo SET ailecode = ? WHERE phone = ?', (None, childtc[4]))
             connection.commit()
             return {"status" : "True", "message": "Başarılı!"}
          else:
             return {"status" : "False", "error" : "Henüz bir ailede değilsiniz."}
         else: 
          return {"status" : "False" , "error" : "Tc kimlik numarası bulunamadı."}
      else:
         return {"status": "False", "error": "Giriş başarısız."}  
   else:
     return {"status": "False", "error": "Lütfen gerekli parametreleri giriniz."} 

############################## BİNA PLANLARI #############################

@app.post("/addbina")
async def addplan(request: Request):
   data = await request.json()
   username = data.get("email",None)
   password = data.get("password",None)
   binaresim = data.get("plan",None)
   if username and password and binaresim != None:
      user = authenticate_user(username,password)
      if user:
         connection = get_db_connection()
         cursor = connection.cursor()
         cursor.execute(f"SELECT * FROM usersinfo WHERE phone = '{user[4]}'", )
         usersinfo = cursor.fetchone()
         ailecode = usersinfo[6] 
         if ailecode is not None:
             cursor.execute("SELECT * FROM families WHERE code = ?", (ailecode,))
             familylist = cursor.fetchone()
             json_data = (familylist[6])
             cursor.execute('UPDATE families SET binaplan = ? WHERE code = ?', (binaresim, ailecode))
             connection.commit()
             return {"status" : "True", "message": "Başarılı!"}
         else:
             return {"status" : "False", "error" : "Henüz bir ailede değilsiniz."}       
      else:
         return {"status": "False", "error": "Giriş başarısız."}
   else:
     return {"status": "False", "error": "Lütfen gerekli parametreleri giriniz."}

@app.get("/removebina")
def addplan(request: Request):
   args = request.query_params
   username = args.get("email",None)
   password = args.get("password",None)

   if username and password != None:
      user = authenticate_user(username,password)
      if user:
         connection = get_db_connection()
         cursor = connection.cursor()
         cursor.execute(f"SELECT * FROM usersinfo WHERE phone = '{user[4]}'", )
         usersinfo = cursor.fetchone()
         ailecode = usersinfo[6] 
         if ailecode is not None:
             cursor.execute("SELECT * FROM families WHERE code = ?", (ailecode,))
             familylist = cursor.fetchone()
             json_data = (familylist[6])
             cursor.execute('UPDATE families SET binaplan = ? WHERE code = ?', ("", ailecode))
             connection.commit()
             return {"status" : "True", "message": "Başarılı!"}
         else:
             return {"status" : "False", "error" : "Henüz bir ailede değilsiniz."}       
      else:
         return {"status": "False", "error": "Giriş başarısız."}
   else:
     return {"status": "False", "error": "Lütfen gerekli parametreleri giriniz."}


############################## ADMİN #####################################
@app.get("/allusers")
def allusers(request: Request):
   args = request.query_params
   username = args.get("email",None)
   password = args.get("password",None)
   if username and password != None:
      user = authenticate_user(username,password)
      if user:
         if user[6] == "admin":
           connection = get_db_connection()
           cursor = connection.cursor()
           cursor.execute("SELECT * FROM users")
           users  = cursor.fetchall()
           userslist = []
           for i in users:
              jsonn = {"name" : i[1] , "surname" : i[2] , "email" : i[3],  "phone" : i[4] , "role" : i[6] ,"tcnumber" : i[7] , "dogumyil" : i[8]}
              userslist.append(jsonn)

           return {"status" : "True" , "users" : userslist}
         else:
            return {"status" : "False", "error" : "Yetkiniz yok!"}
      else:
         return {"status": "False", "error": "Kullanıcı adı ve şifre hatalı."}

   else:
      return {"status" : "False","error" : "Gerekli parametreli giriniz."}

@app.get("/addmessage")
def addmessage(request : Request):
   args = request.query_params
   name = args.get("name",None)
   email = args.get("email",None)
   konu = args.get("konu",None)
   mesaj = args.get("message",None)
   if mesaj and konu and email and name != None:
      connection = get_db_connection()
      cursor = connection.cursor()
      cursor.execute('''INSERT INTO messages (name, email, konu, mesaj) 
                          VALUES (?, ?, ?, ?)''', (name, email, konu, mesaj))
      connection.commit()
      return {"status" : "True", "message" : "Başarıyla gönderildi."}
   else:
      return {"status": "False", "error": "Gerekli parametreleri giriniz!"}

@app.get("/getmessage")
def getmessage(request : Request):
   args = request.query_params
   username = args.get("username",None)
   password = args.get("password",None)
   if username and password != None:
      user = authenticate_user(username,password)
      if user:
         if user[6] == "admin":
           connection = get_db_connection()
           cursor = connection.cursor()
           cursor.execute("SELECT * FROM messages")
           users  = cursor.fetchall()
           userslist = []
           for i in users:
              jsonn = {"name" : i[1] , "email" : i[2] , "konu" : i[3],  "mesaj" : i[4]}
              userslist.append(jsonn)

           return {"status" : "True" , "users" : userslist}
         else:
            return {"status": "False" ,"error" : "Yetkiniz Yok!"}
      else:
         return {"status" : "False","error" : "Kullanıcı adı veya şifre hatalı!"}
   else:
      return {"status": "False","error" : "Gerekli parametreleri giriniz!"}

@app.get("/removeuser")
def getmessage(request: Request):
   args = request.query_params
   username = args.get("username",None)
   password = args.get("password",None)
   phone = args.get("phone",None)

   if username and password and phone != None:
      phone = phoneduzelt(phone)
      user = authenticate_user(username,password)
      if user:
         if user[6] == "admin":
            connection = get_db_connection()
            cursor = connection.cursor()
            cursor.execute("DELETE FROM users WHERE phone = ?", (phone,))
            cursor.execute("DELETE FROM usersinfo WHERE phone = ?", (phone,))
            connection.commit()

            return {"status": "True"}
         else:
            return {"status" : "False" , "error" : "Yetkiniz Yok!"}
      else:
         return {"status" : "False", "error" : "Kullanıcı adı veya şifre hatalı!"}
   else:
      return {"stauts": "False", "error" : "Gerekli parametreleri giriniz!"}


@app.get("/giverole")
def giverole(request : Request):
   args = request.query_params
   username = args.get("username",None)
   password = args.get("password",None)
   phone = args.get("phone",None)
   key = args.get("key",None)
   role = args.get("role",None)
   if username and password and role and phone != None:

      phone = phoneduzelt(phone)
      user = authenticate_user(username,password)
      if user:
        if key == "ber4tbeyselam":
         
            connection = get_db_connection()
            cursor = connection.cursor()
            cursor.execute('UPDATE users SET role = ? WHERE phone = ?', (role, phone))
            connection.commit()
            return {"status": "True"}
         
            
        else:
           return {"status" :  "False" , "error" : "Key hatalı"}
      else:
         return {"status" : "False", "error" : "Kullanıcı adı veya şifre hatalı!"}
   else:
      return {"stauts": "False", "error" : "Gerekli parametreleri giriniz!"}

@app.get("/getusers")
def getusers(request: Request):
    args = request.query_params
    username = args.get("username", None)
    password = args.get("password", None)
    name = args.get("name", None)
    surname = args.get("surname", None)
    tckimlik = args.get("tckimlik")
    phone = args.get("phone", None)
    if phone is not None:
     phone = phoneduzelt(phone)

    if username and password is not None:
        user = authenticate_user(username, password)
        if user:
            if user[6] == "sar":
                connection = get_db_connection()
                cursor = connection.cursor()
                query = "SELECT * FROM usersinfo WHERE 1=1"
                params = {}

                if name:
                    query += " AND LOWER(name) = LOWER(:name)"
                    params["name"] = name.lower().strip()

                if surname:
                    query += " AND LOWER(surname) = LOWER(:surname)"
                    params["surname"] = surname.lower().strip()

                if tckimlik:
                    query += " AND tckimlik = :tckimlik"
                    params["tckimlik"] = tckimlik

                if phone:
                    query += " AND phone = :phone"
                    params["phone"] = phone

                cursor.execute(query, params)
          
                users = cursor.fetchall()

                userlist = []
                for i in users:
                   data = {"name" : i[9] , "surname": i[10] ,"tcnumber": i[11], "kangrup" : i[12],"phone": i[1] , "rehber" : i[2] , "durum" : i[4] , "durumtime" : i[5], "ailecode" : i[6] , "photo" : i[7]}
                   userlist.append(data)
                return {"status" : "True", "data" : userlist}
            else:
                return {"status": "False", "error": "Yetkiniz Yok!"}
        else:
            return {"status": "False", "error": "Kullanıcı adı veya şifre hatalı!"}
    else:
        return {"status": "False", "error": "Gerekli parametreleri giriniz!"}







@app.get("/sehirler")
def get_sehirler():
    return JSONResponse(content=sehir_data[2]['data'])

@app.get("/ilceler/{sehir_id}")
def get_ilceler(sehir_id: int):
    ilceler = [ilce for ilce in ilce_data[2]['data'] if ilce["ilce_sehirkey"] == str(sehir_id)]
    if not ilceler:
        raise HTTPException(status_code=404, detail="İlçe bulunamadı")
    return JSONResponse(content=ilceler)

@app.get("/mahalleler/{ilce_key}")
def get_mahalleler(ilce_key: int):
    mahalleler = [mahalle for mahalle in mahalle_data[2]['data'] if mahalle["mahalle_ilcekey"] == str(ilce_key)]
    if not mahalleler:
        raise HTTPException(status_code=404, detail="Mahalle bulunamadı")
    return JSONResponse(content=mahalleler)

@app.get("/sokaklar/{mahalle_key}")
def get_sokaklar(mahalle_key: int):
    sokaklar = [sokak for sokak in sokak_data[2]['data'] if sokak["sokak_cadde_mahallekey"] == str(mahalle_key)]
    if not sokaklar:
        raise HTTPException(status_code=404, detail="Sokak bulunamadı")
    return JSONResponse(content=sokaklar)



@app.get("/sondepremler")
def getmessage():
   return getKandilliData()

@app.get("/enyüksek")
def getmessagee():
    data = getKandilliData()

    if not data:
        return {"message": "Veri bulunamadı."}

    mw_values = [item["mag"] for item in data]
    max_mw = max(mw_values)
    min_mw = min(mw_values)

    max_index = mw_values.index(max_mw)
    min_index = mw_values.index(min_mw)

    return {"max": data[max_index], "min": data[min_index]}

import random
def generate_random_code():
    code = ''.join(random.choices('0123456789', k=6))
    return code


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=80 )
