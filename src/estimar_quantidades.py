#!/usr/bin/env python3
"""
Script para Estimativa de Quantitativos a partir de Plantas Elétricas (PDF)
Com visualização annotada em PDF

Autor: opencode
Data: 2026-03-26
"""

import os
import re
import pandas as pd
import pdfplumber
import warnings
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor

warnings.filterwarnings("ignore")

FILE_PDF = "/Users/xuxi/anti-projects/sinapi/ELE.pdf"
FILE_SINAPI = "/Users/xuxi/anti-projects/sinapi/SINAPI_Custo_Ref_Composicoes_Analitico_CE_202412_Desonerado.xlsx"
OUTPUT_DIR = "/Users/xuxi/anti-projects/sinapi/quantidades_extraidas"

os.makedirs(OUTPUT_DIR, exist_ok=True)

SIMBOLOS_ELETRICOS = {
    "tomada_baixa": {
        "padroes": ["TB", "TOMADA BAIXA", "T.B."],
        "descricao": "Tomada baixa",
        "categoria": "TOMADA",
        "cor": "#FF6B6B",
    },
    "tomada_media": {
        "padroes": ["TM", "TOMADA MEDIA", "T.M."],
        "descricao": "Tomada média",
        "categoria": "TOMADA",
        "cor": "#FF6B6B",
    },
    "tomada_alta": {
        "padroes": ["TA", "TOMADA ALTA", "T.A."],
        "descricao": "Tomada alta",
        "categoria": "TOMADA",
        "cor": "#FF6B6B",
    },
    "int_simples": {
        "padroes": ["I ", "INT", "1 TECLA"],
        "descricao": "Interruptor",
        "categoria": "INTERRUPTOR",
        "cor": "#4ECDC4",
    },
    "luminaria_led": {
        "padroes": ["LED", "L LED"],
        "descricao": "Luminária LED",
        "categoria": "ILUMINACAO",
        "cor": "#FFE66D",
    },
    "luminaria_tubo": {
        "padroes": ["L ", "LUM", "2x18W", "2x9W"],
        "descricao": "Luminária tubular",
        "categoria": "ILUMINACAO",
        "cor": "#FFE66D",
    },
    "quadro": {
        "padroes": ["QLF", "QD", "QUADRO"],
        "descricao": "Quadro",
        "categoria": "QUADRO",
        "cor": "#95E1D3",
    },
    "caixa": {
        "padroes": ["CP", "CX", "CAIXA"],
        "descricao": "Caixa",
        "categoria": "CAIXA",
        "cor": "#A8E6CF",
    },
}


def extrair_textos_e_tabelas(pdf_path):
    """Extrai texto e tabelas de cada página"""
    dados = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            texto = page.extract_text()
            tabelas = page.extract_tables()
            dados.append(
                {"pagina": i + 1, "texto": texto, "tabelas": tabelas, "page_obj": page}
            )
    return dados


def extrair_quadro_cargas(pdf_path):
    """Extrai quadro de cargas com correção"""
    quadro = {
        "terreo": {"circuitos": [], "iluminacao": 0, "tomadas": 0},
        "superior": {"circuitos": [], "iluminacao": 0, "tomadas": 0},
    }

    with pdfplumber.open(pdf_path) as pdf:
        page3 = pdf.pages[2]
        tables = page3.extract_tables()

        # Tabela térreo (índice 2)
        if len(tables) > 2:
            for row in tables[2]:
                if not row or not row[0]:
                    continue
                try:
                    circ = str(row[0]).strip()
                    if not circ.isdigit():
                        continue
                    desc = str(row[1]) if len(row) > 1 else ""
                    pot = str(row[9]) if len(row) > 9 and row[9] else ""
                    disj = str(row[20]) if len(row) > 20 and row[20] else ""

                    if "ILUMIN" in desc.upper() and pot:
                        try:
                            quadro["terreo"]["iluminacao"] += float(
                                pot.replace(",", ".")
                            )
                        except:
                            pass
                    elif ("TUG" in desc.upper() or "TOMADA" in desc.upper()) and pot:
                        try:
                            quadro["terreo"]["tomadas"] += float(pot.replace(",", "."))
                        except:
                            pass

                    quadro["terreo"]["circuitos"].append(
                        {
                            "numero": circ,
                            "descricao": desc,
                            "potencia_va": pot,
                            "disjuntor": disj,
                        }
                    )
                except:
                    pass

        # Tabela superior (índice 3) - potência está na coluna 12!
        if len(tables) > 3:
            for row in tables[3]:
                if not row or not row[0]:
                    continue
                try:
                    circ = str(row[0]).strip()
                    if not circ.isdigit():
                        continue
                    desc = str(row[1]) if len(row) > 1 else ""
                    pot = str(row[12]) if len(row) > 12 and row[12] else ""
                    disj = str(row[23]) if len(row) > 23 and row[23] else ""

                    if "ILUMIN" in desc.upper() and pot:
                        try:
                            quadro["superior"]["iluminacao"] += float(
                                pot.replace(",", ".")
                            )
                        except:
                            pass
                    elif ("TUG" in desc.upper() or "TOMADA" in desc.upper()) and pot:
                        try:
                            quadro["superior"]["tomadas"] += float(
                                pot.replace(",", ".")
                            )
                        except:
                            pass

                    quadro["superior"]["circuitos"].append(
                        {
                            "numero": circ,
                            "descricao": desc,
                            "potencia_va": pot,
                            "disjuntor": disj,
                        }
                    )
                except:
                    pass

    return quadro


