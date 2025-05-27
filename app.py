from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_migrate import Migrate

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_mail import Mail, Message
from flask_wtf.csrf import CSRFProtect
import urllib
from datetime import datetime, timedelta
import threading
import time
import hashlib # hashlib importunu tekrar ekledim
import random # Bu satırı ekledim
import os
from werkzeug.utils import secure_filename
import secrets

app = Flask(__name__)
# app.config['SECRET_KEY'] = secrets.token_hex(16) # Daha güvenli bir anahtar oluştur - Bu satırı devre dışı bırak
app.config['SECRET_KEY'] = 'bu-sabit-bir-test-anahtaridir' # TEST AMAÇLI SABİT ANAHTAR

# MSSQL bağlantı parametreleri
driver = "ODBC Driver 17 for SQL Server"
server = "MSI\\SQLK"
database = "ReviseMe"

connection_string = f"DRIVER={{{driver}}};SERVER={server};DATABASE={database};Trusted_Connection=yes;TrustServerCertificate=yes;MARS_Connection=yes;"
params = urllib.parse.quote_plus(connection_string)

# SQLAlchemy ayarları
app.config['SQLALCHEMY_DATABASE_URI'] = f"mssql+pyodbc:///?odbc_connect={params}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# CSRF koruması
csrf = CSRFProtect(app)

# Mail ayarları
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your-email@gmail.com'  # Gmail adresin
app.config['MAIL_PASSWORD'] = 'your-app-password'     # Gmail uygulama şifren
app.config['MAIL_DEFAULT_SENDER'] = 'your-email@gmail.com'

# SendGrid ayarları
app.config['SENDGRID_API_KEY'] = 'YOUR_SENDGRID_API_KEY'
app.config['SENDGRID_FROM_EMAIL'] = 'your-verified-sender@yourdomain.com'

# SQLAlchemy nesnesi
db = SQLAlchemy(app)

migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
mail = Mail(app)

# Database Models
class User(UserMixin, db.Model):
    __tablename__ = 'Users'
    UserId = db.Column(db.Integer, primary_key=True)
    UserName = db.Column(db.String(50), unique=True, nullable=False)
    PasswordHash = db.Column(db.String(128), nullable=False)
    Name = db.Column(db.String(50))
    Surname = db.Column(db.String(50))
    Class = db.Column(db.String(50))
    YearOfBirth = db.Column(db.Integer)
    Area = db.Column(db.String(50))
    Aim = db.Column(db.String(100))
    Email = db.Column(db.String(100))
    PhoneNumber = db.Column(db.String(20))
    GoogleAuthId = db.Column(db.String(100))
    SecurityQuestion = db.Column(db.String(200))

    def get_id(self):
        return str(self.UserId)
        
    def can_modify(self, question):
        return self.UserId == question.UserId

class Category(db.Model):
    __tablename__ = 'Categories'
    CategoryId = db.Column(db.Integer, primary_key=True)
    Name = db.Column(db.String(50))

class Question(db.Model):
    __tablename__ = 'Questions'
    
    QuestionId = db.Column(db.Integer, primary_key=True)
    UserId = db.Column(db.Integer, db.ForeignKey('Users.UserId'), nullable=False)
    Content = db.Column(db.Text, nullable=False)
    CategoryId = db.Column(db.Integer, db.ForeignKey('Categories.CategoryId'), nullable=False)
    Topic = db.Column(db.String(100))
    DifficultyLevel = db.Column(db.String(20))
    PhotoPath = db.Column(db.String(255))
    IsRepeated = db.Column(db.Boolean, default=False)
    RepeatCount = db.Column(db.Integer, default=0)
    Repeat1Date = db.Column(db.DateTime)
    Repeat2Date = db.Column(db.DateTime)
    Repeat3Date = db.Column(db.DateTime)
    IsCompleted = db.Column(db.Boolean, default=False)
    IsViewed = db.Column(db.Boolean, default=False)
    Explanation = db.Column(db.Text)
    ImagePath = db.Column(db.String(255))
    IsHidden = db.Column(db.Boolean, default=False)
    
    user = db.relationship('User', backref=db.backref('questions', lazy=True))
    category = db.relationship('Category', backref=db.backref('questions', lazy=True))

class Note(db.Model):
    __tablename__ = 'Notes'
    NoteId = db.Column(db.Integer, primary_key=True)
    QuestionId = db.Column(db.Integer, db.ForeignKey('Questions.QuestionId'))
    Content = db.Column(db.Text)
    
    question = db.relationship('Question', backref='notes')

class Favorite(db.Model):
    __tablename__ = 'Favorites'
    FavoriteId = db.Column(db.Integer, primary_key=True)
    QuestionId = db.Column(db.Integer, db.ForeignKey('Questions.QuestionId'), nullable=False)
    UserId = db.Column(db.Integer, db.ForeignKey('Users.UserId'), nullable=False)
    
    # İlişkiler
    question = db.relationship('Question', backref='favorites')
    user = db.relationship('User', backref='favorites')

class Notification(db.Model):
    __tablename__ = 'Notifications'
    NotificationId = db.Column(db.Integer, primary_key=True)
    UserId = db.Column(db.Integer, db.ForeignKey('Users.UserId'))
    NotificationType = db.Column(db.String(50))
    Schedule = db.Column(db.DateTime)
    
    user = db.relationship('User', backref='notifications')

class PasswordResetToken(db.Model):
    __tablename__ = 'PasswordResetTokens'
    TokenId = db.Column(db.Integer, primary_key=True)
    UserId = db.Column(db.Integer, db.ForeignKey('Users.UserId'), nullable=False)
    Token = db.Column(db.String(100), unique=True, nullable=False)
    ExpiresAt = db.Column(db.DateTime, nullable=False)
    IsUsed = db.Column(db.Boolean, default=False)
    
    user = db.relationship('User', backref='password_reset_tokens')

class TedTalk(db.Model):
    __tablename__ = 'TedTalks'
    TalkId = db.Column(db.Integer, primary_key=True)
    Title = db.Column(db.String(200), nullable=False)
    Speaker = db.Column(db.String(100), nullable=False)
    VideoUrl = db.Column(db.String(500), nullable=False)
    Description = db.Column(db.Text)
    Duration = db.Column(db.String(50))
    Category = db.Column(db.String(100))
    IsWatched = db.Column(db.Boolean, default=False)
    UserId = db.Column(db.Integer, db.ForeignKey('Users.UserId'), nullable=False)
    user = db.relationship('User', backref='ted_talks')

