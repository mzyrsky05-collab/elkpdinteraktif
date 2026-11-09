# -*- coding: utf-8 -*-
"""
E-LKPD INTERAKTIF: PELUANG, FREKUENSI RELATIF, DAN FREKUENSI HARAPAN
Matematika SMP Kelas VIII - Fase D
Jalankan di PythonAnywhere (Flask + SQLite).

Siswa  : buka alamat web  ->  isi nama & kelas  ->  kerjakan per halaman  ->  tersimpan otomatis
Guru   : buka alamat web/guru  ->  masukkan kata sandi  ->  lihat jawaban semua siswa per halaman + kunci jawaban
"""
import os
import re
import json
import sqlite3
import csv
import io
from datetime import datetime, timedelta, timezone
from functools import wraps

from flask import (Flask, request, jsonify, session, redirect, url_for,
                   render_template_string, Response, abort)

# ============ PENGATURAN (UBAH SESUAI KEBUTUHAN) ============
GURU_PASSWORD = os.environ.get("GURU_PASSWORD", "kel1pbam")   # <-- GANTI!
SECRET_KEY = os.environ.get("SECRET_KEY", "password salah")  # <-- GANTI!
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "elkpd.db")
ELKPD_CONTENT_VERSION = "2026-11-09-lkpd-word-peluang-v2"
WIB = timezone(timedelta(hours=7))

app = Flask(__name__)
app.secret_key = SECRET_KEY

# Kunci jawaban pilihan ganda (dinilai otomatis oleh server) - Kegiatan 5
KUNCI_PG = {"pg1": "C", "pg2": "C", "pg3": "C", "pg4": "C", "pg5": "B"}

# Label soal (dipakai di halaman guru, urutan = urutan di LKPD)
LABEL = {
    # --- Kegiatan 1: Mengenal Peluang ---
    "k1_a1": "K1 Ayo Amati 1 - Sisi yang mungkin muncul pada koin",
    "k1_a2": "K1 Ayo Amati 2 - Dapatkah sisi yang muncul dipastikan? Alasan",
    "k1_a3": "K1 Ayo Amati 3 - Peluang angka dan gambar sama besar? Alasan",
    "k1_c1": "K1 Coba Kerjakan 1 - Banyak seluruh hasil pada dadu",
    "k1_c2": "K1 Coba Kerjakan 2 - Jawaban peluang angka 4",
    "k1_c3": "K1 Coba Kerjakan 3 - Jawaban peluang angka genap",
    # --- Kegiatan 2: Frekuensi Relatif (dua percobaan terpisah) ---
    "koin20_a": "K2 Tabel 20 kali - Banyak kemunculan angka",
    "koin20_g": "K2 Tabel 20 kali - Banyak kemunculan gambar",
    "koin20_n": "K2 Tabel 20 kali - Jumlah lemparan",
    "koin40_a": "K2 Tabel 40 kali - Banyak kemunculan angka",
    "koin40_g": "K2 Tabel 40 kali - Banyak kemunculan gambar",
    "koin40_n": "K2 Tabel 40 kali - Jumlah lemparan",
    "k2_a1": "K2 Analisis 1 - Hasil kemunculan angka dan gambar pada setiap percobaan",
    "k2_a2": "K2 Analisis 2 - Frekuensi relatif angka dan gambar pada 20 dan 40 kali",
    "k2_a3": "K2 Analisis 3 - Perbandingan frekuensi relatif angka",
    "k2_a4": "K2 Analisis 4 - Frekuensi harapan angka untuk 20 dan 40 kali",
    "k2_a5": "K2 Analisis 5 - Perbandingan frekuensi relatif dengan peluang teoretis",
    "k2_a6": "K2 Analisis 6 - Perbandingan frekuensi relatif dan frekuensi harapan",
    # --- Kegiatan 3: Frekuensi Harapan (dua percobaan terpisah) ---
    **{"dadu30_%d" % i: "K3 Simulasi 30 kali - Kemunculan angka %d" % i for i in range(1,7)},
    "dadu30_n": "K3 Simulasi 30 kali - Total lemparan",
    **{"dadu60_%d" % i: "K3 Simulasi 60 kali - Kemunculan angka %d" % i for i in range(1,7)},
    "dadu60_n": "K3 Simulasi 60 kali - Total lemparan",
    "k3_sim_a": "K3 Analisis simulasi - Frekuensi relatif angka 6",
    "k3_sim_b": "K3 Analisis simulasi - Frekuensi harapan angka 6",
    "k3_sim_c": "K3 Analisis simulasi - Perbandingan hasil pengamatan dan harapan",
    "k3_1a": "K3 No.1a - Peluang sisi gambar",
    "k3_1b": "K3 No.1b - Jawaban frekuensi harapan gambar",
    "k3_2": "K3 No.2 - Jawaban",
    "k3_3a": "K3 No.3a - Jawaban peluang angka genap",
    "k3_3b": "K3 No.3b - Jawaban frekuensi harapan angka genap",
    # --- Kegiatan 4: Masalah sehari-hari ---
    "k4_1": "K4 No.1 - Banyak hasil yang mungkin",
    "k4_2": "K4 No.2 - Banyak hasil yang mendapat hadiah",
    "k4_3": "K4 No.3 - Jawaban peluang mendapat hadiah",
    "k4_4": "K4 No.4 - Jawaban frekuensi harapan hadiah",
    "k4_5": "K4 No.5 - Apakah pasti sama dengan frekuensi harapan? Penjelasan",
    # --- Kegiatan 5: Uji Pemahaman ---
    "pg1": "PG 1 (kunci C)", "pg2": "PG 2 (kunci C)", "pg3": "PG 3 (kunci C)",
    "pg4": "PG 4 (kunci C)", "pg5": "PG 5 (kunci B)",
    # --- Kesimpulan ---
    "kes1": "Kesimpulan 1 - Peluang digunakan untuk mengetahui ...",
    "kes2": "Kesimpulan 2 - Frekuensi relatif diperoleh dengan membandingkan ...",
    "kes3": "Kesimpulan 3 - Frekuensi harapan ditentukan dengan mengalikan ...",
    "kes4": "Kesimpulan 4 - Hasil percobaan dapat berbeda dari frekuensi harapan karena ...",
    # --- Refleksi ---
    "ref1": "Refleksi - Saya dapat menentukan peluang suatu kejadian sederhana",
    "ref2": "Refleksi - Saya dapat menghitung frekuensi relatif dari hasil percobaan",
    "ref3": "Refleksi - Saya dapat menentukan frekuensi harapan suatu kejadian",
    "ref4": "Refleksi - Saya dapat menyelesaikan masalah sederhana tentang peluang",
    "ref_paham": "Refleksi - Hal yang sudah saya pahami",
    "ref_belajar": "Refleksi - Hal yang masih ingin saya pelajari",
}

# Kunci / contoh jawaban untuk guru (ditampilkan di halaman detail siswa)
KUNCI_TEKS = {
    "k1_a1": "Angka dan gambar.",
    "k1_a2": "Tidak, karena hasil lemparan belum dapat dipastikan sebelum koin dilempar.",
    "k1_a3": "Ya, pada koin seimbang peluang keduanya sama besar (masing-masing 1/2).",
    "k1_c1": "Ruang sampel S = {1, 2, 3, 4, 5, 6}; banyak anggota ruang sampel = 6.",
    "k1_c2": "P(4) = 1/6.",
    "k1_c3": "Kejadian genap = {2, 4, 6}; P(genap) = 3/6 = 1/2.",
    "k2_a1": "Tuliskan banyak angka dan gambar pada percobaan 20 kali dan 40 kali. Jumlah setiap pasangan harus 20 dan 40.",
    "k2_a2": "Frekuensi relatif = banyak kemunculan / jumlah percobaan. Hitung untuk angka dan gambar pada kedua percobaan.",
    "k2_a3": "Nilainya belum tentu sama. Bandingkan berdasarkan hasil percobaan 20 kali dan 40 kali.",
    "k2_a4": "Frekuensi harapan angka: 1/2 × 20 = 10 kali dan 1/2 × 40 = 20 kali.",
    "k2_a5": "Bandingkan frekuensi relatif angka dengan peluang teoretis 1/2 atau 0,5. Hasil percobaan dapat berbeda.",
    "k2_a6": "Frekuensi relatif dan frekuensi harapan merupakan ukuran berbeda; hasil aktual tidak harus sama dengan frekuensi harapan.",
    "k3_sim_a": "Frekuensi relatif angka 6 = banyak kemunculan angka 6 / jumlah lemparan.",
    "k3_sim_b": "Untuk 30 lemparan: 1/6 × 30 = 5 kali; untuk 60 lemparan: 1/6 × 60 = 10 kali.",
    "k3_sim_c": "Hasil pengamatan tidak harus sama dengan frekuensi harapan karena frekuensi harapan merupakan perkiraan.",
    "k3_1a": "1/2",
    "k3_1b": "20 kali",
    "k3_2": "12 kali",
    "k3_3a": "1/2",
    "k3_3b": "60 kali",
    "k4_1": "6 hasil: 1, 2, 3, 4, 5, 6.",
    "k4_2": "2 hasil, yaitu 5 dan 6.",
    "k4_3": "2/6 = 1/3",
    "k4_4": "1/3 × 90 = 30 kali.",
    "k4_5": "Tidak harus sama. Frekuensi harapan adalah perkiraan berdasarkan peluang; hasil nyata dapat berbeda.",
    "kes1": "Ukuran kemungkinan terjadinya suatu kejadian.",
    "kes2": "Banyak kemunculan kejadian dengan jumlah seluruh percobaan.",
    "kes3": "Peluang kejadian dengan jumlah percobaan.",
    "kes4": "Hasil percobaan bersifat acak dan frekuensi harapan hanya merupakan perkiraan.",
}

# kolom yang dihitung untuk "kemajuan pengerjaan" (simulator tidak dihitung)
KUNCI_PROGRESS = [k for k in LABEL if not k.startswith(("dadu30_", "dadu60_", "koin20_", "koin40_", "dadu_", "koin_"))]

# Pengelompokan halaman pada tampilan guru (urutan = urutan halaman)
GROUPS = [
    ("k1", "Kegiatan 1", "Mengenal Peluang"),
    ("k2", "Kegiatan 2", "Frekuensi Relatif"),
    ("k3", "Kegiatan 3", "Frekuensi Harapan"),
    ("k4", "Kegiatan 4", "Masalah Sehari-hari"),
    ("pg", "Kegiatan 5", "Uji Pemahaman"),
    ("kes", "Kesimpulan", ""),
    ("ref", "Refleksi", ""),
    ("tambahan", "Tambahan", "Soal dan aktivitas dari guru"),
]


