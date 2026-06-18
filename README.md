# Smart Split Bill AI

Prototype aplikasi web berbasis Streamlit untuk membaca foto nota secara
OCR-free, mengekstrak data transaksi, dan membagi tagihan kepada beberapa
orang.

**Created by: Hami Ahqafi**

Eksperimen dilakukan pada dua foto nota nyata dengan dua vision-language model.
Raw output, waktu inference, dan tabel ringkasan disimpan pada
[`docs/results`](docs/results).

## Daftar Isi

- [Latar Belakang](#latar-belakang)
- [Fitur Prototype](#fitur-prototype)
- [Struktur Project](#struktur-project)
- [Instalasi dan Menjalankan Aplikasi](#instalasi-dan-menjalankan-aplikasi)
- [Riset dan Perbandingan Model](#riset-dan-perbandingan-model)
- [Menjalankan Eksperimen Dua Nota](#menjalankan-eksperimen-dua-nota)
- [Contoh Hasil Pembacaan](#contoh-hasil-pembacaan)
- [Alasan Pemilihan Model](#alasan-pemilihan-model)
- [Evaluasi Model Pembaca Bill](#evaluasi-model-pembaca-bill)
- [Evaluasi Produk Web](#evaluasi-produk-web)
- [Pengujian](#pengujian)
- [Keamanan](#keamanan)

## Latar Belakang

Smart Split Bill dikembangkan sebagai proof of concept untuk membantu pengguna:

1. Mengubah foto nota menjadi data transaksi terstruktur.
2. Memeriksa dan mengoreksi hasil pembacaan AI.
3. Menentukan orang yang menikmati setiap item.
4. Membagi pajak, service charge, diskon, dan biaya lainnya.
5. Memastikan total tagihan semua orang sama persis dengan total pada nota.

## Fitur Prototype

- Upload nota dalam format JPG, JPEG, PNG, atau WebP.
- Pembacaan nota menggunakan model vision tanpa EasyOCR atau PyTesseract.
- Dukungan Hugging Face Inference Providers, Groq Vision, dan OpenAI Vision.
- Ekstraksi:
  - nama merchant;
  - nama item;
  - jumlah item;
  - harga per item;
  - total harga item;
  - subtotal;
  - pajak, service charge, diskon, dan biaya tambahan;
  - total bill.
- Hasil ekstraksi dapat diedit untuk mengatasi kesalahan AI.
- Peringatan otomatis jika jumlah item, subtotal, charges, dan total bill tidak
  konsisten secara aritmetika.
- Input beberapa peserta.
- Satu item dapat dipilih oleh satu atau beberapa peserta.
- Biaya tambahan dibagi proporsional berdasarkan nilai item yang dikonsumsi.
- Penanganan sisa pembulatan secara deterministik.
- Validasi bahwa jumlah tagihan seluruh peserta sama dengan total bill.
- Download hasil pembagian dalam format JSON.
- Mode demo jika API tidak tersedia.

## Struktur Project

```text
.
├── app.py                         # Antarmuka Streamlit
├── smart_split/
│   ├── ai.py                      # Integrasi model vision
│   ├── models.py                  # Normalisasi data receipt
│   └── splitter.py                # Algoritma pembagian bill
├── scripts/
│   └── benchmark_models.py        # Benchmark dua model pada dua nota
├── docs/
│   ├── receipts/                  # Simpan dua foto nota di sini
│   └── results/                   # Output benchmark tersimpan di sini
├── tests/
│   └── test_splitter.py
├── requirements.txt
└── .env.example
```

## Instalasi dan Menjalankan Aplikasi

### 1. Clone repository

```bash
git clone <URL_REPOSITORY_GITHUB>
cd smart-split-bill-ai
```

### 2. Buat virtual environment

Python 3.11 atau 3.12 direkomendasikan.

```bash
python3.12 -m venv venv312
source venv312/bin/activate
```

Untuk Windows:

```powershell
venv312\Scripts\activate
```

### 3. Install dependency

```bash
pip install -r requirements.txt
```

### 4. Siapkan API token

```bash
cp .env.example .env
```

Isi salah satu provider pada `.env`:

```env
HF_TOKEN=hf_your_token
GROQ_API_KEY=gsk_your_key
OPENAI_API_KEY=sk_your_key
OPENAI_MODEL=gpt-4.1-mini
```

Untuk Hugging Face, gunakan fine-grained token dengan izin **Make calls to
Inference Providers**. Jangan mengunggah `.env` ke GitHub.

### 5. Jalankan Streamlit

```bash
streamlit run app.py
```

Buka `http://localhost:8501`.

## Riset dan Perbandingan Model

Assignment mensyaratkan minimal dua model OCR-free. Model yang dibandingkan:

### Model 1 — Qwen3-VL-8B-Instruct

- Model ID: `Qwen/Qwen3-VL-8B-Instruct:fastest`
- Jenis: vision-language model.
- Eksekusi: Hugging Face Inference Providers.
- Alasan diuji:
  - dapat menerima gambar dan instruksi teks secara langsung;
  - dapat diminta menghasilkan JSON sesuai schema;
  - ukuran lebih kecil daripada varian Qwen VL yang lebih besar;
  - sesuai untuk nota dengan format yang bervariasi.

### Model 2 — Aya Vision 32B

- Model ID: `CohereLabs/aya-vision-32b:fastest`
- Jenis: multilingual vision-language model.
- Eksekusi: Hugging Face Inference Providers.
- Alasan diuji:
  - kemampuan multilingual relevan untuk nota Indonesia;
  - dapat membaca gambar sekaligus mengikuti instruksi ekstraksi;
  - menjadi pembanding model yang lebih besar terhadap Qwen3-VL-8B.

### Model tambahan yang dipertimbangkan

`naver-clova-ix/donut-base-finetuned-cord-v2` adalah model OCR-free yang
di-fine-tune untuk receipt pada dataset CORD. Model ini sangat relevan secara
domain, tetapi umumnya perlu dijalankan secara lokal/Colab atau menggunakan
endpoint khusus. Donut dapat dijadikan eksperimen lanjutan untuk membandingkan
model khusus receipt dengan vision-language model general-purpose.

### Kriteria evaluasi

| Kriteria | Cara evaluasi |
|---|---|
| Kelengkapan item | Bandingkan jumlah item ground truth dan hasil model |
| Nama item | Periksa apakah teks utama item terbaca benar |
| Quantity | Bandingkan jumlah item per baris |
| Harga | Bandingkan unit price dan total item |
| Komponen bill | Periksa subtotal, pajak, service, diskon, dan total |
| Konsistensi aritmetika | Periksa subtotal dan total terhadap komponennya |
| Validitas output | Periksa apakah output dapat diparsing sebagai JSON |
| Kecepatan | Catat durasi inference setiap gambar dalam detik |
| Stabilitas | Catat error API, output kosong, atau format tidak konsisten |

## Menjalankan Eksperimen Dua Nota

### 1. Tambahkan gambar

Simpan dua foto nota sebagai:

```text
docs/receipts/receipt_1.jpg
docs/receipts/receipt_2.jpg
```

Gambar sebaiknya fokus, terang, dan tidak memuat data pribadi sensitif.

### 2. Jalankan benchmark

```bash
python scripts/benchmark_models.py \
  docs/receipts/receipt_1.jpg \
  docs/receipts/receipt_2.jpg
```

Script akan menjalankan dua model pada dua gambar yang sama dan menyimpan:

```text
docs/results/benchmark_results.json
docs/results/model_comparison.csv
```

Setiap hasil berisi nama model, nama gambar, durasi inference, status, dan data
receipt yang berhasil diekstrak. File ini dapat langsung disertakan dalam
repository sebagai bukti eksperimen.

## Contoh Hasil Pembacaan

Ground truth dibuat dengan membaca nota secara manual, kemudian dibandingkan
dengan output model. Detail ground truth tersedia di
[`ground_truth.json`](docs/results/ground_truth.json), sedangkan output lengkap
model tersedia di
[`benchmark_results.json`](docs/results/benchmark_results.json).

### Nota 1

![Nota 1](docs/receipts/receipt_1.jpg)

Nota Tom Sushi memiliki sembilan baris transaksi dengan total quantity 23.

| Field | Ground truth | Qwen3-VL-8B | Aya Vision 32B |
|---|---:|---:|---:|
| Baris item | 9 | 9 | 10 |
| Baris item tepat | 9 | 8 | 6 |
| Subtotal | Rp369.000 | Rp369.000 | Rp1.845.000 |
| Service charge | Rp18.450 | Rp18.450 | Rp92.250 |
| Pajak | Rp38.745 | Rp38.745 | Rp184.500 |
| Total | Rp426.195 | Rp426.195 | Rp2.121.750 |
| Waktu inference | - | 12,380 detik | 17,506 detik |

Temuan kualitatif:

- Qwen menemukan semua baris, merchant, subtotal, biaya tambahan, dan total.
- Qwen salah menafsirkan satu baris `Cold Ocha`: harga total Rp6.000 dianggap
  sebagai harga satuan sehingga total item menjadi Rp12.000.
- Nama `Chx Karaage Mentai Rice` terbaca sebagai `Chx Karage Mental Rice`.
- Aya mengalami *column shifting* mulai bagian bawah daftar. Nilai Blue, Black,
  dan subtotal berpindah menjadi harga satuan/total item, sehingga hasil
  aritmetika akhirnya jauh dari nota.

### Nota 2

![Nota 2](docs/receipts/receipt_2.jpg)

Nota Santuy Mart memiliki tujuh jenis item. Foto berisi anotasi putih
`3 pcs x 8000`, `24000`, `76000`, dan `100000`. Nilai Rp100.000 adalah uang
yang dibayarkan, bukan total transaksi.

| Field | Ground truth | Qwen3-VL-8B | Aya Vision 32B |
|---|---:|---:|---:|
| Baris item | 7 | 7 | 6 |
| Baris item tepat | 7 | 7 | 5 |
| Subtotal | Rp76.000 | Rp76.000 | Rp76.000 |
| Biaya tambahan | Rp0 | Rp0 | Rp0 |
| Total bill | Rp76.000 | Rp100.000 | Rp76.000 |
| Waktu inference | - | 10,971 detik | 11,045 detik |

Temuan kualitatif:

- Qwen menemukan seluruh tujuh item beserta quantity dan harga dengan tepat.
- Qwen menganggap angka anotasi `100000`/paid amount sebagai total bill,
  walaupun subtotal item sudah benar Rp76.000.
- Aya menghasilkan subtotal dan total yang benar, tetapi menggabungkan
  `Kaki Tiga Kaleng Jeruk` dan `Larutan Cap Kaki Tiga Strawberry`. Akibatnya
  hanya enam baris yang dikembalikan.
- Anotasi pada gambar terbukti dapat membantu membaca bagian tertutup, tetapi
  juga berpotensi mengubah interpretasi model.

### Ringkasan komparasi

| Model | Rata-rata inference | Kelengkapan item | Akurasi summary bill |
|---|---:|---|---|
| Qwen3-VL-8B | 11,68 detik | 15/16 baris tepat | 1 nota sepenuhnya tepat; 1 salah total |
| Aya Vision 32B | 14,28 detik | 11/16 baris tepat | 1 nota tepat; 1 gagal berat |

Qwen sekitar **18,2% lebih cepat** dalam eksperimen ini. Angka tersebut adalah
latency end-to-end melalui Hugging Face Inference Providers, sehingga turut
dipengaruhi jaringan, antrean provider, dan cold start.

## Alasan Pemilihan Model

Model yang dipilih untuk prototype adalah
`Qwen/Qwen3-VL-8B-Instruct:fastest`.

Pemilihan ini didasarkan pada hasil eksperimen:

1. Mendukung input gambar tanpa pipeline OCR eksternal.
2. Mampu mengikuti prompt dan menghasilkan struktur JSON yang dibutuhkan UI.
3. Menghasilkan 15 dari 16 baris item dengan benar, dibanding Aya 11 dari 16.
4. Membaca nota Tom Sushi yang lebih padat secara jauh lebih stabil.
5. Rata-rata inference 11,68 detik, sekitar 18,2% lebih cepat dari Aya.
6. Ukuran 8B lebih efisien dibanding model pembanding 32B.
7. Dapat digunakan melalui Hugging Face Inference Providers sehingga deployment
   Streamlit tidak perlu memuat model besar di RAM lokal.

Kelemahan Qwen pada total nota kedua ditangani pada produk dengan menyediakan
editor hasil ekstraksi dan peringatan otomatis jika jumlah item, subtotal,
charges, dan total bill tidak konsisten. Prompt juga membedakan `TOTAL` dari
`CASH/PAID AMOUNT`, meskipun eksperimen menunjukkan prompt saja belum selalu
cukup untuk gambar yang memiliki anotasi besar.

## Evaluasi Model Pembaca Bill

### Kelebihan

- OCR-free: gambar diproses langsung oleh vision-language model.
- Schema prompt membuat hasil lebih mudah dipakai aplikasi.
- Provider API mengurangi kebutuhan GPU lokal.
- Output masih dapat dikoreksi pengguna jika model melakukan kesalahan.

### Kelemahan

- Model dapat salah membaca font kecil, nota buram, singkatan, atau kolom yang
  berhimpitan.
- Model dapat menukar harga satuan dengan total item.
- Qwen salah membedakan total bill dengan paid amount pada nota kedua.
- Aya mengalami column shifting pada nota pertama dan menggabungkan dua produk
  pada nota kedua.
- Output JSON dari model generatif tidak selalu konsisten.
- Latency dan ketersediaan bergantung pada provider eksternal.
- Model general-purpose tidak secara khusus dilatih untuk semua format receipt
  Indonesia.
- Evaluasi dua gambar masih terlalu kecil untuk menyimpulkan performa umum.
- Hasil antar-run dapat berubah meskipun temperature dibuat nol karena routing
  provider dan implementasi model tidak selalu deterministik.

### Ide perbaikan

- Tambahkan preprocessing: auto-rotate, crop, perspective correction, contrast,
  dan resize.
- Jika `total != subtotal + charges`, tampilkan peringatan dan minta model
  melakukan ekstraksi ulang khusus pada bagian total.
- Gunakan constrained/structured generation jika provider mendukung JSON
  schema.
- Fine-tune Donut atau model document understanding pada nota Indonesia.
- Bangun dataset uji dengan variasi minimarket, restoran, e-commerce, font,
  kondisi cahaya, dan tingkat kemiringan.
- Tambahkan confidence score dan tandai field yang perlu diperiksa pengguna.
- Gunakan retry prompt khusus ketika schema atau aritmetika tidak valid.

## Evaluasi Produk Web

### Kelebihan

- Alur aplikasi mengikuti proses pengguna: upload, verifikasi, pilih peserta,
  assign item, dan lihat total.
- Semua field hasil model dapat diedit.
- Satu item dapat dibagi kepada beberapa orang.
- Pajak dan service dibagi proporsional terhadap konsumsi.
- Algoritma memakai integer unit terkecil sehingga pembulatan tidak membuat
  total akhir berbeda dari total bill.
- Terdapat mode demo dan export JSON.

### Kelemahan dan potensi bug

- Belum ada autentikasi atau penyimpanan riwayat transaksi.
- State akan hilang ketika session Streamlit berakhir.
- Assignment peserta masih dilakukan per item, belum mendukung pembagian
  quantity yang berbeda dalam satu baris.
- Biaya tambahan saat ini dibagi proporsional; beberapa kasus mungkin
  membutuhkan pembagian rata atau aturan khusus.
- Belum ada export PDF, gambar ringkasan, atau share link.
- Pengguna masih perlu memahami dan menyediakan API token.
- Belum ada deployment publik dan pengujian multi-user.

### Ide perbaikan

- Tambahkan database untuk riwayat bill.
- Sediakan pilihan pembagian biaya: proporsional, rata, atau custom.
- Tambahkan split berdasarkan quantity, persentase, dan nominal manual.
- Tambahkan login serta link bill yang dapat dibagikan.
- Tambahkan export PDF/WhatsApp-friendly summary.
- Terapkan validasi schema dan indikator field bermasalah pada UI.
- Deploy ke Streamlit Community Cloud atau platform container.
- Tambahkan integration test untuk upload gambar hingga hasil pembagian.

## Pengujian

Jalankan:

```bash
pytest -q
```

Test saat ini mencakup:

- pembagian nominal yang tidak habis dibagi;
- rekonsiliasi total seluruh peserta dengan total bill;
- pembagian diskon bernilai negatif.

## Keamanan

- File `.env` masuk `.gitignore`.
- `.env.example` hanya berisi placeholder.
- API token tidak boleh ditulis di source code, notebook, screenshot, output,
  issue GitHub, atau README.
- Jika token pernah terpublikasi, revoke dan buat token baru.

## Lisensi dan Penggunaan

Project ini dibuat sebagai proof of concept assignment. Periksa lisensi dan
ketentuan penggunaan setiap model sebelum penggunaan produksi.
