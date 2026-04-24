#!/usr/bin/env python3
"""
Script de Extração e Cruzamento Projeto Elétrico → SINAPI
Gera relatório detalhado em markdown para orçamento de mão de obra

Autor: opencode
Data: 2026-03-26
"""

import pandas as pd
import pdfplumber
import re
import warnings
from datetime import datetime

warnings.filterwarnings("ignore")

FILE_PDF = "/Users/xuxi/anti-projects/sinapi/ELE.pdf"
FILE_SINAPI = "/Users/xuxi/anti-projects/sinapi/SINAPI_Custo_Ref_Composicoes_Analitico_CE_202412_Desonerado.xlsx"
OUTPUT_MD = "/Users/xuxi/anti-projects/sinapi/relatorio_orcamento.md"

CATEGORIAS_SINAPI = {
    "ELETRICO": {
        "tomada_alta": {
            "descricao": "Tomada alta 2P+T (sem suporte e sem placa)",
            "termo_busca": "TOMADA ALTA",
            "unidade": "un",
            "referencia": "Código SINAPI 91990",
            "notas": "Instalação a 2,20m do piso, sem suporte e sem placa",
        },
        "tomada_media": {
            "descricao": "Tomada média 2P+T (sem suporte e sem placa)",
            "termo_busca": "TOMADA MEDIA",
            "unidade": "un",
            "referencia": "Código SINAPI 91994",
            "notas": "Instalação a 1,10m do piso",
        },
        "tomada_baixa": {
            "descricao": "Tomada baixa 2P+T",
            "termo_busca": "TOMADA BAIXA",
            "unidade": "un",
            "referencia": "Código SINAPI 91996",
            "notas": "Instalação a 0,30m do piso",
        },
        "interruptor_simples": {
            "descricao": "Interruptor simples 1 tecla",
            "termo_busca": "INTERRUPTOR SIMPLES",
            "unidade": "un",
            "referencia": "Código SINAPI 91940",
            "notas": "Interruptor unipolar 10A, instalado a 1,10m do piso",
        },
        "interruptor_paralelo": {
            "descricao": "Interruptor paralelo (three-way)",
            "termo_busca": "INTERRUPTOR PARALELO",
            "unidade": "un",
            "referencia": "Código SINAPI 91941",
            "notas": "Interruptor paralelo para comando em dois pontos",
        },
        "interruptor_duas_teclas": {
            "descricao": "Interruptor simples 2 teclas",
            "termo_busca": "INTERRUPTOR 2 TECLAS",
            "unidade": "un",
            "referencia": "Código SINAPI 91942",
            "notas": "Interruptor para dois circuitos",
        },
        "interruptor_tres_teclas": {
            "descricao": "Interruptor simples 3 teclas",
            "termo_busca": "INTERRUPTOR 3 TECLAS",
            "unidade": "un",
            "referencia": "Código SINAPI 91943",
            "notas": "Interruptor para três circuitos",
        },
        "disjuntor_20a": {
            "descricao": "Disjuntor bipolar DIN 20A",
            "termo_busca": "DISJUNTOR 20A",
            "unidade": "un",
            "referencia": "Código SINAPI 91803",
            "notas": "Disjuntor termomagnético, curva C, 20A",
        },
        "disjuntor_16a": {
            "descricao": "Disjuntor bipolar DIN 16A",
            "termo_busca": "DISJUNTOR 16A",
            "unidade": "un",
            "referencia": "Código SINAPI 91801",
            "notas": "Disjuntor termomagnético, curva C, 16A",
        },
        "disjuntor_32a": {
            "descricao": "Disjuntor bipolar DIN 32A",
            "termo_busca": "DISJUNTOR 32A",
            "unidade": "un",
            "referencia": "Código SINAPI 91805",
            "notas": "Disjuntor termomagnético, curva C, 32A",
        },
        "disjuntor_63a": {
            "descricao": "Disjuntor bipolar DIN 63A",
            "termo_busca": "DISJUNTOR 63A",
            "unidade": "un",
            "referencia": "Código SINAPI 91807",
            "notas": "Disjuntor geral de entrada",
        },
        "eletroduto_pvc_25": {
            "descricao": 'Eletroduto PVC corrugado DN 25mm (3/4")',
            "termo_busca": "ELETRODUTO 25",
            "unidade": "m",
            "referencia": "Código SINAPI 91834",
            "notas": "Eletroduto flexível corrugado, DN 25mm",
        },
        "eletroduto_pvc_20": {
            "descricao": 'Eletroduto PVC corrugado DN 20mm (1/2")',
            "termo_busca": "ELETRODUTO 20",
            "unidade": "m",
            "referencia": "Código SINAPI 91833",
            "notas": "Eletroduto flexível corrugado, DN 20mm",
        },
        "caixa_eletrica": {
            "descricao": 'Caixa de passagem 2x4"',
            "termo_busca": "CAIXA 2X4",
            "unidade": "un",
            "referencia": "Código SINAPI específico",
            "notas": 'Caixa de embutir 2x4" para tomadas e interruptores',
        },
        "fio_2_5": {
            "descricao": "Fio de cobre 2,5mm²",
            "termo_busca": "FIO 2,5",
            "unidade": "m",
            "referencia": "Insumo - verificar código",
            "notas": "Fio isolado PVC 750V",
        },
        "fio_4": {
            "descricao": "Fio de cobre 4mm²",
            "termo_busca": "FIO 4",
            "unidade": "m",
            "referencia": "Insumo - verificar código",
            "notas": "Fio isolado PVC 750V",
        },
        "cabo_2_5": {
            "descricao": "Cabo de cobre 2,5mm²",
            "termo_busca": "CABO 2,5",
            "unidade": "m",
            "referencia": "Insumo - verificar código",
            "notas": "Cabo unipolar 0,6/1kV",
        },
        "cabo_4": {
            "descricao": "Cabo de cobre 4mm²",
            "termo_busca": "CABO 4",
            "unidade": "m",
            "referencia": "Insumo - verificar código",
            "notas": "Cabo unipolar 0,6/1kV",
        },
        "cabo_6": {
            "descricao": "Cabo de cobre 6mm²",
            "termo_busca": "CABO 6",
            "unidade": "m",
            "referencia": "Insumo - verificar código",
            "notas": "Cabo unipolar 0,6/1kV",
        },
        "cabo_10": {
            "descricao": "Cabo de cobre 10mm²",
            "termo_busca": "CABO 10",
            "unidade": "m",
            "referencia": "Insumo - verificar código",
            "notas": "Cabo unipolar 0,6/1kV",
        },
        "cabo_16": {
            "descricao": "Cabo de cobre 16mm²",
            "termo_busca": "CABO 16",
            "unidade": "m",
            "referencia": "Insumo - verificar código",
            "notas": "Cabo unipolar 0,6/1kV",
        },
        "cabo_25": {
            "descricao": "Cabo de cobre 25mm²",
            "termo_busca": "CABO 25",
            "unidade": "m",
            "referencia": "Insumo - verificar código",
            "notas": "Cabo unipolar 0,6/1kV",
        },
        "quadro_distribuicao": {
            "descricao": "Quadro de distribuição de embutir",
            "termo_busca": "QUADRO DISTRIBUICAO",
            "unidade": "un",
            "referencia": "Código SINAPI 91924",
            "notas": "Quadro de distribuição com barramento",
        },
        "luminaria_teto": {
            "descricao": "Luminária de teto",
            "termo_busca": "LUMINARIA TETO",
            "unidade": "un",
            "referencia": "Verificar código específico",
            "notas": "Luminária para fixation no teto",
        },
        "luminaria_embutir": {
            "descricao": "Luminária de embutir",
            "termo_busca": "LUMINARIA EMBUTIR",
            "unidade": "un",
            "referencia": "Verificar código específico",
            "notas": "Luminária para embutir em forro",
        },
        "projetor": {
            "descricao": "Projetor-spot",
            "termo_busca": "PROJETOR",
            "unidade": "un",
            "referencia": "Verificar código específico",
            "notas": "Spot ou projetor para iluminação",
        },
        "arandela": {
            "descricao": "Arandela",
            "termo_busca": "ARANDE",
            "unidade": "un",
            "referencia": "Verificar código específico",
            "notas": "Luminária de parede",
        },
    },
    "SPDA": {
        "spda_haste": {
            "descricao": "Haste de captação SPDA",
            "termo_busca": "HASTE SPDA",
            "unidade": "un",
            "referencia": "Código SINAPI 96587",
            "notas": "Haste copperweld ou aço copperado",
        },
        "spda_cabo_nu": {
            "descricao": "Cabo de cobre nu para SPDA",
            "termo_busca": "CABO NU",
            "unidade": "m",
            "referencia": "Insumo - verificar código",
            "notas": "Cabo de cobre nu para descidas e interligações",
        },
        "spda_aterramento": {
            "descricao": "Sistema de aterramento SPDA",
            "termo_busca": "ATERRA",
            "unidade": "un",
            "referencia": "Código SINAPI 96587",
            "notas": "Haste de aterramento, conexões, cabo nu",
        },
        "spda_fixacao": {
            "descricao": "Fixação e suporte SPDA",
            "termo_busca": "SUPorte SPDA",
            "unidade": "un",
            "referencia": "Verificar código específico",
            "notas": "Suportes, braçadeiras, ancoragens",
        },
    },
    "RTA": {
        "rta_eletrocalha": {
            "descricao": "Eletrocalha aço galvanizado",
            "termo_busca": "ELETROCALHA",
            "unidade": "m",
            "referencia": "Verificar código específico",
            "notas": "Eletrocalha 50x50mm ou similar",
        },
        "rta_canaleta": {
            "descricao": "Canaleta para cabos",
            "termo_busca": "CANALETA",
            "unidade": "m",
            "referencia": "Verificar código específico",
            "notas": "Canaleta evolutiva ou aparente",
        },
        "rta_terminal": {
            "descricao": "Terminal para cabo",
            "termo_busca": "TERMINAL",
            "unidade": "un",
            "referencia": "Verificar código específico",
            "notas": "Terminal de compressão ou solda",
        },
        "rta_conector": {
            "descricao": "Conector para cabo",
            "termo_busca": "CONECTOR",
            "unidade": "un",
            "referencia": "Verificar código específico",
            "notas": "Conector de compression",
        },
        "rta_curva": {
            "descricao": "Curva para eletrocalha/canaleta",
            "termo_busca": "CURVA",
            "unidade": "un",
            "referencia": "Verificar código específico",
            "notas": "Curva 90° ou 45°",
        },
    },
    "BOMBAS": {
        "bomba": {
            "descricao": "Bomba",
            "termo_busca": "BOMBA",
            "unidade": "un",
            "referencia": "Não previsto em SINAPI padrão",
            "notas": "Verificar especificação técnica - geralmente equipamento",
        },
        "bomba_pressurizador": {
            "descricao": "Bomba pressurizadora",
            "termo_busca": "PRESSURIZ",
            "unidade": "un",
            "referencia": "Não previsto em SINAPI padrão",
            "notas": "Verificar especificação técnica",
        },
        "filtro": {
            "descricao": "Filtro",
            "termo_busca": "FILTRO",
            "unidade": "un",
            "referencia": "Verificar código específico",
            "notas": "Filtro de linha ou sistema",
        },
        "bombas_cano": {
            "descricao": "Tubulação para bombas",
            "termo_busca": "TUBO",
            "unidade": "m",
            "referencia": "Verificar código específico",
            "notas": "Tubulação de sucção e recalque",
        },
    },
}


