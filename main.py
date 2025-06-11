from flask import Flask, render_template, request, redirect, session, flash, url_for
from flaskext.mysql import MySQL
from PIL import Image
from werkzeug.utils import secure_filename
from datetime import timedelta 
import os

app = Flask(__name__)
app.secret_key = 'rahasia'

app.permanent_session_lifetime = timedelta(minutes=60)

# Koneksi ke database dbtokoa
db = MySQL(host="localhost", user="root", passwd="", db="dbtokoa")
db.init_app(app)

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'jfif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def is_admin():
    return session.get('user') and session.get('role') == 'admin'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_user_id_by_username(username):
    with db.get_db().cursor() as cursor:
        cursor.execute("SELECT id FROM user WHERE username = %s", (username,))
        result = cursor.fetchone()
        return result[0] if result else None


@app.route('/')
def index():
    try:
        with db.get_db().cursor() as cursor:
            cursor.execute("SELECT * FROM barang")
            barangs = cursor.fetchall()
    except Exception as e:
        flash(f"Gagal mengambil data barang: {e}", "danger")
        barangs = []
    return render_template('user/index.html', hasil=barangs)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        try:
            conn = db.get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM user WHERE username=%s AND password=%s", (username, password))
            user = cursor.fetchone()
            if user:
                session.permanent = True  # 
                session['user'] = user[1]
                session['role'] = user[3]
                return redirect('/admin/home' if user[3] == 'admin' else '/')
            else:
                flash('Username atau password salah!', 'danger')
        except Exception as e:
            flash(f'Gagal login: {e}', 'danger')
        return redirect('/login')
    return render_template('user/login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        try:
            with db.get_db().cursor() as cursor:
                cursor.execute("SELECT * FROM user WHERE username = %s", (username,))
                if cursor.fetchone():
                    flash('Username sudah digunakan!', 'danger')
                    return redirect('/register')
                cursor.execute("INSERT INTO user (username, password, role) VALUES (%s, %s, 'user')", (username, password))
                db.get_db().commit()
                flash('Pendaftaran berhasil! Silakan login.', 'success')
                return redirect('/login')
        except Exception as e:
            flash(f'Terjadi kesalahan: {e}', 'danger')
            return redirect('/register')
    return render_template('user/register.html')


@app.route('/kontak')
def kontak():
    return render_template('user/kontak.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# ----------------------------- Admin: Beranda -----------------------------
@app.route('/admin/home')
def home():
    if not is_admin():
        return redirect('/login')
    try:
        conn = db.get_db()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM barang")
        total_menu = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM pesanan")
        total_pesanan = cursor.fetchone()[0]

    except Exception as e:
        flash(f"Gagal mengambil data dashboard: {e}", "danger")
        total_menu, total_pesanan = 0, 0

    return render_template('admin/index.html', total_menu=total_menu, total_pesanan=total_pesanan)




# ----------------------------- Admin: Pesanan -----------------------------

@app.route('/admin/pesanan')
def admin_pesanan():
    if not is_admin():
        return redirect('/login')
    try:
        with db.get_db().cursor() as cursor:
            cursor.execute("""
                SELECT p.id, u.username, b.nama AS nama_barang, p.jumlah, p.status
                FROM pesanan p
                JOIN user u ON p.user_id = u.id
                JOIN barang b ON p.barang_id = b.id
                ORDER BY p.id DESC
            """)
            hasil = cursor.fetchall()
    except Exception as e:
        flash(f"Gagal mengambil data pesanan: {e}", "danger")
        hasil = []
    return render_template('admin/pesanan.html', hasil=hasil)


@app.route('/admin/admin-kelola-barang')
def kelolabarang():
    if not is_admin():
        return redirect('/login')
    try:
        with db.get_db().cursor() as cursor:
            cursor.execute("SELECT * FROM barang")
            data = cursor.fetchall()
    except Exception as e:
        flash(f"Gagal mengambil data: {e}", "danger")
        data = []
    return render_template('admin/barang.html', hasil=data)

@app.route('/admin/form-tambah-barang', methods=['GET', 'POST'])
def formbarang():
    if not is_admin():
        return redirect('/login')
    if request.method == 'POST':
        nama = request.form['nama']
        harga = request.form['harga']
        stok = request.form['stok']
        kategori = request.form['kategori']
        deskripsi = request.form['deskripsi']
        status = request.form['status']
        gambar_file = request.files['gambar']
        nama_file_jpg = None
        if gambar_file and allowed_file(gambar_file.filename):
            filename = secure_filename(gambar_file.filename)
            filename_base = os.path.splitext(filename)[0]
            nama_file_jpg = filename_base + '.jpg'
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], nama_file_jpg)
            img = Image.open(gambar_file)
            rgb_img = img.convert('RGB')
            rgb_img.save(filepath, format='JPEG')
        try:
            with db.get_db().cursor() as cursor:
                cursor.execute("""
                    INSERT INTO barang (nama, harga, stok, kategori, deskripsi, status, gambar)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (nama, harga, stok, kategori, deskripsi, status, nama_file_jpg))
                db.get_db().commit()
                flash("Barang berhasil ditambahkan!", "success")
        except Exception as e:
            flash(f"Gagal menyimpan data barang: {e}", "danger")
        return redirect('/admin/admin-kelola-barang')
    return render_template('admin/formbarang.html')

@app.route('/admin/form-edit-barang/<int:id>', methods=['GET', 'POST'])
def formeditbarang(id):
    if not is_admin():
        return redirect('/login')
    if request.method == 'POST':
        nama = request.form['nama']
        harga = request.form['harga']
        stok = request.form['stok']
        kategori = request.form['kategori']
        deskripsi = request.form['deskripsi']
        status = request.form['status']
        try:
            with db.get_db().cursor() as cursor:
                cursor.execute(
                    "UPDATE barang SET nama=%s, harga=%s, stok=%s, kategori=%s, deskripsi=%s, status=%s WHERE id=%s",
                    (nama, harga, stok, kategori, deskripsi, status, id)
                )
                db.get_db().commit()
                flash("Data barang berhasil diupdate!", "success")
        except Exception as e:
            flash(f'Terjadi kesalahan: {e}', 'danger')
        return redirect('/admin/admin-kelola-barang')

    try:
        with db.get_db().cursor() as cursor:
            cursor.execute("SELECT * FROM barang WHERE id=%s", (id,))
            data = cursor.fetchone()
        return render_template('admin/formeditbarang.html', barang=data)
    except Exception as e:
        flash(f'Gagal mengambil data: {e}', 'danger')
        return redirect('/admin/admin-kelola-barang')

@app.route('/admin/hapus-barang/<int:id>', methods=['POST'])
def hapus_barang(id):
    if not is_admin():
        return redirect('/login')
    try:
        with db.get_db().cursor() as cursor:
            cursor.execute("DELETE FROM barang WHERE id = %s", (id,))
            db.get_db().commit()
            flash("Barang berhasil dihapus.", "success")
    except Exception as e:
        flash(f"Gagal menghapus barang: {e}", "danger")
    return redirect('/admin/admin-kelola-barang')

@app.route('/admin/admin-kelola-pengguna')
def kelolapengguna():
    if not is_admin():
        return redirect('/login')
    try:
        with db.get_db().cursor() as cursor:
            cursor.execute("SELECT id, username, role FROM user")
            data = cursor.fetchall()
    except Exception as e:
        flash(f"Gagal mengambil data: {e}", "danger")
        data = []
    return render_template('admin/pengguna.html', hasil=data)

@app.route('/admin/form-tambah-pengguna', methods=['GET', 'POST'])
def formpengguna():
    if not is_admin():
        return redirect('/login')
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form.get('role', 'user')
        try:
            with db.get_db().cursor() as cursor:
                cursor.execute("INSERT INTO user (username, password, role) VALUES (%s, %s, %s)", (username, password, role))
                db.get_db().commit()
                flash("Pengguna berhasil ditambahkan!", "success")
        except Exception as e:
            flash(f'Terjadi kesalahan: {e}', 'danger')
        return redirect('/admin/admin-kelola-pengguna')
    return render_template('admin/formpengguna.html')

@app.route('/admin/form-edit-pengguna/<int:id>', methods=['GET', 'POST'])
def formeditpengguna(id):
    if not is_admin():
        return redirect('/login')
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        try:
            with db.get_db().cursor() as cursor:
                cursor.execute("UPDATE user SET username=%s, password=%s, role=%s WHERE id=%s", (username, password, role, id))
                db.get_db().commit()
                flash("Pengguna berhasil diupdate!", "success")
        except Exception as e:
            flash(f'Gagal menyimpan data: {e}', 'danger')
        return redirect('/admin/admin-kelola-pengguna')

    try:
        with db.get_db().cursor() as cursor:
            cursor.execute("SELECT * FROM user WHERE id=%s", (id,))
            data = cursor.fetchone()
        return render_template('admin/formeditpengguna.html', pengguna=data)
    except Exception as e:
        flash(f'Gagal mengambil data: {e}', 'danger')
        return redirect('/admin/admin-kelola-pengguna')

@app.route('/admin/hapus-pengguna/<int:id>', methods=['POST'])
def hapus_pengguna(id):
    if not is_admin():
        return redirect('/login')
    try:
        with db.get_db().cursor() as cursor:
            cursor.execute("DELETE FROM user WHERE id = %s", (id,))
            db.get_db().commit()
            flash("Pengguna berhasil dihapus.", "success")
    except Exception as e:
        flash(f"Gagal menghapus pengguna: {e}", "danger")
    return redirect('/admin/admin-kelola-pengguna')


# ----------------------------- User: Lihat Pesananku -----------------------------
@app.route('/pesananku')
def pesananku():
    if 'user' not in session:
        return redirect('/login')
    try:
        user_id = get_user_id_by_username(session['user'])
        with db.get_db().cursor() as cursor:
            cursor.execute("""
                SELECT p.id, b.nama, p.jumlah, p.harga_saat_pesan, 
                       (p.jumlah * p.harga_saat_pesan) AS total_harga, 
                       p.status
                FROM pesanan p
                JOIN barang b ON p.barang_id = b.id
                WHERE p.user_id = %s
                ORDER BY p.id DESC
            """, (user_id,))
            hasil = cursor.fetchall()
    except Exception as e:
        flash(f"Gagal mengambil data pesanan: {e}", "danger")
        hasil = []
    return render_template('user/pesananku.html', hasil=hasil)




@app.route('/hapus-pesanan/<int:id>', methods=['POST'])
def hapus_pesanan_user(id):
    if 'user' not in session:
        return redirect('/login')
    try:
        with db.get_db().cursor() as cursor:
            # Kembalikan stok barang sebelum hapus
            cursor.execute("SELECT barang_id, jumlah FROM pesanan WHERE id = %s", (id,))
            data = cursor.fetchone()
            if data:
                barang_id, jumlah = data
                cursor.execute("UPDATE barang SET stok = stok + %s WHERE id = %s", (jumlah, barang_id))
                cursor.execute("DELETE FROM pesanan WHERE id = %s", (id,))
                db.get_db().commit()
                flash("Pesanan berhasil dihapus.", "success")
    except Exception as e:
        flash(f"Gagal menghapus pesanan: {e}", "danger")
    return redirect('/pesananku')

@app.route('/tambah-jumlah/<int:id>', methods=['POST'])
def tambah_jumlah_pesanan(id):
    if 'user' not in session:
        return redirect('/login')
    try:
        conn = db.get_db()
        cursor = conn.cursor()

        # Ambil pesanan terkait
        cursor.execute("SELECT barang_id, jumlah FROM pesanan WHERE id = %s", (id,))
        pesanan = cursor.fetchone()
        if not pesanan:
            flash("Pesanan tidak ditemukan", "danger")
            return redirect('/pesananku')

        barang_id, jumlah_lama = pesanan

        # Periksa stok tersedia
        cursor.execute("SELECT stok FROM barang WHERE id = %s", (barang_id,))
        stok = cursor.fetchone()[0]
        if stok < 1:
            flash("Stok tidak mencukupi", "danger")
            return redirect('/pesananku')

        # Update pesanan & stok
        cursor.execute("UPDATE pesanan SET jumlah = jumlah + 1 WHERE id = %s", (id,))
        cursor.execute("UPDATE barang SET stok = stok - 1 WHERE id = %s", (barang_id,))
        conn.commit()

        flash("Jumlah pesanan berhasil ditambah.", "success")
    except Exception as e:
        flash(f"Gagal menambah jumlah pesanan: {e}", "danger")
    return redirect('/pesananku')




# ----------------------------- User: Pesan Barang -----------------------------


@app.route('/pesanan/kurang/<int:id>', methods=['POST'])
def kurang_jumlah_pesanan(id):
    if 'user' not in session:
        return redirect('/login')
    try:
        conn = db.get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT jumlah FROM pesanan WHERE id = %s", (id,))
        jumlah = cursor.fetchone()[0]
        if jumlah > 1:
            cursor.execute("UPDATE pesanan SET jumlah = jumlah - 1 WHERE id = %s", (id,))
            conn.commit()
            flash("Jumlah pesanan dikurangi.", "success")
        else:
            flash("Jumlah tidak boleh kurang dari 1.", "warning")
    except Exception as e:
        flash(f"Gagal mengurangi jumlah: {e}", "danger")
    return redirect('/pesananku')

@app.route('/pesanan/hapus/<int:id>', methods=['POST'])
def hapus_pesanan(id):
    if 'user' not in session:
        return redirect('/login')
    try:
        conn = db.get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM pesanan WHERE id = %s", (id,))
        conn.commit()
        flash("Pesanan berhasil dihapus.", "success")
    except Exception as e:
        flash(f"Gagal menghapus pesanan: {e}", "danger")
    return redirect('/pesananku')

@app.route('/pesan/<int:id>', methods=['GET', 'POST'])
def pesan(id):
    if 'user' not in session:
        return redirect('/login')
    try:
        conn = db.get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM barang WHERE id=%s", (id,))
        barang = cursor.fetchone()
        if not barang:
            flash("Barang tidak ditemukan", "danger")
            return redirect('/')
        if request.method == 'POST':
            jumlah = int(request.form['jumlah'])
            if jumlah > barang[3]:  # stok
                flash("Stok tidak mencukupi", "danger")
                return redirect(f"/pesan/{id}")
            user_id = get_user_id_by_username(session['user'])
            if not user_id:
                flash("User tidak valid", "danger")
                return redirect('/')
            harga_saat_pesan = barang[2]  # harga
            cursor.execute(
                "INSERT INTO pesanan (user_id, barang_id, jumlah, harga_saat_pesan) VALUES (%s, %s, %s, %s)",
                (user_id, id, jumlah, harga_saat_pesan)
            )
            cursor.execute("UPDATE barang SET stok = stok - %s WHERE id = %s", (jumlah, id))
            conn.commit()
            flash("Pesanan berhasil dibuat!", "success")
            return redirect('/')
        return render_template('user/formpesan.html', barang=barang)
    except Exception as e:
        flash(f"Terjadi kesalahan: {e}", "danger")
        return redirect('/')




@app.route('/admin/ubah-status/<int:id>', methods=['POST'])
def ubah_status_pesanan(id):
    if not is_admin():
        return redirect('/login')
    status_baru = request.form['status']
    try:
        with db.get_db().cursor() as cursor:
            if status_baru == "Selesai":
                cursor.execute("DELETE FROM pesanan WHERE id = %s", (id,))
                flash("Pesanan telah selesai dan dihapus dari database.", "success")
            else:
                cursor.execute("UPDATE pesanan SET status = %s WHERE id = %s", (status_baru, id))
                flash("Status pesanan berhasil diperbarui.", "success")
            db.get_db().commit()
    except Exception as e:
        flash(f"Gagal memperbarui status: {e}", "danger")
    return redirect('/admin/pesanan')

# ----------------------------- Jalankan Aplikasi -----------------------------
if __name__ == '__main__':
    app.run(debug=True)


# ----------------------------- Jalankan -----------------------------

if __name__ == '__main__':
    app.run(debug=True)
