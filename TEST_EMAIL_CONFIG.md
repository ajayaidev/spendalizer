# Test Email Configuration - Both Environments

## 📝 Summary

Your SpendAlizer app now supports email configuration for **both Emergent and localhost** with automatic environment detection!

---

## 🔧 One-Time Setup (Works for Both Environments)

### Configure SMTP in `backend/.env`:

```bash
# Gmail Configuration (Recommended for Testing)
EMAIL_HOST="smtp.gmail.com"
EMAIL_PORT="587"
EMAIL_USER="your-email@gmail.com"        # Your Gmail
EMAIL_PASSWORD="your-16-char-app-pass"   # Gmail App Password
EMAIL_FROM="your-email@gmail.com"        # Same as EMAIL_USER
```

### How to Get Gmail App Password:
1. Enable 2FA: https://myaccount.google.com/security
2. Generate App Password: https://myaccount.google.com/apppasswords
3. Copy the 16-character password (remove spaces)

---

## ✅ Testing on Emergent (Current Preview)

**URL:** https://spend-tracker-140.preview.emergentagent.com

1. Update `backend/.env` with your SMTP credentials (see above)
2. Wait ~10 seconds for backend to auto-reload
3. Test:
   - Go to: https://spend-tracker-140.preview.emergentagent.com/forgot-password
   - Enter a registered email
   - Check your inbox
   - Reset link will use: `https://spend-tracker-140.preview.emergentagent.com/reset-password?token=...`

---

## ✅ Testing on Localhost

**URL:** http://localhost:3000

1. Pull latest changes:
   ```bash
   cd /path/to/spendalizer
   ./update.sh
   ```

2. Your SMTP config from `backend/.env` will automatically work

3. Test:
   - Go to: http://localhost:3000/forgot-password
   - Enter a registered email
   - Check your inbox
   - Reset link will use: `http://localhost:3000/reset-password?token=...`

---

## 🎯 How Auto-Detection Works

The backend automatically detects the environment:

- **Request from Emergent** → Uses `https://spend-tracker-140.preview.emergentagent.com`
- **Request from Localhost** → Uses `http://localhost:3000`
- **Fallback** → Uses `FRONTEND_URL` from `.env`

**You configure SMTP once, it works everywhere!** 🚀

---

## 🧪 Quick Test (No Email Required)

Test the endpoint without SMTP configured:

```bash
# On Emergent
curl -X POST "https://spend-tracker-140.preview.emergentagent.com/api/auth/forgot-password" \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com"}'

# Response: {"message":"If the email exists, a reset link has been sent"}
```

**Note:** Email won't actually send without SMTP config, but endpoint works!

---

## 📋 Configuration Checklist

- [ ] Gmail 2FA enabled
- [ ] Gmail App Password generated
- [ ] `backend/.env` updated with credentials
- [ ] Backend restarted (auto on Emergent, manual on localhost)
- [ ] Test on Emergent preview
- [ ] Pull changes with `./update.sh` (for localhost)
- [ ] Test on localhost

---

## 🚨 Important Notes

1. **Same config works everywhere** - No need to change anything between environments
2. **Backend auto-reloads** on Emergent when `.env` changes
3. **Secure** - `.env` file is in `.gitignore` and never committed
4. **Email links** automatically use the correct URL based on where the request came from

---

## 📚 More Help

- Quick Setup: `EMAIL_SETUP_QUICK_START.md`
- Detailed Guide: `SMTP_SETUP_GUIDE.md`
- Check Logs: `tail -f /var/log/supervisor/backend.out.log`

---

**Ready to test!** Configure your Gmail App Password and try it out! 🎉
