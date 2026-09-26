# deploy/nexus/runner/Dockerfile — image RUNNER des runs AGAGI déportés sur nexus (livrable 2, INFRA-NEXUS).
#
# Construite IN-CLUSTER par Kaniko (deploy/nexus/runner/build-job.yaml, lancé par
# `python -m tools.jobs.remote image`), poussée sur le registre configuré (AGAGI_REGISTRY).
#
# Ce que l'image contient : l'INTERPRÈTE et les DÉPENDANCES, jamais le code d'AGAGI. Le code arrive au
# lancement de chaque Job, au sha demandé (dépôt git superficiel envoyé par `kubectl exec`) : une image sert
# tous les commits dont le contexte d'image est inchangé, et un run ne peut pas tourner sur un code périmé
# cuit dans une couche.
#
# Versions ÉPINGLÉES sur celles de la batcave (constraints.txt, relevé du 2026-09-26) : le témoin du
# livrable 4 exige un JSON bit-identique batcave/nexus, et une version de numpy différente suffirait à le
# rendre ininterprétable (on ne saurait pas si l'écart vient de la machine ou de la bibliothèque).
# Python 3.13.12 = celui de la batcave ; digest amd64 lu sur Docker Hub le 2026-09-26. Seule exception à
# l'épinglage : torch 2.6.0+cpu ici, 2.6.0+cu124 sur la batcave (même version, autre build).
FROM python:3.13.12-slim-bookworm@sha256:3121f8b0804aa3698ab750d9a39ea4a42657a385c9b133722b915e55c51551a6

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# git : le code arrive comme dépôt superficiel au sha, et les runners tamponnent leur provenance par
# `git rev-parse HEAD` / `git status` (tools/preregister.provenance, P2.68). Sans git dans l'image, un run
# déporté publierait `git_sha: None` — remote_entry refuse alors de lancer quoi que ce soit.
# Sources apt basculées en HTTPS : la NetworkPolicy du build n'ouvre que le 443 public.
RUN sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list.d/debian.sources \
 && apt-get update \
 && apt-get install -y --no-install-recommends git \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt constraints.txt /opt/agagi/

# torch CPU d'abord, depuis l'index pytorch : la version locale `+cpu` n'existe QUE là, donc aucune roue
# CUDA (≈ 2 Go de dépendances nvidia) ne peut être tirée de PyPI par erreur. Le reste depuis PyPI, sous
# contraintes. La dernière ligne échoue le build si un import majeur casse (une image qui s'importe mal ne
# doit pas atteindre le registre).
RUN pip install --index-url https://download.pytorch.org/whl/cpu --extra-index-url https://pypi.org/simple \
        "torch==2.6.0+cpu" -c /opt/agagi/constraints.txt \
 && pip install -r /opt/agagi/requirements.txt -c /opt/agagi/constraints.txt \
 && pip freeze > /opt/agagi/pip-freeze.txt \
 && python -c "import numpy, scipy, torch, kuzu, psutil, yaml, jsonschema, pydantic; print('numpy', numpy.__version__, 'torch', torch.__version__)"

USER 65534:65534
WORKDIR /work
