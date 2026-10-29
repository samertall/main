# SafeSignal — pause, check, proceed with confidence

**SafeSpace Hacks 2026** · Privacy-first, explainable scam-message triage.

## Problem and intended user
Everyday people receive texts, emails and DMs that pressure them to click, disclose secrets or pay. They need a calm, accessible way to understand common warning signs before acting.

## What you can do
1. Load the live website, or double-click `standalone.html` in this ZIP to open the standalone demo offline.
2. Select one of three fictional examples or paste text with personal information removed.
3. Click **Check message**. Read the caution category, the specific signs, and inert link hosts.
4. Select **Copy guidance** to copy general advice *without the original message*.
5. Browse **Practice scenarios**, **Safety checklist**, and **How it works**.

No account, API key, installation, third-party dependency or backend is required.

## Technologies
Plain modern JavaScript (deterministic rules), semantic HTML, responsive CSS, SVG, PWA service worker and web app manifest. Browser-based local processing; no tracking, network requests to classify text, external fonts or cookies. PWA caching is enabled on HTTPS hosting after the first visit; the single-file standalone demo works without connectivity and does not require a PWA install.

## Example of a safer outcome
A fictional parcel message demands verification via `https://delivery-confirm.example/track` within 24 hours. SafeSignal explains the urgency and suggests opening the real courier's application instead of the supplied link. The user can verify independently without visiting the suspicious URL.

## Clear limitations
SafeSignal provides **rules-based caution, not an assessment of absolute safety**. No configured warning signs does not mean a message is trustworthy. It cannot verify a real sender, detect novel scams, check domain reputation, inspect shortened final URLs, visit websites, scan attachments, or provide emergency help. False positives and false negatives are possible. The heuristics are educational and are not externally validated as a security product.

## Running locally
Open `standalone.html` directly from your computer. For the multi-file edition, run `python -m http.server 4173` from the source directory then visit `http://localhost:4173`.

## Testing
- `node --test tests/scanner.test.mjs` (9 deterministic engine tests)
- `python tests/browser_smoke.py` (Chromium desktop/mobile in isolated browser fixture; full browser test captures screenshots)

## Built during the event
All application design, markup, CSS, scanner engine, sample data, tests and docs were written on October 29, 2026, within the event period. No pre-existing application was reused.

## Credits
- Product concept, UI, implementation and testing: created for this submission with assistance from ChatGPT (OpenAI).
- No third-party libraries, training datasets or real user data.
- System fonts; inline SVG original icon; text-only synthetic examples on `.example` domains.
- MIT-licensed source (see LICENSE). Screenshot and demo materials generated from this application.

## Responsible disclosure
Please test only the provided synthetic examples or text you have permission to process. Do not paste passwords, personal information, real credentials, or live vulnerabilities.