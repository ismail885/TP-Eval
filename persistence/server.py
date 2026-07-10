import json
import os
import threading
from concurrent import futures

import grpc
from prometheus_client import Gauge, start_http_server

import bacteria_pb2
import bacteria_pb2_grpc

GRPC_PORT = int(os.environ.get("GRPC_PORT", "50051"))
METRICS_PORT = int(os.environ.get("METRICS_PORT", "8000"))
DATA_FILE = os.environ.get("DATA_FILE", "/data/bacteria.json")

lock = threading.Lock()

bacteria_by_state = Gauge(
    "bacteria_count_by_state",
    "Nombre de bacteries dans chaque etat",
    ["state"],
)


def load_store():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def write_store(store):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(store, f)


def refresh_metrics(store):
    counts = {}
    for entry in store.values():
        counts[entry["state"]] = counts.get(entry["state"], 0) + 1
    bacteria_by_state.clear()
    for state, count in counts.items():
        bacteria_by_state.labels(state=state).set(count)


class PersistenceService(bacteria_pb2_grpc.PersistenceServiceServicer):
    def Save(self, request, context):
        with lock:
            store = load_store()
            store[request.bacteria.id] = {
                "volume": request.bacteria.volume,
                "state": request.bacteria.state,
                "last_change_ts": request.bacteria.last_change_ts,
            }
            write_store(store)
            refresh_metrics(store)
        return bacteria_pb2.SaveResponse(ok=True)

    def Load(self, request, context):
        with lock:
            store = load_store()
            entry = store.get(request.id)
        if entry is None:
            return bacteria_pb2.LoadResponse(found=False)
        return bacteria_pb2.LoadResponse(
            found=True,
            bacteria=bacteria_pb2.BacteriaState(
                id=request.id,
                volume=entry["volume"],
                state=entry["state"],
                last_change_ts=entry["last_change_ts"],
            ),
        )


def serve():
    start_http_server(METRICS_PORT)
    refresh_metrics(load_store())
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    bacteria_pb2_grpc.add_PersistenceServiceServicer_to_server(PersistenceService(), server)
    server.add_insecure_port(f"[::]:{GRPC_PORT}")
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
