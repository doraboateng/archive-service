# Converting 2017 SQL backup to RDF

```shell
# From the project root, create a folder to work out of.
mkdir -p tmp/2017-dump

# Create a Docker network to be shared between the two databases.
docker network create dora-2017-backup-network

# Create a Docker container running MariaDB.
docker run \
    --detach \
    --env MYSQL_DATABASE=temp \
    --env MYSQL_ROOT_PASSWORD=temp \
    --interactive \
    --mount type=bind,src="$(pwd)"/tmp/2017-dump,target=/tmp/2017-dump \
    --name dora-2017-backup-mariadb \
    --network dora-2017-backup-network \
    --publish 13306:3306 \
    --tty \
    --rm \
    --workdir /tmp \
    mariadb:10.4.6

# Create a Docker container running Dgraph.
docker run \
    --detach \
    --env LESSCHARSET=utf-8 \
    --env PYTHONIOENCODING=UTF-8 \
    --interactive \
    --mount type=bind,src="$(pwd)"/tmp/2017-dump,target=/tmp/2017-dump \
    --mount type=bind,src="$(pwd)"/scripts/data_converter_2017,target=/tmp/src \
    --name dora-2017-backup-dgraph \
    --network dora-2017-backup-network \
    --publish 18000:8000 \
    --publish 18080:8080 \
    --publish 19080:9080 \
    --tty \
    --rm \
    --workdir /tmp \
    dgraph/standalone:v20.03.1

# Double-check that both containers are running.
docker ps --last 2
```

Copy the SQL dump to `tmp/2017-dump`.

Next, load the SQL dump into MariaDB:

```shell
# Launch a mysql shell into the MariaDB container.
docker exec \
    --interactive \
    --tty \
    dora-2017-backup-mariadb \
    mysql temp --user root --password

# Enter password to use the mysql CLI (the password is "temp").
# ...

# Load the SQL dump into MariaDB and exit the container shell.
source 2017-dump/dump.sql
exit

# Copy the Dgraph schema files into `tmp/2017-dump`.
curl \
    --output tmp/2017-dump/schema.gql \
    https://raw.githubusercontent.com/kwcay/boateng-api/stable/src/graph/schema/graph.gql
curl \
    --output tmp/2017-dump/schema.dgraph \
    https://raw.githubusercontent.com/kwcay/boateng-api/stable/src/graph/schema/indices.dgraph

# Launch a shell into the Dgraph container.
docker exec \
    --interactive \
    --tty \
    dora-2017-backup-dgraph \
    bash

# Install the dependencies needed to run the sync.py script.
apt-get update
    && apt-get upgrade --assume-yes \
    && apt-get install --assume-yes less python3-pip \
    && pip3 install --upgrade pip \
    && cd /tmp/src \
    && pip install --requirement requirements.txt

# Load schema files into graph.
curl localhost:8080/alter -d '{ "drop_all": true }' && \
    curl localhost:8080/admin/schema --data-binary "@/tmp/2017-dump/schema.gql" && \
    curl localhost:8080/alter --data-binary "@/tmp/2017-dump/schema.dgraph"

# Run the sync.py script to load data from MariaDB into Dgraph.
cd /tmp && python3 -m src.sync

# Create RDF backup.
curl --url http://localhost:8080/admin \
    --header 'content-type: application/json' \
    --data '{"query":"mutation {export(input: {format: \"rdf\"}) {response {message code}}}"}'
tar --create --file temp.rdf.tar.gz --gzip $(ls --directory -t export/* | head -1)
mv temp.rdf.tar.gz 2017-dump/doraboateng.$(date +"%Y-%m-%d").$(sha1sum temp.rdf.tar.gz | cut -c 1-6).rdf.tar.gz

# The file should now be in "tmp/2017-dump" on your machine.

# Cleanup.
docker stop dora-2017-backup-mariadb dora-2017-backup-dgraph
docker network rm dora-2017-backup-network
```

# Working on the Python script

```shell
virtualenv venv
. venv/bin/activate
pip install --requirement scripts/data_converter_2017/requirements.txt
```

# Using Dgraph live

```shell
# untar first...
tar --extract --gzip --file 2017-07-19.tar.gz

# then load RDF and schema
dgraph live \
    --alpha 127.0.0.1:9080 \
    --files <RDF> \
    --schema <SCHEMA> \
    --use_compression \
    --zero 127.0.0.1:5080
```
