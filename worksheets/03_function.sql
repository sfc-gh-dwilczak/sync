use schema sync.container;
use role sysadmin;

CREATE or replace FUNCTION process_video (filename VARCHAR)
  RETURNS VARCHAR
  SERVICE=sync_service
  ENDPOINT=app
  AS '/process-video';

select process_video('sample.mp4');

select * from video_metadata;