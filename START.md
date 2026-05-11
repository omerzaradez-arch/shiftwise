# ShiftWise — איך להתחיל

## דרישות מקדימות
- Python 3.12+
- Node.js 20+
- Docker Desktop (לקל ביותר)
- OR: PostgreSQL 16 + Redis מותקנים locally

---

## אפשרות א׳ — Docker (הכי מהיר)

```bash
cd shiftwise

# העתק קבצי env
cp backend/.env.example backend/.env
cp frontend/.env.local.example frontend/.env.local

# הפעל הכל
docker-compose up --build

# בטרמינל נפרד — Seed נתוני דמו
docker-compose exec backend python seed.py
```

פתח בדפדפן:
- Frontend: http://localhost:3000
- API Docs: http://localhost:8000/docs

---

## אפשרות ב׳ — Local Development

### Backend

```bash
cd shiftwise/backend

# צור virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# התקן תלויות
pip install -r requirements.txt

# הגדר env
cp .env.example .env
# ערוך .env לפי הגדרות ה-DB שלך

# הרץ migrations
alembic upgrade head

# Seed נתוני דמו
python seed.py

# הפעל שרת
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd shiftwise/frontend

# התקן תלויות
npm install

# הגדר env
cp .env.local.example .env.local

# הפעל שרת פיתוח
npm run dev
```

---

## כניסה למערכת

| משתמש | טלפון | סיסמה | תפקיד |
|--------|-------|-------|--------|
| יוסי כהן | 0501111111 | 1234 | מנהל |
| שרה לוי | 0502222222 | 1234 | עובד בכיר |
| ריבה אברהם | 0504444444 | 1234 | עובד |

---

## תהליך עבודה ראשון

1. **כנס כעובד** → שלח זמינות לשבוע הבא
2. **כנס כמנהל** → לחץ "הרץ אופטימייזר"
3. **צפה בסידור** שנוצר אוטומטית
4. **ערוך ידנית** אם צריך (drag & drop)
5. **פרסם** לעובדים

---

## מבנה הפרויקט

```
shiftwise/
├── frontend/          Next.js 14 + shadcn/ui
│   └── src/
│       ├── app/       Pages (App Router)
│       ├── components/
│       ├── lib/api/   API clients
│       ├── stores/    Zustand state
│       └── types/     TypeScript types
├── backend/           FastAPI + OR-Tools
│   └── app/
│       ├── api/v1/    REST endpoints
│       ├── core/      Business logic
│       │   └── scheduler/  Optimizer engine
│       ├── models/    SQLAlchemy models
│       └── tasks/     Celery tasks
├── docker-compose.yml
└── START.md           ← אתה כאן
```

---

## השלבים הבאים לפיתוח

- [ ] WebSocket לעדכונים חיים
- [ ] PDF export לסידור
- [ ] Celery Beat לתזמון אוטומטי
- [ ] דף analytics מלא
- [ ] ממשק ניהול עובדים
- [ ] Push notifications
- [ ] WhatsApp Bot integration
