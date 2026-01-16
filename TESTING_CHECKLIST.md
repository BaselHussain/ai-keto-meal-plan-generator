# Manual Testing Checklist - Phases 3-5

**Date**: 2026-01-14
**Tester**: ___________
**Browser**: Chrome/Edge/Firefox
**Device**: Desktop / Mobile

---

## Prerequisites

Before you start testing, make sure:
- [ ] Frontend dev server is running (`npm run dev` in frontend folder)
- [ ] Open browser to `http://localhost:3000`
- [ ] Open browser DevTools (F12) to check console for errors
- [ ] Have a notepad ready to document bugs

---

## Phase 3 Testing: Quiz Flow (T030-T045)

### Test 1: Initial Quiz Load
**Steps:**
1. Navigate to `http://localhost:3000`
2. Look for quiz start button or quiz container
3. Check browser console (F12 → Console tab) for errors

**Expected:**
- [ ] Page loads without errors
- [ ] Quiz interface is visible
- [ ] Step progress shows "Step 1 of 20"

**Actual Result:**
_________________________________

---

### Test 2: Step 1 - Gender Selection
**Steps:**
1. You should see gender selection options
2. Try clicking "Male"
3. Try clicking "Female"
4. Check if selection is visually highlighted

**Expected:**
- [ ] Both options are clickable
- [ ] Selected option shows visual feedback (border/background change)
- [ ] "Next" button becomes enabled after selection

**Actual Result:**
_________________________________

---

### Test 3: Step 2 - Activity Level
**Steps:**
1. Click "Next" from Step 1
2. You should see 5 activity levels:
   - Sedentary
   - Lightly Active
   - Moderately Active
   - Very Active
   - Extremely Active
3. Click each option and verify selection

**Expected:**
- [ ] All 5 options are visible
- [ ] Each option is clickable
- [ ] Selected option shows visual highlight
- [ ] Progress bar shows "Step 2 of 20"

**Actual Result:**
_________________________________

---

### Test 4: Food Selection Grid (Pick any step 3-16)
**Steps:**
1. Navigate to a food selection step (e.g., proteins, vegetables)
2. Click on 3-4 food items
3. Try to deselect one item by clicking again
4. Check if icons are colored (not grayscale)

**Expected:**
- [ ] Food items display with colored SVG icons (64x64px)
- [ ] Multi-select works (can select multiple items)
- [ ] Deselect works (clicking again removes selection)
- [ ] Selected items show visual feedback (border/checkmark)
- [ ] Grid is responsive (no overflow)

**Actual Result:**
_________________________________

---

### Test 5: Food Selection - Minimum Items Validation
**Steps:**
1. On a food selection step, select less than 10 items total across all food steps
2. Try to proceed to Review Screen
3. Check for validation warning

**Expected:**
- [ ] Warning appears if <10 total food items selected
- [ ] Warning message clearly states minimum requirement
- [ ] User can still proceed (warning, not blocker)

**Actual Result:**
_________________________________

---

### Test 6: Step 17 - Dietary Restrictions
**Steps:**
1. Navigate to Step 17
2. Look for textarea with 500-char limit
3. Type some text (e.g., "No dairy, allergic to shellfish")
4. Check character counter updates
5. Try typing more than 500 characters

**Expected:**
- [ ] Textarea is visible with placeholder text
- [ ] Character counter shows remaining characters
- [ ] Counter turns orange/red when <50 chars remaining
- [ ] Cannot type beyond 500 characters
- [ ] Privacy warning (yellow box) is visible
- [ ] Privacy warning text: "DO NOT include medical diagnoses"

**Actual Result:**
_________________________________

---

### Test 7: Step 20 - Biometrics & Privacy Badge
**Steps:**
1. Navigate to Step 20 (final step)
2. Check for green lock icon badge at top
3. Check for blue privacy notice box
4. Try switching between Metric and Imperial units
5. Enter test data:
   - Age: 30
   - Weight: 70 (kg) or 154 (lbs)
   - Height: 170 (cm) or 67 (inches)
6. Select a goal (Weight Loss, Maintenance, or Muscle Gain)

**Expected:**
- [ ] Green lock badge displays "100% Private & Confidential"
- [ ] Blue privacy notice box shows data deletion info (24 hours)
- [ ] Unit toggle switches between Metric (kg/cm) and Imperial (lb/in)
- [ ] Input fields accept numbers
- [ ] Age field validates (18-100)
- [ ] All 3 goal options are selectable
- [ ] Selected goal shows checkmark icon

**Actual Result:**
_________________________________

---

