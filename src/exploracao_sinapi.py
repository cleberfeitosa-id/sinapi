"""
Ferramenta de Exploração de Dados SINAPI para Orçamentos
Uso: python3 exploracao_sinapi.py
"""

from ast import IsNot
import pandas as pd
import warnings

warnings.filterwarnings("ignore")

FILE = "/Users/xuxi/anti-projects/sinapi/SINAPI_Custo_Ref_Composicoes_Analitico_CE_202412_Desonerado.xlsx"


def load_data():
    """Carrega os dados do SINAPI"""
    return pd.read_excel(FILE, header=5)


def load():
    df = load_data()
    print(df.head())
    print(df.columns)
    return df


def choosedfforactivities():
    df = load()
    df = df[
        [
            "CODIGO DA COMPOSICAO",
            "DESCRICAO DA COMPOSICAO",
            "UNIDADE",
            "COEFICIENTE",
            "PRECO UNITARIO",
            "CUSTO TOTAL",
            "CODIGO ITEM",
            "DESCRIÇÃO ITEM",
            "UNIDADE ITEM",
            "TIPO ITEM",
        ]
    ]
    print(df.head())
    print(df.columns)
    return df


def choosedfforcosts():
    df = load()
    df = df[
        [
            "CODIGO DA COMPOSICAO",
            "DESCRICAO DA COMPOSICAO",
            "UNIDADE",
            "CUSTO TOTAL",
            "CUSTO MAO DE OBRA",
            "% MAO DE OBRA",
        ]
    ]
    print(df.head())
    print(df.columns)
    return df


def filterbycosts():
    df = choosedfforcosts()
    df = df[df["CUSTO MAO DE OBRA"].notna()]
    print(df.head())
    print(df.columns)
    return df


def filterbyactivities():
    df = choosedfforactivities()
    df = df[df["TIPO ITEM"].notna()]
    df = df[df["DESCRIÇÃO ITEM"].str.contains("ELETRICISTA", case=False)]
    codigos = df["CODIGO DA COMPOSICAO"].unique().tolist()
    return df, codigos


def filter_main_df_by_activities():
    """Filtra o df principal pelos códigos retornados de filterbyactivities"""
    df_atividades, codigos = filterbyactivities()
    df_principal = load_data()
    df_filtrado = df_principal[df_principal["CODIGO DA COMPOSICAO"].isin(codigos)]
    print(df_filtrado.head())
    df_filtrado.to_csv("df_filtrado.csv", index=False)
    return df_filtrado


if __name__ == "__main__":
    result = filter_main_df_by_activities()
    print(result.head())
