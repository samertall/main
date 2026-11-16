# AccessBeacon — Serverless accessibility triage

AccessBeacon is an accessibility incident desk designed for AWS Lambda, Amazon API Gateway, DynamoDB and AWS Step Functions.

## Two release modes
- **Public interactive preview:** browser-local, clearly labeled, hosted on Vercel. This is not an AWS backend deployment.
- **Full AWS implementation:** production-source package with AWS SAM (Lambda functions, DynamoDB table, and Step Functions state machine), deployment instructions, and tests; preserved in the AccessBeacon challenge ZIP distributed with the project.

For the AWS weekend challenge, deploy the full SAM project to your own authorized AWS account and use that AWS URL for the *real end-to-end demonstration*. The browser preview must not be represented as evidence of AWS execution.

**Creator:** Samer Tallauze · https://samertall.com

Source package includes `template.yaml`, `src/app.py`, `src/triage.py`, `src/persist.py`, `workflow/triage.asl.json`, frontend code, docs, and tests.

This repo folder is an independent project area in Samer's multi-project `main` repository.
