#!/usr/bin/env python3
"""
Pipeline de carga e saneamento das camadas geograficas no PostGIS.
Lê os shapefiles/GeoJSONs brutos em data/raw, reprojeta para o SRID 31983,
aplica correcao topologica (make_valid) e insere nas tabelas da E1:
- unidade_conservacao
- area_preservacao_permanente
- imovel_car
- reserva_legal
"""

import argparse
import datetime
import os
import sys
import geopandas as gpd
import psycopg2
from psycopg2.extras import execute_batch
from shapely import make_valid
from shapely.geometry import MultiPolygon, Polygon

TARGET_SRID = 31983


def get_db_connection(args):
    """Cria conexao com o banco de dados PostgreSQL."""
    if args.db_url:
        return psycopg2.connect(args.db_url)
    return psycopg2.connect(
        host=args.db_host,
        port=args.db_port,
        dbname=args.db_name,
        user=args.db_user,
        password=args.db_password,
    )


def normalizar_para_multipolygon(geom):
    """
    Saneia e converte qualquer geometria poligonal para MultiPolygon valido.
    Descarta geometrias vazias ou nao poligonais geradas por correcao.
    """
    if geom is None or geom.is_empty:
        return None

    # Correcao topologica de auto-intersecoes e aneis invalidos
    if not geom.is_valid:
        geom = make_valid(geom)

    if geom.is_empty:
        return None

    if isinstance(geom, Polygon):
        return MultiPolygon([geom])
    elif isinstance(geom, MultiPolygon):
        return geom
    elif hasattr(geom, "geoms"):
        # Se for GeometryCollection, filtra apenas poligonos
        polys = []
        for g in geom.geoms:
            if isinstance(g, Polygon):
                polys.append(g)
            elif isinstance(g, MultiPolygon):
                polys.extend(g.geoms)
        if polys:
            return MultiPolygon(polys)
    return None


def carregar_unidades_conservacao(conn, raw_dir: str, data_download: str):
    """Carrega as Unidades de Conservacao a partir do GeoJSON do IBRAM."""
    path = os.path.join(raw_dir, "unidades_conservacao.geojson")
    if not os.path.exists(path):
        print(f"[AVISO] Arquivo nao encontrado: {path}. Pulando UCs.")
        return 0

    print("Processando Unidades de Conservacao...")
    gdf = gpd.read_file(path)
    if gdf.crs is None or gdf.crs.to_epsg() != TARGET_SRID:
        gdf = gdf.to_crs(epsg=TARGET_SRID)

    registros = []
    for _, row in gdf.iterrows():
        nome = str(row.get("nome") or "").strip()
        if not nome:
            continue

        categoria = str(row.get("categoria") or "")[:100]
        uc_conserv = str(row.get("uc_conserv") or "").lower()

        if "integral" in uc_conserv:
            grupo = "protecao_integral"
        elif "sustentavel" in uc_conserv or "sustentável" in uc_conserv:
            grupo = "uso_sustentavel"
        else:
            grupo = None

        geom = normalizar_para_multipolygon(row.geometry)
        if geom is None or geom.is_empty:
            continue

        area_ha = float(row.get("area_ha") or (geom.area / 10000.0))
        area_ha = max(round(area_ha, 4), 0.0001)

        registros.append(
            (
                nome[:200],
                categoria if categoria else None,
                grupo,
                area_ha,
                "IBRAM / Geoportal DF",
                data_download,
                geom.wkb_hex,
            )
        )

    sql = """
        INSERT INTO unidade_conservacao (nome, categoria, grupo, area_ha, fonte, data_download, geom)
        VALUES (%s, %s, %s, %s, %s, %s, ST_SetSRID(ST_GeomFromWKB(decode(%s, 'hex')), 31983))
    """
    with conn.cursor() as cur:
        execute_batch(cur, sql, registros, page_size=200)
    conn.commit()
    print(f"  -> {len(registros)} Unidades de Conservacao carregadas com sucesso.")
    return len(registros)


