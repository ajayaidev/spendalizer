# SpendAlizer Backup & Restore Guide

## Overview
The backup and restore feature allows you to export all your financial data and import it back when needed. This guide explains how it works, especially when moving data between different environments.

## How It Works

### Backup (Export)
- **Location:** Settings page → Data Management → Download Backup
- **What's Included:**
  - All transactions
  - **All categories** (both system and user-created)
  - Categorization rules
  - Account information
  - Import history
- **File Format:** ZIP file named `SpendAlizer-{domain}-{yyyymmdd-hhmmss}.zip`
- **Important:** 
  - Only YOUR user data is included (filtered by your user account)
  - System categories are included to ensure transaction references remain valid
  - This creates a completely self-contained, portable backup

### Restore (Import)
- **Location:** Settings page → Data Management → Restore from Backup
- **Process:**
  1. **Pre-Restore Backup:** Automatically creates a backup of your current data first
  2. **Flush:** Removes all your current data
  3. **Restore:** Imports data from the uploaded backup file
  4. **Refresh:** Page reloads to show the restored data

## Understanding Multi-Environment Usage

### Key Concept: User IDs
SpendAlizer uses unique user IDs to separate data between users. **Important:** The same email address will have DIFFERENT user IDs in different environments (local vs. online preview).

### Example Scenario

**Environment 1: Online Preview**
- You create an account: `john@example.com`
- User ID: `abc-123-def`
- You add transactions, categories, rules

**Environment 2: Local**
- You create the same account: `john@example.com`
- User ID: `xyz-789-uvw` (DIFFERENT from preview!)
- Initially empty

### What Happens During Restore

When you restore a backup from **Preview** to **Local**:

1. ✅ You download backup from preview (contains data with user_id: `abc-123-def`)
2. ✅ You upload backup to local (logged in as `john@example.com` with user_id: `xyz-789-uvw`)
3. ✅ The restore process:
   - Creates a pre-restore backup of your current local data
   - Flushes your local data
   - **Changes all user_ids in the backup to your local user_id (`xyz-789-uvw`)**
   - Inserts the data into your local database
4. ✅ You see all your transactions, categories, and rules in local!

### Why Different User IDs?

This is by design for security:
- Local and preview/production have **completely separate databases**
- You can't accidentally access someone else's data
- Each environment is isolated
- The restore feature safely transfers YOUR data between YOUR accounts in different environments

## Important Notes

### ✅ Correct Usage
- **Restoring to the SAME email account:** Data will appear correctly after restore
- **Example:** Backup from `john@example.com` (preview) → Restore to `john@example.com` (local) ✅

### ❌ Common Confusion
- **Expecting data to sync across environments:** Local and preview are SEPARATE
- **Example:** Adding data in preview won't automatically appear in local (you need to backup & restore)

### 🔒 Security Features
- You can only restore backups to YOUR account (the one you're logged in as)
- Pre-restore backups are saved to `/tmp/spendalizer_backups/` (in case you need to rollback)
- All user_ids are automatically updated during restore for security

### 📊 System Categories Handling

**Why System Categories are Included:**
- All transactions reference category UUIDs
- If system categories are missing or different, transactions won't display properly
- System categories might be updated between backup and restore
- Ensures complete data portability

**During Restore:**
- System categories from backup are restored/updated to match backup state
- Ensures your transaction category references remain valid
- If system category exists: updates name and type from backup
- If system category is missing: inserts it from backup
- On next server restart: `system_categories.json` syncs to latest version

**Example Scenario:**
1. You backup data (includes "Investment - WINTWEALTH" as TRANSFER_EXTERNAL_OUT)
2. System categories are updated in a new version
3. You restore backup → your transactions still reference correct categories
4. Server restart → system categories sync to latest definitions

## Step-by-Step: Moving Data from Preview to Local

1. **On Preview Environment:**
   - Login to your account (e.g., `john@example.com`)
   - Go to Settings → Data Management
   - Click "Download Backup"
   - Save the ZIP file (e.g., `SpendAlizer-finance-ai-29-20241214-123456.zip`)

2. **On Local Environment:**
   - Make sure you're logged in with the **SAME EMAIL** (e.g., `john@example.com`)
   - Go to Settings → Data Management
   - Click "Restore from Backup"
   - Upload the ZIP file you downloaded from preview
   - Wait for the restore to complete
   - The page will automatically reload

3. **Verify:**
   - Check Dashboard for your transactions
   - Check Categories page for your custom categories
   - Check Rules page for your categorization rules
   - Check Analytics for your financial data

## Troubleshooting

### "My data isn't showing after restore!"

**Possible Causes:**
1. **Logged in as different email:** Make sure you're logged in with the same email in both environments
2. **Browser cache:** Hard refresh the page (Ctrl+Shift+R or Cmd+Shift+R)
3. **Restore failed:** Check the toast notification for error messages

### "I restored but see different data in preview vs. local"

**This is expected!** Preview and local are separate environments:
- After restore, your LOCAL environment will have the data from the backup
- But your PREVIEW environment still has its original data
- They don't sync automatically - you need to backup & restore to move data between them

### "Can I restore someone else's backup?"

**No.** For security, the restore process forces all data to be associated with YOUR user_id. Even if you upload someone else's backup file, the data will be assigned to your account, and you won't see it as their data.

## Best Practices

1. **Regular Backups:** Download backups regularly, especially before major changes
2. **Backup Before Restore:** The system automatically creates a pre-restore backup, but it's saved locally on the server
3. **Test in Local First:** When trying new features, test in local environment first
4. **Keep Backup Files Safe:** Store your backup ZIP files securely
5. **Use Descriptive Filenames:** The system includes domain and timestamp in the filename for easy identification

## Technical Details

### Backup Contents
```
SpendAlizer-{domain}-{timestamp}.zip
├── transactions.json       # All your transactions
├── categories.json         # Your custom categories
├── rules.json             # Your categorization rules
├── accounts.json          # Your account information
├── import_batches.json    # Your import history
└── metadata.json          # Backup metadata (date, counts, etc.)
```

### Restore Process
```python
1. Authenticate user
2. Create pre-restore backup → /tmp/spendalizer_backups/pre_restore_{user_id}_{timestamp}.zip
3. Validate uploaded ZIP file
4. Flush current user data:
   - Delete all transactions for user
   - Delete all custom categories for user
   - Delete all rules for user
   - Delete all accounts for user
   - Delete all import batches for user
5. Restore data from backup:
   - For each item, set user_id = current_user_id
   - Insert into database
6. Return success with restored counts
```

## Support

If you encounter issues with backup & restore:
1. Check browser console for errors (F12 → Console tab)
2. Verify you're logged in with the correct email
3. Try hard refreshing the page (Ctrl+Shift+R)
4. Check that the backup file is a valid SpendAlizer backup (.zip file)
5. If restoring fails, your original data is preserved (check pre-restore backup)
