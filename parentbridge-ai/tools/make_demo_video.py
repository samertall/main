"""Create a narrated, explicitly SIMULATED 3-minute UI walkthrough.

Requires: Pillow, espeak and ffmpeg. Uses UI screenshots made from the app itself.
This recording is not evidence of an AWS cloud deployment.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import subprocess, json, os, wave, textwrap

ROOT=Path(__file__).resolve().parents[1]
AS=ROOT/'assets'
TMP=ROOT/'.video-temp'; TMP.mkdir(exist_ok=True)
SIZE=(1280,720)
SCENES=[
('One conversation. Every channel.', 'Introducing ParentBridge AI, a conversation assistant for school families. It unifies email and SMS in one shared thread. Parents can continue where they left off instead of explaining things repeatedly. This is a local demonstration with simulated messages.', '01-inbox', 'full'),
('The customer problem', 'School communication is usually scattered. Announcements arrive through multiple channels, questions are lost across inboxes, and families may not know whether a request reached the right person. ParentBridge is designed to close the loop between a question and a helpful, accountable response.', '01-inbox', 'full'),
('A unified family inbox', 'The operator can see active families, total messages, channels and questions that need a human. Every contact has a single profile and preferred channel. These are actual metrics from the local demo dataset, not fabricated reach or conversion figures.', '01-inbox', 'left'),
('Two-way conversation', 'Now a parent responds over SMS, asking for learning resources. The app identifies the request and creates a grounded, useful response. In this local preview, deterministic rules power the answer, so we never pretend to be calling a cloud model without credentials.', '02-resources', 'chat'),
('SMS to email. No restart.', 'A parent switches from SMS to email. ParentBridge updates their preference but retains the same conversation history. The next reply is labeled email, and earlier SMS messages remain visible. Cloud delivery requires deployment and verified consent.', '03-channel-switch', 'chat'),
('Human judgment for sensitive needs', 'When a parent asks about a food allergy, the assistant does not invent a safety guarantee. Instead, the request is marked for school staff review. The design reserves healthcare, transport, payment, attendance and confirmed appointments for accountable human decisions.', '04-handoff', 'chat'),
('Consent-aware outreach', 'Staff can send announcements using the opted-in channel. Our AWS adapters support Amazon SES for email and End User Messaging for SMS. In this preview, delivery is simulated so no real family receives a message.', '05-announcement', 'chat'),
('The right to opt out', 'If a parent sends the STOP keyword on SMS, ParentBridge immediately disables SMS consent and suppresses automated text responses. The family can still use an approved alternative channel. No further outbound SMS should go to an opted-out recipient.', '06-optout', 'chat'),
('A better operational picture', 'The directory displays per-channel consent and the insight screen summarizes the shared message history. As schools scale, the same pattern can support accessible family experiences while keeping staff in control of the conversations that require their judgment.', '08-insights', 'full'),
('Built around real AWS services', 'SNS receives replies. Lambda routes messages. DynamoDB stores history. Bedrock can generate replies. SES sends email and End User Messaging sends texts. This is an AWS-ready design awaiting live verification.', 'architecture', 'architecture'),
]

def font(size,bold=False):
    path='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    return ImageFont.truetype(path,size)

def roundmask(size,radius=12):
    m=Image.new('L',size,0); d=ImageDraw.Draw(m);d.rounded_rectangle((0,0,size[0]-1,size[1]-1),radius,fill=255);return m

def crop_for_mode(im,mode):
    w,h=im.size
    if mode=='chat':
        # Close-up of conversation and context rail.
        return im.crop((max(0,w*0.39),max(0,h*0.32),min(w,w*.99),min(h,h*.995)))
    if mode=='left':
        return im.crop((max(0,w*.14),max(0,h*.13),min(w,w*.89),min(h,h*.94)))
    return im

def wrap(d,text,maxpx,f):
    words=text.split();lines=[];line=''
    for w in words:
        nxt=(line+' '+w).strip()
        if d.textbbox((0,0),nxt,font=f)[2]>maxpx and line:
            lines.append(line);line=w
        else:line=nxt
    if line:lines.append(line)
    return lines

def make_slide(i,title,narration,src,mode):
    img=Image.new('RGB',SIZE,'#081324');d=ImageDraw.Draw(img)
    for y in range(SIZE[1]):
        t=y/SIZE[1];d.line([(0,y),(SIZE[0],y)],fill=(int(8+7*t),int(19+15*t),int(36+23*t)))
    d.rounded_rectangle((35,25,1245,95),radius=14,fill='#101f31',outline='#304d5c',width=1)
    d.ellipse((56,47,66,57),fill='#69eec9');d.text((77,39),'PARENTBRIDGE AI',font=font(22,True),fill='#effdf7')
    d.text((1195,47),f'{i+1:02d} / {len(SCENES)}',font=font(16,True),fill='#8facbd',anchor='ra')
    d.text((45,116),title,font=font(34,True),fill='#f6faff')
    d.rounded_rectangle((990,115,1235,146),radius=14,fill='#1d433e',outline='#3c7365')
    d.text((1111,130),'LOCAL SIMULATION',font=font(13,True),fill='#8af0ca',anchor='mm')
    path=(AS/'architecture.png') if src=='architecture' else (AS/f'scene-{src}.png')
    visual=Image.open(path).convert('RGB');visual=crop_for_mode(visual,mode)
    target=(1160,435)
    if mode=='chat':
        # Focused crop presents larger message copy for judges.
        vis=visual.resize(target,Image.Resampling.LANCZOS)
    else:
        vis=visual.copy();vis.thumbnail(target,Image.Resampling.LANCZOS)
    x=(SIZE[0]-vis.width)//2;y=166+(target[1]-vis.height)//2
    d.rounded_rectangle((x-4,y-4,x+vis.width+4,y+vis.height+4),radius=12,fill='#213a4f')
    img.paste(vis,(x,y),roundmask(vis.size,10))
    d.rounded_rectangle((35,612,1245,695),radius=13,fill='#142737',outline='#37665e',width=1)
    d.rectangle((52,626,57,679),fill='#6ee4be')
    # On-screen captions are intentionally concise; the audio is the full narrative.
    caption=narration.split('. ')[0]+'.'
    lines=wrap(d,caption,1108,font(19))[:2]
    for n,line in enumerate(lines):d.text((74,629+n*27),line,font=font(19),fill='#d9f3ed')
    d.text((1202,674),'SIMULATED SENDS · NO REAL AWS TRAFFIC',font=font(10,True),fill='#79b6ad',anchor='ra')
    dst=TMP/f'{i:02d}.png';img.save(dst,optimize=True)
    return dst

def espeak_audio(i,narration):
    path=TMP/f'{i:02d}.wav'
    subprocess.run(['espeak','-v','en-us+f3','-s','173','-p','46','-a','145','-w',str(path),narration],check=True)
    with wave.open(str(path)) as wav: duration=wav.getnframes()/wav.getframerate()
    return path,duration


def main():
    manifest=[]
    for i,(title,narr,src,mode) in enumerate(SCENES):
        slide=make_slide(i,title,narr,src,mode)
        audio,sec=espeak_audio(i,narr)
        manifest.append({'slide':str(slide),'audio':str(audio),'title':title,'narration_duration':round(sec,1)})
        print(f'{i+1:02d} {title:<32} {sec:4.1f}s')
        if sec>=17.4:print('WARNING: narration may exceed scene length')
        cmd=['ffmpeg','-y','-hide_banner','-loglevel','error','-loop','1','-framerate','12','-i',str(slide),'-i',str(audio),
             '-vf','fade=t=in:st=0:d=0.55,fade=t=out:st=17.4:d=0.6,format=yuv420p','-t','18',
             '-r','12','-c:v','libx264','-preset','ultrafast','-crf','25','-c:a','aac','-b:a','72k','-af','apad',
             '-movflags','+faststart',str(TMP/f'{i:02d}.mp4')]
        subprocess.run(cmd,check=True)
    concat=TMP/'concat.txt';concat.write_text(''.join(f"file '{(TMP/f'{i:02d}.mp4').resolve()}'\n" for i in range(len(SCENES))))
    subprocess.run(['ffmpeg','-y','-hide_banner','-loglevel','error','-f','concat','-safe','0','-i',str(concat),
            '-c','copy','-movflags','+faststart',str(AS/'parentbridge-demo-3min.mp4')],check=True)
    (AS/'video-manifest.json').write_text(json.dumps(manifest,indent=2))
    print('Saved:',AS/'parentbridge-demo-3min.mp4')

if __name__=='__main__':main()
