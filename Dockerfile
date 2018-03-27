FROM python:3.6

WORKDIR /srv

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "-u", "app.py"]