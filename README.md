# TP 3INSI - Bactérie

Simulation d'une bactérie modélisée comme une machine à états finis distribuée.
Chaque état est un microservice gRPC autonome déployé dans son propre pod
Kubernetes. Une gateway web affiche le volume et l'état de la bactérie et permet
de déclencher les transitions autorisées.

## Modèle

La bactérie démarre à l'état `stable_vivant` avec un volume de 1 m³.

| État | Effet sur le volume | États joignables |
|------|---------------------|------------------|
| `stable_vivant` | inchangé | `hypertrophie`, `atrophie` |
| `hypertrophie` | +10 % toutes les 10 s | `stable_vivant` |
| `atrophie` | -5 % toutes les 10 s | `stable_vivant`, `stable_impasse` (si volume ≤ 0) |
| `stable_impasse` | inchangé (terminal) | aucun |

## Architecture

- `proto/bacteria.proto` : contrat gRPC partagé (états + persistance).
- `states/*` : les 4 états, chacun un serveur gRPC autonome exposant une
  métrique Prometheus `bacteria_state_traversals_total`.
- `gateway/` : application Flask (page web + orchestration des transitions).
- `persistence/` : pod conservant l'état des bactéries (évolution), avec une
  métrique `bacteria_count_by_state` pour le tableau de bord.
- `k8s/` : manifests Kubernetes (Deployments, Services, Prometheus).
- `perf/` : test de charge.

## Lancer en local (sans Kubernetes)

Depuis la racine du projet, générer le code gRPC :

```
python -m grpc_tools.protoc -I proto --python_out=. --grpc_python_out=. proto/bacteria.proto
```

Lancer chaque état dans un terminal séparé (ports metrics différents pour éviter
les collisions en local) :

```
python states/stable_vivant/server.py
python states/hypertrophie/server.py
python states/atrophie/server.py
python states/stable_impasse/server.py
```

Lancer la gateway : elle pointe par défaut vers `localhost:50051` en mode local,
et les adresses Kubernetes sont injectées par les manifests dans le cluster.

```
python gateway/app.py
```

Puis ouvrir http://localhost:5000

## Déployer sur Kubernetes

Construire les images (contexte = racine du projet) :

```
docker build -f states/stable_vivant/Dockerfile  -t bacteria/stable-vivant:latest .
docker build -f states/hypertrophie/Dockerfile   -t bacteria/hypertrophie:latest .
docker build -f states/atrophie/Dockerfile       -t bacteria/atrophie:latest .
docker build -f states/stable_impasse/Dockerfile -t bacteria/stable-impasse:latest .
docker build -f gateway/Dockerfile               -t bacteria/gateway:latest .
docker build -f persistence/Dockerfile           -t bacteria/persistence:latest .
```

Appliquer les manifests :

```
kubectl apply -f k8s/
```

- Page web : http://<node-ip>:30080
- Prometheus : http://<node-ip>:30090

## Test de performance : Locust

Outil choisi : **Locust**. Il est écrit en Python, comme le reste du projet, ce
qui rend le scénario de charge lisible et maintenable (`perf/locustfile.py`). Il
simule de la charge HTTP concurrente sur la gateway, mesure temps de réponse et
débit, et fournit une interface web temps réel ainsi qu'un rapport exportable.

Le scénario cible la gateway via `GET /` (et quelques `POST /transition`), ce qui
déclenche à chaque requête un appel gRPC vers l'état courant : on teste donc
l'ensemble de la chaîne gateway → gRPC → état, et on fait grimper la métrique
Prometheus `bacteria_state_traversals_total`.

Installer Locust :

```
pip install locust
```

Lancer avec l'interface web (puis ouvrir http://localhost:8089) :

```
locust -f perf/locustfile.py --host http://localhost:5000
```

Lancer sans interface (50 utilisateurs, montée en 10 s, durée 1 min, rapport HTML) :

```
locust -f perf/locustfile.py --host http://localhost:5000 --headless -u 50 -r 10 -t 1m --csv perf/results --html perf/report.html
```
