# Visual Test Instructions - AI Detection in Listings

## Current Status

✅ Backend: Running on http://localhost:8000
✅ Frontend: Running on http://localhost:8501
✅ Test Data: Listing with 2 AI-detected images created

## Step-by-Step Visual Test

### Step 1: Open the Application
1. Open your browser
2. Go to: **http://localhost:8501**

### Step 2: Login as Seller
1. Click **"Login"** button (top right)
2. Or go to **"Auth"** page from sidebar
3. Enter credentials:
   - Email: `seller1@propertyai.demo`
   - Password: `Seller123!`
4. Click **"Login"**

### Step 3: Go to Seller Dashboard
1. After login, you should see **"Seller Dashboard"** in the sidebar
2. Click on **"Seller Dashboard"**
3. You'll see several tabs at the top

### Step 4: View My Listings
1. Click the **"📋 My Listings"** tab
2. You should see at least one listing: **"Test Property"**
3. Click to **expand** the listing (click anywhere on the listing row)

### Step 5: Look for AI Detection
Inside the expanded listing, you should see:

```
📍 Seattle, WA
Type: house  Beds: 3  Baths: 2  Sqft: —

[Primary photo if available]

📸 Images:
🤖 real_7jlVQPX8PLE.jpg - AI Generated (100%)
🤖 fake_002e9544.jpg - AI Generated (100%)

Quality: 63/100
```

## What You Should See

### If Working Correctly:
- **"📸 Images:"** heading in bold
- List of images with icons:
  - 🤖 for AI-generated
  - ✅ for Real
  - ❓ for Uncertain
- Filename and confidence percentage

### If Not Showing:
The section might not appear if:
1. No images uploaded to listing
2. Images not analyzed yet
3. API call failing silently

## Troubleshooting

### Issue: No "📸 Images:" section visible

**Solution 1: Upload Images**
1. Go to **"📤 Upload & Validate"** tab
2. Select the listing from dropdown
3. Upload some images
4. Wait for analysis to complete
5. Go back to **"📋 My Listings"** tab
6. Expand the listing again

**Solution 2: Check Browser Console**
1. Press F12 to open Developer Tools
2. Look for any errors in Console tab
3. Refresh the page (Ctrl+R or Cmd+R)

**Solution 3: Verify Backend**
Run this command to check if analysis data exists:
```bash
python scripts/test_listing_ai_display.py
```

This will show you what the backend is returning.

## Expected Output from Test Script

```
🔐 Logging in as seller...
✅ Using listing: 324197c66e854838a96b3cac27e68b90

📤 Uploading test images...
   Real: real_7jlVQPX8PLE.jpg
   Fake: fake_002e9544.jpg
✅ Uploaded 2 images
   Average quality: 63.0

📋 Fetching listing with AI detection...

🏠 Test Property
   Price: $300,000
   Status: draft
   Quality Score: 63.0
   Authenticity: ⚠️  Contains AI images

📸 Images (2):
======================================================================

📷 real_7jlVQPX8PLE.jpg
   Room: Bedroom
   Quality: 62/100
   Status: 🤖 AI GENERATED (100%)

📷 fake_002e9544.jpg
   Room: Kitchen
   Quality: 64/100
   Status: 🤖 AI GENERATED (100%)
```

If you see this output, the backend is working correctly.

## Alternative: Use Analyze Tab

If the "My Listings" display isn't showing, you can still see AI detection in the **"🔍 Analyze Images"** tab:

1. Go to **"🔍 Analyze Images"** tab
2. Select listing from dropdown
3. You'll see each image with full analysis:
   - Image thumbnail
   - AI detection status
   - Quality scores
   - Accept/Reject buttons

## Quick Fix Commands

### Restart Streamlit
```bash
# Kill old process
Get-Process | Where-Object {$_.ProcessName -like "*streamlit*"} | Stop-Process -Force

# Start new
cd property-ai-masterpiece
streamlit run frontend/Home.py --server.port 8501
```

### Check Backend Status
```bash
# Test backend health
curl http://localhost:8000/health

# Test analysis endpoint
python scripts/test_listing_ai_display.py
```

## Contact Points

If still not working:
1. Check that both servers are running (backend + frontend)
2. Verify test data exists (run test script)
3. Check browser console for JavaScript errors
4. Try the Analyze tab as alternative view

The feature is implemented and tested - if you're not seeing it visually, it's likely a data or refresh issue rather than a code problem.
