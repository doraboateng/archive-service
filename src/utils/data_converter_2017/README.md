# Using Docker to convert the 2017 SQL dump to RDF

Create 2 Docker images:

1. Using MariaDB, to load the SQL dump.
2. Using Dgraph, to generate the RDF dump.

```shell
mkdir -p tmp/2017-dump
docker network \
    create \
    dora-temp-network
docker run \
    --detach \
    --env MYSQL_DATABASE=temp \
    --env MYSQL_ROOT_PASSWORD=temp \
    --interactive \
    --mount type=bind,src="$(pwd)"/tmp/2017-dump,target=/tmp/2017-dump \
    --name dora-temp-maria \
    --network dora-temp-network \
    --tty \
    --rm \
    --workdir /tmp \
    mariadb:10.4.6
docker run \
    --detach \
    --interactive \
    --mount type=bind,src="$(pwd)"/tmp/2017-dump,target=/tmp/2017-dump \
    --mount type=bind,src="$(pwd)"/src/utils/data_converter_2017,target=/tmp/src \
    --name dora-temp-dgraph \
    --network dora-temp-network \
    --publish 8005:8000 \
    --publish 8085:8080 \
    --publish 9085:9080 \
    --tty \
    --rm \
    --workdir /tmp \
    dgraph/standalone:v2.0.0-rc1
docker ps
```

Copy SQL dump to `tmp/2017-dump`, then load SQL dump into MariaDB.

```shell
docker exec \
    --interactive \
    --tty \
    dora-temp-maria \
    mysql temp --user root --password
# enter password (temp)...
source 2017-dump/dump.sql
exit
```

Copy the Dgraph schema files into `tmp/2017-dump`.

```shell
curl \
    --output tmp/2017-dump/schema.gql \
    https://raw.githubusercontent.com/kwcay/boateng-api/stable/src/schema.gql
curl \
    --output tmp/2017-dump/schema.dgraph \
    https://raw.githubusercontent.com/kwcay/boateng-api/stable/src/schema.dgraph
```

Copy data from MariaDB to Dgraph.

```shell
docker exec \
    --interactive \
    --tty \
    dora-temp-dgraph \
    bash

# Prep environment
apt-get update && \
    apt-get upgrade --assume-yes && \
    apt-get install --assume-yes python3-pip && \
    pip3 install --upgrade pip && \
    cd /tmp/src && \
    pip install --requirement requirements.txt && \
    export PYTHONIOENCODING=UTF-8

# Load schema files
curl localhost:8080/admin/schema --data-binary "@/tmp/2017-dump/schema.gql"
curl localhost:8080/alter --data-binary "@/tmp/2017-dump/schema.dgraph"

# Sync databases
python3 sync.py
```

Cleanup

```shell
docker stop dora-temp-maria dora-temp-dgraph
docker network rm dora-temp-network
```

# Working on the Python script

```shell
virtualenv venv
. venv/bin/activate
pip install --requirement src/utils/data_converter_2017/requirements.txt
```










# BACKUP...

Create Docker image.

```
docker run \
    --detach \
    --env MYSQL_DATABASE=temp \
    --env MYSQL_ROOT_PASSWORD=temp \
    --interactive \
    --mount type=bind,src="$(pwd)",target="/dora-temp" \
    --name dora-temp-db \
    --tty \
    --rm \
    mariadb:10.4.6
docker ps
```

Launch shell into container.

```
docker exec \
    --interactive \
    --tty \
    --workdir /dora-temp \
    dora-temp-db \
    bash
```

Load data into database.

```
mysql temp --user root --password
# enter password (temp)...
source 2017-07-19.sql
exit
```

Generate dump and tarball.

```
apt-get update && apt-get install libmysqlclient-dev python3 python3-pip --assume-yes
pip3 install mysql-connector-python-rf rdflib

# JSON dump
python3 dump_json.py
tar --create --gzip --file 2017-07-19.tar.gz *.json

# RDF dump
python3 dump_rdf.py
```
