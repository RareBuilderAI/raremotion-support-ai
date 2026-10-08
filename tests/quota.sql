-- Transaction-only fixtures; no test accounts or allowance changes are retained.
begin;
insert into auth.users(id,email) values
 ('9eb940f2-f6ac-4ce5-9000-000000000001','support-test-one@example.invalid'),
 ('9eb940f2-f6ac-4ce5-9000-000000000002','support-test-two@example.invalid');
update support_ai_private.config set secret_hash=encode(sha256(convert_to('transaction-test-only','UTF8')),'hex') where id;
select set_config('request.jwt.claim.sub','9eb940f2-f6ac-4ce5-9000-000000000001',true);
set local role authenticated;
do $$
declare q jsonb;
begin
 q:=public.support_ai_quota('transaction-test-only');
 assert (q->>'remaining')::int=2;
 q:=public.support_ai_quota('transaction-test-only','reserve','9eb940f2-f6ac-4ce5-9001-000000000001');
 assert (q->>'applied')::boolean;
 q:=public.support_ai_quota('transaction-test-only','reserve','9eb940f2-f6ac-4ce5-9001-000000000002');
 assert (q->>'applied')::boolean;
 q:=public.support_ai_quota('transaction-test-only','reserve','9eb940f2-f6ac-4ce5-9001-000000000003');
 assert not (q->>'applied')::boolean, 'third simultaneous reservation must fail';
 q:=public.support_ai_quota('transaction-test-only','fail','9eb940f2-f6ac-4ce5-9001-000000000001');
 assert (q->>'remaining')::int=1, 'failure must return allowance';
 q:=public.support_ai_quota('transaction-test-only','reserve','9eb940f2-f6ac-4ce5-9001-000000000003');
 assert (q->>'applied')::boolean;
 q:=public.support_ai_quota('transaction-test-only','succeed','9eb940f2-f6ac-4ce5-9001-000000000002');
 q:=public.support_ai_quota('transaction-test-only','succeed','9eb940f2-f6ac-4ce5-9001-000000000003');
 assert (q->>'used')::int=2 and (q->>'remaining')::int=0;
 q:=public.support_ai_quota('transaction-test-only','succeed','9eb940f2-f6ac-4ce5-9001-000000000003');
 assert (q->>'used')::int=2, 'settlement must be idempotent';
 q:=public.support_ai_quota('transaction-test-only','fail','9eb940f2-f6ac-4ce5-9001-000000000003');
 assert (q->>'used')::int=2, 'success cannot be refunded';
 q:=public.support_ai_quota('transaction-test-only','reserve','9eb940f2-f6ac-4ce5-9001-000000000004');
 assert not (q->>'applied')::boolean, 'third answer must be denied';
 begin
  perform public.support_ai_quota('wrong-secret');
  raise exception 'wrong secret accepted';
 exception when insufficient_privilege then null; end;
end $$;
select set_config('request.jwt.claim.sub','9eb940f2-f6ac-4ce5-9000-000000000002',true);
do $$ declare q jsonb; begin
 q:=public.support_ai_quota('transaction-test-only'); assert (q->>'remaining')::int=2, 'allowances must be independent';
 q:=public.support_ai_quota('transaction-test-only','succeed','9eb940f2-f6ac-4ce5-9001-000000000003'); assert not (q->>'applied')::boolean;
 assert not has_schema_privilege('authenticated','support_ai_private','USAGE');
 assert not has_function_privilege('anon','public.support_ai_quota(text,text,uuid)','EXECUTE');
end $$;
reset role;
rollback;
select 'PASS: two-answer limit, failure refund, idempotency, user isolation, secret gate, private storage' as result;
