import os
import sys
import json
import re
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from groq import Groq

STOPWORDS_ID = {
    "yang", "dan", "di", "ke", "dari", "ini", "itu", "untuk", "dengan", "pada",
    "adalah", "akan", "juga", "atau", "bahwa", "beredar", "kabar", "informasi",
    "berita", "viral", "sebuah", "dalam", "tidak", "bisa", "dapat", "secara",
    "karena", "oleh", "setelah", "sebelum", "saat", "ketika", "langsung", "seketika"
}


def dapatkan_path_config_appdata() -> str:
    """Mengembalikan lokasi penyimpanan config.env di folder AppData pengguna."""
    appdata = os.environ.get("APPDATA") or os.path.expanduser("~")
    folder_config = os.path.join(appdata, "HoaxIsland")
    os.makedirs(folder_config, exist_ok=True)
    return os.path.join(folder_config, "config.env")


def simpan_api_key(api_key: str) -> bool:
    """Menyimpan Groq API Key milik pengguna secara permanen di AppData."""
    kunci_bersih = api_key.strip().strip('"').strip("'")
    try:
        path_config = dapatkan_path_config_appdata()
        with open(path_config, "w", encoding="utf-8") as f:
            f.write(f"GROQ_API_KEY={kunci_bersih}\n")
        return True
    except Exception:
        return False


def _baca_key_dari_file(path_file: str) -> str:
    if not os.path.exists(path_file):
        return ""
    try:
        with open(path_file, "r", encoding="utf-8") as f:
            for baris in f:
                baris = baris.strip()
                if not baris or baris.startswith("#") or "=" not in baris:
                    continue
                nama, nilai = baris.split("=", 1)
                if nama.strip() == "GROQ_API_KEY":
                    kandidat = nilai.strip().strip('"').strip("'")
                    if kandidat and kandidat != "TEMPEL_GROQ_API_KEY_KAMU_DI_SINI":
                        return kandidat
    except Exception:
        pass
    return ""


def muat_api_key() -> str:
    """Membaca GROQ_API_KEY dari AppData pengguna, .env lokal, atau environment sistem."""
    kunci_appdata = _baca_key_dari_file(dapatkan_path_config_appdata())
    if kunci_appdata:
        return kunci_appdata

    kandidat_folder = []
    if getattr(sys, "frozen", False):
        kandidat_folder.append(os.path.dirname(sys.executable))
    kandidat_folder.append(os.path.dirname(os.path.abspath(__file__)))

    for folder in kandidat_folder:
        kunci_lokal = _baca_key_dari_file(os.path.join(folder, ".env"))
        if kunci_lokal:
            return kunci_lokal

    return os.environ.get("GROQ_API_KEY", "").strip()


def ekstrak_kata_kunci(teks: str, maks_kata: int = 7) -> str:
    bersih = "".join(c if c.isalnum() or c.isspace() else " " for c in teks.lower())
    kata_penting = [k for k in bersih.split() if k not in STOPWORDS_ID and len(k) > 2]
    return " ".join(kata_penting[:maks_kata]) if kata_penting else teks[:60]


def cari_referensi_berita(teks_klaim: str, maks_hasil: int = 5) -> str:
    kata_kunci = ekstrak_kata_kunci(teks_klaim)
    encoded_q = urllib.parse.quote(kata_kunci)
    url = f"https://news.google.com/rss/search?q={encoded_q}&hl=id&gl=ID&ceid=ID:id"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})

    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            xml_data = resp.read()
        root = ET.fromstring(xml_data)
        items = root.findall(".//item")[:maks_hasil]
        if not items:
            return "Tidak ditemukan artikel berita spesifik untuk kata kunci ini."

        daftar_berita = []
        for idx, item in enumerate(items, 1):
            judul = item.findtext("title", default="").strip()
            tautan = item.findtext("link", default="").strip()
            tanggal = item.findtext("pubDate", default="").strip()
            sumber_el = item.find("source")
            sumber = sumber_el.text.strip() if (sumber_el is not None and sumber_el.text) else "Media Online"
            daftar_berita.append(
                f"{idx}. [{sumber} | {tanggal}] {judul}\n   URL: {tautan}"
            )
        return "\n".join(daftar_berita)
    except Exception as e:
        return f"Pencarian berita tidak tersedia sementara ({e})"


def dapatkan_daftar_model(client: Groq) -> list[str]:
    kandidat = []
    kata_terlarang = ("whisper", "tts", "guard", "vision", "embed", "safeguard", "orpheus", "playai")
    try:
        for m in client.models.list().data:
            nama = getattr(m, "id", "")
            if not nama or any(k in nama.lower() for k in kata_terlarang):
                continue
            kandidat.append(nama)
    except Exception:
        pass

    def prioritas(nama: str) -> tuple:
        n = nama.lower()
        if "70b" in n or "120b" in n:
            return (0, n)
        if "llama" in n or "qwen" in n or "gpt-oss" in n:
            return (1, n)
        return (2, n)

    kandidat.sort(key=prioritas)
    return kandidat if kandidat else ["llama-3.1-8b-instant"]


def ekstrak_json(teks: str) -> dict:
    teks_bersih = re.sub(r"<think>.*?</think>", "", teks, flags=re.DOTALL).strip()
    try:
        return json.loads(teks_bersih)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", teks_bersih, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise


