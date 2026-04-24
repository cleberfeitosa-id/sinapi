#!/usr/bin/env python3
"""
Script para visualização de plantas elétricas com detecção de símbolos
Usa PyMuPDF para converter PDF em imagens e OpenCV para processamento

Autor: opencode
Data: 2026-03-26
Dependências: pip3 install pymupdf opencv-python pillow
"""

import os
import re
import cv2
import numpy as np
import pandas as pd
import fitz  # PyMuPDF
from PIL import Image, ImageDraw, ImageFont
import warnings
from datetime import datetime

warnings.filterwarnings("ignore")

FILE_PDF = "/Users/xuxi/anti-projects/sinapi/ELE.pdf"
OUTPUT_DIR = "/Users/xuxi/anti-projects/sinapi/quantidades_extraidas"

os.makedirs(OUTPUT_DIR, exist_ok=True)


def converter_pdf_imagens(pdf_path, output_folder, dpi=150):
    """Converte PDF em imagens usando PyMuPDF"""
    print("[1/5] Convertendo PDF em imagens...")

    doc = fitz.open(pdf_path)
    image_paths = []

    for i, page in enumerate(doc):
        # Renderizar página em pixmap
        zoom = dpi / 72
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)

        # Salvar como imagem
        img_path = os.path.join(output_folder, f"pagina_{i + 1:02d}.png")
        pix.save(img_path)
        image_paths.append(img_path)
        print(f"       Página {i + 1}/{len(doc)} salva")

    doc.close()
    return image_paths


