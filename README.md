# Element Counter

Interactive web-based tool for marking and counting elements on construction plans (PDF/images).

## Features

- **Interactive Marking**: Click on plans to mark elements
- **Multiple Categories**: Organize elements by discipline (Electrical, SPDA, Pumps, Junctions)
- **Custom Markers**: Adjust marker size, border color, text color
- **Overlay Legend**: Legend positioned over the image (no dimension changes)
- **UTF-8 Support**: Full support for Portuguese characters (ç, ã, ó, etc.)
- **Export**: Save marked images with legend, CSV and TXT files with coordinates

## Installation

```bash
pip install opencv-python numpy flask pdf2image pillow
```

## Usage

```bash
python src/contar_elementos.py path/to/your/plan.pdf
```

Open your browser at `http://localhost:5000`

### Controls

- **Click**: Mark element
- **WASD**: Pan image
- **Q/E**: Zoom in/out
- **Z/Y**: Undo/Redo
- **1-9**: Quick element selection

### Legend Controls

- **Position**: Choose corner (bottom-right, bottom-left, top-right, top-left)
- **Font Size**: Adjust (0.5 - 5.0)
- **Transparency**: Background opacity (0-255)
- **Colors**: Customize background and text colors

## Output Files

When saving, generates:
- `*_marcado.png` - Image with markers and legend
- `*_contagem.csv` - CSV with element counts
- `*_coordenadas.txt` - Text file with coordinates

## License

MIT