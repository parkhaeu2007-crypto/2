-- Run once in Supabase SQL Editor for the NEST project.
create table if not exists public.nest_user_data (
  user_id uuid primary key references auth.users(id) on delete cascade,
  snapshot jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

alter table public.nest_user_data enable row level security;
revoke all on table public.nest_user_data from anon;
grant select, insert, update, delete on table public.nest_user_data to authenticated;

drop policy if exists "Users can read their own NEST data" on public.nest_user_data;
drop policy if exists "Users can create their own NEST data" on public.nest_user_data;
drop policy if exists "Users can update their own NEST data" on public.nest_user_data;
drop policy if exists "Users can delete their own NEST data" on public.nest_user_data;

create policy "Users can read their own NEST data"
  on public.nest_user_data for select to authenticated
  using ((select auth.uid()) = user_id);
create policy "Users can create their own NEST data"
  on public.nest_user_data for insert to authenticated
  with check ((select auth.uid()) = user_id);
create policy "Users can update their own NEST data"
  on public.nest_user_data for update to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);
create policy "Users can delete their own NEST data"
  on public.nest_user_data for delete to authenticated
  using ((select auth.uid()) = user_id);
