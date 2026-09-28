#!/usr/bin/env bash
set -euo pipefail

# Script de execucao do benchmark minimo do MongoDB (ADR 0001)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

echo "=================================================================="
echo "    Benchmark Minimo: MongoDB 7.0 vs PostgreSQL 16 + PostGIS"
echo "=================================================================="

# Verifica se o Docker esta disponivel
if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
    echo "Ambiente Docker detectado. Executando benchmark via contêineres isolados..."
    echo "Subindo MongoDB e runner com limites de 2 CPUs e 2 GB de RAM..."

    docker compose -f "${SCRIPT_DIR}/docker-compose.mongo.yml" up --build --abort-on-container-exit --exit-code-from benchmark_runner

    echo ""
    echo "Para encerrar e limpar o volume do MongoDB:"
    echo "docker compose -f ${SCRIPT_DIR}/docker-compose.mongo.yml down -v"
else
    echo "Docker daemon nao detectado ou inacessivel. Tentando execucao local direta..."
    export MONGO_URI="${MONGO_URI:-mongodb://localhost:27017}"
    export MONGO_DB="${MONGO_DB:-corta-fogo-mongo}"
    export DATA_DIR="${DATA_DIR:-${REPO_ROOT}/data}"

    echo "Verificando dependencias Python (pymongo)..."
    python3 -c "import pymongo" 2>/dev/null || {
        echo "Instalando dependencias locais..."
        pip install -r "${SCRIPT_DIR}/requirements.txt"
    }

    echo "1. Executando carga e indexacao no MongoDB..."
    python3 "${SCRIPT_DIR}/carregar_mongo.py" --mongo-uri "$MONGO_URI" --mongo-db "$MONGO_DB" --data-dir "$DATA_DIR"

    echo "2. Executando benchmark da consulta..."
    python3 "${SCRIPT_DIR}/benchmark_mongo.py" --mongo-uri "$MONGO_URI" --mongo-db "$MONGO_DB"
fi

echo "=================================================================="
echo "Benchmark concluido com sucesso."
echo "=================================================================="
