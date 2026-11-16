"""One Lambda serves the website and its API through API Gateway HTTP API."""
import json
import os
import uuid
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import boto3
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError

ROOT = Path(__file__).parent
CATEGORIES = {"keyboard", "screen-reader", "contrast", "forms", "motion", "navigation"}
IMPACTS = {"blocked", "difficult", "inconsistent"}
STATUSES = {"open", "in_progress", "resolved"}
CHANNELS = {"website", "mobile", "other"}


def reply(status, payload, content_type="application/json; charset=utf-8"):
    content = json.dumps(payload, ensure_ascii=False, default=str) if not isinstance(payload, str) else payload
    return {
        "statusCode": status,
        "headers": {
            "content-type": content_type,
            "cache-control": "no-store",
            "x-content-type-options": "nosniff",
            "referrer-policy": "no-referrer",
            "x-frame-options": "DENY",
            "content-security-policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'",
        },
        "body": content,
    }


def error(status, message):
    return reply(status, {"error": message})


def table():
    return boto3.resource("dynamodb").Table(os.environ["REPORTS_TABLE"])


def validate_report(data):
    if not isinstance(data, dict):
        raise ValueError("Send a JSON object")
    title = str(data.get("title", "")).strip()
    detail = str(data.get("detail", "")).strip()
    category = data.get("category")
    impact = data.get("impact")
    channel = data.get("channel", "website")
    page_url = str(data.get("pageUrl", "")).strip()
    if not 5 <= len(title) <= 110:
        raise ValueError("Title must be between 5 and 110 characters")
    if len(detail) > 650:
        raise ValueError("Details must contain at most 650 characters")
    if category not in CATEGORIES or impact not in IMPACTS or channel not in CHANNELS:
        raise ValueError("Select a valid barrier, impact and channel")
    if len(page_url) > 300:
        raise ValueError("Page URL is too long")
    if page_url:
        parsed = urlsplit(page_url)
        if parsed.scheme not in ("https", "http") or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("Provide a valid HTTP or HTTPS page URL")
    return {"title": title, "detail": detail, "category": category, "impact": impact, "channel": channel, "pageUrl": page_url}


def make_report(fields):
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return {
        "id": str(uuid.uuid4()),
        **fields,
        "createdAt": now,
        "updatedAt": now,
        "expiresAt": int(time.time()) + 30 * 86400,
        "status": "open",
        "triageStatus": "processing",
    }


def serve_asset(path):
    files = {"/": ("index.html", "text/html; charset=utf-8")}
    if path not in files:
        return error(404, "Not found")
    filename, mime = files[path]
    body = (ROOT / filename).read_text(encoding="utf-8")
    return reply(200, body, mime)


def handler(event, _context):
    method = (event.get("requestContext", {}).get("http", {}).get("method") or event.get("httpMethod") or "GET").upper()
    path = event.get("rawPath") or event.get("path") or "/"
    if method == "GET" and path == "/":
        return serve_asset(path)

    if method == "GET" and path == "/health":
        return reply(200, {"status": "ok"})

    if method == "GET" and path == "/reports":
        try:
            result = table().scan(Limit=100)
            reports = sorted(result.get("Items", []), key=lambda r: r.get("createdAt", ""), reverse=True)[:40]
            for item in reports:
                item.pop("expiresAt", None)
            return reply(200, {"reports": reports, "partial": "LastEvaluatedKey" in result})
        except ClientError:
            return error(503, "Unable to load reports right now")

    if method == "POST" and path == "/reports":
        body = event.get("body") or ""
        if len(body.encode("utf-8")) > 8192:
            return error(413, "Request is too large")
        try:
            raw = json.loads(body)
            fields = validate_report(raw)
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            return error(400, str(exc))
        report = make_report(fields)
        try:
            table().put_item(Item=report, ConditionExpression="attribute_not_exists(id)")
            boto3.client("stepfunctions").start_execution(
                stateMachineArn=os.environ["TRIAGE_FLOW_ARN"],
                name="issue-" + report["id"],
                input=json.dumps({"reportId": report["id"], "category": report["category"], "impact": report["impact"]}),
            )
        except ClientError:
            try:
                table().update_item(
                    Key={"id": report["id"]},
                    UpdateExpression="SET triageStatus=:state",
                    ExpressionAttributeValues={":state": "needs_review"},
                )
            except ClientError:
                pass
            return error(503, "Saved report, but triage did not start. Please retry later.")
        report.pop("expiresAt")
        return reply(202, {"report": report})

    if path.startswith("/reports/"):
        report_id = path.rsplit("/", 1)[-1]
        try:
            uuid.UUID(report_id)
        except (ValueError, AttributeError):
            return error(400, "Invalid report ID")
        if method == "GET":
            try:
                item = table().get_item(Key={"id": report_id}).get("Item")
                if not item:
                    return error(404, "Report not found")
                item.pop("expiresAt", None)
                return reply(200, {"report": item})
            except ClientError:
                return error(503, "Unable to load this report")
        if method == "PATCH":
            try:
                body = event.get("body") or "{}"
                if len(body.encode("utf-8")) > 2048:
                    return error(413, "Request is too large")
                data = json.loads(body)
                status = data.get("status") if isinstance(data, dict) else None
                if status not in STATUSES:
                    return error(400, "Status must be open, in_progress or resolved")
                updated = table().update_item(
                    Key={"id": report_id},
                    UpdateExpression="SET #s=:s, updatedAt=:u",
                    ExpressionAttributeNames={"#s": "status"},
                    ExpressionAttributeValues={":s": status, ":u": datetime.now(timezone.utc).isoformat(timespec="seconds")},
                    ConditionExpression="attribute_exists(id)",
                    ReturnValues="ALL_NEW",
                )["Attributes"]
                updated.pop("expiresAt", None)
                return reply(200, {"report": updated})
            except (json.JSONDecodeError, TypeError):
                return error(400, "Invalid JSON")
            except ClientError as exc:
                if exc.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
                    return error(404, "Report not found")
                return error(503, "Unable to update this report")
    return error(404, "Not found")
