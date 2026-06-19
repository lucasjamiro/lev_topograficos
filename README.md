# Simulador de Levantamentos Topográficos

Simulador de dados observacionais para levantamentos topográficos de poligonação (fechada e enquadrada) e nivelamentos (geométricos e trigonométricos).

## Funcionalidades
- **Poligonação**: Gera coordenadas e simula ângulos e distâncias para poligonais fechadas e enquadradas.
- **Nivelamento**: Simula cadernetas de nivelamento geométrico e trigonométrico.
- **Visualização**: Mapa interativo utilizando Folium.
- **Interatividade**: Ajuste o número de pontos, precisão das observações e localização inicial.

## Como Executar Localmente

1. Instale as dependências:
   ```bash
   pip install streamlit folium streamlit-folium numpy pandas
   ```
2. Execute o Streamlit:
   ```bash
   streamlit run app.py
   ```

## Como Hospedar no GitHub Pages

Este projeto foi preparado para rodar diretamente no navegador utilizando **Stlite** (Streamlit via WebAssembly), o que permite a hospedagem gratuita no GitHub Pages sem a necessidade de um servidor Python.

1. Faça o upload do arquivo `index.html` para o seu repositório no GitHub.
2. Vá em **Settings** > **Pages**.
3. Em **Branch**, selecione `main` (ou a sua branch principal) e a pasta `/ (root)`.
4. Salve e aguarde o link ser gerado.

O arquivo `index.html` contém todo o código necessário embutido para carregar a aplicação.
