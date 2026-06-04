#!/usr/bin/env python3
"""
Ferramenta Interativa de Contagem de Elementos em Plantas
Versão Web com Flask - Interface no navegador

Uso: python3 contar_elementos.py [--port 5000] [arquivo]

Autor: opencode
Data: 2026-03-26
"""

import os
import sys
import argparse
import cv2
import numpy as np
from pathlib import Path
import base64
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

from flask import Flask, render_template_string, request, jsonify, json
from pdf2image import convert_from_path

app = Flask(__name__)


@app.template_filter("sanitize")
def sanitize_filter(s):
    return s.replace(" ", "_").replace("-", "_")


@app.template_filter("sanitize_id")
def sanitize_id_filter(s):
    import re

    return re.sub(r"[^a-zA-Z0-9_]", "_", s)


IMG_PATH = None
PAGINA = 1
DPI = 150
img_global = None
nome_base = ""
marcacoes = []
tipo_atual = "tomada_bx"
offset_x = 0
offset_y = 0
zoom = 5.0  # Começa com zoom máximo

predefinicoes = {
    "Elétrica": [
        {"id": "tomada_bx", "nome": "Tomada Baixa"},
        {"id": "tomada_md", "nome": "Tomada Média"},
        {"id": "tomada_alt", "nome": "Tomada Alta"},
        {"id": "interruptor", "nome": "Interruptor"},
        {"id": "interruptor_tomada", "nome": "Interruptor + Tomada"},
        {"id": "luminaria", "nome": "Luminária"},
        {"id": "luminaria_embutir", "nome": "Luminária Embutir"},
        {"id": "refletor", "nome": "Refletor"},
        {"id": "quadro", "nome": "Quadro Elétrico"},
        {"id": "caixa_passagem", "nome": "Caixa de Passagem"},
    ],
    "SPDA": [
        {"id": "spda_captador", "nome": "Captador"},
        {"id": "spda_haste", "nome": "Haste"},
        {"id": "spda_cabo", "nome": "Cabo"},
        {"id": "spda_mao_franca", "nome": "Mão Francesa"},
        {"id": "spda_terminal", "nome": "Terminal"},
        {"id": "spda_aterramento", "nome": "Aterramento"},
        {"id": "spda_primerio", "nome": "Primerio"},
        {"id": "spda_isolador", "nome": "Isolador"},
    ],
    "Bombas Elétricas": [
        {"id": "bomba", "nome": "Bomba"},
        {"id": "quadro_comando", "nome": "Quadro de Comando"},
        {"id": "ventilador", "nome": "Ventilador"},
        {"id": "reservatorio", "nome": "Reservatório"},
    ],
    "Junções": [
        {"id": "curva_90_pvc", "nome": "Curva 90° PVC"},
        {"id": "joelho_90_pvc", "nome": "Joelho 90° PVC"},
        {"id": "curva_45_pvc", "nome": "Curva 45° PVC"},
        {"id": "joelho_45_pvc", "nome": "Joelho 45° PVC"},
        {"id": "tee_pvc", "nome": "Tê PVC"},
        {"id": "reducao_pvc", "nome": "Redução PVC"},
        {"id": "luva_pvc", "nome": "Luva PVC"},
        {"id": "registro", "nome": "Registro"},
        {"id": "caixa_inspecao", "nome": "Caixa de Inspeção"},
        {"id": "ralo", "nome": "Ralo"},
    ],
}

cores_tipo = {
    "tomada_bx": "#cbb0ff",
    "tomada_md": "#b482f0",
    "tomada_alt": "#9664dc",
    "interruptor": "#e6e6fa",
    "interruptor_tomada": "#ffb6c1",
    "luminaria": "#00ffff",
    "luminaria_embutir": "#00c8c8",
    "refletor": "#ffff00",
    "quadro": "#90ee90",
    "caixa_passagem": "#9370db",
    "spda_captador": "#ff0000",
    "spda_haste": "#c80000",
    "spda_cabo": "#0000c8",
    "spda_mao_franca": "#0064ff",
    "spda_terminal": "#ff00ff",
    "spda_aterramento": "#8b4513",
    "spda_primerio": "#ffa500",
    "spda_isolador": "#808000",
    "bomba": "#ffa500",
    "quadro_comando": "#ff6347",
    "ventilador": "#64c864",
    "reservatorio": "#009696",
    "curva_90_pvc": "#00ced1",
    "joelho_90_pvc": "#20b2aa",
    "curva_45_pvc": "#48d1cc",
    "joelho_45_pvc": "#40e0d0",
    "tee_pvc": "#5f9ea0",
    "reducao_pvc": "#778899",
    "luva_pvc": "#8fbc8f",
    "registro": "#cd853f",
    "caixa_inspecao": "#dda0dd",
    "ralo": "#b0c4de",
    "outro": "#ffffff",
}

config_marker = {
    "raio": 35,
    "espessura": 3,
    "fonte_escala": 1.2,
    "fonte_grossura": 3,
    "cor_borda": "#000000",
    "cor_texto": "#ffffff",
    "zoom_inicial": 5.0,
    "legenda_posicao": "baixo-dir",
    "legenda_tamanho_fonte": 0.8,
    "legenda_cor_fundo": "#000000",
    "legenda_cor_texto": "#ffffff",
    "legenda_opacidade": 255,
}


def carregar_imagem(path, pagina, dpi):
    global img_global, nome_base
    path = Path(path)
    if path.suffix.lower() == ".pdf":
        pages = convert_from_path(
            str(path), dpi=dpi, first_page=pagina, last_page=pagina
        )
        if pages:
            pil_img = pages[0]
            img_global = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
            nome_base = f"pagina_{pagina}"
    else:
        img_global = cv2.imread(str(path))
        nome_base = path.stem

    return img_global