def carregar_apps_ibram(conn, raw_dir: str, data_download: str):
    """Carrega as APPs fisicas mapeadas pelo IBRAM/SISDIA."""
    camadas_app = [
        ("app_nascentes.geojson", "nascente"),
        ("app_borda_chapada.geojson", "borda_de_chapada"),
        ("app_reservatorio.geojson", "reservatorio"),
    ]

    total_carregado = 0
    sql = """
        INSERT INTO area_preservacao_permanente (tipo, area_ha, data_download, geom)
        VALUES (%s, %s, %s, %s, ST_SetSRID(ST_GeomFromWKB(decode(%s, 'hex')), 31983))
    """

    for filename, tipo in camadas_app:
        path = os.path.join(raw_dir, filename)
        if not os.path.exists(path):
            continue

        print(f"Processando APPs ({tipo})...")
        gdf = gpd.read_file(path)
        if gdf.crs is None or gdf.crs.to_epsg() != TARGET_SRID:
            gdf = gdf.to_crs(epsg=TARGET_SRID)

        registros = []
        for _, row in gdf.iterrows():
            geom = normalizar_para_multipolygon(row.geometry)
            if geom is None or geom.is_empty:
                continue

            area_ha = geom.area / 10000.0
            area_ha = max(round(area_ha, 4), 0.0001)

            registros.append(
                (
                    None,
                    tipo,
                    area_ha,
                    "IBRAM / Geoportal DF",
                    data_download,
                    geom.wkb_hex,
                )
            )

        with conn.cursor() as cur:
            execute_batch(
                cur,
                """
                INSERT INTO area_preservacao_permanente (cod_imovel, tipo, area_ha, fonte, data_download, geom)
                VALUES (%s, %s, %s, %s, %s, ST_SetSRID(ST_GeomFromWKB(decode(%s, 'hex')), 31983))
                """,
                registros,
                page_size=500,
            )
        conn.commit()
        print(f"  -> {len(registros)} APPs ({tipo}) carregadas.")
        total_carregado += len(registros)

    return total_carregado


def carregar_imoveis_car(conn, raw_dir: str, data_download: str) -> set:
    """Carrega os imoveis rurais do CAR-DF a partir do zip do SICAR."""
    zip_path = os.path.join(raw_dir, "AREA_IMOVEL.zip")
    if not os.path.exists(zip_path):
        print(f"[AVISO] Arquivo {zip_path} nao encontrado. Pulando imoveis.")
        return set()

    print("Processando Imoveis Rurais do CAR-DF (pode levar cerca de 1 minuto)...")
    gdf = gpd.read_file(f"zip://{zip_path}")
    if gdf.crs is None or gdf.crs.to_epsg() != TARGET_SRID:
        gdf = gdf.to_crs(epsg=TARGET_SRID)

    registros = []
    cods_inseridos = set()

    for _, row in gdf.iterrows():
        cod = str(row.get("cod_imovel") or "").strip()
        if not cod.startswith("DF-") or cod in cods_inseridos:
            continue

        situacao = str(row.get("ind_status") or "")[:40]
        condicao = str(row.get("des_condic") or "")[:200]

        geom = normalizar_para_multipolygon(row.geometry)
        if geom is None or geom.is_empty:
            continue

        try:
            area_ha = float(row.get("num_area") or (geom.area / 10000.0))
        except (ValueError, TypeError):
            area_ha = geom.area / 10000.0

        area_ha = max(round(area_ha, 4), 0.0001)

        registros.append(
            (
                cod,
                situacao if situacao else None,
                condicao if condicao else None,
                area_ha,
                data_download,
                geom.wkb_hex,
            )
        )
        cods_inseridos.add(cod)

    sql = """
        INSERT INTO imovel_car (cod_imovel, situacao, condicao, area_ha, data_download, geom)
        VALUES (%s, %s, %s, %s, %s, ST_SetSRID(ST_GeomFromWKB(decode(%s, 'hex')), 31983))
        ON CONFLICT (cod_imovel) DO NOTHING
    """
    with conn.cursor() as cur:
        execute_batch(cur, sql, registros, page_size=1000)
    conn.commit()
    print(f"  -> {len(registros)} Imoveis rurais do CAR carregados.")
    return cods_inseridos


