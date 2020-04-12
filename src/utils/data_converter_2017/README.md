# Using Docker to convert the 2017 SQL dump to RDF

Create a Docker network to connect two Docker images (one for MariaDB, and another for Dgraph):

```shell
# Create a folder to work out of.
mkdir -p tmp/2017-dump

# Create a Docker network to be shared between images.
docker network \
    create \
    dora-temp-network

# Create a Docker container running MariaDB.
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

# Create a Docker container running Dgraph.
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

# Double-check that both containers are running.
docker ps
```

Copy the SQL dump to `tmp/2017-dump`.

Next, load the SQL dump into MariaDB:

```shell
# Launch a Bash shell into the MariaDB container.
docker exec \
    --interactive \
    --tty \
    dora-temp-maria \
    mysql temp --user root --password

# Enter password to use the mysql CLI (the password is "temp").
# ...

# Load the SQL dump into MariaDB and exit the container shell.
source 2017-dump/dump.sql
exit

# Copy the Dgraph schema files into `tmp/2017-dump`.
curl \
    --output tmp/2017-dump/schema.gql \
    https://raw.githubusercontent.com/kwcay/boateng-api/stable/src/schema.gql
curl \
    --output tmp/2017-dump/schema.dgraph \
    https://raw.githubusercontent.com/kwcay/boateng-api/stable/src/schema-indices.dgraph

# Launch a shell into the Dgraph container.
docker exec \
    --interactive \
    --tty \
    dora-temp-dgraph \
    bash

# Install the dependencies needed to run the sync.py script.
apt-get update && \
    apt-get upgrade --assume-yes && \
    apt-get install --assume-yes python3-pip && \
    pip3 install --upgrade pip && \
    cd /tmp/src && \
    pip install --requirement requirements.txt && \
    export PYTHONIOENCODING=UTF-8

# Load schema files into graph.
curl localhost:8080/admin/schema --data-binary "@/tmp/2017-dump/schema.gql"
curl localhost:8080/alter --data-binary "@/tmp/2017-dump/schema-indices.dgraph"

# Run the sync.py script to load data from MariaDB into Dgraph.
python3 sync.py

# Cleanup.
docker stop dora-temp-maria dora-temp-dgraph
docker network rm dora-temp-network
```

# Working on the Python script

```shell
virtualenv venv
. venv/bin/activate
pip install --requirement src/utils/data_converter_2017/requirements.txt
```
