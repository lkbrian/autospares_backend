# Dockerfile

FROM python:3.11-slim-buster

WORKDIR /app

COPY requirements.txt ./

RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

EXPOSE 4000

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:4000", "app:app"]

