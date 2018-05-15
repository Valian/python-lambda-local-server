FROM python:3.6 as builder

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt


FROM lambci/lambda:python3.6
WORKDIR /srv

USER root

RUN yum install -y git

COPY --from=builder /usr/local/lib/python3.6/site-packages /var/lang/lib/python3.6/site-packages
COPY . /srv

# let's clear previous entrypoint
ENTRYPOINT []
CMD ["python", "-u", "app.py"]