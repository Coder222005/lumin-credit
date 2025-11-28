# Limit Generator Debugging Guide

## Current Status
The Limit Generator component has been updated with console logging to help debug display issues.

## How to Debug

### Step 1: Open Browser Console
1. Go to http://localhost:5173
2. Open Developer Tools (F12 or Right-click → Inspect)
3. Go to the **Console** tab

### Step 2: Login and Check Console
1. Login with any user (e.g., user01/user01)
2. Look for these console messages:
   ```
   LimitGeneratorView received limits: {status: "NA", safe_limit: ..., max_limit: ..., ...}
   ```

### Step 3: Expected Console Output

#### When NO goal is set:
```javascript
LimitGeneratorView received limits: {
  status: "NA",
  message: "No active goal set.",
  safe_limit: 1000000,
  max_limit: 1000000,
  goal_value: "N/A",
  impact_analysis: "Set a financial goal..."
}
Limit status is NA - no goal set
```
**Expected UI:** Grayed out card saying "Set a goal to activate limit generation."

#### When goal IS set:
```javascript
LimitGeneratorView received limits: {
  status: "Active",
  safe_limit: 70000,
  max_limit: 85000,
  goal_value: "$120,000",
  impact_analysis: "Paying more than $70,000 will..."
}
Displaying active limits: {safe: 70000, max: 85000, goal: "$120,000"}
```
**Expected UI:** 
- Safe Limit: $70,000 (green)
- Max Limit: $85,000 (amber)
- Goal Value: $120,000
- Analysis text

## Testing Steps

### Test 1: Verify NA State
1. Login as fresh user (user01)
2. Scroll to "Limit Generator" card
3. Console should show: `Limit status is NA - no goal set`
4. UI should show grayed out message

### Test 2: Set a Goal
1. Scroll up to "Goal Setting Agent"
2. Select "Buy a House"
3. Enter amount: 120000
4. Click "Set Goal & Get Plan"
5. Wait for the plan to appear
6. Scroll down to "Limit Generator"

### Test 3: Verify Active State
After setting goal:
1. Console should show: `Displaying active limits: {...}`
2. UI should show:
   - ✓ Safe Limit with dollar amount (green)
   - ✓ Max Limit with dollar amount (amber)
   - ✓ Goal Value displaying your amount
   - ✓ Impact analysis text

## Common Issues & Fixes

### Issue: Shows "Loading..." forever
**Cause:** Backend not returning payment_limits
**Fix:** Check backend logs for errors in LimitGeneratorAgent

### Issue: Shows "N/A" state even after setting goal
**Cause 1:** Goal not saved to user data
**Fix:** Check console - should see goal being saved

**Cause 2:** Dashboard not refreshing after goal set
**Fix:** The fetchData() should be called after goal is set

### Issue: Limits show as "undefined" or "$NaN"
**Cause:** LLM returned non-integer values
**Fix:** Backend has fallback, check if it's being triggered

## Backend Verification

Test the API directly:
```bash
# Check user01's payment limits
curl -s "http://localhost:5001/dashboard?user=user01" | python3 -m json.tool | grep -A 10 "payment_limits"
```

Expected output:
```json
"payment_limits": {
    "status": "NA",  // or "Active"
    "safe_limit": 70000,
    "max_limit": 85000,
    "goal_value": "$120,000",
    "impact_analysis": "..."
}
```

## What Should Happen

### Scenario: User with $100K savings wants house ($120K)
1. Set goal: "Buy a House" with amount 120000
2. Backend LimitGeneratorAgent calculates:
   - safe_limit: ~$60K-70K (leaves enough for house)
   - max_limit: ~$90K (emergency reserve)
   - goal_value: "$120,000"
3. Frontend displays all three values
4. If payment of $80K attempted: Warning shown (exceeds safe limit)

## Action Items

If still not working:
1. ✓ Check browser console for the log messages
2. ✓ Verify API returns payment_limits in response
3. ✓ Check if goal was saved (look for "User data saved." in backend)
4. ✓ Refresh page after setting goal
5. ✓ Try with a different user

## Quick Test Command

```bash
# Test with user05 (has goal set if you tested earlier)
curl -s "http://localhost:5001/dashboard?user=user05" | python3 -m json.tool | grep -B2 -A8 "payment_limits"
```
