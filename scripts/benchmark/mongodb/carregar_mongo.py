#!/usr/bin/env python3
"""
Carga e indexacao espacial no MongoDB para o benchmark da E1.
Insere as colecoes equivalentes as tabelas do PostGIS com coordenadas
GeoJSON (EPSG:4326 / WGS84) e cria indices espaciais 2dsphere.
"""

import argparse
import csv
import datetime
import glob
import json
import os
import sys
import time
from typing import Dict, List, Optional

try:
    from pymongo import MongoClient, ASCENDING
except ImportError:
    print("Erro: pymongo nao instalado. Instale com: pip install pymongo", file=sys.stderr)
    sys.exit(1)


def conectar_mongo(uri: str, db_name: str):
    """Conecta ao MongoDB e retorna o banco de dados."""
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    client.server_info()  # Dispara teste de conexao
    return client[db_name]


def tentar_conectar_postgres(args):
    """Tenta conectar ao PostgreSQL caso a extracao direta seja desejada."""
    try:
        import psycopg2
        conn = psycopg2.connect(
            host=args.pg_host,
            port=args.pg_port,
            dbname=args.pg_db,
            user=args.pg_user,
            password=args.pg_password,
            connect_timeout=3,
        )
        return conn
    except Exception:
        return None


def carregar_focos_csv(caminho_csv: str) -> List[Dict]:
    """Le o arquivo de focos de calor processado e gera documentos com GeoJSON Point."""
    if not os.path.exists(caminho_csv):
        raise FileNotFoundError(f"Arquivo de focos nao encontrado: {caminho_csv}")

    documentos = []
    with open(caminho_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            lat = float(row["latitude"])
            lon = float(row["longitude"])
            dt_str = row["data_hora_evento"]
            dt_evento = datetime.datetime.fromisoformat(dt_str)
            dt_ingestao = datetime.datetime.fromisoformat(row["data_hora_ingestao"])

            doc = {
                "id_foco": i + 1,
                "data_hora_evento": dt_evento,
                "data_hora_ingestao": dt_ingestao,
                "ano_evento": dt_evento.year,
                "satelite": row["satelite"],
                "is_satelite_referencia": row["is_satelite_referencia"].lower() == "true",
                "geometry": {
                    "type": "Point",
                    "coordinates": [lon, lat],  # GeoJSON padrao [longitude, latitude]
                },
            }
            documentos.append(doc)
    return documentos


def carregar_camadas_geopandas(data_dir: str):
    """Carrega shapefiles e GeoJSONs locais usando GeoPandas e converte para EPSG:4326."""
    try:
        import geopandas as gpd
        from shapely import make_valid
        from shapely.geometry import mapping, Polygon, MultiPolygon
    except ImportError:
        print("Aviso: geopandas/shapely nao disponiveis no host. Execute via container Docker.", file=sys.stderr)
        return {}, {}, [], []

    raw_dir = os.path.join(data_dir, "raw")
    imoveis_docs = []
    reservas_docs = []
    apps_docs = []
    ucs_docs = []

    def normalizar_geom(geom):
        if geom is None or geom.is_empty:
            return None
        if not geom.is_valid:
            geom = make_valid(geom)
        if geom.is_empty:
            return None
        if isinstance(geom, (Polygon, MultiPolygon)):
            return mapping(geom)
        if hasattr(geom, "geoms"):
            polys = [g for g in geom.geoms if isinstance(g, (Polygon, MultiPolygon))]
            if polys:
                return mapping(MultiPolygon(polys))
        return None

    # 1. Imoveis CAR
    path_car = os.path.join(raw_dir, "AREA_IMOVEL.zip")
    if os.path.exists(path_car):
        print(f"Lendo {path_car}...")
        gdf_car = gpd.read_file(path_car)
        if gdf_car.crs and gdf_car.crs.to_epsg() != 4326:
            gdf_car = gdf_car.to_crs(epsg=4326)
        for _, row in gdf_car.iterrows():
            cod = str(row.get("cod_imovel") or row.get("COD_IMOVEL") or "").strip()
            geom_json = normalizar_geom(row.geometry)
            if cod and geom_json:
                imoveis_docs.append({"cod_imovel": cod, "geometry": geom_json})

    # 2. Reserva Legal
    path_rl = os.path.join(raw_dir, "RESERVA_LEGAL.zip")
    if os.path.exists(path_rl):
        print(f"Lendo {path_rl}...")
        gdf_rl = gpd.read_file(path_rl)
        if gdf_rl.crs and gdf_rl.crs.to_epsg() != 4326:
            gdf_rl = gdf_rl.to_crs(epsg=4326)
        for i, row in gdf_rl.iterrows():
            cod = str(row.get("cod_imovel") or row.get("COD_IMOVEL") or "").strip()
            geom_json = normalizar_geom(row.geometry)
            if cod and geom_json:
                reservas_docs.append({"id_reserva": i + 1, "cod_imovel": cod, "geometry": geom_json})

    # 3. UCs
    path_uc = os.path.join(raw_dir, "unidades_conservacao.geojson")
    if os.path.exists(path_uc):
        print(f"Lendo {path_uc}...")
        gdf_uc = gpd.read_file(path_uc)
        if gdf_uc.crs and gdf_uc.crs.to_epsg() != 4326:
            gdf_uc = gdf_uc.to_crs(epsg=4326)
        for i, row in gdf_uc.iterrows():
            geom_json = normalizar_geom(row.geometry)
            if geom_json:
                ucs_docs.append({
                    "id_uc": i + 1,
                    "nome": str(row.get("nome") or f"UC_{i+1}"),
                    "geometry": geom_json,
                })

    # 4. APPs
    for app_file in glob.glob(os.path.join(raw_dir, "app_*.geojson")):
        print(f"Lendo {app_file}...")
        gdf_app = gpd.read_file(app_file)
        if gdf_app.crs and gdf_app.crs.to_epsg() != 4326:
            gdf_app = gdf_app.to_crs(epsg=4326)
        for row in gdf_app.itertuples():
            geom_json = normalizar_geom(row.geometry)
            if geom_json:
                apps_docs.append({"geometry": geom_json})

    return imoveis_docs, reservas_docs, ucs_docs, apps_docs


def carregar_de_postgres(pg_conn):
    """Extrai as camadas ja saneadas do PostgreSQL/PostGIS convertendo para GeoJSON WGS84."""
    print("Extraindo camadas geometricas saneadas diretamente do PostGIS...")
    cursor = pg_conn.cursor()

    # Imoveis
    cursor.execute("SELECT cod_imovel, ST_AsGeoJSON(ST_Transform(geom, 4326)) FROM imovel_car;")
    imoveis_docs = [
        {"cod_imovel": r[0], "geometry": json.loads(r[1])}
        for r in cursor.fetchall()
        if r[1]
    ]

    # Reservas
    cursor.execute("SELECT id_reserva, cod_imovel, ST_AsGeoJSON(ST_Transform(geom, 4326)) FROM reserva_legal;")
    reservas_docs = [
        {"id_reserva": r[0], "cod_imovel": r[1], "geometry": json.loads(r[2])}
        for r in cursor.fetchall()
        if r[2]
    ]

    # UCs
    cursor.execute("SELECT id_uc, nome, ST_AsGeoJSON(ST_Transform(geom, 4326)) FROM unidade_conservacao;")
    ucs_docs = [
        {"id_uc": r[0], "nome": r[1], "geometry": json.loads(r[2])}
        for r in cursor.fetchall()
        if r[2]
    ]

    # APPs
    cursor.execute("SELECT id_app, ST_AsGeoJSON(ST_Transform(geom, 4326)) FROM area_preservacao_permanente;")
    apps_docs = [
        {"id_app": r[0], "geometry": json.loads(r[1])}
        for r in cursor.fetchall()
        if r[1]
    ]

    cursor.close()
    return imoveis_docs, reservas_docs, ucs_docs, apps_docs


def inserir_em_lotes(collection, docs: List[Dict], tamanho_lote: int = 5000):
    """Insere documentos em lotes para eficiencia de rede e memoria."""
    total = len(docs)
    if total == 0:
        return
    for i in range(0, total, tamanho_lote):
        lote = docs[i : i + tamanho_lote]
        collection.insert_many(lote, ordered=False)


def main():
    parser = argparse.ArgumentParser(description="Carga e indexacao espacial no MongoDB (Benchmark E1).")
    parser.add_argument("--mongo-uri", default=os.getenv("MONGO_URI", "mongodb://localhost:27017"))
    parser.add_argument("--mongo-db", default=os.getenv("MONGO_DB", "corta-fogo-mongo"))
    parser.add_argument("--data-dir", default=os.getenv("DATA_DIR", "data"))
    parser.add_argument("--pg-host", default=os.getenv("POSTGRES_HOST", "localhost"))
    parser.add_argument("--pg-port", default=int(os.getenv("POSTGRES_PORT", "5434")))
    parser.add_argument("--pg-db", default=os.getenv("POSTGRES_DB", "corta-fogo-df"))
    parser.add_argument("--pg-user", default=os.getenv("POSTGRES_USER", "corta-fogo"))
    parser.add_argument("--pg-password", default=os.getenv("POSTGRES_PASSWORD", "corta-fogo"))
    parser.add_argument("--drop-before", action="store_true", default=True, help="Limpa as colecoes antes de carregar.")

    args = parser.parse_args()

    print("=" * 60)
    print("BENCHMARK MONGODB: CARGA E INDEXACAO ESPACIAL")
    print(f"MongoDB URI : {args.mongo_uri}")
    print(f"Database    : {args.mongo_db}")
    print(f"Data dir    : {args.data_dir}")
    print("=" * 60)

    try:
        db = conectar_mongo(args.mongo_uri, args.mongo_db)
        print("Conectado ao MongoDB com sucesso.")
    except Exception as e:
        print(f"Erro ao conectar ao MongoDB ({args.mongo_uri}): {e}", file=sys.stderr)
        sys.exit(1)

    if args.drop_before:
        print("Limpando colecoes anteriores...")
        for col_name in ["focos", "imoveis", "reservas", "apps", "ucs"]:
            db[col_name].drop()

    t_inicio_total = time.time()

    # 1. Carga de Focos de Calor
    caminho_csv = os.path.join(args.data_dir, "processed", "focos_df_2015_2025.csv")
    print(f"\n[1/5] Carregando focos de calor de {caminho_csv}...")
    t0 = time.time()
    focos_docs = carregar_focos_csv(caminho_csv)
    inserir_em_lotes(db.focos, focos_docs)
    tempo_focos = time.time() - t0
    print(f"  OK: {len(focos_docs)} focos inseridos em {tempo_focos:.2f} s")

    # 2. Carga das Camadas Territoriais
    pg_conn = tentar_conectar_postgres(args)
    if pg_conn:
        imoveis_docs, reservas_docs, ucs_docs, apps_docs = carregar_de_postgres(pg_conn)
        pg_conn.close()
    else:
        imoveis_docs, reservas_docs, ucs_docs, apps_docs = carregar_camadas_geopandas(args.data_dir)

    print(f"\n[2/5] Inserindo {len(imoveis_docs)} imoveis rurais...")
    t0 = time.time()
    inserir_em_lotes(db.imoveis, imoveis_docs)
    print(f"  OK em {time.time() - t0:.2f} s")

    print(f"\n[3/5] Inserindo {len(reservas_docs)} reservas legais...")
    t0 = time.time()
    inserir_em_lotes(db.reservas, reservas_docs)
    print(f"  OK em {time.time() - t0:.2f} s")

    print(f"\n[4/5] Inserindo {len(ucs_docs)} unidades de conservacao...")
    t0 = time.time()
    inserir_em_lotes(db.ucs, ucs_docs)
    print(f"  OK em {time.time() - t0:.2f} s")

    print(f"\n[5/5] Inserindo {len(apps_docs)} areas de preservacao permanente...")
    t0 = time.time()
    inserir_em_lotes(db.apps, apps_docs)
    print(f"  OK em {time.time() - t0:.2f} s")

    # 3. Criacao dos Indices Espaciais 2dsphere
    print("\nCriando indices espaciais 2dsphere e relacionais...")
    t_idx = time.time()

    print("  Criando indice em focos (geometry: 2dsphere, data_hora_evento: 1)...")
    db.focos.create_index([("geometry", "2dsphere"), ("data_hora_evento", ASCENDING)])

    print("  Criando indice em imoveis (geometry: 2dsphere, cod_imovel: 1)...")
    db.imoveis.create_index([("geometry", "2dsphere")])
    db.imoveis.create_index("cod_imovel")

    print("  Criando indice em reservas (geometry: 2dsphere, cod_imovel: 1)...")
    db.reservas.create_index([("geometry", "2dsphere")])
    db.reservas.create_index("cod_imovel")

    print("  Criando indice em ucs (geometry: 2dsphere)...")
    db.ucs.create_index([("geometry", "2dsphere")])

    print("  Criando indice em apps (geometry: 2dsphere)...")
    db.apps.create_index([("geometry", "2dsphere")])

    tempo_indices = time.time() - t_idx
    print(f"  Indices criados em {tempo_indices:.2f} s")

    tempo_total = time.time() - t_inicio_total
    print("\n" + "=" * 60)
    print("RESUMO DA CARGA NO MONGODB:")
    print(f"  focos                : {db.focos.count_documents({})} docs")
    print(f"  imoveis              : {db.imoveis.count_documents({})} docs")
    print(f"  reservas             : {db.reservas.count_documents({})} docs")
    print(f"  ucs                  : {db.ucs.count_documents({})} docs")
    print(f"  apps                 : {db.apps.count_documents({})} docs")
    print(f"  Tempo total de carga : {tempo_total:.2f} s")
    print("=" * 60)


if __name__ == "__main__":
    main()
