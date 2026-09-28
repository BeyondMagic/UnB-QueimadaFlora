#!/usr/bin/env python3
"""
Benchmark da consulta central da pergunta de gestao no MongoDB (ADR 0001).
Executa o cruzamento espacial entre focos de calor, imoveis rurais,
reservas legais, APPs e UCs usando indices 2dsphere.
"""

import argparse
import datetime
import os
import sys
import time
from typing import Dict, List, Set

try:
    from pymongo import MongoClient
    from pymongo.errors import OperationFailure
except ImportError:
    print("Erro: pymongo nao instalado. Instale com: pip install pymongo", file=sys.stderr)
    sys.exit(1)

RAIO_TERRA_METROS = 6378137.0
DISTANCIA_UC_METROS = 1000.0
DISTANCIA_RADIANOS = DISTANCIA_UC_METROS / RAIO_TERRA_METROS


def conectar_mongo(uri: str, db_name: str):
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    return client[db_name]


def demonstrar_falha_lookup_espacial(db) -> str:
    """
    Demonstra tecnicamente por que o MongoDB nao suporta $lookup com predicado espacial
    indexado entre duas colecoes em uma unica consulta declarativa.
    """
    pipeline = [
        {"$limit": 5},
        {
            "$lookup": {
                "from": "imoveis",
                "let": {"geom_foco": "$geometry"},
                "pipeline": [
                    {
                        "$match": {
                            "$expr": {
                                "$geoIntersects": ["$geometry", "$$geom_foco"]
                            }
                        }
                    }
                ],
                "as": "imovel_match",
            }
        },
    ]
    try:
        list(db.focos.aggregate(pipeline))
        return "Inesperado: $lookup espacial executou sem erro."
    except OperationFailure as err:
        return f"Confirmado: MongoDB rejeita $geoIntersects dentro de $expr: {err.details.get('errmsg', str(err))}"
    except Exception as e:
        return f"Confirmado: MongoDB nao suporta expressao espacial em pipeline: {e}"


def verificar_foco_em_area_protegida(db, foco_geom: dict, cod_imovel: str) -> bool:
    """
    Verifica se o ponto do foco intercepta reserva legal do mesmo imovel,
    APP distrital ou esta no raio de 1 km de uma Unidade de Conservacao.
    """
    # 1. Reserva Legal do mesmo imovel
    reserva = db.reservas.find_one(
        {
            "cod_imovel": cod_imovel,
            "geometry": {"$geoIntersects": {"$geometry": foco_geom}},
        },
        {"_id": 1},
    )
    if reserva is not None:
        return True

    # 2. Area de Preservacao Permanente
    app = db.apps.find_one(
        {"geometry": {"$geoIntersects": {"$geometry": foco_geom}}},
        {"_id": 1},
    )
    if app is not None:
        return True

    # 3. Raio de 1 km (1.000 m) de Unidade de Conservacao
    # No MongoDB 2dsphere com WGS84, $geoWithin com $centerSphere usa radianos
    lon, lat = foco_geom["coordinates"]
    uc = db.ucs.find_one(
        {
            "geometry": {
                "$geoWithin": {
                    "$centerSphere": [[lon, lat], DISTANCIA_RADIANOS]
                }
            }
        },
        {"_id": 1},
    )
    if uc is not None:
        return True

    return False


def executar_benchmark_por_imovel(
    db,
    data_inicio: datetime.datetime,
    data_fim: datetime.datetime,
    limite_imoveis: int = 0,
    timeout_segundos: float = 300.0,
) -> Dict:
    """
    Executa a consulta central iterando sobre imoveis rurais e consultando focos
    via indice espacial 2dsphere.
    """
    imoveis_cursor = db.imoveis.find({}, {"cod_imovel": 1, "geometry": 1})
    if limite_imoveis > 0:
        imoveis_cursor = imoveis_cursor.limit(limite_imoveis)

    imoveis = list(imoveis_cursor)
    total_imoveis = len(imoveis)
    print(f"\nIniciando avaliacao espacial de {total_imoveis} imoveis rurais...")

    imoveis_reincidentes: Set[str] = set()
    total_consultas_focos = 0
    total_testes_protecao = 0

    t_inicio = time.time()
    tempo_esgotado = False

    for idx, imovel in enumerate(imoveis, start=1):
        tempo_decorrido = time.time() - t_inicio
        if tempo_decorrido > timeout_segundos:
            print(f"\n[TIMEOUT] Tempo limite de {timeout_segundos:.0f}s atingido apos {idx} imoveis.")
            tempo_esgotado = True
            break

        cod_imovel = imovel["cod_imovel"]
        geom_imovel = imovel.get("geometry")
        if not geom_imovel:
            continue

        # Consulta focos que intersectam o imovel rural no intervalo temporal
        focos_no_imovel = list(
            db.focos.find(
                {
                    "geometry": {"$geoIntersects": {"$geometry": geom_imovel}},
                    "data_hora_evento": {"$gte": data_inicio, "$lte": data_fim},
                },
                {"ano_evento": 1, "geometry": 1},
            )
        )
        total_consultas_focos += 1

        if not focos_no_imovel:
            continue

        # Agrupa anos distintos de deteccao
        anos_distintos = {f["ano_evento"] for f in focos_no_imovel}
        if len(anos_distintos) < 2:
            continue

        # Verifica se ao menos um foco atingiu reserva legal, APP ou raio de 1 km de UC
        tem_foco_protegido = False
        for f in focos_no_imovel:
            total_testes_protecao += 1
            if verificar_foco_em_area_protegida(db, f["geometry"], cod_imovel):
                tem_foco_protegido = True
                break

        if tem_foco_protegido:
            imoveis_reincidentes.add(cod_imovel)

        # Progresso a cada 1.000 imoveis
        if idx % 1000 == 0 or idx == total_imoveis:
            taxa = idx / max(0.001, tempo_decorrido)
            projecao_total = (total_imoveis / taxa) if taxa > 0 else 0
            print(
                f"  [{idx:5d}/{total_imoveis}] ({idx/total_imoveis*100:5.1f}%) "
                f"- tempo: {tempo_decorrido:5.1f}s - taxa: {taxa:5.1f} imov/s "
                f"- reincidentes: {len(imoveis_reincidentes)} - projecao: {projecao_total:5.1f}s"
            )

    duracao_total = time.time() - t_inicio
    imoveis_processados = idx if not tempo_esgotado else idx - 1

    return {
        "estrategia": "Iteracao por Imovel (Imovel -> 2dsphere Focos)",
        "imoveis_totais": total_imoveis,
        "imoveis_processados": imoveis_processados,
        "imoveis_reincidentes": len(imoveis_reincidentes),
        "duracao_segundos": duracao_total,
        "taxa_imoveis_por_segundo": imoveis_processados / max(0.001, duracao_total),
        "timeout_atingido": tempo_esgotado,
        "amostra_reincidentes": sorted(list(imoveis_reincidentes))[:10],
    }


