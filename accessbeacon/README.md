# AccessBeacon — AWS Serverless Accessibility Triage

AccessBeacon helps product teams report, prioritize, and resolve accessibility barriers with explainable severity scores and suggested WCAG guidance.

## Public project links

- Source: https://github.com/samertall/main/tree/main/accessbeacon
- Interactive frontend preview: https://accessbeacon-weekend.vercel.app/

**Deployment status:** The Vercel preview works with browser-local data only. It is NOT connected to AWS. The AWS stack is supplied as deployable source but has not been deployed or verified from this account.

## AWS infrastructure

Browser -> API Gateway -> App Lambda -> DynamoDB.

App Lambda -> Step Functions Standard -> Classify Lambda -> Persist Lambda -> DynamoDB.

- AWS SAM infrastructure: template.yaml
- State machine: workflow/triage.asl.json
- API Gateway Lambda: src/app.py
- Deterministic accessibility classifier: src/triage.py
- Data persistence Lambda: src/persist.py
- API-connected AWS dashboard: src/index.html
- Standalone browser-local UI preview: preview/index.html

## Deploy to actual AWS (CloudShell)

Sign into an authorized AWS account and run:

    git clone https://github.com/samertall/main.git
    cd main/accessbeacon
    sam validate
    sam deploy --guided

Choose the stack name accessbeacon-weekend. Review the IAM permissions and stack change set before approving. AWS services may incur usage charges.

After the deployment, extract the actual AWS demo URL with:

    aws cloudformation describe-stacks --stack-name accessbeacon-weekend --query 'Stacks[0].Outputs[?OutputKey==`AppUrl`].OutputValue' --output text

That returned API Gateway address, not the Vercel preview, is the required AWS-backed endpoint for an end-to-end challenge demonstration.

## Verification checklist

1. Open the AWS AppUrl and confirm the interface loads.
2. Submit a synthetic accessibility report.
3. Confirm the report was persisted in DynamoDB.
4. Confirm the classification workflow succeeded in Step Functions.
5. Confirm score and WCAG guidance are saved, then resolve the report and refresh to verify persistence.
6. Record a public demo video shorter than 3 minutes and include its link in the AWS Builder Center submission.

## Limitations

This is a public hackathon prototype with no authentication, rate limiting, or WAF. Do not enter personal or confidential data. Configure billing alerts and clean up the stack after the challenge. Suggested WCAG mappings require professional validation and do not certify conformance.

## Creator

Samer Tallauze — https://samertall.com

Built for the AWS Builder Center Weekend Challenge: No Pipeline, No Problem (November 2026).
