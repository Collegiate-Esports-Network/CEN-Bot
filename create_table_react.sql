-- Creates the database for the CEN Bot
drop table if exists public.reactcategory;
create table if not exists public.reactcategory (
--  ID              dtype           conditions  default  
    guild_id        bigint          not null,
    cate_name       varchar(256)    not null,
    cate_desc       varchar(1024),
    role_ids        bigint[],

    --Constraints
    constraint pkey_reactcategory primary key (guild_id),
    constraint fkey_reactcategory foreign key (guild_id) references public.serverdata(guild_id)
        on delete cascade
        on update no action
) tablespace pg_default;
alter table if exists public.reactcategory owner to cenbot;

-- Creates the database for the CEN Bot
drop table if exists public.reactdata;
create table if not exists public.reactdata (
--  ID              dtype           conditions  default  
    role_id         bigint          not null,
    role_name       varchar(256)    not null,
    role_desc       varchar(1024),
    role_emoji_id   bigint          not null,

    --Constraints
    constraint pkey_reactdata primary key (role_id)
) tablespace pg_default;
alter table if exists public.reactdata owner to cenbot;