
/* 
-- Upload container process.

docker tag website easyconnect-demo.registry.snowflakecomputing.com/sync/container/docker/website
docker login easyconnect-demo.registry.snowflakecomputing.com -u danielwilczak
docker push easyconnect-demo.registry.snowflakecomputing.com/sync/container/docker/website
*/

create service sync_service
    in compute pool sync
    from specification $$
    spec:
      containers:
        - name: website
          image: /sync/container/docker/website
          env:
            SNOWFLAKE_WAREHOUSE: "development"
            DEV: true
      endpoints:
        - name: app
          port: 80
          public: true  
    $$
external_access_integrations = (EXTERNAL_ACCESS_SYNC);

-- To see the url to login to the application.
show endpoints in service sync_service;
select "ingress_url" from TABLE(RESULT_SCAN(LAST_QUERY_ID()));


-- Get logs from container.
select SYSTEM$GET_SERVICE_LOGS('sync.container.sync_service', 0, 'website', 100) as logs;


-- drop service if exists sync_service;  


