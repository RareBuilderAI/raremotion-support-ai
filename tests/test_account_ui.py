import os
import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest

class AccountGateTests(unittest.TestCase):
    def run_app(self):
        return AppTest.from_file('../app.py').run(timeout=20)

    def test_anonymous_sees_create_account_before_workspace(self):
        app=self.run_app()
        self.assertFalse(app.exception)
        self.assertEqual([t.label for t in app.tabs], ['Create Account','Log In'])
        self.assertEqual(len(app.chat_input),0)
        self.assertEqual(len(app.text_area),0)
        self.assertIn('Create Account',[b.label for b in app.button])

    def test_verified_account_can_use_workspace(self):
        with patch('account_ui.Accounts') as cls:
            cls.return_value.validate.return_value={'id':'test-user','email':'test@example.invalid'}
            cls.return_value.quota.return_value={'used':0,'pending':0,'remaining':2}
            app=AppTest.from_file('../app.py')
            app.session_state.account_session={'access_token':'test-only'}
            app.run(timeout=20)
            self.assertFalse(app.exception)
            self.assertEqual(len(app.chat_input),1)
            self.assertFalse(app.chat_input[0].disabled)

    def test_exhausted_account_cannot_send(self):
        with patch('account_ui.Accounts') as cls:
            cls.return_value.validate.return_value={'id':'test-user','email':'test@example.invalid'}
            cls.return_value.quota.return_value={'used':2,'pending':0,'remaining':0}
            app=AppTest.from_file('../app.py')
            app.session_state.account_session={'access_token':'test-only'}
            app.run(timeout=20)
            self.assertFalse(app.exception)
            self.assertTrue(app.chat_input[0].disabled)

if __name__=='__main__': unittest.main()
