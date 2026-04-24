# PROJECT KNOWLEDGE BASE

**Generated:** 2026-04-24
**Commit:** N/A (no git)
**Branch:** N/A

## OVERVIEW
Data analysis pipeline for SINAPI (Sistema Nacional de Pesquisa de Custos e Índices da Construção Civil) - Brazilian construction cost database. Python scripts process Excel reference data, extract quantities from PDFs, and generate LaTeX reports.

## STRUCTURE
```
./
├── *.py                    # Analysis scripts (root-level, no src/)
├── *.xlsx                  # SINAPI reference data
├── *.pdf                   # Project documents, ELE.pdf
├── *.tex                   # LaTeX budget files
├── *.csv, *.txt            # Extracted coordinates/counts per page
├── pagina_*_marcado.png    # Annotated page scans
├── quantidades_extraidas/  # Output directory (estimativas, HTML reports)
└── .ruff_cache/            # Linter cache (ruff present but no config)
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| Data exploration | `explorar_sinapi.py` | Initial SINAPI Excel analysis |
| Element counting | `contar_elementos.py` | Count elements from PDF pages |
| Visual analysis | `analise_visual.py` | OCR/visual extraction |
| Quantity estimation | `estimar_quantidades.py` | Main quantity calculator |
| Report generation | `gerar_relatorio.py` | LaTeX output |
| Reference data | `SINAPI_Custo_Ref_*_202412_Desonerado.xlsx` | Cost database |
| Extracted data | `quantidades_extraidas/` | Processed results |

## CODE MAP
| Symbol | Type | Location | Refs | Role |
|--------|------|----------|------|------|
| main() | function | explorar_sinapi.py | - | Entry point |
| main() | function | contar_elementos.py | - | Entry point |
| main() | function | analise_visual.py | - | Entry point |
| main() | function | estimar_quantidades.py | - | Entry point |
| main() | function | gerar_relatorio.py | - | Entry point |

## CONVENTIONS
- All Python files at root level (no src/ package structure)
- No `__init__.py` - not a proper Python package
- Output directory: `quantidades_extraidas/`
- Page data files: `pagina_N_contagem.csv`, `pagina_N_coordenadas.txt`, `pagina_N_marcado.png`
- Portuguese language in code comments and output

## ANTI-PATTERNS (THIS PROJECT)
- No version control (no .git/)
- No dependency management (no requirements.txt, pyproject.toml)
- No test files or test directory
- No CI/CD configuration
- Mixed concerns: code, data, outputs all in root
- No ruff/eslint config (only cache present)

## UNIQUE STYLES
- Single-function `main()` scripts as entry points
- Output-heavy: generates HTML, Excel, Markdown, LaTeX
- Page-based data: each PDF page has associated coordinate/count files
- Brazilian Portuguese domain (SINAPI construction costs)

## COMMANDS
```bash
# No standard commands - run individual scripts:
python explorar_sinapi.py
python contar_elementos.py
python analise_visual.py
python estimar_quantidades.py
python gerar_relatorio.py
```

## NOTES
- Ruff linter cache present (.ruff_cache/) but no config file
- Excel file contains SINAPI reference compositions (2024-12, Ceará, Desonerado)
- PDFs contain project ELE (Elementos de Lista de Especificações)
- Coordinate files map PDF regions to element counts