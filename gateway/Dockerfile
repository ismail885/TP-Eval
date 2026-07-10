FROM python:3.12-slim

WORKDIR /app

COPY gateway/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY proto/bacteria.proto proto/bacteria.proto
RUN python -m grpc_tools.protoc -I proto --python_out=. --grpc_python_out=. proto/bacteria.proto

COPY gateway/app.py .
COPY gateway/templates templates

EXPOSE 5000

CMD ["python", "app.py"]