# ------------------------------ DATABASE ------------------------------
def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with db() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS jawaban (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nama TEXT NOT NULL,
                kelas TEXT NOT NULL,
                data TEXT NOT NULL DEFAULT '{}',
                skor_pg INTEGER NOT NULL DEFAULT 0,
                nilai_guru TEXT DEFAULT '',
                catatan_guru TEXT DEFAULT '',
                dibuat TEXT,
                diperbarui TEXT,
                UNIQUE(nama, kelas)
            )""")
        c.execute("""CREATE TABLE IF NOT EXISTS soal_tambahan (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pertanyaan TEXT NOT NULL,
            kunci TEXT DEFAULT '',
            jenis TEXT NOT NULL DEFAULT 'esai',
            opsi TEXT DEFAULT '',
            aktif INTEGER NOT NULL DEFAULT 1
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS elkpd_konten (
            id INTEGER PRIMARY KEY CHECK (id=1),
            main_html TEXT NOT NULL,
            diperbarui TEXT,
            versi TEXT DEFAULT ''
        )""")
        kolom_konten = [r["name"] for r in c.execute("PRAGMA table_info(elkpd_konten)").fetchall()]
        if "versi" not in kolom_konten:
            c.execute("ALTER TABLE elkpd_konten ADD COLUMN versi TEXT DEFAULT ''")
        # Migrasi aman untuk database lama
        cols = [r["name"] for r in c.execute("PRAGMA table_info(jawaban)").fetchall()]
        if "feedback_json" not in cols:
            c.execute("ALTER TABLE jawaban ADD COLUMN feedback_json TEXT DEFAULT '{}'")


init_db()


def sekarang():
    return datetime.now(WIB).strftime("%d-%m-%Y %H:%M:%S")


def norm(s):
    return " ".join((s or "").strip().split())


def hitung_pg(data):
    return sum(1 for k, v in KUNCI_PG.items() if str(data.get(k, "")).upper() == v)


def hitung_progress(data):
    isi = sum(1 for k in KUNCI_PROGRESS if str(data.get(k, "")).strip())
    return isi, len(KUNCI_PROGRESS)


# ------------------------------ API SISWA ------------------------------
@app.route("/api/muat", methods=["POST"])
def api_muat():
    p = request.get_json(silent=True) or {}
    nama, kelas = norm(p.get("nama")), norm(p.get("kelas"))
    if not nama or not kelas:
        return jsonify(ok=False, pesan="Nama dan kelas wajib diisi."), 400
    with db() as c:
        row = c.execute("SELECT data, skor_pg FROM jawaban WHERE nama=? AND kelas=?",
                        (nama, kelas)).fetchone()
        if row is None:
            c.execute("INSERT INTO jawaban(nama,kelas,data,dibuat,diperbarui) VALUES(?,?,?,?,?)",
                      (nama, kelas, "{}", sekarang(), sekarang()))
            return jsonify(ok=True, data={}, baru=True)
    return jsonify(ok=True, data=json.loads(row["data"]), baru=False)


@app.route("/api/simpan", methods=["POST"])
def api_simpan():
    p = request.get_json(silent=True) or {}
    nama, kelas = norm(p.get("nama")), norm(p.get("kelas"))
    data = p.get("data")
    if not nama or not kelas or not isinstance(data, dict):
        return jsonify(ok=False, pesan="Data tidak lengkap."), 400
    # simpan hanya kunci yang dikenal, batasi panjang
    bersih = {}
    for k in LABEL:
        if k in data:
            bersih[k] = str(data[k])[:2000]
    # Soal tambahan yang dibuat guru, hasil percobaan koin Kegiatan 1, dan riwayat lemparan simulasi
    for k, v in data.items():
        if (str(k).startswith("custom_q_") or str(k).startswith("activity_") or
                str(k).startswith("k1_koin_") or
                k in ("koin_riwayat", "dadu_riwayat")):
            bersih[str(k)[:80]] = str(v)[:200000]
    skor = hitung_pg(bersih)
    with db() as c:
        c.execute("""
            INSERT INTO jawaban(nama,kelas,data,skor_pg,dibuat,diperbarui)
            VALUES(?,?,?,?,?,?)
            ON CONFLICT(nama,kelas) DO UPDATE SET
                data=excluded.data, skor_pg=excluded.skor_pg, diperbarui=excluded.diperbarui
        """, (nama, kelas, json.dumps(bersih, ensure_ascii=False), skor, sekarang(), sekarang()))
    return jsonify(ok=True, waktu=sekarang(), skor_pg=skor)


# ------------------------------ HALAMAN GURU ------------------------------
def guru_wajib(f):
    @wraps(f)
    def w(*a, **k):
        if not session.get("guru"):
            return redirect(url_for("guru_login"))
        return f(*a, **k)
    return w


GURU_CSS = """
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
*{box-sizing:border-box}body{font-family:'Segoe UI',system-ui,sans-serif;background:#eef3f8;color:#14213d;margin:0;padding:20px 20px 100px}
.wrap{max-width:1100px;margin:auto}h1{margin:0 0 4px}a{color:#0f766e}
.card{background:#fff;border:1px solid #d5dee8;border-radius:12px;padding:18px;margin:14px 0}
table{width:100%;border-collapse:collapse;font-size:14px}th,td{padding:9px 10px;border-bottom:1px solid #e3e9f0;text-align:left;vertical-align:top}
th{background:#14213d;color:#fff;position:sticky;top:0}
.btn{background:#0f766e;color:#fff;border:0;padding:9px 16px;border-radius:8px;cursor:pointer;text-decoration:none;display:inline-block;font-size:14px;font-family:inherit}
.btn.alt{background:#fff;color:#14213d;border:1px solid #14213d}
.btn.gold{background:#e0a800;color:#3a2b00}
.btn[disabled]{opacity:.45;cursor:not-allowed}
input,textarea{padding:9px;border:1px solid #b9c6d4;border-radius:8px;font:inherit;width:100%}
.bar{background:#e3e9f0;border-radius:99px;height:9px;min-width:90px}.bar i{display:block;height:100%;background:#0f766e;border-radius:99px}
.jwb{background:#f5f8fb;border-left:4px solid #0f766e;padding:8px 12px;border-radius:6px;white-space:pre-wrap;margin-top:4px;display:block}
.kg{background:#fff8e1;border-left:4px solid #e0a800;padding:6px 12px;border-radius:6px;margin-top:6px;font-size:13px;color:#5c4400;display:block}
.kosong{color:#9aa7b5;font-style:italic}.ok{color:#0a7a3d;font-weight:700}.salah{color:#b3261e;font-weight:700}
.scroll{overflow-x:auto}

/* ----- Ringkasan angka (dashboard & ringkasan siswa) ----- */
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:14px 0}
.stat{background:#fff;border:1px solid #d5dee8;border-radius:12px;padding:14px 16px}
.stat b{display:block;font-size:28px;color:#0f766e;line-height:1.2}.stat span{font-size:13px;color:#5b6b7e}

/* ----- Tampilan per halaman (detail siswa) ----- */
.topnav{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:10px}.topnav .grow{flex:1}
.meta{color:#5b6b7e;margin:0 0 10px}
.tabs{display:flex;gap:6px;overflow-x:auto;padding:8px 2px;position:sticky;top:0;z-index:15;background:#eef3f8}
.tabs button{white-space:nowrap;border:1px solid #b9c6d4;background:#fff;color:#14213d;border-radius:99px;padding:8px 14px;font:inherit;font-size:14px;font-weight:600;cursor:pointer}
.tabs button.on{background:#14213d;color:#fff;border-color:#14213d}
.tabs small{opacity:.75;margin-left:6px;font-weight:400}
.prog{height:5px;background:#dbe4ee;border-radius:99px;overflow:hidden;margin:2px 0 10px}
.prog i{display:block;height:100%;width:0;background:#0f766e;transition:width .25s}
.opsi{display:flex;gap:18px;flex-wrap:wrap;align-items:center;margin:6px 0 10px;font-size:14px}.opsi input{width:auto}
.page{display:none}.page.aktif{display:block}
body.semua .page{display:block;margin-bottom:28px}
.page h2{margin:6px 0 12px}.page h2 small{font-weight:400;color:#5b6b7e;font-size:15px}
.item{background:#fff;border:1px solid #d5dee8;border-left:6px solid #0f766e;border-radius:12px;padding:14px 16px;margin:12px 0}
.item.kosong-item{border-left-color:#c5ced9;background:#fafbfd}
.item.salah-item{border-left-color:#b3261e}.item.benar-item{border-left-color:#0a7a3d}
.item .tag{font-size:13px;font-weight:700;color:#0f766e}
.item .soal{font-weight:700;margin:2px 0 8px}
.item .jwb{font-size:16px}
.badge{display:inline-block;padding:2px 10px;border-radius:99px;font-size:13px;font-weight:700;margin-left:8px}
.badge.ok{background:#d9f3e4;color:#0a7a3d}.badge.no{background:#fde2e0;color:#b3261e}
.item details{margin-top:10px}.item summary{cursor:pointer;color:#0f766e;font-weight:600;font-size:14px}
.item textarea{margin-top:6px}
body.sembunyi-kunci .kg{display:none}
.simbox{background:#fff;border:1px dashed #9fb2c6;border-radius:12px;padding:12px 16px;margin:12px 0}
.chips{display:flex;gap:8px;flex-wrap:wrap;margin:8px 0}.chip{background:#eef7f5;border-radius:8px;padding:6px 12px}
.riw{background:#f5f8fb;border-radius:8px;padding:8px 12px;max-height:130px;overflow:auto;font-family:monospace;font-size:13px;word-break:break-word}
.gbar{display:block;text-decoration:none;color:inherit;padding:10px 12px;border:1px solid #d5dee8;border-radius:10px;margin:8px 0;background:#fff}
.gbar:hover{border-color:#0f766e}
.pager{position:fixed;left:0;right:0;bottom:0;background:#fff;border-top:1px solid #d5dee8;padding:10px 16px;display:flex;gap:10px;align-items:center;justify-content:center;flex-wrap:wrap;z-index:30}
.pager .pinfo{font-weight:700;font-size:14px;min-width:120px;text-align:center}
@media print{.tabs,.pager,.topnav,.prog,.opsi{display:none}.page{display:block!important}}
</style>
"""

LOGIN_HTML = GURU_CSS + """
<div class="wrap" style="max-width:380px;margin-top:10vh"><div class="card">
<h2>Masuk Guru</h2><p>Lihat jawaban E-LKPD Peluang seluruh siswa.</p>
{% if salah %}<p class="salah">Kata sandi salah. Coba lagi.</p>{% endif %}
<form method="post"><input type="password" name="pw" placeholder="Kata sandi guru" autofocus required>
<p><button class="btn">Masuk</button></p></form></div></div>
"""

DASH_HTML = GURU_CSS + """
<div class="wrap">
<h1>Rekap Jawaban E-LKPD Peluang</h1>
<p>
<a class="btn" href="{{ url_for('guru_editor_elkpd') }}">Buka ELKPD yang ada untuk diedit</a>
<a class="btn" href="{{ url_for('guru_soal') }}">Kelola soal tambahan</a>
<a class="btn" href="{{ url_for('guru_csv') }}">Unduh Rekap (CSV/Excel)</a>
<a class="btn alt" href="{{ url_for('guru_keluar') }}">Keluar</a></p>

<div class="stats">
  <div class="stat"><b>{{ rows|length }}</b><span>Siswa yang sudah membuka E-LKPD</span></div>
  <div class="stat"><b>{{ selesai }}</b><span>Siswa yang menjawab semua soal</span></div>
  <div class="stat"><b>{{ rata_prog }}%</b><span>Rata-rata kemajuan pengerjaan</span></div>
  <div class="stat"><b>{{ rata_pg }}/5</b><span>Rata-rata skor pilihan ganda</span></div>
</div>

<details class="card"><summary><b>Petunjuk singkatan kegiatan (klik untuk membuka)</b></summary>
<ul><li><b>K1</b> = Kegiatan 1: Mengenal Peluang</li><li><b>K2</b> = Kegiatan 2: Frekuensi Relatif</li>
<li><b>K3</b> = Kegiatan 3: Frekuensi Harapan</li><li><b>K4</b> = Kegiatan 4: Masalah Sehari-hari</li>
<li><b>PG</b> = Pilihan Ganda</li>
<li><b>dik</b> = diketahui, <b>dit</b> = ditanya</li></ul>
<p>Contoh: <b>K2 Analisis 4 - Frekuensi harapan angka</b> adalah pertanyaan nomor 4 pada Kegiatan 2.</p></details>

<form method="get" style="max-width:320px"><input name="kelas" value="{{ kelas }}" placeholder="Filter kelas, mis. 8A (Enter)"></form>
<div class="card scroll"><table>
<tr><th>No</th><th>Nama</th><th>Kelas</th><th>Kemajuan</th><th>Skor PG</th><th>Nilai guru</th><th>Terakhir simpan</th><th></th></tr>
{% for r in rows %}
<tr><td>{{ loop.index }}</td><td>{{ r.nama }}</td><td>{{ r.kelas }}</td>
<td><div class="bar"><i style="width:{{ r.persen }}%"></i></div>{{ r.isi }}/{{ r.total }} soal</td>
<td>{{ r.skor_pg }}/5</td><td>{{ r.nilai_guru or '-' }}</td><td>{{ r.diperbarui }}</td>
<td><a class="btn" href="{{ url_for('guru_detail', sid=r.id) }}">Lihat jawaban</a></td></tr>
{% else %}<tr><td colspan="8" class="kosong">Belum ada siswa yang mengerjakan.</td></tr>{% endfor %}
</table></div></div>
"""

DETAIL_HTML = GURU_CSS + """
<div class="wrap">
<div class="topnav">
  <a class="btn alt" href="{{ url_for('guru_dashboard') }}">&larr; Rekap</a><span class="grow"></span>
  {% if prev_id %}<a class="btn alt" href="{{ url_for('guru_detail', sid=prev_id) }}">&larr; Siswa sebelumnya</a>{% endif %}
  {% if next_id %}<a class="btn alt" href="{{ url_for('guru_detail', sid=next_id) }}">Siswa berikutnya &rarr;</a>{% endif %}
</div>
<h1>{{ r.nama }} <small>({{ r.kelas }})</small></h1>
<p class="meta">Terakhir disimpan: {{ r.diperbarui }}</p>

<div class="tabs" id="tabs"></div>
<div class="prog"><i id="progI"></i></div>
<div class="opsi">
  <label><input type="checkbox" id="cbKunci" checked> Tampilkan kunci jawaban</label>
  <label><input type="checkbox" id="cbSemua"> Tampilkan semua halaman sekaligus</label>
</div>

<div class="page aktif" data-judul="Ringkasan" data-info="">
  <h2>Ringkasan</h2>
  <div class="stats">
    <div class="stat"><b>{{ r.skor_pg }}/5</b><span>Skor pilihan ganda (otomatis)</span></div>
    <div class="stat"><b>{{ persen }}%</b><span>Soal yang sudah diisi ({{ isi }}/{{ total }})</span></div>
    <div class="stat"><b>{{ r.nilai_guru or '-' }}</b><span>Nilai akhir dari guru</span></div>
  </div>
  <div class="card"><h3 style="margin-top:0">Kemajuan per kegiatan <small>(klik untuk membuka halaman)</small></h3>
    {% for g in groups %}
    <a class="gbar" href="#p{{ g.idx }}"><b>{{ g.judul }}</b> {{ g.sub }}
      <span style="float:right">{{ g.isi }}/{{ g.total }}</span>
      <div class="bar" style="margin-top:6px"><i style="width:{{ g.persen }}%"></i></div></a>
    {% endfor %}
  </div>
  <div class="card"><h3 style="margin-top:0">Penilaian Guru</h3>
    <form method="post" action="{{ url_for('guru_nilai', sid=r.id) }}">
      <p>Nilai akhir<input name="nilai" value="{{ r.nilai_guru or '' }}" style="max-width:160px"></p>
      <p>Catatan / umpan balik umum<textarea name="catatan" rows="3">{{ r.catatan_guru or '' }}</textarea></p>
      <button class="btn">Simpan penilaian</button>
    </form>
  </div>
</div>

<form id="fbForm" method="post" action="{{ url_for('guru_feedback', sid=r.id) }}">
<input type="hidden" name="hal" id="halIn" value="0">
{% for g in groups %}
<div class="page" data-judul="{{ g.judul }}" data-info="{{ g.isi }}/{{ g.total }}">
  <h2>{{ g.judul }} <small>{{ g.sub }}</small></h2>
  {% if g.sim %}
  <div class="simbox"><b>{{ g.sim.judul }}</b>
    <div class="chips">{% for nm, val in g.sim.chips %}<span class="chip">{{ nm }}: <b>{{ val }}</b></span>{% endfor %}</div>
    {% if g.sim.riwayat %}<div class="riw">{{ g.sim.riwayat }}</div>{% else %}<span class="kosong">Belum ada riwayat percobaan</span>{% endif %}
  </div>
  {% endif %}
  {% for it in g.butir %}
  <div class="item {{ it.kelas }}">
    <div class="tag">{{ it.head }}</div>
    {% if it.desk %}<div class="soal">{{ it.desk }}</div>{% endif %}
    <div>
      {% if it.v %}<span class="jwb">{{ it.v }}</span>{% else %}<span class="kosong">Belum diisi</span>{% endif %}
      {% if it.status == 'benar' %}<span class="badge ok">&#10003; Benar</span>{% elif it.status == 'salah' %}<span class="badge no">&#10007; Salah</span>{% endif %}
    </div>
    {% if it.kt %}<span class="kg">Kunci / contoh: {{ it.kt }}</span>{% endif %}
    <details {% if it.fb %}open{% endif %}><summary>&#9998; Umpan balik untuk soal ini</summary>
      <textarea name="fb__{{ it.k }}" rows="2" placeholder="Contoh: Jawaban sudah benar, tetapi tuliskan satuannya.">{{ it.fb }}</textarea>
    </details>
  </div>
  {% endfor %}
</div>
{% endfor %}
</form>
</div>

<div class="pager">
  <button type="button" class="btn alt" id="pPrev">&larr; Sebelumnya</button>
  <span class="pinfo" id="pInfo"></span>
  <button type="button" class="btn" id="pNext">Berikutnya &rarr;</button>
  <button type="submit" form="fbForm" class="btn gold">Simpan umpan balik</button>
</div>

<script>
(function(){
  var pages=[].slice.call(document.querySelectorAll('.page')), idx=0, tabs=document.getElementById('tabs');
  pages.forEach(function(p,i){
    var b=document.createElement('button'); b.type='button';
    var info=p.getAttribute('data-info');
    b.textContent=p.getAttribute('data-judul');
    if(info){var s=document.createElement('small'); s.textContent=info; b.appendChild(s);}
    b.onclick=function(){go(i,true);};
    tabs.appendChild(b);
  });
  function go(i,dariKlik){
    i=Math.max(0,Math.min(pages.length-1,i)); idx=i;
    pages.forEach(function(p,j){p.classList.toggle('aktif',j===i);});
    [].forEach.call(tabs.children,function(b,j){b.classList.toggle('on',j===i);});
    if(tabs.children[i].scrollIntoView) tabs.children[i].scrollIntoView({inline:'center',block:'nearest'});
    document.getElementById('pInfo').textContent='Halaman '+(i+1)+' dari '+pages.length;
    document.getElementById('progI').style.width=((i+1)*100/pages.length)+'%';
    document.getElementById('pPrev').disabled=(i===0);
    document.getElementById('pNext').disabled=(i===pages.length-1);
    document.getElementById('halIn').value=i;
    if(dariKlik){
      if(location.hash!=='#p'+i) location.hash='p'+i;
      window.scrollTo(0,0);
    }
  }
  function dariHash(){return parseInt(location.hash.replace('#p',''),10);}
  window.addEventListener('hashchange',function(){var p=dariHash(); if(!isNaN(p)&&p!==idx) go(p,false);});
  document.getElementById('pPrev').onclick=function(){go(idx-1,true);};
  document.getElementById('pNext').onclick=function(){go(idx+1,true);};
  document.getElementById('cbKunci').onchange=function(){document.body.classList.toggle('sembunyi-kunci',!this.checked);};
  document.getElementById('cbSemua').onchange=function(){document.body.classList.toggle('semua',this.checked);};
  var h=dariHash(); go(isNaN(h)?0:h,false);
})();
</script>
"""


@app.route("/guru", methods=["GET"])
@guru_wajib
def guru_dashboard():
    kelas = norm(request.args.get("kelas"))
    with db() as c:
        if kelas:
            res = c.execute("SELECT * FROM jawaban WHERE kelas LIKE ? ORDER BY kelas, nama",
                            (kelas,)).fetchall()
        else:
            res = c.execute("SELECT * FROM jawaban ORDER BY kelas, nama").fetchall()
    rows = []
    for r in res:
        d = dict(r)
        isi, total = hitung_progress(json.loads(r["data"]))
        d.update(isi=isi, total=total, persen=int(isi * 100 / total) if total else 0)
        rows.append(d)
    n = len(rows)
    rata_pg = round(sum(r["skor_pg"] for r in rows) / n, 1) if n else 0
    rata_prog = int(sum(r["persen"] for r in rows) / n) if n else 0
    selesai = sum(1 for r in rows if r["persen"] >= 100)
    return render_template_string(DASH_HTML, rows=rows, kelas=kelas,
                                  rata_pg=rata_pg, rata_prog=rata_prog, selesai=selesai)


@app.route("/guru/login", methods=["GET", "POST"])
def guru_login():
    salah = False
    if request.method == "POST":
        if request.form.get("pw") == GURU_PASSWORD:
            session["guru"] = True
            return redirect(url_for("guru_dashboard"))
        salah = True
    return render_template_string(LOGIN_HTML, salah=salah)


@app.route("/guru/keluar")
def guru_keluar():
    session.clear()
    return redirect(url_for("guru_login"))


def grup_dari_kunci(k):
    if k.startswith("k1_"):
        return "k1"
    if k.startswith(("koin20_", "koin40_", "koin_", "k2_")):
        return "k2"
    if k.startswith(("dadu30_", "dadu60_", "dadu_", "k3_")):
        return "k3"
    if k.startswith("k4_"):
        return "k4"
    if k.startswith("pg"):
        return "pg"
    if k.startswith("kes"):
        return "kes"
    if k.startswith("ref"):
        return "ref"
    return "tambahan"


def ringkas_riwayat(teks):
    return (teks or "").replace("Angka", "A").replace("Gambar", "G")


def susun_detail(r):
    """Kelompokkan jawaban siswa per kegiatan agar bisa ditampilkan per halaman."""
    data = json.loads(r["data"] or "{}")
    feedback = json.loads((r["feedback_json"] if "feedback_json" in r.keys() else "{}") or "{}")
    grup = {kode: {"kode": kode, "judul": judul, "sub": sub, "butir": [], "isi": 0, "total": 0, "sim": None}
            for kode, judul, sub in GROUPS}

    def tambah(kode, key, head, desk, v, kt, status=""):
        g = grup[kode]
        g["total"] += 1
        if v:
            g["isi"] += 1
        if status == "benar":
            kelas = "benar-item"
        elif status == "salah":
            kelas = "salah-item"
        else:
            kelas = "" if v else "kosong-item"
        g["butir"].append({"k": key, "head": head, "desk": desk, "v": v, "kt": kt,
                           "status": status, "kelas": kelas, "fb": feedback.get(key, "")})

    for k, lab in LABEL.items():
        if k.startswith(("koin20_", "koin40_", "dadu30_", "dadu60_", "koin_", "dadu_")):
            continue  # hasil simulasi ditampilkan sebagai kotak ringkasan
        v = str(data.get(k, "")).strip()
        head, _, desk = lab.partition(" - ")
        status, kt = "", KUNCI_TEKS.get(k, "")
        if k in KUNCI_PG:
            head = head.split(" (")[0]
            kt = "Jawaban benar: " + KUNCI_PG[k]
            if v:
                status = "benar" if v.upper() == KUNCI_PG[k] else "salah"
        tambah(grup_dari_kunci(k), k, head, desk, v, kt, status)

    grup["k1"]["sim"] = {
        "judul": "Percobaan lempar koin (Kegiatan 1)",
        "chips": [("Angka", data.get("k1_koin_angka", "0")), ("Gambar", data.get("k1_koin_gambar", "0"))],
        "riwayat": ringkas_riwayat(data.get("k1_koin_riwayat", "")),
    }
    grup["k2"]["sim"] = {
        "judul": "Hasil dua percobaan pelemparan koin",
        "chips": [
            ("A 20x", data.get("koin20_a", "0")), ("G 20x", data.get("koin20_g", "0")),
            ("Total 20x", data.get("koin20_n", "0")),
            ("A 40x", data.get("koin40_a", "0")), ("G 40x", data.get("koin40_g", "0")),
            ("Total 40x", data.get("koin40_n", "0"))
        ],
        "riwayat": "",
    }
    grup["k3"]["sim"] = {
        "judul": "Hasil dua percobaan pelemparan dadu",
        "chips": [("30x mata %d" % i, data.get("dadu30_%d" % i, "0")) for i in range(1, 7)]
                 + [("Total 30x", data.get("dadu30_n", "0"))]
                 + [("60x mata %d" % i, data.get("dadu60_%d" % i, "0")) for i in range(1, 7)]
                 + [("Total 60x", data.get("dadu60_n", "0"))],
        "riwayat": "",
    }

    # Soal tambahan dan aktivitas tambahan dari guru
    with db() as c:
        extra = c.execute("SELECT id, pertanyaan, kunci, jenis FROM soal_tambahan WHERE aktif=1 ORDER BY id").fetchall()
    for q in extra:
        key = "custom_q_" + str(q["id"])
        v = str(data.get(key, "")).strip()
        kunci = (q["kunci"] or "").strip()
        status = ""
        if q["jenis"] == "pg" and v and len(kunci) == 1:
            status = "benar" if v.upper() == kunci.upper() else "salah"
        tambah("tambahan", key, "Soal tambahan", q["pertanyaan"], v, kunci, status)
    for key in sorted(k for k in data if str(k).startswith("activity_")):
        tambah("tambahan", key, "Aktivitas tambahan",
               "Jawaban pada aktivitas yang ditambahkan guru di E-LKPD",
               str(data.get(key, "")).strip(), "")

    hasil = []
    for kode, _, _ in GROUPS:
        g = grup[kode]
        if g["total"] == 0 and not g["sim"]:
            continue
        g["persen"] = int(g["isi"] * 100 / g["total"]) if g["total"] else 0
        g["idx"] = len(hasil) + 1   # halaman 0 = Ringkasan
        hasil.append(g)
    return data, hasil


@app.route("/guru/siswa/<int:sid>")
@guru_wajib
def guru_detail(sid):
    with db() as c:
        r = c.execute("SELECT * FROM jawaban WHERE id=?", (sid,)).fetchone()
        ids = [x["id"] for x in c.execute("SELECT id FROM jawaban ORDER BY kelas, nama").fetchall()]
    if r is None:
        abort(404)
    data, groups = susun_detail(r)
    i = ids.index(sid) if sid in ids else 0
    prev_id = ids[i - 1] if i > 0 else None
    next_id = ids[i + 1] if i < len(ids) - 1 else None
    isi, total = hitung_progress(data)
    return render_template_string(DETAIL_HTML, r=r, groups=groups, prev_id=prev_id, next_id=next_id,
                                  isi=isi, total=total, persen=int(isi * 100 / total) if total else 0)


@app.route("/guru/nilai/<int:sid>", methods=["POST"])
@guru_wajib
def guru_nilai(sid):
    with db() as c:
        c.execute("UPDATE jawaban SET nilai_guru=?, catatan_guru=? WHERE id=?",
                  (request.form.get("nilai", "")[:20], request.form.get("catatan", "")[:1000], sid))
    return redirect(url_for("guru_detail", sid=sid))


@app.route("/guru/soal", methods=["GET", "POST"])
@guru_wajib
def guru_soal():
    pesan = ""
    if request.method == "POST":
        aksi = request.form.get("aksi", "tambah")
        if aksi == "ubah":
            qid = request.form.get("id", type=int)
            teks_edit = norm(request.form.get("pertanyaan"))
            kunci_edit = norm(request.form.get("kunci"))
            jenis_edit = request.form.get("jenis", "esai")
            opsi_edit = request.form.get("opsi", "").strip()
            if qid and teks_edit:
                with db() as c:
                    c.execute("UPDATE soal_tambahan SET pertanyaan=?,kunci=?,jenis=?,opsi=? WHERE id=?",
                              (teks_edit[:1000], kunci_edit[:500], jenis_edit if jenis_edit in ("esai","pg") else "esai", opsi_edit[:1000], qid))
                pesan = "Soal berhasil diperbarui."
            else:
                pesan = "Pertanyaan tidak boleh kosong."
        elif aksi == "hapus":
            qid = request.form.get("id", type=int)
            with db() as c:
                c.execute("DELETE FROM soal_tambahan WHERE id=?", (qid,))
            pesan = "Soal tambahan dihapus."
        else:
            teks = norm(request.form.get("pertanyaan"))
            kunci = norm(request.form.get("kunci"))
            jenis = request.form.get("jenis", "esai")
            opsi = request.form.get("opsi", "").strip()
            if teks:
                with db() as c:
                    c.execute("INSERT INTO soal_tambahan(pertanyaan,kunci,jenis,opsi) VALUES(?,?,?,?)",
                              (teks[:1000], kunci[:500], jenis if jenis in ("esai","pg") else "esai", opsi[:1000]))
                pesan = "Soal berhasil ditambahkan. Soal akan tampil di halaman siswa."
            else:
                pesan = "Teks soal wajib diisi."
    with db() as c:
        soal = c.execute("SELECT * FROM soal_tambahan ORDER BY id DESC").fetchall()
    html = GURU_CSS + """
    <div class="wrap"><p><a href="{{ url_for('guru_dashboard') }}">← Kembali ke rekap</a></p>
    <h1>Kelola Soal E-LKPD</h1><p>Tambahkan soal tanpa mengubah kode program. Soal baru muncul sebagai halaman terakhir pada tampilan siswa.</p>
    {% if pesan %}<div class="card">{{ pesan }}</div>{% endif %}
    <div class="card"><form method="post"><label>Pertanyaan<textarea name="pertanyaan" rows="3" required></textarea></label>
    <p><label>Jenis jawaban<select name="jenis"><option value="esai">Jawaban uraian</option><option value="pg">Pilihan ganda</option></select></label></p>
    <p><label>Pilihan jawaban (khusus PG, pisahkan dengan tanda | )<input name="opsi" placeholder="A. ... | B. ... | C. ... | D. ..."></label></p>
    <p><label>Kunci jawaban (opsional; untuk PG tulis A/B/C/D)<input name="kunci"></label></p>
    <button class="btn">Tambah soal</button></form></div>
    <div class="card"><h3>Soal tambahan saat ini</h3>{% for q in soal %}
    <form method="post" class="card"><input type="hidden" name="aksi" value="ubah"><input type="hidden" name="id" value="{{ q.id }}">
    <label>Soal {{ loop.index }}<textarea name="pertanyaan" rows="3" required>{{ q.pertanyaan }}</textarea></label>
    <p><label>Jenis jawaban<select name="jenis"><option value="esai" {% if q.jenis=='esai' %}selected{% endif %}>Uraian</option><option value="pg" {% if q.jenis=='pg' %}selected{% endif %}>Pilihan ganda</option></select></label></p>
    <p><label>Pilihan jawaban (pisahkan dengan |)<input name="opsi" value="{{ q.opsi or '' }}"></label></p>
    <p><label>Kunci jawaban<input name="kunci" value="{{ q.kunci or '' }}"></label></p>
    <button class="btn">Simpan perubahan soal</button></form>
    <form method="post" onsubmit="return confirm('Hapus soal ini?')"><input type="hidden" name="aksi" value="hapus"><input type="hidden" name="id" value="{{ q.id }}"><button class="btn" style="background:#b3261e">Hapus soal</button></form>
    {% else %}<p>Belum ada soal tambahan.</p>{% endfor %}</div></div>
    """
    return render_template_string(html, soal=soal, pesan=pesan)

@app.route("/api/soal-tambahan")
def api_soal_tambahan():
    with db() as c:
        rows = c.execute("SELECT id,pertanyaan,jenis,opsi FROM soal_tambahan WHERE aktif=1 ORDER BY id").fetchall()
    return jsonify(soal=[dict(r) for r in rows])

@app.route("/guru/feedback/<int:sid>", methods=["POST"])
@guru_wajib
def guru_feedback(sid):
    obj = {}
    for k, v in request.form.items():
        if k.startswith("fb__"):
            obj[k[4:]] = v
    aman = {str(k)[:80]: str(v)[:1000] for k,v in obj.items()}
    with db() as c:
        c.execute("UPDATE jawaban SET feedback_json=? WHERE id=?", (json.dumps(aman, ensure_ascii=False), sid))
    hal = request.form.get("hal", "0")
    hal = hal if hal.isdigit() else "0"
    # kembali ke halaman yang sedang dibuka guru
    return redirect(url_for("guru_detail", sid=sid) + "#p" + hal)

@app.route("/guru/rekap.csv")
@guru_wajib
def guru_csv():
    with db() as c:
        res = c.execute("SELECT * FROM jawaban ORDER BY kelas, nama").fetchall()
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["Nama", "Kelas", "Skor PG (0-5)", "Nilai Guru", "Catatan Guru", "Terakhir Simpan"]
               + list(LABEL.values()))
    for r in res:
        d = json.loads(r["data"])
        w.writerow([r["nama"], r["kelas"], r["skor_pg"], r["nilai_guru"], r["catatan_guru"],
                    r["diperbarui"]] + [d.get(k, "") for k in LABEL])
    return Response("\ufeff" + out.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=rekap_elkpd_peluang.csv"})


# ------------------------------ API UMPAN BALIK UNTUK SISWA ------------------------------
@app.route("/api/umpan-balik", methods=["POST"])
def api_umpan_balik():
    p = request.get_json(silent=True) or {}
    nama, kelas = norm(p.get("nama")), norm(p.get("kelas"))
    if not nama or not kelas:
        return jsonify(ok=False, pesan="Identitas siswa tidak lengkap."), 400

    with db() as c:
        row = c.execute(
            "SELECT nilai_guru, catatan_guru, feedback_json FROM jawaban WHERE nama=? AND kelas=?",
            (nama, kelas)
        ).fetchone()

    if row is None:
        return jsonify(ok=False, pesan="Data siswa tidak ditemukan."), 404

    try:
        feedback = json.loads(row["feedback_json"] or "{}")
    except (TypeError, ValueError):
        feedback = {}

    rincian = []
    for key, komentar in feedback.items():
        komentar = str(komentar or "").strip()
        if komentar:
            rincian.append({
                "soal": LABEL.get(key, key),
                "komentar": komentar
            })

    return jsonify(
        ok=True,
        nilai=row["nilai_guru"] or "",
        catatan=row["catatan_guru"] or "",
        rincian=rincian,
        ada=bool((row["nilai_guru"] or "").strip() or
                 (row["catatan_guru"] or "").strip() or rincian)
    )


# ------------------------------ HALAMAN SISWA ------------------------------
def normalisasi_konten_lama(main_html):
    """Bersihkan label/kolom Perhitungan lama dan perbarui Tujuan Pembelajaran ABCD.
    Pertanyaan serta kolom jawaban utama tetap dipertahankan.
    """
    main_html = str(main_html or "")

    # Hapus hanya kolom jawaban tambahan yang khusus dipakai untuk perhitungan.
    main_html = re.sub(
        r'<input\b(?=[^>]*(?:id|data-key)="[^"]*_hit")[^>]*>',
        '',
        main_html,
        flags=re.I
    )
    # Hapus label kecil "Perhitungan" tanpa menghapus pertanyaan utama.
    main_html = re.sub(
        r'<span\b[^>]*>\s*Perhitungan(?:\s+[^<]*)?\s*</span>\s*',
        '',
        main_html,
        flags=re.I
    )
    main_html = re.sub(r'for="([^"]+)_hit"', r'for="\1"', main_html, flags=re.I)

    # Bersihkan sisa kata/label Perhitungan dari konten lama.
    main_html = re.sub(r'\s*[-–—:]\s*Perhitungan\b', '', main_html, flags=re.I)
    main_html = re.sub(r'\bPerhitungan\b', '', main_html, flags=re.I)

    # Perbarui instruksi lama agar tidak merujuk pada kolom terpisah.
    main_html = main_html.replace(
        'sertakan langkah penyelesaian dan hasil akhirnya.',
        'sertakan langkah penyelesaian dan hasil akhirnya.'
    )

    tp_baru = """<ul>
    <li>Peserta didik kelas VIII mampu menjelaskan pengertian peluang dan menentukan peluang suatu kejadian sederhana melalui pengamatan terhadap koin dan dadu serta percobaan sederhana dengan benar sekurang-kurangnya 3 dari 4 soal.</li>
    <li>Peserta didik kelas VIII mampu menentukan frekuensi relatif suatu kejadian dalam bentuk pecahan, desimal, atau persen setelah melakukan simulasi pelemparan koin dan mencatat hasil percobaan dengan benar sekurang-kurangnya 2 dari 3 soal.</li>
    <li>Peserta didik kelas VIII mampu menentukan frekuensi harapan suatu kejadian menggunakan peluang dan jumlah percobaan setelah mengamati contoh dan menyelesaikan masalah kontekstual tentang pelemparan koin atau dadu dengan benar sekurang-kurangnya 2 dari 3 soal.</li>
  </ul>
  <p class="info">Unsur ABCD: A = peserta didik kelas VIII; B = perilaku/kemampuan yang diharapkan; C = kondisi saat pembelajaran; D = tingkat pencapaian yang dapat diukur.</p>"""
    pola_tp = r'(<h2[^>]*>[^<]*Tujuan Pembelajaran[^<]*</h2>\s*)<ul>.*?</ul>(?:\s*<p class="info">Unsur ABCD:.*?</p>)?'
    main_html = re.sub(pola_tp, lambda m: m.group(1) + tp_baru,
                       main_html, count=1, flags=re.I | re.S)
    return main_html


def konten_elkpd_tersimpan():
    awal = SISWA_HTML.find("<main>")
    akhir = SISWA_HTML.find("</main>", awal)
    konten_bawaan = SISWA_HTML[awal + len("<main>"):akhir] if awal >= 0 and akhir >= 0 else ""
    with db() as c:
        row = c.execute("SELECT main_html, versi FROM elkpd_konten WHERE id=1").fetchone()
        # Saat versi kode berubah mengikuti revisi Word, konten lama diganti
        # satu kali dengan isi dasar terbaru agar halaman siswa tidak tetap
        # menampilkan materi lama yang tersimpan di database.
        if row and row["versi"] != ELKPD_CONTENT_VERSION:
            c.execute("UPDATE elkpd_konten SET main_html=?, versi=?, diperbarui=? WHERE id=1",
                      (konten_bawaan, ELKPD_CONTENT_VERSION, sekarang()))
            return konten_bawaan
        if row and row["main_html"]:
            return row["main_html"]
    return konten_bawaan


def render_elkpd(main_html=None):
    halaman = SISWA_HTML
    if main_html is None:
        main_html = konten_elkpd_tersimpan()

    # Pastikan panel umpan balik tetap muncul pada konten lama yang pernah
    # disimpan guru sebelum fitur ini ditambahkan.
    if 'id="hasilGuru"' not in main_html:
        main_html += """
        <section id="hasilGuru">
          <h2>J. Hasil Penilaian dan Umpan Balik Guru</h2>
          <p class="info">Bagian ini menampilkan nilai, catatan umum, dan komentar guru terhadap jawabanmu.</p>
          <div id="hasilGuruIsi"><p class="info">Masuk terlebih dahulu untuk memeriksa umpan balik dari guru.</p></div>
          <button type="button" class="btn ghost" id="btnMuatFeedback">Perbarui umpan balik</button>
        </section>
        """

    awal = halaman.find("<main>")
    akhir = halaman.find("</main>", awal)
    if awal >= 0 and akhir >= 0:
        halaman = halaman[:awal + len("<main>")] + main_html + halaman[akhir:]
    return halaman


@app.route("/")
def siswa():
    response = Response(render_elkpd(), mimetype="text/html")
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.route("/guru/elkpd")
@guru_wajib
def guru_editor_elkpd():
    halaman = render_elkpd()
    toolbar = r'''<div id="editorBar" style="position:sticky;top:0;z-index:9999;background:#14213d;color:white;padding:12px 16px;box-shadow:0 3px 12px #0002;font-family:Arial,sans-serif">
      <div style="max-width:1000px;margin:auto;display:flex;gap:8px;align-items:center;flex-wrap:wrap">
        <b style="margin-right:8px">Mode Edit E-LKPD</b>
        <button type="button" id="editToggle" style="padding:8px 12px;border:0;border-radius:7px;cursor:pointer">Mulai ubah teks</button>
        <button type="button" id="addActivity" style="padding:8px 12px;border:0;border-radius:7px;cursor:pointer">+ Tambah aktivitas di bawah</button>
        <button type="button" id="saveELKPD" style="padding:8px 12px;background:#0f766e;color:white;border:0;border-radius:7px;cursor:pointer;font-weight:bold">Simpan perubahan</button>
        <a href="/guru" style="color:white;margin-left:auto">Kembali ke rekap guru</a>
        <span id="editorStatus" style="font-size:13px;width:100%">Buka ELKPD yang sudah ada. Aktifkan edit untuk mengubah soal, instruksi, penjelasan, rumus, dan contoh Ayo Pahami; tambahkan aktivitas bila perlu. Setiap bagian (section) akan menjadi satu halaman pada tampilan siswa.</span>
      </div></div>'''
    editor_script = r'''<script>
(function(){
 var aktif=false;
 document.getElementById('gate').style.display='none';
 document.getElementById('bar').style.display='none';
 function status(t){document.getElementById('editorStatus').textContent=t;}

 // Bungkus semua teks yang terlihat agar seluruh tulisan dalam isi E-LKPD dapat diedit.
 // Kontrol jawaban dan elemen program tidak diubah.
 function siapkanSemuaTeks(){
   var main=document.querySelector('main');
   var walker=document.createTreeWalker(main,NodeFilter.SHOW_TEXT,{
     acceptNode:function(node){
       var p=node.parentElement;
       if(!p || !node.nodeValue.trim()) return NodeFilter.FILTER_REJECT;
       if(p.closest('script,style,noscript,textarea,input,select,option,button,svg,[contenteditable="true"],[data-guru-editable]')) return NodeFilter.FILTER_REJECT;
       return NodeFilter.FILTER_ACCEPT;
     }
   });
   var nodes=[], n;
   while((n=walker.nextNode())) nodes.push(n);
   nodes.forEach(function(node){
     var span=document.createElement('span');
     span.setAttribute('data-guru-editable','1');
     node.parentNode.insertBefore(span,node);
     span.appendChild(node);
   });
 }
 function aturModeEdit(){
   document.querySelectorAll('main [data-guru-editable="1"]').forEach(function(el){
     el.contentEditable=aktif?'true':'false';
     el.style.outline=aktif?'1px dashed #0f766e':'';
     el.style.cursor=aktif?'text':'';
     el.style.backgroundColor=aktif?'#fffde7':'';
     el.style.borderRadius=aktif?'3px':'';
   });
 }
 siapkanSemuaTeks();
 aturModeEdit();

 document.getElementById('editToggle').onclick=function(){
   aktif=!aktif;
   aturModeEdit();
   this.textContent=aktif?'Selesai mengubah teks':'Mulai ubah teks';
   status(aktif?'Semua tulisan pada isi E-LKPD dapat diedit, termasuk judul, petunjuk, penjelasan, tabel, pilihan jawaban, rumus, dan contoh.':'Mode edit dimatikan. Tekan Simpan perubahan agar revisi tampil pada halaman siswa.');
 };
 document.getElementById('addActivity').onclick=function(){
   var main=document.querySelector('main'), n=Date.now();
   var sec=document.createElement('section'); sec.id='aktivitasGuru'+n;
   sec.innerHTML='<h2>Aktivitas tambahan</h2><p class="amati">Tuliskan petunjuk aktivitas di sini.</p><div class="q"><label class="t" for="activity_'+n+'">Jawaban siswa:</label><textarea id="activity_'+n+'" data-key="activity_'+n+'" rows="4" placeholder="Tuliskan jawabanmu di sini"></textarea></div>';
   main.appendChild(sec);
   siapkanSemuaTeks();
   aturModeEdit();
   sec.scrollIntoView({behavior:'smooth',block:'center'});
   status('Aktivitas baru ditambahkan. Edit tulisannya bila diperlukan, lalu simpan perubahan.');
 };
 document.getElementById('saveELKPD').onclick=function(){
   var main=document.querySelector('main');
   var salinan=main.cloneNode(true);
   // Bersihkan atribut editor hanya dari salinan yang disimpan.
   // Halaman editor tetap utuh agar guru dapat melanjutkan penyuntingan.
   salinan.querySelectorAll('[data-guru-editable]').forEach(function(el){
     el.removeAttribute('contenteditable');
     el.removeAttribute('data-guru-editable');
     el.removeAttribute('style');
   });
   status('Menyimpan seluruh perubahan E-LKPD...');
   this.disabled=true;
   fetch('/guru/elkpd/simpan',{method:'POST',cache:'no-store',headers:{'Content-Type':'application/json'},body:JSON.stringify({main_html:salinan.innerHTML})})
   .then(function(r){return r.json().then(function(j){if(!r.ok) throw new Error(j.pesan||'Gagal menyimpan.');return j;});})
   .then(function(j){status('Berhasil disimpan pada '+(j.waktu||'server')+'. Halaman siswa akan menggunakan versi terbaru.');})
   .catch(function(e){status('Gagal menyimpan: '+e.message+'. Periksa koneksi lalu coba lagi.');})
   .finally(function(){document.getElementById('saveELKPD').disabled=false;});
 };
})();
</script>'''
    # Mode edit menampilkan semua bagian sekaligus (tanpa tampilan per halaman)
    penanda = '<script>window.ELKPD_EDITOR=true;document.body.classList.remove("paged");</script>\n'
    halaman = halaman.replace('<body class="paged">', '<body class="paged">\n' + penanda + toolbar, 1)
    halaman = halaman.replace('</body>', editor_script + '\n</body>', 1)
    response = Response(halaman, mimetype="text/html")
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.route("/guru/elkpd/simpan", methods=["POST"])
@guru_wajib
def guru_simpan_elkpd():
    p = request.get_json(silent=True) or {}
    main_html = p.get("main_html", "")
    if not isinstance(main_html, str) or not main_html.strip():
        return jsonify(ok=False, pesan="Isi ELKPD tidak boleh kosong."), 400
    if len(main_html) > 2_000_000:
        return jsonify(ok=False, pesan="Ukuran perubahan terlalu besar."), 413
    with db() as c:
        c.execute("INSERT INTO elkpd_konten(id,main_html,diperbarui,versi) VALUES(1,?,?,?) "
                  "ON CONFLICT(id) DO UPDATE SET main_html=excluded.main_html,diperbarui=excluded.diperbarui,versi=excluded.versi",
                  (main_html, sekarang(), ELKPD_CONTENT_VERSION))
    return jsonify(ok=True, waktu=sekarang())


SISWA_HTML = r"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>E-LKPD Peluang - Matematika Kelas VIII</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;800&display=swap" rel="stylesheet">
<style>
:root{--ink:#14213d;--bg:#eef3f8;--card:#fff;--line:#d5dee8;--teal:#0f766e;--teal2:#d7f0ec;--gold:#e0a800;--red:#c8102e;--muted:#5b6b7e}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;font-family:'Nunito','Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--ink);line-height:1.6;font-size:17px}
header{background:var(--ink);color:#fff;padding:28px 18px 24px}
header .in{max-width:860px;margin:auto}
header h1{margin:0 0 6px;font-size:clamp(26px,5vw,38px);font-weight:800}
header p{margin:0;color:#c7d3e3}
.coins{display:flex;gap:10px;margin-top:14px;font-size:30px}
body.dalam header{padding:12px 18px}
body.dalam header p,body.dalam .coins{display:none}
body.dalam header h1{font-size:22px;margin:0}
nav{position:sticky;top:0;z-index:20;background:#fff;border-bottom:1px solid var(--line)}
nav .in{max-width:860px;margin:auto;display:flex;gap:4px;overflow-x:auto;padding:6px 10px}
nav a{white-space:nowrap;padding:7px 12px;border-radius:99px;text-decoration:none;color:var(--ink);font-size:14px;font-weight:600}
nav a:hover{background:var(--teal2)}
nav .tab{white-space:nowrap;padding:7px 12px;border-radius:99px;border:0;background:none;color:var(--ink);font-size:14px;font-weight:600}
nav .tab:hover{background:var(--teal2)}
nav .tab.on{background:var(--ink);color:#fff}
#progHal{height:4px;background:#e3e9f0}
#progHal i{display:block;height:100%;width:0;background:var(--teal);transition:width .25s}
body:not(.paged) #progHal{display:none}
main{max-width:860px;margin:auto;padding:14px 14px 160px}
section{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:20px;margin:18px 0}
body.paged main>section{display:none}
body.paged main>section.aktif{display:block;animation:masuk .25s ease-out}
@keyframes masuk{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
h2{margin:0 0 4px;font-size:24px;font-weight:800}
h3{margin:18px 0 6px;font-size:18px}
.tujuan{background:var(--teal2);border-radius:10px;padding:10px 14px;margin:10px 0;font-size:15px}
.amati{background:#fff8e1;border-left:4px solid var(--gold);border-radius:8px;padding:10px 14px;margin:10px 0}
.koin-klik-wrap{background:#f5f8fb;border:1.5px solid #d8e2ec;border-radius:14px;padding:16px;margin:14px 0;text-align:center}
.koin-klik-btn{background:transparent;border:0;padding:8px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center}
.koin-klik-btn:focus-visible{outline:3px solid #7cc9bf;outline-offset:3px}
.koin-visual{width:132px;height:132px;border-radius:50%;border:7px solid #b7791f;background:radial-gradient(circle at 32% 28%,#fff2b8 0%,#f6d365 35%,#d69e2e 72%,#a66b12 100%);box-shadow:inset 0 0 0 4px #ffed9c,0 5px 10px #0002;display:flex;align-items:center;justify-content:center;color:#6b450b;font-size:48px;font-weight:900;text-shadow:0 1px 0 #fff8}
.koin-visual.muncul{animation:koin-pop .28s ease-out}
@keyframes koin-pop{0%{transform:rotateY(0) scale(.85)}50%{transform:rotateY(180deg) scale(1.08)}100%{transform:rotateY(360deg) scale(1)}}
.koin-counter{display:flex;justify-content:center;gap:10px;flex-wrap:wrap;margin:10px 0}
.koin-counter span{background:white;border:1px solid #d8e2ec;border-radius:9px;padding:8px 12px}
.rumus{background:var(--ink);color:#fff;border-radius:10px;padding:12px 16px;margin:12px 0;font-size:19px;text-align:center}
.q{margin:16px 0;padding:12px 14px;background:#f5f8fb;border-left:4px solid var(--teal);border-radius:8px}
.q label.t{display:block;font-weight:600;margin-bottom:6px}
.q .sub{display:block;font-size:14px;color:var(--muted);font-weight:600;margin:8px 0 3px}
input[type=text],input[type=number],textarea{width:100%;padding:10px 12px;border:1.5px solid #b9c6d4;border-radius:8px;font:inherit;background:#fff}
input:focus,textarea:focus,button:focus-visible,a:focus-visible{outline:3px solid #7cc9bf;outline-offset:1px}
input[readonly]{background:#e9eef4;font-weight:800}
.row{display:flex;gap:10px;flex-wrap:wrap}.row>*{flex:1 1 120px}
.opt{display:block;padding:8px 12px;margin:6px 0;border:1.5px solid #b9c6d4;border-radius:8px;background:#fff;cursor:pointer}
.opt:has(input:checked){border-color:var(--teal);background:var(--teal2)}
.opt input{margin-right:8px}
button{font:inherit;cursor:pointer}
.btn{background:var(--teal);color:#fff;border:0;padding:10px 18px;border-radius:9px;font-weight:700}
.btn.gold{background:var(--gold);color:#3a2b00}.btn.red{background:var(--red)}
.btn.ghost{background:#fff;color:var(--ink);border:1.5px solid var(--ink)}
.btn[disabled]{opacity:.5;cursor:not-allowed}
.sim{background:#fbfcfe;border:1.5px dashed #9fb2c6;border-radius:12px;padding:14px;margin:12px 0}
.hasil{font-size:56px;text-align:center;min-height:76px;margin:4px 0}
.bars{display:grid;gap:6px;margin-top:10px}
.bars .b{display:grid;grid-template-columns:70px 1fr 50px;align-items:center;gap:8px;font-size:14px}
.bars .track{background:#e3e9f0;border-radius:99px;height:16px;overflow:hidden}
.bars .fill{height:100%;background:var(--teal);width:0;transition:width .25s}
.bars .fill.g{background:var(--gold)}
.dgrid{display:grid;grid-template-columns:repeat(6,1fr);gap:6px;margin-top:8px}
.dgrid div{text-align:center;font-size:13px}
.dgrid input{text-align:center;padding:8px 2px}
.info{color:var(--muted);font-size:14px}
#gate{position:fixed;inset:0;background:rgba(20,33,61,.94);z-index:100;display:flex;align-items:center;justify-content:center;padding:16px}
#gate .box{background:#fff;border-radius:16px;padding:24px;max-width:420px;width:100%}
#gate h2{font-size:26px}
.err{color:var(--red);font-weight:700;min-height:22px}
#bar{position:fixed;left:0;right:0;bottom:0;background:#fff;border-top:1px solid var(--line);padding:8px 14px;z-index:30;display:flex;flex-direction:column;gap:6px;align-items:center}
.pgr{display:flex;gap:10px;align-items:center;justify-content:space-between;width:100%;max-width:860px}
.pgr #halInfo{font-weight:700;font-size:14px;text-align:center}
.sv{display:flex;gap:10px;align-items:center;justify-content:center;flex-wrap:wrap}
.sv .btn{padding:6px 14px;font-size:14px}
body:not(.paged) .pgr{display:none}
#status{font-size:14px;color:var(--muted)}#status.ok{color:#0a7a3d;font-weight:700}#status.bad{color:var(--red);font-weight:700}
#who{font-size:14px;font-weight:700}
#hasilGuru .feedback-card{background:#fff;border:1px solid var(--line);border-left:5px solid var(--teal);border-radius:10px;padding:13px 15px;margin:12px 0}
#hasilGuru .feedback-card h3{margin:0 0 5px;font-size:16px}
#hasilGuru .feedback-komentar{white-space:pre-wrap;margin:4px 0 0}
#hasilGuru .feedback-kosong{background:#fff8e1;border-left:4px solid var(--gold);padding:12px;border-radius:8px}
#hasilGuru .nilai-guru{font-size:26px;font-weight:800;color:var(--teal)}
#hasilGuru .btn{margin:8px 0}

.hid{display:none}
table.t{border-collapse:collapse;margin:8px 0;width:100%}table.t td,table.t th{border:1px solid #b9c6d4;padding:6px 12px;text-align:center}
table.t th{background:var(--teal2)}
table.t td.l,table.t th.l{text-align:left}
table.t input[type=text]{text-align:center;max-width:140px}
.cth{background:#eef7f5;border-radius:8px;padding:8px 12px;margin:8px 0;font-size:15px}
@media (prefers-reduced-motion:reduce){*{transition:none!important;scroll-behavior:auto!important}body.paged main>section.aktif{animation:none}}
</style>
</head>
<body class="paged">

<!-- ========== LOGIN SISWA ========== -->
<div id="gate">
  <div class="box">
    <h2>Selamat datang!</h2>
    <p>Isi identitasmu dulu. Jawabanmu akan tersimpan otomatis dan bisa dilihat gurumu.</p>
    <p><label>Nama lengkap<input type="text" id="inNama" autocomplete="name"></label></p>
    <p><label>Kelas (contoh: VIII-A)<input type="text" id="inKelas"></label></p>
    <p class="err" id="gateErr"></p>
    <button class="btn" id="btnMulai" style="width:100%">Mulai mengerjakan</button>
    <p class="info">Tip: kalau kamu menutup halaman ini, masuk lagi dengan nama dan kelas yang sama. Jawabanmu akan muncul kembali.</p>
  </div>
</div>

<header><div class="in">
  <h1>E-LKPD Peluang</h1>
  <p>Matematika Kelas VIII &ndash; Fase D &middot; Peluang, Frekuensi Relatif, dan Frekuensi Harapan</p>
  <div class="coins" aria-hidden="true"><span>🪙</span><span>🎲</span></div>
</div></header>

<nav><div class="in" id="navHal">
  <a href="#tujuan">Petunjuk &amp; Tujuan</a><a href="#k1">1. Mengenal Peluang</a><a href="#k2">2. Frekuensi Relatif</a>
  <a href="#k3">3. Frekuensi Harapan</a><a href="#k4">4. Masalah Sehari-hari</a>
  <a href="#k5">5. Uji Pemahaman</a><a href="#kesimpulan">Kesimpulan</a><a href="#refleksi">Refleksi</a>
</div><div id="progHal"><i id="progI"></i></div></nav>

<main>

<!-- ========== PETUNJUK & TUJUAN ========== -->
<section id="tujuan">
  <h2>Petunjuk Pengerjaan</h2>
  <ul>
    <li>Kerjakan kegiatan secara berurutan. Bacalah informasi dan petunjuk sebelum melakukan setiap kegiatan.</li>
    <li>Gunakan simulasi pelemparan koin dan dadu pada website. Jika simulasi tidak tersedia, gunakan koin atau dadu asli.</li>
    <li>Untuk setiap percobaan, catat hasil yang diperoleh pada tabel. Pastikan jumlah seluruh hasil sama dengan jumlah percobaan.</li>
    <li>Tuliskan cara perhitungan dan jawaban pada tempat yang disediakan. Gunakan satuan yang sesuai.</li>
    <li>Periksa kembali hasil pekerjaanmu sebelum melanjutkan ke kegiatan berikutnya.</li>
    <li>Gunakan tombol <b>Berikutnya</b> dan <b>Sebelumnya</b> di bagian bawah layar untuk berpindah halaman. Kamu juga bisa menekan judul halaman di bagian atas.</li>
  </ul>
  <div class="tujuan">
    Jawabanmu <b>tersimpan otomatis</b>. Kamu juga bisa menekan tombol <b>Simpan jawaban</b> di bagian bawah layar.
  </div>
  <h2 style="margin-top:20px">A. Capaian Pembelajaran (CP)</h2>
  <p>Pada akhir Fase D, peserta didik dapat menjelaskan dan menggunakan pengertian peluang serta frekuensi relatif untuk menentukan frekuensi harapan satu kejadian pada suatu percobaan sederhana yang semua hasilnya memiliki kesempatan sama untuk terjadi.</p>
  <h2 style="margin-top:20px">B. Tujuan Pembelajaran</h2>
  <p>Setelah menyelesaikan LKPD ini, peserta didik diharapkan mampu:</p>
  <ol>
    <li>Menjelaskan peluang suatu kejadian sederhana berdasarkan ruang sampel dan kejadian.</li>
    <li>Menentukan frekuensi relatif berdasarkan hasil percobaan.</li>
    <li>Menghitung frekuensi harapan dan membandingkannya dengan hasil percobaan.</li>
  </ol>
</section>

<!-- ========== KEGIATAN 1 ========== -->
<section id="k1">
  <h2>C. Kegiatan 1 &ndash; Mengenal Peluang</h2>

  <h3>Ayo Amati!</h3>
  <div class="amati">Perhatikan sebuah koin seimbang yang memiliki dua sisi, yaitu angka (A) dan gambar (G). Koin dikatakan seimbang jika kedua sisinya memiliki kesempatan yang sama untuk muncul. Ketika koin dilempar, salah satu sisi akan muncul, tetapi hasilnya belum dapat dipastikan sebelumnya.</div>

  <div class="koin-klik-wrap" id="percobaanKoinK1">
    <h3 style="margin-top:0">Coba Lempar Koin!</h3>
    <p>Klik gambar koin untuk melempar satu kali. Klik lagi untuk melakukan lemparan berikutnya.</p>
    <button type="button" class="koin-klik-btn" id="k1KoinLempar" aria-label="Lempar koin satu kali">
      <span class="koin-visual" id="k1KoinVisual" aria-live="polite">🪙</span>
    </button>
    <p id="k1KoinHasil"><b>Hasil lemparan:</b> Belum dilempar. Klik gambar koin di atas.</p>
    <div class="koin-counter">
      <span>Angka (A): <b id="k1KoinAngkaTampil">0</b></span>
      <span>Gambar (G): <b id="k1KoinGambarTampil">0</b></span>
      <span>Total lemparan: <b id="k1KoinTotalTampil">0</b></span>
    </div>
    <input type="hidden" id="k1_koin_angka" data-key="k1_koin_angka" value="0">
    <input type="hidden" id="k1_koin_gambar" data-key="k1_koin_gambar" value="0">
    <input type="hidden" id="k1_koin_riwayat" data-key="k1_koin_riwayat" value="">
    <button type="button" class="btn ghost" id="k1KoinReset">Ulangi percobaan</button>
    <p class="info">Hasil setiap klik diacak secara terpisah. Angka dan gambar memiliki peluang yang sama, tetapi jumlah kemunculannya tidak harus sama.</p>
  </div>

  <div class="q"><label class="t" for="k1_a1">1. Apa saja sisi yang mungkin muncul ketika sebuah koin dilempar?</label>
    <input type="text" id="k1_a1" data-key="k1_a1" placeholder="Jawaban"></div>
  <div class="q"><label class="t" for="k1_a2">2. Apakah kita dapat memastikan sisi yang muncul sebelum koin dilempar? Jelaskan alasanmu.</label>
    <textarea id="k1_a2" data-key="k1_a2" rows="3" placeholder="Jawaban"></textarea></div>
  <div class="q"><label class="t" for="k1_a3">3. Menurutmu, apakah peluang munculnya angka dan gambar pada koin seimbang sama besar? Berikan alasanmu.</label>
    <textarea id="k1_a3" data-key="k1_a3" rows="3" placeholder="Jawaban"></textarea></div>

  <h3>Ayo Pahami!</h3>
  <p>Peluang adalah ukuran kemungkinan terjadinya suatu kejadian. Jika setiap hasil dalam ruang sampel memiliki kesempatan sama untuk muncul, peluang kejadian A ditentukan dengan rumus berikut.</p>
  <div class="rumus">P(A) = banyak hasil yang mendukung kejadian A &divide; banyak seluruh hasil dalam ruang sampel</div>
  <div class="cth"><b>Contoh:</b> sebuah koin seimbang memiliki dua hasil yang mungkin, yaitu angka dan gambar. Kejadian muncul angka didukung oleh satu hasil dari dua hasil yang mungkin. Jadi, P(angka) = 1/2. Dengan cara yang sama, P(gambar) = 1/2.</div>

  <h3>Coba Kerjakan!</h3>
  <div class="q"><label class="t" for="k1_c1">1. Sebuah dadu seimbang memiliki enam sisi bernomor 1, 2, 3, 4, 5, dan 6. Tuliskan ruang sampel dari percobaan tersebut dan tentukan banyak anggotanya.</label>
    <textarea id="k1_c1" data-key="k1_c1" rows="2" placeholder="Tuliskan ruang sampel dan banyak anggotanya"></textarea></div>
  <div class="q"><label class="t" for="k1_c2">2. Berdasarkan ruang sampel tersebut, tentukan peluang munculnya angka 4.</label>
    <span class="sub">Perhitungan dan jawaban</span><textarea id="k1_c2" data-key="k1_c2" rows="2" placeholder="Tuliskan perhitungan dan jawabanmu"></textarea></div>
  <div class="q"><label class="t" for="k1_c3">3. Tentukan peluang munculnya bilangan genap pada satu kali pelemparan dadu. Tuliskan anggota kejadian bilangan genap terlebih dahulu.</label>
    <span class="sub">Perhitungan dan jawaban</span><textarea id="k1_c3" data-key="k1_c3" rows="2" placeholder="Tuliskan anggota kejadian, perhitungan, dan jawabanmu"></textarea></div>
</section>

<!-- ========== KEGIATAN 2 ========== -->
<section id="k2">
  <h2>D. Kegiatan 2 &ndash; Menyelidiki Frekuensi Relatif</h2>
  <h3>Ayo Lakukan Percobaan!</h3>
  <p>Lakukan dua percobaan pelemparan koin seimbang menggunakan simulasi website atau koin asli. Pada percobaan pertama, lempar koin 20 kali. Pada percobaan kedua, lempar koin 40 kali. Catat banyak kemunculan sisi angka dan gambar untuk setiap percobaan. Mulailah setiap percobaan dari awal dan jangan menjumlahkan hasil percobaan pertama ke percobaan kedua.</p>

  <div class="sim" id="simKoin20">
    <b>Percobaan pertama: 20 kali pelemparan</b>
    <div class="hasil" id="koin20Hasil">🪙</div>
    <div class="row">
      <button type="button" class="btn" data-koin20="20">Lakukan 20 lemparan</button>
      <button type="button" class="btn ghost" id="koin20Reset">Ulangi percobaan</button>
    </div>
    <p class="info" id="koin20Info">Belum dilakukan.</p>
    <table class="t"><tr><th class="l">Hasil pelemparan</th><th>Banyak kemunculan</th></tr>
      <tr><td class="l">Angka (A)</td><td><input type="text" readonly id="koin20_a" data-key="koin20_a" value="0"></td></tr>
      <tr><td class="l">Gambar (G)</td><td><input type="text" readonly id="koin20_g" data-key="koin20_g" value="0"></td></tr>
      <tr><td class="l">Jumlah kemunculan</td><td><input type="text" readonly id="koin20_n" data-key="koin20_n" value="0"></td></tr>
      <tr><td class="l">Frekuensi relatif angka</td><td><span id="koin20_fr_a">..............</span></td></tr>
      <tr><td class="l">Frekuensi relatif gambar</td><td><span id="koin20_fr_g">..............</span></td></tr>
      <tr><td class="l">Frekuensi harapan angka</td><td>10 kali</td></tr>
    </table>
  </div>

  <div class="sim" id="simKoin40">
    <b>Percobaan kedua: 40 kali pelemparan</b>
    <div class="hasil" id="koin40Hasil">🪙</div>
    <div class="row">
      <button type="button" class="btn" data-koin40="40">Lakukan 40 lemparan</button>
      <button type="button" class="btn ghost" id="koin40Reset">Ulangi percobaan</button>
    </div>
    <p class="info" id="koin40Info">Belum dilakukan.</p>
    <table class="t"><tr><th class="l">Hasil pelemparan</th><th>Banyak kemunculan</th></tr>
      <tr><td class="l">Angka (A)</td><td><input type="text" readonly id="koin40_a" data-key="koin40_a" value="0"></td></tr>
      <tr><td class="l">Gambar (G)</td><td><input type="text" readonly id="koin40_g" data-key="koin40_g" value="0"></td></tr>
      <tr><td class="l">Jumlah kemunculan</td><td><input type="text" readonly id="koin40_n" data-key="koin40_n" value="0"></td></tr>
      <tr><td class="l">Frekuensi relatif angka</td><td><span id="koin40_fr_a">..............</span></td></tr>
      <tr><td class="l">Frekuensi relatif gambar</td><td><span id="koin40_fr_g">..............</span></td></tr>
      <tr><td class="l">Frekuensi harapan angka</td><td>20 kali</td></tr>
    </table>
  </div>

  <h3>Ayo Analisis!</h3>
  <div class="q"><label class="t" for="k2_a1">1. Berdasarkan tabel, berapa kali sisi angka dan sisi gambar muncul pada setiap percobaan? Periksa apakah jumlah keduanya sesuai dengan jumlah lemparan.</label>
    <textarea id="k2_a1" data-key="k2_a1" rows="3" placeholder="Tuliskan hasil percobaan 20 kali dan 40 kali"></textarea></div>
  <div class="q"><label class="t" for="k2_a2">2. Hitung frekuensi relatif sisi angka dan sisi gambar pada percobaan 20 kali dan 40 kali. Tuliskan perhitunganmu.</label>
    <textarea id="k2_a2" data-key="k2_a2" rows="4" placeholder="Tuliskan perhitungan untuk kedua percobaan"></textarea></div>
  <div class="q"><label class="t" for="k2_a3">3. Bandingkan frekuensi relatif sisi angka pada percobaan 20 kali dan 40 kali. Apakah nilainya sama? Jelaskan berdasarkan hasil percobaanmu.</label>
    <textarea id="k2_a3" data-key="k2_a3" rows="3"></textarea></div>
  <div class="rumus">Frekuensi relatif = banyak kemunculan kejadian &divide; jumlah percobaan</div>
  <h3>Ayo Pahami!</h3>
  <p>Frekuensi relatif adalah perbandingan antara banyak kemunculan suatu kejadian dan jumlah seluruh percobaan yang dilakukan.</p>
  <div class="cth"><b>Contoh:</b> dalam 20 kali pelemparan, sisi angka muncul 12 kali. Frekuensi relatif sisi angka = 12/20 = 0,6 atau 60%. Nilai frekuensi relatif dapat berbeda pada setiap percobaan.</div>
  <div class="q"><label class="t" for="k2_a4">4. Peluang teoretis munculnya sisi angka pada koin seimbang adalah 1/2. Tentukan frekuensi harapan sisi angka untuk 20 kali dan 40 kali pelemparan.</label>
    <textarea id="k2_a4" data-key="k2_a4" rows="3"></textarea></div>
  <div class="q"><label class="t" for="k2_a5">5. Bandingkan frekuensi relatif sisi angka yang kamu peroleh dengan peluang teoretisnya, yaitu 1/2. Apakah hasilnya mendekati 1/2 ketika jumlah percobaan bertambah? Jelaskan berdasarkan data yang kamu peroleh.</label>
    <textarea id="k2_a5" data-key="k2_a5" rows="3"></textarea></div>
  <div class="q"><label class="t" for="k2_a6">6. Berdasarkan tabel, bandingkan frekuensi relatif sisi angka dengan frekuensi harapannya pada masing-masing jumlah percobaan. Apa yang dapat kamu simpulkan?</label>
    <textarea id="k2_a6" data-key="k2_a6" rows="3"></textarea></div>
</section>

<!-- ========== KEGIATAN 3 ========== -->
<section id="k3">
  <h2>E. Kegiatan 3 &ndash; Menentukan Frekuensi Harapan</h2>
  <h3>Ayo Amati!</h3>
  <div class="amati">Sebuah dadu seimbang memiliki enam sisi bernomor 1 sampai 6. Jika dadu dilempar berulang kali, setiap angka memiliki peluang teoretis 1/6 untuk muncul. Frekuensi harapan digunakan untuk memperkirakan banyak kemunculan suatu kejadian.</div>
  <div class="rumus">Frekuensi harapan = peluang kejadian &times; jumlah percobaan</div>
  <div class="cth"><b>Contoh:</b> dadu seimbang dilempar 60 kali. Peluang munculnya angka 6 adalah 1/6. Frekuensi harapan angka 6 = 1/6 &times; 60 = 10 kali. Artinya, angka 6 diperkirakan muncul 10 kali, tetapi hasil sebenarnya tidak harus tepat 10 kali.</div>

  <h3>Ayo Lakukan Simulasi!</h3>
  <p>Lempar sebuah dadu seimbang sebanyak 30 kali melalui simulasi website atau menggunakan dadu asli. Catat banyak kemunculan setiap angka. Ulangi percobaan dari awal hingga mencapai 60 kali lemparan, lalu catat hasilnya secara terpisah.</p>
  <div class="sim" id="simDadu30">
    <b>Percobaan pertama: 30 kali lemparan</b>
    <div class="hasil" id="dadu30Hasil">🎲</div>
    <button type="button" class="btn" id="dadu30Mulai">Lempar 30 kali</button>
    <button type="button" class="btn ghost" id="dadu30Reset">Ulangi percobaan</button>
    <div class="dgrid" id="dgrid30"></div>
    <p class="info" id="dadu30Info">Belum ada lemparan.</p>
  </div>
  <div class="sim" id="simDadu60">
    <b>Percobaan kedua: 60 kali lemparan (dimulai dari awal)</b>
    <div class="hasil" id="dadu60Hasil">🎲</div>
    <button type="button" class="btn" id="dadu60Mulai">Lempar 60 kali</button>
    <button type="button" class="btn ghost" id="dadu60Reset">Ulangi percobaan</button>
    <div class="dgrid" id="dgrid60"></div>
    <p class="info" id="dadu60Info">Belum ada lemparan.</p>
  </div>
  <div class="q"><label class="t" for="k3_sim_a">Analisis simulasi: (a) Tentukan frekuensi relatif kemunculan angka 6 pada masing-masing percobaan.</label>
    <textarea id="k3_sim_a" data-key="k3_sim_a" rows="3"></textarea></div>
  <div class="q"><label class="t" for="k3_sim_b">(b) Tentukan frekuensi harapan angka 6 untuk 30 dan 60 kali lemparan.</label>
    <textarea id="k3_sim_b" data-key="k3_sim_b" rows="3"></textarea></div>
  <div class="q"><label class="t" for="k3_sim_c">(c) Bandingkan hasil pengamatan dengan frekuensi harapan. Apakah hasilnya sama? Jelaskan.</label>
    <textarea id="k3_sim_c" data-key="k3_sim_c" rows="3"></textarea></div>

  <h3>Ayo Kerjakan!</h3>
  <div class="q"><b>1. Sebuah koin seimbang dilempar sebanyak 40 kali.</b>
    <label class="t sub" for="k3_1a">a. Berapa peluang munculnya sisi gambar?</label>
    <input type="text" id="k3_1a" data-key="k3_1a" placeholder="Jawaban">
    <label class="t sub" for="k3_1b">b. Berapa frekuensi harapan munculnya sisi gambar?</label>
    <span class="sub">Jawaban</span><input type="text" id="k3_1b" data-key="k3_1b" placeholder="Tuliskan cara dan jawabanmu"></div>

  <div class="q"><b>2. Sebuah dadu seimbang dilempar sebanyak 72 kali. Tentukan frekuensi harapan munculnya angka 3.</b>
    <span class="sub">Diketahui</span><textarea id="k3_2" data-key="k3_2" rows="3" placeholder="Tuliskan yang diketahui, ditanya, perhitungan, dan jawaban"></textarea></div>

  <div class="q"><b>3. Sebuah dadu seimbang dilempar sebanyak 120 kali. Tentukan frekuensi harapan munculnya angka genap (2, 4, dan 6).</b>
    <span class="sub">a. Peluang munculnya angka genap</span><textarea id="k3_3a" data-key="k3_3a" rows="2" placeholder="Tuliskan perhitungan dan jawaban"></textarea>
    <span class="sub">b. Frekuensi harapan munculnya angka genap</span><textarea id="k3_3b" data-key="k3_3b" rows="2" placeholder="Tuliskan perhitungan dan jawaban"></textarea></div>
</section>

<!-- ========== KEGIATAN 4 ========== -->
<section id="k4">
  <h2>F. Kegiatan 4 &ndash; Menyelesaikan Masalah Sehari-hari</h2>
  <div class="amati">Dalam sebuah permainan di sekolah, peserta melempar satu dadu seimbang. Peserta memperoleh hadiah apabila hasil pelemparan memenuhi ketentuan yang ditetapkan panitia, yaitu bilangan yang lebih besar dari 4.</div>

  <div class="q"><label class="t" for="k4_1">1. Ada berapa hasil yang mungkin muncul ketika dadu dilempar satu kali?</label>
    <input type="text" id="k4_1" data-key="k4_1" placeholder="Jawaban"></div>
  <div class="q"><label class="t" for="k4_2">2. Ada berapa hasil yang membuat peserta mendapatkan hadiah?</label>
    <input type="text" id="k4_2" data-key="k4_2" placeholder="Jawaban"></div>
  <div class="q"><label class="t" for="k4_3">3. Tentukan peluang seorang peserta mendapatkan hadiah.</label>
    <span class="sub">Jawaban</span><input type="text" id="k4_3" data-key="k4_3" placeholder="Tuliskan cara dan jawabanmu"></div>
  <div class="q"><label class="t" for="k4_4">4. Jika permainan dilakukan sebanyak 90 kali, berapa frekuensi harapan peserta mendapatkan hadiah?</label>
    <span class="sub">Jawaban</span><input type="text" id="k4_4" data-key="k4_4" placeholder="Tuliskan cara dan jawabanmu"></div>
  <div class="q"><label class="t" for="k4_5">5. Apakah jumlah peserta yang benar-benar mendapatkan hadiah pasti sama dengan frekuensi harapan? Jelaskan.</label>
    <textarea id="k4_5" data-key="k4_5" rows="3" placeholder="Jawaban"></textarea></div>
</section>

<!-- ========== KEGIATAN 5: PG ========== -->
<section id="k5">
  <h2>G. Kegiatan 5 &ndash; Uji Pemahaman</h2>
  <h3>Contoh Soal dan Pembahasan</h3>
  <div class="amati"><b>Soal:</b> Sebuah dadu seimbang dilempar sebanyak 24 kali. Tentukan frekuensi harapan munculnya bilangan ganjil.</div>
  <p><b>Diketahui:</b> jumlah percobaan = 24; ruang sampel = {1, 2, 3, 4, 5, 6}; kejadian bilangan ganjil = {1, 3, 5}.</p>
  <p><b>Langkah 1.</b> Tentukan peluang kejadian: P(ganjil) = 3/6 = 1/2.</p>
  <p><b>Langkah 2.</b> Gunakan rumus frekuensi harapan: Fh = P(kejadian) &times; jumlah percobaan.</p>
  <p><b>Langkah 3.</b> Substitusikan nilai: Fh = 1/2 &times; 24 = 12 kali.</p>
  <div class="cth">Jadi, frekuensi harapan munculnya bilangan ganjil adalah 12 kali. Hasil sebenarnya dapat berbeda dari nilai tersebut.</div>
  <p class="info">Setelah mempelajari contoh soal dan pembahasannya, kerjakan soal berikut secara mandiri. Pilih satu jawaban yang paling tepat.</p>

  <div class="q"><b>1. Sebuah dadu seimbang dilempar satu kali. Peluang munculnya angka 2 adalah ....</b>
    <label class="opt"><input type="radio" name="pg1" data-key="pg1" value="A">A. 1/2</label>
    <label class="opt"><input type="radio" name="pg1" data-key="pg1" value="B">B. 1/3</label>
    <label class="opt"><input type="radio" name="pg1" data-key="pg1" value="C">C. 1/6</label>
    <label class="opt"><input type="radio" name="pg1" data-key="pg1" value="D">D. 2/6</label></div>

  <div class="q"><b>2. Dalam 25 kali pelemparan koin, sisi gambar muncul sebanyak 15 kali. Frekuensi relatif gambar adalah ....</b>
    <label class="opt"><input type="radio" name="pg2" data-key="pg2" value="A">A. 0,25</label>
    <label class="opt"><input type="radio" name="pg2" data-key="pg2" value="B">B. 0,40</label>
    <label class="opt"><input type="radio" name="pg2" data-key="pg2" value="C">C. 0,60</label>
    <label class="opt"><input type="radio" name="pg2" data-key="pg2" value="D">D. 0,75</label></div>

  <div class="q"><b>3. Sebuah koin seimbang dilempar sebanyak 80 kali. Frekuensi harapan munculnya sisi angka adalah ....</b>
    <label class="opt"><input type="radio" name="pg3" data-key="pg3" value="A">A. 20 kali</label>
    <label class="opt"><input type="radio" name="pg3" data-key="pg3" value="B">B. 30 kali</label>
    <label class="opt"><input type="radio" name="pg3" data-key="pg3" value="C">C. 40 kali</label>
    <label class="opt"><input type="radio" name="pg3" data-key="pg3" value="D">D. 80 kali</label></div>

  <div class="q"><b>4. Sebuah dadu seimbang dilempar sebanyak 48 kali. Frekuensi harapan munculnya angka genap adalah ....</b>
    <label class="opt"><input type="radio" name="pg4" data-key="pg4" value="A">A. 8 kali</label>
    <label class="opt"><input type="radio" name="pg4" data-key="pg4" value="B">B. 16 kali</label>
    <label class="opt"><input type="radio" name="pg4" data-key="pg4" value="C">C. 24 kali</label>
    <label class="opt"><input type="radio" name="pg4" data-key="pg4" value="D">D. 32 kali</label></div>

  <div class="q"><b>5. Dalam 30 kali pelemparan koin, sisi angka muncul sebanyak 18 kali. Pernyataan yang benar adalah ....</b>
    <label class="opt"><input type="radio" name="pg5" data-key="pg5" value="A">A. Frekuensi relatif angka adalah 0,3.</label>
    <label class="opt"><input type="radio" name="pg5" data-key="pg5" value="B">B. Frekuensi relatif angka adalah 0,6.</label>
    <label class="opt"><input type="radio" name="pg5" data-key="pg5" value="C">C. Peluang teoretis angka adalah 0,6.</label>
    <label class="opt"><input type="radio" name="pg5" data-key="pg5" value="D">D. Peluang teoretis angka adalah 1.</label></div>
</section>

<!-- ========== KESIMPULAN ========== -->
<section id="kesimpulan">
  <h2>H. Kesimpulan</h2>
  <p class="info">Lengkapi kalimat berikut.</p>
  <div class="q"><label class="t" for="kes1">1. Peluang digunakan untuk mengetahui ....</label>
    <input type="text" id="kes1" data-key="kes1"></div>
  <div class="q"><label class="t" for="kes2">2. Frekuensi relatif diperoleh dengan membandingkan ....</label>
    <input type="text" id="kes2" data-key="kes2"></div>
  <div class="q"><label class="t" for="kes3">3. Frekuensi harapan dapat ditentukan dengan mengalikan ....</label>
    <input type="text" id="kes3" data-key="kes3"></div>
  <div class="q"><label class="t" for="kes4">4. Hasil percobaan dapat berbeda dari frekuensi harapan karena ....</label>
    <input type="text" id="kes4" data-key="kes4"></div>
</section>

<!-- ========== REFLEKSI ========== -->
<section id="refleksi">
  <h2>I. Refleksi Diri</h2>
  <div class="scroll" style="overflow-x:auto">
  <table class="t">
    <tr><th class="l">Pernyataan</th><th>Sudah Paham</th><th>Masih Perlu Belajar</th></tr>
    <tr><td class="l">Saya dapat menentukan peluang suatu kejadian sederhana.</td>
      <td><input type="radio" name="ref1" data-key="ref1" value="Sudah Paham" aria-label="Sudah paham, pernyataan 1"></td>
      <td><input type="radio" name="ref1" data-key="ref1" value="Masih Perlu Belajar" aria-label="Masih perlu belajar, pernyataan 1"></td></tr>
    <tr><td class="l">Saya dapat menghitung frekuensi relatif berdasarkan hasil percobaan.</td>
      <td><input type="radio" name="ref2" data-key="ref2" value="Sudah Paham" aria-label="Sudah paham, pernyataan 2"></td>
      <td><input type="radio" name="ref2" data-key="ref2" value="Masih Perlu Belajar" aria-label="Masih perlu belajar, pernyataan 2"></td></tr>
    <tr><td class="l">Saya dapat menentukan frekuensi harapan suatu kejadian.</td>
      <td><input type="radio" name="ref3" data-key="ref3" value="Sudah Paham" aria-label="Sudah paham, pernyataan 3"></td>
      <td><input type="radio" name="ref3" data-key="ref3" value="Masih Perlu Belajar" aria-label="Masih perlu belajar, pernyataan 3"></td></tr>
    <tr><td class="l">Saya dapat menyelesaikan masalah sederhana tentang peluang.</td>
      <td><input type="radio" name="ref4" data-key="ref4" value="Sudah Paham" aria-label="Sudah paham, pernyataan 4"></td>
      <td><input type="radio" name="ref4" data-key="ref4" value="Masih Perlu Belajar" aria-label="Masih perlu belajar, pernyataan 4"></td></tr>
  </table></div>
  <div class="q"><label class="t" for="ref_paham">Hal yang sudah saya pahami:</label>
    <textarea id="ref_paham" data-key="ref_paham" rows="3"></textarea></div>
  <div class="q"><label class="t" for="ref_belajar">Hal yang masih ingin saya pelajari:</label>
    <textarea id="ref_belajar" data-key="ref_belajar" rows="3"></textarea></div>
  <p><button class="btn" id="btnSimpan2">Simpan jawaban</button></p>
</section>

<!-- ========== HASIL PENILAIAN DAN UMPAN BALIK GURU ========== -->
<section id="hasilGuru">
  <h2>J. Hasil Penilaian dan Umpan Balik Guru</h2>
  <p class="info">Bagian ini menampilkan nilai, catatan umum, dan komentar guru terhadap jawabanmu.</p>
  <div id="hasilGuruIsi">
    <p class="info">Masuk terlebih dahulu untuk memeriksa umpan balik dari guru.</p>
  </div>
  <button type="button" class="btn ghost" id="btnMuatFeedback">Perbarui umpan balik</button>
</section>

</main>

<div id="bar">
  <div class="pgr">
    <button type="button" class="btn ghost" id="prevBtn">&larr; Sebelumnya</button>
    <span id="halInfo">Halaman 1</span>
    <button type="button" class="btn" id="nextBtn">Berikutnya &rarr;</button>
  </div>
  <div class="sv">
    <span id="who"></span>
    <span id="status">Belum disimpan</span>
    <button type="button" class="btn gold" id="btnSimpan">Simpan jawaban</button>
  </div>
</div>

<script>
(function(){
"use strict";
var nama="", kelas="", timer=null, memuat=false;
var riwayatKoin=[], riwayatDadu=[], riwayatKoinK1=[];
var dataMuat=null, halaman=[], idx=0, awalHash=true;

/* ---------- Pembantu ---------- */
function $(id){return document.getElementById(id);}
function semuaField(){return document.querySelectorAll("[data-key]");}
function kumpulkan(){
  var d={};
  semuaField().forEach(function(el){
    var k=el.getAttribute("data-key");
    if(el.type==="radio"){ if(el.checked) d[k]=el.value; }
    else d[k]=el.value;
  });
  return d;
}
function isiKembali(d){
  memuat=true;
  semuaField().forEach(function(el){
    var k=el.getAttribute("data-key");
    if(!(k in d)) return;
    if(el.type==="radio") el.checked=(el.value===d[k]);
    else el.value=d[k];
  });
  memuat=false;
  segarkanSim();
}
function setStatus(t,c){var s=$("status");s.textContent=t;s.className=c||"";}

/* ---------- Simpan ke server ---------- */
function simpan(){
  if(!nama) return;
  setStatus("Menyimpan...","");
  fetch("/api/simpan",{method:"POST",headers:{"Content-Type":"application/json"},
    body:JSON.stringify({nama:nama,kelas:kelas,data:kumpulkan()})})
  .then(function(r){return r.json();})
  .then(function(j){
    if(j.ok) setStatus("Tersimpan pukul "+j.waktu.split(" ")[1],"ok");
    else setStatus("Gagal menyimpan: "+(j.pesan||""),"bad");
  })
  .catch(function(){setStatus("Gagal menyimpan. Periksa internet, lalu tekan Simpan jawaban.","bad");});
}
function jadwalSimpan(){
  if(memuat) return;
  setStatus("Menunggu disimpan...","");
  clearTimeout(timer); timer=setTimeout(simpan,1200);
}
document.addEventListener("input",function(e){
  if(e.target.hasAttribute&&e.target.hasAttribute("data-key")) jadwalSimpan();
});
document.addEventListener("change",function(e){
  if(e.target.hasAttribute&&e.target.hasAttribute("data-key")) jadwalSimpan();
});
$("btnSimpan").onclick=function(){clearTimeout(timer);simpan();};
$("btnSimpan2").onclick=function(){clearTimeout(timer);simpan();};
window.addEventListener("beforeunload",function(){
  if(nama && navigator.sendBeacon){
    var b=new Blob([JSON.stringify({nama:nama,kelas:kelas,data:kumpulkan()})],{type:"application/json"});
    navigator.sendBeacon("/api/simpan",b);
  }
});

/* ---------- Memuat hasil penilaian dan umpan balik guru ---------- */
function muatUmpanBalik(){
  if(!nama || !kelas) return;
  var wadah=$("hasilGuruIsi");
  wadah.innerHTML="<p class='info'>Memeriksa umpan balik guru...</p>";
  fetch("/api/umpan-balik",{
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify({nama:nama,kelas:kelas})
  })
  .then(function(r){return r.json();})
  .then(function(j){
    if(!j.ok){
      wadah.textContent=j.pesan||"Umpan balik belum dapat dimuat.";
      return;
    }
    wadah.innerHTML="";
    if(j.nilai){
      var nilai=document.createElement("div");
      nilai.className="feedback-card";
      var judul=document.createElement("h3");
      judul.textContent="Nilai dari Guru";
      var angka=document.createElement("div");
      angka.className="nilai-guru";
      angka.textContent=j.nilai;
      nilai.appendChild(judul); nilai.appendChild(angka); wadah.appendChild(nilai);
    }
    if(j.catatan){
      var cat=document.createElement("div");
      cat.className="feedback-card";
      var ct=document.createElement("h3");
      ct.textContent="Catatan Umum Guru";
      var cp=document.createElement("p");
      cp.className="feedback-komentar";
      cp.textContent=j.catatan;
      cat.appendChild(ct); cat.appendChild(cp); wadah.appendChild(cat);
    }
    if(j.rincian && j.rincian.length){
      var sub=document.createElement("h3");
      sub.textContent="Umpan Balik untuk Setiap Soal";
      wadah.appendChild(sub);
      j.rincian.forEach(function(item){
        var card=document.createElement("div");
        card.className="feedback-card";
        var q=document.createElement("h3");
        q.textContent=item.soal;
        var p=document.createElement("p");
        p.className="feedback-komentar";
        p.textContent=item.komentar;
        card.appendChild(q); card.appendChild(p); wadah.appendChild(card);
      });
    }
    if(!j.ada){
      var kosong=document.createElement("div");
      kosong.className="feedback-kosong";
      kosong.textContent="Guru belum memberikan penilaian atau umpan balik. Silakan periksa kembali nanti.";
      wadah.appendChild(kosong);
    }
  })
  .catch(function(){
    wadah.textContent="Tidak dapat mengambil umpan balik. Periksa koneksi internet lalu coba lagi.";
  });
}
$("btnMuatFeedback").onclick=muatUmpanBalik;

/* ---------- Login ---------- */
function masuk(){
  var n=$("inNama").value.trim().replace(/\s+/g," "), k=$("inKelas").value.trim().replace(/\s+/g," ");
  if(!n||!k){$("gateErr").textContent="Nama dan kelas wajib diisi.";return;}
  $("gateErr").textContent="Memuat...";
  fetch("/api/muat",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({nama:n,kelas:k})})
  .then(function(r){return r.json();})
  .then(function(j){
    if(!j.ok){$("gateErr").textContent=j.pesan||"Gagal masuk.";return;}
    nama=n;kelas=k;
    try{localStorage.setItem("elkpd_id",JSON.stringify({n:n,k:k}));}catch(e){}
    dataMuat=j.data||{};
    isiKembali(dataMuat);
    $("who").textContent=n+" ("+k+")";
    $("gate").style.display="none";
    setStatus(j.baru?"Belum ada jawaban":"Jawaban sebelumnya dimuat","ok");
    muatUmpanBalik();
  })
  .catch(function(){$("gateErr").textContent="Tidak bisa terhubung ke server.";});
}
$("btnMulai").onclick=masuk;
["inNama","inKelas"].forEach(function(id){$(id).addEventListener("keydown",function(e){if(e.key==="Enter")masuk();});});
try{var s=JSON.parse(localStorage.getItem("elkpd_id")||"null");if(s){$("inNama").value=s.n;$("inKelas").value=s.k;}}catch(e){}

/* ---------- Soal tambahan dari guru (tanpa edit kode) ---------- */
function muatSoalTambahan(){
 fetch("/api/soal-tambahan").then(function(r){return r.json();}).then(function(j){
   if(!j.soal || !j.soal.length) return;
   var sec=document.createElement("section"); sec.id="soalTambahan";
   sec.innerHTML="<h2>I. Soal Tambahan dari Guru</h2><p class='info'>Jawab soal tambahan yang diberikan guru.</p>";
   j.soal.forEach(function(q){
     var box=document.createElement("div"); box.className="q";
     var lab=document.createElement("label"); lab.className="t"; lab.textContent=q.pertanyaan; box.appendChild(lab);
     var key="custom_q_"+q.id;
     if(q.jenis==="pg" && q.opsi){
       q.opsi.split("|").forEach(function(opt,i){var text=opt.trim();if(!text)return;var l=document.createElement("label");l.className="opt";var inp=document.createElement("input");inp.type="radio";inp.name=key;inp.setAttribute("data-key",key);inp.value=String.fromCharCode(65+i);l.appendChild(inp);l.appendChild(document.createTextNode(" "+text));box.appendChild(l);});
     } else {var inp=document.createElement("textarea");inp.rows=3;inp.setAttribute("data-key",key);inp.placeholder="Tuliskan jawabanmu";box.appendChild(inp);}
     sec.appendChild(box);
   }); document.querySelector("main").appendChild(sec);
   // isi kembali jawaban tersimpan untuk soal tambahan (jika siswa sudah masuk lebih dulu)
   if(dataMuat){ sec.querySelectorAll("[data-key]").forEach(function(el){
     var k=el.getAttribute("data-key"); if(!(k in dataMuat)) return;
     if(el.type==="radio") el.checked=(el.value===dataMuat[k]); else el.value=dataMuat[k];
   }); }
   bangunHalaman();
 }).catch(function(){});
}
/* Aktivitas baru dibuat langsung pada editor ELKPD guru, bukan halaman kelola soal. */

/* ---------- Pengacak hasil yang kuat dan adil ---------- */
/*
  Setiap lemparan diacak secara independen menggunakan Web Crypto pada browser.
  Untuk dadu, rejection sampling dipakai agar 1-6 tidak terkena bias modulo.
  Catatan: peluang tiap sisi sama, tetapi jumlah kemunculannya tidak harus sama.
*/
function angkaAcakAdil(banyakKemungkinan){
  var batasRuang=4294967296; // 2^32
  if(window.crypto && window.crypto.getRandomValues){
    var batasTerima=Math.floor(batasRuang/banyakKemungkinan)*banyakKemungkinan;
    var buf=new Uint32Array(1),x;
    do { window.crypto.getRandomValues(buf); x=buf[0]; } while(x>=batasTerima);
    return x % banyakKemungkinan;
  }
  // Cadangan untuk browser lama; PythonAnywhere biasanya berjalan melalui HTTPS.
  return Math.floor(Math.random()*banyakKemungkinan);
}
function setVal(id,v){var el=$(id);if(el)el.value=v;}
/* ---------- Simulasi koin pengamatan awal Kegiatan 1 ---------- */
function segarkanKoinK1(){
  var a=+$("k1_koin_angka").value||0,g=+$("k1_koin_gambar").value||0;
  $("k1KoinAngkaTampil").textContent=a;
  $("k1KoinGambarTampil").textContent=g;
  $("k1KoinTotalTampil").textContent=a+g;
}
$("k1KoinLempar").onclick=function(){
  var a=+$("k1_koin_angka").value||0,g=+$("k1_koin_gambar").value||0;
  var hasil=angkaAcakAdil(2)===0?"Angka":"Gambar";
  if(hasil==="Angka"){a++;$("k1KoinVisual").textContent="A";}else{g++;$("k1KoinVisual").textContent="G";}
  setVal("k1_koin_angka",a);setVal("k1_koin_gambar",g);
  $("k1KoinHasil").innerHTML="<b>Hasil lemparan ke-"+(a+g)+":</b> "+hasil;
  segarkanKoinK1();jadwalSimpan();
};
$("k1KoinReset").onclick=function(){
  setVal("k1_koin_angka",0);setVal("k1_koin_gambar",0);
  setVal("k1_koin_riwayat","");
  $("k1KoinVisual").textContent="🪙";
  $("k1KoinHasil").innerHTML="<b>Hasil lemparan:</b> Belum dilempar. Klik gambar koin di atas.";
  segarkanKoinK1();jadwalSimpan();
};
/* ---------- Simulasi koin Kegiatan 2: 20 dan 40 lemparan terpisah ---------- */
function jalankanKoin(prefix,jumlah){
  var a=0,g=0;
  for(var i=0;i<jumlah;i++){if(angkaAcakAdil(2)===0)a++;else g++;}
  setVal(prefix+"_a",a);setVal(prefix+"_g",g);setVal(prefix+"_n",a+g);
  $(prefix+"Hasil").textContent="🪙";
  $(prefix+"Info").textContent="Hasil: angka "+a+" kali, gambar "+g+" kali. Jumlah = "+(a+g)+" lemparan.";
  jadwalSimpan();
}
$("simKoin20").querySelector("[data-koin20]").onclick=function(){jalankanKoin("koin20",20);};
$("simKoin40").querySelector("[data-koin40]").onclick=function(){jalankanKoin("koin40",40);};
function resetKoin(prefix){
  setVal(prefix+"_a",0);setVal(prefix+"_g",0);setVal(prefix+"_n",0);
  $(prefix+"Hasil").textContent="🪙";$(prefix+"Info").textContent="Belum dilakukan.";
  jadwalSimpan();
}
$("koin20Reset").onclick=function(){resetKoin("koin20");};
$("koin40Reset").onclick=function(){resetKoin("koin40");};

/* ---------- Simulasi dadu Kegiatan 3: 30 dan 60 lemparan terpisah ---------- */
var wajah=["","⚀","⚁","⚂","⚃","⚄","⚅"];
function buatDadu(prefix,gridId){
  var el=$(gridId),html="";
  for(var i=1;i<=6;i++)html+='<div>Mata '+i+'<input type="text" readonly id="'+prefix+'_'+i+'" data-key="'+prefix+'_'+i+'" value="0"></div>';
  el.innerHTML=html;
}
buatDadu("dadu30","dgrid30");
buatDadu("dadu60","dgrid60");
function jalankanDadu(prefix,jumlah){
  var c=[0,0,0,0,0,0,0],last=0;
  for(var i=0;i<jumlah;i++){last=1+angkaAcakAdil(6);c[last]++;}
  for(var j=1;j<=6;j++)setVal(prefix+"_"+j,c[j]);
  setVal(prefix+"_n",jumlah);
  $(prefix+"Hasil").textContent=wajah[last]+" "+last;
  $(prefix+"Info").textContent="Total "+jumlah+" lemparan. Angka 6 muncul "+c[6]+" kali.";
  jadwalSimpan();
}
function resetDadu(prefix){
  for(var i=1;i<=6;i++)setVal(prefix+"_"+i,0);
  setVal(prefix+"_n",0);
  $(prefix+"Hasil").textContent="🎲";$(prefix+"Info").textContent="Belum ada lemparan.";
  jadwalSimpan();
}
$("dadu30Mulai").onclick=function(){jalankanDadu("dadu30",30);};
$("dadu60Mulai").onclick=function(){jalankanDadu("dadu60",60);};
$("dadu30Reset").onclick=function(){resetDadu("dadu30");};
$("dadu60Reset").onclick=function(){resetDadu("dadu60");};
function segarkanSim(){
  // Semua elemen diperiksa terlebih dahulu agar satu elemen yang tidak ada
  // tidak menghentikan proses login dan pemulihan jawaban siswa.
  if(typeof segarkanKoinK1 === "function"){
    try{ segarkanKoinK1(); }
    catch(err){ console.warn("Simulasi koin kegiatan 1 belum dapat diperbarui:", err); }
  }

  ["koin20","koin40"].forEach(function(p){
    var ea=$(p+"_a"), eg=$(p+"_g"), en=$(p+"_n");
    var info=$(p+"Info");
    if(!ea || !eg || !en){
      console.warn("Elemen simulasi koin tidak lengkap:", p);
      return;
    }
    var a=Number(ea.value)||0;
    var g=Number(eg.value)||0;
    var n=Number(en.value)||0;
    if(info){
      info.textContent=n
        ?"Hasil tersimpan: angka "+a+" kali, gambar "+g+" kali. Jumlah = "+n+" lemparan."
        :"Belum dilakukan.";
    }
    var frA=$(p+"_fr_a"), frG=$(p+"_fr_g");
    if(frA) frA.textContent=n
      ?a+"/"+n+" = "+(a/n).toFixed(2).replace(".",",")
      :"..............";
    if(frG) frG.textContent=n
      ?g+"/"+n+" = "+(g/n).toFixed(2).replace(".",",")
      :"..............";
  });

  ["dadu30","dadu60"].forEach(function(p){
    var en=$(p+"_n"), e6=$(p+"_6"), info=$(p+"Info");
    if(!en || !e6){
      console.warn("Elemen simulasi dadu tidak lengkap:", p);
      return;
    }
    var n=Number(en.value)||0;
    var e=Number(e6.value)||0;
    if(info){
      info.textContent=n
        ?"Total "+n+" lemparan. Angka 6 muncul "+e+" kali."
        :"Belum ada lemparan.";
    }
  });
}
/* ---------- Tampilan per halaman ---------- */
var JUDUL={tujuan:"Petunjuk",k1:"1. Mengenal Peluang",k2:"2. Frekuensi Relatif",k3:"3. Frekuensi Harapan",
  k4:"4. Masalah Sehari-hari",k5:"5. Uji Pemahaman",kesimpulan:"Kesimpulan",refleksi:"Refleksi",soalTambahan:"Soal dari Guru",hasilGuru:"Umpan Balik Guru"};
function halDariHash(){var m=/^#hal-(\d+)$/.exec(location.hash);return m?parseInt(m[1],10)-1:NaN;}
function bangunHalaman(){
  if(window.ELKPD_EDITOR) return;   // mode edit guru menampilkan semua bagian
  var nav=$("navHal"); nav.innerHTML="";
  halaman=[].slice.call(document.querySelectorAll("main > section"));
  halaman.forEach(function(s,i){
    var h2=s.querySelector("h2"), b=document.createElement("button");
    b.type="button"; b.className="tab";
    b.textContent=JUDUL[s.id]||(h2?h2.textContent.replace(/^[A-Z]\.\s*/,""):"Halaman "+(i+1));
    b.onclick=function(){bukaHalaman(i,true);};
    nav.appendChild(b);
  });
  if(awalHash){awalHash=false; var p=halDariHash(); if(!isNaN(p)) idx=p;}
  bukaHalaman(idx,false);
}
function bukaHalaman(i,dariKlik){
  if(!halaman.length) return;
  i=Math.max(0,Math.min(halaman.length-1,i)); idx=i;
  halaman.forEach(function(s,j){s.classList.toggle("aktif",j===i);});
  var tabs=$("navHal").children;
  for(var j=0;j<tabs.length;j++) tabs[j].classList.toggle("on",j===i);
  if(tabs[i] && tabs[i].scrollIntoView) tabs[i].scrollIntoView({inline:"center",block:"nearest"});
  document.body.classList.toggle("dalam",i>0);
  $("halInfo").textContent="Halaman "+(i+1)+" dari "+halaman.length;
  $("progI").style.width=((i+1)*100/halaman.length)+"%";
  $("prevBtn").disabled=(i===0);
  $("nextBtn").textContent=(i===halaman.length-1)?"Simpan & Selesai":"Berikutnya \u2192";
  if(dariKlik){
    if(location.hash!=="#hal-"+(i+1)) location.hash="hal-"+(i+1);
    window.scrollTo(0,0);
    if(nama){clearTimeout(timer);simpan();}
  }
}
window.addEventListener("hashchange",function(){
  var p=halDariHash(); if(!isNaN(p) && p!==idx) bukaHalaman(p,false);
});
$("prevBtn").onclick=function(){bukaHalaman(idx-1,true);};
$("nextBtn").onclick=function(){
  if(idx>=halaman.length-1){
    clearTimeout(timer); simpan();
    $("halInfo").textContent="Jawabanmu sudah disimpan. Terima kasih!";
  } else bukaHalaman(idx+1,true);
};
bangunHalaman();
if(!window.ELKPD_EDITOR) muatSoalTambahan();
})();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    app.run(debug=True)