def adicionar_legenda(img, marcacoes, nomes_personalizados, config_legenda=None):
    if config_legenda is None:
        config_legenda = {}

    posicao = config_legenda.get("posicao", "baixo-dir")
    escala_legenda = config_legenda.get("tamanho_fonte", 0.8)
    opacidade = config_legenda.get("opacidade", 255)
    cor_fundo = config_legenda.get("cor_fundo", "#000000")
    cor_texto = config_legenda.get("cor_texto", "#ffffff")

    tipos_presentes = {}
    for _, _, _, tipo in marcacoes:
        if tipo not in tipos_presentes:
            nome = tipo
            for disc, itens in predefinicoes.items():
                for item in itens:
                    if item["id"] == tipo:
                        nome = nomes_personalizados.get(disc, {}).get(
                            tipo, item["nome"]
                        )
                        break
            tipos_presentes[tipo] = nome

    if not tipos_presentes:
        return img

    h, w = img.shape[:2]
    fonte = cv2.FONT_HERSHEY_DUPLEX
    grossura = 1
    padding = int(12 * escala_legenda)
    espaco_linha = int(24 * escala_legenda)
    raio_legenda = max(6, int(8 * escala_legenda))

    linhas = []
    for tipo, nome in tipos_presentes.items():
        cor = cores_tipo.get(tipo, "#ffffff")
        r = int(cor[1:3], 16)
        g = int(cor[3:5], 16)
        b = int(cor[5:7], 16)
        count = sum(1 for m in marcacoes if m[3] == tipo)
        texto = f"{nome}: {count}"
        linhas.append((texto, (r, g, b), cor))

    max_largura = 0
    max_altura = 0
    for texto, _, _ in linhas:
        (tw, th), _ = cv2.getTextSize(texto, fonte, escala_legenda, grossura)
        max_largura = max(max_largura, tw)
        max_altura = max(max_altura, th)

    largura_legenda = max_largura + raio_legenda * 2 + padding * 3 + 20
    altura_legenda = len(linhas) * espaco_linha + padding * 2

    fb = int(cor_fundo[1:3], 16)
    fg = int(cor_fundo[3:5], 16)
    fr = int(cor_fundo[5:7], 16)

    tb = int(cor_texto[1:3], 16)
    tg = int(cor_texto[3:5], 16)
    tr = int(cor_texto[5:7], 16)

    if posicao == "baixo-dir":
        x_legenda = w - largura_legenda - 20
        y_legenda = h - altura_legenda - 20
    elif posicao == "baixo-esq":
        x_legenda = 20
        y_legenda = h - altura_legenda - 20
    elif posicao == "topo-dir":
        x_legenda = w - largura_legenda - 20
        y_legenda = 20
    elif posicao == "topo-esq":
        x_legenda = 20
        y_legenda = 20
    else:
        x_legenda = w - largura_legenda - 20
        y_legenda = h - altura_legenda - 20

    resultado = img.copy()

    if opacidade < 255:
        fundo_legenda = np.zeros((h, w, 3), dtype=np.uint8)
        cv2.rectangle(
            fundo_legenda,
            (x_legenda, y_legenda),
            (x_legenda + largura_legenda, y_legenda + altura_legenda),
            (fb, fg, fr),
            -1,
        )
        alpha = opacidade / 255.0
        for y in range(y_legenda, min(y_legenda + altura_legenda, h)):
            for x in range(x_legenda, min(x_legenda + largura_legenda, w)):
                resultado[y, x] = (
                    fundo_legenda[y, x] * alpha + resultado[y, x] * (1 - alpha)
                ).astype(np.uint8)
    else:
        cv2.rectangle(
            resultado,
            (x_legenda, y_legenda),
            (x_legenda + largura_legenda, y_legenda + altura_legenda),
            (fb, fg, fr),
            -1,
        )

    cv2.rectangle(
        resultado,
        (x_legenda, y_legenda),
        (x_legenda + largura_legenda, y_legenda + altura_legenda),
        (tb, tg, tr),
        1,
    )

    img_pil = Image.fromarray(cv2.cvtColor(resultado, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(img_pil)

    try:
        font_path = "/System/Library/Fonts/Helvetica.ttc"
        font = ImageFont.truetype(font_path, int(20 * escala_legenda))
    except:
        font = ImageFont.load_default()

    for i, (texto, (b, g, r), cor_hex) in enumerate(linhas):
        y = y_legenda + padding + espaco_linha * i + max_altura

        circle_x = x_legenda + padding + raio_legenda + 10
        circle_y = y - raio_legenda // 2

        draw.ellipse(
            [
                circle_x - raio_legenda,
                circle_y - raio_legenda,
                circle_x + raio_legenda,
                circle_y + raio_legenda,
            ],
            fill=(r, g, b),
            outline=(tb, tg, tr),
        )

        bbox = draw.textbbox((0, 0), texto, font=font)
        text_width = bbox[2] - bbox[0]
        text_x = circle_x + raio_legenda + 15
        text_y = y - (bbox[3] - bbox[1]) // 2

        draw.text(
            (text_x, text_y),
            texto,
            font=font,
            fill=(tb, tg, tr),
        )

    resultado = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)

    return resultado


def gerar_imagem_base64(img, zoom, off_x, off_y, marcacoes, cfg=None):
    if cfg is None:
        cfg = config_marker

    raio = cfg.get("raio", 35)
    espessura = cfg.get("espessura", 3)
    fonte_escala = cfg.get("fonte_escala", 1.2)
    fonte_grossura = cfg.get("fonte_grossura", 3)
    cor_borda = cfg.get("cor_borda", "#000000")
    cor_texto = cfg.get("cor_texto", "#ffffff")

    h, w = img.shape[:2]

    view_w = int(w / zoom)
    view_h = int(h / zoom)

    roi = img[off_y : min(off_y + view_h, h), off_x : min(off_x + view_w, w)]

    if roi.size > 0:
        disp = cv2.resize(roi, (int(roi.shape[1] * zoom), int(roi.shape[0] * zoom)))

        for x_orig, y_orig, num, tipo in marcacoes:
            x_disp = int((x_orig - off_x) * zoom)
            y_disp = int((y_orig - off_y) * zoom)

            if 0 <= x_disp < disp.shape[1] and 0 <= y_disp < disp.shape[0]:
                cor = cores_tipo.get(tipo, "#ffffff")
                b = int(cor[1:3], 16)
                g = int(cor[3:5], 16)
                r = int(cor[5:7], 16)

                rb = int(cor_borda[1:3], 16)
                gb = int(cor_borda[3:5], 16)
                rt = int(cor_borda[5:7], 16)

                tb = int(cor_texto[1:3], 16)
                tg = int(cor_texto[3:5], 16)
                tr = int(cor_texto[5:7], 16)

                cv2.circle(disp, (x_disp, y_disp), raio, (b, g, r), -1)
                cv2.circle(disp, (x_disp, y_disp), raio, (rb, gb, rt), espessura)

                texto = str(num)
                fonte = cv2.FONT_HERSHEY_SIMPLEX

                (tw, th), baseline = cv2.getTextSize(
                    texto, fonte, fonte_escala, fonte_grossura
                )
                cv2.putText(
                    disp,
                    texto,
                    (x_disp - tw // 2, y_disp + th // 2 + baseline),
                    fonte,
                    fonte_escala,
                    (0, 0, 0),
                    fonte_grossura + 2,
                    cv2.LINE_AA,
                )

                cv2.putText(
                    disp,
                    texto,
                    (x_disp - tw // 2, y_disp + th // 2 + baseline),
                    fonte,
                    fonte_escala,
                    (tb, tg, tr),
                    fonte_grossura,
                    cv2.LINE_AA,
                )
    else:
        # ROI vazia - criar imagem preta
        disp = np.zeros((max(1, view_h), max(1, view_w), 3), dtype=np.uint8)

    disp_rgb = cv2.cvtColor(disp, cv2.COLOR_BGR2RGB)

    _, buffer = cv2.imencode(".png", disp_rgb)
    img_base64 = base64.b64encode(buffer).decode()
    return f"data:image/png;base64,{img_base64}"


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Contador de Elementos - SINAPI</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Arial, sans-serif;
            background: #1e1e1e;
            color: #e0e0e0;
            display: flex;
            height: 100vh;
            overflow: hidden;
        }
        
        .sidebar {
            width: 320px;
            background: #252525;
            display: flex;
            flex-direction: column;
            border-right: 1px solid #333;
            overflow-y: auto;
        }
        
        .header {
            background: #0d7377;
            padding: 15px;
            text-align: center;
        }
        
        .header h1 {
            font-size: 1.3rem;
            color: white;
        }
        
        .section {
            padding: 15px;
            border-bottom: 1px solid #333;
        }
        
        .section h3 {
            color: #aaa;
            font-size: 0.85rem;
            margin-bottom: 10px;
            text-transform: uppercase;
        }
        
        .tabs {
            display: flex;
            background: #1e1e1e;
        }
        
        .tab {
            flex: 1;
            padding: 12px 5px;
            text-align: center;
            cursor: pointer;
            border-bottom: 3px solid transparent;
            font-size: 0.85rem;
            transition: all 0.3s;
        }
        
        .tab:hover {
            background: #2d2d2d;
        }
        
        .tab.active {
            border-bottom-color: #0d7377;
            color: #0d7377;
            background: #252525;
        }
        
        .element-list {
            display: flex;
            flex-direction: column;
            gap: 5px;
            max-height: 180px;
            overflow-y: auto;
        }
        
        .element-item {
            padding: 10px;
            background: #1e1e1e;
            border-radius: 5px;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 10px;
            transition: all 0.2s;
        }
        
        .element-item:hover {
            background: #333;
        }
        
        .element-item.selected {
            background: #0d7377;
        }
        
        .color-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            border: 1px solid white;
        }
        
        .edit-box {
            margin-top: 15px;
        }
        
        .edit-box input {
            width: 100%;
            padding: 10px;
            background: #1e1e1e;
            border: 1px solid #333;
            color: white;
            border-radius: 5px;
            margin-bottom: 10px;
        }
        
        .btn-group {
            display: flex;
            gap: 10px;
        }
        
        .btn {
            flex: 1;
            padding: 10px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-weight: bold;
            transition: all 0.2s;
        }
        
        .btn-apply {
            background: #0d7377;
            color: white;
        }
        
        .btn-apply:hover {
            background: #14a3a8;
        }
        
        .btn-reset {
            background: #8b0000;
            color: white;
        }
        
        .btn-reset:hover {
            background: #aa0000;
        }
        
        .info-panel {
            background: #1e1e1e;
            padding: 15px;
            border-radius: 5px;
            margin-top: 10px;
        }
        
        .info-row {
            display: flex;
            justify-content: space-between;
            margin-bottom: 8px;
            font-size: 0.9rem;
        }
        
        .info-label {
            color: #888;
        }
        
        .info-value {
            color: #0d7377;
            font-weight: bold;
        }
        
        .info-value.total {
            color: white;
        }
        
        .info-type-container {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .info-type-count {
            color: #ffa500;
            font-weight: bold;
            font-size: 0.85em;
        }
        
        .actions {
            display: flex;
            gap: 10px;
            margin-top: 15px;
        }
        
        .config-panel {
            background: #1e1e1e;
            padding: 10px;
            border-radius: 5px;
            margin-top: 10px;
        }
        
        .config-row {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 10px;
            font-size: 0.85rem;
        }
        
        .config-label {
            color: #888;
            min-width: 70px;
        }
        
        .config-row input[type="range"] {
            flex: 1;
            cursor: pointer;
        }
        
        .config-row input[type="color"] {
            width: 40px;
            height: 25px;
            border: none;
            cursor: pointer;
        }
        
        .config-row select {
            flex: 1;
            padding: 5px;
            background: #1e1e1e;
            border: 1px solid #333;
            color: white;
            border-radius: 3px;
            cursor: pointer;
        }
        
        .config-value {
            color: #0d7377;
            font-weight: bold;
            min-width: 30px;
        }
        
        .btn-save {
            flex: 1;
            background: #0d7377;
            color: white;
            padding: 12px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-weight: bold;
        }
        
        .btn-clear {
            flex: 1;
            background: #8b0000;
            color: white;
            padding: 12px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-weight: bold;
        }
        
        .btn-preview {
            flex: 1;
            background: #2196F3;
            color: white;
            padding: 12px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-weight: bold;
        }
        
        .btn-preview:hover {
            background: #1976D2;
        }
        
        .btn-back {
            flex: 1;
            background: #FF9800;
            color: white;
            padding: 12px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-weight: bold;
        }
        
        .btn-back:hover {
            background: #F57C00;
        }
        
        .main-area {
            flex: 1;
            display: flex;
            flex-direction: column;
            background: #111;
            position: relative;
        }
        
        .canvas-container {
            flex: 1;
            overflow: hidden;
            position: relative;
            cursor: crosshair;
        }
        
        #canvas {
            width: 100%;
            height: 100%;
            object-fit: contain;
        }
        
        .controls-bar {
            background: #252525;
            padding: 10px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-top: 1px solid #333;
        }
        
        .controls {
            display: flex;
            gap: 20px;
            color: #888;
            font-size: 0.85rem;
        }
        
        .controls kbd {
            background: #333;
            padding: 3px 8px;
            border-radius: 3px;
            color: #ccc;
        }
        
        .legend {
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
        }
        
        .legend-item {
            display: flex;
            align-items: center;
            gap: 5px;
            font-size: 0.8rem;
            color: #aaa;
        }
        
        .legend-color {
            width: 10px;
            height: 10px;
            border-radius: 50%;
        }
        
        .tab-content {
            display: none;
        }
        
        .tab-content.active {
            display: block;
        }
    </style>
</head>
<body>
    <div class="sidebar">
        <div class="header">
            <h1>📊 Contador de Elementos</h1>
        </div>
        
        <div class="section">
            <h3>Gerenciar Categorias</h3>
            <div class="edit-box">
                <input type="text" id="nova-categoria" placeholder="Nova categoria...">
                <div class="btn-group">
                    <button class="btn btn-apply" onclick="adicionarCategoria()">Adicionar</button>
                </div>
            </div>
            <div class="edit-box" style="margin-top: 10px;">
                <input type="text" id="editar-categoria" placeholder="Nome da categoria para editar...">
                <input type="text" id="novo-nome-categoria" placeholder="Novo nome...">
                <div class="btn-group">
                    <button class="btn btn-apply" onclick="renomearCategoria()">Renomear</button>
                    <button class="btn btn-reset" onclick="removerCategoria()">Remover</button>
                </div>
            </div>
        </div>
        
        <div class="tabs" id="tabs">
            {% for disciplina in predefinicoes.keys() %}
            <div class="tab" data-tab="{{ disciplina|sanitize_id }}">{{ disciplina }}</div>
            {% endfor %}
        </div>
        
        {% for disciplina, elementos in predefinicoes.items() %}
        <div class="tab-content" id="tab-{{ disciplina|sanitize_id }}">
            <div class="section">
                <h3>Selecione o elemento</h3>
                <div class="element-list" id="elements-{{ disciplina|sanitize_id }}">
                    {% for el in elementos %}
                    <div class="element-item" data-id="{{ el.id }}" data-name="{{ el.nome }}">
                        <div class="color-dot" style="background: {{ cores[el.id] }}"></div>
                        <span>{{ el.nome }}</span>
                    </div>
                    {% endfor %}
                </div>
                
                <div class="edit-box">
                    <input type="text" id="edit-name-{{ disciplina|sanitize_id }}" placeholder="Editar nome...">
                    <div class="btn-group">
                        <button class="btn btn-apply" onclick="applyEdit('{{ disciplina|sanitize_id }}')">Aplicar</button>
                        <button class="btn btn-reset" onclick="resetNames('{{ disciplina|sanitize_id }}')">Resetar</button>
                    </div>
                </div>
            </div>
        </div>
        {% endfor %}
        
        <div class="section">
            <h3>Informações</h3>
            <div class="info-panel">
                <div class="info-row">
                    <span class="info-label">Arquivo:</span>
                    <span class="info-value" id="info-file">{{ nome_base }}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Tipo:</span>
                    <div class="info-type-container">
                        <span class="info-value" id="info-type">Selecione...</span>
                        <span class="info-type-count" id="info-type-count">(0)</span>
                    </div>
                </div>
                <div class="info-row">
                    <span class="info-label">Total:</span>
                    <span class="info-value total" id="info-total">0</span>
                </div>
            </div>
        </div>
        
        <div class="section">
            <h3>Configurações do Marcador</h3>
            <div class="config-panel">
                <div class="config-row">
                    <span class="config-label">Raio:</span>
                    <input type="range" id="config-raio" min="10" max="100" value="{{ config.raio }}" onchange="atualizarConfig()">
                    <span class="config-value" id="val-raio">{{ config.raio }}</span>
                </div>
                <div class="config-row">
                    <span class="config-label">Espessura:</span>
                    <input type="range" id="config-espessura" min="1" max="10" value="{{ config.espessura }}" onchange="atualizarConfig()">
                    <span class="config-value" id="val-espessura">{{ config.espessura }}</span>
                </div>
                <div class="config-row">
                    <span class="config-label">Fonte:</span>
                    <input type="range" id="config-fonte" min="0.5" max="3" step="0.1" value="{{ config.fonte_escala }}" onchange="atualizarConfig()">
                    <span class="config-value" id="val-fonte">{{ config.fonte_escala }}</span>
                </div>
                <div class="config-row">
                    <span class="config-label">Cor texto:</span>
                    <input type="color" id="config-cor" value="{{ config.cor_texto }}" onchange="atualizarConfig()">
                </div>
                <div class="config-row">
                    <span class="config-label">Cor borda:</span>
                    <input type="color" id="config-cor-borda" value="{{ config.cor_borda }}" onchange="atualizarConfig()">
                </div>
            </div>
        </div>
        
        <div class="section">
            <h3>Gerar Visualização Final</h3>
            <div class="config-panel">
                <div class="config-row">
                    <span class="config-label">Posição:</span>
                    <select id="legenda-posicao" onchange="atualizarLegenda()">
                        <option value="baixo-dir">⬌ Baixo-Direita</option>
                        <option value="baixo-esq">⬌ Baixo-Esquerda</option>
                        <option value="topo-dir">⬌ Topo-Direita</option>
                        <option value="topo-esq">⬌ Topo-Esquerda</option>
                    </select>
                </div>
                <div class="config-row">
                    <span class="config-label">Fonte:</span>
                    <input type="range" id="legenda-fonte" min="0.5" max="5.0" step="0.1" value="0.8" onchange="atualizarLegenda()">
                    <span class="config-value" id="val-legenda-fonte">0.8</span>
                </div>
                <div class="config-row">
                    <span class="config-label">Transp.:</span>
                    <input type="range" id="legenda-opacidade" min="0" max="255" step="5" value="255" onchange="atualizarLegenda()">
                    <span class="config-value" id="val-legenda-opacidade">255</span>
                </div>
                <div class="config-row">
                    <span class="config-label">Fundo:</span>
                    <input type="color" id="legenda-cor-fundo" value="#000000" onchange="atualizarLegenda()">
                </div>
                <div class="config-row">
                    <span class="config-label">Texto:</span>
                    <input type="color" id="legenda-cor-texto" value="#ffffff" onchange="atualizarLegenda()">
                </div>
            </div>
            <div class="actions" style="margin-top: 10px;">
                <button class="btn-preview" onclick="gerarLegenda()">📋 Gerar com Legenda</button>
                <button class="btn-back" id="btn-voltar" onclick="voltarEdicao()" style="display:none">✏️ Voltar a Editar</button>
            </div>
        </div>
        
        <div class="section">
            <div class="actions">
                <button class="btn-save" onclick="salvar()">💾 Salvar</button>
                <button class="btn-clear" onclick="resetAll()">🔄 Reset</button>
            </div>
        </div>
    </div>
    
    <div class="main-area">
        <div class="canvas-container">
            <img id="canvas" src="{{ img_src }}" alt="Planta">
        </div>
        <div class="controls-bar">
            <div class="controls">
                <span><kbd>Click</kbd> Marcar</span>
                <span><kbd>WASD</kbd> Mover</span>
                <span><kbd>Q/E</kbd> Zoom</span>
                <span><kbd>Z/Y</kbd> Desfazer/Refazer</span>
                <span><kbd>1-9</kbd> Selecionar tipo</span>
            </div>
            <div class="legend">
                <div class="legend-item"><div class="legend-color" style="background:#cbb0ff"></div>Tomada</div>
                <div class="legend-item"><div class="legend-color" style="background:#00ffff"></div>Luminária</div>
                <div class="legend-item"><div class="legend-color" style="background:#ff0000"></div>SPDA</div>
            </div>
        </div>
    </div>
    
    <script>
        let currentType = null;
        let currentTypeName = null;
        let zoom = 1.0;
        let offsetX = 0;
        let offsetY = 0;
        let selectedDisciplina = 'Elétrica';
        let nomesPersonalizados = {{ nomes_json | safe }};
        let markerConfig = {{ config | safe }};
        
        const elementosPorDisciplina = {
            {% for disciplina, elementos in predefinicoes.items() %}
            "{{ disciplina }}": [
                {% for el in elementos %}
                {id: "{{ el.id }}", name: "{{ el.nome }}"},
                {% endfor %}
            ],
            {% endfor %}
        };
        
        // Initialize
        document.addEventListener('DOMContentLoaded', () => {
            selectTab('Elétrica');
            updateImage();
        });
        
        function selectTab(disciplina) {
            const sanitized = sanitizeId(disciplina);
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
            
            document.querySelector(`[data-tab="${sanitized}"]`).classList.add('active');
            document.getElementById(`tab-${sanitized}`).classList.add('active');
            selectedDisciplina = disciplina;
        }
        
        document.querySelectorAll('.tab').forEach(tab => {
            tab.addEventListener('click', () => selectTab(tab.dataset.tab));
        });
        
        function selectElement(id, name) {
            document.querySelectorAll('.element-item').forEach(i => i.classList.remove('selected'));
            const el = document.querySelector(`.element-item[data-id="${id}"]`);
            if (el) el.classList.add('selected');
            currentType = id;
            currentTypeName = name;
            document.getElementById('info-type').textContent = name;
            updateInfo();
        }
        
        // Event delegation - funciona para elementos dinamicamente adicionados
        document.addEventListener('click', (e) => {
            // Não selecionar elemento se clicar em input ou botão
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'BUTTON') return;
            
            const item = e.target.closest('.element-item');
            if (item) {
                selectElement(item.dataset.id, item.dataset.name);
            }
        });
        
        function sanitizeId(name) {
            return name.replace(/[^a-zA-Z0-9_]/g, '_');
        }
        
        function applyEdit(disciplina) {
            const input = document.getElementById('edit-name-' + sanitizeId(disciplina));
            if (!input) {
                return alert('Categoria não encontrada. Recarregue a página.');
            }
            const novoNome = input.value.trim();
            if (!novoNome) return alert('Digite um novo nome');
            
            const selected = document.querySelector(`#elements-${sanitizeId(disciplina)} .element-item.selected`);
            if (!selected) return alert('Selecione um elemento primeiro');
            
            const id = selected.dataset.id;
            const nomeVelho = selected.dataset.name;
            
            fetch('/apply-edit', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({disciplina, id, novoNome})
            }).then(() => {
                // Atualizar nome na lista de elementos
                selected.dataset.name = novoNome;
                selected.querySelector('span').textContent = novoNome;
                
                // Atualizar nomes personalizados
                nomesPersonalizados[disciplina][id] = novoNome;
                
                // Se for o tipo atual, atualizar nome exibido
                if (currentType === id) {
                    currentTypeName = novoNome;
                    document.getElementById('info-type').textContent = novoNome;
                }
                
                input.value = '';
                updateImage();
                alert(`Aplicado: ${nomeVelho} → ${novoNome}`);
            });
        }
        
        function resetNames(disciplina) {
            fetch('/reset-names', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({disciplina})
            }).then(() => {
                // Recarregar página para atualizar listas
                location.reload();
            });
        }
        
        function adicionarCategoria() {
            const nome = document.getElementById('nova-categoria').value.trim();
            if (!nome) return alert('Digite o nome da nova categoria');
            
            fetch('/adicionar-categoria', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({nome})
            }).then(r => r.json()).then(d => {
                if (d.ok) {
                    alert('Categoria adicionada: ' + nome);
                    location.reload();
                } else {
                    alert('Erro: ' + d.erro);
                }
            });
        }
        
        function renomearCategoria() {
            const nomeAntigo = document.getElementById('editar-categoria').value.trim();
            const nomeNovo = document.getElementById('novo-nome-categoria').value.trim();
            if (!nomeAntigo || !nomeNovo) return alert('Preencha ambos os campos');
            
            fetch('/renomear-categoria', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({nomeAntigo, nomeNovo})
            }).then(r => r.json()).then(d => {
                if (d.ok) {
                    alert('Categoria renomeada: ' + nomeAntigo + ' → ' + nomeNovo);
                    location.reload();
                } else {
                    alert('Erro: ' + d.erro);
                }
            });
        }
        
        function removerCategoria() {
            const nome = document.getElementById('editar-categoria').value.trim();
            if (!nome) return alert('Digite o nome da categoria para remover');
            if (!confirm('Tem certeza que deseja remover a categoria "' + nome + '"?')) return;
            
            fetch('/remover-categoria', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({nome})
            }).then(r => r.json()).then(d => {
                if (d.ok) {
                    alert('Categoria removida: ' + nome);
                    location.reload();
                } else {
                    alert('Erro: ' + d.erro);
                }
            });
        }
        
        function salvar() {
            fetch('/salvar', {method: 'POST'})
                .then(r => r.json())
                .then(d => alert('Arquivos salvos: ' + d.files.join(', ')));
        }
        
        function resetAll() {
            fetch('/reset-all', {method: 'POST'})
                .then(() => {
                    currentType = null;
                    currentTypeName = null;
                    document.getElementById('info-type').textContent = 'Selecione...';
                    document.getElementById('info-type-count').textContent = '0';
                    updateImage();
                });
        }
        
        function updateImage() {
            fetch('/image')
                .then(r => r.json())
                .then(d => {
                    document.getElementById('canvas').src = d.img;
                    document.getElementById('info-total').textContent = d.total;
                    currentZoom = d.zoom || 5.0;
                    currentOffsetX = d.offsetX || 0;
                    currentOffsetY = d.offsetY || 0;
                    updateInfo();
                });
        }
        
        function updateInfo() {
            if (!currentType) {
                document.getElementById('info-type').textContent = 'Selecione...';
                document.getElementById('info-type-count').textContent = '0';
                return;
            }
            fetch('/contagem-tipo', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({tipo: currentType})
            }).then(r => r.json()).then(d => {
                document.getElementById('info-type-count').textContent = d.count;
            });
        }
        
        function atualizarConfig() {
            const raio = parseInt(document.getElementById('config-raio').value);
            const espessura = parseInt(document.getElementById('config-espessura').value);
            const fonte_escala = parseFloat(document.getElementById('config-fonte').value);
            const cor_texto = document.getElementById('config-cor').value;
            const cor_borda = document.getElementById('config-cor-borda').value;
            
            document.getElementById('val-raio').textContent = raio;
            document.getElementById('val-espessura').textContent = espessura;
            document.getElementById('val-fonte').textContent = fonte_escala;
            
            markerConfig = {
                raio: raio,
                espessura: espessura,
                fonte_escala: fonte_escala,
                fonte_grossura: 3,
                cor_borda: cor_borda,
                cor_texto: cor_texto,
                zoom_inicial: 5.0
            };
            
            fetch('/atualizar-config', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(markerConfig)
            }).then(() => updateImage());
        }
        
