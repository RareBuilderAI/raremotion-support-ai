-- Isolated Support AI storage. No changes to Analytics tables or auth settings.
begin;
create schema if not exists support_ai_private;
revoke all on schema support_ai_private from public, anon, authenticated;
create table if not exists support_ai_private.config (
 id boolean primary key default true check (id), secret_hash text not null
);
create table if not exists support_ai_private.accounts (
 user_id uuid primary key references auth.users(id) on delete cascade
);
create table if not exists support_ai_private.requests (
 id uuid primary key, user_id uuid not null references support_ai_private.accounts(user_id) on delete cascade,
 state text not null check (state in ('pending','succeeded','failed')),
 expires_at timestamptz not null, created_at timestamptz not null default now()
);
create index if not exists support_ai_requests_user on support_ai_private.requests(user_id);
alter table support_ai_private.config enable row level security;
alter table support_ai_private.accounts enable row level security;
alter table support_ai_private.requests enable row level security;
revoke all on all tables in schema support_ai_private from public, anon, authenticated;

create or replace function public.support_ai_quota(p_secret text, p_action text default 'status', p_request uuid default null)
returns jsonb language plpgsql security definer set search_path = '' as $$
declare
 uid uuid := auth.uid();
 used_count integer;
 pending_count integer;
 existing support_ai_private.requests%rowtype;
 applied boolean := false;
begin
 if uid is null or not exists (
  select 1 from support_ai_private.config where id=true
   and secret_hash=encode(sha256(convert_to(p_secret,'UTF8')),'hex')
 ) then raise exception 'Access denied' using errcode='42501'; end if;
 if p_action not in ('status','reserve','succeed','fail') then raise exception 'Invalid action'; end if;
 insert into support_ai_private.accounts(user_id) values(uid) on conflict do nothing;
 perform 1 from support_ai_private.accounts where user_id=uid for update;
 update support_ai_private.requests set state='failed'
  where user_id=uid and state='pending' and expires_at<=clock_timestamp();
 select count(*) filter(where state='succeeded'), count(*) filter(where state='pending')
  into used_count,pending_count from support_ai_private.requests where user_id=uid;
 if p_action <> 'status' and p_request is null then raise exception 'Request required'; end if;
 if p_action='reserve' then
  select * into existing from support_ai_private.requests where id=p_request;
  if found then
   applied := existing.user_id=uid and existing.state='pending';
  elsif used_count+pending_count < 2 then
   insert into support_ai_private.requests(id,user_id,state,expires_at)
    values(p_request,uid,'pending',clock_timestamp()+interval '5 minutes');
   applied:=true;
  end if;
 elsif p_action in ('succeed','fail') then
  update support_ai_private.requests set state=case when p_action='succeed' then 'succeeded' else 'failed' end
   where id=p_request and user_id=uid and state='pending';
  applied:=found;
  if not applied and p_action='succeed' then
   applied:=exists(select 1 from support_ai_private.requests where id=p_request and user_id=uid and state='succeeded');
  end if;
 end if;
 select count(*) filter(where state='succeeded'), count(*) filter(where state='pending')
  into used_count,pending_count from support_ai_private.requests where user_id=uid;
 return jsonb_build_object('used',used_count,'pending',pending_count,'remaining',greatest(0,2-used_count-pending_count),'applied',applied);
end; $$;
revoke all on function public.support_ai_quota(text,text,uuid) from public, anon;
grant execute on function public.support_ai_quota(text,text,uuid) to authenticated;
commit;
-- Install the server-gate hash separately; never put the secret in this file.