def main():
    parser = argparse.ArgumentParser(description="Benchmark da consulta central no MongoDB.")
    parser.add_argument("--mongo-uri", default=os.getenv("MONGO_URI", "mongodb://localhost:27017"))
    parser.add_argument("--mongo-db", default=os.getenv("MONGO_DB", "corta-fogo-mongo"))
    parser.add_argument("--limite", type=int, default=0, help="Limita o numero de imoveis (0 = todos)")
    parser.add_argument("--timeout", type=float, default=180.0, help="Timeout em segundos (padrao 180s)")
    parser.add_argument("--ano-inicio", type=int, default=2015)
    parser.add_argument("--ano-fim", type=int, default=2025)

    args = parser.parse_args()

    print("=" * 65)
    print("BENCHMARK MONGODB: CONSULTA DA PERGUNTA DE GESTAO (ADR 0001)")
    print(f"Banco       : {args.mongo_db} @ {args.mongo_uri}")
    print(f"Periodo     : {args.ano_inicio}-01-01 a {args.ano_fim}-12-31")
    print(f"Timeout     : {args.timeout} s")
    print("=" * 65)

    try:
        db = conectar_mongo(args.mongo_uri, args.mongo_db)
    except Exception as e:
        print(f"Erro ao conectar ao MongoDB: {e}", file=sys.stderr)
        sys.exit(1)

    # 1. Demonstracao de limitacao do $lookup
    print("\n[Teste de Engenharia] Validando suporte a $lookup com predicado espacial:")
    resultado_lookup = demonstrar_falha_lookup_espacial(db)
    print(f"  {resultado_lookup}")

    # 2. Execucao da Consulta Central
    dt_inicio = datetime.datetime(args.ano_inicio, 1, 1, 0, 0, 0)
    dt_fim = datetime.datetime(args.ano_fim, 12, 31, 23, 59, 59)

    res = executar_benchmark_por_imovel(
        db,
        dt_inicio,
        dt_fim,
        limite_imoveis=args.limite,
        timeout_segundos=args.timeout,
    )

    # 3. Relatorio Consolidado
    print("\n" + "=" * 65)
    print("RESULTADO DO BENCHMARK NO MONGODB:")
    print("=" * 65)
    print(f"  Estrategia              : {res['estrategia']}")
    print(f"  Imoveis processados     : {res['imoveis_processados']} / {res['imoveis_totais']}")
    print(f"  Imoveis identificados   : {res['imoveis_reincidentes']}")
    print(f"  Tempo decorrido         : {res['duracao_segundos']:.2f} s")
    print(f"  Taxa de processamento   : {res['taxa_imoveis_por_segundo']:.1f} imoveis/s")
    if res["timeout_atingido"]:
        print(f"  Status                  : TIMEOUT (> {args.timeout:.0f} s)")
    else:
        print(f"  Status                  : Concluido")

    print("\n" + "-" * 65)
    print("COMPARACAO COM POSTGRESQL + POSTGIS (ADR 0001):")
    print("-" * 65)
    print(f"  PostgreSQL 16 + PostGIS 3.4 (GiST) : 41.8 s (consulta completa no SGBD)")
    if res["timeout_atingido"]:
        proj = (res["imoveis_totais"] / max(0.001, res["taxa_imoveis_por_segundo"]))
        print(f"  MongoDB 7.0 (2dsphere + cliente)   : > {args.timeout:.0f} s (projecao total: ~{proj:.0f} s)")
    else:
        print(f"  MongoDB 7.0 (2dsphere + cliente)   : {res['duracao_segundos']:.2f} s")
    print("=" * 65)


if __name__ == "__main__":
    main()
