# Privacy, safety and responsible AI

**Scope:** This is a fictional school-family communication prototype, not an operational education service.

- All sample families, students, email addresses and phone numbers are synthetic. Domain `example.org` and the displayed portal URL are placeholders.
- Do not process actual student records, diagnoses, emergencies, payments or contact information in this demo.
- Never add contacts without explicit consent to the requested communications channel. The API enforces consent before sending.
- SMS keywords STOP, UNSUBSCRIBE, CANCEL, END and QUIT immediately disable the app's SMS consent flag and suppress the automated reply. Provider-level opt-out handling should also be configured.
- Email content is accepted as plain text only; unrecognized senders are ignored. SES spam/virus FAIL verdicts are rejected. External messages are treated as untrusted text.
- Human handoff flags appear for allergies, medical, emergency, transport, finance, attendance and unconfirmed scheduling. No actual appointments or account changes are made automatically.
- The Bedrock system instructions restrict responses to synthetic school facts and require structured output. A deterministic rules fallback is explicitly identified; neither is a substitute for human review.
- No live API key is stored in the frontend code. AWS mode requires an admin key for API access. A real deployment requires stronger auth, tenancy, auditability and data retention controls.
- In production, collect only necessary data, implement deletion requests, ensure regional legal review and use appropriate school privacy agreements.
