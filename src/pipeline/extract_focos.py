#!/usr/bin/env python3
"""
Pipeline de extração e tratamento dos focos de calor do INPE (BDQueimadas).
Filtra dados para o Distrito Federal e prepara o CSV para carga no PostGIS.
"""

import argparse
import os
import tempfile
import urllib.request
import zipfile
from datetime import datetime, timezone
import pandas as pd

BASE_URL = "https://dataserver-coids.inpe.br/queimadas/queimadas/focos/csv/anual/Brasil_todos_sats"


def baixar_e_filtrar_ano(ano: int, data_ingestao_iso: str) -> pd.DataFrame:
    """
    Baixa o arquivo zip de um ano especifico do INPE, filtra o Distrito Federal
    e normaliza as colunas necessarias para a modelagem espacial.
    """
    url = f"{BASE_URL}/focos_br_todos-sats_{ano}.zip"
    print(f"Baixando e processando {ano}: {url}")

    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp_file:
        tmp_path = tmp_file.name

    try:
        urllib.request.urlretrieve(url, tmp_path)

        partes = []
        with zipfile.ZipFile(tmp_path) as z:
            csv_name = next(n for n in z.namelist() if n.lower().endswith(".csv"))
            with z.open(csv_name) as f:
                # Leitura em lotes para evitar estouro de memoria
                for chunk in pd.read_csv(f, chunksize=200_000, dtype=str, encoding="utf-8"):
                    col_estado = next(
                        (c for c in chunk.columns if c.lower() == "estado"), None
                    )
                    if not col_estado:
                        continue

                    # Filtra apenas ocorrencias do Distrito Federal
                    mask_df = chunk[col_estado].str.upper().str.contains(
                        "DISTRITO FEDERAL", na=False
                    )
                    df_filtrado = chunk[mask_df]
                    if not df_filtrado.empty:
                        partes.append(df_filtrado)

        if not partes:
            print(f"Aviso: nenhum foco encontrado para o DF em {ano}.")
            return pd.DataFrame()

        df_ano = pd.concat(partes, ignore_index=True)

        # Padronizacao dos nomes das colunas
        cols_map = {c: c.lower().strip() for c in df_ano.columns}
        df_ano = df_ano.rename(columns=cols_map)

        # Trata carimbo de data/hora do evento e ingestao
        col_data = next((c for c in df_ano.columns if c in ["data_pas", "data_hora"]), None)
        if col_data:
            df_ano["data_hora_evento"] = pd.to_datetime(
                df_ano[col_data], errors="coerce"
            ).dt.strftime("%Y-%m-%d %H:%M:%S")
        else:
            df_ano["data_hora_evento"] = None

        df_ano["data_hora_ingestao"] = data_ingestao_iso

        # Identifica satelite e flag de satelite de referencia
        col_sat = next((c for c in df_ano.columns if c.startswith("satelite")), None)
        if col_sat:
            df_ano["satelite"] = df_ano[col_sat].fillna("DESCONHECIDO").str.strip()
            df_ano["is_satelite_referencia"] = (
                df_ano["satelite"].str.upper().str.contains("AQUA_M-T")
            )
        else:
            df_ano["satelite"] = "DESCONHECIDO"
            df_ano["is_satelite_referencia"] = False

        # Conversao numerica de coordenadas
        df_ano["latitude"] = pd.to_numeric(df_ano["latitude"], errors="coerce")
        df_ano["longitude"] = pd.to_numeric(df_ano["longitude"], errors="coerce")

        # Trata campos analiticos complementares
        if "risco_fogo" in df_ano.columns:
            df_ano["risco_fogo"] = pd.to_numeric(df_ano["risco_fogo"], errors="coerce")
        else:
            df_ano["risco_fogo"] = None

        if "municipio" not in df_ano.columns:
            df_ano["municipio"] = "Brasília"

        if "bioma" not in df_ano.columns:
            df_ano["bioma"] = "Cerrado"

        # Colunas finais organizadas para a carga no banco
        colunas_finais = [
            "latitude",
            "longitude",
            "data_hora_evento",
            "data_hora_ingestao",
            "satelite",
            "is_satelite_referencia",
            "municipio",
            "bioma",
            "risco_fogo",
        ]

        # Mantem apenas colunas presentes
        cols_presentes = [c for c in colunas_finais if c in df_ano.columns]
        return df_ano[cols_presentes]

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def executar_extracao(
    ano_inicio: int = 2015,
    ano_fim: int = 2025,
    output_dir: str = "data/processed",
    output_file: str = "focos_df_2015_2025.csv",
):
    os.makedirs(output_dir, exist_ok=True)
    data_ingestao_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    resultados = []
    resumo_linhas = []

    for ano in range(ano_inicio, ano_fim + 1):
        df_ano = baixar_e_filtrar_ano(ano, data_ingestao_iso)
        if not df_ano.empty:
            total_ano = len(df_ano)
            total_ref = int(df_ano["is_satelite_referencia"].sum())
            satelites_distintos = int(df_ano["satelite"].nunique())

            resumo_linhas.append(
                {
                    "ano": ano,
                    "total_focos": total_ano,
                    "satelite_referencia": total_ref,
                    "satelites_distintos": satelites_distintos,
                }
            )
            resultados.append(df_ano)

    if not resultados:
        print("Erro: nenhum dado foi processado.")
        return

    df_consolidado = pd.concat(resultados, ignore_index=True)
    caminho_final = os.path.join(output_dir, output_file)
    df_consolidado.to_csv(caminho_final, index=False)

    df_resumo = pd.DataFrame(resumo_linhas)
    print("\nResumo da extracao por ano no Distrito Federal:")
    print(df_resumo.to_string(index=False))
    print(
        f"\nTotal geral (2015-2025): {len(df_consolidado)} focos | "
        f"Satélite de referência: {df_consolidado['is_satelite_referencia'].sum()}"
    )
    print(f"Arquivo gerado com sucesso em: {caminho_final}")


def main():
    parser = argparse.ArgumentParser(
        description="Extrai focos de calor do INPE filtrados para o Distrito Federal."
    )
    parser.add_argument("--ano-inicio", type=int, default=2015, help="Ano inicial da serie.")
    parser.add_argument("--ano-fim", type=int, default=2025, help="Ano final da serie.")
    parser.add_argument(
        "--output-dir", type=str, default="data/processed", help="Pasta de saida."
    )
    parser.add_argument(
        "--output-file",
        type=str,
        default="focos_df_2015_2025.csv",
        help="Nome do arquivo CSV gerado.",
    )

    args = parser.parse_args()
    executar_extracao(
        ano_inicio=args.ano_inicio,
        ano_fim=args.ano_fim,
        output_dir=args.output_dir,
        output_file=args.output_file,
    )


if __name__ == "__main__":
    main()
