"""Conversation orchestration: cross-channel context, consent and escalation."""
import re
import uuid
from .agent import Agent
from .channels import ChannelGateway, DeliveryError, pick_channel, allowed
from .store import new_message, get_store
from . import settings

class UserInputError(ValueError):
    pass


class Coordinator:
    def __init__(self, store=None, agent=None, gateway=None):
        self.store=store or get_store()
        self.agent=agent or Agent()
        self.gateway=gateway or ChannelGateway()

    def dashboard(self, cid=None):
        contacts=self.store.list_contacts()
        views=[]
        for c in contacts:
            messages=self.store.messages(c["id"])
            views.append({**c,"last_message":messages[-1]["body"] if messages else "No conversation yet",
                          "last_at":messages[-1]["created_at"] if messages else "",
                          "unresolved":sum(bool(m.get("handoff")) for m in messages if m["direction"]=="outbound")})
        views.sort(key=lambda x:x["last_at"],reverse=True)
        chosen=cid if any(c["id"]==cid for c in contacts) else (views[0]["id"] if views else None)
        all_msgs=[m for c in contacts for m in self.store.messages(c["id"])]
        escalations=sum(1 for m in all_msgs if m.get("handoff"))
        return {"contacts":views,"active_contact":chosen,
                "messages":self.store.messages(chosen) if chosen else [],
                "metrics":{"conversations":len(contacts),"messages":len(all_msgs),"handoffs":escalations,
                           "channels":len({m["channel"] for m in all_msgs})},
                "system":{"mode":"AWS connected" if settings.is_live() else "Local simulation",
                    "ai":"Bedrock configured" if settings.is_live() and settings.setting("BEDROCK_MODEL_ID") else "Rules preview",
                    "delivery":"Enabled" if settings.can_send() else "Simulated / disabled"}}

    def register(self, data):
        name=str(data.get("name", "")).strip()[:90]
        email=str(data.get("email", "")).strip().lower()
        phone=str(data.get("phone", "")).strip()
        if len(name)<2: raise UserInputError("A contact name is required")
        if email and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+",email):
            raise UserInputError("Invalid email")
        if phone and not re.fullmatch(r"\+[1-9][0-9]{7,14}",phone):
            raise UserInputError("Use E.164 phone numbers, e.g. +12025550101")
        if not email and not phone: raise UserInputError("An email or phone is required")
        consent_email=data.get("consent_email") is True
        consent_sms=data.get("consent_sms") is True
        if not consent_email and not consent_sms: raise UserInputError("At least one explicit consent is required")
        cid=uuid.uuid4().hex[:12]
        contact={"id":cid,"name":name,"initials":"".join(w[0] for w in name.split()[:2]).upper(),
            "role":str(data.get("role","Family member"))[:70],"child":"Not displayed",
            "email":email,"phone":phone,"preferred_channel":str(data.get("preferred_channel","email")),
            "consent_email":consent_email,"consent_sms":consent_sms,"status":"active","segment":"New contact"}
        if not allowed(contact,contact["preferred_channel"]):
            contact["preferred_channel"]=pick_channel(contact)
        if not contact["preferred_channel"]:
            raise UserInputError("Consent must match a provided email or phone number")
        self.store.put_contact(contact)
        return contact

    def inbound(self, cid, channel, text, external_id=None, simulate=False):
        contact=self.store.get_contact(cid)
        if not contact: raise UserInputError("Unknown contact")
        if channel not in {"sms","email"}: raise UserInputError("Use email or sms")
        text=str(text).strip()
        if not text or len(text)>2500: raise UserInputError("Message must contain 1-2500 characters")
        if external_id and not self.store.claim_event(channel+":"+external_id):
            return {"duplicate":True,"contact_id":cid}
        if simulate and settings.is_live() and settings.setting("ALLOW_SIMULATION","0")!="1":
            raise UserInputError("Synthetic inbound disabled in AWS mode")
        stop = channel=="sms" and text.upper() in {"STOP","UNSUBSCRIBE","CANCEL","END","QUIT"}
        if stop:
            contact["consent_sms"]=False
            if contact.get("preferred_channel")=="sms":
                contact["preferred_channel"]=pick_channel(contact,"email")
            self.store.put_contact(contact)
        elif text.lower().strip() in {"use email","reply by email","email please","switch to email"}:
            if allowed(contact,"email"):
                contact["preferred_channel"]="email";self.store.put_contact(contact)
        elif text.lower().strip() in {"use sms","reply by sms","text please","switch to sms"}:
            if allowed(contact,"sms"):
                contact["preferred_channel"]="sms";self.store.put_contact(contact)
        incoming=new_message(cid,"inbound",channel,text)
        self.store.add_message(cid,incoming)
        if stop:
            return {"contact_id":cid,"message":incoming,"response":None,"opted_out":True}
        history=self.store.messages(cid)
        channel_cmd=text.lower().strip() in {"use email","reply by email","email please","switch to email","use sms","reply by sms","text please","switch to sms"}
        if channel_cmd:
            preferred=contact.get("preferred_channel")
            response={"intent":"channel","reply":f"Thanks. Future replies will use {preferred.upper()} when available and permitted.","handoff":False,"engine":"routing"}
        else:
            response=self.agent.reply(contact,text,history)
        destination=pick_channel(contact)
        if not destination:
            response["handoff"]=True
            reply=new_message(cid,"outbound",channel,"A member of our team will review your request.","human","blocked","routing")
            reply["handoff"]=True;self.store.add_message(cid,reply)
            return {"contact_id":cid,"message":incoming,"response":reply}
        try:
            delivery=self.gateway.deliver(contact,destination,response["reply"])
            status=delivery["status"]
        except Exception:
            status="failed"
            response["handoff"]=True
        reply=new_message(cid,"outbound",destination,response["reply"],response["intent"],status,response["engine"])
        reply["handoff"]=response["handoff"]
        self.store.add_message(cid,reply)
        return {"contact_id":cid,"message":incoming,"response":reply,"preferred_channel":destination}

    def inbound_address(self, channel, address, text, external_id):
        contact=self.store.find_contact(channel,address)
        if not contact:
            return {"ignored":True,"reason":"Unknown sender; not auto-enrolled"}
        return self.inbound(contact["id"],channel,text,external_id=external_id)

    def announcement(self,cid,text,channel=None):
        contact=self.store.get_contact(cid)
        if not contact:raise UserInputError("Unknown contact")
        text=str(text).strip()
        if not text or len(text)>1800:raise UserInputError("Message must contain 1-1800 characters")
        destination=pick_channel(contact,channel)
        if not destination:raise UserInputError("No consented channel is available")
        delivery=self.gateway.deliver(contact,destination,text,subject="Message from Cedar Grove Academy")
        msg=new_message(cid,"outbound",destination,text,"announcement",delivery["status"],"staff")
        self.store.add_message(cid,msg)
        return msg