def carregar_sinapi():
    print("  [1/5] Carregando dados do SINAPI...")
    df = pd.read_excel(FILE_SINAPI, header=5)
    print(f"         Total de registros: {len(df)}")
    return df


def extrair_quadro_cargas(pdf_path):
    print("  [2/5] Extraindo quadro de cargas do PDF...")

    dados = {"terreo": {"circuitos": []}, "superior": {"circuitos": []}}

    with pdfplumber.open(pdf_path) as pdf:
        page3 = pdf.pages[2]
        tables = page3.extract_tables()

        for table in tables[:3]:
            if not table:
                continue
            for row in table:
                if not row or not row[0]:
                    continue
                try:
                    circuito = str(row[0]).strip()
                    if not circuito.isdigit():
                        continue
                    desc = row[1] if len(row) > 1 else ""
                    pot = row[10] if len(row) > 10 else ""
                    disj = row[21] if len(row) > 21 else ""
                    dados["terreo"]["circuitos"].append(
                        {
                            "numero": circuito,
                            "descricao": desc,
                            "potencia_va": pot,
                            "disjuntor": disj,
                        }
                    )
                except:
                    pass

        for table in tables[3:6]:
            if not table:
                continue
            for row in table:
                if not row or not row[0]:
                    continue
                try:
                    circuito = str(row[0]).strip()
                    if not circuito.isdigit():
                        continue
                    desc = row[1] if len(row) > 1 else ""
                    dados["superior"]["circuitos"].append(
                        {"numero": circuito, "descricao": desc}
                    )
                except:
                    pass

    print(f"         Circuitos térreo: {len(dados['terreo']['circuitos'])}")
    print(f"         Circuitos superior: {len(dados['superior']['circuitos'])}")
    return dados


