# SMTP Email Configuration Guide

The "Forgot Password" feature requires email functionality. You need to configure SMTP settings in your `backend/.env` file.

## 📧 Configuration Variables

Add these values to `/app/backend/.env`:

```
EMAIL_HOST="your-smtp-host"
EMAIL_PORT="your-smtp-port"
EMAIL_USER="your-email@example.com"
EMAIL_PASSWORD="your-email-password-or-app-password"
EMAIL_FROM="your-email@example.com"
FRONTEND_URL="http://localhost:3000"
```

---

## 🔧 Common Email Provider Settings

### Option 1: Gmail (Recommended for Testing)

1. **Enable 2-Factor Authentication** on your Google account
2. **Generate an App Password**:
   - Go to: https://myaccount.google.com/apppasswords
   - Select "Mail" and your device
   - Copy the generated 16-character password
3. **Add to `.env`**:
   ```
   EMAIL_HOST="smtp.gmail.com"
   EMAIL_PORT="587"
   EMAIL_USER="your-gmail@gmail.com"
   EMAIL_PASSWORD="your-16-char-app-password"
   EMAIL_FROM="your-gmail@gmail.com"
   FRONTEND_URL="http://localhost:3000"
   ```

### Option 2: Outlook/Hotmail

```
EMAIL_HOST="smtp-mail.outlook.com"
EMAIL_PORT="587"
EMAIL_USER="your-email@outlook.com"
EMAIL_PASSWORD="your-outlook-password"
EMAIL_FROM="your-email@outlook.com"
FRONTEND_URL="http://localhost:3000"
```

### Option 3: SendGrid (Production Recommended)

1. **Sign up**: https://sendgrid.com/
2. **Create API Key**: Settings → API Keys → Create API Key
3. **Add to `.env`**:
   ```
   EMAIL_HOST="smtp.sendgrid.net"
   EMAIL_PORT="587"
   EMAIL_USER="apikey"
   EMAIL_PASSWORD="your-sendgrid-api-key"
   EMAIL_FROM="verified-sender@yourdomain.com"
   FRONTEND_URL="http://localhost:3000"
   ```
   Note: You need to verify your sender email/domain in SendGrid

### Option 4: Mailgun

1. **Sign up**: https://www.mailgun.com/
2. **Get SMTP credentials**: Sending → Domain Settings → SMTP credentials
3. **Add to `.env`**:
   ```
   EMAIL_HOST="smtp.mailgun.org"
   EMAIL_PORT="587"
   EMAIL_USER="postmaster@your-domain.mailgun.org"
   EMAIL_PASSWORD="your-mailgun-smtp-password"
   EMAIL_FROM="noreply@your-domain.mailgun.org"
   FRONTEND_URL="http://localhost:3000"
   ```

---

## 🚀 After Configuration

1. **Save** your changes to `backend/.env`
2. **Restart the backend server**:
   ```bash
   ./stop.sh
   ./start.sh
   ```
   Or use the `update.sh` script if you pulled from Git

3. **Test the feature**:
   - Navigate to: http://localhost:3000/forgot-password
   - Enter a registered email address
   - Check your inbox for the password reset email

---

## 🐛 Troubleshooting

### Email not sending?
- Check backend logs: `tail -f backend_logs.txt`
- Verify SMTP credentials are correct
- For Gmail: Ensure App Password is used (not regular password)
- Check if email provider requires "less secure app access"

### "Authentication failed" error?
- Double-check `EMAIL_USER` and `EMAIL_PASSWORD`
- For Gmail, regenerate the App Password
- Try port `465` with SSL if `587` doesn't work

### Email goes to spam?
- Normal for development/testing
- In production, use verified domain and proper DNS records (SPF, DKIM)
- Consider using SendGrid or Mailgun for better deliverability

---

## 🔒 Security Notes

- **Never commit** your `.env` file to Git (it's in `.gitignore`)
- Use **App Passwords** for Gmail (not your main password)
- For production, use dedicated email service (SendGrid, Mailgun, AWS SES)
- Consider environment variable management tools for production

---

## 📝 Feature Details

- Reset links expire after **1 hour**
- Links are single-use only
- All reset tokens are securely hashed in the database
- Email template includes user-friendly instructions
