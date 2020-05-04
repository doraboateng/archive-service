FROM python:3.8.2-slim-buster

RUN pip install --disable-pip-version-check --no-cache-dir \
        pylint \
        flake8 \
        autopep8 \
        yapf \
        pydocstyle \
        pycodestyle \
        bandit \
    && mkdir --parents /tmp/data
