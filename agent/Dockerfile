FROM --platform=linux/arm64 public.ecr.aws/docker/library/python:3.12-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY nova_sonic_bridge.py ./
COPY server.py ./

EXPOSE 8080

ENV PORT=8080
ENV LOGLEVEL=INFO

CMD ["python", "server.py"]
