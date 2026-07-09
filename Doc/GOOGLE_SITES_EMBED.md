# Google Sites Embed Setup

## What updates automatically
- `run_bot.ps1` generates the report and refreshes Google Docs / Sheets through `publish_google_workspace.py`.
- Google Sites does **not** watch local `index.html` files directly.
- To show live updates in Google Sites, embed the Google Doc or Google Sheet that the bot updates.

## Recommended embed path
1. Create or choose one Google Sheet and, optionally, one Google Doc.
2. Share those files with the service account email from your Google credentials JSON.
3. Copy the file IDs into `google_workspace.local.ps1`:
   - `GOOGLE_APPLICATION_CREDENTIALS`
   - `GOOGLE_SHEETS_ID`
   - `GOOGLE_DOC_ID` if you want the report mirrored into Docs too
4. Run `run_bot.ps1` normally.
5. In Google Sites, use `Insert -> Drive` and embed the Sheet or Doc.

## What to embed
- If you want a compact live table, embed the Sheet.
- If you want a news-style reading view, embed the Doc.
- If you want both, put the Sheet on one section and the Doc in another.

## Notes
- The Doc output is formatted to keep the headline / timestamp / section structure.
- The Sheet output is split into `Report` and `Data` tabs for quick scanning.
- When Sheets or Docs are configured, the generated HTML report and email include direct links to the latest synced files.
- If you change the target Sheet or Doc, only update `google_workspace.local.ps1`.
