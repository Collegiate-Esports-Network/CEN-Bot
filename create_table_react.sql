-- Creates the database for the CEN Bot
drop table if exists public.reactcategory;
create table if not exists public.reactcategory (
--  ID              dtype           conditions  default
    category_id     serial          not null,
    guild_id        bigint          not null,
    cate_name       varchar(256)    not null,
    cate_desc       varchar(1024),
    cate_embed      bigint,

    --Constraints
    constraint pkey_reactcategory primary key (category_id),
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
    category_id     int             not null,
    role_desc       varchar(1024),
    role_emoji      varchar(19)     not null,

    --Constraints
    constraint pkey_reactdata primary key (role_id),
    constraint fkey_reactdata foreign key (category_id) references public.reactcategory(category_id)
        on delete cascade
        on update no action
) tablespace pg_default;
alter table if exists public.reactdata owner to cenbot;