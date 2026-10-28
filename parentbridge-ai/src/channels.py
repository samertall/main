"""AWS CDS runtime adapters. No sends in preview; explicit consent required."""
import re
from . import settings

class DeliveryError(RuntimeError):
    pass


def allowed(contact, channel):
    if channel not in {"email", "sms"}:
        return False
    return bool(contact.get("consent_"+channel)) and bool(contact.get("email" if channel=="email" else "phone"))


def pick_channel(contact, requested=None):
    for channel in [requested,contact.get("preferred_channel"),"email","sms"]:
        if channel and allowed(contact,channel):
            return channel
    return None


class ChannelGateway:
    def __init__(self, ses=None, sms=None):
        self.ses=ses
        self.sms=sms

    def deliver(self, contact, channel, body, subject="ParentBridge school update"):
        if not allowed(contact,channel):
            raise DeliveryError("Consent or address missing for this channel")
        if not settings.can_send():
            return {"status":"simulated" if not settings.is_live() else "disabled", "provider_id":None}
        if channel=="email":
            sender=settings.setting("SES_FROM_EMAIL")
            if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+",sender):
                raise DeliveryError("Verified SES_FROM_EMAIL is required")
            if self.ses is None:
                import boto3
                self.ses=boto3.client("sesv2",region_name=settings.region())
            response=self.ses.send_email(
                FromEmailAddress=sender,
                Destination={"ToAddresses":[contact["email"]]},
                Content={"Simple":{"Subject":{"Data":subject,"Charset":"UTF-8"},
                    "Body":{"Text":{"Data":body,"Charset":"UTF-8"}}}}
            )
        else:
            orig=settings.setting("SMS_ORIGINATION_ID")
            if not orig:
                raise DeliveryError("SMS_ORIGINATION_ID is required")
            if self.sms is None:
                import boto3
                self.sms=boto3.client("pinpoint-sms-voice-v2",region_name=settings.region())
            response=self.sms.send_text_message(
                DestinationPhoneNumber=contact["phone"], OriginationIdentity=orig,
                MessageBody=body[:1400], MessageType="TRANSACTIONAL"
            )
        return {"status":"sent", "provider_id":response.get("MessageId")}