let modoLegenda = false;
        
        function gerarLegenda() {
            fetch('/contagem-total')
                .then(r => r.json())
                .then(d => {
                    if (d.total === 0) {
                        alert('Marque alguns elementos primeiro');
                        return;
                    }
                    document.getElementById('btn-voltar').style.display = 'block';
                    document.querySelector('.sidebar').style.opacity = '0.85';
                    document.getElementById('canvas').style.cursor = 'default';
                    document.getElementById('canvas').style.pointerEvents = 'none';
                    
                    const posicao = document.getElementById('legenda-posicao').value;
                    const tamanhoFonte = document.getElementById('legenda-fonte').value;
                    const opacidade = document.getElementById('legenda-opacidade').value;
                    const corFundo = document.getElementById('legenda-cor-fundo').value;
                    const corTexto = document.getElementById('legenda-cor-texto').value;
                    
                    fetch('/atualizar-config-legenda', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            posicao: posicao,
                            tamanho_fonte: parseFloat(tamanhoFonte),
                            opacidade: parseInt(opacidade),
                            cor_fundo: corFundo,
                            cor_texto: corTexto
                        })
                    });
                    
                    const params = new URLSearchParams({
                        posicao: posicao,
                        tamanho_fonte: tamanhoFonte,
                        opacidade: opacidade,
                        cor_fundo: corFundo,
                        cor_texto: corTexto
                    });
                    
                    fetch('/image-legenda?' + params)
                        .then(r => r.json())
                        .then(d => {
                            document.getElementById('canvas').src = d.img;
                        });
                });
        }
        
        function atualizarLegenda() {
            document.getElementById('val-legenda-fonte').textContent = document.getElementById('legenda-fonte').value;
            document.getElementById('val-legenda-opacidade').textContent = document.getElementById('legenda-opacidade').value;
        }
        
        function voltarEdicao() {
            document.getElementById('btn-voltar').style.display = 'none';
            document.querySelector('.sidebar').style.opacity = '1';
            document.getElementById('canvas').style.cursor = 'crosshair';
            document.getElementById('canvas').style.pointerEvents = 'auto';
            updateImage();
        }
        
        let imgWidth = 0;
        let imgHeight = 0;
        let currentZoom = {{ initial_zoom }};
        let currentOffsetX = {{ initial_offset_x }};
        let currentOffsetY = {{ initial_offset_y }};
        
        // Obter dimensões da imagem do backend
        fetch('/dimensoes')
            .then(r => r.json())
            .then(d => {
                imgWidth = d.width;
                imgHeight = d.height;
            });
        
        function updateImage() {
            fetch('/image')
                .then(r => r.json())
                .then(d => {
                    document.getElementById('canvas').src = d.img;
                    document.getElementById('info-total').textContent = d.total;
                    // Atualizar zoom e offset do servidor
                    currentZoom = d.zoom || 5.0;
                    currentOffsetX = d.offsetX || 0;
                    currentOffsetY = d.offsetY || 0;
                });
        }
        
        document.getElementById('canvas').addEventListener('click', (e) => {
            if (!currentType) return alert('Selecione um elemento primeiro');
            if (!imgWidth || !imgHeight) return alert('Aguarde a imagem carregar');
            
            const rect = e.target.getBoundingClientRect();
            const displayedWidth = rect.width;
            const displayedHeight = rect.height;
            
            // Posição proporcional no canvas exibido
            const clickX = (e.clientX - rect.left) / displayedWidth;
            const clickY = (e.clientY - rect.top) / displayedHeight;
            
            // A view tem tamanho = img / zoom
            const viewW = imgWidth / currentZoom;
            const viewH = imgHeight / currentZoom;
            
            // Converter para coordenadas da imagem original
            const x = Math.floor(clickX * viewW + currentOffsetX);
            const y = Math.floor(clickY * viewH + currentOffsetY);
            
            // Limitar aos limites da imagem
            const finalX = Math.max(0, Math.min(x, imgWidth - 1));
            const finalY = Math.max(0, Math.min(y, imgHeight - 1));
            
            fetch('/add-marcacao', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({x: finalX, y: finalY, tipo: currentType})
            }).then(() => updateImage());
        });
        
        document.addEventListener('keydown', (e) => {
            // Ignorar atalhos se estiver em campo de input
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
                return;
            }
            
            const key = e.key.toLowerCase();
            
            // Atalhos numéricos para selecionar elemento (1-9, 0, -, =)
            if (e.key >= '1' && e.key <= '9') {
                const idx = parseInt(e.key) - 1;
                const elementos = elementosPorDisciplina[selectedDisciplina];
                if (elementos && idx < elementos.length) {
                    selectElement(elementos[idx].id, elementos[idx].name);
                    return;
                }
            } else if (e.key === '0') {
                const elementos = elementosPorDisciplina[selectedDisciplina];
                if (elementos && elementos.length >= 10) {
                    selectElement(elementos[9].id, elementos[9].name);
                    return;
                }
            } else if (e.key === '-' && elementosPorDisciplina[selectedDisciplina]?.length >= 11) {
                selectElement(elementosPorDisciplina[selectedDisciplina][10].id, elementosPorDisciplina[selectedDisciplina][10].name);
                return;
            } else if (e.key === '=' && elementosPorDisciplina[selectedDisciplina]?.length >= 12) {
                selectElement(elementosPorDisciplina[selectedDisciplina][11].id, elementosPorDisciplina[selectedDisciplina][11].name);
                return;
            }
            
            if (key === 'z') {
                fetch('/undo', {method: 'POST'}).then(() => updateImage());
            } else if (key === 'y') {
                fetch('/redo', {method: 'POST'}).then(() => updateImage());
            } else if (key === 'q') {
                currentZoom = Math.min(5, currentZoom * 1.3);
                fetch('/set-zoom', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({zoom: currentZoom})}).then(() => updateImage());
            } else if (key === 'e') {
                currentZoom = Math.max(0.2, currentZoom / 1.3);
                fetch('/set-zoom', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({zoom: currentZoom})}).then(() => updateImage());
            } else if (key === 'w') {
                currentOffsetY = Math.max(0, currentOffsetY - 50);
                fetch('/set-offset', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({x: currentOffsetX, y: currentOffsetY})}).then(() => updateImage());
            } else if (key === 's') {
                currentOffsetY = currentOffsetY + 50;
                fetch('/set-offset', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({x: currentOffsetX, y: currentOffsetY})}).then(() => updateImage());
            } else if (key === 'a') {
                currentOffsetX = Math.max(0, currentOffsetX - 50);
                fetch('/set-offset', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({x: currentOffsetX, y: currentOffsetY})}).then(() => updateImage());
            } else if (key === 'd') {
                currentOffsetX = currentOffsetX + 50;
                fetch('/set-offset', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({x: currentOffsetX, y: currentOffsetY})}).then(() => updateImage());
            }
        });
        
        // Carregar dados iniciais
        updateImage();
    </script>