class Book(db.Model):
    __tablename__ = 'Books'
    BookId = db.Column(db.Integer, primary_key=True)
    Title = db.Column(db.String(200))
    Author = db.Column(db.String(100))
    CurrentPage = db.Column(db.Integer)
    TotalPages = db.Column(db.Integer)
    StartDate = db.Column(db.DateTime)
    UserId = db.Column(db.Integer, db.ForeignKey('Users.UserId'))
    user = db.relationship('User', backref='books')

class BookQuote(db.Model):
    __tablename__ = 'BookQuotes'
    QuoteId = db.Column(db.Integer, primary_key=True)
    BookId = db.Column(db.Integer, db.ForeignKey('Books.BookId'))
    PageNumber = db.Column(db.Integer)
    Content = db.Column(db.Text)
    Note = db.Column(db.Text)
    CreatedAt = db.Column(db.DateTime, default=datetime.utcnow)
    book = db.relationship('Book', backref='quotes')

class ChatMessage(db.Model):
    __tablename__ = 'ChatMessages'
    MessageId = db.Column(db.Integer, primary_key=True)
    UserId = db.Column(db.Integer, db.ForeignKey('Users.UserId'))
    Content = db.Column(db.Text)
    IsFromAI = db.Column(db.Boolean, default=False)
    CreatedAt = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref='chat_messages')

class Task(db.Model):
    __tablename__ = 'Tasks'
    TaskId = db.Column(db.Integer, primary_key=True)
    UserId = db.Column(db.Integer, db.ForeignKey('Users.UserId'))
    Title = db.Column(db.String(200))
    Description = db.Column(db.Text)
    DueDate = db.Column(db.DateTime)
    Priority = db.Column(db.String(20))  # 'high', 'medium', 'low'
    Category = db.Column(db.String(50))  # 'work', 'personal', 'hobby'
    Status = db.Column(db.String(20))  # 'pending', 'completed'
    CreatedAt = db.Column(db.DateTime, default=datetime.utcnow)
    CompletedAt = db.Column(db.DateTime)
    user = db.relationship('User', backref='tasks')

class TaskTime(db.Model):
    __tablename__ = 'TaskTimes'
    TimeId = db.Column(db.Integer, primary_key=True)
    TaskId = db.Column(db.Integer, db.ForeignKey('Tasks.TaskId'))
    StartTime = db.Column(db.DateTime)
    EndTime = db.Column(db.DateTime)
    Duration = db.Column(db.Integer)  # Dakika cinsinden
    task = db.relationship('Task', backref='time_records')

class TaskReport(db.Model):
    __tablename__ = 'TaskReports'
    ReportId = db.Column(db.Integer, primary_key=True)
    UserId = db.Column(db.Integer, db.ForeignKey('Users.UserId'))
    ReportDate = db.Column(db.DateTime)
    CompletedTasks = db.Column(db.Integer)
    OverdueTasks = db.Column(db.Integer)
    TotalTimeSpent = db.Column(db.Integer)  # Dakika cinsinden
    ReportContent = db.Column(db.Text)
    user = db.relationship('User', backref='task_reports')

class UserSettings(db.Model):
    __tablename__ = 'UserSettings'
    SettingId = db.Column(db.Integer, primary_key=True)
    UserId = db.Column(db.Integer, db.ForeignKey('Users.UserId'))
    Theme = db.Column(db.String(20), default='light')  # 'light', 'dark'
    EmailNotifications = db.Column(db.Boolean, default=True)
    user = db.relationship('User', backref='settings')

class Reminder(db.Model):
    __tablename__ = 'Reminders'
    ReminderId = db.Column(db.Integer, primary_key=True)
    UserId = db.Column(db.Integer, db.ForeignKey('Users.UserId'), nullable=False)
    QuestionId = db.Column(db.Integer, db.ForeignKey('Questions.QuestionId'), nullable=False)
    Frequency = db.Column(db.String(20))  # 'daily', 'weekly', 'monthly'
    Time = db.Column(db.Time)  # Hatırlatma saati
    IsActive = db.Column(db.Boolean, default=True)
    LastSent = db.Column(db.DateTime)
    CreatedAt = db.Column(db.DateTime, default=datetime.now)
    
    user = db.relationship('User', backref='reminders')
    question = db.relationship('Question', backref='reminders')

def create_categories():
    categories = [
        {'name': 'Matematik', 'icon': 'math.png'},
        {'name': 'Türk Dili ve Edebiyatı', 'icon': 'literature.png'},
        {'name': 'Felsefe', 'icon': 'philosophy.png'},
        {'name': 'Din', 'icon': 'religion.png'},
        {'name': 'Coğrafya', 'icon': 'geography.png'},
        {'name': 'Fizik', 'icon': 'physics.png'},
        {'name': 'Kimya', 'icon': 'chemistry.png'},
        {'name': 'Biyoloji', 'icon': 'biology.png'},
        {'name': 'Tarih', 'icon': 'history.png'},
        {'name': 'Yabancı Dil', 'icon': 'language.png'}
    ]
    
    for category in categories:
        if not Category.query.filter_by(Name=category['name']).first():
            new_category = Category(Name=category['name'])
            db.session.add(new_category)
    
    try:
        db.session.commit()
        print("Kategoriler başarıyla oluşturuldu.")
    except Exception as e:
        db.session.rollback()
        print(f"Kategori oluşturma hatası: {str(e)}")

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/welcome')
def welcome():
    return render_template('welcome.html')

