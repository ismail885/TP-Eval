"""
Test de charge de la gateway avec Locust.

Chaque requête GET / sur la gateway déclenche un appel gRPC vers l'état courant
de la bactérie : on teste donc l'ensemble de la chaîne gateway -> gRPC -> état,
et on fait grimper le compteur Prometheus bacteria_state_traversals_total.

Lancer (interface web) :
    locust -f perf/locustfile.py --host http://localhost:5000

Lancer (sans interface, rapport CSV + HTML) :
    locust -f perf/locustfile.py --host http://localhost:5000 \
        --headless -u 50 -r 10 -t 1m \
        --csv perf/results --html perf/report.html
"""

import random

from locust import HttpUser, between, task


class BacteriaUser(HttpUser):
    # Temps d'attente entre deux actions d'un même utilisateur virtuel.
    wait_time = between(1, 2)

    @task(5)
    def view_page(self):
        # Lecture de la page : déclenche l'appel gRPC vers l'état courant.
        self.client.get("/")

    @task(1)
    def trigger_transition(self):
        # Provoque une transition. La gateway ignore une cible non autorisée
        # (redirection 302), ce qui reste une charge valide pour le test.
        target = random.choice(["hypertrophie", "atrophie", "stable_vivant"])
        self.client.post("/transition", data={"target": target})
