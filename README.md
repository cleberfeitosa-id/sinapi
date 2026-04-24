# SINAPI Pipeline

Ferramentas Python para análise de custos e quantitativos da construção civil usando o banco de dados SINAPI (Sistema Nacional de Pesquisa de Custos e Índices da Construção Civil).

## Estrutura

```
sinapi/
├── src/
│   ├── __init__.py
│   ├── contar_elementos.py     # Contador interativo de elementos em plantas
│   ├── analise_visual.py     # Extração visual de dados via OCR
│   ├── estimar_quantidades.py # Estimativa de quantidades
│   ├── gerar_relatorio.py   # Geração de relatórios LaTeX
│   └── exploracao_sinapi.py  # Exploração de dados SINAPI
├── data/
│   ├── ELE.pdf              # Projeto arquitetônico
│   └── SINAPI_Custo_Ref_*.xlsx # Banco de dados SINAPI
├── output/
│   └── *.csv, *.tex, *.md   # Resultados gerados
└── docs/
```

## Instalação

```bash
pip install -r requirements.txt
```

## Uso

### Contador de Elementos (Web)

Contagem interativa de elementos em plantas:

```bash
python src/contar_elementos.py data/ELE.pdf --port 5000
```

Acesse: http://localhost:5000

### Exploração de Dados SINAPI

```bash
python src/exploracao_sinapi.py
```

### Estimativa de Quantidades

```bash
python src/estimar_quantidades.py
```

### Geração de Relatório LaTeX

```bash
python src/gerar_relatorio.py
```

## Dependências

- opencv-python
- numpy
- pdf2image
- flask
- pandas
- matplotlib

## Licença

MIT