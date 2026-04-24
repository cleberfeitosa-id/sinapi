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

from flask import Flask, render_template_string, request, jsonify
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
contador = 1
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
    "Hidrossanitário": [
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
    # Hidrossanitário
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


def gerar_imagem_base64(img, zoom, off_x, off_y, marcacoes):
    h, w = img.shape[:2]

    # Calcula tamanho da view baseada no zoom (zoom 1 = imagem inteira, zoom 5 = 1/5)
    view_w = int(w / zoom)
    view_h = int(h / zoom)

    # Recorta a região de interesse
    roi = img[off_y : min(off_y + view_h, h), off_x : min(off_x + view_w, w)]

    if roi.size > 0:
        # Redimensiona a ROI para o tamanho de visualização (mantendo qualidade)
        disp = cv2.resize(roi, (int(roi.shape[1] * zoom), int(roi.shape[0] * zoom)))

        # Desenha as marcações
        for x_orig, y_orig, num, tipo in marcacoes:
            # Calcula posição relativa ao offset atual
            x_disp = int((x_orig - off_x) * zoom)
            y_disp = int((y_orig - off_y) * zoom)

            if 0 <= x_disp < disp.shape[1] and 0 <= y_disp < disp.shape[0]:
                cor = cores_tipo.get(tipo, "#ffffff")
                b = int(cor[1:3], 16)
                g = int(cor[3:5], 16)
                r = int(cor[5:7], 16)

                # Raio maior para melhor visibilidade
                raio = max(25, int(35 * zoom))
                cv2.circle(disp, (x_disp, y_disp), raio, (b, g, r), -1)
                cv2.circle(disp, (x_disp, y_disp), raio, (0, 0, 0), 3)

                # Texto maior (metade do raio) e branco com borda preta
                texto = str(num)
                fonte = cv2.FONT_HERSHEY_SIMPLEX
                escala = max(1.2, 1.5 * zoom)
                grossura = 3

                # Primeiro desenha borda preta
                (tw, th), baseline = cv2.getTextSize(texto, fonte, escala, grossura)
                cv2.putText(
                    disp,
                    texto,
                    (x_disp - tw // 2, y_disp + th // 2 + baseline),
                    fonte,
                    escala,
                    (0, 0, 0),
                    grossura + 2,
                    cv2.LINE_AA,
                )

                # Depois desenha texto branco
                cv2.putText(
                    disp,
                    texto,
                    (x_disp - tw // 2, y_disp + th // 2 + baseline),
                    fonte,
                    escala,
                    (255, 255, 255),
                    grossura,
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
        
        // Elementos por disciplina para atalhos numéricos
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

    img_src = gerar_imagem_base64(img_global, zoom, offset_x, offset_y, marcacoes)

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

    img_src = gerar_imagem_base64(img_global, zoom, offset_x, offset_y, marcacoes)
    return jsonify(
        {
            "img": img_src,
            "total": len(marcacoes),
            "zoom": zoom,
            "offsetX": offset_x,
            "offsetY": offset_y,
        }
    )


@app.route("/dimensoes")
def get_dimensoes():
    if img_global is None:
        return jsonify({"width": 0, "height": 0})
    h, w = img_global.shape[:2]
    return jsonify({"width": w, "height": h})


@app.route("/add-marcacao", methods=["POST"])
def add_marcacao():
    global contador, marcacoes

    data = request.json
    x = int(data["x"])
    y = int(data["y"])
    tipo = data["tipo"]

    marcacoes.append((x, y, contador, tipo))
    contador += 1

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
    global marcacoes, contador
    # Simplified - just clear last
    if marcacoes:
        marcacoes.pop()
        if marcacoes:
            contador = max(m[2] for m in marcacoes) + 1
        else:
            contador = 1
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
    global img_global, nome_base, marcacoes

    if img_global is None:
        return jsonify({"files": []})

    img_marcada = img_global.copy()
    for x, y, num, tipo in marcacoes:
        cor = cores_tipo.get(tipo, "#ffffff")
        b = int(cor[1:3], 16)
        g = int(cor[3:5], 16)
        r = int(cor[5:7], 16)

        raio = 35
        cv2.circle(img_marcada, (x, y), raio, (b, g, r), -1)
        cv2.circle(img_marcada, (x, y), raio, (0, 0, 0), 3)

        texto = str(num)
        fonte = cv2.FONT_HERSHEY_SIMPLEX
        escala = 1.2
        grossura = 3

        (tw, th), baseline = cv2.getTextSize(texto, fonte, escala, grossura)
        cv2.putText(
            img_marcada,
            texto,
            (x - tw // 2, y + th // 2 + baseline),
            fonte,
            escala,
            (0, 0, 0),
            grossura + 2,
            cv2.LINE_AA,
        )
        cv2.putText(
            img_marcada,
            texto,
            (x - tw // 2, y + th // 2 + baseline),
            fonte,
            escala,
            (255, 255, 255),
            grossura,
            cv2.LINE_AA,
        )

    # Salvar imagem PNG
    saida_img = f"{nome_base}_marcado.png"
    cv2.imwrite(saida_img, img_marcada)

    # Salvar CSV de contagem
    csv_file = f"{nome_base}_contagem.csv"
    with open(csv_file, "w") as f:
        f.write("numero,tipo,x,y\n")
        for x, y, n, t in marcacoes:
            f.write(f"{n},{t},{x},{y}\n")

    # Salvar arquivo de coordenadas
    txt_file = f"{nome_base}_coordenadas.txt"
    with open(txt_file, "w") as f:
        f.write(f"# {nome_base}\n")
        f.write(f"# Total: {len(marcacoes)}\n\n")
        f.write("numero,tipo,x,y\n")
        for x, y, n, t in marcacoes:
            f.write(f"{n},{t},{x},{y}\n")

    return jsonify({"files": [saida_img, csv_file, txt_file]})


@app.route("/reset-all", methods=["POST"])
def reset_all():
    global marcacoes, contador
    marcacoes = []
    contador = 1
    return jsonify({"ok": True})


@app.route("/contagem-tipo", methods=["POST"])
def contagem_tipo():
    data = request.json
    tipo = data.get("tipo", "")
    count = sum(1 for m in marcacoes if m[3] == tipo)
    return jsonify({"count": count})


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
