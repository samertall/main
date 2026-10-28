# ParentBridge AI — three-minute demonstration script

**Recording requirement:** State clearly whether the recording shows the local simulation or a deployed AWS build. Do not imply that a screenshot of the local demo proves live CDS calls. Capture actual AWS console/runtime evidence only after deployment.

**00:00–00:20 | The customer problem**

"School messages are fragmented. A parent receives an SMS, replies with a concern, and later has to repeat everything over email. ParentBridge is a small conversational command center that carries context with the family."

**00:20–00:45 | Operator dashboard**

Show the four actual computed metrics, consent-first contact directory, and inbox. Point out each contact's preferred channel.

**00:45–01:15 | Two-way messaging**

Open Maria's conversation. In *Simulate parent reply*, choose SMS and type `Can I have the homework resources?` Show how a response is added to the same thread. State: "This local preview uses safe rules and no actual sending."

**01:15–01:45 | Cross-channel continuity**

In the same thread, enter `switch to email`. The next response appears tagged Email without losing the SMS history. Explain: "An AWS deployment uses SES for outbound email and End User Messaging SMS for text. SNS carries provider replies to Lambda, and DynamoDB retains conversation history."

**01:45–02:10 | Responsible agentic handoff**

Type `My child has a nut allergy. Is the food safe?` and show the staff handoff flag, no invented medical advice or unapproved decision.

**02:10–02:35 | Architecture & AWS services**

Open architecture modal and show `assets/architecture.svg`. Briefly identify SES v2, EUM SMS, SNS, Lambda, DynamoDB and Bedrock Converse. Show code methods `send_email()` and `send_text_message()` and the test suite.

**02:35–03:00 | Packaging & call to action**

Show the family directory and insights. Explain the AWS SAM stack and repeatable SaaS product potential for schools. If AWS is deployed, show a redacted successful provider event and CloudWatch log. End: "ParentBridge makes every message a continuation, not a restart."
