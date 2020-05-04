<details>
    <summary>Table of Contents</summary>

- [Local Setup](#local-setup)
    - [Running the Archive Service](#running-the-archive-service)
- [Creating a Dgraph backup](#creating-a-dgraph-backup)
    - [RDF backup](#rdf-backup)
    - [JSON backup](#json-backup)
- [Restoring a backup](#restoring-a-backup)
    - [Graph native format](#graph-native-format)
    - [2017 format](#2017-format)
- [Deploying](#deploying)
- [License](#license)

</details>

# Local Setup

<details>
    <summary>Requirements</summary>

- [Docker](https://www.docker.com)

</details>

<details>
    <summary>Initial setup</summary>

```shell
# Clone the repository.
git clone git@github.com:kwcay/boateng-archive-service.git
cd boateng-archive-service

# Build Docker image.
docker build --tag doraboateng/archive-service --target dev .

# Create Docker container.
docker create \
    --interactive \
    --mount type=bind,src=$(pwd)/data,dst=/tmp/data \
    --mount type=bind,src=$(pwd)/src,dst=/boateng-archive-service \
    --name boateng-archive-service \
    --tty \
    --workdir /boateng-archive-service \
    doraboateng/archive-service
```
</details>

## Running the Archive Service

```shell
# Start the Docker container.
docker start boateng-archive-service

# Launch a shell in the Docker container (using `ash`).
docker exec -it boateng-archive-service ash

# Exit the `ash` shell.
exit

# Stop the Docker container.
docker stop boateng-archive-service
```

# Creating a Dgraph backup

## RDF backup

>To do...

## JSON backup

>To do...

# Restoring a backup

## Graph native format

>To do...

## 2017 format

# Deploying

# License

[GNU General Public License v3](https://github.com/kwcay/boateng-graph-service/blob/stable/LICENSE) © Kwahu & Cayes

# WIP NOTES

From inside the `ash` shell:

```shell
# Download and extract the backup file.
export JSON_DUMP_DIR=/tmp/"$(date +"%Y%m%d-%H%M%S")"
mkdir --parents "$JSON_DUMP_DIR"
tar --extract --gzip --file data/2017-07-19.tar.gz --directory "$JSON_DUMP_DIR"

# Load backup into Dgraph.
pip install -r requirements.txt
python restore.py "$JSON_DUMP_DIR"
```
