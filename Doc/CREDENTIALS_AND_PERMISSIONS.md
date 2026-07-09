# Credentials and Permissions Checklist

Last updated: 2026-06-29

## Purpose

This project generates a daily report, syncs it to Google Sheets and Google Docs, publishes a web report, and deploys the site through Firebase Hosting.

## Required Google Identity

- Service account email: `taiwanstock-bot-publisher@taiwanstockbot-500607.iam.gserviceaccount.com`
- Google Cloud project ID: `taiwanstockbot-500607`

## Access That Must Be Granted

- Google Sheet ID `154_wkavzn289a-PuR-mMwb3USKNeW-gfLCkYFga-S6k`: Editor
- Google Doc ID `1UD2-7vvD90_Xs6xYAoypbcp2GCq0tcQbC8FJRGBbme0`: Editor
- Firebase project access for Hosting deploys, if the site needs to be published

## Local Credential Files

- `F:\TaiwanStockBot\taiwanstock.json`
  - Google service account JSON used by the project
  - Contains `private_key`, so keep it local and do not paste it into chat or commit it into shared output
- `F:\TaiwanStockBot\google_workspace.local.ps1`
  - Local environment bootstrap for Google Workspace sync
  - Loaded by `run_bot.ps1` when present

## Environment Variables

- `GOOGLE_APPLICATION_CREDENTIALS`
  - Points to `F:\TaiwanStockBot\taiwanstock.json`
- `GOOGLE_SHEETS_ID`
  - Points to the target Google Sheet
- `GOOGLE_DOC_ID`
  - Points to the target Google Doc

## Files That Use These Credentials

- `fetch_sheet_trade_context.py`
  - Reads the Google Sheet using the service account JSON
- `publish_google_workspace.py`
  - Syncs the generated report to Google Sheets and Google Docs
- `run_bot.ps1`
  - Loads `google_workspace.local.ps1` and runs the end-to-end pipeline

## Firebase Notes

- `firebase.json` only contains Hosting configuration.
- No separate Firebase Admin service-account JSON was found in this repository.
- The deployment flow uses the local Firebase CLI installed in the project, not a separate secret file in the repo.

## What To Share During Handoff

- Share the service account email with whoever manages Google Sheet / Doc permissions.
- Share the Sheet ID and Doc ID with the person granting access.
- Do not share the raw contents of `taiwanstock.json`.

## Quick Verification

- Confirm `google_workspace.local.ps1` exists and points to the local JSON file.
- Confirm the service account has edit access to the target Sheet and Doc.
- Run `run_bot.ps1` and verify Google sync and Hosting deploy succeed.

## Related Files

- [WORKFLOW_HANOFF.md](WORKFLOW_HANOFF.md)
- [FIREBASE_MAPPING.md](FIREBASE_MAPPING.md)