-- Creates the database for the CEN Bot
drop table if exists public.xp;
create table if not exists public.xp (
--  ID              dtype       conditions  default  
    user_id         bigint      not null,
--  Constraints
    constraint pkey_xp primary key (user_id)
) tablespace pg_default;
alter table if exists public.xp owner to cenbot;