def detectar_simbolos(dados_paginas):
    """Detecta símbolos em todas as páginas"""
    contadores = {}

    for dados in dados_paginas:
        texto = dados.get("texto", "")
        if not texto:
            continue

        texto_upper = texto.upper()

        for chave, info in SIMBOLOS_ELETRICOS.items():
            for padrao in info["padroes"]:
                # Conta ocorrências do padrão
                matches = re.findall(
                    r"\b" + re.escape(padrao.upper()) + r"\b", texto_upper
                )
                qtd = len(matches)

                if qtd > 0:
                    if chave not in contadores:
                        contadores[chave] = {
                            "descricao": info["descricao"],
                            "categoria": info["categoria"],
                            "cor": info["cor"],
                            "quantidade": 0,
                            "paginas": [],
                        }
                    contadores[chave]["quantidade"] += qtd
                    contadores[chave]["paginas"].append(dados["pagina"])

    return contadores


def estimar_eletrodutos(quadro):
    """
    ESTIMATIVA DE ELETRODUTOS

    Metodologia:
    - Considera-se que cada 10-15 VA de carga requer 1 metro de eletroduto
    - Este valor inclui: ramais, derivações, descidas, retorno
    - Aplica-se fator de 1.2 (20%) para reserves, perdas e adaptações

    Fórmula:
    metros = (potencia_total_va / fator_conversao) × fator_seguranca

    Onde:
    - fator_conversao = 15 (média: 1m de eletroduto para cada 15VA)
    - fator_seguranca = 1.2 (20% para reservas)

    Distribuição típica:
    - 60% Eletroduto 3/4" (DN 25) - circuitos terminais
    - 30% Eletroduto 1/2" (DN 20) - iluminação
    - 10% Outros (DN 32, 40, 50) - alimentações principais
    """
    pot_terreo = sum(
        int(re.sub(r"\D", "", str(c.get("potencia_va", 0))))
        for c in quadro["terreo"]["circuitos"]
        if c.get("potencia_va")
    )
    pot_superior = sum(
        int(re.sub(r"\D", "", str(c.get("potencia_va", 0))))
        for c in quadro["superior"]["circuitos"]
        if c.get("potencia_va")
    )

    fator_conversao = 15  # 1m de eletroduto para cada 15VA
    fator_seguranca = 1.2  # +20% para reserves

    m_terreo = int((pot_terreo / fator_conversao) * fator_seguranca)
    m_superior = int((pot_superior / fator_conversao) * fator_seguranca)

    return {
        "terreo": {
            "potencia_va": pot_terreo,
            "dn25": int(m_terreo * 0.6),
            "dn20": int(m_terreo * 0.3),
            "outros": int(m_terreo * 0.1),
            "total": m_terreo,
        },
        "superior": {
            "potencia_va": pot_superior,
            "dn25": int(m_superior * 0.6),
            "dn20": int(m_superior * 0.3),
            "outros": int(m_superior * 0.1),
            "total": m_superior,
        },
    }


def estimar_fios(eletrodutos):
    """Estima fios/cabos baseado em eletrodutos"""
    total = eletrodutos["terreo"]["total"] + eletrodutos["superior"]["total"]

    return {
        "fio_1_5": int(total * 0.15 * 2),  # Iluminação
        "fio_2_5": int(total * 0.45 * 3),  # Tomadas
        "fio_4": int(total * 0.25 * 3),  # Circuitos robustos
        "fio_6": int(total * 0.15 * 3),  # Alimentação
    }


