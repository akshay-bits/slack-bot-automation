# How to Find Your Google Sheet ID

## Method 1: From the URL (Easiest)

1. **Open your Google Sheet** in a web browser
2. **Look at the URL** in the address bar
3. The URL will look like this:
   ```
   https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit#gid=0
   ```
4. **The Sheet ID** is the long string between `/d/` and `/edit`:
   ```
   1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms
   ```
   ↑ This is your SPREADSHEET_ID

## Method 2: From Google Drive

1. **Open Google Drive** (https://drive.google.com)
2. **Right-click on your spreadsheet**
3. Select **"Get link"** or **"Share"**
4. The link will contain the Sheet ID in the same format

## Method 3: Extract from Share Link

If someone shared a link with you:
- Format: `https://docs.google.com/spreadsheets/d/SHEET_ID_HERE/edit`
- Copy the `SHEET_ID_HERE` part

## Example:

If your URL is:
```
https://docs.google.com/spreadsheets/d/1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7/edit
```

Then your `SPREADSHEET_ID` in `.env` should be:
```
SPREADSHEET_ID=1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7
```

## Important Notes:

- The Sheet ID is **different** from the Sheet name
- The Sheet ID is a long alphanumeric string (usually 44 characters)
- It stays the same even if you rename the sheet
- You need the service account email to have access to this sheet

## After Getting the ID:

1. Update your `.env` file:
   ```bash
   SPREADSHEET_ID=your-actual-sheet-id-here
   ```

2. Make sure the service account has access:
   - Open the spreadsheet
   - Click "Share" button
   - Add the email from `google_credentials.json` (look for `client_email` field)
   - Give it at least "Viewer" permission

3. Restart Docker:
   ```bash
   docker-compose restart worker
   ```