</body>
</html>
"""


nomes_personalizados = {}
for disc, itens in predefinicoes.items():
    nomes_personalizados[disc] = {item["id"]: item["nome"] for item in itens}


@app.route("/")
def index():
    global img_global, nome_base

    if img_global is None:
        return "Nenhuma imagem carregada"

    img_src = gerar_imagem_base64(
        img_global, zoom, offset_x, offset_y, marcacoes, config_marker
    )

    nomes_json = {}
    for disc, itens in predefinicoes.items():
        nomes_json[disc] = {
            item["id"]: nomes_personalizados[disc].get(item["id"], item["nome"])
            for item in itens
        }

    return render_template_string(
        HTML_TEMPLATE,
        predefinicoes=predefinicoes,
        cores=cores_tipo,
        img_src=img_src,
        nome_base=nome_base,
        nomes_json=nomes_json,
        initial_zoom=zoom,
        initial_offset_x=offset_x,
        initial_offset_y=offset_y,
        config=json.dumps(config_marker),
    )


@app.route("/image")
def get_image():
    if img_global is None:
        return jsonify(
            {
                "img": "",
                "total": 0,
                "zoom": zoom,
                "offsetX": offset_x,
                "offsetY": offset_y,
            }
        )

    img_src = gerar_imagem_base64(
        img_global, zoom, offset_x, offset_y, marcacoes, config_marker
    )
    return jsonify(
        {
            "img": img_src,
            "total": len(marcacoes),
            "zoom": zoom,
            "offsetX": offset_x,
            "offsetY": offset_y,
        }
    )


@app.route("/contagem-total")
def contagem_total():
    return jsonify({"total": len(marcacoes)})


@app.route("/image-legenda")
def get_image_legenda():
    posicao = request.args.get(
        "posicao", config_marker.get("legenda_posicao", "baixo-dir")
    )
    tamanho_fonte = float(
        request.args.get(
            "tamanho_fonte", config_marker.get("legenda_tamanho_fonte", 0.8)
        )
    )
    opacidade = int(
        request.args.get("opacidade", config_marker.get("legenda_opacidade", 255))
    )
    cor_fundo = request.args.get(
        "cor_fundo", config_marker.get("legenda_cor_fundo", "#000000")
    )
    cor_texto = request.args.get(
        "cor_texto", config_marker.get("legenda_cor_texto", "#ffffff")
    )

    config_legenda = {
        "posicao": posicao,
        "tamanho_fonte": tamanho_fonte,
        "opacidade": opacidade,
        "cor_fundo": cor_fundo,
        "cor_texto": cor_texto,
    }

    if img_global is None:
        return jsonify({"img": "", "total": 0})

    img_com_marcas = img_global.copy()
    cfg = config_marker
    raio = cfg.get("raio", 35)
    espessura = cfg.get("espessura", 3)
    fonte_escala = cfg.get("fonte_escala", 1.2)
    fonte_grossura = cfg.get("fonte_grossura", 3)
    cor_borda = cfg.get("cor_borda", "#000000")
    cor_texto_marker = cfg.get("cor_texto", "#ffffff")

    rb = int(cor_borda[1:3], 16)
    gb = int(cor_borda[3:5], 16)
    rt = int(cor_borda[5:7], 16)
    tb = int(cor_texto_marker[1:3], 16)
    tg = int(cor_texto_marker[3:5], 16)
    tr = int(cor_texto_marker[5:7], 16)

    for x, y, num, tipo in marcacoes:
        cor = cores_tipo.get(tipo, "#ffffff")
        b = int(cor[1:3], 16)
        g = int(cor[3:5], 16)
        r = int(cor[5:7], 16)

        cv2.circle(img_com_marcas, (x, y), raio, (b, g, r), -1)
        cv2.circle(img_com_marcas, (x, y), raio, (rb, gb, rt), espessura)

        texto = str(num)
        fonte = cv2.FONT_HERSHEY_SIMPLEX

        (tw, th), baseline = cv2.getTextSize(texto, fonte, fonte_escala, fonte_grossura)
        cv2.putText(
            img_com_marcas,
            texto,
            (x - tw // 2, y + th // 2 + baseline),
            fonte,
            fonte_escala,
            (0, 0, 0),
            fonte_grossura + 2,
            cv2.LINE_AA,
        )
        cv2.putText(
            img_com_marcas,
            texto,
            (x - tw // 2, y + th // 2 + baseline),
            fonte,
            fonte_escala,
            (tb, tg, tr),
            fonte_grossura,
            cv2.LINE_AA,
        )

    img_com_legenda = adicionar_legenda(
        img_com_marcas, marcacoes, nomes_personalizados, config_legenda
    )
    img_com_legenda_bgr = cv2.cvtColor(img_com_legenda, cv2.COLOR_RGB2BGR)
    _, buffer = cv2.imencode(".png", img_com_legenda_bgr)
    img_base64 = base64.b64encode(buffer).decode()
    return jsonify(
        {"img": f"data:image/png;base64,{img_base64}", "total": len(marcacoes)}
    )


@app.route("/dimensoes")
def get_dimensoes():
    if img_global is None:
        return jsonify({"width": 0, "height": 0})
    h, w = img_global.shape[:2]
    return jsonify({"width": w, "height": h})


@app.route("/add-marcacao", methods=["POST"])
def add_marcacao():
    global marcacoes

    data = request.json
    x = int(data["x"])
    y = int(data["y"])
    tipo = data["tipo"]

    num = sum(1 for m in marcacoes if m[3] == tipo) + 1
    marcacoes.append((x, y, num, tipo))

    return jsonify({"ok": True})


@app.route("/apply-edit", methods=["POST"])
def apply_edit():
    global nomes_personalizados, marcacoes

    data = request.json
    disciplina = data["disciplina"]
    id_elem = data["id"]
    novoNome = data["novoNome"]

    nomes_personalizados[disciplina][id_elem] = novoNome

    for i, (x, y, num, tipo) in enumerate(marcacoes):
        if tipo == id_elem:
            marcacoes[i] = (x, y, num, tipo)

    return jsonify({"ok": True})


@app.route("/reset-names", methods=["POST"])
def reset_names():
    global nomes_personalizados

    data = request.json
    disciplina = data["disciplina"]

    nomes_personalizados[disciplina] = {
        item["id"]: item["nome"] for item in predefinicoes[disciplina]
    }

    return jsonify({"ok": True})


@app.route("/adicionar-categoria", methods=["POST"])
def adicionar_categoria():
    data = request.json
    nome = data.get("nome", "").strip()

    if not nome:
        return jsonify({"ok": False, "erro": "Nome vazio"})

    if nome in predefinicoes:
        return jsonify({"ok": False, "erro": "Categoria já existe"})

    # Cores distintas para placeholders (12 cores diferentes)
    cores_placeholders = [
        "#ff6b6b",
        "#4ecdc4",
        "#45b7d1",
        "#96ceb4",
        "#ffeaa7",
        "#dfe6e9",
        "#fd79a8",
        "#a29bfe",
        "#00b894",
        "#e17055",
        "#74b9ff",
        "#fdcb6e",
    ]

    # Filtrar cores já usadas
    cores_usadas = set(cores_tipo.values())
    cores_disponiveis = [c for c in cores_placeholders if c not in cores_usadas]
    if not cores_disponiveis:
        cores_disponiveis = cores_placeholders

    # Criar 9 elementos placeholders com atalhos 1-9
    elementos = []
    for i in range(9):
        elemento_id = f"{nome.lower().replace(' ', '_')}_{i + 1}"
        elemento_nome = f"Elemento {i + 1}"
        elementos.append({"id": elemento_id, "nome": elemento_nome})
        cores_tipo[elemento_id] = cores_disponiveis[i % len(cores_disponiveis)]

    predefinicoes[nome] = elementos
    nomes_personalizados[nome] = {item["id"]: item["nome"] for item in elementos}

    return jsonify({"ok": True})


@app.route("/renomear-categoria", methods=["POST"])
def renomear_categoria():
    data = request.json
    nome_antigo = data.get("nomeAntigo", "").strip()
    nome_novo = data.get("nomeNovo", "").strip()

    if not nome_antigo or not nome_novo:
        return jsonify({"ok": False, "erro": "Nomes inválidos"})

    if nome_antigo not in predefinicoes:
        return jsonify({"ok": False, "erro": "Categoria não existe"})

    if nome_novo in predefinicoes:
        return jsonify({"ok": False, "erro": "Nome já existe"})

    predefinicoes[nome_novo] = predefinicoes.pop(nome_antigo)
    nomes_personalizados[nome_novo] = nomes_personalizados.pop(nome_antigo)

    return jsonify({"ok": True})


@app.route("/remover-categoria", methods=["POST"])
def remover_categoria():
    global predefinicoes

    data = request.json
    nome = data.get("nome", "").strip()

    if nome not in predefinicoes:
        return jsonify({"ok": False, "erro": "Categoria não existe"})

    if len(predefinicoes) <= 1:
        return jsonify({"ok": False, "erro": "Não pode remover última categoria"})

    del predefinicoes[nome]
    if nome in nomes_personalizados:
        del nomes_personalizados[nome]

    return jsonify({"ok": True})


@app.route("/undo", methods=["POST"])
def undo():
    global marcacoes
    # Simplified - just clear last
    if marcacoes:
        marcacoes.pop()
    return jsonify({"ok": True})


@app.route("/redo", methods=["POST"])
def redo():
    return jsonify({"ok": True})


@app.route("/set-zoom", methods=["POST"])
def set_zoom():
    global zoom
    zoom = request.json.get("zoom", 1.0)
    return jsonify({"ok": True})


@app.route("/set-offset", methods=["POST"])
def set_offset():
    global offset_x, offset_y
    offset_x = request.json.get("x", 0)
    offset_y = request.json.get("y", 0)
    return jsonify({"ok": True})


@app.route("/salvar", methods=["POST"])
def salvar():
    global img_global, nome_base, marcacoes, config_marker

    print(f"[DEBUG] /salvar chamado - marcacoes: {len(marcacoes)}")
    if img_global is None:
        return jsonify({"files": []})

    cfg = config_marker
    raio = cfg.get("raio", 35)
    espessura = cfg.get("espessura", 3)
    fonte_escala = cfg.get("fonte_escala", 1.2)
    fonte_grossura = cfg.get("fonte_grossura", 3)
    cor_borda = cfg.get("cor_borda", "#000000")
    cor_texto = cfg.get("cor_texto", "#ffffff")

    rb = int(cor_borda[1:3], 16)
    gb = int(cor_borda[3:5], 16)
    rt = int(cor_borda[5:7], 16)
    tb = int(cor_texto[1:3], 16)
    tg = int(cor_texto[3:5], 16)
    tr = int(cor_texto[5:7], 16)

    img_marcada = img_global.copy()
    for x, y, num, tipo in marcacoes:
        cor = cores_tipo.get(tipo, "#ffffff")
        b = int(cor[1:3], 16)
        g = int(cor[3:5], 16)
        r = int(cor[5:7], 16)

        cv2.circle(img_marcada, (x, y), raio, (b, g, r), -1)
        cv2.circle(img_marcada, (x, y), raio, (rb, gb, rt), espessura)

        texto = str(num)
        fonte = cv2.FONT_HERSHEY_SIMPLEX

        (tw, th), baseline = cv2.getTextSize(texto, fonte, fonte_escala, fonte_grossura)
        cv2.putText(
            img_marcada,
            texto,
            (x - tw // 2, y + th // 2 + baseline),
            fonte,
            fonte_escala,
            (0, 0, 0),
            fonte_grossura + 2,
            cv2.LINE_AA,
        )
        cv2.putText(
            img_marcada,
            texto,
            (x - tw // 2, y + th // 2 + baseline),
            fonte,
            fonte_escala,
            (tb, tg, tr),
            fonte_grossura,
            cv2.LINE_AA,
        )

    config_legenda = {
        "posicao": config_marker.get("legenda_posicao", "baixo-dir"),
        "tamanho_fonte": config_marker.get("legenda_tamanho_fonte", 0.8),
        "opacidade": config_marker.get("legenda_opacidade", 255),
        "cor_fundo": config_marker.get("legenda_cor_fundo", "#000000"),
        "cor_texto": config_marker.get("legenda_cor_texto", "#ffffff"),
    }
    img_com_legenda = adicionar_legenda(
        img_marcada, marcacoes, nomes_personalizados, config_legenda
    )
    img_com_legenda_bgr = cv2.cvtColor(img_com_legenda, cv2.COLOR_RGB2BGR)

    img_dir = os.path.dirname(os.path.abspath(IMG_PATH)) if IMG_PATH else "."
    saida_img = os.path.join(img_dir, f"{nome_base}_marcado.png")
    print(f"[DEBUG] Salvando imagem em: {saida_img}")
    cv2.imwrite(saida_img, img_com_legenda_bgr)

    # Salvar CSV de contagem
    csv_file = os.path.join(img_dir, f"{nome_base}_contagem.csv")
    with open(csv_file, "w") as f:
        f.write("numero,tipo,x,y\n")
        for x, y, n, t in marcacoes:
            f.write(f"{n},{t},{x},{y}\n")

    # Salvar arquivo de coordenadas
    txt_file = os.path.join(img_dir, f"{nome_base}_coordenadas.txt")
    with open(txt_file, "w") as f:
        f.write(f"# {nome_base}\n")
        f.write(f"# Total: {len(marcacoes)}\n\n")
        f.write("numero,tipo,x,y\n")
        for x, y, n, t in marcacoes:
            f.write(f"{n},{t},{x},{y}\n")

    return jsonify({"files": [saida_img, csv_file, txt_file]})


@app.route("/reset-all", methods=["POST"])
def reset_all():
    global marcacoes
    marcacoes = []
    return jsonify({"ok": True})


@app.route("/contagem-tipo", methods=["POST"])
def contagem_tipo():
    data = request.json
    tipo = data.get("tipo", "")
    count = sum(1 for m in marcacoes if m[3] == tipo)
    return jsonify({"count": count})


@app.route("/atualizar-config", methods=["POST"])
def atualizar_config():
    global config_marker
    data = request.json
    config_marker["raio"] = data.get("raio", config_marker.get("raio", 35))
    config_marker["espessura"] = data.get(
        "espessura", config_marker.get("espessura", 3)
    )
    config_marker["fonte_escala"] = data.get(
        "fonte_escala", config_marker.get("fonte_escala", 1.2)
    )
    config_marker["fonte_grossura"] = data.get(
        "fonte_grossura", config_marker.get("fonte_grossura", 3)
    )
    config_marker["cor_borda"] = data.get(
        "cor_borda", config_marker.get("cor_borda", "#000000")
    )
    config_marker["cor_texto"] = data.get(
        "cor_texto", config_marker.get("cor_texto", "#ffffff")
    )
    return jsonify({"ok": True})


@app.route("/atualizar-config-legenda", methods=["POST"])
def atualizar_config_legenda():
    global config_marker
    data = request.json
    config_marker["legenda_posicao"] = data.get(
        "posicao", config_marker.get("legenda_posicao", "baixo-dir")
    )
    config_marker["legenda_tamanho_fonte"] = data.get(
        "tamanho_fonte", config_marker.get("legenda_tamanho_fonte", 0.8)
    )
    config_marker["legenda_opacidade"] = data.get(
        "opacidade", config_marker.get("legenda_opacidade", 255)
    )
    config_marker["legenda_cor_fundo"] = data.get(
        "cor_fundo", config_marker.get("legenda_cor_fundo", "#000000")
    )
    config_marker["legenda_cor_texto"] = data.get(
        "cor_texto", config_marker.get("legenda_cor_texto", "#ffffff")
    )
    return jsonify({"ok": True})


def main():
    global IMG_PATH, PAGINA, DPI

    parser = argparse.ArgumentParser(description="Contador interativo web")
    parser.add_argument("arquivo", nargs="?", help="Arquivo de imagem ou PDF")
    parser.add_argument("--pagina", type=int, default=1)
    parser.add_argument("--dpi", type=int, default=150)
    parser.add_argument("--port", type=int, default=5000)
    args = parser.parse_args()

    IMG_PATH = args.arquivo or "ELE.pdf"
    PAGINA = args.pagina
    DPI = args.dpi

    print(f"\n📄 Carregando: {IMG_PATH}...")
    img = carregar_imagem(IMG_PATH, PAGINA, DPI)
    print(f"✓ Imagem carregada: {img.shape[1]}x{img.shape[0]}")

    print(f"\n🌐 Servidor iniciado em: http://localhost:{args.port}")
    print("   Pressione Ctrl+C para encerrar\n")

    app.run(host="0.0.0.0", port=args.port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