@app.route('/notifications')
@login_required
def notifications():
    today = datetime.now().date()
    now = datetime.now()


    # Soru Bildirimleri için verileri çek
    today_questions = Question.query.filter(
        Question.UserId == current_user.UserId,
        Question.IsCompleted == False,
        Question.IsHidden == False,
        (
            (Question.RepeatCount == 0 and Question.Repeat1Date is not None and db.func.cast(Question.Repeat1Date, db.Date) == today)
            |
            (Question.RepeatCount == 1 and Question.Repeat2Date is not None and db.func.cast(Question.Repeat2Date, db.Date) == today)
            |
            (Question.RepeatCount == 2 and Question.Repeat3Date is not None and db.func.cast(Question.Repeat3Date, db.Date) == today)
        )
    ).all()


    past_questions = Question.query.filter(
        Question.UserId == current_user.UserId,
        Question.IsCompleted == False,
        Question.RepeatCount < 3,
        (
            (Question.RepeatCount == 0 and db.func.cast(Question.Repeat1Date, db.Date) < today) # İlk tekrar tarihi geçmişse
            |
            (Question.RepeatCount == 1 and db.func.cast(Question.Repeat2Date, db.Date) < today) # İkinci tekrar tarihi geçmişse
            |
            (Question.RepeatCount == 2 and db.func.cast(Question.Repeat3Date, db.Date) < today) # Üçüncü tekrar tarihi geçmişse
        )
    ).all()

    # Tamamlanan soruları çek (CompletedAt olmadığı için şimdilik sadece IsCompleted=True olanları sayabiliriz veya bu kısmı atlayabiliriz)
    # Şimdilik bu kısmı atlıyorum, eğer CompletedAt sütununu eklerseniz burayı güncelleyebiliriz.
    completed_today = [] # Boş liste gönderiyoruz

    # Görev Bildirimleri için verileri çek
    overdue_tasks = Task.query.filter(
        Task.UserId == current_user.UserId,
        Task.Status == 'pending',
        Task.DueDate < now
    ).all()

    completed_tasks = Task.query.filter(
        Task.UserId == current_user.UserId,
        Task.Status == 'completed',
        Task.CompletedAt is not None, # CompletedAt Task modelinde var
        db.func.cast(Task.CompletedAt, db.Date) == today
    ).all()

    new_tasks = Task.query.filter(
        Task.UserId == current_user.UserId,
        Task.CreatedAt is not None,
        db.func.cast(Task.CreatedAt, db.Date) == today
    ).all()

    
    # Şablonu render et ve verileri gönder
    return render_template('notifications.html',
                           today_questions=today_questions,
                           past_questions=past_questions,
                           completed_today=completed_today, # Şimdilik boş
                           overdue_tasks=overdue_tasks,
                           completed_tasks=completed_tasks,
                           new_tasks=new_tasks,
                           section='takipsistemi' # Navbar görünümü için
                          )