def gerar_pdf_anotado(dados_paginas, simbolos, output_path):
    """Gera PDF com anotações visuais"""

    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4
    y = height - 0.5 * inch

    # Página de título
    c.setFont("Helvetica-Bold", 24)
    c.drawString(1 * inch, y, "RELATÓRIO DE ANÁLISE - PROJETO ELÉTRICO")
    y -= 0.5 * inch

    c.setFont("Helvetica", 12)
    c.drawString(1 * inch, y, f"Data: {datetime.now().strftime('%d/%m/%Y')}")
    y -= 0.3 * inch
    c.drawString(1 * inch, y, f"Projeto: UFCA - Bloco O")
    y -= 0.8 * inch

    # Sumário de símbolos detectados
    c.setFont("Helvetica-Bold", 16)
    c.drawString(1 * inch, y, "SÍMBOLOS DETECTADOS NO PROJETO")
    y -= 0.4 * inch

    c.setFont("Helvetica", 10)
    for chave, info in simbolos.items():
        if info["quantidade"] > 0:
            c.setFillColor(HexColor(info["cor"]))
            c.rect(1 * inch, y - 0.15 * inch, 0.2 * inch, 0.2 * inch, fill=1)
            c.setFillColor(HexColor("#000000"))
            c.drawString(
                1.3 * inch,
                y - 0.1 * inch,
                f"{info['descricao']} ({info['categoria']}): {info['quantidade']} unidades",
            )
            y -= 0.25 * inch
            if y < 1 * inch:
                c.showPage()
                y = height - 0.5 * inch

    y -= 0.5 * inch
    c.setFont("Helvetica-Bold", 14)
    c.drawString(1 * inch, y, "LEGENDA DE CORES")
    y -= 0.3 * inch

    cores = [
        ("#FF6B6B", "Tomadas"),
        ("#4ECDC4", "Interruptores"),
        ("#FFE66D", "Iluminação"),
        ("#95E1D3", "Quadros"),
        ("#A8E6CF", "Caixas"),
    ]

    c.setFont("Helvetica", 10)
    for cor, desc in cores:
        c.setFillColor(HexColor(cor))
        c.rect(1 * inch, y - 0.15 * inch, 0.2 * inch, 0.2 * inch, fill=1)
        c.setFillColor(HexColor("#000000"))
        c.drawString(1.3 * inch, y - 0.1 * inch, desc)
        y -= 0.25 * inch

    c.showPage()
    y = height - 0.5 * inch

    # Extrair texto das plantas térreo e superior
    for dados in dados_paginas[:4]:  # Primeiras 4 páginas (plantas)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(1 * inch, y, f"Página {dados['pagina']} - Texto Extraído")
        y -= 0.4 * inch

        texto = dados.get("texto", "")
        if texto:
            # Limitar texto
            linhas = texto.split("\n")[:50]
            c.setFont("Helvetica", 8)
            for linha in linhas:
                if len(linha) > 80:
                    linha = linha[:80] + "..."
                c.drawString(1 * inch, y, linha)
                y -= 0.12 * inch
                if y < 1 * inch:
                    c.showPage()
                    y = height - 0.5 * inch

        y -= 0.3 * inch
        if y < 2 * inch:
            c.showPage()
            y = height - 0.5 * inch

    c.save()
    print(f"  PDF anotado salvo em: {output_path}")


