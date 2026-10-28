import json
import os
from email.message import EmailMessage
from src.handler import dispatch,process_sns,lambda_handler,extract_email_body
from src.core import Coordinator
from src.store import DemoStore


def setup_function():
    os.environ['APP_MODE']='demo'

def test_api_state_and_static_assets():
    c=Coordinator(store=DemoStore())
    result=dispatch('GET','/api/state',coordinator=c)
    assert result['statusCode']==200
    assert json.loads(result['body'])['metrics']['conversations']==4
    page=dispatch('GET','/',coordinator=c)
    assert page['statusCode']==200
    assert 'parentbridge' in page['body']
    assert 'text/html' in page['headers']['Content-Type']

def test_post_inbound_api_roundtrip():
    c=Coordinator(store=DemoStore())
    response=dispatch('POST','/api/message',raw_body=json.dumps({'contact_id':'maria','channel':'sms','text':'Can I get the homework resources?'}),coordinator=c)
    result=json.loads(response['body'])
    assert response['statusCode']==200
    assert result['response']['intent']=='resources'
    assert result['response']['status']=='simulated'

def test_post_rejects_invalid_data():
    r=dispatch('POST','/api/message',raw_body='invalid-json',coordinator=Coordinator(store=DemoStore()))
    assert r['statusCode']==400

def test_sns_sms_inbound_is_processed():
    c=Coordinator(store=DemoStore())
    event={'Records':[{'EventSource':'aws:sns','Sns':{'Message':json.dumps({'originationNumber':'+12025550101','messageBody':'Can we meet the teacher?','inboundMessageId':'e1'}),'MessageId':'event1'}}]}
    r=process_sns(event,coordinator=c)
    assert r['processed'][0]['response']['intent']=='scheduling'
    assert r['processed'][0]['response']['channel']=='sms'

def test_sns_ses_email_inbound_is_processed():
    c=Coordinator(store=DemoStore())
    msg=EmailMessage();msg['From']='James Reed <james@example.org>';msg['To']='school@example.org';msg['Subject']='Meeting';msg.set_content('Can I book a conference?')
    event={'Records':[{'EventSource':'aws:sns','Sns':{'Message':json.dumps({'notificationType':'Received','content':msg.as_string(),'mail':{'source':'james@example.org','messageId':'email-e1'},'receipt':{'virusVerdict':{'status':'PASS'}}}),'MessageId':'e2'}}]}
    r=process_sns(event,coordinator=c)
    assert r['processed'][0]['response']['channel']=='email'

def test_ses_malformed_email_is_ignored_by_known_sender():
    assert extract_email_body('From: abc@example.org\nContent-Type: text/html\n\n<html>hi</html>')==''

def test_lambda_api_gateway_v2():
    e={'requestContext':{'http':{'method':'GET'}},'rawPath':'/api/health','headers':{}}
    r=lambda_handler(e,None)
    assert r['statusCode']==200

def test_protect_live_api_without_token(monkeypatch):
    monkeypatch.setenv('APP_MODE','aws')
    monkeypatch.setenv('ADMIN_API_KEY','very-long-secret-key-123456')
    r=dispatch('GET','/api/state',coordinator=Coordinator(store=DemoStore()))
    assert r['statusCode']==401