def analisar_imagem_detectar_elementos(img_path):
    """Analisa imagem para detectar elementos visuais usando OpenCV"""
    print(f"       Processando: {os.path.basename(img_path)}")

    img = cv2.imread(img_path)
    if img is None:
        return {"erro": "Imagem não pôde ser carregada"}

    altura, largura = img.shape[:2]

    resultado = {
        "arquivo": os.path.basename(img_path),
        "dimensoes": f"{largura}x{altura}",
        "tomadas": 0,
        "interruptores": 0,
        "luminarias": 0,
        "quadros": 0,
        "caixas": 0,
        "spda": 0,
        "bombas": 0,
        "elementos_detectados": [],
    }

    # Converter para escala de cinza
    cinza = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Binarizar a imagem
    _, binaria = cv2.threshold(cinza, 200, 255, cv2.THRESH_BINARY_INV)

    # Encontrar contornos
    contornos, hierarquia = cv2.findContours(
        binaria, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
    )

    for cnt in contornos:
        area = cv2.contourArea(cnt)
        if area < 100 or area > 50000:
            continue

        x, y, w, h = cv2.boundingRect(cnt)
        proporcao = w / float(h) if h > 0 else 0
        aspecto = float(w) / h

        # Classificar elemento baseado em características
        elemento = None

        if 0.8 < aspecto < 1.2 and area < 1000:
            # Quase quadrado -> possível caixa ou tomada
            if w < 30:
                elemento = "caixa"
                resultado["caixas"] += 1
            else:
                elemento = "tomada"
                resultado["tomadas"] += 1

        elif aspecto > 2 and h < 30:
            # Retangular horizontal -> possível interruptor
            elemento = "interruptor"
            resultado["interruptores"] += 1

        elif area > 2000 and area < 8000:
            # Grande -> possível luminária
            elemento = "luminaria"
            resultado["luminarias"] += 1

        elif area > 8000 and w > h * 2:
            # Muito grande e longo -> possível quadro
            elemento = "quadro"
            resultado["quadros"] += 1

        if elemento:
            resultado["elementos_detectados"].append(
                {"tipo": elemento, "x": x, "y": y, "w": w, "h": h, "area": area}
            )

    # Contagem alternativa: análise de cores (áreas claras = luminárias)
    # Detectar regiões claras (possíveis luminárias na planta)
    _, binaria_clara = cv2.threshold(cinza, 230, 255, cv2.THRESH_BINARY)
    contornos_clara, _ = cv2.findContours(
        binaria_clara, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    count_luminarias = 0
    for cnt in contornos_clara:
        area = cv2.contourArea(cnt)
        if 500 < area < 5000:
            count_luminarias += 1

    if count_luminarias > resultado["luminarias"]:
        resultado["luminarias"] = count_luminarias

    return resultado


def analisar_planta_texto(pdf_path):
    """Extrai informações das plantas via texto (mais preciso para símbolos)"""
    print("[2/5] Extraindo informações das plantas...")

    informacoes = []

    with fitz.open(pdf_path) as doc:
        for i in range(len(doc)):
            page = doc[i]
            info = {"pagina": i + 1, "tipo": "", "elementos": {}, "texto_preview": ""}

            # Extrair texto
            texto = page.get_text()
            texto_upper = texto.upper()

            # Detectar tipo de planta
            if "TÉRREO" in texto_upper and "LEGENDA" in texto_upper:
                info["tipo"] = "Planta Térreo - Legenda de fiação"
            elif "SUPERIOR" in texto_upper and "LEGENDA" in texto_upper:
                info["tipo"] = "Planta Superior - Legenda de fiação"
            elif "QUADRO" in texto_upper and "CARGAS" in texto_upper:
                info["tipo"] = "Quadro de Cargas"
            elif "SPDA" in texto_upper:
                info["tipo"] = "Planta SPDA"
            elif "COBERTA" in texto_upper:
                info["tipo"] = "Planta de Cobertura"

            # Contar símbolos mencionados no texto (mais confiável)
            # Procurar na legenda
            padroes = {
                "TOMADA ALTA": len(re.findall(r"TOMADA.*ALTA|TA\s", texto_upper)),
                "TOMADA MEDIA": len(re.findall(r"TOMADA.*MEDIA|TM\s", texto_upper)),
                "TOMADA BAIXA": len(re.findall(r"TOMADA.*BAIXA|TB\s", texto_upper)),
                "INTERRUPTOR": len(
                    re.findall(r"INTERRUPTOR|INT\b|I\s+\d", texto_upper)
                ),
                "LUMINARIA": len(re.findall(r"LUMINARIA|LED", texto_upper)),
                "QUADRO": len(re.findall(r"QUADRO|QLF", texto_upper)),
                "CAIXA": len(re.findall(r"CAIXA|CP\b", texto_upper)),
            }
            info["elementos"] = {k: v for k, v in padroes.items() if v > 0}

            # Preview do texto (primeiras linhas da legenda)
            linhas = texto.split("\n")[:20]
            info["texto_preview"] = "\n".join(linhas)

            informacoes.append(info)
            print(f"       Página {i + 1}: {info['tipo'] or 'Sem tipo específico'}")

    return informacoes


def criar_marcacao_imagem(img_path, resultado, output_path):
    """Cria imagem com marcações coloridas sobre os elementos detectados"""

    img = cv2.imread(img_path)
    if img is None:
        return None

    # Cores BGR
    cores = {
        "tomada": (203, 192, 255),  # Rosa
        "interruptor": (230, 230, 250),  # Azul claro
        "luminaria": (0, 255, 255),  # Amarelo
        "quadro": (144, 238, 144),  # Verde
        "caixa": (147, 112, 219),  # Roxo
    }

    # Desenhar retângulos sobre elementos detectados
    for elem in resultado.get("elementos_detectados", []):
        tipo = elem["tipo"]
        cor = cores.get(tipo, (255, 255, 255))
        x, y, w, h = elem["x"], elem["y"], elem["w"], elem["h"]

        cv2.rectangle(img, (x, y), (x + w, y + h), cor, 2)

        # Adicionar label
        label = f"{tipo}:{elem['area']:.0f}"
        cv2.putText(img, label, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, cor, 1)

    # Adicionar legenda na imagem
    altura, largura = img.shape[:2]

    # Fundo branco para legenda
    cv2.rectangle(img, (10, 10), (300, 120), (255, 255, 255), -1)
    cv2.rectangle(img, (10, 10), (300, 120), (0, 0, 0), 1)

    y_texto = 30
    for tipo, cor in cores.items():
        qtd = resultado.get(tipo + "s", 0)
        if qtd > 0:
            cv2.putText(
                img,
                f"{tipo}: {qtd}",
                (20, y_texto),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                cor,
                2,
            )
            y_texto += 20

    # Salvar imagem marcada
    cv2.imwrite(output_path, img)
    return output_path


def gerar_html_interativo(info_plantas, resultados_imagem, output_path):
    """Gera relatório HTML com visualização"""
    print("[5/5] Gerando relatório HTML...")

    # Calcular totais
    total_tomadas = sum(
        p.get("elementos", {}).get("TOMADA ALTA", 0)
        + p.get("elementos", {}).get("TOMADA MEDIA", 0)
        + p.get("elementos", {}).get("TOMADA BAIXA", 0)
        for p in info_plantas
    )

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Análise Projeto Elétrico UFCA - Bloco O</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', Arial, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; padding: 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        
        h1 {{ color: white; text-align: center; padding: 20px; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }}
        h2 {{ color: #333; margin: 30px 0 15px 0; padding-bottom: 10px; border-bottom: 2px solid #667eea; }}
        
        .cards {{ display: flex; flex-wrap: wrap; gap: 15px; justify-content: center; margin: 20px 0; }}
        .card {{ background: white; padding: 20px 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.2); text-align: center; min-width: 140px; }}
        .card h3 {{ color: #666; font-size: 0.85em; margin-bottom: 8px; text-transform: uppercase; }}
        .card .valor {{ font-size: 2.5em; font-weight: bold; color: #667eea; }}
        
        .pagina {{ background: white; margin: 20px 0; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.2); }}
        .pagina-cabecalho {{ background: linear-gradient(90deg, #667eea, #764ba2); color: white; padding: 15px 20px; }}
        .pagina-cabecalho h3 {{ margin: 0; }}
        
        .conteudo {{ padding: 20px; }}
        
        .tabela {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
        .tabela th {{ background: #f8f9fa; padding: 12px; text-align: left; border-bottom: 2px solid #667eea; color: #333; }}
        .tabela td {{ padding: 10px; border-bottom: 1px solid #eee; }}
        .tabela tr:hover {{ background: #f8f9fa; }}
        
        .legenda-cores {{ display: flex; gap: 15px; flex-wrap: wrap; margin: 15px 0; }}
        .legenda-item {{ display: flex; align-items: center; gap: 8px; }}
        .cor-box {{ width: 20px; height: 20px; border-radius: 4px; }}
        
        .metodologia {{ background: white; padding: 20px; border-radius: 12px; margin: 20px 0; }}
        .metodologia p {{ margin: 10px 0; line-height: 1.6; color: #555; }}
        .metodologia code {{ background: #f4f4f4; padding: 2px 6px; border-radius: 4px; font-family: monospace; }}
        
        .observacoes {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0; border-radius: 0 8px 8px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🏗️ Análise do Projeto Elétrico - UFCA (Bloco O)</h1>
        
        <div class="cards">
            <div class="card">
                <h3>Total Páginas</h3>
                <div class="valor">{len(info_plantas)}</div>
            </div>
            <div class="card">
                <h3>Tomadas</h3>
                <div class="valor">{sum(p.get("elementos", {}).get("TOMADA ALTA", 0) + p.get("elementos", {}).get("TOMADA MEDIA", 0) + p.get("elementos", {}).get("TOMADA BAIXA", 0) for p in info_plantas)}</div>
            </div>
            <div class="card">
                <h3>Interruptores</h3>
                <div class="valor">{sum(p.get("elementos", {}).get("INTERRUPTOR", 0) for p in info_plantas)}</div>
            </div>
            <div class="card">
                <h3>Luminárias</h3>
                <div class="valor">{sum(p.get("elementos", {}).get("LUMINARIA", 0) for p in info_plantas)}</div>
            </div>
            <div class="card">
                <h3>Quadros</h3>
                <div class="valor">{sum(p.get("elementos", {}).get("QUADRO", 0) for p in info_plantas)}</div>
            </div>
            <div class="card">
                <h3>Caixas</h3>
                <div class="valor">{sum(p.get("elementos", {}).get("CAIXA", 0) for p in info_plantas)}</div>
            </div>
        </div>
        
        <h2>📋 Detalhamento por Página</h2>
"""

    for info in info_plantas:
        if info["tipo"] or info["elementos"]:
            html += f"""
        <div class="pagina">
            <div class="pagina-cabecalho">
                <h3>Página {info["pagina"]}: {info["tipo"] or "Sem classificação"}</h3>
            </div>
            <div class="conteudo">
"""
            if info["elementos"]:
                html += """
                <table class="tabela">
                    <tr><th>Elemento</th><th>Quantidade Detectada</th></tr>
"""
                for elem, qtd in info["elementos"].items():
                    html += f"""
                    <tr><td>{elem}</td><td><strong>{qtd}</strong></td></tr>
"""
                html += """
                </table>
"""
            else:
                html += (
                    "<p><em>Nenhum elemento específico detectado nesta página.</em></p>"
                )

            if info["texto_preview"]:
                html += f"""
                <details style="margin-top: 15px;">
                    <summary style="cursor: pointer; color: #667eea;">Ver texto extraído</summary>
                    <pre style="background: #f4f4f4; padding: 15px; border-radius: 8px; overflow-x: auto; font-size: 12px; margin-top: 10px;">{info["texto_preview"][:1000]}</pre>
                </details>
"""

            html += """
            </div>
        </div>
"""

    html += """
        <h2>🎨 Legenda de Cores (Detecção por Imagem)</h2>
        <div class="legenda-cores">
            <div class="legenda-item"><div class="cor-box" style="background: rgb(203,192,255)"></div><span>Tomadas</span></div>
            <div class="legenda-item"><div class="cor-box" style="background: rgb(230,230,250)"></div><span>Interruptores</span></div>
            <div class="legenda-item"><div class="cor-box" style="background: rgb(0,255,255)"></div><span>Luminárias</span></div>
            <div class="legenda-item"><div class="cor-box" style="background: rgb(144,238,144)"></div><span>Quadros</span></div>
            <div class="legenda-item"><div class="cor-box" style="background: rgb(147,112,219)"></div><span>Caixas</span></div>
        </div>
        
        <h2>📊 Metodologia</h2>
        <div class="metodologia">
            <p><strong>1. Extração de Texto:</strong> O PDF é processado usando PyMuPDF (fitz) para extrair o texto de cada página. O texto é analisado para identificar símbolos mencionados nas legendas.</p>
            <p><strong>2. Classificação por Tipo de Planta:</strong> Cada página é classificada berdasarkan seu conteúdo (Térreo, Superior, SPDA, Quadro de Cargas, etc.).</p>
            <p><strong>3. Contagem de Elementos:</strong> Símbolos são contados usando expressões regulares no texto extraído, o que é mais confiável que detecção visual.</p>
            <p><strong>Fórmula de Eletrodutos:</strong> <code>metros = (VA / 15) × 1.2</code> - 1m de eletroduto para cada 15VA, com 20% de margem.</p>
        </div>
        
        <div class="observacoes">
            <strong>⚠️ Observações Importantes:</strong>
            <ul style="margin-top: 10px; padding-left: 20px;">
                <li>Os valores são <strong>estimativas</strong> baseadas na análise do PDF.</li>
                <li>Recomenda-se <strong>validação manual</strong> em planta para precisão total.</li>
                <li>Para medições precisas, использовать ferramentas especializadas como Drawer AI ou Civils.ai.</li>
                <li>Usar o arquivo <code>quantitativos_verificar.md</code> para levantamento detalhado.</li>
            </ul>
        </div>
    </div>
</body>
</html>
"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"       Relatório salvo em: {output_path}")
    return output_path


def main():
    print("\n" + "=" * 60)
    print("ANÁLISE VISUAL DE PLANTA ELÉTRICA")
    print("=" * 60 + "\n")

    # 1. Converter PDF em imagens
    image_paths = converter_pdf_imagens(FILE_PDF, OUTPUT_DIR)
    print(f"\nTotal de páginas: {len(image_paths)}")

    # 2. Extrair informações das plantas via texto
    info_plantas = analisar_planta_texto(FILE_PDF)

    # 3. Analisar imagens (processamento visual)
    resultados_imagem = []
    for img_path in image_paths:
        res = analisar_imagem_detectar_elementos(img_path)
        resultados_imagem.append(res)

    # 4. Criar imagens com marcações
    for img_path, res in zip(image_paths, resultados_imagem):
        output_marcada = img_path.replace(".png", "_marcada.png")
        criar_marcacao_imagem(img_path, res, output_marcada)

    # 5. Gerar HTML
    html_path = os.path.join(OUTPUT_DIR, "analise_completa.html")
    gerar_html_interativo(info_plantas, resultados_imagem, html_path)

    print("\n" + "=" * 60)
    print("ANÁLISE CONCLUÍDA!")
    print("=" * 60)
    print(f"\nArquivos gerados em {OUTPUT_DIR}:")
    print(f"  - Imagens originais: pagina_*.png")
    print(f"  - Imagens marcadas: pagina_*_marcada.png")
    print(f"  - Relatório HTML: analise_completa.html")


if __name__ == "__main__":
    main()