def gerar_relatorio(quadro, simbolos, eletrodutos, fios, output_path):
    """Gera relatório detalhado"""

    md = []
    md.append("# RELATÓRIO DE ESTIMATIVA DE QUANTITATIVOS - PROJETO ELÉTRICO\n")
    md.append(f"**Data:** {datetime.now().strftime('%d/%m/%Y')}\n")
    md.append(f"**Projeto:** Universidade Federal do Cariri - UFCA (Bloco O)\n")
    md.append("---\n")

    md.append("## 1. RESUMO DO PROJETO\n")
    md.append(
        "| Pavimento | Circuitos | Pot. Iluminação (VA) | Pot. Tomadas (VA) | Pot. Total (VA) |\n"
    )
    md.append(
        "|-----------|-----------|---------------------|-------------------|----------------|\n"
    )

    pot_total_terreo = quadro["terreo"]["iluminacao"] + quadro["terreo"]["tomadas"]
    pot_total_superior = (
        quadro["superior"]["iluminacao"] + quadro["superior"]["tomadas"]
    )

    md.append(
        f"| Térreo | {len(quadro['terreo']['circuitos'])} | {quadro['terreo']['iluminacao']:.0f} | {quadro['terreo']['tomadas']:.0f} | {pot_total_terreo:.0f} |\n"
    )
    md.append(
        f"| Superior | {len(quadro['superior']['circuitos'])} | {quadro['superior']['iluminacao']:.0f} | {quadro['superior']['tomadas']:.0f} | {pot_total_superior:.0f} |\n"
    )
    md.append(
        f"| **Total** | **{len(quadro['terreo']['circuitos']) + len(quadro['superior']['circuitos'])}** | **{quadro['terreo']['iluminacao'] + quadro['superior']['iluminacao']:.0f}** | **{quadro['terreo']['tomadas'] + quadro['superior']['tomadas']:.0f}** | **{(pot_total_terreo + pot_total_superior):.0f}** |\n"
    )

    md.append("\n---\n")
    md.append("## 2. SÍMBOLOS DETECTADOS NO PROJETO\n")
    md.append(
        "> Os símbolos foram detectados automaticamente via extração de texto das páginas do PDF.\n"
    )

    md.append("| Categoria | Símbolo | Quantidade | Páginas |\n")
    md.append("|-----------|---------|------------|----------|\n")

    for chave, info in simbolos.items():
        if info["quantidade"] > 0:
            paginas = set(info["paginas"])
            md.append(
                f"| {info['categoria']} | {info['descricao']} | **{info['quantidade']}** | {sorted(paginas)} |\n"
            )

    md.append("\n---\n")
    md.append("## 3. METODOLOGIA DE ESTIMATIVA DE ELETRODUTOS\n")
    md.append("### 3.1 Fórmula de Cálculo\n")
    md.append("```\n")
    md.append("metros = (potencia_total_va / 15) × 1.2\n")
    md.append("```\n")
    md.append("- **15**: Fator de conversão (1m de eletroduto para cada 15VA)\n")
    md.append(
        "- **1.2**: Fator de segurança (20% para reserves, perdas e adaptações)\n"
    )
    md.append("\n### 3.2 Distribuição Típica\n")
    md.append("| Bitola | Percentual | Uso |\n")
    md.append("|--------|------------|-----|\n")
    md.append('| DN 25 (3/4") | 60% | Circuitos terminais |\n')
    md.append('| DN 20 (1/2") | 30% | Iluminação |\n')
    md.append("| DN 32+ | 10% | Alimentações principais |\n")

    md.append("\n---\n")
    md.append("## 4. ESTIMATIVA DE ELETRODUTOS\n")
    md.append("### 4.1 Térreo\n")
    md.append(f"| Tipo | Quantidade |\n")
    md.append(f"|------|------------|\n")
    md.append(f'| Eletroduto DN 25 (3/4") | {eletrodutos["terreo"]["dn25"]} m |\n')
    md.append(f'| Eletroduto DN 20 (1/2") | {eletrodutos["terreo"]["dn20"]} m |\n')
    md.append(f"| Outros DN | {eletrodutos['terreo']['outros']} m |\n")
    md.append(f"| **Total Térreo** | **{eletrodutos['terreo']['total']} m** |\n")

    md.append("\n### 4.2 Superior\n")
    md.append(f"| Tipo | Quantidade |\n")
    md.append(f"|------|------------|\n")
    md.append(f'| Eletroduto DN 25 (3/4") | {eletrodutos["superior"]["dn25"]} m |\n')
    md.append(f'| Eletroduto DN 20 (1/2") | {eletrodutos["superior"]["dn20"]} m |\n')
    md.append(f"| Outros DN | {eletrodutos['superior']['outros']} m |\n")
    md.append(f"| **Total Superior** | **{eletrodutos['superior']['total']} m** |\n")

    md.append("\n### 4.3 Total Geral\n")
    total_geral = eletrodutos["terreo"]["total"] + eletrodutos["superior"]["total"]
    md.append(f"**{total_geral} metros** de eletrodutos estimados\n")

    md.append("\n---\n")
    md.append("## 5. ESTIMATIVA DE FIOS E CABOS\n")
    md.append(
        "> Baseado no comprimento total de eletrodutos × 2-3 condutores por circuito\n"
    )
    md.append(f"| Bitola | Quantidade |\n")
    md.append(f"|--------|------------|\n")
    md.append(f"| 1,5 mm² | {fios['fio_1_5']} m |\n")
    md.append(f"| 2,5 mm² | {fios['fio_2_5']} m |\n")
    md.append(f"| 4 mm² | {fios['fio_4']} m |\n")
    md.append(f"| 6 mm² | {fios['fio_6']} m |\n")

    md.append("\n---\n")
    md.append("## 6. OBSERVAÇÕES\n")
    md.append("1. Os valores são **estimativas baseadas em regras empíricas**.\n")
    md.append("2. Recomenda-se **validação manual** em planta para precisão.\n")
    md.append("3. Adicionar **10-20% de margem** para perdas, emendas e adaptações.\n")
    md.append(
        "4. Usar arquivo `quantitativos_verificar.md` para levantamento detalhado.\n"
    )
    md.append(
        f"\n---\n*Relatório gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}*\n"
    )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    return output_path


