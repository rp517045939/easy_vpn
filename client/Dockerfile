FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY *.py ./

EXPOSE 7070

ENTRYPOINT ["python", "main.py", "--config", "/config/config.yml"]
