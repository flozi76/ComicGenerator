---
title: Privacy Policy
---

# Privacy Policy — ComicGenerator

_Last updated: 2026-05-31_

## 1. Overview

ComicGenerator ("the app") is a personal, open-source command-line tool run by
an individual on their own computer. It has no servers, no user accounts, and
no analytics. It does not collect, sell, or share personal data from any third
parties. This policy explains the limited data the app handles to do its job.

## 2. Data the app handles

The app runs entirely on the operator's local machine. The only data it stores
or transmits is what is needed to generate a comic and upload it to the
operator's **own** TikTok account:

- **API keys / credentials** — your OpenAI (and/or other provider) API key and
  your TikTok app `client_key` / `client_secret`, read from a local
  `config.yml`. These never leave your machine except as part of authenticated
  requests to those providers.
- **TikTok OAuth tokens** — after you authorize the app, an access token and
  refresh token are cached locally in `tiktok_token.json` so the app can upload
  on your behalf. These are stored only on your machine and are used solely to
  call the TikTok Content Posting API.
- **Generated content** — the comic images and the rendered video are written
  to a local `output/` folder and uploaded to your own TikTok drafts (inbox
  mode) or profile (direct mode).

## 3. What the app does NOT do

- It does **not** collect data about other people or other TikTok users.
- It does **not** read your TikTok content, followers, messages, or analytics.
- It does **not** send your data to the operator or to any third party other
  than the API providers required to perform the request you initiated
  (content generation and TikTok upload).
- It has **no** tracking, advertising, or profiling.

## 4. TikTok scopes used

The app requests only the minimum TikTok scopes needed to upload video on your
behalf:

- `video.upload` — upload a video to your TikTok drafts (inbox mode).
- `video.publish` — only if you opt into direct-post mode.
- `user.info.basic` — used by Login Kit to complete authorization.

## 5. Data retention

Credentials and tokens persist locally only as long as the files
(`config.yml`, `tiktok_token.json`) exist on your machine. Delete those files
to remove all stored credentials. The operator holds no copy.

## 6. Third-party policies

Data sent to third-party providers is governed by their privacy policies, e.g.:

- [TikTok Privacy Policy](https://www.tiktok.com/legal/privacy-policy)
- [OpenAI Privacy Policy](https://openai.com/policies/privacy-policy)

## 7. Children

The app is not directed to children and collects no data from them.

## 8. Changes

This policy may be updated from time to time; the "last updated" date above
reflects the latest revision.

## 9. Contact

Questions: flozi76@gmail.com
