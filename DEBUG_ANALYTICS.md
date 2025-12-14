# Debug Analytics Data Mismatch

## Issue
After restoring backup from local to preview:
- Dashboard shows correct data
- Analytics shows different data

## Debugging Steps

### Step 1: Check Transaction Counts
Open browser console (F12) and run:

**On Local:**
```javascript
fetch('/api/transactions?limit=1000', {
  headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
})
.then(r => r.json())
.then(d => console.log('Local Transactions:', d.length));
```

**On Preview:**
```javascript
fetch('/api/transactions?limit=1000', {
  headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
})
.then(r => r.json())
.then(d => console.log('Preview Transactions:', d.length));
```

### Step 2: Check Category IDs in Transactions
```javascript
fetch('/api/transactions?limit=1000', {
  headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
})
.then(r => r.json())
.then(d => {
  const categoryIds = [...new Set(d.map(t => t.category_id).filter(Boolean))];
  console.log('Unique Category IDs in transactions:', categoryIds);
});
```

### Step 3: Check Available Categories
```javascript
fetch('/api/categories', {
  headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
})
.then(r => r.json())
.then(d => {
  console.log('Total Categories:', d.length);
  console.log('Category IDs:', d.map(c => c.id));
  console.log('User Categories:', d.filter(c => c.user_id).map(c => ({id: c.id, name: c.name})));
  console.log('System Categories:', d.filter(c => c.is_system).length);
});
```

### Step 4: Check Analytics Response
```javascript
fetch('/api/analytics/summary', {
  headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
})
.then(r => r.json())
.then(d => {
  console.log('Analytics Summary:', d);
  console.log('Category Breakdown:', d.category_breakdown);
});
```

### Step 5: Check for Orphaned Transactions
Transactions with category_ids that don't exist in categories collection:

```javascript
Promise.all([
  fetch('/api/transactions?limit=1000', {
    headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
  }).then(r => r.json()),
  fetch('/api/categories', {
    headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
  }).then(r => r.json())
]).then(([transactions, categories]) => {
  const categoryIds = new Set(categories.map(c => c.id));
  const orphaned = transactions.filter(t => t.category_id && !categoryIds.has(t.category_id));
  console.log('Orphaned transactions (category not found):', orphaned.length);
  if (orphaned.length > 0) {
    console.log('Sample orphaned transaction:', orphaned[0]);
    console.log('Missing category IDs:', [...new Set(orphaned.map(t => t.category_id))]);
  }
});
```

## Common Issues

### Issue 1: Orphaned Category IDs
**Symptom:** Transactions reference category_ids that don't exist in categories collection
**Cause:** Categories weren't properly restored or were deleted
**Fix:** Need to ensure categories are restored before transactions reference them

### Issue 2: System Categories Not Matching
**Symptom:** System category IDs are different between environments
**Cause:** System categories are created with different UUIDs in each environment
**Fix:** System categories should have consistent UUIDs across all environments

### Issue 3: User Category IDs Changed
**Symptom:** User-created categories have different IDs after restore
**Cause:** Restore process regenerates IDs instead of preserving them
**Fix:** Preserve original category IDs during restore

## Expected Behavior

After restore:
1. All transactions should be present (check Dashboard)
2. All categories should be present (check Categories page)
3. Analytics should show breakdown by category (check Analytics page)
4. No orphaned transactions (transactions with invalid category_ids)

## Quick Test

Run this comprehensive check:
```javascript
async function debugAnalytics() {
  const token = localStorage.getItem('token');
  const headers = { 'Authorization': `Bearer ${token}` };
  
  const [txns, cats, analytics] = await Promise.all([
    fetch('/api/transactions?limit=1000', { headers }).then(r => r.json()),
    fetch('/api/categories', { headers }).then(r => r.json()),
    fetch('/api/analytics/summary', { headers }).then(r => r.json())
  ]);
  
  console.log('=== DATA SUMMARY ===');
  console.log('Transactions:', txns.length);
  console.log('Categories:', cats.length);
  console.log('Analytics Transaction Count:', analytics.transaction_count);
  console.log('Analytics Categories:', analytics.category_breakdown.length);
  
  const catIds = new Set(cats.map(c => c.id));
  const orphaned = txns.filter(t => t.category_id && !catIds.has(t.category_id));
  
  console.log('\n=== ORPHANED TRANSACTIONS ===');
  console.log('Count:', orphaned.length);
  if (orphaned.length > 0) {
    console.log('Missing Category IDs:', [...new Set(orphaned.map(t => t.category_id))]);
  }
  
  console.log('\n=== CATEGORY TYPES ===');
  console.log('System:', cats.filter(c => c.is_system).length);
  console.log('User:', cats.filter(c => c.user_id).length);
  
  return {
    transactions: txns.length,
    categories: cats.length,
    orphaned: orphaned.length,
    analytics: analytics.category_breakdown.length
  };
}

debugAnalytics();
```
