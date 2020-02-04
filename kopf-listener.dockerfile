FROM python:3.7-buster as base
FROM base as builder
# RUN apk add --no-cache gcc musl-dev g++ mysql-dev python3-dev

# RUN mkdir /install
# WORKDIR /install
COPY requirements.txt /requirements.txt
# RUN pip install --install-option="--prefix=/install" -r /requirements.txt -i http://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com
RUN pip install -r /requirements.txt -i http://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com

# FROM base
# COPY --from=builder /install /usr/local
WORKDIR /app
COPY kopf-listener* ./
COPY requirements.txt ./

ENTRYPOINT ["/app/kopf-listener-entrypoint.sh"]