def buscar_servico_sinapi(df_sinapi, termo_busca):
    resultados = df_sinapi[
        df_sinapi["DESCRICAO DA COMPOSICAO"].str.contains(
            termo_busca, case=False, na=False
        )
    ]
    resultados = resultados[resultados["CUSTO TOTAL"].notna()]
    resultados = resultados.drop_duplicates(subset=["CODIGO DA COMPOSICAO"])

    return resultados[
        [
            "CODIGO DA COMPOSICAO",
            "DESCRICAO DA COMPOSICAO",
            "UNIDADE",
            "CUSTO TOTAL",
            "CUSTO MAO DE OBRA",
            "% MAO DE OBRA",
            "CUSTO MATERIAL",
            "% MATERIAL",
        ]
    ].head(10)


def gerar_relatorio_markdown(dados_projeto, df_sinapi):
    print("  [4/5] Gerando relatório em markdown...")

    md = []

    md.append("# RELATÓRIO DE ORÇAMENTO - MÃO DE OBRA ELÉTRICA\n")
    md.append(f"**Data:** {datetime.now().strftime('%d/%m/%Y')}\n")
    md.append("**Projeto:** Universidade Federal do Cariri - UFCA (Bloco O)\n")
    md.append("**Objetivo:** Estimar custo de mão de obra para execução das ")
    md.append("instalações elétricas, cruzando dados do projeto com composição ")
    md.append("de custos SINAPI (Custo de Referência - CE - Desonerado, 12/2024)\n")
    md.append("---\n")

    md.append("## 1. QUADRO DE CARGAS EXTRAÍDO DO PROJETO\n")

    md.append("### 1.1 Térreo\n")
    md.append("| Circuito | Descrição | Potência (VA) | Disjuntor (A) |\n")
    md.append("|----------|-----------|---------------|----------------|\n")
    for circ in dados_projeto["terreo"]["circuitos"]:
        md.append(
            f"| {circ['numero']} | {circ['descricao']} | {circ.get('potencia_va', '-')} | {circ.get('disjuntor', '-')} |\n"
        )

    md.append("\n### 1.2 Superior\n")
    md.append("| Circuito | Descrição |\n")
    md.append("|----------|-----------|\n")
    for circ in dados_projeto["superior"]["circuitos"]:
        md.append(f"| {circ['numero']} | {circ['descricao']} |\n")

    md.append("\n---\n")
    md.append("## 2. CRUZAMENTO COM SINAPI\n")
    md.append("> **Metodologia:** Para cada item do projeto, foi realizada busca ")
    md.append("no banco de dados SINAPI utilizando termos específicos que ")
    md.append("correspondem aos serviços típicos de instalação elétrica. ")
    md.append("Os custos de mão de obra são baseados na composição analítica. ")
    md.append("**Referência:** SINAPI Ceará (CE) - Desonerado - 12/2024\n")

    for categoria, itens in CATEGORIAS_SINAPI.items():
        md.append(f"\n---\n")
        md.append(f"## {categoria}\n")

        for chave, info in itens.items():
            md.append(f"\n### {info['descricao']}\n")
            md.append(f"- **Unidade:** {info['unidade']}\n")
            md.append(f"- **Referência SINAPI:** {info['referencia']}\n")
            md.append(f"- **Notas:** {info['notas']}\n")
            md.append(f"- **Termo de busca:** `{info['termo_busca']}`\n")
            md.append("\n**Resultado da busca no SINAPI:**\n")

            resultados = buscar_servico_sinapi(df_sinapi, info["termo_busca"])

            if resultados.empty:
                md.append("*Nenhum serviço encontrado com este termo.*\n")
                md.append(
                    "**Sugestão:** Rever termo de busca ou verificar manualmente no sistema SINAPI.\n"
                )
            else:
                md.append(
                    "| Código | Descrição | Und | Custo Total | Mão de Obra | % MO | Material | % Mat |\n"
                )
                md.append(
                    "|--------|-----------|-----|-------------|-------------|-----|----------|-------|\n"
                )

                for _, row in resultados.iterrows():
                    custo = row["CUSTO TOTAL"]
                    mo = row["CUSTO MAO DE OBRA"]
                    pct_mo = row["% MAO DE OBRA"]
                    mat = row["CUSTO MATERIAL"]
                    pct_mat = row["% MATERIAL"]

                    desc = str(row["DESCRICAO DA COMPOSICAO"])[:40]

                    md.append(
                        f"| {row['CODIGO DA COMPOSICAO']:.0f} | {desc}... | "
                        f"{row['UNIDADE']} | R$ {custo} | R$ {mo} | {pct_mo}% | R$ {mat} | {pct_mat}% |\n"
                    )

            md.append(f"\n**Quantidade estimada do projeto:** A definir conforme ")
            md.append("levantamento de quantitativos nas plantas.\n")

    md.append("---\n")
    md.append("## 3. OBSERVAÇÕES IMPORTANTES\n")
    md.append("1. **Percentual de Mão de Obra:** Os valores apresentados são ")
    md.append("baseados no custo desonerado (sem encargos sociais sobre a folha). ")
    md.append("Recomenda-se aplicar BDI conforme a obra.\n")
    md.append("2. **Quantitativos:** Este relatório apresenta custos unitários. ")
    md.append("Multiplicar pela quantidade de cada item no projeto para obter ")
    md.append("o orçamento total.\n")
    md.append("3. **Atividades Não Inclusas:** Verificar nas composições SINAPI se ")
    md.append("há atividades não previstas (ex: infraestrutura, adaptações, etc).\n")
    md.append("4. **Profissionais Previstos:** As composições tipicamente incluem ")
    md.append("Eletricista e Auxiliar de Eletricista.\n")
    md.append("5. **Referências:** Este relatório utiliza o SINAPI de Ceará (CE) ")
    md.append("com data de referência 12/2024, versão desonerada.\n")

    md.append(
        f"\n---\n*Relatório gerado automaticamente em {datetime.now().strftime('%d/%m/%Y %H:%M')}*"
    )

    return "\n".join(md)


def main():
    print("\n" + "=" * 60)
    print("EXTRAÇÃO E CRUZAMENTO PROJETO ELÉTRICO → SINAPI")
    print("=" * 60 + "\n")

    df_sinapi = carregar_sinapi()
    dados_projeto = extrair_quadro_cargas(FILE_PDF)
    relatorio = gerar_relatorio_markdown(dados_projeto, df_sinapi)

    print(f"  [5/5] Salvando relatório em: {OUTPUT_MD}")
    with open(OUTPUT_MD, "w", encoding="utf-8") as f:
        f.write(relatorio)

    print("\n" + "=" * 60)
    print("RELATÓRIO GERADO COM SUCESSO!")
    print("=" * 60)


if __name__ == "__main__":
    main()
