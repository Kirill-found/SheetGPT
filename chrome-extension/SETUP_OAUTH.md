# OAuth Setup for SheetGPT Chrome Extension

## Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Name it: **SheetGPT Extension**

## Step 2: Enable Google Sheets API

1. Go to **APIs & Services** → **Library**
2. Search for **Google Sheets API**
3. Click **Enable**

## Step 3: Configure OAuth Consent Screen

1. Go to **APIs & Services** → **OAuth consent screen**
2. Select **External**
3. Fill in:
   - App name: SheetGPT AI Assistant
   - User support email: your email
   - Developer contact: your email
4. Add scope: `https://www.googleapis.com/auth/spreadsheets`
5. Add your email to **Test users**

## Step 4: Create OAuth Client ID

1. Go to **APIs & Services** → **Credentials**
2. Click **Create Credentials** → **OAuth client ID**
3. Select **Chrome Extension**
4. Get your Extension ID:
   - Open `chrome://extensions/`
   - Find SheetGPT and copy the ID
5. Paste Extension ID in **Item ID** field
6. Copy the generated **Client ID**

## Step 5: Update manifest.json

Replace `YOUR_CLIENT_ID` in manifest.json:

```json
"oauth2": {
  "client_id": "YOUR_CLIENT_ID.apps.googleusercontent.com",
  "scopes": ["https://www.googleapis.com/auth/spreadsheets"]
}
```

## Step 6: Reload Extension

1. Open `chrome://extensions/`
2. Find SheetGPT
3. Click **Reload**

## Step 7: Test

1. Open any Google Sheets document
2. Open SheetGPT sidebar
3. Chrome will ask for Google Sheets permission
4. Click **Allow**

Done! 🎉
