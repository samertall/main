"""Step Functions completion handler. Never logs report text or user input."""
import os
from datetime import datetime, timezone
import boto3
from botocore.exceptions import ClientError

def handler(event, _context):
    table = boto3.resource("dynamodb").Table(os.environ["REPORTS_TABLE"])
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    decision = event.get("decision")
    report_id = event["reportId"]
    if decision:
        values = {
            ":state": "complete", ":now": now,
            ":sev": decision["severity"], ":score": int(decision["priorityScore"]),
            ":wcag": decision["wcag"], ":principle": decision["principle"],
            ":recommendation": decision["recommendation"], ":rationale": decision["rationale"],
        }
        expr = "SET triageStatus=:state, updatedAt=:now, severity=:sev, priorityScore=:score, wcag=:wcag, principle=:principle, recommendation=:recommendation, rationale=:rationale"
    else:
        values = {":state": "needs_review", ":now": now}
        expr = "SET triageStatus=:state, updatedAt=:now"
    try:
        table.update_item(
            Key={"id": report_id},
            UpdateExpression=expr,
            ExpressionAttributeValues=values,
            ConditionExpression="attribute_exists(id)",
        )
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
            raise ValueError("Report no longer exists") from exc
        raise
    return {"reportId": report_id, "triageStatus": "complete" if decision else "needs_review"}
