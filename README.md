# ParentBridge AI

Source code for **ParentBridge AI — One Conversation, Every Channel** is in the [`parentbridge-ai/`](parentbridge-ai/) directory.

The application provides an offline demonstrator for consent-aware school-family communications with AWS SES and End User Messaging SMS SDK adapters, an optional Bedrock model integration, AWS SAM deployment infrastructure, and 19 automated tests.

**Important:** Offline preview simulates delivery. AWS deployment and live CDS service sends were not verified at publication time.

Run locally: `cd parentbridge-ai && python -m src.server --port 8787`.

See [full documentation](parentbridge-ai/README.md). MIT licensed.
