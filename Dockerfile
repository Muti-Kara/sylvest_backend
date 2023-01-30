FROM python:3.10

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1

WORKDIR /app

COPY ./app ./app
COPY requirements.txt .

RUN pip install -r requirements.txt
