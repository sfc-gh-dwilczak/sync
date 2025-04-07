use role sysadmin;

create database sync;
create schema sync.container;

-- Docker image repo. Tell us where to upload our docker image to.
create image repository if not exists docker;
show image repositories;
select "repository_url" from table(result_scan(last_query_id()));

create or replace table video_metadata (
    filename varchar,
    duration float,
    fps float,
    width int,
    height int,
    processed_at timestamp_ntz default current_timestamp()
);


-- This section only has to be setup once.
use role accountadmin;

grant bind service endpoint on account to role sysadmin;

-- Networking
create or replace network rule sync
    mode = egress
    type = host_port
    value_list = (
        'danielwilczak.s3.amazonaws.com/:80',
        'danielwilczak.s3.amazonaws.com:443');
    --  value_list = ('0.0.0.0:80', '0.0.0.0:443')

create or replace external access integration external_access_sync
    allowed_network_rules = (sync)
    enabled = true;

grant usage on integration external_access_sync to role sysadmin;



