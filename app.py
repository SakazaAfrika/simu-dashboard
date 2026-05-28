from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from functools import wraps
import os, re, random, httpx, json
from urllib.parse import quote

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'change-this-in-production')

SUPABASE_URL = os.environ.get('SUPABASE_URL', '')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY', '')
if SUPABASE_URL and not SUPABASE_URL.startswith('http'):
    SUPABASE_URL = f'https://{SUPABASE_URL}'

RESPOND_BASE = 'https://simubysakaza.com/respond.html'


# --- Supabase helper ---

def supabase_request(method, path, data=None, token=None):
    headers = {
        'apikey': SUPABASE_KEY,
        'Content-Type': 'application/json',
        'Prefer': 'return=representation'
    }
    if token:
        headers['Authorization'] = f'Bearer {token}'
    url = f'{SUPABASE_URL}/rest/v1/{path}'
    with httpx.Client(timeout=10) as client:
        if method == 'GET':    r = client.get(url, headers=headers)
        elif method == 'POST': r = client.post(url, headers=headers, json=data)
        elif method == 'PATCH':r = client.patch(url, headers=headers, json=data)
    return r.json() if r.content else []


# --- Auth decorator ---

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('access_token'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


# ─── Public routes ───────────────────────────────────────────────────────────

@app.route('/')
def landing():
    if session.get('access_token'):
        return redirect(url_for('dashboard'))
    return render_template('landing.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        email    = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        try:
            with httpx.Client(timeout=10) as client:
                r = client.post(
                    f'{SUPABASE_URL}/auth/v1/token?grant_type=password',
                    headers={'apikey': SUPABASE_KEY, 'Content-Type': 'application/json'},
                    json={'email': email, 'password': password}
                )
            data = r.json()
            if 'access_token' in data:
                session['access_token'] = data['access_token']
                session['user']         = data.get('user', {})
                return redirect(url_for('dashboard'))
            error = 'Incorrect email or password.'
        except Exception as e:
            error = 'Something went wrong. Please try again.'
    return render_template('login.html', error=error)


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    error = None
    if request.method == 'POST':
        name     = request.form.get('name', '').strip()
        org      = request.form.get('organisation', '').strip()
        email    = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        if not all([name, org, email, password]):
            error = 'Please fill in all fields.'
        elif len(password) < 8:
            error = 'Password must be at least 8 characters.'
        else:
            try:
                with httpx.Client(timeout=10) as client:
                    r = client.post(
                        f'{SUPABASE_URL}/auth/v1/signup',
                        headers={'apikey': SUPABASE_KEY, 'Content-Type': 'application/json'},
                        json={'email': email, 'password': password}
                    )
                data = r.json()
                if data.get('id'):
                    session['access_token'] = data.get('access_token', '')
                    session['user']         = data
                    session['user_name']    = name
                    session['user_org']     = org
                    return redirect(url_for('campaign_new'))
                error = data.get('msg', 'Sign up failed. Try again.')
            except Exception as e:
                error = str(e)
    return render_template('signup.html', error=error)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('landing'))


# ─── Password reset ───────────────────────────────────────────────────────────

@app.route('/reset-password', methods=['GET', 'POST'])
def reset_request():
    message = None
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        try:
            with httpx.Client(timeout=10) as client:
                client.post(
                    f'{SUPABASE_URL}/auth/v1/recover',
                    headers={'apikey': SUPABASE_KEY, 'Content-Type': 'application/json'},
                    json={'email': email}
                )
        except: pass
        message = f'If {email} exists, a reset link has been sent.'
    return render_template('reset_request.html', message=message)


@app.route('/reset-password/confirm', methods=['GET', 'POST'])
def reset_confirm():
    token = request.args.get('access_token') or request.form.get('token')
    error = None
    if request.method == 'POST':
        new_pw  = request.form.get('password', '')
        confirm = request.form.get('confirm', '')
        if new_pw != confirm:
            error = 'Passwords do not match.'
        elif len(new_pw) < 8:
            error = 'Password must be at least 8 characters.'
        else:
            try:
                with httpx.Client(timeout=10) as client:
                    r = client.put(
                        f'{SUPABASE_URL}/auth/v1/user',
                        headers={'apikey': SUPABASE_KEY, 'Authorization': f'Bearer {token}',
                                 'Content-Type': 'application/json'},
                        json={'password': new_pw}
                    )
                if r.status_code == 200:
                    return redirect(url_for('login'))
                error = 'Reset failed. Please request a new link.'
            except Exception as e:
                error = str(e)
    return render_template('reset_confirm.html', token=token, error=error)


# ─── Dashboard ────────────────────────────────────────────────────────────────

@app.route('/dashboard')
@require_auth
def dashboard():
    user    = session.get('user', {})
    user_id = user.get('id') if isinstance(user, dict) else None
    campaigns = []
    if user_id:
        try:
            result = supabase_request('GET',
                f'campaigns?user_id=eq.{user_id}&order=created_at.desc',
                token=session.get('access_token'))
            print(f'[DEBUG] user_id: {user_id}')
            print(f'[DEBUG] campaigns result: {result}')
            campaigns = result if isinstance(result, list) else []
        except Exception as e:
            print(f'[DEBUG] campaigns error: {e}')
    return render_template('dashboard.html',
        campaigns=campaigns,
        user=user,
        supabase_url=SUPABASE_URL,
        supabase_key=SUPABASE_KEY,
        respond_base=RESPOND_BASE)


# ─── Campaign creation ────────────────────────────────────────────────────────

@app.route('/campaign/new', methods=['GET', 'POST'])
@require_auth
def campaign_new():
    if request.method == 'POST':
        name     = request.form.get('name', 'campaign').strip()
        org      = request.form.get('organisation', '').strip()
        channels = request.form.getlist('channels')
        formats  = request.form.getlist('formats')
        prompts  = [p for p in request.form.getlist('prompts') if p.strip()]
        slug     = f"{re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')}-{random.randint(1000,9999)}"
        user     = session.get('user', {})
        user_id  = user.get('id') if isinstance(user, dict) else None

        campaign_data = {
            'name':             name,
            'organisation':     org,
            'description':      request.form.get('description', ''),
            'campaign_type':    request.form.get('campaign_type', ''),
            'target_responses': request.form.get('target_responses', ''),
            'channels':         channels,
            'formats':          formats,
            'language':         request.form.get('language', 'English'),
            'location_tagging': request.form.get('location_tagging', 'Optional'),
            'prompts':          prompts,
            'closing_message':  request.form.get('closing_message', ''),
            'user_id':          user_id,
            'slug':             slug,
            'is_live':          True
        }
        try:
            supabase_request('POST', 'campaigns', campaign_data, session.get('access_token'))
        except: pass

        session['launch_slug'] = slug
        session['launch_name'] = name
        return redirect(url_for('campaign_launched'))

    return render_template('campaign_new.html',
        user_org=session.get('user_org', ''))


@app.route('/campaign/launched')
@require_auth
def campaign_launched():
    slug = session.pop('launch_slug', '')
    name = session.pop('launch_name', 'Your campaign')
    link = f'{RESPOND_BASE}?c={slug}'
    return render_template('campaign_launched.html', name=name, link=link)


# ─── API endpoints (used by dashboard JS) ────────────────────────────────────

@app.route('/api/campaigns')
@require_auth
def api_campaigns():
    user    = session.get('user', {})
    user_id = user.get('id') if isinstance(user, dict) else None
    result  = supabase_request('GET',
        f'campaigns?user_id=eq.{user_id}&order=created_at.desc',
        token=session.get('access_token'))
    return jsonify(result if isinstance(result, list) else [])


@app.route('/api/responses/<campaign_id>')
@require_auth
def api_responses(campaign_id):
    result = supabase_request('GET',
        f'responses?campaign_id=eq.{campaign_id}&order=submitted_at.desc',
        token=session.get('access_token'))
    return jsonify(result if isinstance(result, list) else [])


# ─── SMS webhook — Africa's Talking ──────────────────────────────────────────

@app.route('/sms/incoming', methods=['POST'])
def sms_incoming():
    phone     = request.form.get('from', '')
    message   = request.form.get('text', '').strip()
    shortcode = request.form.get('to', '')

    # Try to match to a campaign via shortcode, or store unmatched
    submission = {
        'phone':     phone,
        'content':   message,
        'channel':   'SMS',
        'shortcode': shortcode,
        'verified':  False
    }
    try:
        supabase_request('POST', 'responses', submission)
    except Exception as e:
        print(f'[SMS webhook error] {e}')

    return '', 200
# --- WhatsApp Webhook (simu) ---

def twiml_msg(body):
    return (
        f'<?xml version="1.0" encoding="UTF-8"?>'
        f'<Response><Message>{body}</Message></Response>'
    ), 200, {'Content-Type': 'text/xml'}

@app.route('/whatsapp', methods=['POST'])
def whatsapp_webhook():
    incoming_msg = request.values.get('Body', '').strip()
    from_number = request.values.get('From', '').strip()
    # Normalise to digits only — avoids all URL-encoding issues with + and :
    clean_number = re.sub(r'\D', '', from_number)

    conv = supabase_request(
        'GET',
        f'conversations?phone_number=eq.{clean_number}&status=eq.active&limit=1'
    )
    conversation = conv[0] if isinstance(conv, list) and conv else None

    if conversation is None:
        campaign_res = supabase_request(
            'GET',
            f'campaigns?keyword=ilike.{incoming_msg.lower()}&limit=1'
        )
        campaign = campaign_res[0] if isinstance(campaign_res, list) and campaign_res else None

        if campaign:
            prompts = campaign.get('prompts', [])
            supabase_request('POST', 'conversations', {
                'phone_number': clean_number,
                'campaign_id': campaign['id'],
                'current_question_index': 0,
                'status': 'active'
            })
            welcome = campaign.get('description') or f"Welcome to {campaign['name']}!"
            reply = f"{welcome}\n\nQuestion 1 of {len(prompts)}:\n{prompts[0]}"
        else:
            reply = "Hi! To join a simu campaign, please use the link or keyword you received."

    else:
        campaign_res = supabase_request(
            'GET',
            f'campaigns?id=eq.{conversation["campaign_id"]}&limit=1'
        )
        campaign = campaign_res[0] if isinstance(campaign_res, list) and campaign_res else None
        prompts = campaign.get('prompts', [])
        current_index = conversation['current_question_index']

        supabase_request('POST', 'responses', {
            'conversation_id': conversation['id'],
            'phone_number': clean_number,
            'question_index': current_index,
            'question_text': prompts[current_index],
            'content': incoming_msg,
            'format': 'text'
        })

        next_index = current_index + 1

        if next_index < len(prompts):
            supabase_request(
                'PATCH',
                f'conversations?id=eq.{conversation["id"]}',
                {'current_question_index': next_index}
            )
            reply = f"Question {next_index + 1} of {len(prompts)}:\n{prompts[next_index]}"
        else:
            supabase_request(
                'PATCH',
                f'conversations?id=eq.{conversation["id"]}',
                {'status': 'completed'}
            )
            reply = campaign.get('closing_message') or "Thank you! Your voice has been recorded. ✅"

    return twiml_msg(reply)

# --- Campaign QR page (simu) ---

QR_PAGE_HTML = r'''<!doctype html><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/qrious/4.0.2/qrious.min.js"></script>
<style>
:root{--mint:#5DCAA5;--charcoal:#1F2937;--offwhite:#F8FAF8;--tint1:#E8F7F1;--grey:#6B7280;--line:#e2efe9}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Nunito',sans-serif;background:radial-gradient(900px 520px at 88% -10%,rgba(93,202,165,.18),transparent 62%),var(--offwhite);color:var(--charcoal);min-height:100vh;display:flex;align-items:flex-start;justify-content:center;padding:40px 24px}
.wrap{width:100%;max-width:980px;display:grid;grid-template-columns:1fr 1.05fr;gap:34px}
@media(max-width:780px){.wrap{grid-template-columns:1fr}}
.panel{background:#fff;border:1px solid var(--line);border-radius:22px;padding:30px;box-shadow:0 24px 60px -34px rgba(31,41,55,.28)}
.brand{display:flex;flex-direction:column;gap:2px;margin-bottom:22px}
.brand .row{display:flex;align-items:center;gap:12px}
.brand .dot{width:26px;height:26px;border-radius:50%;background:var(--mint)}
.brand .name{font-weight:800;font-size:36px;letter-spacing:-.01em}
.brand .by{font-size:13px;color:var(--grey);margin-left:38px}
h1{font-weight:800;font-size:27px;line-height:1.14;margin-bottom:8px}h1 span{color:var(--mint)}
.sub{font-size:14.5px;color:var(--grey);line-height:1.55;margin-bottom:24px;font-weight:500}
label{display:block;font-weight:700;font-size:13px;margin:18px 0 7px}
input{width:100%;font-family:'Nunito';font-weight:500;font-size:15px;color:var(--charcoal);background:var(--offwhite);border:1px solid var(--line);border-radius:12px;padding:13px 14px;outline:none}
input:focus{border-color:var(--mint);box-shadow:0 0 0 3px rgba(93,202,165,.22)}
button{margin-top:26px;width:100%;font-family:'Nunito';font-weight:800;font-size:16px;color:var(--charcoal);background:var(--mint);border:none;border-radius:12px;padding:15px;cursor:pointer;box-shadow:0 12px 26px -12px rgba(93,202,165,.95)}
button:hover{filter:brightness(1.03)}
.preview{display:flex;flex-direction:column;align-items:center;gap:16px}
.canvas-frame{width:100%;border-radius:22px;overflow:hidden;box-shadow:0 30px 70px -34px rgba(31,41,55,.4)}
canvas{width:100%;display:block;height:auto}
.hint{font-size:12.5px;color:var(--grey);text-align:center;font-weight:500}
</style>
<div class="wrap">
<div class="panel">
<div class="brand"><div class="row"><span class="dot"></span><span class="name">simu</span></div><span class="by">by Sakaza Afrika</span></div>
<h1>Campaign <span>QR code</span></h1>
<p class="sub">Download a print-ready code for posters, flyers and community gatherings — no typing, no app, just scan.</p>
<label for="name">Campaign name</label>
<input id="name" type="text" value="Join simu">
<label for="link">Campaign link</label>
<input id="link" type="text" value="https://simubysakaza.com/respond.html?c=join-simu-1758">
<label for="tag">Call to action</label>
<input id="tag" type="text" value="Scan to share your voice">
<button id="dl">Download PNG</button>
</div>
<div class="preview"><div class="canvas-frame"><canvas id="card" width="820" height="1060"></canvas></div>
<p class="hint">Live preview — downloads at high resolution for print.</p></div>
</div>
<script>
const cv=document.getElementById('card'),ctx=cv.getContext('2d'),$=id=>document.getElementById(id);
const params=new URLSearchParams(window.location.search);
if(params.get('c'))$('link').value='https://simubysakaza.com/respond.html?c='+params.get('c');
if(params.get('name'))$('name').value=params.get('name');
function roundRect(c,x,y,w,h,r){c.beginPath();c.moveTo(x+r,y);c.arcTo(x+w,y,x+w,y+h,r);c.arcTo(x+w,y+h,x,y+h,r);c.arcTo(x,y+h,x,y,r);c.arcTo(x,y,x+w,y,r);c.closePath();}
function draw(){
const W=cv.width,H=cv.height,name=$('name').value.trim()||'Campaign',link=$('link').value.trim(),tag=$('tag').value.trim()||'Scan to share your voice';
ctx.fillStyle='#F8FAF8';ctx.fillRect(0,0,W,H);
const glow=ctx.createRadialGradient(W*0.86,80,30,W*0.86,80,440);glow.addColorStop(0,'rgba(93,202,165,.22)');glow.addColorStop(1,'rgba(93,202,165,0)');ctx.fillStyle=glow;ctx.fillRect(0,0,W,H);
ctx.fillStyle='rgba(93,202,165,.08)';ctx.beginPath();ctx.arc(70,H-50,230,0,Math.PI*2);ctx.fill();
ctx.strokeStyle='rgba(93,202,165,.6)';ctx.lineWidth=3;roundRect(ctx,32,32,W-64,H-64,30);ctx.stroke();
ctx.textAlign='left';ctx.font='800 76px Nunito';const wm='simu',tw=ctx.measureText(wm).width,dotR=25,gap=22,baseY=172,total=dotR*2+gap+tw,sx=(W-total)/2;
ctx.fillStyle='#5DCAA5';ctx.beginPath();ctx.arc(sx+dotR,baseY-24,dotR,0,Math.PI*2);ctx.fill();
ctx.fillStyle='#1F2937';ctx.fillText(wm,sx+dotR*2+gap,baseY);
ctx.textAlign='center';ctx.fillStyle='#6B7280';ctx.font='500 20px Nunito';ctx.fillText('by Sakaza Afrika',W/2,baseY+34);
ctx.strokeStyle='rgba(93,202,165,.65)';ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(W/2-80,238);ctx.lineTo(W/2+80,238);ctx.stroke();
ctx.fillStyle='#1F2937';ctx.font='700 38px Nunito';
(function(t,x,y,mw,lh){const ws=t.split(' ');let ln='',ls=[];for(const w of ws){const tt=ln?ln+' '+w:w;if(ctx.measureText(tt).width>mw&&ln){ls.push(ln);ln=w;}else ln=tt;}ls.push(ln);const sy=y-((ls.length-1)*lh)/2;ls.forEach((l,i)=>ctx.fillText(l,x,sy+i*lh));})(name,W/2,302,W-200,46);
const pY=364,pS=400,pX=(W-pS)/2;
ctx.fillStyle='#E8F7F1';roundRect(ctx,pX-16,pY-16,pS+32,pS+32,30);ctx.fill();
ctx.fillStyle='#fff';ctx.shadowColor='rgba(31,41,55,.16)';ctx.shadowBlur=30;ctx.shadowOffsetY=12;roundRect(ctx,pX,pY,pS,pS,24);ctx.fill();ctx.shadowColor='transparent';ctx.shadowBlur=0;ctx.shadowOffsetY=0;
if(link){const qr=new QRious({value:link,size:640,level:'H',background:'#ffffff',foreground:'#1F2937'});const q=322;ctx.drawImage(qr.canvas,(W-q)/2,pY+(pS-q)/2,q,q);}
ctx.fillStyle='#1F2937';ctx.font='700 31px Nunito';ctx.textAlign='center';ctx.fillText(tag,W/2,pY+pS+90);
ctx.fillStyle='#6B7280';ctx.font='500 16px Nunito';ctx.fillText('No app needed \u00b7 Scan with your camera',W/2,pY+pS+128);
}
function download(){const a=document.createElement('a');a.download='simu-qr-'+(($('name').value.trim()||'campaign').toLowerCase().replace(/[^a-z0-9]+/g,'-'))+'.png';a.href=cv.toDataURL('image/png');a.click();}
['name','link','tag'].forEach(id=>$(id).addEventListener('input',draw));
$('dl').addEventListener('click',download);
document.fonts.ready.then(draw);setTimeout(draw,400);
</script>'''


@app.route('/qr')
def campaign_qr():
    return QR_PAGE_HTML, 200, {'Content-Type': 'text/html'}


# ─── Run ──────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
