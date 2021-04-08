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
----
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

- new table (in psql)::

    CREATE TABLE my_meas2 (
        time TIMESTAMP NOT NULL,
        location TEXT NOT NULL,
        current FLOAT NOT NULL,
        voltage FLOAT NOT NULL);

    # check with:
    \dt
    \d my_meas2

- note1: time and date can be stored separately (DateCaptured DATE, TimeStampCaptured TIME)
- note2: TIMESTAMP can have timezone (TIMESTAMPTZ), both are 8 byte
    - maybe BIGINT is better suited, so nanoseconds can stay

- create hypertable (in psql)::

    SELECT create_hypertable('my_meas2', 'time', 'location');
    # TODO: maybe even partition by location, here the code for after creation:
    TRUNCATE TABLE my_meas2;
    SELECT add_dimension('my_meas2', 'location', number_partitions => 4);

- test (in psql)::

    INSERT INTO my_meas2(time, location, current, voltage)
        VALUES (NOW(), 'office', 0.1, 3.0);

    # OR BATCH

    INSERT INTO my_meas2
        VALUES
            (NOW(), 'office', 0.1, 3.0),
            (NOW(), 'lab', 0.2, 3.1);

    SELECT * FROM my_meas2 ORDER BY time DESC LIMIT 100;