@app.route('/mark_notification_read/<int:notification_id>', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    # ... existing code ...
    pass

@app.route('/today_questions')
@login_required
def today_questions():
    today = datetime.now().date()
    
    # Get questions that are due for review today
    questions = Question.query.filter(
        Question.UserId == current_user.UserId,
        Question.IsCompleted == False,
        Question.IsHidden == False,
        (
            # First repeat is due today
            (Question.RepeatCount == 0 and Question.Repeat1Date is not None and db.func.cast(Question.Repeat1Date, db.Date) == today) |
            # Second repeat is due today
            (Question.RepeatCount == 1 and Question.Repeat2Date is not None and db.func.cast(Question.Repeat2Date, db.Date) == today) |
            # Third repeat is due today
            (Question.RepeatCount == 2 and Question.Repeat3Date is not None and db.func.cast(Question.Repeat3Date, db.Date) == today)
        )
    ).order_by(Question.Repeat1Date).all()

    categories = Category.query.all()
    return render_template('today_questions.html', questions=questions, categories=categories, section='takipsistemi')

@app.route('/past_questions')
@login_required
def past_questions():
    today = datetime.now().date()

    # Tekrar tarihi bugünden önce olan, tamamlanmamış ve 3 tekrarı tamamlanmamış soruları filtrele
    # Mevcut RepeatCount'a göre ilgili RepeatDate'in bugünden önce olması gerekir
    questions = Question.query.filter(
        Question.UserId == current_user.UserId,
        Question.IsCompleted == False,
        Question.RepeatCount < 3,
        (
            # RepeatCount 0 ise, Repeat1Date bugünden önce olmalı
            (Question.RepeatCount == 0 and db.func.cast(Question.Repeat1Date, db.Date) < today)
            |
            # RepeatCount 1 ise, Repeat2Date bugünden önce olmalı
            (Question.RepeatCount == 1 and db.func.cast(Question.Repeat2Date, db.Date) < today)
            |
            # RepeatCount 2 ise, Repeat3Date bugünden önce olmalı
            (Question.RepeatCount == 2 and db.func.cast(Question.Repeat3Date, db.Date) < today)
        )
    ).order_by(Question.Repeat1Date.desc()).all() # Sıralama tercihi kalabilir
    
    categories = Category.query.all()
    return render_template('index.html', questions=questions, categories=categories, section='no_nav') # index.html şablonunu kullanıyoruz

@app.route('/reminders')
@login_required
def reminders():
    today = datetime.now().date()
    questions = Question.query.filter(
        Question.UserId == current_user.UserId,
        db.text("CAST([Questions].[Repeat1Date] AS DATE) > :today"), # Burayı eski haline getirdik
        Question.IsCompleted == False,
        Question.RepeatCount < 3
    ).params(today=today).order_by(Question.Repeat1Date).all()
    
    categories = Category.query.all()
    return render_template('questions.html', questions=questions, categories=categories, section='no_nav') # questions.html şablonunu kullanıyoruz

@app.route('/set_reminder/<int:question_id>', methods=['POST'])
# ... existing code ...

@app.route('/')
def index():
    if not current_user.is_authenticated:
        return redirect(url_for('welcome'))
    
    # Bugünün sorularını say (mevcut index verisi)
    today = datetime.now().date()
    daily_questions_count = Question.query.filter(
        Question.UserId == current_user.UserId,
        db.text("CAST([Questions].[Repeat1Date] AS DATE) = :today"),
        Question.IsCompleted == False
    ).params(today=today).count()

    # Toplam soru sayısı (mevcut index verisi)
    total_questions_count = Question.query.filter_by(
        UserId=current_user.UserId
    ).count()

    # Okunan kitap sayısı (mevcut index verisi)
    books_count = Book.query.filter_by(
        UserId=current_user.UserId
    ).count()

    # İzlenen TEDx sayısı (mevcut index verisi)
    ted_talks_count = TedTalk.query.filter_by(
        UserId=current_user.UserId
    ).count()

    # Aktif görev sayısı (mevcut index verisi)
    tasks_count = Task.query.filter_by(
        UserId=current_user.UserId,
        Status='pending'
    ).count()

    # Motivasyon mesajları (hem eski index hem de questions verisi)
    motivation_messages = [
        "Başarı, küçük adımların toplamıdır!",
        "Her gün bir adım daha ileriye!",
        "Zorlandığında vazgeçme, mola ver ve devam et!",
        "Küçük adımlar büyük başarılar getirir!",
        "Bugün dünden daha iyi ol!",
        "Başarı yolunda ilerliyorsun!",
        "Kendine inan, başarabilirsin!",
        "Her tekrar seni hedefe yaklaştırır!"
    ]
    motivation_message = random.choice(motivation_messages)

    # Kategorileri getir (questions verisi)
    categories = Category.query.all()
    
    # Kullanıcının sorularını getir (questions verisi)
    questions = Question.query.filter_by(UserId=current_user.UserId, IsHidden=False).order_by(Question.QuestionId.desc()).all()

    return render_template('index.html',
                         daily_questions_count=daily_questions_count,
                         total_questions_count=total_questions_count,
                         books_count=books_count,
                         ted_talks_count=ted_talks_count,
                         tasks_count=tasks_count,
                         motivation_message=motivation_message,
                         categories=categories,
                         questions=questions,
                         section='takipsistemi'  # Yeni eklenen
                           )

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            # Form verilerini al
            username = request.form.get('username')
            password = request.form.get('password')
            password_confirm = request.form.get('password_confirm')
            first_name = request.form.get('first_name')
            last_name = request.form.get('last_name')
            email = request.form.get('email')
            class_level = request.form.get('class_level')
            year_of_birth = request.form.get('year_of_birth')
            area = request.form.get('area')
            aim = request.form.get('aim')
            security_question = request.form.get('security_question')
            security_answer = request.form.get('security_answer')

            # Zorunlu alanları kontrol et
            if not all([username, password, first_name, last_name, email, class_level, year_of_birth, area, aim, security_question, security_answer]):
                flash('Lütfen tüm zorunlu alanları doldurun.', 'error')
                return redirect(url_for('register'))

            # Kullanıcı adı kontrolü
            if User.query.filter_by(UserName=username).first():
                flash('Bu kullanıcı adı zaten kullanılıyor.', 'error')
                return redirect(url_for('register'))

            # E-posta kontrolü
            if User.query.filter_by(Email=email).first():
                flash('Bu e-posta adresi zaten kullanılıyor.', 'error')
                return redirect(url_for('register'))

            # Şifre kontrolü
            if password != password_confirm:
                flash('Şifreler eşleşmiyor.', 'error')
                return redirect(url_for('register'))

            # Şifreyi hashle
            password_hash = hashlib.sha256(password.encode()).hexdigest()

            # Yeni kullanıcı oluştur
            new_user = User(
                UserName=username,
                PasswordHash=password_hash,
                Name=first_name,
                Surname=last_name,
                Email=email,
                Class=class_level,
                YearOfBirth=int(year_of_birth),
                Area=area,
                Aim=aim,
                SecurityQuestion=security_question
            )

            # Veritabanına kaydet
            db.session.add(new_user)
            db.session.commit()

            flash('Kayıt başarılı! Şimdi giriş yapabilirsiniz.', 'success')
            return redirect(url_for('login'))

        except Exception as e:
            db.session.rollback()
            print(f"Kayıt hatası: {str(e)}")  # Hata logla
            flash('Kayıt sırasında bir hata oluştu. Lütfen tekrar deneyin.', 'error')
            return redirect(url_for('register'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember') # 'remember' onay kutusunu al
        user = User.query.filter_by(UserName=username).first()
        
        if user and user.PasswordHash == hashlib.sha256(password.encode()).hexdigest():
            # Eğer 'remember' onay kutusu işaretli ise remember=True olarak login_user'ı çağır
            login_user(user, remember=bool(remember)) 
            flash('Başarıyla giriş yaptınız!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Geçersiz kullanıcı adı veya şifre', 'danger')
    return render_template('login.html')

@app.route('/welcome_after_login')
@login_required
def welcome_after_login():
    user = current_user
    # Hoş geldiniz mesajı için kullanıcının adını al
    welcome_message = f"Hoş Geldiniz, {user.Name}!" if user.Name else "Hoş Geldiniz!"
    return render_template('welcome_after_login.html', welcome_message=welcome_message, section='welcome')

@app.route('/hedefleyici')
@login_required
def hedefleyici():
    return render_template('hedefleyici.html', section='hedefleyici')

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/add_question', methods=['GET', 'POST'])
@login_required
def add_question():
    if request.method == 'POST':
        try:
            content = request.form.get('content')
            category = request.form.get('category')
            topic = request.form.get('topic')  # Yeni eklenen alan
            question_image = request.files.get('question_image')
            difficulty = request.form.get('difficulty') # Zorluk seviyesini al
            
            # Check if required fields (category, topic, and difficulty) are present.
            if not category or not topic or not difficulty:
                flash('Lütfen tüm zorunlu alanları doldurun.', 'error')
                return redirect(url_for('add_question'))
            
            # Set content to an empty string if not provided (e.g., if the field was removed from HTML)
            content = content if content is not None else ''

            # Görsel yükleme işlemi
            image_path = None
            now = datetime.now() # Soru eklenme zamanı
            
            # Tekrar tarihleri şimdiki zamandan 1 dakika, 10 gün ve 20 gün sonraya ayarlanır
            repeat1_date = now + timedelta(minutes=1)
            repeat2_date = now + timedelta(days=10)
            repeat3_date = now + timedelta(days=20)

            if question_image and question_image.filename:
                try:
                    filename = secure_filename(question_image.filename)
                    unique_filename = f"{now.strftime('%Y%m%d_%H%M%S')}_{filename}"
                    
                    upload_folder = os.path.join(app.static_folder, 'uploads')
                    if not os.path.exists(upload_folder):
                        os.makedirs(upload_folder)
                    
                    image_path = f"uploads/{unique_filename}"
                    full_path = os.path.join(app.static_folder, 'uploads', unique_filename)
                    
                    question_image.save(full_path)

                except Exception as e:
                    flash('Görsel yüklenirken bir hata oluştu.', 'error')

            # Yeni soru oluştur
            new_question = Question(
                UserId=current_user.UserId,
                Content=content,
                CategoryId=category,
                Topic=topic,  # Yeni eklenen alan
                DifficultyLevel=difficulty, # Zorluk seviyesini ata
                PhotoPath=None,
                IsCompleted=False,
                IsViewed=False,
                IsRepeated=False,
                RepeatCount=0,
                Repeat1Date=repeat1_date,
                Repeat2Date=repeat2_date,
                Repeat3Date=repeat3_date,
                Explanation=None,
                ImagePath=image_path
            )
            
            db.session.add(new_question)
            db.session.commit()
            
            flash('Soru başarıyla eklendi.', 'success')
            return redirect(url_for('questions'))
            
        except Exception as e:
            db.session.rollback()
            flash('Soru eklenirken bir hata oluştu: ' + str(e), 'error')
            return redirect(url_for('add_question'))
    
    # Kategorileri veritabanından çek
    categories = Category.query.order_by(Category.Name).all()
    return render_template('add_question.html', categories=categories, section='takipsistemi')

@app.route('/edit_question/<int:question_id>', methods=['GET', 'POST'])
@login_required
def edit_question(question_id):
    question = Question.query.get_or_404(question_id)
    if question.UserId != current_user.UserId:
        flash('Bu soruyu düzenleme yetkiniz yok.')
        return redirect(url_for('questions'))
    
    if request.method == 'POST':
        question.Content = request.form.get('content')
        question.CategoryId = request.form.get('category')
        
        try:
            db.session.commit()
            flash('Soru başarıyla güncellendi.')
            return redirect(url_for('questions'))
        except Exception as e:
            db.session.rollback()
            flash('Soru güncellenirken bir hata oluştu.')
            return redirect(url_for('edit_question', question_id=question_id))
    
    categories = Category.query.order_by(Category.Name).all()
    return render_template('edit_question.html', question=question, categories=categories)

@app.route('/view_today_question/<int:question_id>')
@login_required
def view_today_question(question_id):
    question = Question.query.get_or_404(question_id)
    if question.UserId != current_user.UserId:
        abort(403) # Kullanıcı sorunun sahibi değilse izin verme
        
    # Notları getir (varsa)
    notes = Note.query.filter_by(QuestionId=question.QuestionId).all()

    # Favori bilgisini kontrol et
    is_favorite = Favorite.query.filter_by(UserId=current_user.UserId, QuestionId=question.QuestionId).first() is not None

    return render_template('view_today_question.html', question=question, notes=notes, is_favorite=is_favorite, section='no_nav') # section'ı isteğe göre ayarlayabilirsiniz

@app.route('/view_question/<int:question_id>')
@login_required
def view_question(question_id):
    question = Question.query.get_or_404(question_id)
    if question.UserId != current_user.UserId:
        flash('Bu soruyu görüntüleme yetkiniz yok.', 'error')
        return redirect(url_for('index'))
    
    # Notları getir
    notes = Note.query.filter_by(QuestionId=question_id).order_by(Note.NoteId.desc()).all()
    
    # Favori durumunu kontrol et
    is_favorite = Favorite.query.filter_by(
        QuestionId=question_id,
        UserId=current_user.UserId
    ).first() is not None
    
    # Tekrar durumunu hesapla
    repeat_status = {
        'count': question.RepeatCount,
        'is_completed': question.IsCompleted,
        'is_repeated': question.IsRepeated,
        'dates': {
            'repeat1': question.Repeat1Date,
            'repeat2': question.Repeat2Date,
            'repeat3': question.Repeat3Date
        }
    }
    
    return render_template('view_question.html', 
                         question=question, 
                         notes=notes,
                         is_favorite=is_favorite,
                         repeat_status=repeat_status)

@app.route('/add_note/<int:question_id>', methods=['POST'])
@login_required
def add_note(question_id):
    try:
        question = Question.query.get_or_404(question_id)
        if question.UserId != current_user.UserId:
            return jsonify({'success': False, 'error': 'Bu işlem için yetkiniz yok.'}), 403

        data = request.get_json()
        if not data or 'content' not in data:
            return jsonify({'success': False, 'error': 'Not içeriği gerekli.'}), 400

        note = Note(
            QuestionId=question_id,
            Content=data['content']
        )
        db.session.add(note)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'note': {
                'id': note.NoteId,
                'content': note.Content
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/delete_question/<int:question_id>', methods=['POST'])
@login_required
def delete_question(question_id):
    try:
        question = Question.query.get_or_404(question_id)
        if question.UserId != current_user.UserId:
            return jsonify({'success': False, 'error': 'Bu işlem için yetkiniz yok.'}), 403

        # Önce favorilerden sil
        Favorite.query.filter_by(QuestionId=question_id).delete()
        
        # Sonra soruyu sil
        db.session.delete(question)
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/mark_completed/<int:question_id>', methods=['POST'])
@login_required
def mark_completed(question_id):
    question = Question.query.get_or_404(question_id)
    if question.UserId != current_user.UserId:
        abort(403)
    
    question.IsCompleted = True
    question.CompletedAt = datetime.now()
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/settings')
@login_required
def settings():
    return render_template('settings.html')

@app.route('/questions')
@login_required
def questions():
    # Bu rotada artık tüm soruları çekmiyoruz, sadece kategorileri gönderiyoruz
    # query = Question.query.filter_by(UserId=current_user.UserId, IsHidden=False)
    # questions = query.order_by(Question.QuestionId.desc()).all()

    # Rastgele motive mesajı seç (bu kısım kalabilir veya kaldırılabilir)
    motivation_messages = [
        "Her gün bir adım daha ileriye!",
        "Baş başarı yolunda her soru bir fırsat!",
        "Bugün çalış, yarın başar!",
        "Küçük adımlar büyük başarılar getirir!",
        "Her soru seni hedefe yaklaştırıyor!"
    ]
    motivation_message = random.choice(motivation_messages)
    
    all_categories = Category.query.all()
    categories_with_counts = []
    for category in all_categories:
        # Mevcut kullanıcıya ait ve gizli olmayan soruları say
        question_count = Question.query.filter_by(
            UserId=current_user.UserId,
            CategoryId=category.CategoryId,
            IsHidden=False
        ).count()
        categories_with_counts.append({
            'category': category,
            'count': question_count
        })

    return render_template('questions.html',
                         categories_with_counts=categories_with_counts,
                         motivation_message=motivation_message,
                         section='no_nav'
)

@app.route('/category/<int:category_id>')
@login_required
def category_questions(category_id):
    category = Category.query.get_or_404(category_id)
    
    # Get the selected topic from the query parameters, default to None
    selected_topic = request.args.get('topic')

    # Base query for questions in this category for the current user, not hidden
    query = Question.query.filter_by(
        UserId=current_user.UserId,
        CategoryId=category_id,
        IsHidden=False
    )
    
    # If a topic is selected, filter the query by topic
    if selected_topic:
        # Handle the case where "Diğer" (Other) is selected for questions with no topic
        if selected_topic == "Diğer":
            query = query.filter(Question.Topic == None)
        else:
            query = query.filter_by(Topic=selected_topic)

    questions = query.order_by(Question.Topic).all()
    
    # Get all unique topics for this category and user (for the filter dropdown)
    all_topics_query = Question.query.with_entities(Question.Topic).filter_by(
        UserId=current_user.UserId,
        CategoryId=category_id,
        IsHidden=False
    ).distinct()
    all_topics = [topic[0] if topic[0] is not None else "Diğer" for topic in all_topics_query]
    all_topics.sort() # Sort topics alphabetically

    return render_template('category_questions.html', 
                         category=category, 
                         questions=questions, # Pass filtered questions
                         all_topics=all_topics, # Pass all unique topics for the filter
                         selected_topic=selected_topic, # Pass the currently selected topic
                         section='takipsistemi')

@app.route('/favorites')
@login_required
def favorites():
    categories = Category.query.all() # Tüm kategorileri çek
    category_id = request.args.get('category') # URL'den kategori ID'sini al

    query = Question.query.join(
        Favorite,
        Question.QuestionId == Favorite.QuestionId
    ).filter(
        Favorite.UserId == current_user.UserId
    ).order_by(Question.Repeat1Date)

    if category_id:
        try:
            category_id = int(category_id)
            query = query.filter(Question.CategoryId == category_id)
        except ValueError:
            # Geçersiz kategori ID'si durumunda hata yönetimi veya tüm favorileri gösterme
            flash('Geçersiz kategori seçimi.', 'warning')
            pass # Hata durumunda filtreleme yapma

    questions = query.all()

    return render_template('favorites.html', questions=questions, categories=categories, selected_category_id=category_id, section='no_nav')

@app.route('/toggle_favorite/<int:question_id>', methods=['POST'])
@login_required
def toggle_favorite(question_id):
    try:
        question = Question.query.get_or_404(question_id)
        if question.UserId != current_user.UserId:
            return jsonify({'success': False, 'error': 'Bu işlem için yetkiniz yok.'}), 403

        # Favori durumunu kontrol et
        favorite = Favorite.query.filter_by(
            QuestionId=question_id,
            UserId=current_user.UserId
        ).first()

        if favorite:
            # Favori varsa sil
            db.session.delete(favorite)
        else:
            # Favori yoksa ekle
            new_favorite = Favorite(
                QuestionId=question_id,
                UserId=current_user.UserId
            )
            db.session.add(new_favorite)
        
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/get_reminders')
@login_required
def get_reminders():
    try:
        reminders = Reminder.query.filter_by(
            UserId=current_user.UserId,
            IsActive=True
        ).all()
        
        reminder_list = []
        for reminder in reminders:
            question = Question.query.get(reminder.QuestionId)
            if question and not question.IsCompleted:
                reminder_list.append({
                    'id': reminder.ReminderId,
                    'question_id': reminder.QuestionId,
                    'question_content': question.Content[:100] + '...' if len(question.Content) > 100 else question.Content,
                    'frequency': reminder.Frequency,
                    'time': reminder.Time.strftime('%H:%M'),
                    'category': question.category.Name
                })
        
        return jsonify({'success': True, 'reminders': reminder_list})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/delete_reminder/<int:reminder_id>', methods=['POST'])
@login_required
def delete_reminder(reminder_id):
    try:
        reminder = Reminder.query.get_or_404(reminder_id)
        if reminder.UserId != current_user.UserId:
            return jsonify({'success': False, 'error': 'Bu hatırlatıcıya erişim izniniz yok.'})
        
        db.session.delete(reminder)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

def check_reminders():
    """Hatırlatıcıları kontrol eden ve bildirim gönderen fonksiyon"""
    with app.app_context():
        try:
            now = datetime.now()
            current_time = now.time()
            
            # Aktif hatırlatıcıları al
            reminders = Reminder.query.filter_by(IsActive=True).all()
            
            for reminder in reminders:
                # Son gönderim zamanını kontrol et
                if reminder.LastSent:
                    time_diff = now - reminder.LastSent
                    
                    # Frekansa göre kontrol
                    if reminder.Frequency == 'daily' and time_diff.days < 1:
                        continue
                    elif reminder.Frequency == 'weekly' and time_diff.days < 7:
                        continue
                    elif reminder.Frequency == 'monthly' and time_diff.days < 30:
                        continue
                
                # Hatırlatma saatini kontrol et
                if reminder.Time.hour == current_time.hour and reminder.Time.minute == current_time.minute:
                    # Bildirim gönder
                    question = Question.query.get(reminder.QuestionId)
                    if question and not question.IsCompleted:
                        notification = Notification(
                            UserId=reminder.UserId,
                            NotificationType='reminder',
                            TaskId=None,
                            Schedule=now
                        )
                        db.session.add(notification)
                        reminder.LastSent = now
                        db.session.commit()
                        
                        print(f"Hatırlatma gönderildi: {question.Content[:50]}...")
        
        except Exception as e:
            print(f"Hatırlatıcı kontrolü hatası: {str(e)}")

# Hatırlatıcı kontrolü için zamanlanmış görev
def schedule_reminder_check():
    while True:
        check_reminders()
        time.sleep(60)  # Her dakika kontrol et

# Arka planda çalışacak hatırlatıcı thread'ini başlat
reminder_thread = threading.Thread(target=schedule_reminder_check, daemon=True)
reminder_thread.start()

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(Email=email).first()
        
        if user:
            # Benzersiz bir token oluştur
            token = secrets.token_urlsafe(32)
            expires_at = datetime.now() + timedelta(hours=24)
            
            # Token'ı veritabanına kaydet
            reset_token = PasswordResetToken(
                UserId=user.UserId,
                Token=token,
                ExpiresAt=expires_at
            )
            db.session.add(reset_token)
            db.session.commit()
            
            # E-posta gönder
            reset_url = url_for('reset_password', token=token, _external=True)
            msg = Message('Şifre Sıfırlama',
                        recipients=[user.Email])
            msg.body = f'''Şifrenizi sıfırlamak için aşağıdaki bağlantıya tıklayın:
{reset_url}

Bu bağlantı 24 saat boyunca geçerlidir.

Eğer bu isteği siz yapmadıysanız, bu e-postayı görmezden gelebilirsiniz.
'''
            mail.send(msg)
            
            flash('Şifre sıfırlama bağlantısı e-posta adresinize gönderildi.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Bu e-posta adresi ile kayıtlı bir kullanıcı bulunamadı.', 'error')
    
    return render_template('forgot_password.html')

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    reset_token = PasswordResetToken.query.filter_by(Token=token, IsUsed=False).first()
    
    if not reset_token or reset_token.ExpiresAt < datetime.now():
        flash('Geçersiz veya süresi dolmuş şifre sıfırlama bağlantısı.', 'error')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Şifreler eşleşmiyor.', 'error')
            return redirect(url_for('reset_password', token=token))
        
        # Şifreyi güncelle
        user = User.query.get(reset_token.UserId)
        user.PasswordHash = hashlib.sha256(password.encode()).hexdigest()
        
        # Token'ı kullanıldı olarak işaretle
        reset_token.IsUsed = True
        
        db.session.commit()
        flash('Şifreniz başarıyla güncellendi. Şimdi giriş yapabilirsiniz.', 'success')
        return redirect(url_for('login'))
    
    return render_template('reset_password.html')

@app.route('/report')
@login_required
def report():
    today = datetime.now().date()
    # Tamamlanan görevler
    completed_tasks = Task.query.filter(
        Task.UserId == current_user.UserId,
        Task.Status == 'completed',
        db.text("CAST([Tasks].[CompletedAt] AS DATE) = :today")
    ).params(today=today).all()
    # Geciken görevler
    overdue_tasks = Task.query.filter(
        Task.UserId == current_user.UserId,
        Task.Status == 'pending',
        Task.DueDate < datetime.now()
    ).all()
    # Toplam çalışma süresi (görev türü fark etmeksizin, o günün tüm TaskTime kayıtları)
    total_time = db.session.query(db.func.sum(TaskTime.Duration)).join(Task).filter(
        Task.UserId == current_user.UserId,
        db.text("CAST([TaskTimes].[StartTime] AS DATE) = :today")
    ).params(today=today).scalar() or 0
    # Toplam görev sayısı (bugün tamamlanan + geciken + aktif)
    total_tasks = len(completed_tasks) + len(overdue_tasks)
    completion_rate = int((len(completed_tasks) / total_tasks) * 100) if total_tasks > 0 else 0
    return render_template(
        'report.html',
        report_date=today.strftime('%d.%m.%Y'),
        completed_count=len(completed_tasks),
        overdue_count=len(overdue_tasks),
        total_time=total_time,
        completed_tasks=completed_tasks,
        overdue_tasks=overdue_tasks,
        completion_rate=completion_rate
    )

@app.route('/pomodoro_settings')
@login_required
def pomodoro_settings():
    return render_template('pomodoro_settings.html')

@app.route('/timer')
@login_required
def timer():
    return render_template('timer.html', section='no_nav')

@app.route('/hide_question/<int:question_id>', methods=['POST'])
@login_required
def hide_question(question_id):
    question = Question.query.get_or_404(question_id)
    if question.UserId != current_user.UserId:
        return jsonify({'success': False, 'error': 'Bu işlem için yetkiniz yok'}), 403
    
    try:
        question.IsHidden = True
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/progress_report')
@login_required
def progress_report():
    today = datetime.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)

    # Haftalık ve aylık tamamlanan soru/görev
    weekly_questions = Question.query.filter(
        Question.UserId == current_user.UserId,
        Question.IsCompleted == True,
        db.text("CAST([Questions].[CompletedAt] AS DATE) >= :week_ago")
    ).params(week_ago=week_ago).all()
    monthly_questions = Question.query.filter(
        Question.UserId == current_user.UserId,
        Question.IsCompleted == True,
        db.text("CAST([Questions].[CompletedAt] AS DATE) >= :month_ago")
    ).params(month_ago=month_ago).all()

    weekly_tasks = Task.query.filter(
        Task.UserId == current_user.UserId,
        Task.Status == 'completed',
        db.text("CAST([Tasks].[CompletedAt] AS DATE) >= :week_ago")
    ).params(week_ago=week_ago).all()
    monthly_tasks = Task.query.filter(
        Task.UserId == current_user.UserId,
        Task.Status == 'completed',
        db.text("CAST([Tasks].[CompletedAt] AS DATE) >= :month_ago")
    ).params(month_ago=month_ago).all()

    # Kategori bazlı dağılım (haftalık)
    categories = Category.query.all()
    category_stats = []
    for category in categories:
        count = Question.query.filter(
            Question.UserId == current_user.UserId,
            Question.IsCompleted == True,
            Question.CategoryId == category.CategoryId,
            db.text("CAST([Questions].[CompletedAt] AS DATE) >= :week_ago")
        ).params(week_ago=week_ago).count()
        category_stats.append({
            'category': category.Name,
            'count': count
        })

    # Başarı oranı (haftalık)
    total_weekly_questions = Question.query.filter(
        Question.UserId == current_user.UserId,
        db.text("CAST([Questions].[Repeat1Date] AS DATE) >= :week_ago")
    ).params(week_ago=week_ago).count()
    completed_weekly_questions = len(weekly_questions)
    success_rate = int((completed_weekly_questions / total_weekly_questions) * 100) if total_weekly_questions > 0 else 0

    # Öneri ve hedef (en az yapılan kategori)
    min_category = min(category_stats, key=lambda x: x['count']) if category_stats else None
    suggestion = None
    if min_category and min_category['count'] < 5:
        suggestion = f"Bu hafta {min_category['category']} kategorisinde daha fazla soru çözmeye çalış!"
    elif min_category:
        suggestion = f"Harika! Tüm kategorilerde iyi gidiyorsun."

    # Haftalık hedef (örnek: 10 soru)
    weekly_goal = 10
    goal_message = f"Bu hafta en az {weekly_goal} soru çöz!"

    return jsonify({
        'weekly_questions': completed_weekly_questions,
        'monthly_questions': len(monthly_questions),
        'weekly_tasks': len(weekly_tasks),
        'monthly_tasks': len(monthly_tasks),
        'success_rate': success_rate,
        'category_stats': category_stats,
        'suggestion': suggestion,
        'goal_message': goal_message
    })

@app.route('/progress')
@login_required
def progress():
    return render_template('progress_report.html')

@app.route('/next_question/<int:current_id>')
@login_required
def next_question(current_id):
    # Kullanıcının tüm sorularını id'ye göre sırala
    questions = Question.query.filter_by(UserId=current_user.UserId, IsHidden=False).order_by(Question.QuestionId).all()
    ids = [q.QuestionId for q in questions]
    if current_id in ids:
        idx = ids.index(current_id)
        if idx + 1 < len(ids):
            return jsonify({'next_id': ids[idx+1]})
    # Sonraki yoksa veya tek soru ise
    return jsonify({'next_id': None})

# Ana sayfa yönlendirmesi
@app.before_request
def redirect_to_welcome():
    if not current_user.is_authenticated and request.endpoint in ['index', None]:
        return redirect(url_for('welcome'))

@app.route('/save_timer', methods=['POST'])
@login_required
def save_timer():
    data = request.get_json()
    seconds = data.get('seconds', 0)
    if not seconds or seconds <= 0:
        return jsonify({'success': False, 'error': 'Geçersiz süre'}), 400
    # TaskTime tablosuna günlük serbest çalışma olarak ekle
    from datetime import datetime
    now = datetime.now()
    # Serbest çalışma için özel bir Task kaydı bul veya oluştur
    free_task = Task.query.filter_by(UserId=current_user.UserId, Title='Serbest Çalışma', Status='completed').filter(Task.CompletedAt >= now.replace(hour=0, minute=0, second=0)).first()
    if not free_task:
        free_task = Task(
            UserId=current_user.UserId,
            Title='Serbest Çalışma',
            Description='Sayaç ile kaydedilen serbest çalışma',
            Status='completed',
            CompletedAt=now
        )
        db.session.add(free_task)
        db.session.commit()
    # TaskTime kaydı ekle
    time_entry = TaskTime(
        TaskId=free_task.TaskId,
        StartTime=now,
        EndTime=now,
        Duration=int(seconds // 60)
    )
    db.session.add(time_entry)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/update_repeat_count/<int:question_id>', methods=['POST'])
@login_required
def update_repeat_count(question_id):
    question = Question.query.get_or_404(question_id)
    if question.UserId != current_user.UserId:
        return jsonify({'success': False, 'error': 'Bu soruya erişim izniniz yok.'})
    
    try:
        question.RepeatCount += 1
        now = datetime.now()

        # 3 veya daha fazla tekrar tamamlandıysa soruyu tamamlandı olarak işaretle
        if question.RepeatCount >= 3:
            question.IsCompleted = True
            question.CompletedAt = now
            # İsteğe bağlı: Tamamlandıktan sonra tekrar tarihlerini sıfırlayabilir veya tutabiliriz
            # question.Repeat1Date = None
            # question.Repeat2Date = None
            # question.Repeat3Date = None

        db.session.commit()

        # JavaScript'e döndürülecek sonraki tekrar tarihi (bilgilendirme amaçlı)
        next_repeat_date = None
        if not question.IsCompleted:
            if question.RepeatCount == 0 and question.Repeat1Date: # İlk tekrar tamamlandı, sıra ikincide
                 # İkinci tekrar tarihi add_question'da belirlendiği gibi kalacak
                 next_repeat_date = question.Repeat2Date.strftime('%d.%m.%Y %H:%M') if question.Repeat2Date else None
            elif question.RepeatCount == 1 and question.Repeat2Date: # İkinci tekrar tamamlandı, sıra üçüncüde
                 # Üçüncü tekrar tarihi add_question'da belirlendiği gibi kalacak
                 next_repeat_date = question.Repeat3Date.strftime('%d.%m.%Y %H:%M') if question.Repeat3Date else None
            elif question.RepeatCount == 2 and question.Repeat3Date: # Üçüncü tekrar tamamlandı, soru bitti sayılır
                 next_repeat_date = 'Tamamlandı'
            elif question.RepeatCount == 0 and question.Repeat1Date: # İlk tekrar daha yapılmamış
                 next_repeat_date = question.Repeat1Date.strftime('%d.%m.%Y %H:%M') if question.Repeat1Date else None
            
        else:
            next_repeat_date = 'Tamamlandı'
            

        return jsonify({
            'success': True, 
            'repeat_count': question.RepeatCount,
            'is_completed': question.IsCompleted,
            'next_repeat_date': next_repeat_date, # Bu artık sadece bilgilendirme amaçlı, frontend diğer tarihleri kullanacak
            'updated_repeat_dates': { # Frontend'e gönderilecek güncel tekrar tarihleri
                'repeat1': question.Repeat1Date.strftime('%d.%m.%Y') if question.Repeat1Date else 'Belirlenmedi',
                'repeat2': question.Repeat2Date.strftime('%d.%m.%Y') if question.Repeat2Date else 'Belirlenmedi',
                'repeat3': question.Repeat3Date.strftime('%d.%m.%Y') if question.Repeat3Date else 'Belirlenmedi'
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/complete_question/<int:question_id>', methods=['POST'])
@login_required
def complete_question(question_id):
    question = Question.query.get_or_404(question_id)
    if question.UserId != current_user.UserId:
        return jsonify({'success': False, 'error': 'Bu işlem için yetkiniz yok.'}), 403
    
    try:
        question.IsCompleted = True
        question.CompletedAt = datetime.now()
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

# Uygulama başlatıldığında temizleme işlemini yap
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        create_categories()  # Kategorileri oluştur
    app.run(host='127.0.0.1', port=5000, debug=True)
