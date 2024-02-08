FROM alpine:3.19 AS base

RUN apk add --no-cache --update python3 tzdata

FROM alpine:3.19 AS install

RUN apk add --no-cache --update python3 py3-pip

COPY requirements.lock .

RUN sed '/-e/d' requirements.lock > requirements.txt

RUN pip install --no-cache-dir --break-system-packages -r requirements.txt

RUN rm -rf /usr/lib/python3.11/site-packages/pip*

RUN rm -rf /usr/lib/python3.11/site-packages/setuptools*

FROM base

COPY --from=install /usr/lib/python3.11/site-packages /usr/lib/python3.11/site-packages

WORKDIR /app

COPY src/ .

ENTRYPOINT ["python3", "main.py"]