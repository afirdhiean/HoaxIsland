# HoaxIsland 🛡️

Asisten pemeriksa fakta dan detektor hoaks ringan untuk Windows dengan antarmuka **Dynamic Island** minimalis di tepi atas layar. Ditenagai oleh **Groq AI** dan pencarian berita real-time **Google News RSS**.

## ✨ Fitur Utama
* **Dynamic Island UX:** Bersembunyi sebagai poni tipis di pojok kiri atas layar dan mengembang halus saat diarahkan kursor atau menerima teks.
* **Verifikasi Instan (`Ctrl + Shift + H`):** Blok teks klaim di browser, WhatsApp Desktop, atau PDF, lalu tekan pintasan keyboard untuk mengeceknya secara otomatis.
* **Drag & Drop:** Seret teks berita langsung ke poni di pojok kiri atas layar.
* **Riset Berita Real-Time:** Menggabungkan analisis LLM Groq dengan rujukan berita terkini beserta tautan langsung ke sumber asli (**Kunjungi Sumber**).
* **Pemantau Kuota Token Real-Time:** Menampilkan pemakaian dan sisa batas harian/menitan Groq API langsung di kartu hasil.
* **BYOK (Bring Your Own Key):** Pengguna dapat memasukkan dan mengganti Groq API Key gratis mereka sendiri langsung dari antarmuka aplikasi.

## 📥 Instalasi (Windows)
1. Buka halaman **[Releases](../../releases)** di repositori ini.
2. Unduh file **`HoaxIsland_Setup.exe`** versi terbaru.
3. Jalankan installer hingga selesai (jika muncul peringatan *Windows SmartScreen*, klik **More info** > **Run anyway**).
4. Saat pertama kali dijalankan, masukkan **Groq API Key** gratis milikmu (bisa dibuat di [console.groq.com/keys](https://console.groq.com/keys)).

## 🛠️ Menjalankan dari Kode Sumber (Untuk Developer)
```bash
git clone [https://github.com/USERNAME_KAMU/HoaxIsland.git](https://github.com/USERNAME_KAMU/HoaxIsland.git)
cd HoaxIsland
pip install -r requirements.txt
python main.py