# RegTech Application - Quick Start Guide

## ⚡ Quick Start (Windows)

### Option 1: Using Batch Scripts (Easiest! 🎯)

1. **Open two Command Prompts**

2. **In first prompt, run:**

   ```bash
   start_backend.bat
   ```

   Expected: `INFO:     Application startup complete`

3. **In second prompt, run:**

   ```bash
   start_frontend.bat
   ```

   Expected: `VITE v... ready in ... ms`

4. **Open browser:** http://localhost:3000

5. **Hard refresh:** Ctrl+F5

Done! Both servers auto-start on correct ports.

---

### Option 2: Manual Commands (If scripts don't work)

**Terminal 1 - Backend:**

```bash
cd <project-root>
uvicorn api.main:app --reload --port 8001
```

**Terminal 2 - Frontend:**

```bash
cd <project-root>/frontend
npm run dev
```

---

## 🔧 Important Notes

### ⚠️ CRITICAL: Port 8000 is Blocked

- **DO NOT USE:** `uvicorn api.main:app --reload` (defaults to port 8000)
- **ALWAYS USE:** `uvicorn api.main:app --reload --port 8001`

### Port Configuration

- Backend: **8001** (Uvicorn)
- Frontend: **3000** (Vite)
- Frontend proxy: `/api/*` → `http://localhost:8001` (with path rewrite)

---

## 🧪 Testing the Application

1. Navigate to: http://localhost:3000
2. Click "Evaluate" in sidebar
3. Fill form:
   - Borrower Type: Individual
   - Loan Amount: 1500000
   - Loan Type: Home
   - Tenure: 20
   - Interest Rate: 8.5
   - Collateral: Gold
4. Click "Evaluate Application"
5. ✅ Should see result (ALLOW or DENY) with debug trace

---

## 🐛 Troubleshooting

### Backend won't start

```
ERROR: [WinError 10013] An attempt was made to access a socket...
```

**Solution:** Use `--port 8001`

```bash
uvicorn api.main:app --reload --port 8001
```

### Frontend shows blank page

- Hard refresh: **Ctrl+F5** (not just F5)
- Clear cache: **Ctrl+Shift+Delete**
- Reload: **http://localhost:3000**

### Still getting 404 error

1. Check backend shows "Application startup complete"
2. Check frontend shows "VITE ready"
3. Open DevTools (F12)
4. Go to Network tab
5. Click "Evaluate Application"
6. Look for "simulate" request
7. Should show **Status 200** (not 404)

### Check if servers are running

**Backend:**

```bash
curl http://localhost:8001/docs
```

Should return HTML page (200 OK)

**Frontend:**

```bash
http://localhost:3000
```

Should load the application

---

## 📁 Key Files

| File                      | Purpose                                 |
| ------------------------- | --------------------------------------- |
| `start_backend.bat`       | Quick start backend on port 8001        |
| `start_frontend.bat`      | Quick start frontend on port 3000       |
| `frontend/vite.config.ts` | Proxy configuration (rewrite /api to /) |
| `api/main.py`             | Backend API entry point                 |
| `FINAL_FIX_WORKING.md`    | Technical fix details                   |

---

## ✅ Expected Output

**Backend Terminal:**

```
INFO:     Will watch for changes in these directories...
INFO:     Uvicorn running on http://127.0.0.1:8001 (Press CTRL+C to quit)
INFO:     Started reloader process [...]
INFO:     Started server process [...]
INFO:     Application startup complete.
```

**Frontend Terminal:**

```
> regtech-dashboard@1.0.0 dev
> vite

  VITE v5.4.21  ready in 1350 ms

  ➜  Local:   http://localhost:3000/
```

**Browser (after evaluation):**

- Result: ALLOW or DENY
- Debug trace visible
- No error messages

---

## 🔄 Restarting Servers

To restart either server:

1. Press **Ctrl+C** in the terminal
2. Wait 2 seconds
3. Run the script or command again

---

## 💾 Development Workflow

Both servers watch for changes:

- **Backend:** Changes to Python files auto-reload
- **Frontend:** Changes to TypeScript/CSS auto-reload

Just save files and they'll automatically refresh!

---

## 📞 Common Issues Quick Reference

| Issue                  | Solution                     |
| ---------------------- | ---------------------------- |
| Port 8000 error        | Use `--port 8001`            |
| 404 on evaluation      | Hard refresh Ctrl+F5         |
| Blank page             | Clear cache Ctrl+Shift+Del   |
| Stale data shown       | Restart frontend             |
| Backend not responding | Check port with curl/browser |

---

**Ready to go!** Use `start_backend.bat` and `start_frontend.bat` for easiest startup. 🚀
