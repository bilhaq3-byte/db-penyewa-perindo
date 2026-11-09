import os
import json
import uuid
import shutil
from datetime import datetime, date
from functools import wraps
from decimal import Decimal

from flask import (Flask, render_template, request, redirect, url_for, flash,
                   jsonify, send_file, session, abort, g)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy import func, case, and_, or_, text
from sqlalchemy.orm import joinedload

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'perindo-db-penyewa-lahan-2026-secret'
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(BASE_DIR, "database.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max

db = SQLAlchemy(app)

ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png', 'doc', 'docx', 'xls', 'xlsx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ======================== MODELS ========================

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    nama_lengkap = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='cabang')  # 'pusat' or 'cabang'
    cabang_id = db.Column(db.Integer, db.ForeignKey('cabang.id'), nullable=True)  # null for pusat
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    cabang = db.relationship('Cabang', backref='users')

    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw)

    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)


class Cabang(db.Model):
    __tablename__ = 'cabang'
    id = db.Column(db.Integer, primary_key=True)
    kode = db.Column(db.String(20), unique=True, nullable=False)
    nama = db.Column(db.String(150), nullable=False)
    alamat = db.Column(db.Text)
    telepon = db.Column(db.String(30))
    kepala_cabang = db.Column(db.String(150))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    sertifikats = db.relationship('Sertifikat', backref='cabang', lazy='dynamic')


class Sertifikat(db.Model):
    __tablename__ = 'sertifikat'
    id = db.Column(db.Integer, primary_key=True)
    cabang_id = db.Column(db.Integer, db.ForeignKey('cabang.id'), nullable=False)
    nomor_sertifikat = db.Column(db.String(100), nullable=False)
    jenis_hak = db.Column(db.String(50), nullable=False)  # HPL, HP, HGB, dll
    lokasi = db.Column(db.String(200), nullable=False)
    luas_total = db.Column(db.Float, nullable=False)  # m2
    masa_berlaku = db.Column(db.Date, nullable=True)
    nomor_akta = db.Column(db.String(100))
    status_kepemilikan = db.Column(db.String(50), default='Milik sendiri')
    kondisi = db.Column(db.String(50), default='Produktif')
    scan_file = db.Column(db.String(255))
    keterangan = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    bidang_lahans = db.relationship('BidangLahan', backref='sertifikat', lazy='dynamic')


class BidangLahan(db.Model):
    __tablename__ = 'bidang_lahan'
    id = db.Column(db.Integer, primary_key=True)
    sertifikat_id = db.Column(db.Integer, db.ForeignKey('sertifikat.id'), nullable=False)
    kode_bidang = db.Column(db.String(50), nullable=False)
    nama_bidang = db.Column(db.String(150))
    luas = db.Column(db.Float, nullable=False)
    jenis_aset = db.Column(db.String(50), default='Lahan')
    status_pemanfaatan = db.Column(db.String(30), default='Belum Disewakan')  # Disewakan, Belum Disewakan, Dipakai Sendiri
    alamat_lokasi = db.Column(db.String(200))
    keterangan = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    penyewas = db.relationship('Penyewa', backref='bidang_lahan', lazy='dynamic')


class Penyewa(db.Model):
    __tablename__ = 'penyewa'
    id = db.Column(db.Integer, primary_key=True)
    bidang_lahan_id = db.Column(db.Integer, db.ForeignKey('bidang_lahan.id'), nullable=False)
    nama = db.Column(db.String(200), nullable=False)
    jenis = db.Column(db.String(20), default='Perorangan')  # Perorangan / Badan Usaha
    jabatan_penandatangan = db.Column(db.String(100))
    alamat = db.Column(db.Text)
    telepon = db.Column(db.String(30))
    email = db.Column(db.String(100))
    npwp = db.Column(db.String(50))
    luas_disewakan = db.Column(db.Float, nullable=False)
    peruntukan = db.Column(db.String(100))
    status_hgb = db.Column(db.String(20), default='Non HGB')  # HGB, Non HGB
    keterangan = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    perjanjians = db.relationship('Perjanjian', backref='penyewa', lazy='dynamic',
                                  order_by='Perjanjian.tanggal_mulai.desc()')


