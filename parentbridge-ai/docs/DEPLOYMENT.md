# AWS Deployment and Live CDS Verification

The **local preview is not an AWS deployment**. Complete every step here to claim hackathon-eligible runtime use.

## AWS resources and responsible operation

AWS SAM provisions an HTTP API, a Lambda handler, DynamoDB table and an SNS topic. Amazon SES (email sender/domain and inbound recipient) and an AWS End User Messaging SMS two-way origination identity are account-level configurations with AWS service approval requirements. Amazon Bedrock model access is account- and region-dependent.

### 1. Prerequisites

- AWS account and permissions to create Lambda, DynamoDB, API Gateway, SNS, IAM and CloudFormation stacks.
- AWS CLI v2 authenticated to the intended account (`aws sts get-caller-identity`).
- AWS SAM CLI, Python 3.12, and a region that supports the selected messaging features.
- A verified Amazon SES sending email identity. If still in the SES sandbox, only approved/verified recipient emails may be used.
- For SMS, an approved origination identity and a two-way supported number (not an alphanumeric one-way Sender ID).
- A model enabled for Amazon Bedrock Converse, if using LLM-generated responses. The rules engine remains a non-AI fallback.
- Written opt-in records from actual recipients. Fictional demo addresses must never be used for live sending.

### 2. Deploy infrastructure

```bash
sam validate --lint
sam build
sam deploy --guided
```

Choose a stack such as `parentbridge-ai` and your approved region. Provide:

- `AdminApiKey`: a random secret (at least 24 characters). This is used in `x-admin-key` for all dashboard API requests in AWS mode; **do not add it to public JavaScript**.
- `SesFromEmail`: verified sender email for SES.
- `SmsOriginationIdentity`: approved EUM SMS origination identity, or blank when testing email only.
- `BedrockModelId`: approved model or inference profile ID (e.g. an approved Amazon Nova model compatible with `Converse`).
- `EnableRealSend`: **0** initially; only set to **1** after consent and service validation.
- `AllowSimulation`: **0** in normal AWS mode (only provider SNS events can start inbound conversations).

Note the `DashboardUrl`, `IncomingSnsTopicArn`, and `TableName` outputs. The dashboard requests a secret key when opened in AWS mode. It does not persist it to a cookie or browser storage.

### 3. Configure SES inbound email

1. In the SES receiving region, verify the relevant domain, set its MX record to the region's SES inbound endpoint, and create an active receipt rule set.
2. Add a receipt rule for an approved support address, e.g. `reply@school.example`. Add an **SNS action** pointing to `IncomingSnsTopicArn` with UTF-8 encoding and enable spam/virus scanning.
3. Ensure SES can publish to the SNS topic. The SAM template adds a topic policy for SES from the same AWS account; check receipt action/region policy requirements in your account.
4. Forward a small plain-text test email from a **registered opt-in contact**. The SNS notification's `content` holds the raw email and is parsed by `src/handler.py`. Messages with failed scan verdicts are ignored.
5. Attachments and HTML-only inbound emails are not processed by this prototype; keep tests to plain text.

References: [SES inbound SNS action](https://docs.aws.amazon.com/ses/latest/dg/receiving-email-action-sns.html) and [SES receipt notification contents](https://docs.aws.amazon.com/ses/latest/dg/receiving-email-notifications-contents.html).

### 4. Configure EUM SMS two-way messaging

1. Register/obtain an eligible two-way SMS phone number in the required destination country; check regulatory and country support.
2. Configure its **two-way messages destination** to publish to the SAM `IncomingSnsTopicArn`. Follow the AWS End User Messaging documentation to configure an appropriate SNS publish role and provider permissions.
3. Set `SmsOriginationIdentity` to the approved origination number, pool ARN or resource ID.
4. From an **authorized opt-in test phone**, send a text to the assigned number. The SNS event contains `originationNumber`, `messageBody`, and `inboundMessageId`.
5. Enable real sending only after tests and recipient consents: re-deploy with `EnableRealSend=1`.

Reference: [Two-way SMS SNS payload](https://docs.aws.amazon.com/sms-voice/latest/userguide/two-way-sms-payload.html).

### 5. Create real contacts securely

The admin dashboard's **New contact** requires explicit consent checkbox(es). For AWS mode the API is authenticated:

```bash
curl -X POST "https://YOUR_API_ID.execute-api.YOUR_REGION.amazonaws.com/api/contacts" \
  -H "x-admin-key: YOUR_SECRET_KEY" -H "Content-Type: application/json" \
  -d '{"name":"Approved Test Recipient","email":"verified-test@example.net","phone":"", "consent_email":true,"consent_sms":false,"preferred_channel":"email"}'
```

Never copy invented sample email addresses or phone numbers into AWS mode and never enable actual sends to a destination without consent. Contact identifiers and history are stored in encrypted DynamoDB. The demo uses an in-memory database and fictional example.org addresses.

### 6. Verify real CDS API calls

Using a consented registered contact, click **School announcement** and send a short message via SES, or send an inbound reply by the configured SMS number. Verify the logs and AWS service delivery metrics. Inspect `src/channels.py` and CloudWatch to confirm actual `send_email(...)` or `send_text_message(...)` execution. Record screenshots of AWS service configuration and logs (with all sensitive fields redacted) for the hackathon demo. A local simulated send does **not** establish CDS eligibility.

### 7. Production hardening beyond the hackathon

- Add an identity layer (Cognito or other IdP), per-tenant partitions, least-privilege IAM resource ARNs, queue worker / dead-letter queue, rate limiting and explicit deletion/retention policies.
- Replace the simple staff-review flag with a staff queue and resolution lifecycle.
- Use verified family identity before discussing educational records; review local data protection requirements and school privacy policies.
- Instrument bounce/complaint events and throttle, consent audit and suppression lists.
- Add explicit approval before any booking, academic data changes, billing or health-related decisions.

## Troubleshooting

- **SES MessageRejected**: verify sender identity, recipient sandbox status, region and sending permissions.
- **SMS not delivered**: confirm E.164 number, origination approval, spending quotas, country restrictions and two-way capabilities.
- **No inbound event**: confirm SNS topic ARN, receipt rule/phone routing, IAM publish role and Lambda subscription.
- **AI fallback**: the Bedrock model must be enabled in the region and allow `bedrock:InvokeModel` access; no API key is embedded in code.
- **Dashboard Unauthorized**: use the `AdminApiKey` passed during SAM deployment; the same value is never committed.
