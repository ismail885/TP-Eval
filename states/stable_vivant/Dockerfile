FROM python:3.12-slim

WORKDIR /app

COPY states/stable_vivant/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY proto/bacteria.proto proto/bacteria.proto
RUN python -m grpc_tools.protoc -I proto --python_out=. --grpc_python_out=. proto/bacteria.proto

COPY states/stable_vivant/server.py .

EXPOSE 50051 8000

CMD ["python", "server.py"]
