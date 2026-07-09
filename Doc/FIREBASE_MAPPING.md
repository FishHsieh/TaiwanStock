# Firebase Mapping

Last updated: 2026-06-29

## Purpose

This file explains how `vinson-stock-bot` is used in this repository.

## Mapping Table

| Item | Value | Meaning |
| --- | --- | --- |
| Firebase project alias | `vinson-stock-bot` | Default Firebase project used by the repo |
| Hosting URL | `https://vinson-stock-bot.web.app` | Public site URL after Firebase Hosting deploy |
| Firebase alias file | `.firebaserc` | Maps the default project name used by the CLI |
| Hosting config | `firebase.json` | Tells Firebase which local folder to publish |

## Where It Appears

- `.firebaserc`
- `QUICKSTART.md`
- `WORKFLOW_HANOFF.md`

## What Uses It

- `run_bot.ps1` deploys the generated web output through the local Firebase CLI.
- `QUICKSTART.md` and `WORKFLOW_HANOFF.md` point to the hosted site URL.
- The core data pipeline still runs in Python; `vinson-stock-bot` is only the Firebase deployment identity.
