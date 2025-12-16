# Quick Email Setup for SpendAlizer

The "Forgot Password" feature requires email configuration to send password reset links.

## 🚀 Quick Setup with Gmail (Recommended for Testing)

### Step 1: Generate Gmail App Password

1. **Enable 2-Factor Authentication** on your Google account (required)
   - Go to: https://myaccount.google.com/security
   - Enable 2-Step Verification

2. **Generate an App Password**
   - Go to: https://myaccount.google.com/apppasswords
   - Select "Mail" and your device
   - Copy the generated 16-character password (e.g., `abcd efgh ijkl mnop`)

### Step 2: Update `backend/.env`

Open `/app/backend/.env` and fill in these values:

```bash
EMAIL_HOST="smtp.gmail.com"
EMAIL_PORT="587"
EMAIL_USER="your-gmail@gmail.com"           # Your Gmail address
EMAIL_PASSWORD="abcd efgh ijkl mnop"        # Your 16-char App Password (remove spaces)
EMAIL_FROM="your-gmail@gmail.com"           # Same as EMAIL_USER
FRONTEND_URL="http://localhost:3000"        # Auto-detects for Emergent, use this for local
```

**Example:**
```bash
EMAIL_HOST="smtp.gmail.com"
EMAIL_PORT="587"
EMAIL_USER="johndoe@gmail.com"
EMAIL_PASSWORD="abcdefghijklmnop"
EMAIL_FROM="johndoe@gmail.com"
FRONTEND_URL="http://localhost:3000"
```

### Step 3: Restart Backend (if running locally)

```bash
# On Mac/Linux
./stop.sh && ./start.sh

# Or if using update script
./update.sh
```

**On Emergent:** The backend automatically reloads when `.env` changes are detected.

---

## 🌐 How It Works on Different Environments

### ✅ Automatic Environment Detection

The backend now **automatically detects** which environment you're using:

1. **On Emergent Preview** (`https://spendalizer.preview.emergentagent.com`):
   - Email reset links will use: `https://spendalizer.preview.emergentagent.com/reset-password?token=...`
   - Works automatically via request origin detection

2. **On Localhost** (`http://localhost:3000`):
   - Email reset links will use: `http://localhost:3000/reset-password?token=...`
   - Uses `FRONTEND_URL` from `.env`

**You only need to configure SMTP once, and it works everywhere!** 🎉

---

## 🧪 Testing the Email Feature

### On Emergent (Current Environment):

1. Navigate to: https://spendalizer.preview.emergentagent.com/forgot-password
2. Enter a registered email address
3. Check your email inbox for the reset link
4. Click the link and reset your password

### On Localhost (After Pulling Changes):

1. Pull latest changes: `./update.sh`
2. Navigate to: http://localhost:3000/forgot-password
3. Enter a registered email address
4. Check your email inbox
5. Click the reset link

---

## 📧 Gmail-Specific Tips

### If Email Isn't Sending:

1. **Check App Password**: Make sure you're using the 16-character App Password, NOT your regular Gmail password
2. **Remove Spaces**: Copy the App Password without spaces (e.g., `abcdefghijklmnop`)
3. **Check Backend Logs**:
   ```bash
   tail -f backend_logs.txt  # On Mac
   # Or check: /var/log/supervisor/backend.out.log on Emergent
   ```
4. **Verify 2FA is Enabled**: App Passwords only work when 2-Factor Authentication is enabled

### If Email Goes to Spam:

- This is normal for development/testing
- Check your spam folder
- In production, consider using SendGrid or Mailgun for better deliverability

---

## 🔐 Security Notes

- **Never commit** `.env` file to Git (it's already in `.gitignore`)
- Use **App Passwords** for Gmail, not your main password
- For production, consider using dedicated email services:
  - SendGrid (Free tier: 100 emails/day)
  - Mailgun (Free tier: 5,000 emails/month)
  - AWS SES (Very cheap, $0.10 per 1,000 emails)

---

## 🆘 Troubleshooting

### "Email not configured" warning in logs
- SMTP credentials are missing or empty in `backend/.env`
- Fill in `EMAIL_USER` and `EMAIL_PASSWORD`

### "Authentication failed" error
- Wrong App Password or regular password used
- Generate a new App Password: https://myaccount.google.com/apppasswords

### Email reset link doesn't work
- Link expired (1-hour validity)
- Request a new reset link

### Need more options?
- See detailed guide: `SMTP_SETUP_GUIDE.md`
- Includes: Outlook, SendGrid, Mailgun configurations

---

## ✅ Quick Verification

After setup, verify it works:

```bash
# Test the endpoint
curl -X POST "http://localhost:8001/api/auth/forgot-password" \
  -H "Content-Type: application/json" \
  -d '{"email":"your-test-email@gmail.com"}'

# Should return: {"message":"If the email exists, a reset link has been sent"}
# Check your email inbox!
```

---

**Questions?** Check the full guide: `SMTP_SETUP_GUIDE.md` or check backend logs for errors.
