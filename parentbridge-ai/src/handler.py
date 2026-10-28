"""AWS Lambda/API Gateway + SNS entry point; same dispatcher as local server."""
import base64
import email
import hmac
import json
import mimetypes
import pathlib
from email import policy
from email.utils import parseaddr
from urllib.parse import parse_qs
from .core import Coordinator, UserInputError
from . import settings

ROOT=pathlib.Path(__file__).resolve().parent.parent
WEB=ROOT / "web"


def response(status, body, headers=None, binary=False):
    default={"Cache-Control":"no-store","X-Content-Type-Options":"nosniff","Referrer-Policy":"no-referrer",
             "X-Frame-Options":"DENY","Content-Security-Policy":"default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'"}
    default.update(headers or {})
    if isinstance(body,(dict,list)):
        body=json.dumps(body,default=str)
        default["Content-Type"]="application/json; charset=utf-8"
    elif isinstance(body,bytes):
        body=base64.b64encode(body).decode() if binary else body.decode("utf-8",errors="replace")
    return {"statusCode":status,"headers":default,"body":body,"isBase64Encoded":binary}


def extract_email_body(raw):
    msg=email.message_from_string(raw,policy=policy.default)
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type()=="text/plain" and part.get_content_disposition()!="attachment":
                return str(part.get_content())[:2500]
        return ""  # do not process arbitrary HTML attachments
    return str(msg.get_content())[:2500] if msg.get_content_type()=="text/plain" else ""


def process_sns(event, coordinator=None):
    coordinator=coordinator or Coordinator()
    results=[]
    for record in event.get("Records",[]):
        if record.get("EventSource", record.get("eventSource"))!="aws:sns": continue
        packet=json.loads(record["Sns"]["Message"])
        if "messageBody" in packet and "originationNumber" in packet:
            results.append(coordinator.inbound_address("sms",packet["originationNumber"],
                packet["messageBody"],packet.get("inboundMessageId",record["Sns"]["MessageId"])))
        elif packet.get("notificationType")=="Received" and packet.get("content"):
            # SES receipt rule SNS action is configured by administrator, not a web request.
            verd=packet.get("receipt",{})
            if any(verd.get(k,{}).get("status")=="FAIL" for k in ("virusVerdict","spamVerdict","spfVerdict")):
                results.append({"ignored":True,"reason":"Email verification verdict failed"})
                continue
            raw=packet["content"]
            source=parseaddr(packet.get("mail",{}).get("source",""))[1]
            if not source:
                source=parseaddr(email.message_from_string(raw,policy=policy.default).get("From",""))[1]
            plain=extract_email_body(raw)
            if not plain.strip():
                results.append({"ignored":True,"reason":"No plain-text email content"})
                continue
            results.append(coordinator.inbound_address("email",source,
                plain, packet.get("mail",{}).get("messageId",record["Sns"]["MessageId"])))
        else:
            results.append({"ignored":True,"reason":"Unknown SNS event type"})
    return {"processed":results}


def authorized(headers):
    if not settings.is_live():return True
    token=settings.setting("ADMIN_API_KEY")
    if not token:return False
    usertoken=next((v for k,v in (headers or {}).items() if k.lower()=="x-admin-key"),"")
    return hmac.compare_digest(token,str(usertoken))


def dispatch(method,path,headers=None,raw_body="",query=None,coordinator=None):
    coordinator=coordinator or Coordinator()
    query=query or {}
    if method=="GET" and path=="/api/health":
        return response(200,{"ok":True,"service":"parentbridge-ai","mode":settings.setting("APP_MODE","demo")})
    if path.startswith("/api/"):
        if not authorized(headers):return response(401,{"error":"Admin key required or invalid"})
        try:
            data=json.loads(raw_body or "{}") if method in {"POST","PUT"} else {}
            if not isinstance(data,dict):raise UserInputError("Expected a JSON object")
            if method=="GET" and path=="/api/state":
                cid=query.get("contact_id")
                if isinstance(cid,list):cid=cid[0]
                return response(200,coordinator.dashboard(cid))
            if method=="POST" and path=="/api/message":
                if settings.is_live() and settings.setting("ALLOW_SIMULATION","0")!="1":
                    return response(403,{"error":"Synthetic inbound disabled in AWS mode"})
                result=coordinator.inbound(str(data.get("contact_id","")),str(data.get("channel","email")),
                                         data.get("text",""),simulate=True)
                return response(200,result)
            if method=="POST" and path=="/api/announce":
                msg=coordinator.announcement(str(data.get("contact_id","")),data.get("text",""),data.get("channel"))
                return response(200,{"message":msg})
            if method=="POST" and path=="/api/contacts":
                contact=coordinator.register(data)
                return response(201,{"contact":contact})
            return response(404,{"error":"Unknown API endpoint"})
        except (UserInputError, ValueError, json.JSONDecodeError) as exc:
            return response(400,{"error":str(exc)[:180]})
        except Exception:
            return response(500,{"error":"Request could not be completed. Check server logs."})
    if method!="GET":return response(405,{"error":"Method not allowed"})
    static_files={"/":"index.html","/index.html":"index.html","/app.css":"app.css","/app.js":"app.js"}
    filename=static_files.get(path)
    if not filename:return response(404,"Not found",{"Content-Type":"text/plain"})
    p=WEB / filename
    body=p.read_bytes()
    typ=mimetypes.guess_type(str(p))[0] or "text/plain"
    return response(200,body,{"Content-Type":typ+"; charset=utf-8","Cache-Control":"public, max-age=120"})


def lambda_handler(event,context):
    if isinstance(event,dict) and event.get("Records") and any(
        x.get("EventSource",x.get("eventSource"))=="aws:sns" for x in event["Records"]):
        return process_sns(event)
    http=event.get("requestContext",{}).get("http",{})
    method=http.get("method",event.get("httpMethod","GET"))
    path=event.get("rawPath",event.get("path","/"))
    raw=event.get("body","") or ""
    if event.get("isBase64Encoded"):
        raw=base64.b64decode(raw).decode("utf-8")
    q=parse_qs(event.get("rawQueryString", "")) if event.get("rawQueryString") else event.get("queryStringParameters",{})
    return dispatch(method,path,headers=event.get("headers",{}),raw_body=raw,query=q)
