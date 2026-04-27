# Fintrix Running Instructions

## 1. Push to GitHub
Run these commands in the root directory:
```powershell
git init
git remote add origin https://github.com/nishankkhadpe7-afk/FintrixA.git
git add .
git commit -m "Fix login inconsistency, AI agent topic guard, and news seeding"
git push -u origin main
```

## 2. Run Backend
Run these commands in the `Backend/fintrix-api` directory:
```powershell
cd Backend/fintrix-api
# Ensure your virtual environment is active
.\venv\Scripts\activate
# Start the FastAPI server
python -m uvicorn backend.main:app --reload
```
The backend will be available at `http://127.0.0.1:8000`.

## 3. Run Frontend
Run these commands in the `Frontend/fintrix-web` directory:
```powershell
cd Frontend/fintrix-web
# Install dependencies if not already done
npm install
# Start the Next.js dev server
npm run dev
```
The frontend will be available at `http://127.0.0.1:3000`.

---
**Note**: The agent was unable to execute these commands directly due to environment security restrictions (sandboxing) on this Windows system.