class Perjanjian(db.Model):
    __tablename__ = 'perjanjian'
    id = db.Column(db.Integer, primary_key=True)
    penyewa_id = db.Column(db.Integer, db.ForeignKey('penyewa.id'), nullable=False)
    nomor_perjanjian = db.Column(db.String(150), nullable=False)
    tanggal_mulai = db.Column(db.Date, nullable=False)
    tanggal_berakhir = db.Column(db.Date, nullable=False)
    masa_sewa_tahun = db.Column(db.Float)
    penandatangan_perindo = db.Column(db.String(150))
    nilai_dc = db.Column(db.Float, default=0)  # Development Contribution
    nilai_sc = db.Column(db.Float, default=0)  # Service Charge / tahun
    biaya_admin = db.Column(db.Float, default=0)
    nilai_total = db.Column(db.Float, default=0)
    deposit = db.Column(db.Float, default=0)
    rekening_perindo = db.Column(db.String(50))
    bank_perindo = db.Column(db.String(80))
    dokumen_file = db.Column(db.String(255))
    status = db.Column(db.String(20), default='Aktif')  # Aktif, Berakhir, Dibatalkan
    keterangan = db.Column(db.Text)
    is_perpanjangan = db.Column(db.Boolean, default=False)
    perjanjian_asal_id = db.Column(db.Integer, db.ForeignKey('perjanjian.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class RiwayatPengalihan(db.Model):
    __tablename__ = 'riwayat_pengalihan'
    id = db.Column(db.Integer, primary_key=True)
    bidang_lahan_id = db.Column(db.Integer, db.ForeignKey('bidang_lahan.id'), nullable=False)
    penyewa_lama_id = db.Column(db.Integer, db.ForeignKey('penyewa.id'), nullable=False)
    penyewa_baru_id = db.Column(db.Integer, db.ForeignKey('penyewa.id'), nullable=False)
    tanggal_pengalihan = db.Column(db.Date, nullable=False)
    nomor_dokumen = db.Column(db.String(150))
    keterangan = db.Column(db.Text)
    dokumen_file = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    bidang_lahan = db.relationship('BidangLahan')
    penyewa_lama = db.relationship('Penyewa', foreign_keys=[penyewa_lama_id])
    penyewa_baru = db.relationship('Penyewa', foreign_keys=[penyewa_baru_id])


class Dokumen(db.Model):
    __tablename__ = 'dokumen'
    id = db.Column(db.Integer, primary_key=True)
    entity_type = db.Column(db.String(30), nullable=False)  # sertifikat, penyewa, perjanjian
    entity_id = db.Column(db.Integer, nullable=False)
    nama_file = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    tipe = db.Column(db.String(50))
    uploaded_by = db.Column(db.String(80))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ======================== AUTH HELPERS ========================

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Silakan login terlebih dahulu.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def pusat_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        if session.get('role') != 'pusat':
            flash('Akses hanya untuk Kantor Pusat.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@app.before_request
def load_user():
    g.user = None
    if 'user_id' in session:
        g.user = db.session.get(User, session['user_id'])
        if g.user is None:
            session.clear()

@app.context_processor
def inject_user():
    return dict(current_user=g.user)

def get_user_cabang_filter():
    """Return cabang_id filter for cabang users, None for pusat"""
    if session.get('role') == 'pusat':
        return None
    return session.get('cabang_id')

def save_uploaded_file(file, subfolder=''):
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        unique_name = f"{uuid.uuid4().hex[:8]}_{filename}"
        target_dir = os.path.join(app.config['UPLOAD_FOLDER'], subfolder)
        os.makedirs(target_dir, exist_ok=True)
        filepath = os.path.join(target_dir, unique_name)
        file.save(filepath)
        return os.path.join(subfolder, unique_name) if subfolder else unique_name
    return None

def format_rupiah(value):
    if value is None or value == 0:
        return 'Rp 0'
    try:
        v = float(value)
        if v >= 1_000_000_000:
            return f'Rp {v/1_000_000_000:,.2f} M'
        elif v >= 1_000_000:
            return f'Rp {v/1_000_000:,.1f} Jt'
        else:
            return f'Rp {v:,.0f}'
    except (ValueError, TypeError):
        return 'Rp 0'

def format_rupiah_full(value):
    if value is None or value == 0:
        return 'Rp 0'
    try:
        return f'Rp {float(value):,.0f}'.replace(',', '.')
    except (ValueError, TypeError):
        return 'Rp 0'

def format_luas(value):
    if value is None:
        return '0'
    try:
        v = float(value)
        if v == int(v):
            return f'{int(v):,}'.replace(',', '.')
        return f'{v:,.2f}'.replace(',', '.')
    except (ValueError, TypeError):
        return '0'

def hitung_sisa_periode(penyewa_or_perjanjian):
    today = date.today()
    pj = None
    if hasattr(penyewa_or_perjanjian, 'perjanjians'):
        pj = penyewa_or_perjanjian.perjanjians.filter_by(status='Aktif').first() or penyewa_or_perjanjian.perjanjians.first()
    elif hasattr(penyewa_or_perjanjian, 'tanggal_berakhir'):
        pj = penyewa_or_perjanjian
    elif isinstance(penyewa_or_perjanjian, (date, datetime)):
        class FakePJ:
            tanggal_berakhir = penyewa_or_perjanjian if isinstance(penyewa_or_perjanjian, date) else penyewa_or_perjanjian.date()
        pj = FakePJ()

    if not pj or not pj.tanggal_berakhir:
        return {
            'status': 'none',
            'label': 'Belum Ada Kontrak',
            'sublabel': 'Perlu perikatan sewa',
            'badge_class': 'bg-slate-100 text-slate-600 border-slate-200',
            'dot_class': 'bg-slate-400',
            'icon': 'fa-circle-question',
            'days': 0,
            'tgl_akhir': None,
            'tgl_str': '-',
            'pj': None
        }

    diff = (pj.tanggal_berakhir - today).days
    tgl_str = pj.tanggal_berakhir.strftime('%d/%m/%Y')

    if diff < 0:
        abs_days = abs(diff)
        if abs_days < 30:
            durasi = f"{abs_days} hari lalu"
        elif abs_days < 365:
            durasi = f"{abs_days // 30} bulan lalu"
        else:
            thn = abs_days // 365
            bln = (abs_days % 365) // 30
            durasi = f"{thn} thn {bln} bln lalu" if bln else f"{thn} thn lalu"
        return {
            'status': 'expired',
            'label': 'Sudah Berakhir',
            'sublabel': f'Lewat {durasi}',
            'badge_class': 'bg-rose-50 text-rose-700 border-rose-200/90 font-semibold',
            'dot_class': 'bg-rose-500',
            'icon': 'fa-circle-xmark',
            'days': diff,
            'tgl_akhir': pj.tanggal_berakhir,
            'tgl_str': tgl_str,
            'pj': pj
        }
    elif diff <= 90:
        return {
            'status': 'critical',
            'label': f'Kritis: Sisa {diff} Hari',
            'sublabel': f'Berakhir {tgl_str}',
            'badge_class': 'bg-red-50 text-red-700 border-red-300 font-bold',
            'dot_class': 'bg-red-500',
            'icon': 'fa-triangle-exclamation',
            'days': diff,
            'tgl_akhir': pj.tanggal_berakhir,
            'tgl_str': tgl_str,
            'pj': pj
        }
    elif diff <= 365:
        bln = max(1, diff // 30)
        sisa_hari = diff % 30
        teks_waktu = f"{bln} bln {sisa_hari} hr" if sisa_hari > 0 and bln < 3 else f"{bln} bulan"
        return {
            'status': 'warning',
            'label': f'Akan Berakhir: Sisa {teks_waktu}',
            'sublabel': f'Berakhir {tgl_str}',
            'badge_class': 'bg-amber-50 text-amber-800 border-amber-300 font-semibold',
            'dot_class': 'bg-amber-500',
            'icon': 'fa-clock',
            'days': diff,
            'tgl_akhir': pj.tanggal_berakhir,
            'tgl_str': tgl_str,
            'pj': pj
        }
    else:
        thn = diff // 365
        bln = (diff % 365) // 30
        teks_waktu = f"{thn} thn {bln} bln" if bln else f"{thn} tahun"
        return {
            'status': 'active',
            'label': f'Sisa {teks_waktu}',
            'sublabel': f'Aktif s/d {tgl_str}',
            'badge_class': 'bg-emerald-50 text-emerald-700 border-emerald-200/90 font-medium',
            'dot_class': 'bg-emerald-500',
            'icon': 'fa-circle-check',
            'days': diff,
            'tgl_akhir': pj.tanggal_berakhir,
            'tgl_str': tgl_str,
            'pj': pj
        }

app.jinja_env.filters['rupiah'] = format_rupiah
app.jinja_env.filters['rupiah_full'] = format_rupiah_full
app.jinja_env.filters['luas'] = format_luas
app.jinja_env.filters['sisa_periode'] = hitung_sisa_periode
app.jinja_env.globals['csrf_token'] = lambda: ''
app.jinja_env.globals['max'] = max
app.jinja_env.globals['min'] = min




# ======================== AUTH ROUTES ========================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(username=username, is_active=True).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            session['cabang_id'] = user.cabang_id
            session['nama'] = user.nama_lengkap
            flash(f'Selamat datang, {user.nama_lengkap}!', 'success')
            return redirect(url_for('dashboard'))
        flash('Username atau password salah.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Anda telah logout.', 'info')
    return redirect(url_for('login'))


# ======================== DASHBOARD ========================

@app.route('/')
@login_required
def dashboard():
    cabang_filter = get_user_cabang_filter()
    
    # All cabang list
    if cabang_filter:
        cabang_list = Cabang.query.filter_by(id=cabang_filter, is_active=True).all()
    else:
        cabang_list = Cabang.query.filter_by(is_active=True).order_by(Cabang.nama).all()

    stats = []
    total_sertifikat = 0
    total_luas_tanah = 0
    total_penyewa = 0
    total_luas_disewakan = 0
    total_pendapatan = 0
    total_bidang = 0

    for cab in cabang_list:
        sert_count = Sertifikat.query.filter_by(cabang_id=cab.id, is_active=True).count()
        luas_tanah = db.session.query(func.sum(Sertifikat.luas_total)).filter_by(
            cabang_id=cab.id, is_active=True).scalar() or 0

        # Get all sertifikat IDs for this cabang
        sert_ids = [s.id for s in Sertifikat.query.filter_by(cabang_id=cab.id, is_active=True).all()]
        
        bidang_count = 0
        penyewa_count = 0
        luas_disewakan = 0
        pendapatan = 0

        if sert_ids:
            bidang_count = BidangLahan.query.filter(
                BidangLahan.sertifikat_id.in_(sert_ids), BidangLahan.is_active == True).count()
            
            bidang_ids = [b.id for b in BidangLahan.query.filter(
                BidangLahan.sertifikat_id.in_(sert_ids), BidangLahan.is_active == True).all()]
            
            if bidang_ids:
                penyewa_count = Penyewa.query.filter(
                    Penyewa.bidang_lahan_id.in_(bidang_ids), Penyewa.is_active == True).count()
                luas_disewakan = db.session.query(func.sum(Penyewa.luas_disewakan)).filter(
                    Penyewa.bidang_lahan_id.in_(bidang_ids), Penyewa.is_active == True).scalar() or 0

                penyewa_ids = [p.id for p in Penyewa.query.filter(
                    Penyewa.bidang_lahan_id.in_(bidang_ids), Penyewa.is_active == True).all()]
                if penyewa_ids:
                    pendapatan = db.session.query(func.sum(Perjanjian.nilai_total)).filter(
                        Perjanjian.penyewa_id.in_(penyewa_ids),
                        Perjanjian.status == 'Aktif').scalar() or 0

        stats.append({
            'cabang': cab,
            'sertifikat': sert_count,
            'bidang': bidang_count,
            'luas_tanah': luas_tanah,
            'penyewa': penyewa_count,
            'luas_disewakan': luas_disewakan,
            'luas_tersedia': luas_tanah - luas_disewakan,
            'pendapatan': pendapatan,
            'persen_terpakai': round((luas_disewakan / luas_tanah * 100), 1) if luas_tanah > 0 else 0
        })

        total_sertifikat += sert_count
        total_bidang += bidang_count
        total_luas_tanah += luas_tanah
        total_penyewa += penyewa_count
        total_luas_disewakan += luas_disewakan
        total_pendapatan += pendapatan

    # Perjanjian expiring within 12 months
    today = date.today()
    from dateutil.relativedelta import relativedelta
    next_year = today + relativedelta(months=12)
    
    expiring_query = Perjanjian.query.filter(
        Perjanjian.status == 'Aktif',
        Perjanjian.tanggal_berakhir <= next_year,
        Perjanjian.tanggal_berakhir >= today
    ).join(Penyewa).join(BidangLahan).join(Sertifikat)
    
    if cabang_filter:
        expiring_query = expiring_query.filter(Sertifikat.cabang_id == cabang_filter)
    
    expiring = expiring_query.order_by(Perjanjian.tanggal_berakhir).limit(10).all()

    return render_template('dashboard.html',
                           stats=stats,
                           total_sertifikat=total_sertifikat,
                           total_bidang=total_bidang,
                           total_luas_tanah=total_luas_tanah,
                           total_penyewa=total_penyewa,
                           total_luas_disewakan=total_luas_disewakan,
                           total_pendapatan=total_pendapatan,
                           persen_total=round((total_luas_disewakan / total_luas_tanah * 100), 1) if total_luas_tanah > 0 else 0,
                           expiring=expiring,
                           today=today)


# ======================== MASTER CABANG ========================

@app.route('/cabang')
@login_required
def cabang_list():
    cabang_filter = get_user_cabang_filter()
    if cabang_filter:
        items = Cabang.query.filter_by(id=cabang_filter, is_active=True).all()
    else:
        items = Cabang.query.filter_by(is_active=True).order_by(Cabang.nama).all()
    return render_template('cabang/list.html', items=items)

@app.route('/cabang/tambah', methods=['GET', 'POST'])
@pusat_required
def cabang_tambah():
    if request.method == 'POST':
        cab = Cabang(
            kode=request.form['kode'].strip().upper(),
            nama=request.form['nama'].strip(),
            alamat=request.form.get('alamat', '').strip(),
            telepon=request.form.get('telepon', '').strip(),
            kepala_cabang=request.form.get('kepala_cabang', '').strip()
        )
        db.session.add(cab)
        db.session.commit()
        flash(f'Cabang {cab.nama} berhasil ditambahkan.', 'success')
        return redirect(url_for('cabang_list'))
    return render_template('cabang/form.html', item=None)

@app.route('/cabang/<int:id>/edit', methods=['GET', 'POST'])
@pusat_required
def cabang_edit(id):
    cab = db.session.get(Cabang, id) or abort(404)
    if request.method == 'POST':
        cab.kode = request.form['kode'].strip().upper()
        cab.nama = request.form['nama'].strip()
        cab.alamat = request.form.get('alamat', '').strip()
        cab.telepon = request.form.get('telepon', '').strip()
        cab.kepala_cabang = request.form.get('kepala_cabang', '').strip()
        db.session.commit()
        flash(f'Cabang {cab.nama} berhasil diperbarui.', 'success')
        return redirect(url_for('cabang_list'))
    return render_template('cabang/form.html', item=cab)

@app.route('/cabang/<int:id>/hapus', methods=['POST'])
@pusat_required
def cabang_hapus(id):
    cab = db.session.get(Cabang, id) or abort(404)
    cab.is_active = False
    db.session.commit()
    flash(f'Cabang {cab.nama} berhasil dihapus.', 'success')
    return redirect(url_for('cabang_list'))


# ======================== MASTER SERTIFIKAT ========================

@app.route('/sertifikat')
@login_required
def sertifikat_list():
    cabang_filter = get_user_cabang_filter()
    query = Sertifikat.query.filter_by(is_active=True)
    if cabang_filter:
        query = query.filter_by(cabang_id=cabang_filter)
    
    # Search
    search = request.args.get('q', '').strip()
    if search:
        query = query.filter(or_(
            Sertifikat.nomor_sertifikat.ilike(f'%{search}%'),
            Sertifikat.lokasi.ilike(f'%{search}%'),
            Sertifikat.jenis_hak.ilike(f'%{search}%')
        ))

    cab_id = request.args.get('cabang_id', type=int)
    if cab_id:
        query = query.filter_by(cabang_id=cab_id)

    items = query.order_by(Sertifikat.cabang_id, Sertifikat.nomor_sertifikat).all()
    cabang_all = Cabang.query.filter_by(is_active=True).order_by(Cabang.nama).all()
    return render_template('sertifikat/list.html', items=items, cabang_all=cabang_all,
                           search=search, cab_id=cab_id)

@app.route('/sertifikat/tambah', methods=['GET', 'POST'])
@login_required
def sertifikat_tambah():
    cabang_filter = get_user_cabang_filter()
    if request.method == 'POST':
        s = Sertifikat(
            cabang_id=int(request.form['cabang_id']),
            nomor_sertifikat=request.form['nomor_sertifikat'].strip(),
            jenis_hak=request.form['jenis_hak'].strip(),
            lokasi=request.form['lokasi'].strip(),
            luas_total=float(request.form['luas_total']),
            masa_berlaku=datetime.strptime(request.form['masa_berlaku'], '%Y-%m-%d').date() if request.form.get('masa_berlaku') else None,
            nomor_akta=request.form.get('nomor_akta', '').strip(),
            status_kepemilikan=request.form.get('status_kepemilikan', 'Milik sendiri'),
            kondisi=request.form.get('kondisi', 'Produktif'),
            keterangan=request.form.get('keterangan', '').strip()
        )
        file = request.files.get('scan_file')
        if file:
            s.scan_file = save_uploaded_file(file, 'sertifikat')
        db.session.add(s)
        db.session.commit()
        flash(f'Sertifikat {s.nomor_sertifikat} berhasil ditambahkan.', 'success')
        return redirect(url_for('sertifikat_list'))
    cabang_all = Cabang.query.filter_by(is_active=True).order_by(Cabang.nama).all()
    return render_template('sertifikat/form.html', item=None, cabang_all=cabang_all, cabang_filter=cabang_filter)

@app.route('/sertifikat/<int:id>')
@login_required
def sertifikat_detail(id):
    s = db.session.get(Sertifikat, id) or abort(404)
    cabang_filter = get_user_cabang_filter()
    if cabang_filter and s.cabang_id != cabang_filter:
        abort(403)
    bidangs = BidangLahan.query.filter_by(sertifikat_id=s.id, is_active=True).all()
    total_bidang_luas = sum(b.luas for b in bidangs)
    sisa_luas = s.luas_total - total_bidang_luas
    return render_template('sertifikat/detail.html', item=s, bidangs=bidangs,
                           total_bidang_luas=total_bidang_luas, sisa_luas=sisa_luas)

@app.route('/sertifikat/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def sertifikat_edit(id):
    s = db.session.get(Sertifikat, id) or abort(404)
    cabang_filter = get_user_cabang_filter()
    if cabang_filter and s.cabang_id != cabang_filter:
        abort(403)
    if request.method == 'POST':
        s.cabang_id = int(request.form['cabang_id'])
        s.nomor_sertifikat = request.form['nomor_sertifikat'].strip()
        s.jenis_hak = request.form['jenis_hak'].strip()
        s.lokasi = request.form['lokasi'].strip()
        s.luas_total = float(request.form['luas_total'])
        s.masa_berlaku = datetime.strptime(request.form['masa_berlaku'], '%Y-%m-%d').date() if request.form.get('masa_berlaku') else None
        s.nomor_akta = request.form.get('nomor_akta', '').strip()
        s.status_kepemilikan = request.form.get('status_kepemilikan', 'Milik sendiri')
        s.kondisi = request.form.get('kondisi', 'Produktif')
        s.keterangan = request.form.get('keterangan', '').strip()
        file = request.files.get('scan_file')
        if file and file.filename:
            s.scan_file = save_uploaded_file(file, 'sertifikat')
        db.session.commit()
        flash(f'Sertifikat {s.nomor_sertifikat} berhasil diperbarui.', 'success')
        return redirect(url_for('sertifikat_detail', id=s.id))
    cabang_all = Cabang.query.filter_by(is_active=True).order_by(Cabang.nama).all()
    return render_template('sertifikat/form.html', item=s, cabang_all=cabang_all, cabang_filter=cabang_filter)

@app.route('/sertifikat/<int:id>/hapus', methods=['POST'])
@login_required
def sertifikat_hapus(id):
    s = db.session.get(Sertifikat, id) or abort(404)
    s.is_active = False
    db.session.commit()
    flash(f'Sertifikat {s.nomor_sertifikat} berhasil dihapus.', 'success')
    return redirect(url_for('sertifikat_list'))


# ======================== MASTER BIDANG LAHAN ========================

@app.route('/bidang-lahan')
@login_required
def bidang_list():
    cabang_filter = get_user_cabang_filter()
    query = BidangLahan.query.filter_by(is_active=True).join(Sertifikat)
    if cabang_filter:
        query = query.filter(Sertifikat.cabang_id == cabang_filter)
    
    search = request.args.get('q', '').strip()
    if search:
        query = query.filter(or_(
            BidangLahan.kode_bidang.ilike(f'%{search}%'),
            BidangLahan.nama_bidang.ilike(f'%{search}%'),
            BidangLahan.alamat_lokasi.ilike(f'%{search}%')
        ))

    sert_id = request.args.get('sertifikat_id', type=int)
    if sert_id:
        query = query.filter(BidangLahan.sertifikat_id == sert_id)

    status = request.args.get('status', '')
    if status:
        query = query.filter(BidangLahan.status_pemanfaatan == status)

    items = query.order_by(BidangLahan.kode_bidang).all()
    sertifikat_all = Sertifikat.query.filter_by(is_active=True).all()
    return render_template('bidang/list.html', items=items, sertifikat_all=sertifikat_all,
                           search=search, sert_id=sert_id, status=status)

@app.route('/bidang-lahan/tambah', methods=['GET', 'POST'])
@login_required
def bidang_tambah():
    cabang_filter = get_user_cabang_filter()
    if request.method == 'POST':
        sert_id = int(request.form['sertifikat_id'])
        sert = db.session.get(Sertifikat, sert_id)
        if not sert:
            flash('Sertifikat tidak ditemukan.', 'danger')
            return redirect(url_for('bidang_list'))

        luas_baru = float(request.form['luas'])
        existing_luas = db.session.query(func.sum(BidangLahan.luas)).filter_by(
            sertifikat_id=sert_id, is_active=True).scalar() or 0
        
        if existing_luas + luas_baru > sert.luas_total:
            flash(f'GAGAL: Total luas bidang ({format_luas(existing_luas + luas_baru)} m²) melebihi luas sertifikat ({format_luas(sert.luas_total)} m²). Sisa tersedia: {format_luas(sert.luas_total - existing_luas)} m².', 'danger')
            sertifikat_all = Sertifikat.query.filter_by(is_active=True).all()
            return render_template('bidang/form.html', item=None, sertifikat_all=sertifikat_all, cabang_filter=cabang_filter)

        b = BidangLahan(
            sertifikat_id=sert_id,
            kode_bidang=request.form['kode_bidang'].strip(),
            nama_bidang=request.form.get('nama_bidang', '').strip(),
            luas=luas_baru,
            jenis_aset=request.form.get('jenis_aset', 'Lahan'),
            status_pemanfaatan=request.form.get('status_pemanfaatan', 'Belum Disewakan'),
            alamat_lokasi=request.form.get('alamat_lokasi', '').strip(),
            keterangan=request.form.get('keterangan', '').strip()
        )
        db.session.add(b)
        db.session.commit()
        flash(f'Bidang Lahan {b.kode_bidang} berhasil ditambahkan.', 'success')
        return redirect(url_for('bidang_list'))
    
    sertifikat_all = Sertifikat.query.filter_by(is_active=True).all()
    if cabang_filter:
        sertifikat_all = [s for s in sertifikat_all if s.cabang_id == cabang_filter]
    return render_template('bidang/form.html', item=None, sertifikat_all=sertifikat_all, cabang_filter=cabang_filter)

@app.route('/bidang-lahan/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def bidang_edit(id):
    b = db.session.get(BidangLahan, id) or abort(404)
    cabang_filter = get_user_cabang_filter()
    if request.method == 'POST':
        sert_id = int(request.form['sertifikat_id'])
        sert = db.session.get(Sertifikat, sert_id)
        luas_baru = float(request.form['luas'])
        existing_luas = db.session.query(func.sum(BidangLahan.luas)).filter(
            BidangLahan.sertifikat_id == sert_id,
            BidangLahan.is_active == True,
            BidangLahan.id != b.id).scalar() or 0
        
        if existing_luas + luas_baru > sert.luas_total:
            flash(f'GAGAL: Total luas bidang ({format_luas(existing_luas + luas_baru)} m²) melebihi luas sertifikat ({format_luas(sert.luas_total)} m²).', 'danger')
            sertifikat_all = Sertifikat.query.filter_by(is_active=True).all()
            return render_template('bidang/form.html', item=b, sertifikat_all=sertifikat_all, cabang_filter=cabang_filter)

        b.sertifikat_id = sert_id
        b.kode_bidang = request.form['kode_bidang'].strip()
        b.nama_bidang = request.form.get('nama_bidang', '').strip()
        b.luas = luas_baru
        b.jenis_aset = request.form.get('jenis_aset', 'Lahan')
        b.status_pemanfaatan = request.form.get('status_pemanfaatan', 'Belum Disewakan')
        b.alamat_lokasi = request.form.get('alamat_lokasi', '').strip()
        b.keterangan = request.form.get('keterangan', '').strip()
        db.session.commit()
        flash(f'Bidang Lahan {b.kode_bidang} berhasil diperbarui.', 'success')
        return redirect(url_for('bidang_list'))
    
    sertifikat_all = Sertifikat.query.filter_by(is_active=True).all()
    if cabang_filter:
        sertifikat_all = [s for s in sertifikat_all if s.cabang_id == cabang_filter]
    return render_template('bidang/form.html', item=b, sertifikat_all=sertifikat_all, cabang_filter=cabang_filter)

@app.route('/bidang-lahan/<int:id>/hapus', methods=['POST'])
@login_required
def bidang_hapus(id):
    b = db.session.get(BidangLahan, id) or abort(404)
    b.is_active = False
    db.session.commit()
    flash(f'Bidang Lahan {b.kode_bidang} berhasil dihapus.', 'success')
    return redirect(url_for('bidang_list'))

@app.route('/api/sertifikat/<int:sert_id>/sisa-luas')
@login_required
def api_sisa_luas(sert_id):
    sert = db.session.get(Sertifikat, sert_id)
    if not sert:
        return jsonify({'error': 'Not found'}), 404
    used = db.session.query(func.sum(BidangLahan.luas)).filter_by(
        sertifikat_id=sert_id, is_active=True).scalar() or 0
    exclude_id = request.args.get('exclude', type=int)
    if exclude_id:
        excluded_luas = db.session.query(BidangLahan.luas).filter_by(id=exclude_id).scalar() or 0
        used -= excluded_luas
    return jsonify({
        'luas_total': sert.luas_total,
        'luas_terpakai': used,
        'sisa': sert.luas_total - used
    })


# ======================== MASTER PENYEWA ========================

@app.route('/penyewa')
@login_required
def penyewa_list():
    cabang_filter = get_user_cabang_filter()
    query = Penyewa.query.filter_by(is_active=True).join(BidangLahan).join(Sertifikat)
    if cabang_filter:
        query = query.filter(Sertifikat.cabang_id == cabang_filter)
    
    search = request.args.get('q', '').strip()
    if search:
        query = query.filter(or_(
            Penyewa.nama.ilike(f'%{search}%'),
            Penyewa.npwp.ilike(f'%{search}%'),
            Penyewa.peruntukan.ilike(f'%{search}%')
        ))

    cab_id = request.args.get('cabang_id', type=int)
    if cab_id:
        query = query.filter(Sertifikat.cabang_id == cab_id)

    all_items = query.order_by(Penyewa.nama).all()
    
    # Calculate status counts for quick tabs
    count_total = len(all_items)
    count_aktif = 0
    count_akan_berakhir = 0
    count_sudah_berakhir = 0
    
    for item in all_items:
        info = hitung_sisa_periode(item)
        if info['status'] == 'active':
            count_aktif += 1
        elif info['status'] in ('warning', 'critical'):
            count_akan_berakhir += 1
        elif info['status'] == 'expired':
            count_sudah_berakhir += 1

    status_filter = request.args.get('status_sewa', 'semua').strip().lower()
    if status_filter == 'aktif':
        filtered_items = [p for p in all_items if hitung_sisa_periode(p)['status'] == 'active']
    elif status_filter == 'akan_berakhir':
        filtered_items = [p for p in all_items if hitung_sisa_periode(p)['status'] in ('warning', 'critical')]
    elif status_filter == 'sudah_berakhir':
        filtered_items = [p for p in all_items if hitung_sisa_periode(p)['status'] == 'expired']
    else:
        filtered_items = all_items

    cabang_all = Cabang.query.filter_by(is_active=True).order_by(Cabang.nama).all()
    return render_template('penyewa/list.html',
                           items=filtered_items,
                           cabang_all=cabang_all,
                           search=search,
                           cab_id=cab_id,
                           status_filter=status_filter,
                           count_total=count_total,
                           count_aktif=count_aktif,
                           count_akan_berakhir=count_akan_berakhir,
                           count_sudah_berakhir=count_sudah_berakhir)

@app.route('/penyewa/tambah', methods=['GET', 'POST'])
@login_required
def penyewa_tambah():
    cabang_filter = get_user_cabang_filter()
    if request.method == 'POST':
        p = Penyewa(
            bidang_lahan_id=int(request.form['bidang_lahan_id']),
            nama=request.form['nama'].strip(),
            jenis=request.form.get('jenis', 'Perorangan'),
            jabatan_penandatangan=request.form.get('jabatan_penandatangan', '').strip(),
            alamat=request.form.get('alamat', '').strip(),
            telepon=request.form.get('telepon', '').strip(),
            email=request.form.get('email', '').strip(),
            npwp=request.form.get('npwp', '').strip(),
            luas_disewakan=float(request.form['luas_disewakan']),
            peruntukan=request.form.get('peruntukan', '').strip(),
            status_hgb=request.form.get('status_hgb', 'Non HGB'),
            keterangan=request.form.get('keterangan', '').strip()
        )
        # Update bidang status
        bidang = db.session.get(BidangLahan, p.bidang_lahan_id)
        if bidang:
            bidang.status_pemanfaatan = 'Disewakan'
        db.session.add(p)
        db.session.commit()
        flash(f'Penyewa {p.nama} berhasil ditambahkan.', 'success')
        return redirect(url_for('penyewa_list'))
    
    bidang_query = BidangLahan.query.filter_by(is_active=True).join(Sertifikat)
    if cabang_filter:
        bidang_query = bidang_query.filter(Sertifikat.cabang_id == cabang_filter)
    bidang_all = bidang_query.all()
    return render_template('penyewa/form.html', item=None, bidang_all=bidang_all, cabang_filter=cabang_filter)

@app.route('/penyewa/<int:id>')
@login_required
def penyewa_detail(id):
    p = db.session.get(Penyewa, id) or abort(404)
    perjanjians = Perjanjian.query.filter_by(penyewa_id=p.id).order_by(Perjanjian.tanggal_mulai.desc()).all()
    riwayat = RiwayatPengalihan.query.filter(
        or_(RiwayatPengalihan.penyewa_lama_id == p.id,
            RiwayatPengalihan.penyewa_baru_id == p.id)
    ).order_by(RiwayatPengalihan.tanggal_pengalihan.desc()).all()
    return render_template('penyewa/detail.html', item=p, perjanjians=perjanjians, riwayat=riwayat)

@app.route('/penyewa/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def penyewa_edit(id):
    p = db.session.get(Penyewa, id) or abort(404)
    cabang_filter = get_user_cabang_filter()
    if request.method == 'POST':
        p.bidang_lahan_id = int(request.form['bidang_lahan_id'])
        p.nama = request.form['nama'].strip()
        p.jenis = request.form.get('jenis', 'Perorangan')
        p.jabatan_penandatangan = request.form.get('jabatan_penandatangan', '').strip()
        p.alamat = request.form.get('alamat', '').strip()
        p.telepon = request.form.get('telepon', '').strip()
        p.email = request.form.get('email', '').strip()
        p.npwp = request.form.get('npwp', '').strip()
        p.luas_disewakan = float(request.form['luas_disewakan'])
        p.peruntukan = request.form.get('peruntukan', '').strip()
        p.status_hgb = request.form.get('status_hgb', 'Non HGB')
        p.keterangan = request.form.get('keterangan', '').strip()
        db.session.commit()
        flash(f'Penyewa {p.nama} berhasil diperbarui.', 'success')
        return redirect(url_for('penyewa_detail', id=p.id))
    
    bidang_query = BidangLahan.query.filter_by(is_active=True).join(Sertifikat)
    if cabang_filter:
        bidang_query = bidang_query.filter(Sertifikat.cabang_id == cabang_filter)
    bidang_all = bidang_query.all()
    return render_template('penyewa/form.html', item=p, bidang_all=bidang_all, cabang_filter=cabang_filter)

@app.route('/penyewa/<int:id>/hapus', methods=['POST'])
@login_required
def penyewa_hapus(id):
    p = db.session.get(Penyewa, id) or abort(404)
    p.is_active = False
    db.session.commit()
    flash(f'Penyewa {p.nama} berhasil dihapus.', 'success')
    return redirect(url_for('penyewa_list'))


# ======================== MASTER PERJANJIAN ========================

@app.route('/perjanjian')
@login_required
def perjanjian_list():
    cabang_filter = get_user_cabang_filter()
    query = Perjanjian.query.join(Penyewa).join(BidangLahan).join(Sertifikat)
    if cabang_filter:
        query = query.filter(Sertifikat.cabang_id == cabang_filter)
    
    search = request.args.get('q', '').strip()
    if search:
        query = query.filter(or_(
            Perjanjian.nomor_perjanjian.ilike(f'%{search}%'),
            Penyewa.nama.ilike(f'%{search}%')
        ))

    status = request.args.get('status', '')
    if status:
        query = query.filter(Perjanjian.status == status)

    items = query.order_by(Perjanjian.tanggal_berakhir.desc()).all()
    return render_template('perjanjian/list.html', items=items, search=search, status=status)

@app.route('/perjanjian/tambah', methods=['GET', 'POST'])
@login_required
def perjanjian_tambah():
    cabang_filter = get_user_cabang_filter()
    if request.method == 'POST':
        pj = Perjanjian(
            penyewa_id=int(request.form['penyewa_id']),
            nomor_perjanjian=request.form['nomor_perjanjian'].strip(),
            tanggal_mulai=datetime.strptime(request.form['tanggal_mulai'], '%Y-%m-%d').date(),
            tanggal_berakhir=datetime.strptime(request.form['tanggal_berakhir'], '%Y-%m-%d').date(),
            masa_sewa_tahun=float(request.form.get('masa_sewa_tahun', 0) or 0),
            penandatangan_perindo=request.form.get('penandatangan_perindo', '').strip(),
            nilai_dc=float(request.form.get('nilai_dc', 0) or 0),
            nilai_sc=float(request.form.get('nilai_sc', 0) or 0),
            biaya_admin=float(request.form.get('biaya_admin', 0) or 0),
            nilai_total=float(request.form.get('nilai_total', 0) or 0),
            deposit=float(request.form.get('deposit', 0) or 0),
            rekening_perindo=request.form.get('rekening_perindo', '').strip(),
            bank_perindo=request.form.get('bank_perindo', '').strip(),
            status=request.form.get('status', 'Aktif'),
            keterangan=request.form.get('keterangan', '').strip(),
            is_perpanjangan=bool(request.form.get('is_perpanjangan')),
            perjanjian_asal_id=int(request.form['perjanjian_asal_id']) if request.form.get('perjanjian_asal_id') else None
        )
        file = request.files.get('dokumen_file')
        if file and file.filename:
            pj.dokumen_file = save_uploaded_file(file, 'perjanjian')
        db.session.add(pj)
        db.session.commit()
        flash(f'Perjanjian {pj.nomor_perjanjian} berhasil ditambahkan.', 'success')
        return redirect(url_for('perjanjian_list'))
    
    penyewa_query = Penyewa.query.filter_by(is_active=True).join(BidangLahan).join(Sertifikat)
    if cabang_filter:
        penyewa_query = penyewa_query.filter(Sertifikat.cabang_id == cabang_filter)
    penyewa_all = penyewa_query.order_by(Penyewa.nama).all()
    return render_template('perjanjian/form.html', item=None, penyewa_all=penyewa_all)

@app.route('/perjanjian/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def perjanjian_edit(id):
    pj = db.session.get(Perjanjian, id) or abort(404)
    cabang_filter = get_user_cabang_filter()
    if request.method == 'POST':
        pj.penyewa_id = int(request.form['penyewa_id'])
        pj.nomor_perjanjian = request.form['nomor_perjanjian'].strip()
        pj.tanggal_mulai = datetime.strptime(request.form['tanggal_mulai'], '%Y-%m-%d').date()
        pj.tanggal_berakhir = datetime.strptime(request.form['tanggal_berakhir'], '%Y-%m-%d').date()
        pj.masa_sewa_tahun = float(request.form.get('masa_sewa_tahun', 0) or 0)
        pj.penandatangan_perindo = request.form.get('penandatangan_perindo', '').strip()
        pj.nilai_dc = float(request.form.get('nilai_dc', 0) or 0)
        pj.nilai_sc = float(request.form.get('nilai_sc', 0) or 0)
        pj.biaya_admin = float(request.form.get('biaya_admin', 0) or 0)
        pj.nilai_total = float(request.form.get('nilai_total', 0) or 0)
        pj.deposit = float(request.form.get('deposit', 0) or 0)
        pj.rekening_perindo = request.form.get('rekening_perindo', '').strip()
        pj.bank_perindo = request.form.get('bank_perindo', '').strip()
        pj.status = request.form.get('status', 'Aktif')
        pj.keterangan = request.form.get('keterangan', '').strip()
        pj.is_perpanjangan = bool(request.form.get('is_perpanjangan'))
        pj.perjanjian_asal_id = int(request.form['perjanjian_asal_id']) if request.form.get('perjanjian_asal_id') else None
        file = request.files.get('dokumen_file')
        if file and file.filename:
            pj.dokumen_file = save_uploaded_file(file, 'perjanjian')
        db.session.commit()
        flash(f'Perjanjian {pj.nomor_perjanjian} berhasil diperbarui.', 'success')
        return redirect(url_for('perjanjian_list'))
    
    penyewa_query = Penyewa.query.filter_by(is_active=True).join(BidangLahan).join(Sertifikat)
    if cabang_filter:
        penyewa_query = penyewa_query.filter(Sertifikat.cabang_id == cabang_filter)
    penyewa_all = penyewa_query.order_by(Penyewa.nama).all()
    return render_template('perjanjian/form.html', item=pj, penyewa_all=penyewa_all)

@app.route('/perjanjian/<int:id>/hapus', methods=['POST'])
@login_required
def perjanjian_hapus(id):
    pj = db.session.get(Perjanjian, id) or abort(404)
    db.session.delete(pj)
    db.session.commit()
    flash('Perjanjian berhasil dihapus.', 'success')
    return redirect(url_for('perjanjian_list'))

@app.route('/perjanjian/<int:id>/perpanjang', methods=['GET', 'POST'])
@login_required
def perjanjian_perpanjang(id):
    pj_lama = db.session.get(Perjanjian, id) or abort(404)
    cabang_filter = get_user_cabang_filter()
    if request.method == 'POST':
        pj_baru = Perjanjian(
            penyewa_id=pj_lama.penyewa_id,
            nomor_perjanjian=request.form['nomor_perjanjian'].strip(),
            tanggal_mulai=datetime.strptime(request.form['tanggal_mulai'], '%Y-%m-%d').date(),
            tanggal_berakhir=datetime.strptime(request.form['tanggal_berakhir'], '%Y-%m-%d').date(),
            masa_sewa_tahun=float(request.form.get('masa_sewa_tahun', 0) or 0),
            penandatangan_perindo=request.form.get('penandatangan_perindo', '').strip(),
            nilai_dc=float(request.form.get('nilai_dc', 0) or 0),
            nilai_sc=float(request.form.get('nilai_sc', 0) or 0),
            biaya_admin=float(request.form.get('biaya_admin', 0) or 0),
            nilai_total=float(request.form.get('nilai_total', 0) or 0),
            deposit=float(request.form.get('deposit', 0) or 0),
            rekening_perindo=request.form.get('rekening_perindo', '').strip(),
            bank_perindo=request.form.get('bank_perindo', '').strip(),
            status='Aktif',
            is_perpanjangan=True,
            perjanjian_asal_id=pj_lama.id,
            keterangan=request.form.get('keterangan', '').strip()
        )
        file = request.files.get('dokumen_file')
        if file and file.filename:
            pj_baru.dokumen_file = save_uploaded_file(file, 'perjanjian')
        pj_lama.status = 'Berakhir'
        db.session.add(pj_baru)
        db.session.commit()
        flash(f'Perpanjangan perjanjian berhasil dibuat: {pj_baru.nomor_perjanjian}', 'success')
        return redirect(url_for('perjanjian_list'))
    
    return render_template('perjanjian/perpanjang.html', pj_lama=pj_lama)


# ======================== PENGALIHAN PENYEWA ========================

@app.route('/pengalihan')
@login_required
def pengalihan_list():
    cabang_filter = get_user_cabang_filter()
    query = RiwayatPengalihan.query.join(BidangLahan).join(Sertifikat)
    if cabang_filter:
        query = query.filter(Sertifikat.cabang_id == cabang_filter)
    items = query.order_by(RiwayatPengalihan.tanggal_pengalihan.desc()).all()
    return render_template('pengalihan/list.html', items=items)

@app.route('/pengalihan/tambah', methods=['GET', 'POST'])
@login_required
def pengalihan_tambah():
    cabang_filter = get_user_cabang_filter()
    if request.method == 'POST':
        rp = RiwayatPengalihan(
            bidang_lahan_id=int(request.form['bidang_lahan_id']),
            penyewa_lama_id=int(request.form['penyewa_lama_id']),
            penyewa_baru_id=int(request.form['penyewa_baru_id']),
            tanggal_pengalihan=datetime.strptime(request.form['tanggal_pengalihan'], '%Y-%m-%d').date(),
            nomor_dokumen=request.form.get('nomor_dokumen', '').strip(),
            keterangan=request.form.get('keterangan', '').strip()
        )
        file = request.files.get('dokumen_file')
        if file and file.filename:
            rp.dokumen_file = save_uploaded_file(file, 'pengalihan')
        
        # Deactivate old tenant
        old = db.session.get(Penyewa, rp.penyewa_lama_id)
        if old:
            old.is_active = False
        
        db.session.add(rp)
        db.session.commit()
        flash('Pengalihan penyewa berhasil dicatat.', 'success')
        return redirect(url_for('pengalihan_list'))
    
    penyewa_query = Penyewa.query.filter_by(is_active=True).join(BidangLahan).join(Sertifikat)
    if cabang_filter:
        penyewa_query = penyewa_query.filter(Sertifikat.cabang_id == cabang_filter)
    penyewa_all = penyewa_query.order_by(Penyewa.nama).all()
    
    bidang_query = BidangLahan.query.filter_by(is_active=True).join(Sertifikat)
    if cabang_filter:
        bidang_query = bidang_query.filter(Sertifikat.cabang_id == cabang_filter)
    bidang_all = bidang_query.all()
    
    return render_template('pengalihan/form.html', penyewa_all=penyewa_all, bidang_all=bidang_all)


# ======================== MONITORING ========================

@app.route('/monitoring')
@login_required
def monitoring():
    cabang_filter = get_user_cabang_filter()
    today = date.today()
    
    # Active perjanjian with status info
    query = Perjanjian.query.filter_by(status='Aktif').join(Penyewa).filter(
        Penyewa.is_active == True).join(BidangLahan).join(Sertifikat)
    if cabang_filter:
        query = query.filter(Sertifikat.cabang_id == cabang_filter)

    cab_id = request.args.get('cabang_id', type=int)
    if cab_id:
        query = query.filter(Sertifikat.cabang_id == cab_id)

    search = request.args.get('q', '').strip()
    if search:
        query = query.filter(or_(
            Penyewa.nama.ilike(f'%{search}%'),
            Perjanjian.nomor_perjanjian.ilike(f'%{search}%')
        ))

    perjanjians = query.order_by(Perjanjian.tanggal_berakhir).all()
    
    # Categorize
    berakhir = []
    segera_berakhir = []  # < 12 months
    aktif_normal = []
    
    from dateutil.relativedelta import relativedelta
    batas_12_bulan = today + relativedelta(months=12)
    
    for pj in perjanjians:
        if pj.tanggal_berakhir < today:
            berakhir.append(pj)
        elif pj.tanggal_berakhir <= batas_12_bulan:
            segera_berakhir.append(pj)
        else:
            aktif_normal.append(pj)

    # Land usage summary
    sert_query = Sertifikat.query.filter_by(is_active=True)
    if cabang_filter:
        sert_query = sert_query.filter_by(cabang_id=cabang_filter)
    if cab_id:
        sert_query = sert_query.filter_by(cabang_id=cab_id)
    
    sertifikats = sert_query.all()
    lahan_summary = []
    for s in sertifikats:
        bidangs = BidangLahan.query.filter_by(sertifikat_id=s.id, is_active=True).all()
        total_bidang = sum(b.luas for b in bidangs)
        disewakan = sum(b.luas for b in bidangs if b.status_pemanfaatan == 'Disewakan')
        lahan_summary.append({
            'sertifikat': s,
            'total_bidang': total_bidang,
            'disewakan': disewakan,
            'belum': total_bidang - disewakan,
            'sisa_sertifikat': s.luas_total - total_bidang
        })

    cabang_all = Cabang.query.filter_by(is_active=True).order_by(Cabang.nama).all()

    return render_template('monitoring.html',
                           berakhir=berakhir,
                           segera_berakhir=segera_berakhir,
                           aktif_normal=aktif_normal,
                           lahan_summary=lahan_summary,
                           cabang_all=cabang_all,
                           today=today,
                           search=search,
                           cab_id=cab_id)


# ======================== LAPORAN / EXPORT ========================

@app.route('/laporan')
@login_required
def laporan():
    cabang_all = Cabang.query.filter_by(is_active=True).order_by(Cabang.nama).all()
    return render_template('laporan.html', cabang_all=cabang_all)

@app.route('/laporan/export-excel')
@login_required
def export_excel():
    import openpyxl
    from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
    
    cabang_filter = get_user_cabang_filter()
    cab_id = request.args.get('cabang_id', type=int)
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Data Penyewa Lahan"
    
    # Header styles
    header_font = Font(bold=True, color='FFFFFF', size=11)
    header_fill = PatternFill(start_color='1F4E79', end_color='1F4E79', fill_type='solid')
    header_alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    thin_border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin')
    )
    
    headers = ['No', 'Cabang', 'Lokasi', 'Sertifikat', 'Jenis Hak', 'Luas Sertifikat (m²)',
               'Kode Bidang', 'Luas Bidang (m²)', 'Nama Penyewa', 'Jenis', 'Luas Sewa (m²)',
               'Status HGB', 'Peruntukan', 'No Perjanjian', 'Tgl Mulai', 'Tgl Berakhir',
               'Masa Sewa (Th)', 'Nilai DC (Rp)', 'SC/Tahun (Rp)', 'Biaya Admin (Rp)',
               'Total (Rp)', 'Deposit (Rp)', 'Status Perjanjian']
    
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = thin_border

    query = Penyewa.query.filter_by(is_active=True).join(BidangLahan).join(Sertifikat).join(Cabang)
    if cabang_filter:
        query = query.filter(Sertifikat.cabang_id == cabang_filter)
    if cab_id:
        query = query.filter(Sertifikat.cabang_id == cab_id)
    
    penyewas = query.order_by(Cabang.nama, Sertifikat.nomor_sertifikat, Penyewa.nama).all()
    
    row_num = 2
    for idx, p in enumerate(penyewas, 1):
        bidang = p.bidang_lahan
        sert = bidang.sertifikat
        cab = sert.cabang
        pj = p.perjanjians.filter_by(status='Aktif').first()
        
        data = [
            idx, cab.nama, sert.lokasi, sert.nomor_sertifikat, sert.jenis_hak,
            sert.luas_total, bidang.kode_bidang, bidang.luas, p.nama, p.jenis,
            p.luas_disewakan, p.status_hgb, p.peruntukan,
            pj.nomor_perjanjian if pj else '-',
            pj.tanggal_mulai.strftime('%d/%m/%Y') if pj else '-',
            pj.tanggal_berakhir.strftime('%d/%m/%Y') if pj else '-',
            pj.masa_sewa_tahun if pj else 0,
            pj.nilai_dc if pj else 0,
            pj.nilai_sc if pj else 0,
            pj.biaya_admin if pj else 0,
            pj.nilai_total if pj else 0,
            pj.deposit if pj else 0,
            pj.status if pj else '-'
        ]
        for col, val in enumerate(data, 1):
            cell = ws.cell(row=row_num, column=col, value=val)
            cell.border = thin_border
        row_num += 1

    # Auto-width
    for col in ws.columns:
        max_len = 0
        for cell in col:
            try:
                if len(str(cell.value)) > max_len:
                    max_len = len(str(cell.value))
            except:
                pass
        ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 35)

    filepath = os.path.join(BASE_DIR, 'uploads', 'export_penyewa_lahan.xlsx')
    wb.save(filepath)
    return send_file(filepath, as_attachment=True, download_name='Data_Penyewa_Lahan_Perindo.xlsx')


# ======================== FILE SERVING ========================

@app.route('/uploads/<path:filename>')
@login_required
def uploaded_file(filename):
    return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename))


# ======================== USER MANAGEMENT ========================

@app.route('/users')
@pusat_required
def user_list():
    users = User.query.filter_by(is_active=True).order_by(User.role, User.username).all()
    return render_template('users/list.html', users=users)

@app.route('/users/tambah', methods=['GET', 'POST'])
@pusat_required
def user_tambah():
    if request.method == 'POST':
        u = User(
            username=request.form['username'].strip(),
            nama_lengkap=request.form['nama_lengkap'].strip(),
            role=request.form['role'],
            cabang_id=int(request.form['cabang_id']) if request.form.get('cabang_id') else None
        )
        u.set_password(request.form['password'])
        db.session.add(u)
        db.session.commit()
        flash(f'User {u.username} berhasil ditambahkan.', 'success')
        return redirect(url_for('user_list'))
    cabang_all = Cabang.query.filter_by(is_active=True).order_by(Cabang.nama).all()
    return render_template('users/form.html', item=None, cabang_all=cabang_all)

@app.route('/users/<int:id>/edit', methods=['GET', 'POST'])
@pusat_required
def user_edit(id):
    u = db.session.get(User, id) or abort(404)
    if request.method == 'POST':
        u.username = request.form['username'].strip()
        u.nama_lengkap = request.form['nama_lengkap'].strip()
        u.role = request.form['role']
        u.cabang_id = int(request.form['cabang_id']) if request.form.get('cabang_id') else None
        if request.form.get('password'):
            u.set_password(request.form['password'])
        db.session.commit()
        flash(f'User {u.username} berhasil diperbarui.', 'success')
        return redirect(url_for('user_list'))
    cabang_all = Cabang.query.filter_by(is_active=True).order_by(Cabang.nama).all()
    return render_template('users/form.html', item=u, cabang_all=cabang_all)

@app.route('/users/<int:id>/hapus', methods=['POST'])
@pusat_required
def user_hapus(id):
    u = db.session.get(User, id) or abort(404)
    u.is_active = False
    db.session.commit()
    flash(f'User {u.username} berhasil dihapus.', 'success')
    return redirect(url_for('user_list'))


# ======================== IMPORT DATA ========================

@app.route('/import', methods=['GET', 'POST'])
@pusat_required
def import_data():
    if request.method == 'POST':
        file = request.files.get('file')
        if not file or not file.filename.endswith(('.xlsx', '.xls')):
            flash('Harap upload file Excel (.xlsx).', 'danger')
            return redirect(url_for('import_data'))
        
        import openpyxl
        filepath = os.path.join(BASE_DIR, 'uploads', 'import_temp.xlsx')
        file.save(filepath)
        
        try:
            wb = openpyxl.load_workbook(filepath, data_only=True)
            ws = wb[wb.sheetnames[0]]
            
            imported = 0
            
            # Detect cabang from sheet or row A
            current_cabang = None
            current_sertifikat = None
            
            for row_idx in range(6, ws.max_row + 1):
                cabang_val = ws.cell(row=row_idx, column=1).value
                lokasi_val = ws.cell(row=row_idx, column=2).value
                alas_hak = ws.cell(row=row_idx, column=3).value
                luas_sert = ws.cell(row=row_idx, column=4).value
                nama_penyewa = ws.cell(row=row_idx, column=11).value
                
                if cabang_val and cabang_val not in ('Sub Total', 'Total'):
                    cab = Cabang.query.filter_by(nama=cabang_val).first()
                    if not cab:
                        cab = Cabang(kode=cabang_val[:10].upper().replace(' ', ''), nama=cabang_val)
                        db.session.add(cab)
                        db.session.flush()
                    current_cabang = cab
                
                if alas_hak and luas_sert and current_cabang:
                    sert = Sertifikat.query.filter_by(
                        nomor_sertifikat=str(alas_hak),
                        cabang_id=current_cabang.id
                    ).first()
                    if not sert:
                        jenis = 'HPL' if 'Pengelolaan' in str(alas_hak) else 'HP' if 'Pakai' in str(alas_hak) else 'HGB'
                        sert = Sertifikat(
                            cabang_id=current_cabang.id,
                            nomor_sertifikat=str(alas_hak),
                            jenis_hak=jenis,
                            lokasi=str(lokasi_val or ''),
                            luas_total=float(luas_sert),
                            status_kepemilikan=str(ws.cell(row=row_idx, column=8).value or 'Milik sendiri'),
                            kondisi=str(ws.cell(row=row_idx, column=7).value or 'Produktif'),
                            nomor_akta=str(ws.cell(row=row_idx, column=10).value or '')
                        )
                        db.session.add(sert)
                        db.session.flush()
                    current_sertifikat = sert
                
                if not nama_penyewa or nama_penyewa in ('-', 'Sub Total', 'Total') or not current_sertifikat:
                    continue
                
                alamat = str(ws.cell(row=row_idx, column=14).value or '')
                luas_sewa = ws.cell(row=row_idx, column=16).value
                if not luas_sewa:
                    continue
                
                # Create bidang from alamat
                kode_bidang = alamat[:50] if alamat else f'BDG-{row_idx}'
                bidang = BidangLahan.query.filter_by(
                    sertifikat_id=current_sertifikat.id,
                    kode_bidang=kode_bidang
                ).first()
                if not bidang:
                    bidang = BidangLahan(
                        sertifikat_id=current_sertifikat.id,
                        kode_bidang=kode_bidang,
                        nama_bidang=alamat,
                        luas=float(luas_sewa),
                        jenis_aset=str(ws.cell(row=row_idx, column=15).value or 'Lahan'),
                        status_pemanfaatan='Disewakan',
                        alamat_lokasi=alamat
                    )
                    db.session.add(bidang)
                    db.session.flush()
                
                # Check if penyewa already exists
                existing = Penyewa.query.filter_by(
                    nama=str(nama_penyewa).strip(),
                    bidang_lahan_id=bidang.id
                ).first()
                if existing:
                    continue
                
                status_sewa = str(ws.cell(row=row_idx, column=21).value or 'Non HGB')
                penandatangan = str(ws.cell(row=row_idx, column=12).value or '')
                jenis_pemohon = 'Badan Usaha' if 'PT ' in str(nama_penyewa) or 'CV ' in str(nama_penyewa) else 'Perorangan'
                
                penyewa = Penyewa(
                    bidang_lahan_id=bidang.id,
                    nama=str(nama_penyewa).strip(),
                    jenis=jenis_pemohon,
                    jabatan_penandatangan=penandatangan,
                    alamat=alamat,
                    luas_disewakan=float(luas_sewa),
                    peruntukan=str(ws.cell(row=row_idx, column=15).value or 'Lahan'),
                    status_hgb=status_sewa if status_sewa in ('HGB', 'Non HGB') else 'Non HGB'
                )
                db.session.add(penyewa)
                db.session.flush()
                
                # Create perjanjian
                no_prj = ws.cell(row=row_idx, column=17).value
                tgl_mulai = ws.cell(row=row_idx, column=18).value
                tgl_akhir = ws.cell(row=row_idx, column=19).value
                
                if no_prj and no_prj != '-':
                    try:
                        if isinstance(tgl_mulai, datetime):
                            dm = tgl_mulai.date()
                        elif isinstance(tgl_mulai, str):
                            for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%m/%d/%Y'):
                                try:
                                    dm = datetime.strptime(tgl_mulai, fmt).date()
                                    break
                                except ValueError:
                                    continue
                            else:
                                dm = date(2020, 1, 1)
                        elif isinstance(tgl_mulai, date):
                            dm = tgl_mulai
                        else:
                            dm = date(2020, 1, 1)
                            
                        if isinstance(tgl_akhir, datetime):
                            da = tgl_akhir.date()
                        elif isinstance(tgl_akhir, str):
                            for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%m/%d/%Y'):
                                try:
                                    da = datetime.strptime(tgl_akhir, fmt).date()
                                    break
                                except ValueError:
                                    continue
                            else:
                                da = date(2040, 12, 31)
                        elif isinstance(tgl_akhir, date):
                            da = tgl_akhir
                        else:
                            da = date(2040, 12, 31)
                        
                        masa = ws.cell(row=row_idx, column=20).value
                        nilai_dc = ws.cell(row=row_idx, column=22).value
                        nilai_sc = ws.cell(row=row_idx, column=23).value
                        biaya_adm = ws.cell(row=row_idx, column=24).value
                        total_val = ws.cell(row=row_idx, column=25).value
                        deposit_val = ws.cell(row=row_idx, column=34).value
                        rek_val = ws.cell(row=row_idx, column=26).value
                        bank_val = ws.cell(row=row_idx, column=27).value
                        penandatangan_perindo = str(ws.cell(row=row_idx, column=13).value or '')
                        
                        perjanjian = Perjanjian(
                            penyewa_id=penyewa.id,
                            nomor_perjanjian=str(no_prj).strip(),
                            tanggal_mulai=dm,
                            tanggal_berakhir=da,
                            masa_sewa_tahun=float(masa) if masa else 0,
                            penandatangan_perindo=penandatangan_perindo,
                            nilai_dc=float(nilai_dc) if nilai_dc else 0,
                            nilai_sc=float(nilai_sc) if nilai_sc else 0,
                            biaya_admin=float(biaya_adm) if biaya_adm else 0,
                            nilai_total=float(total_val) if total_val else 0,
                            deposit=float(deposit_val) if deposit_val else 0,
                            rekening_perindo=str(rek_val or ''),
                            bank_perindo=str(bank_val or ''),
                            status='Aktif' if da >= date.today() else 'Berakhir'
                        )
                        db.session.add(perjanjian)
                    except Exception as e:
                        print(f"Warning row {row_idx}: {e}")
                        continue
                
                imported += 1
            
            db.session.commit()
            flash(f'Berhasil mengimpor {imported} data penyewa.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error saat import: {str(e)}', 'danger')
        
        return redirect(url_for('import_data'))
    
    return render_template('import.html')


# ======================== INIT DB & SEED ========================

def init_db():
    with app.app_context():
        db.create_all()
        
        # Create default admin if not exists
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                nama_lengkap='Administrator Kantor Pusat',
                role='pusat'
            )
            admin.set_password('admin123')
            db.session.add(admin)
            
            # Seed cabang data
            cabang_data = [
                ('JKT', 'Jakarta', 'Pelabuhan Perikanan Samudera Nizam Zachman, Muara Baru'),
                ('BLW', 'Belawan', 'Pelabuhan Perikanan Samudera Belawan, Medan'),
                ('PKL', 'Pekalongan', 'Pelabuhan Perikanan Nusantara Pekalongan'),
                ('TGL', 'Tegal', 'Pelabuhan Perikanan Pantai Tegalsari, Tegal'),
                ('PRG', 'Prigi', 'Pelabuhan Perikanan Nusantara Prigi, Trenggalek'),
                ('PTI', 'Pati', 'Pelabuhan Perikanan Pantai Bajomulyo, Pati'),
                ('MYG', 'Mayangan', 'Pelabuhan Perikanan Pantai Mayangan, Probolinggo'),
                ('RMB', 'Rembang', 'Pelabuhan Perikanan Pantai Tasikagung, Rembang'),
                ('BNG', 'Benoa', 'Pelabuhan Perikanan Benoa, Bali'),
                ('SKB', 'Sukabumi', 'Pelabuhan Perikanan Pantai Palabuhanratu, Sukabumi'),
                ('SRG', 'Sorong', 'Pelabuhan Perikanan Sorong, Papua Barat'),
                ('AMB', 'Ambon', 'Pelabuhan Perikanan Ambon, Maluku'),
                ('KDR', 'Kendari', 'Pelabuhan Perikanan Samudera Kendari'),
                ('BTG', 'Bitung', 'Pelabuhan Perikanan Samudera Bitung, Sulawesi Utara'),
                ('BDN', 'Banjarmasin', 'Pelabuhan Perikanan Banjarmasin, Kalimantan Selatan'),
            ]
            
            for kode, nama, alamat in cabang_data:
                if not Cabang.query.filter_by(kode=kode).first():
                    cab = Cabang(kode=kode, nama=nama, alamat=alamat)
                    db.session.add(cab)
            
            # Create cabang user sample
            db.session.flush()
            cab_jkt = Cabang.query.filter_by(kode='JKT').first()
            if cab_jkt:
                if not User.query.filter_by(username='jakarta').first():
                    user_jkt = User(
                        username='jakarta',
                        nama_lengkap='Admin Cabang Jakarta',
                        role='cabang',
                        cabang_id=cab_jkt.id
                    )
                    user_jkt.set_password('jakarta123')
                    db.session.add(user_jkt)
            
            db.session.commit()
            print("Database initialized with default data.")


# Ensure tables exist on import/startup
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=True)
