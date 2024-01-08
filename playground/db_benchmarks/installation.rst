Installation
============

InfluxDB
--------

https://docs.influxdata.com/influxdb/v2.0/get-started/?t=Linux
- install binary in path
- install service
- setup DB (localhost:8086)
    - hans / hanshans, tud, nes
- disable telemetry::

    # add to /etc/default/influxdb2
    ARG1="--reporting-disabled"
    # add to /lib/systemd/system/influxdb.service
    # line ExecStart=/usr/bin/influxd
    ExecStart=/usr/bin/influxd $ARG1

- config in /etc/default/influxdb2
- path-config in /etc/influxdb/config.toml

- default location TS-data: /var/lib/influxdb/engine/
- default location Key-value data: /var/lib/influxdb/influxd.bolt
- default port: 8086

Influx-TODO
-----------

- create admin, org, bucket, user for bucket
- limit DB to local access

TimescaleDB
-----------

https://www.postgresql.org/download/linux/ubuntu/
- install, if not already
https://docs.timescale.com/latest/getting-started/installation/ubuntu/installation-apt-ubuntu
- installing & tuning
- setting up - deviate with::

    sudo su postgres
    psql
        CREATE database shepherd;
        \c shepherd
        CREATE EXTENSION IF NOT EXISTS timescaledb;

- disable telemetry, https://docs.timescaledb.com/using-timescaledb/telemetry
- new user (in psql)::

    "CREATE ROLE [role_name] WITH LOGIN CREATEDB PASSWORD '[password]';"
    hans//hanshans, port 5432

    # change
    ALTER ROLE hans WITH SUPERUSER LOGIN REPLICATION BYPASSRLS;

    # check with
    \du

    # grant access
    GRANT ALL ON DATABASE shepherd TO hans;

- new table (in psql)::

    CREATE TABLE my_meas3 (
        time TIMESTAMP NOT NULL,
        node_id INTEGER NOT NULL,
        current FLOAT NOT NULL,
        voltage FLOAT NOT NULL);

    # check with:
    \dt
    \d my_meas3

- note1: time and date can be stored separately (DateCaptured DATE, TimeStampCaptured TIME)
- note2: TIMESTAMP can have timezone (TIMESTAMPTZ), both are 8 byte
    - maybe BIGINT is better suited, so nanoseconds can stay

- create hypertable (in psql)::

    SELECT create_hypertable('my_meas3', 'time', 'node_id', 8);
    # note: last parameter is partition / (space) dimension: a logical chunking good for parallel IO, disks, nodes

    # maybe even partition by location, here the code for after creation:
    TRUNCATE TABLE my_meas2;
    SELECT add_dimension('my_meas3', 'location', number_partitions => 4);

    # add secondary special index:
    create index on my_meas3 (node_id, time desc);

    # good tutorial: https://mccarthysean.dev/timescale-dash-flask-part-1

- test (in psql)::

    INSERT INTO my_meas3(time, node_id, current, voltage)
        VALUES (NOW(), 0, 0.1, 3.0);

    # OR BATCH

    INSERT INTO my_meas3
        VALUES
            (NOW(), 0, 0.1, 3.0),
            (NOW(), 1, 0.2, 3.1);

    SELECT * FROM my_meas3 ORDER BY time DESC LIMIT 100;

- allow access from external ip::

    sudo nano /etc/postgresql/13/main/pg_hba.conf
    # add ip, ip range, users
    host    all             all             samenet             md5
    # OR
    host    all             all             10.0.0.0/24         md5

    sudo nano /etc/postgresql/13/main/
    listen_addresses = '*'    # uncomment and change to * instead of localhost

    sudo service postgresql restart

Timescale_TODO:

- define nodes itself::

    CREATE TABLE nodes(
        id SERIAL PRIMARY KEY,
        type VARCHAR(50),
        location VARCHAR(50)
    );

    CREATE TABLE measurements (
        time TIMESTAMP NOT NULL,
        node_id INTEGER NOT NULL,
        current FLOAT NOT NULL,
        voltage FLOAT NOT NULL,
        FOREIGN KEY (node_id) REFERENCES nodes (id)
    );

- usermanagement
    - node-user should only be allowed to add data (and has external access)
    - web-user only reads
    - garbage collection can also delete
- db is slower right now - tuning:
    - https://gist.github.com/valyala/ae3cbfa4104f1a022a2af9b8656b1131
-