### Test 8: Review Screen
**Steps:**
1. Complete all 20 quiz steps with valid data
2. You should see a Review/Summary screen
3. Look for:
   - Quiz summary (your answers)
   - Calorie breakdown section
   - BMR calculation display
   - Activity multiplier
   - Goal adjustment
   - Final calorie target
4. Check for "Proceed to Payment" button

**Expected:**
- [ ] Review screen displays all entered data
- [ ] Calorie breakdown is visible and shows math
- [ ] BMR formula result is shown
- [ ] Activity multiplier applied (e.g., x1.2, x1.55)
- [ ] Goal adjustment shown (-400, +0, +250 kcal)
- [ ] Final calorie target displayed (e.g., 1800 kcal)
- [ ] If calorie hit floor (1200F/1500M), warning shown
- [ ] "Proceed to Payment" button is enabled

**Actual Result:**
_________________________________

---

## Phase 4 Testing: Back Navigation (T046-T048)

### Test 9: Back Button Disabled on Step 1
**Steps:**
1. Start quiz from beginning (refresh page)
2. Look for "Back" button on Step 1

**Expected:**
- [ ] Back button is visible but disabled/grayed out
- [ ] Cannot click Back on Step 1

**Actual Result:**
_________________________________

---

### Test 10: Back Navigation with Data Persistence
**Steps:**
1. Navigate to Step 5 and select some food items
2. Click "Next" to go to Step 6
3. Select items on Step 6
4. Click "Next" to go to Step 7
5. Now click "Back" button
6. Verify you're on Step 6 and your selections are still there
7. Click "Back" again
8. Verify you're on Step 5 and your selections are still there

**Expected:**
- [ ] Back button works from any step 2-20
- [ ] Clicking Back takes you to previous step
- [ ] Previous step data is fully restored
- [ ] No data loss when navigating backward
- [ ] Progress bar updates correctly (shows correct step number)

**Actual Result:**
_________________________________

---

### Test 11: Forward Navigation After Going Back
**Steps:**
1. From Test 10, you should be on Step 5
2. Click "Next" to go forward to Step 6
3. Check if Step 6 data is still there
4. Click "Next" to go to Step 7
5. Continue forward to Step 10
6. Check if all data from steps 5-10 is preserved

**Expected:**
- [ ] Forward navigation restores all previously entered data
- [ ] No data loss when moving forward after going back
- [ ] All selections/inputs remain intact

**Actual Result:**
_________________________________

---

### Test 12: localStorage Persistence (Page Refresh)
**Steps:**
1. Fill quiz up to Step 15 with various data
2. Press F5 to refresh the page
3. Check if quiz resumes from Step 15
4. Navigate back to Step 10
5. Verify all data from Step 10 is still present

**Expected:**
- [ ] After refresh, quiz resumes at last completed step
- [ ] All previously entered data is restored
- [ ] localStorage persists across page refreshes
- [ ] No data loss after F5 refresh

**Actual Result:**
_________________________________

---

## Phase 5 Testing: Privacy Features (T049-T052)

### Test 13: Step 17 Privacy Warning & Link
**Steps:**
1. Navigate to Step 17 (Dietary Restrictions)
2. Look for yellow warning box with alert icon
3. Read the privacy notice text
4. Click on "Read our Privacy Policy" link
5. Check if link opens in new tab

**Expected:**
- [ ] Yellow warning box is visible
- [ ] Warning icon (triangle with exclamation) displays
- [ ] Text says "Enter only food preferences. DO NOT include medical diagnoses"
- [ ] Text mentions "retained for 90 days"
- [ ] "Read our Privacy Policy" link is underlined
- [ ] Link opens in **new tab** (not same tab)
- [ ] New tab goes to `/privacy` page

**Actual Result:**
_________________________________

---

### Test 14: Step 20 Privacy Badge & Link
**Steps:**
1. Navigate to Step 20 (Biometrics)
2. Look for green badge with lock icon at top
3. Look for blue info box below the badge
4. Click "Read our Privacy Policy" link in blue box
5. Check if link opens in new tab

**Expected:**
- [ ] Green badge shows lock icon + "100% Private & Confidential"
- [ ] Blue info box mentions "automatically deleted after 24 hours"
- [ ] Blue box mentions "We never share or sell your information"
- [ ] "Read our Privacy Policy" link is present
- [ ] Link opens in **new tab**
- [ ] New tab goes to `/privacy` page

**Actual Result:**
_________________________________

---

