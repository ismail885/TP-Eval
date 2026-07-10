import os
import time

import grpc
from flask import Flask, redirect, render_template, request, url_for

import bacteria_pb2
import bacteria_pb2_grpc

app = Flask(__name__)

BACTERIA_ID = "default"

STATE_ADDRESSES = {
    "stable_vivant": os.environ.get("STABLE_VIVANT_ADDR", "stable-vivant:50051"),
    "hypertrophie": os.environ.get("HYPERTROPHIE_ADDR", "hypertrophie:50051"),
    "atrophie": os.environ.get("ATROPHIE_ADDR", "atrophie:50051"),
    "stable_impasse": os.environ.get("STABLE_IMPASSE_ADDR", "stable-impasse:50051"),
}

PERSISTENCE_ADDR = os.environ.get("PERSISTENCE_ADDR", "")

bacteria = {"volume": 1.0, "state": "stable_vivant", "last_change_ts": time.time()}


def call_state(state_name, b):
    with grpc.insecure_channel(STATE_ADDRESSES[state_name]) as channel:
        stub = bacteria_pb2_grpc.StateServiceStub(channel)
        req = bacteria_pb2.Bacteria(
            volume=b["volume"],
            state=b["state"],
            last_change_ts=b["last_change_ts"],
        )
        return stub.Apply(req)


def save_state():
    if not PERSISTENCE_ADDR:
        return
    try:
        with grpc.insecure_channel(PERSISTENCE_ADDR) as channel:
            stub = bacteria_pb2_grpc.PersistenceServiceStub(channel)
            stub.Save(
                bacteria_pb2.SaveRequest(
                    bacteria=bacteria_pb2.BacteriaState(
                        id=BACTERIA_ID,
                        volume=bacteria["volume"],
                        state=bacteria["state"],
                        last_change_ts=bacteria["last_change_ts"],
                    )
                )
            )
    except grpc.RpcError:
        pass


def load_state():
    if not PERSISTENCE_ADDR:
        return
    try:
        with grpc.insecure_channel(PERSISTENCE_ADDR) as channel:
            stub = bacteria_pb2_grpc.PersistenceServiceStub(channel)
            resp = stub.Load(bacteria_pb2.LoadRequest(id=BACTERIA_ID))
            if resp.found:
                bacteria["volume"] = resp.bacteria.volume
                bacteria["state"] = resp.bacteria.state
                bacteria["last_change_ts"] = resp.bacteria.last_change_ts
    except grpc.RpcError:
        pass


@app.route("/")
def index():
    resp = call_state(bacteria["state"], bacteria)
    bacteria["volume"] = resp.volume
    bacteria["last_change_ts"] = resp.last_change_ts
    save_state()
    return render_template(
        "index.html",
        volume=bacteria["volume"],
        state=bacteria["state"],
        reachable=list(resp.reachable_states),
    )


@app.route("/transition", methods=["POST"])
def transition():
    target = request.form.get("target")
    resp = call_state(bacteria["state"], bacteria)
    if target in resp.reachable_states:
        bacteria["state"] = target
        bacteria["last_change_ts"] = time.time()
        save_state()
    return redirect(url_for("index"))


load_state()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