def _ekstrak_info_kuota(headers, completion) -> str:
    """Membaca sisa kuota real-time dari HTTP headers Groq & penggunaan token."""
    bagian = []

    usage = getattr(completion, "usage", None)
    total_pakai = getattr(usage, "total_tokens", None) if usage else None
    if total_pakai is not None:
        try:
            bagian.append(f"Pakai: {int(total_pakai):,} token")
        except (ValueError, TypeError):
            pass

    sisa_tpm = headers.get("x-ratelimit-remaining-tokens")
    batas_tpm = headers.get("x-ratelimit-limit-tokens")
    if sisa_tpm and batas_tpm:
        try:
            bagian.append(f"Sisa Menit: {int(float(sisa_tpm)):,}/{int(float(batas_tpm)):,} TPM")
        except (ValueError, TypeError):
            pass

    sisa_rpd = headers.get("x-ratelimit-remaining-requests")
    batas_rpd = headers.get("x-ratelimit-limit-requests")
    if sisa_rpd and batas_rpd:
        try:
            bagian.append(f"Harian: {int(float(sisa_rpd)):,}/{int(float(batas_rpd)):,} req")
        except (ValueError, TypeError):
            pass

    return " · ".join(bagian)


def cek_fakta(teks_klaim: str) -> dict:
    api_key = muat_api_key()
    if not api_key:
        return {
            "status": "API KEY BELUM DIATUR",
            "ringkasan": "Silakan masukkan Groq API Key gratis Anda terlebih dahulu agar aplikasi dapat memverifikasi klaim.",
            "sumber": "-",
            "url": "",
            "is_direct_url": False,
            "butuh_api_key": True,
            "kuota": ""
        }

    client = Groq(api_key=api_key)
    hasil_pencarian = cari_referensi_berita(teks_klaim)

    instruksi_sistem = (
        "Kamu adalah sistem pemeriksa fakta (fact-checker) berbahasa Indonesia yang objektif, netral, dan akurat. "
        "Gunakan referensi berita yang diberikan bersama pengetahuan faktualmu untuk memverifikasi klaim. "
        "Balas HANYA dengan objek JSON valid menggunakan 4 kunci berikut tanpa teks tambahan di luar JSON:\n"
        '{\n'
        '  "status": "Pilih salah satu: FAKTA, HOAKS, MENYESATKAN, atau BELUM TERVERIFIKASI",\n'
        '  "ringkasan": "Penjelasan singkat, jelas, dan padat (1-2 kalimat) mengenai alasan status tersebut",\n'
        '  "sumber": "Nama media kredibel atau lembaga resmi yang menjadi rujukan",\n'
        '  "url": "Salin persis URL artikel dari daftar referensi yang paling relevan, atau kosongkan (\\"\\") jika tidak ada yang cocok"\n'
        '}'
    )

    prompt_pengguna = (
        f"KLAIM YANG DIPERIKSA:\n{teks_klaim}\n\n"
        f"REFERENSI BERITA TERKAIT DARI INTERNET:\n{hasil_pencarian}"
    )

    daftar_model = dapatkan_daftar_model(client)
    parsed = None
    info_kuota = ""
    error_terakhir = None

    for nama_model in daftar_model[:5]:
        try:
            try:
                raw_resp = client.chat.completions.with_raw_response.create(
                    model=nama_model,
                    messages=[
                        {"role": "system", "content": instruksi_sistem},
                        {"role": "user", "content": prompt_pengguna},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.1,
                )
            except Exception as err_json:
                if "400" in str(err_json) or "json" in str(err_json).lower():
                    raw_resp = client.chat.completions.with_raw_response.create(
                        model=nama_model,
                        messages=[
                            {"role": "system", "content": instruksi_sistem},
                            {"role": "user", "content": prompt_pengguna},
                        ],
                        temperature=0.1,
                    )
                else:
                    raise err_json

            response = raw_resp.parse()
            info_kuota = _ekstrak_info_kuota(raw_resp.headers, response)
            hasil_mentah = response.choices[0].message.content.strip()
            parsed = ekstrak_json(hasil_mentah)
            break
        except Exception as e:
            error_terakhir = e
            parsed = None

    if parsed is None:
        pesan_err = str(error_terakhir)
        return {
            "status": "ERROR",
            "ringkasan": f"Gagal memproses verifikasi: {pesan_err}",
            "sumber": "-",
            "url": "",
            "is_direct_url": False,
            "butuh_api_key": "401" in pesan_err or "invalid_api_key" in pesan_err.lower(),
            "kuota": ""
        }

    status = str(parsed.get("status", "BELUM TERVERIFIKASI")).strip().upper()
    ringkasan = str(parsed.get("ringkasan", "")).strip()
    sumber = str(parsed.get("sumber", "Analisis AI & Berita Web")).strip()
    url_artikel = str(parsed.get("url", "")).strip()

    if not ringkasan:
        ringkasan = "AI tidak memberikan rincian penjelasan untuk klaim ini."

    is_direct_url = url_artikel.startswith("http://") or url_artikel.startswith("https://")
    if not is_direct_url:
        kata_kunci = ekstrak_kata_kunci(teks_klaim)
        url_artikel = f"https://www.google.com/search?q={urllib.parse.quote(kata_kunci)}"

    return {
        "status": status,
        "ringkasan": ringkasan,
        "sumber": sumber if sumber else "Analisis AI & Berita Web",
        "url": url_artikel,
        "is_direct_url": is_direct_url,
        "butuh_api_key": False,
        "kuota": info_kuota
    }