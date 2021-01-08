FROM golang:1.15.6-buster AS dev

RUN apt-get update \
    && apt-get upgrade --yes \
    && apt-get install --no-install-recommends --yes \
        curl \
        git \
        ipython \
        less \
        python3-pip \
        vim \
    && apt-get remove subversion --yes \
    && apt-get autoremove --yes \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && pip3 install --disable-pip-version-check --no-cache-dir \
        pylint \
        flake8 \
        autopep8 \
        yapf \
        pydocstyle \
        pycodestyle \
        bandit \
    && mkdir --parents /tmp/data

ADD . /boateng-archive-service
WORKDIR /boateng-archive-service
