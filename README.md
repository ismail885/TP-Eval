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

Lancer la gateway en pointant vers les états locaux :

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

## Test de performance sur Jmeter

Justification : JMeter permet de simuler facilement de la charge HTTP concurrente
sur la gateway (50 utilisateurs virtuels), de mesurer le temps de réponse et le
débit, et de générer un rapport synthétique sans écrire de code. C'est un outil
standard vu en classe pour les tests de charge.

Le plan de test cible la gateway via `GET /`, ce qui déclenche à chaque requête
un appel gRPC vers l'état courant : on teste donc l'ensemble de la chaîne
gateway → gRPC → état.

Lancer le test :

```
jmeter -n -t perf/bacteria-loadtest.jmx -Jhost=localhost -Jport=5000 -l perf/results.jtl
```
