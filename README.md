# Visualizador de Matriz OD

Este repositório contém um aplicativo em Streamlit para visualização interativa de uma matriz Origem-Destino (OD), com base em dados geográficos de zonas de tráfego.

## Funcionalidades

- Visualização de conexões OD em mapa interativo
- Filtros por origem, destino e volume
- Tabela de dados interativa

## Como rodar

1. Clone este repositório:
```bash
git clone https://github.com/seu-usuario/visualizador-matriz-od.git
cd visualizador-matriz-od
```

2. Instale as dependências:
```bash
pip install -r requirements.txt
```

3. Execute o app:
```bash
streamlit run app.py
```

## Estrutura dos arquivos

- `app.py`: código principal do app
- `matriz_od.csv`: dados OD em formato longo
- `zonas_OD/`: shapefiles geográficos das zonas