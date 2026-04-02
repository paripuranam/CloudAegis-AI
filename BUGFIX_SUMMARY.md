# CloudAegis AI - Bug Fixes Summary (April 2, 2026)

## Issues Identified & Fixed

### 1. **Dashboard Data Showing Null When Switching Tabs/Accounts**

**Root Causes:**
- Race condition when switching accounts - `selectedScanId` wasn't properly cleared, pointing to old account's scans
- `useFetching` hook was clearing data on every refetch instead of preserving previous data
- Circular dependency on `selectedScanId` in the scan selection useEffect
- `fetchInventory` was returning `{ data: null }` instead of providing a safe default structure

**Fixes Applied:**

#### a) Enhanced `useFetching` Hook (`frontend/src/hooks/useFetching.jsx`)
- Added `previousDataRef` to track and restore last successful data
- On error, now preserves previous data instead of clearing it
- Improved loading state: only sets `loading: true` on initial fetch, prevents flashing during refetches
- Better error recovery: restores previous data if current fetch fails

#### b) Fixed Dashboard Component (`frontend/src/pages/Dashboard.jsx`)
- Changed `fetchInventory` to return `{ data: { summary: {} } }` instead of `null` when no account selected
- Changed data display logic to use `activeHistoryItem` as fallback when `selectedScan` is loading
- Fixed the useEffect for scan selection:
  - Removed `selectedScanId` from dependencies (was causing infinite loop)
  - Added explicit logic to select first scan if none selected
  - Properly handles account switching by detecting if current scan still exists
  - Returns early if scan history is empty

#### c) Fixed Findings Page (`frontend/src/pages/Findings.jsx`)
- Applied same useEffect fix as Dashboard
- Removed `selectedScanId` from dependency array to prevent infinite loops
- Better scan selection logic when account changes
- Fallback to activeHistoryItem data when selectedScan is loading

### 2. **Frontend Babel Parsing Errors**

**Root Cause:**
- `useFetching.jsx` had markdown code block syntax (```` ```jsx ``` ````) wrapping the code
- Conflicting JSX pragma comment conflicted with React's automatic JSX transform

**Fixes Applied:**
- Removed markdown formatting from `useFetching.jsx`
- Removed JSX pragma comment (`/** @jsx React.createElement */`)
- Ensured `.jsx` file extension for proper Vite/Babel handling

### 3. **Bridge the Gap - Data Persistence During Load**

**Improvements:**
- Dashboard and Findings now use `activeHistoryItem` as fallback data source
- When switching scans, data remains visible from previous scan until new data loads
- Error states don't cause data to disappear
- More graceful handling of temporary network issues

---

## Files Modified

1. **frontend/src/hooks/useFetching.jsx**
   - Enhanced data preservation on errors
   - Better loading state management
   - Previous data tracking for fallback

2. **frontend/src/pages/Dashboard.jsx**
   - Fixed account switching logic  
   - Improved fallback data handling
   - Fixed scan selection useEffect dependencies

3. **frontend/src/pages/Findings.jsx**
   - Fixed account switching logic
   - Improved scan selection useEffect


4. **docs/ARCHITECTURE.md**
   - Updated hook file references (useFetching.jsx, useStore.jsx)

---

## Testing Recommendations

1. **Account Switching**: Connect multiple AWS accounts, switch between them rapidly
   - Verify dashboard data persists during tab switches
   - Confirm scan history updates correctly

2. **Scan Selection**: 
   - Run a scan on one account
   - Switch to different account with its own scans
   - Select different scans rapidly
   - Verify data displays correctly and doesn't show null

3. **Tab Navigation**:
   - Switch between Dashboard, Findings, Accounts tabs
   - Verify data is retained and displayed properly
   - Check that scan history remains selected

4. **Network Resilience**:
   - Refresh page while data is loading
   - Verify previous data is shown instead of null
   - Test with network throttling in browser DevTools

---

## Performance Improvements

- Eliminated unnecessary refetches due to dependency issues
- Better memory usage with previousDataRef for fallback data
- Reduced component re-renders by fixing useEffect dependencies
- Faster tab switching due to data preservation

---

## Current Application Status

✅ **Frontend**: Running cleanly at http://localhost:3008
✅ **Backend**: Running and responding at http://localhost:8010/api/v1
✅ **Database**: PostgreSQL healthy and connected
✅ **All Services**: Docker Compose up and operational

### Branding
- ✅ All references renamed from "CloudGuard" to "CloudAegis AI"
- ✅ Database names updated to cloudaegis
- ✅ Container names updated to cloudaegis-*

---

## Development Notes

**Key Learning**: The most critical fix was removing `selectedScanId` from the dependency array in the scan selection useEffect. This prevented the infinite loop of:
1. selectedScanId changes → useEffect runs with old deps
2. setSelectedScanId called → selectedScanId state updates
3. Go back to step 1

By using only `scanHistory` and `setSelectedScanId` in dependencies, we allow the effect to run when the account's scan history changes, but not when the user manually selects a scan within the same account.
