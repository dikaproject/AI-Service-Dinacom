# AI-Service-Dinacom

## Deskripsi
Proyek ini menyediakan layanan AI dengan FastAPI dan Uvicorn untuk kebutuhan kompetisi.

## Persiapan (Windows)

1. Pastikan Python sudah terinstall.
2. Buat virtual environment:
   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```

3. Install dependensi:
   ```bash
   pip install -r requirements.txt
   ```

4. Jalankan server:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

## Troubleshooting

### Warning - "ModuleNotFoundError: No module named 'google_search_results'"

Jika mengalami error di atas, coba:
```bash
pip uninstall google-search-results
pip install google-search-results
```

## Account ( Simple Testing )

Link Demo Website : https://dinacom.intechofficial.com

---
- email : admin@gmail.com (Demo Admin)
- passsword : password123
---
- email : dikagilang2007@gmail.com (Demo User)
- password : Dika#3321
---
- email : dika@gmail.com (Demo Doctor)
- password : password

---