def carregar_reserva_legal(conn, raw_dir: str, data_download: str, cods_validos: set):
    """Carrega as Reservas Legais do CAR-DF respeitando a FK com imovel_car."""
    zip_path = os.path.join(raw_dir, "RESERVA_LEGAL.zip")
    if not os.path.exists(zip_path):
        print(f"[AVISO] Arquivo {zip_path} nao encontrado. Pulando reserva legal.")
        return 0

    print("Processando Reserva Legal do CAR-DF...")
    gdf = gpd.read_file(f"zip://{zip_path}")
    if gdf.crs is None or gdf.crs.to_epsg() != TARGET_SRID:
        gdf = gdf.to_crs(epsg=TARGET_SRID)

    registros = []
    for _, row in gdf.iterrows():
        cod = str(row.get("cod_imovel") or "").strip()
        if not cod or (cods_validos and cod not in cods_validos):
            continue

        situacao = str(row.get("ind_status") or "")[:40]
        geom = normalizar_para_multipolygon(row.geometry)
        if geom is None or geom.is_empty:
            continue

        try:
            area_ha = float(row.get("num_area") or (geom.area / 10000.0))
        except (ValueError, TypeError):
            area_ha = geom.area / 10000.0

        area_ha = max(round(area_ha, 4), 0.0001)

        registros.append(
            (
                cod,
                situacao if situacao else None,
                area_ha,
                data_download,
                geom.wkb_hex,
            )
        )

    sql = """
        INSERT INTO reserva_legal (cod_imovel, situacao, area_ha, data_download, geom)
        VALUES (%s, %s, %s, %s, ST_SetSRID(ST_GeomFromWKB(decode(%s, 'hex')), 31983))
    """
    with conn.cursor() as cur:
        execute_batch(cur, sql, registros, page_size=1000)
    conn.commit()
    print(f"  -> {len(registros)} Reservas Legais carregadas com sucesso.")
    return len(registros)


def main():
    parser = argparse.ArgumentParser(
        description="Carrega camadas geograficas (UCs, APPs e CAR) no PostGIS com SRID 31983."
    )
    parser.add_argument(
        "--raw-dir",
        default=os.path.join("data", "raw"),
        help="Diretorio com arquivos brutos (padrao: data/raw).",
    )
    parser.add_argument(
        "--db-host",
        default=os.getenv("DB_HOST", "localhost"),
        help="Host do PostgreSQL (padrao: localhost).",
    )
    parser.add_argument(
        "--db-port",
        default=int(os.getenv("DB_PORT", "5434")),
        help="Porta do PostgreSQL (padrao: 5434).",
    )
    parser.add_argument(
        "--db-name",
        default=os.getenv("DB_NAME", "corta-fogo-df"),
        help="Nome do banco de dados (padrao: corta-fogo-df).",
    )
    parser.add_argument(
        "--db-user",
        default=os.getenv("DB_USER", "queimada"),
        help="Usuario do banco (padrao: queimada).",
    )
    parser.add_argument(
        "--db-password",
        default=os.getenv("DB_PASSWORD", "queimada"),
        help="Senha do banco (padrao: queimada).",
    )
    parser.add_argument(
        "--db-url",
        default=os.getenv("DATABASE_URL"),
        help="URL completa de conexao (sobrescreve parametros individuais).",
    )
    parser.add_argument(
        "--no-truncate",
        action="store_true",
        help="Nao limpa as tabelas antes da carga.",
    )

    args = parser.parse_args()
    data_download = datetime.date.today().isoformat()

    try:
        conn = get_db_connection(args)
        print("Conexao com o PostgreSQL estabelecida com sucesso.")
    except Exception as e:
        print(f"Erro ao conectar ao PostgreSQL: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        if not args.no_truncate:
            print("Limpando tabelas geograficas para carga limpa...")
            with conn.cursor() as cur:
                cur.execute("""
                    TRUNCATE TABLE reserva_legal, imovel_car, area_preservacao_permanente, unidade_conservacao, hidrografia RESTART IDENTITY CASCADE;
                """)
            conn.commit()

        carregar_unidades_conservacao(conn, args.raw_dir, data_download)
        carregar_apps_ibram(conn, args.raw_dir, data_download)
        cods = carregar_imoveis_car(conn, args.raw_dir, data_download)
        carregar_reserva_legal(conn, args.raw_dir, data_download, cods)

        with conn.cursor() as cur:
            cur.execute("ANALYZE unidade_conservacao, area_preservacao_permanente, imovel_car, reserva_legal;")
        conn.commit()

        print("\nCarga de todas as camadas geograficas finalizada com exito.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
