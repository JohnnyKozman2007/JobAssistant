-- Create the users table for JobAssistant
-- Run this in the Supabase SQL editor or via your migration workflow.

create table if not exists public.users (
    user_id text primary key,
    email text not null unique,
    first_name text not null,
    last_name text not null,
    phone_number text,
    location text,
    desired_job_title text,
    years_of_experience integer check (years_of_experience >= 0),
    has_resume boolean not null default false,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists users_email_idx on public.users (email);
create index if not exists users_has_resume_idx on public.users (has_resume);

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

drop trigger if exists users_set_updated_at on public.users;
create trigger users_set_updated_at
before update on public.users
for each row
execute function public.set_updated_at();
