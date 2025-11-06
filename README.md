# SPC Project
docker build -t spc-cloud . && docker run -it --rm --env-file .env -p 8000:8000 spc-cloud
## 🛠️ Stack
- **Backend:** Django + Django REST Framework
- **Frontend:** Django Templates, HTML, CSS, JavaScript
- **API:** Modular (user app)
- **Docker:** Compose for local development
- **Database:** PostgreSQL

---

## 🚀 Jak uruchomić projekt?

1. **Skonfiguruj plik `.env`**
   - Skopiuj `.env.example` do `.env` i uzupełnij dane

2. **Uruchom projekt przez Docker Compose**
   ```bash
   docker compose up -d --build
   ```

3. **Frontend dostępny na:**
   - `http://localhost:6543/`

4. **API dostępne na:**
   - `http://localhost:6543/api/auth/`

---

## 📁 Struktura katalogów

```
frontend/      # Moduł frontendowy (HTML, CSS, JS)
user/          # Moduł API użytkownika (REST)
spc/           # Konfiguracja projektu Django
static/        # Pliki statyczne (CSS, JS)
templates/     # Szablony HTML
```

---

## 🎨 Możliwości frontendu
- Klasyczne szablony Django (HTML, CSS, JS)
- Integracja z API przez JavaScript
- Możliwość podpięcia React/Vue/Angular jako SPA
- Prosty design, animacje, responsywność

---

## 📦 Rozwój
- Dodawaj endpointy w `user/`
- Rozwijaj frontend w `frontend/`

---

## 🧑‍💻 Autor
- Twórca: kacperous
- Rok: 2025

---

## 📚 Przydatne komendy
- Migracje:
  ```bash
  python3 manage.py makemigrations && python3 manage.py migrate
  ```
- Tworzenie superużytkownika:
  ```bash
  python3 manage.py createsuperuser
  ```
- Dostęp do panelu admina:
  - `http://localhost:6543/admin/`

---

## 💡 Notatki
- Frontend komunikuje się z API przez fetch/AJAX
- Całość działa w Dockerze
