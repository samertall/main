"""Conversation store: deterministic local preview or AWS DynamoDB persistence."""
import copy
import datetime as dt
import threading
import uuid
from . import settings
from .sample_data import DEMO_CONTACTS, SEED_MESSAGES


def utc_now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds")


def new_message(contact_id, direction, channel, body, intent="general", status="delivered", engine="system"):
    return {"id":uuid.uuid4().hex[:14],"contact_id":contact_id,"direction":direction,
            "channel":channel,"body":body,"intent":intent,"status":status,
            "engine":engine,"created_at":utc_now()}


class DemoStore:
    def __init__(self, seed=True):
        self.lock = threading.RLock()
        self.contacts = {}
        self.threads = {}
        self.seen_events = set()
        if seed:
            for c in DEMO_CONTACTS:
                self.put_contact(copy.deepcopy(c))
            base = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=3)
            for cid, items in SEED_MESSAGES.items():
                for i, (direction, channel, body, intent) in enumerate(items):
                    msg = new_message(cid, direction, channel, body, intent)
                    msg["created_at"] = (base + dt.timedelta(minutes=7*i)).isoformat(timespec="milliseconds")
                    msg["handoff"] = intent == "handoff" or (intent == "scheduling" and direction == "outbound")
                    self.add_message(cid, msg)

    def list_contacts(self):
        with self.lock:
            return copy.deepcopy(list(self.contacts.values()))

    def get_contact(self, cid):
        with self.lock:
            return copy.deepcopy(self.contacts.get(cid))

    def find_contact(self, channel, address):
        key = "email" if channel == "email" else "phone"
        with self.lock:
            for c in self.contacts.values():
                if str(c.get(key, "")).lower() == str(address).lower():
                    return copy.deepcopy(c)
        return None

    def put_contact(self, contact):
        with self.lock:
            self.contacts[contact["id"]] = copy.deepcopy(contact)
            self.threads.setdefault(contact["id"], [])

    def add_message(self, cid, message):
        with self.lock:
            self.threads.setdefault(cid, []).append(copy.deepcopy(message))

    def messages(self, cid, limit=100):
        with self.lock:
            return copy.deepcopy(sorted(self.threads.get(cid, []), key=lambda x:x["created_at"])[-limit:])

    def claim_event(self, event_id):
        with self.lock:
            if event_id in self.seen_events:
                return False
            self.seen_events.add(event_id)
            return True


class DynamoStore:
    """Single-table datastore. Recommended to add tenant partitioning for multi-school production."""
    def __init__(self, table=None):
        import boto3
        self.table = table or boto3.resource("dynamodb", region_name=settings.region()).Table(settings.setting("DDB_TABLE"))

    def list_contacts(self):
        from boto3.dynamodb.conditions import Attr
        contacts = []
        kw = {"FilterExpression":Attr("sk").eq("PROFILE")}
        while True:
            page = self.table.scan(**kw)
            contacts.extend({k:v for k,v in item.items() if k not in {"pk","sk"}} for item in page.get("Items",[]))
            if not page.get("LastEvaluatedKey"): break
            kw["ExclusiveStartKey"] = page["LastEvaluatedKey"]
        return contacts

    def get_contact(self, cid):
        item = self.table.get_item(Key={"pk":"CONTACT#"+cid,"sk":"PROFILE"}).get("Item")
        return {k:v for k,v in item.items() if k not in {"pk","sk"}} if item else None

    def find_contact(self, channel, address):
        key = f"ADDRESS#{channel}#{str(address).lower()}"
        link = self.table.get_item(Key={"pk":key,"sk":"LINK"}).get("Item")
        return self.get_contact(link["contact_id"]) if link else None

    def put_contact(self, contact):
        import re
        if not re.fullmatch(r"[a-zA-Z0-9_-]{2,48}", contact["id"]):
            raise ValueError("Invalid contact ID")
        old = self.get_contact(contact["id"])
        with self.table.batch_writer() as batch:
            if old:
                for channel,key in (("email","email"),("sms","phone")):
                    if old.get(key):
                        batch.delete_item(Key={"pk":f'ADDRESS#{channel}#{str(old[key]).lower()}',"sk":"LINK"})
            batch.put_item(Item={**contact,"pk":"CONTACT#"+contact["id"],"sk":"PROFILE"})
            for channel,key in (("email","email"),("sms","phone")):
                if contact.get(key):
                    batch.put_item(Item={"pk":f'ADDRESS#{channel}#{str(contact[key]).lower()}',"sk":"LINK","contact_id":contact["id"]})

    def add_message(self, cid, message):
        item = {**message, "pk":"THREAD#"+cid,
                "sk":f"MSG#{message['created_at']}#{message['id']}"}
        self.table.put_item(Item=item)

    def messages(self, cid, limit=100):
        from boto3.dynamodb.conditions import Key
        response = self.table.query(KeyConditionExpression=Key("pk").eq("THREAD#"+cid)&Key("sk").begins_with("MSG#"),
                                    ScanIndexForward=False, Limit=min(100,max(1,limit)))
        return [{k:v for k,v in item.items() if k not in {"pk","sk"}} for item in reversed(response.get("Items", []))]

    def claim_event(self, event_id):
        try:
            self.table.put_item(Item={"pk":"EVENT#"+event_id[:180],"sk":"CLAIM","expires":int(dt.datetime.now(dt.timezone.utc).timestamp())+7*86400},
                                ConditionExpression="attribute_not_exists(pk)")
            return True
        except Exception as exc:
            if getattr(exc, "response", {}).get("Error", {}).get("Code") == "ConditionalCheckFailedException":
                return False
            raise

_store = None

def get_store():
    global _store
    if _store is None:
        _store = DynamoStore() if settings.is_live() else DemoStore()
    return _store


def set_store(store):
    global _store
    _store = store
