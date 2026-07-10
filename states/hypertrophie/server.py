import time
from concurrent import futures

import grpc
from prometheus_client import Counter, start_http_server

import bacteria_pb2
import bacteria_pb2_grpc

STATE_NAME = "hypertrophie"
GROWTH_INTERVAL = 10.0
GROWTH_FACTOR = 1.10
GRPC_PORT = 50051
METRICS_PORT = 8000

traversals = Counter(
    "bacteria_state_traversals_total",
    "Nombre de fois que l'etat a ete traverse",
    ["state"],
)


class StateService(bacteria_pb2_grpc.StateServiceServicer):
    def Apply(self, request, context):
        traversals.labels(state=STATE_NAME).inc()
        volume = request.volume
        last_change_ts = request.last_change_ts
        now = time.time()
        if now - last_change_ts >= GROWTH_INTERVAL:
            volume = volume * GROWTH_FACTOR
            last_change_ts = now
        return bacteria_pb2.TransitionResponse(
            volume=volume,
            state=STATE_NAME,
            last_change_ts=last_change_ts,
            reachable_states=["stable_vivant"],
        )


def serve():
    start_http_server(METRICS_PORT)
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    bacteria_pb2_grpc.add_StateServiceServicer_to_server(StateService(), server)
    server.add_insecure_port(f"[::]:{GRPC_PORT}")
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
