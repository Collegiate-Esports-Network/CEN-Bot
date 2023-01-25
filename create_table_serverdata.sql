-- Creates the database for the CEN Bot
drop table if exists public.serverdata;
create table if not exists public.serverdata (
--  ID              dtype       conditions  default  
    guild_id        bigint      not null,
    -- logging
    log_channel     bigint                  default null,
    report_channel  bigint                  default null,
    log_level       smallint    not null    default 2,
    -- welcome
    welcome_channel bigint                  default null,
    welcome_message text        not null    default 'Welcome to the server <new_member>!',
    -- react
    react_channel   bigint                  default null,
    -- Constraints
    constraint pkey_serverdata primary key (guild_id)
) tablespace pg_default;
alter table if exists public.serverdata owner to cenbot;