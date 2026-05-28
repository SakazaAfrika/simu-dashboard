from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from functools import wraps
import os, re, random, httpx, json

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

    conv = supabase_request(
        'GET',
        f'conversations?phone_number=eq.{from_number}&status=eq.active&limit=1'
    )
    conversation = conv[0] if isinstance(conv, list) and conv else None

    if conversation is None:
        campaign_res = supabase_request(
            'GET',
            f'campaigns?keyword=ilike.{incoming_msg.lower()}&active=eq.true&limit=1'
        )
        campaign = campaign_res[0] if isinstance(campaign_res, list) and campaign_res else None

        if campaign:
            prompts = campaign.get('prompts', [])
            supabase_request('POST', 'conversations', {
                'phone_number': from_number,
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
            'phone_number': from_number,
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




# ─── Run ──────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
