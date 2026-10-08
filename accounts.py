"""Supabase email authentication and atomic, server-authorized usage reservations."""
import json
import time
import urllib.error
import urllib.request


class AccessError(Exception):
    def __init__(self, code='unavailable'):
        self.code = code
        super().__init__(code)


class Accounts:
    def __init__(self, url, key, gate):
        self.url = url.rstrip('/')
        self.key = key
        self.gate = gate

    def call(self, path, data=None, token=None, method=None):
        headers = {'apikey': self.key, 'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = 'Bearer ' + token
        req = urllib.request.Request(self.url + path, data=None if data is None else json.dumps(data).encode(),
                                     headers=headers, method=method or ('GET' if data is None else 'POST'))
        try:
            with urllib.request.urlopen(req, timeout=20) as result:
                raw = result.read()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as error:
            try:
                body = json.loads(error.read())
                code = body.get('error_code') or body.get('code') or 'unavailable'
            except (ValueError, AttributeError):
                code = 'unavailable'
            raise AccessError(code) from None
        except (OSError, ValueError):
            raise AccessError() from None

    def signup(self, email, password):
        return self.call('/auth/v1/signup?redirect_to=https%3A%2F%2Fraremotion-support-ai.streamlit.app%2F', {'email': email, 'password': password})

    def login(self, email, password):
        session = self.call('/auth/v1/token?grant_type=password', {'email': email, 'password': password})
        session['expires_at'] = time.time() + session.get('expires_in', 3600)
        return session

    def validate(self, session):
        if session.get('expires_at', 0) < time.time() + 120:
            fresh = self.call('/auth/v1/token?grant_type=refresh_token', {'refresh_token': session['refresh_token']})
            fresh['expires_at'] = time.time() + fresh.get('expires_in', 3600)
            session.clear()
            session.update(fresh)
        user = self.call('/auth/v1/user', token=session['access_token'])
        if not user.get('id') or not user.get('email_confirmed_at'):
            raise AccessError('email_not_confirmed')
        return user

    def logout(self, session):
        self.call('/auth/v1/logout?scope=local', {}, token=session['access_token'])

    def quota(self, session, action='status', request_id=None):
        return self.call('/rest/v1/rpc/support_ai_quota', {
            'p_secret': self.gate, 'p_action': action, 'p_request': request_id,
        }, token=session['access_token'])


def run_metered(accounts, session, generate):
    """Reserve before OpenAI; settle before showing an answer. Fail closed."""
    import uuid
    request_id = str(uuid.uuid4())
    reservation = accounts.quota(session, 'reserve', request_id)
    if not reservation['applied']:
        raise AccessError('trial_exhausted')
    try:
        answer = generate()
        if not answer or not answer.strip():
            raise AccessError('empty_answer')
        settled = accounts.quota(session, 'succeed', request_id)
        if not settled['applied']:
            raise AccessError('reservation_expired')
        return answer
    except Exception:
        try:
            accounts.quota(session, 'fail', request_id)
        except AccessError:
            pass  # A reservation expires after five minutes if the network is unavailable.
        raise