def main():
    print("\n" + "=" * 60)
    print("ESTIMATIVA DE QUANTITATIVOS - PROJETO ELÉTRICO UFCA")
    print("=" * 60 + "\n")

    # 1. Extrair textos e tabelas
    print("[1/5] Extraindo dados do PDF...")
    dados_paginas = extrair_textos_e_tabelas(FILE_PDF)

    # 2. Extrair quadro de cargas
    print("[2/5] Processando quadro de cargas...")
    quadro = extrair_quadro_cargas(FILE_PDF)
    print(
        f"       Térreo: {len(quadro['terreo']['circuitos'])} circuitos, {quadro['terreo']['iluminacao'] + quadro['terreo']['tomadas']:.0f} VA"
    )
    print(
        f"       Superior: {len(quadro['superior']['circuitos'])} circuitos, {quadro['superior']['iluminacao'] + quadro['superior']['tomadas']:.0f} VA"
    )

    # 3. Detectar símbolos
    print("[3/5] Detectando símbolos...")
    simbolos = detectar_simbolos(dados_paginas)
    for chave, info in simbolos.items():
        if info["quantidade"] > 0:
            print(f"       {info['descricao']}: {info['quantidade']}")

    # 4. Estimar eletrodutos
    print("[4/5] Estimando eletrodutos...")
    eletrodutos = estimar_eletrodutos(quadro)
    print(f"       Térreo: {eletrodutos['terreo']['total']} m")
    print(f"       Superior: {eletrodutos['superior']['total']} m")

    # 5. Estimar fios
    fios = estimar_fios(eletrodutos)
    print(f"       Fios 2,5mm: {fios['fio_2_5']} m")

    # 6. Gerar relatório
    print("[5/5] Gerando arquivos...")
    md_path = os.path.join(OUTPUT_DIR, "estimativa_detalhada.md")
    gerar_relatorio(quadro, simbolos, eletrodutos, fios, md_path)

    # 7. Gerar PDF anotado
    pdf_anotado_path = os.path.join(OUTPUT_DIR, "projeto_anotado.pdf")
    gerar_pdf_anotado(dados_paginas, simbolos, pdf_anotado_path)

    # 8. Gerar planilha Excel
    xlsx_path = os.path.join(OUTPUT_DIR, "estimativa.xlsx")
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        pd.DataFrame(
            [
                {
                    "Pavimento": "Térreo",
                    "Circuitos": len(quadro["terreo"]["circuitos"]),
                    "Pot. Ilum (VA)": quadro["terreo"]["iluminacao"],
                    "Pot. Tomadas (VA)": quadro["terreo"]["tomadas"],
                    "Eletroduto DN25 (m)": eletrodutos["terreo"]["dn25"],
                    "Eletroduto DN20 (m)": eletrodutos["terreo"]["dn20"],
                    "Total (m)": eletrodutos["terreo"]["total"],
                }
            ]
        ).to_excel(writer, sheet_name="Térreo", index=False)

        pd.DataFrame(
            [
                {
                    "Pavimento": "Superior",
                    "Circuitos": len(quadro["superior"]["circuitos"]),
                    "Pot. Ilum (VA)": quadro["superior"]["iluminacao"],
                    "Pot. Tomadas (VA)": quadro["superior"]["tomadas"],
                    "Eletroduto DN25 (m)": eletrodutos["superior"]["dn25"],
                    "Eletroduto DN20 (m)": eletrodutos["superior"]["dn20"],
                    "Total (m)": eletrodutos["superior"]["total"],
                }
            ]
        ).to_excel(writer, sheet_name="Superior", index=False)

        pd.DataFrame(
            [
                {
                    "Símbolo": info["descricao"],
                    "Categoria": info["categoria"],
                    "Quantidade": info["quantidade"],
                }
                for chave, info in simbolos.items()
                if info["quantidade"] > 0
            ]
        ).to_excel(writer, sheet_name="Símbolos", index=False)

    print("\n" + "=" * 60)
    print("CONCLUÍDO!")
    print("=" * 60)
    print(f"\nArquivos gerados:")
    print(f"  - {md_path}")
    print(f"  - {pdf_anotado_path}")
    print(f"  - {xlsx_path}")


if __name__ == "__main__":
    main()
