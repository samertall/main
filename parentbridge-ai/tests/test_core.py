import os
from unittest.mock import Mock
import pytest
from src.store import DemoStore
from src.core import Coordinator, UserInputError
from src.agent import Agent
from src.channels import ChannelGateway, DeliveryError, pick_channel
from src import settings

@pytest.fixture(autouse=True)
def safe_mode(monkeypatch):
    monkeypatch.setenv('APP_MODE','demo')
    monkeypatch.setenv('SEND_ENABLED','0')
    monkeypatch.delenv('BEDROCK_MODEL_ID',raising=False)

@pytest.fixture
def coordinator():
    return Coordinator(store=DemoStore())


def test_seed_has_four_demo_contacts(coordinator):
    d=coordinator.dashboard('maria')
    assert d['metrics']['conversations']==4
    assert d['metrics']['messages']>=10
    assert d['system']['mode']=='Local simulation'


def test_cross_channel_keeps_same_thread(coordinator):
    old=len(coordinator.store.messages('maria'))
    r=coordinator.inbound('maria','sms','switch to email',simulate=True)
    assert r['response']['channel']=='email'
    assert coordinator.store.get_contact('maria')['preferred_channel']=='email'
    assert len(coordinator.store.messages('maria'))==old+2
    r=coordinator.inbound('maria','email','Where are the homework resources?',simulate=True)
    assert r['response']['channel']=='email'
    assert len(coordinator.store.messages('maria'))==old+4


def test_no_sms_without_explicit_consent(coordinator):
    c=coordinator.store.get_contact('james')
    assert pick_channel(c,'sms')=='email'
    result=coordinator.inbound('james','email','Send homework resources',simulate=True)
    assert result['response']['channel']=='email'


def test_stop_prevents_further_sms(coordinator):
    r=coordinator.inbound('maria','sms','STOP',simulate=True)
    c=coordinator.store.get_contact('maria')
    assert c['consent_sms'] is False
    assert c['preferred_channel']=='email'
    assert r['opted_out'] is True
    assert r['response'] is None
    with pytest.raises(DeliveryError):
        ChannelGateway().deliver(c,'sms','Nope')


def test_sensitive_request_forces_handoff(coordinator):
    r=coordinator.inbound('noura','sms','My child has a nut allergy. Is the meal safe?',simulate=True)
    assert r['response']['handoff'] is True
    assert r['response']['intent']=='safety'
    assert 'office' in r['response']['body'].lower()


def test_scheduling_never_auto_confirms(coordinator):
    r=coordinator.inbound('james','email','Book conference tomorrow at noon please',simulate=True)
    assert r['response']['handoff'] is True
    assert 'will confirm' in r['response']['body'].lower()


def test_message_idempotency(coordinator):
    a=coordinator.inbound('maria','sms','Hello',external_id='abc',simulate=False)
    b=coordinator.inbound('maria','sms','Hello',external_id='abc',simulate=False)
    assert 'response' in a
    assert b['duplicate'] is True


def test_unknown_sender_is_not_registered(coordinator):
    r=coordinator.inbound_address('sms','+12025550999','Hi','unknown')
    assert r['ignored'] is True
    assert len(coordinator.store.list_contacts())==4


def test_create_requires_consent_and_e164(coordinator):
    with pytest.raises(UserInputError):
        coordinator.register({'name':'Alex Morgan','phone':'123','consent_sms':True})
    with pytest.raises(UserInputError):
        coordinator.register({'name':'Alex Morgan','email':'alex@example.org'})
    c=coordinator.register({'name':'Alex Morgan','email':'alex@example.org','consent_email':True})
    assert c['preferred_channel']=='email'


def test_live_ses_adapter_invokes_real_sdk_method(monkeypatch):
    monkeypatch.setenv('APP_MODE','aws');monkeypatch.setenv('SEND_ENABLED','1')
    monkeypatch.setenv('SES_FROM_EMAIL','verified@example.com')
    ses=Mock();ses.send_email.return_value={'MessageId':'ses-123'}
    c={'email':'parent@example.org','consent_email':True,'phone':'','consent_sms':False}
    r=ChannelGateway(ses=ses).deliver(c,'email','Hello family')
    assert r['status']=='sent'
    ses.send_email.assert_called_once()
    assert ses.send_email.call_args.kwargs['Destination']['ToAddresses']==['parent@example.org']


def test_live_sms_adapter_invokes_real_sdk_method(monkeypatch):
    monkeypatch.setenv('APP_MODE','aws');monkeypatch.setenv('SEND_ENABLED','1')
    monkeypatch.setenv('SMS_ORIGINATION_ID','origination-resource')
    sms=Mock();sms.send_text_message.return_value={'MessageId':'sms-123'}
    c={'phone':'+12025550101','consent_sms':True}
    r=ChannelGateway(sms=sms).deliver(c,'sms','Hello family')
    assert r['status']=='sent'
    assert sms.send_text_message.call_args.kwargs['DestinationPhoneNumber']=='+12025550101'
