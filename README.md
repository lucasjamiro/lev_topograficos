# Simulador de Levantamentos Topográficos

Simulador interativo para o aprendizado prático de poligonação (traverses) e nivelamento (leveling). O sistema permite a simulação de dados de campo, processamento de cálculos topográficos e validação pedagógica através do "Modo Desafio".

## Arquitetura do Sistema

Abaixo está representada a organização das classes de estado e os módulos funcionais do simulador.

```mermaid
classDiagram
    class SessionState {
        +list survey_points
        +DataFrame survey_data
        +list map_center_coord
        +int map_zoom
        +list true_elevations
    }

    class AppUI {
        +Sidebar settings
        +FoliumMap interactive_map
        +DataEditor vertex_table
        +Tabs results_display
        +reset_survey()
    }

    class Simulator {
        +generate_traverse_coordinates(n_inter, type, start_lat, start_lon) NDArray
        +simulate_traverse_observations(e_coords, n_coords, type) DataFrame
        +process_traverse_data(df, start, hv2, type, end_s, end_e) tuple
        +simulate_leveling(n_pts, type, method) tuple
        +get_rod_reading_visual(value) String
    }

    AppUI --> SessionState : gerencia
    AppUI --> Simulator : solicita cálculos
    Simulator ..> SessionState : consome/gera dados
```

## Fluxo de Execução Funcional

O diagrama a seguir detalha a cadeia de processamento para os modos de Poligonação e Nivelamento.

### 1. Fluxo de Poligonação (Traverse)
```mermaid
graph TD
    A[Seleção no Mapa / Entrada Manual] --> B[Simulação de Observações de Campo]
    B --> C[Geração de Caderneta: Dist. Inclinada, Ângulos Zenitais e Horizontais]
    C --> D[Cálculo do Erro Angular Verdadeiro]
    D --> E[Distribuição das Correções de Azimute]
    E --> F[Cálculo de Coordenadas Provisórias]
    F --> G[Ajuste Linear de Bowditch]
    G --> H[Renderização da Tabela de Coordenadas Finais]
```

### 2. Fluxo de Nivelamento (Leveling)
```mermaid
graph TD
    I[Geração de Trajeto / Pontos] --> J[Simulação de Leituras de Mira]
    J --> K[Visualização da Mira Falante - ASCII]
    K --> L[Entrada de Cálculos Manuais pelo Aluno]
    L --> M[Validação Backend vs. Valores Reais]
    M --> N[Exibição do Erro Médio e Status de Aprovação]
```

## Tecnologias Utilizadas

- **Frontend:** Streamlit, Folium, streamlit-folium.
- **Cálculos:** NumPy, Pandas, UTM.
- **Distribuição:** Stlite (WebAssembly para execução no navegador).

## Como Executar

Para rodar localmente:
```bash
pip install streamlit folium streamlit-folium numpy pandas utm
streamlit run app.py
```
