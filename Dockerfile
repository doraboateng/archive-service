FROM alpine:3.11.5

RUN apk update && \
    apk upgrade && \
    apk add curl ipython less python3 vim && \
    ln -s /usr/bin/python3 /usr/bin/python && \
    ln -s /usr/bin/pip3 /usr/bin/pip && \
    mkdir --parents /tmp/data

ADD ./src /boateng-archive-service
WORKDIR /boateng-archive-service