### Test 15: Privacy Policy Page - Navigation
**Steps:**
1. Manually navigate to `http://localhost:3000/privacy`
2. Check if page loads without errors
3. Look for "Back to Home" link at top
4. Click "Back to Home" link
5. Verify it takes you back to homepage/quiz

**Expected:**
- [ ] Privacy policy page loads successfully
- [ ] No 404 error
- [ ] "Back to Home" link is visible at top
- [ ] Clicking link navigates to home (/)
- [ ] Back arrow icon displays next to link

**Actual Result:**
_________________________________

---

### Test 16: Privacy Policy Page - Content Sections
**Steps:**
1. On `/privacy` page, scroll through the entire page
2. Count the major sections (headings)
3. Check if these sections exist:
   - Introduction
   - Information We Collect
   - How We Use Your Information
   - Data Retention & Automatic Deletion
   - Data Security
   - Third-Party Services
   - Your Rights (GDPR)
   - Cookies & Local Storage
   - Children's Privacy
   - Changes to This Policy
   - Contact Us
   - Filing a Complaint

**Expected:**
- [ ] All 12 sections are present
- [ ] Green lock icon badge displays at top
- [ ] Each section has clear heading
- [ ] Automatic deletion schedule is visible (24h, 90d, 91d)
- [ ] Contact emails are clickable links
- [ ] Page design matches app theme (green #22c55e)
- [ ] Readable on desktop (max-width container)

**Actual Result:**
_________________________________

---

## Mobile Responsiveness Testing

### Test 17: Mobile Viewport (360px width)
**Steps:**
1. Open DevTools (F12)
2. Click "Toggle device toolbar" icon (or Ctrl+Shift+M)
3. Select "iPhone SE" or set custom width to 360px
4. Go through Steps 1-5 of the quiz

**Expected:**
- [ ] No horizontal scroll at 360px width
- [ ] All buttons are ≥44px (tap-friendly)
- [ ] Text is readable (not too small)
- [ ] Food grid items display properly (may wrap to fewer columns)
- [ ] Step progress bar fits screen
- [ ] Next/Back buttons are easily tappable

**Actual Result:**
_________________________________

---

### Test 18: Mobile - Step 20 Unit Toggle
**Steps:**
1. Still in mobile view (360px)
2. Navigate to Step 20
3. Try toggling between Metric/Imperial
4. Enter biometric data
5. Select a goal

**Expected:**
- [ ] Unit toggle buttons are tappable (≥44px)
- [ ] Input fields fit screen width
- [ ] Privacy badge and notice are readable
- [ ] Goal buttons are large enough to tap

**Actual Result:**
_________________________________

---

## Performance Testing

### Test 19: Quiz Load Time
**Steps:**
1. Open DevTools → Network tab
2. Refresh page (F5)
3. Look at "DOMContentLoaded" and "Load" times at bottom of Network tab
4. Note the times

**Expected:**
- [ ] Quiz loads in <3 seconds on desktop
- [ ] No JavaScript errors in console

**Actual Result:**
Load time: _______ seconds
Errors: _________________________________

---

### Test 20: Step Transition Smoothness
**Steps:**
1. Navigate through Steps 1-5
2. Watch the transition animation between steps
3. Check if transitions are smooth (no jank/stuttering)

**Expected:**
- [ ] Transitions are smooth (300-400ms)
- [ ] No visible jank or stuttering
- [ ] Framer Motion animations work (if implemented)

**Actual Result:**
_________________________________

---

## Cross-Browser Testing (Optional)

### Test 21: Try Another Browser
**Steps:**
1. If you tested in Chrome, now try Firefox or Edge
2. Run through Tests 1-10 again in the new browser

**Expected:**
- [ ] Quiz works identically in different browsers
- [ ] No browser-specific bugs

**Actual Result:**
_________________________________

---

## Bug Documentation

### Bugs Found

**Bug #1:**
- **Severity**: Critical / High / Medium / Low
- **Location**: Step ___
- **Description**:
- **Steps to Reproduce**:
  1.
  2.
  3.
- **Expected**:
- **Actual**:
- **Screenshot**: (if applicable)

**Bug #2:**
_________________________________

**Bug #3:**
_________________________________

---

## Testing Summary

**Total Tests**: 21
**Tests Passed**: ___ / 21
**Tests Failed**: ___ / 21
**Bugs Found**: ___
**Critical Bugs**: ___
**Testing Duration**: ___ minutes

**Overall Assessment**:
- [ ] Ready for Phase 6 implementation
- [ ] Needs bug fixes before proceeding
- [ ] Major blockers found (describe): _________________________________

**Tester Signature**: ___________
**Date Completed**: ___________
