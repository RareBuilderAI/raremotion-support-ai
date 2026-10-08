import unittest
from unittest.mock import Mock
from accounts import AccessError, run_metered

class MeteringTests(unittest.TestCase):
    def test_success_is_committed_before_return(self):
        backend=Mock();backend.quota.return_value={'applied':True}
        self.assertEqual(run_metered(backend,{},lambda:'Answer'),'Answer')
        self.assertEqual([x.args[1] for x in backend.quota.call_args_list],['reserve','succeed'])
        self.assertEqual(backend.quota.call_args_list[0].args[2],backend.quota.call_args_list[1].args[2])
    def test_exhausted_never_calls_ai(self):
        backend=Mock();backend.quota.return_value={'applied':False};generate=Mock()
        with self.assertRaises(AccessError):run_metered(backend,{},generate)
        generate.assert_not_called()
    def test_failure_returns_reservation(self):
        backend=Mock();backend.quota.return_value={'applied':True}
        with self.assertRaises(RuntimeError):run_metered(backend,{},Mock(side_effect=RuntimeError('network')))
        self.assertEqual([x.args[1] for x in backend.quota.call_args_list],['reserve','fail'])
    def test_empty_answer_does_not_consume(self):
        backend=Mock();backend.quota.return_value={'applied':True}
        with self.assertRaises(AccessError):run_metered(backend,{},lambda:' ')
        self.assertEqual(backend.quota.call_args_list[-1].args[1],'fail')
    def test_database_failure_prevents_ai(self):
        backend=Mock();backend.quota.side_effect=AccessError();generate=Mock()
        with self.assertRaises(AccessError):run_metered(backend,{},generate)
        generate.assert_not_called()
    def test_failed_settlement_never_displays_answer(self):
        backend=Mock();backend.quota.side_effect=[{'applied':True},{'applied':False},{'applied':True}]
        with self.assertRaises(AccessError):run_metered(backend,{},lambda:'Answer')

if __name__=='__main__':unittest.main()
