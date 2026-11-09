---
title: Database Penyewa Lahan PT Perikanan Indonesia
emoji: 🏢
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# Sistem Database Penyewa Lahan Terintegrasi
### PT Perikanan Indonesia (Persero)

Aplikasi web terpadu untuk pengelolaan, pemantauan, dan pelaporan aset lahan yang disewakan kepada mitra di seluruh unit dan cabang pelabuhan PT Perikanan Indonesia.

---

## 🌟 Fitur Utama

1. **Dashboard Eksekutif Real-time**:
   - Rekapitulasi jumlah sertifikat tanah induk, total luas lahan ($m^2$), jumlah bidang/kavling, jumlah mitra penyewa aktif, luas yang disewakan, luas tersedia, dan estimasi potensi pendapatan sewa per cabang.
   - Grafik tingkat okupansi lahan dan persentase luas terpetakan.
   - Peringatan dini (*early warning system*) untuk kontrak sewa yang akan jatuh tempo dalam kurun waktu kurang dari 12 bulan atau yang telah lewat jatuh tempo.

2. **Master Cabang**:
   - Manajemen data seluruh cabang pelabuhan dan unit kerja (Jakarta PPSNZJ, Belawan, Pekalongan, Tegal, Prigi, Pati, Mayangan, Rembang, Benoa, Sukabumi, Sorong, Ambon, Kendari, Bitung, Banjarmasin).

3. **Master Sertifikat Tanah Induk**:
   - Pencatatan nomor sertifikat alas hak (HPL No. 1, HP 128, HGB, dll.), jenis hak, lokasi kawasan, luas total ($m^2$), masa berlaku sertifikat, nomor akte legalitas, kondisi aset, serta fitur upload dan preview scan dokumen fisik (PDF).

4. **Master Bidang Lahan (Kavling)**:
   - Pembagian bidang lahan di atas sertifikat induk dengan validasi luas tanah secara *real-time* (mencegah akumulasi luas bidang melampaui luas sertifikat induk).
   - Pencatatan status pemanfaatan (*Disewakan, Belum Disewakan, Dipakai Sendiri*).

5. **Master Penyewa (Mitra Kerja Sama)**:
   - Data mitra (Badan Usaha PT/CV/Koperasi maupun Perorangan), penandatangan, NPWP, alamat kavling, status hak (HGB / Non HGB), dan peruntukan usaha (Cold Storage, Pengolahan Ikan, Galangan Kapal, dll.).
   - Setiap penyewa terhubung secara hierarkis ke bidang lahan dan sertifikat tanah induknya.
   - Indikator sisa periode sewa: Aktif (hijau), Mendekati Berakhir (kuning/oranye), atau Sudah Berakhir (merah).

6. **Master Perjanjian & Komersial**:
   - Pencatatan nomor kontrak perjanjian sewa, masa sewa (tahun), tanggal mulai dan berakhir.
   - Rincian tarif komersial: *Development Contribution* (DC), *Service Charge* (SC/tahun), Biaya Administrasi, Total Nilai Kontrak, dan Deposit Jaminan (5%).
   - Rekening bank penampung (BNI Cabang Roa Malaka) dan upload berkas kontrak pindaian (PDF).

7. **Riwayat Perpanjangan & Pengalihan Penyewa**:
   - Fitur 1-klik perpanjangan kontrak sewa yang otomatis mengarsipkan kontrak sebelumnya dan mencatat riwayat addendum.
   - Modul pencatatan mutasi/pengalihan hak sewa lahan antar mitra dengan dasar surat persetujuan Direksi dan dokumen notariil.

8. **Monitoring & Peringatan Dini**:
   - Pengelompokan kontrak: Jatuh Tempo/Lewat, Berakhir dalam < 12 Bulan, dan Kontrak Aktif Normal.
   - Monitoring tingkat keterisian (*occupancy rate*) tanah per sertifikat induk.

9. **Laporan, Filter, & Export Excel/PDF**:
   - Penyaringan data multi-kriteria (berdasarkan cabang, status sewa, kata kunci).
   - Ekspor data lengkap ke format Microsoft Excel (`.xlsx`) siap pakai dengan styling rapi.
   - Cetak laporan rekapitulasi ke format PDF.

10. **Sinkronisasi Data (Import Excel)**:
    - Fitur impor data dari berkas Excel master sewa aset PT Perikanan Indonesia untuk sinkronisasi berkala dari kantor cabang ke kantor pusat.

11. **Hak Akses Berjenjang (Role-Based Access Control)**:
    - **Kantor Pusat (`pusat`)**: Akses penuh ke seluruh data cabang se-Indonesia, manajemen pengguna, import data master, dan rekapitulasi nasional.
    - **Kantor Cabang (`cabang`)**: Akses terisolasi khusus ke data cabang masing-masing untuk menjaga kerahasiaan dan integritas data lokal.

---

## 🔑 Kredensial Login Bawaan

| Akun | Username | Password | Hak Akses | Cakupan Wilayah |
| :--- | :--- | :--- | :--- | :--- |
| **Kantor Pusat** | `admin` | `admin123` | Administrator | Seluruh Cabang (Nasional) |
| **Cabang Jakarta** | `jakarta` | `jakarta123` | Operator Cabang | Khusus Cabang Jakarta (PPSNZJ) |
| **Cabang Belawan** | `belawan` | `belawan123` | Operator Cabang | Khusus Cabang Belawan |

---

## 🚀 Cara Menjalankan Aplikasi

### Opsi A: Di Komputer Lokal
1. Buka folder aplikasi di:
   `C:\Users\Asus Vivobook\.gemini\antigravity\scratch\db-penyewa-lahan`
2. Klik ganda file **`start_app.bat`**.
3. Browser akan otomatis terbuka ke alamat: **`http://127.0.0.1:8080`**

### Opsi B: Online 24 Jam di Cloud (Hugging Face Spaces)
1. Klik ganda file **`deploy_to_hf.bat`**.
2. Masukkan Token Hugging Face Anda.
3. Aplikasi akan otomatis ter-deploy ke Cloud dan aktif 24 jam nonstop dengan tautan HTTPS publik.
