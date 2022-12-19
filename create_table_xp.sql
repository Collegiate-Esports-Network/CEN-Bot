-- Creates the database for the CEN Bot
drop table if exists public.xp;
create table if not exists public.xp (
--  ID              dtype       conditions  default  
    guild_id        bigint      not null,
    --Constraints
    constraint pkey_xp primary key (guild_id),
    constraint fkey_xp foreign key (guild_id) references public.serverdata(guild_id)
        on delete cascade
        on update no action
) tablespace pg_default;
alter table if exists public.xp owner to cenbot;