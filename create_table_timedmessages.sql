-- Creates the database for the CEN Bot
drop table if exists public.timedmessages;
create table if not exists public.timedmessages (
--  ID              dtype              conditions  default
    job_id          serial             not null,

    guild_id        bigint             not null,
    channel_id      bigint             not null,
    content         text               not null,
    time_stamp      timestamptz        not null,
    dow             int,
    
    -- Constraints
    constraint pkey_timedmessages primary key (job_id),
    constraint fkey_timedmessages foreign key (guild_id) references public.serverdata(guild_id)
        on delete cascade
        on update no action
) tablespace pg_default;
alter table if exists public.timedmessages owner to cenbot;
set timezone = 'America/New_York';