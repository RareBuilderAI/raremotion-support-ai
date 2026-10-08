import os
import streamlit as st
from accounts import Accounts, AccessError


def setting(name):
    value = os.getenv(name)
    if value:
        return value
    try:
        return st.secrets.get(name, '')
    except FileNotFoundError:
        return ''


def require_account():
    config = [setting(x) for x in ('SUPABASE_URL', 'SUPABASE_KEY', 'SUPPORT_AI_GATE_SECRET')]
    if not all(config):
        st.info('Account access is being configured. Please check back shortly.')
        st.stop()
    accounts = Accounts(*config)
    session = st.session_state.get('account_session')
    if session:
        try:
            user = accounts.validate(session)
        except AccessError as error:
            if error.code in {'bad_jwt', 'session_not_found', 'refresh_token_not_found', 'refresh_token_already_used', 'email_not_confirmed'}:
                st.session_state.clear()
                st.rerun()
            st.error('We could not verify your account. Please try again shortly.')
            if st.button('Return to login'):
                st.session_state.clear()
                st.rerun()
            st.stop()
        st.caption('Signed in as ' + user['email'])
        if st.button('Log out'):
            try:
                accounts.logout(session)
            except AccessError:
                pass
            st.session_state.clear()
            st.rerun()
        try:
            quota = accounts.quota(session)
        except AccessError:
            st.error('We could not check your free-answer allowance. Please try again shortly.')
            st.stop()
        if quota['used'] >= 2:
            st.info("You've used your two free answers. More access is coming soon.")
        elif quota['pending']:
            st.info('An answer is being processed. Unfinished requests release their allowance within five minutes.')
        else:
            st.caption(f"{quota['remaining']} of 2 free AI answers remaining")
        return accounts, session, quota

    st.subheader('Welcome to Raremotion Support AI')
    st.write('Create an account or log in to try two free AI answers.')
    st.caption('Already use Raremotion Analytics? You can use the same login. Your Support AI allowance is separate.')
    signup, login = st.tabs(['Create Account', 'Log In'])
    with login:
        with st.form('login', clear_on_submit=True):
            email = st.text_input('Email', max_chars=254)
            password = st.text_input('Password', type='password', max_chars=128)
            submitted = st.form_submit_button('Log in', use_container_width=True)
        if submitted:
            try:
                session = accounts.login(email.strip(), password)
                accounts.validate(session)
                st.session_state.clear()
                st.session_state.account_session = session
                st.rerun()
            except AccessError as error:
                if error.code == 'email_not_confirmed':
                    st.error('Please confirm your email address before logging in.')
                elif error.code == 'invalid_credentials':
                    st.error('Email or password is incorrect.')
                else:
                    st.error('We could not log you in. Please wait a moment and try again.')
    with signup:
        with st.form('signup', clear_on_submit=True):
            email = st.text_input('Email address', max_chars=254)
            password = st.text_input('Create password', type='password', max_chars=128, help='Use at least 12 characters.')
            confirm = st.text_input('Confirm password', type='password', max_chars=128)
            submitted = st.form_submit_button('Create Account', use_container_width=True)
        if submitted:
            if '@' not in email or '.' not in email.rsplit('@', 1)[-1]:
                st.error('Enter a valid email address.')
            elif len(password) < 12:
                st.error('Use a password with at least 12 characters.')
            elif password != confirm:
                st.error('The passwords do not match.')
            else:
                try:
                    accounts.signup(email.strip(), password)
                    st.success('Check your inbox to confirm your email, then return here to log in. If you already have an account, use Log in.')
                except AccessError as error:
                    if error.code == 'weak_password':
                        st.error('Choose a stronger password and try again.')
                    elif error.code in {'over_email_send_rate_limit', 'over_request_rate_limit'}:
                        st.error('Please wait a few minutes before trying again.')
                    else:
                        st.error('We could not create the account. If you already registered, try logging in; otherwise please try again shortly.')
    st.caption('Two successful answers per account. Failed AI requests do not use your allowance. Payments are not enabled.')
    st.stop()
