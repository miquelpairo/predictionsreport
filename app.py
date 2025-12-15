"""
NIR Predictions Analyzer - Streamlit Application
Análisis de predicciones NIR de diferentes lámparas
"""

import streamlit as st
import pandas as pd
import numpy as np
import xml.etree.ElementTree as ET
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import io
from datetime import datetime
from buchi_streamlit_theme import apply_buchi_styles, BUCHI_COLORS


class NIRAnalyzer:
    """Clase para analizar datos NIR desde archivos XML"""
    
    def __init__(self):
        self.data = {}
        self.products = []
        self.sensor_serial = None
        
    def parse_xml(self, uploaded_file):
        """Parse XML file from NIR-Online software"""
        try:
            # Leer el contenido del archivo
            content = uploaded_file.read()
            
            # Parse XML
            root = ET.fromstring(content)
            
            # Namespace del XML
            ns = {'ss': 'urn:schemas-microsoft-com:office:spreadsheet'}
            
            # Variable para almacenar el número de serie del sensor
            sensor_serial = None
            
            # Encontrar todas las worksheets (productos)
            worksheets = root.findall('.//ss:Worksheet', ns)
            
            for worksheet in worksheets:
                product_name = worksheet.get('{urn:schemas-microsoft-com:office:spreadsheet}Name')
                
                # Saltar hojas que no son productos
                if product_name in ['Espectros', 'Summary'] or product_name is None:
                    continue
                
                # Extraer datos de la tabla
                table = worksheet.find('.//ss:Table', ns)
                if table is None:
                    continue
                
                rows = table.findall('.//ss:Row', ns)
                
                # Encontrar la fila de encabezado
                headers = []
                data_rows = []
                start_data = False
                
                for row in rows:
                    cells = row.findall('.//ss:Cell', ns)
                    row_data = []
                    
                    for cell in cells:
                        data_elem = cell.find('.//ss:Data', ns)
                        if data_elem is not None:
                            row_data.append(data_elem.text)
                        else:
                            row_data.append(None)
                    
                    # Detectar fila de encabezado
                    # Buscar fila que contenga las columnas clave: ID, Note, Product
                    if (not start_data and row_data and 
                        'ID' in row_data and 'Note' in row_data and 
                        ('Product' in row_data or 'Method' in row_data)):
                        headers = row_data
                        # Normalizar el nombre de la primera columna a "No"
                        if headers[0] in ['#', 'No']:
                            headers[0] = 'No'
                        start_data = True
                        continue
                    
                    # Recoger filas de datos (antes de "Average", "Min", "Max", etc.)
                    if start_data and row_data:
                        # Verificar si es una fila de datos (primera columna es número)
                        if row_data[0] and str(row_data[0]).replace('.', '').isdigit():
                            data_rows.append(row_data)
                            
                            # Extraer número de serie del sensor (columna Unit) de la primera fila
                            if sensor_serial is None and 'Unit' in headers:
                                unit_idx = headers.index('Unit')
                                if unit_idx < len(row_data) and row_data[unit_idx]:
                                    sensor_serial = row_data[unit_idx]
                        # Verificar si llegamos a las filas de estadísticas
                        elif len(row_data) > 1 and row_data[1] in ['Average', 'Min', 'Max', 'Std.Dev.', 'Target']:
                            break
                
                # Crear DataFrame
                if headers and data_rows:
                    # Asegurar que todas las filas tengan la misma longitud
                    max_len = len(headers)
                    data_rows = [row + [None] * (max_len - len(row)) if len(row) < max_len else row[:max_len] 
                                for row in data_rows]
                    
                    df = pd.DataFrame(data_rows, columns=headers)
                    
                    # Convertir columnas numéricas
                    for col in df.columns:
                        if col not in ['No', 'ID', 'Note', 'Product', 'Method', 'Unit']:
                            try:
                                df[col] = pd.to_numeric(df[col], errors='coerce')
                            except:
                                pass
                    
                    self.data[product_name] = df
                    self.products.append(product_name)
            
            # Guardar el número de serie del sensor
            self.sensor_serial = sensor_serial
            
            return True
            
        except Exception as e:
            st.error(f"Error al parsear el archivo XML: {str(e)}")
            return False
    
    def get_id_note_combinations(self, products):
        """Obtener combinaciones únicas de ID y Note para productos seleccionados"""
        combinations = set()
        
        for product in products:
            if product in self.data:
                df = self.data[product]
                for _, row in df.iterrows():
                    id_val = row.get('ID', '')
                    note_val = row.get('Note', '')
                    if pd.notna(id_val) and pd.notna(note_val):
                        combinations.add((id_val, note_val))
        
        return sorted(list(combinations))
    
    def filter_data(self, products, id_note_combinations):
        """Filtrar datos por productos y combinaciones ID-Note"""
        filtered_data = {}
        
        for product in products:
            if product not in self.data:
                continue
                
            df = self.data[product].copy()
            
            # Filtrar por combinaciones ID-Note
            mask = pd.Series([False] * len(df))
            for id_val, note_val in id_note_combinations:
                mask |= ((df['ID'] == id_val) & (df['Note'] == note_val))
            
            filtered_df = df[mask]
            
            if not filtered_df.empty:
                filtered_data[product] = filtered_df
        
        return filtered_data
    
    def calculate_statistics(self, filtered_data):
        """Calcular estadísticas por producto y lámpara (Note)"""
        stats = {}
        
        for product, df in filtered_data.items():
            product_stats = {}
            
            # Agrupar por Note (lámpara)
            for note in df['Note'].unique():
                note_df = df[df['Note'] == note]
                
                note_stats = {
                    'n': len(note_df),
                    'note': note
                }
                
                # Calcular media y std para cada parámetro numérico
                numeric_cols = note_df.select_dtypes(include=[np.number]).columns
                
                for col in numeric_cols:
                    if col != 'No':
                        values = note_df[col].dropna()
                        if len(values) > 0:
                            note_stats[col] = {
                                'mean': values.mean(),
                                'std': values.std(),
                                'min': values.min(),
                                'max': values.max(),
                                'values': values.tolist()
                            }
                
                product_stats[note] = note_stats
            
            stats[product] = product_stats
        
        return stats

def load_buchi_css():
    """Carga el CSS corporativo de BUCHI"""
    try:
        with open('buchi_report_styles_simple.css', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        # CSS inline completo como fallback
        return """
            /* Estilos globales Streamlit */
            .main .block-container {
                padding-top: 2rem;
                max-width: 1400px;
            }
            
            /* Sidebar corporativo */
            [data-testid="stSidebar"] {
                background: linear-gradient(180deg, #093A34 0%, #064d45 100%);
            }
            
            [data-testid="stSidebar"] h1, 
            [data-testid="stSidebar"] h2, 
            [data-testid="stSidebar"] h3,
            [data-testid="stSidebar"] label,
            [data-testid="stSidebar"] .stMarkdown {
                color: white !important;
            }
            
            /* Botones corporativos */
            .stButton > button {
                background: linear-gradient(135deg, #093A34 0%, #64B445 100%);
                color: white !important;
                border: none;
                border-radius: 5px;
                padding: 0.75rem 2rem;
                font-weight: 600;
                transition: all 0.3s;
            }
            
            .stButton > button:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(100, 180, 69, 0.4);
            }
            
            /* Info boxes */
            .stAlert {
                border-radius: 8px;
                border-left: 4px solid #64B445;
            }
            
            /* Tabs corporativos */
            .stTabs [data-baseweb="tab-list"] {
                gap: 8px;
                background-color: #f8f9fa;
                padding: 0.5rem;
                border-radius: 8px;
            }
            
            .stTabs [data-baseweb="tab"] {
                background-color: white;
                border-radius: 5px;
                color: #093A34;
                font-weight: 600;
                padding: 0.75rem 1.5rem;
            }
            
            .stTabs [aria-selected="true"] {
                background: linear-gradient(135deg, #093A34 0%, #64B445 100%);
                color: white !important;
            }
            
            /* Tablas */
            .dataframe thead tr th {
                background-color: #093A34 !important;
                color: white !important;
                font-weight: 600 !important;
            }
            
            /* Expanders */
            .streamlit-expanderHeader {
                background-color: #f8f9fa;
                border-radius: 5px;
                color: #093A34;
                font-weight: 600;
            }
            
            /* Métricas */
            [data-testid="stMetricValue"] {
                color: #093A34;
                font-size: 2rem;
                font-weight: bold;
            }
            
            /* Spinners */
            .stSpinner > div {
                border-top-color: #64B445 !important;
            }
        """


def wrap_chart_in_expandable(chart_html, title, chart_id, default_open=True):
    """
    Envuelve un gráfico en un elemento expandible HTML con estilo BUCHI.
    """
    open_attr = "open" if default_open else ""
    
    return f"""
    <details {open_attr} style="margin: 20px 0; border: 1px solid #ddd; border-radius: 5px; padding: 10px; background-color: white;">
        <summary style="cursor: pointer; font-weight: bold; padding: 10px; background-color: #f8f9fa; border-radius: 5px; user-select: none; color: #093A34;">
            📊 {title}
        </summary>
        <div style="padding: 15px; margin-top: 10px;">
            {chart_html}
        </div>
    </details>
    """

def generate_html_header():
    """Genera el encabezado HTML con sidebar BUCHI"""
    
    # Definir secciones del índice EN EL ORDEN CORRECTO
    sections = [
        ("info-general", "Información General"),
        ("statistics", "Estadísticas Detalladas"),
        ("comparison-charts", "Gráficos Comparativos"),
        ("differences-by-product", "Diferencias por Producto"),
        ("text-report", "Reporte en Texto")
    ]
    
    sidebar_items = "\n".join(
        f'<li><a href="#{section_id}">{section_name}</a></li>'
        for section_id, section_name in sections
    )
    
    html = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Reporte de Predicciones NIR - BUCHI</title>
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        <style>
            {load_buchi_css()}
        </style>
    </head>
    <body>
        <div class="sidebar">
            <ul>
                {sidebar_items}
            </ul>
        </div>
        
        <div class="main-content">
    """
    
    return html
    
def create_comparison_plots(stats):
    """Crear gráficos comparativos entre lámparas para todos los parámetros"""
    
    # Preparar datos para gráficos
    products = list(stats.keys())
    
    # Obtener todas las lámparas
    lamps = set()
    for product_stats in stats.values():
        lamps.update(product_stats.keys())
    
    lamps = sorted(list(lamps))
    
    if len(lamps) < 2:
        st.warning("Se necesitan al menos 2 lámparas diferentes para comparar.")
        return None
    
    # Selector de producto
    st.markdown("### Configuración de comparación")
    selected_product = st.selectbox(
        "Selecciona el producto a visualizar:",
        products,
        key='comparison_product'
    )
    
    # Verificar que el producto tenga lámparas disponibles
    if selected_product not in stats or not stats[selected_product]:
        st.warning(f"No hay datos disponibles para {selected_product}")
        return None
    
    available_lamps_for_product = sorted(list(stats[selected_product].keys()))
    
    # Selector de lámparas (hasta 4)
    st.markdown("#### Selecciona las lámparas a comparar (mínimo 2, máximo 4)")
    
    col1, col2, col3, col4 = st.columns(4)
    
    selected_lamps = []
    
    with col1:
        lamp1 = st.selectbox("Lámpara 1:", available_lamps_for_product, key='comp_lamp1')
        selected_lamps.append(lamp1)
    
    with col2:
        available_for_lamp2 = [l for l in available_lamps_for_product if l != lamp1]
        if available_for_lamp2:
            lamp2 = st.selectbox("Lámpara 2:", available_for_lamp2, key='comp_lamp2')
            selected_lamps.append(lamp2)
    
    with col3:
        available_for_lamp3 = [l for l in available_lamps_for_product if l not in selected_lamps]
        if len(available_for_lamp3) > 0:
            lamp3_options = ["(ninguna)"] + available_for_lamp3
            lamp3 = st.selectbox("Lámpara 3 (opcional):", lamp3_options, key='comp_lamp3')
            if lamp3 != "(ninguna)":
                selected_lamps.append(lamp3)
    
    with col4:
        available_for_lamp4 = [l for l in available_lamps_for_product if l not in selected_lamps]
        if len(available_for_lamp4) > 0:
            lamp4_options = ["(ninguna)"] + available_for_lamp4
            lamp4 = st.selectbox("Lámpara 4 (opcional):", lamp4_options, key='comp_lamp4')
            if lamp4 != "(ninguna)":
                selected_lamps.append(lamp4)
    
    if len(selected_lamps) < 2:
        st.warning("Por favor selecciona al menos 2 lámparas para comparar.")
        return None
    
    # Obtener todos los parámetros disponibles para el producto seleccionado
    all_params = set()
    for lamp in selected_lamps:
        if lamp in stats[selected_product]:
            all_params.update([k for k in stats[selected_product][lamp].keys() if k not in ['n', 'note']])
    
    all_params = sorted(list(all_params))
    
    if not all_params:
        st.warning("No se encontraron parámetros para comparar.")
        return None
    
    # Usar la primera lámpara como baseline
    baseline_lamp = selected_lamps[0]
    comparison_lamps = selected_lamps[1:]
    
    # Calcular diferencias para cada lámpara comparada con el baseline
    # differences[param][lamp] = valor de diferencia
    differences = {param: {} for param in all_params}
    
    for param in all_params:
        if param in stats[selected_product][baseline_lamp]:
            baseline_value = stats[selected_product][baseline_lamp][param]['mean']
            
            for lamp in comparison_lamps:
                if lamp in stats[selected_product] and param in stats[selected_product][lamp]:
                    lamp_value = stats[selected_product][lamp][param]['mean']
                    diff = lamp_value - baseline_value
                    differences[param][lamp] = diff
    
    # Filtrar parámetros que tienen al menos un valor
    params_with_data = [p for p in all_params if any(differences[p].values() if differences[p] else [])]
    
    if not params_with_data:
        st.warning("No hay datos suficientes para comparar entre las lámparas seleccionadas.")
        return None
    
    # Calcular número de filas y columnas para subplots
    n_params = len(params_with_data)
    n_cols = min(3, n_params)  # Máximo 3 columnas
    n_rows = (n_params + n_cols - 1) // n_cols  # Redondear hacia arriba
    
    # Crear subplots
    fig = make_subplots(
        rows=n_rows, 
        cols=n_cols,
        subplot_titles=[f'{param}' for param in params_with_data],
        vertical_spacing=0.15,
        horizontal_spacing=0.10
    )
    
    # Colores para cada lámpara
    lamp_colors = {}
    color_palette = ['#FF6B6B', '#4ECDC4', '#95E1D3']  # Rojo, Turquesa, Verde claro
    
    for idx, lamp in enumerate(comparison_lamps):
        lamp_colors[lamp] = color_palette[idx] if idx < len(color_palette) else '#95A5A6'
    
    for idx, param in enumerate(params_with_data):
        row = idx // n_cols + 1
        col = idx % n_cols + 1
        
        # Obtener valores de diferencia para este parámetro
        lamps_list = list(differences[param].keys())
        values = list(differences[param].values())
        
        if not values:
            continue
        
        # Crear barras para cada lámpara comparada
        for lamp_idx, lamp in enumerate(lamps_list):
            if lamp in differences[param]:
                value = differences[param][lamp]
                color = lamp_colors.get(lamp, '#95A5A6')
                
                fig.add_trace(
                    go.Bar(
                        name=lamp,
                        x=[lamp],
                        y=[value],
                        marker=dict(color=color),
                        text=[f"{value:+.3f}"],
                        textposition='inside',
                        textfont=dict(color='white', size=10),
                        showlegend=(idx == 0),  # Solo mostrar leyenda en el primer gráfico
                        legendgroup=lamp
                    ),
                    row=row, col=col
                )
        
        # Configurar eje Y independiente para cada parámetro
        # Calcular rango simétrico alrededor de cero
        if values:
            max_abs = max(abs(v) for v in values)
            y_range = [-max_abs * 1.2, max_abs * 1.2]  # 20% de margen
            
            fig.update_yaxes(
                title_text=f"Δ (%)",
                row=row, 
                col=col,
                range=y_range,
                zeroline=True,
                zerolinewidth=2,
                zerolinecolor='black'
            )
        
        fig.update_xaxes(title_text="", row=row, col=col)
    
    # Configurar layout
    fig.update_layout(
        height=300 * n_rows,
        title_text=f"<b>{selected_product}</b> - Diferencias respecto a {baseline_lamp}",
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.15,
            xanchor="center",
            x=0.5,
            title=dict(text="Lámparas comparadas:")
        ),
        barmode='group'
    )
    
    return fig


def create_detailed_comparison(stats, param='H'):
    """Crear gráfico de comparación detallada por producto"""
    
    products = list(stats.keys())
    lamps = set()
    for product_stats in stats.values():
        lamps.update(product_stats.keys())
    lamps = sorted(list(lamps))
    
    # Filtrar productos que tienen datos para el parámetro seleccionado
    products_with_data = []
    for product in products:
        has_data = False
        for lamp in lamps:
            if lamp in stats[product] and param in stats[product][lamp]:
                has_data = True
                break
        if has_data:
            products_with_data.append(product)
    
    if not products_with_data:
        st.warning(f"No hay datos disponibles para el parámetro {param}")
        return None
    
    # Calcular valor máximo para ajustar escala Y
    max_val = 0
    for product in products_with_data:
        for lamp in lamps:
            if lamp in stats[product] and param in stats[product][lamp]:
                max_val = max(max_val, stats[product][lamp][param]['mean'])
    
    # Número de subplots
    n_products = len(products_with_data)
    
    fig = make_subplots(
        rows=1, cols=n_products,
        subplot_titles=[f"{prod} - {param}" for prod in products_with_data]
    )
    
    colors = px.colors.qualitative.Plotly
    
    for col_idx, product in enumerate(products_with_data):
        for lamp_idx, lamp in enumerate(lamps):
            if lamp in stats[product]:
                if param in stats[product][lamp]:
                    mean_val = stats[product][lamp][param]['mean']
                    
                    fig.add_trace(
                        go.Bar(
                            name=lamp,
                            x=[lamp],
                            y=[mean_val],
                            marker=dict(color=colors[lamp_idx % len(colors)]),
                            showlegend=(col_idx == 0),
                            text=[f"{mean_val:.2f}"],
                            textposition='inside'
                        ),
                        row=1, col=col_idx+1
                    )
        
        fig.update_yaxes(
            title_text=f"{param} (%)", 
            row=1, 
            col=col_idx+1,
            range=[0, max_val * 1.15]
        )
    
    fig.update_layout(
        height=400,
        title_text=f"Comparación Detallada: Media y Variabilidad por Lámpara - {param}",
        showlegend=True,
        barmode='group'
    )
    
    return fig

def get_params_in_original_order(analyzer, products):
    """Obtener parámetros en el orden original del archivo XML"""
    params_order = []
    
    # Usar el primer producto para obtener el orden de columnas
    for product in products:
        if product in analyzer.data:
            df = analyzer.data[product]
            # Excluir columnas no numéricas y metadatos
            excluded_cols = ['No', 'ID', 'Note', 'Product', 'Method', 'Unit', 'Begin', 'End', 'Length']
            # También excluir las columnas que son nombres de productos
            if len(df.columns) > 1:
                excluded_cols.append(df.columns[1])
            
            params = [col for col in df.columns if col not in excluded_cols]
            params_order.extend([p for p in params if p not in params_order])
    
    return params_order


def create_box_plots(stats, analyzer):
    """Crear box plots para todos los productos y parámetros"""
    
    products = list(stats.keys())
    
    # Obtener parámetros en orden original
    params = get_params_in_original_order(analyzer, products)
    
    # Permitir selección de parámetros
    selected_params = st.multiselect(
        "Selecciona parámetros para visualizar en box plots:",
        params,
        default=params[:2] if len(params) >= 2 else params,
        key='boxplot_params'
    )
    
    if not selected_params:
        return None
    
    colors = px.colors.qualitative.Plotly
    lamps = set()
    for product_stats in stats.values():
        lamps.update(product_stats.keys())
    lamps = sorted(list(lamps))
    
    # Para cada parámetro, verificar qué productos tienen datos
    params_products_data = {}
    for param in selected_params:
        products_with_data = []
        for product in products:
            has_data = False
            for lamp in lamps:
                if lamp in stats[product] and param in stats[product][lamp]:
                    has_data = True
                    break
            if has_data:
                products_with_data.append(product)
        
        if products_with_data:
            params_products_data[param] = products_with_data
    
    if not params_products_data:
        st.warning("No hay datos disponibles para los parámetros seleccionados")
        return None
    
    # Calcular estructura de subplots
    total_subplots = sum(len(prods) for prods in params_products_data.values())
    n_params = len(params_products_data)
    max_products = max(len(prods) for prods in params_products_data.values())
    
    fig = make_subplots(
        rows=n_params, 
        cols=max_products,
        subplot_titles=[],  # Los añadiremos manualmente
        vertical_spacing=0.1,
        horizontal_spacing=0.05
    )
    
    row_idx = 0
    for param in selected_params:
        if param not in params_products_data:
            continue
            
        row_idx += 1
        products_with_data = params_products_data[param]
        
        for col_idx, product in enumerate(products_with_data):
            # Añadir título manualmente
            fig.layout.annotations[0 if row_idx == 1 and col_idx == 0 else len(fig.layout.annotations)].update(
                text=f"{product}"
            ) if len(fig.layout.annotations) > 0 else None
            
            for lamp_idx, lamp in enumerate(lamps):
                if lamp in stats[product] and param in stats[product][lamp]:
                    values = stats[product][lamp][param]['values']
                    
                    fig.add_trace(
                        go.Box(
                            name=lamp,
                            y=values,
                            marker=dict(color=colors[lamp_idx % len(colors)]),
                            showlegend=(row_idx == 1 and col_idx == 0),
                            boxmean='sd'
                        ),
                        row=row_idx, col=col_idx+1
                    )
            
            # Actualizar etiquetas
            if col_idx == 0:
                fig.update_yaxes(title_text=f"{param} (%)", row=row_idx, col=col_idx+1)
    
    # Añadir títulos de subplot correctamente
    titles = []
    for param in selected_params:
        if param in params_products_data:
            for product in params_products_data[param]:
                titles.append(f"{product} - {param}")
    
    fig = make_subplots(
        rows=n_params, 
        cols=max_products,
        subplot_titles=titles if len(titles) <= n_params * max_products else None,
        vertical_spacing=0.1,
        horizontal_spacing=0.05
    )
    
    # Recrear trazas con estructura correcta
    row_idx = 0
    for param in selected_params:
        if param not in params_products_data:
            continue
            
        row_idx += 1
        products_with_data = params_products_data[param]
        
        for col_idx, product in enumerate(products_with_data):
            for lamp_idx, lamp in enumerate(lamps):
                if lamp in stats[product] and param in stats[product][lamp]:
                    values = stats[product][lamp][param]['values']
                    
                    fig.add_trace(
                        go.Box(
                            name=lamp,
                            y=values,
                            marker=dict(color=colors[lamp_idx % len(colors)]),
                            showlegend=(row_idx == 1 and col_idx == 0),
                            boxmean='sd'
                        ),
                        row=row_idx, col=col_idx+1
                    )
            
            if col_idx == 0:
                fig.update_yaxes(title_text=f"{param} (%)", row=row_idx, col=col_idx+1)
    
    fig.update_layout(
        height=300 * n_params,
        title_text="Comparación de Predicciones por Lámpara",
        showlegend=True
    )
    
    return fig


def create_scatter_plots(stats):
    """Crear scatter plots H vs PB"""
    
    products = list(stats.keys())
    lamps = set()
    for product_stats in stats.values():
        lamps.update(product_stats.keys())
    lamps = sorted(list(lamps))
    
    # Buscar parámetros H y PB (o similares)
    param_h = None
    param_pb = None
    
    for product_stats in stats.values():
        for lamp_stats in product_stats.values():
            for param in lamp_stats.keys():
                if param not in ['n', 'note']:
                    if 'H' in param.upper() and param_h is None:
                        param_h = param
                    if 'PB' in param.upper() or 'PROTEIN' in param.upper():
                        param_pb = param
    
    if param_h is None or param_pb is None:
        st.warning("No se encontraron parámetros de Humedad (H) y Proteína (PB)")
        return None
    
    n_products = len(products)
    
    fig = make_subplots(
        rows=1, cols=n_products,
        subplot_titles=[f"{prod} - {param_h} vs {param_pb}" for prod in products]
    )
    
    colors = px.colors.qualitative.Plotly
    
    for col_idx, product in enumerate(products):
        for lamp_idx, lamp in enumerate(lamps):
            if lamp in stats[product]:
                if param_h in stats[product][lamp] and param_pb in stats[product][lamp]:
                    h_values = stats[product][lamp][param_h]['values']
                    pb_values = stats[product][lamp][param_pb]['values']
                    
                    fig.add_trace(
                        go.Scatter(
                            name=lamp,
                            x=h_values,
                            y=pb_values,
                            mode='markers',
                            marker=dict(
                                color=colors[lamp_idx % len(colors)],
                                size=10,
                                line=dict(width=1, color='white')
                            ),
                            showlegend=(col_idx == 0)
                        ),
                        row=1, col=col_idx+1
                    )
        
        fig.update_xaxes(title_text=f"{param_h} (%)", row=1, col=col_idx+1)
        if col_idx == 0:
            fig.update_yaxes(title_text=f"{param_pb} (%)", row=1, col=col_idx+1)
    
    fig.update_layout(
        height=400,
        title_text=f"{param_h} vs {param_pb}",
        showlegend=True
    )
    
    return fig

def calculate_lamp_differences(stats, analyzer):
    """
    Calcula diferencias entre lámparas para cada producto de forma estructurada.
    
    Returns:
        dict: {
            'Producto A': {
                'baseline_lamp': 'W-2024-001',
                'comparisons': [
                    {
                        'lamp': 'W-2025-002',
                        'n_baseline': 10,
                        'n_compared': 12,
                        'differences': {
                            'H': {
                                'baseline_mean': 10.5,
                                'compared_mean': 10.7,
                                'absolute_diff': 0.2,
                                'percent_diff': 1.9
                            },
                            'PB': {...}
                        }
                    }
                ]
            }
        }
    """
    differences_by_product = {}
    
    for product, product_stats in stats.items():
        # Usar primera lámpara como baseline
        lamps = sorted(list(product_stats.keys()))
        
        if len(lamps) < 2:
            continue  # Necesitamos al menos 2 lámparas para comparar
        
        baseline_lamp = lamps[0]
        comparison_lamps = lamps[1:]
        
        # Obtener parámetros en orden original
        if product in analyzer.data:
            df = analyzer.data[product]
            excluded_cols = ['No', 'ID', 'Note', 'Product', 'Method', 'Unit', 'Begin', 'End', 'Length']
            if len(df.columns) > 1:
                excluded_cols.append(df.columns[1])
            params = [col for col in df.columns if col not in excluded_cols]
        else:
            params = set()
            for lamp_stats in product_stats.values():
                params.update([k for k in lamp_stats.keys() if k not in ['n', 'note']])
            params = sorted(list(params))
        
        # Estructura de comparaciones
        comparisons = []
        
        for comp_lamp in comparison_lamps:
            comparison = {
                'lamp': comp_lamp,
                'n_baseline': product_stats[baseline_lamp]['n'],
                'n_compared': product_stats[comp_lamp]['n'],
                'differences': {}
            }
            
            for param in params:
                if (param in product_stats[baseline_lamp] and 
                    param in product_stats[comp_lamp]):
                    
                    baseline_mean = product_stats[baseline_lamp][param]['mean']
                    compared_mean = product_stats[comp_lamp][param]['mean']
                    
                    abs_diff = compared_mean - baseline_mean
                    percent_diff = (abs_diff / baseline_mean * 100) if baseline_mean != 0 else 0
                    
                    comparison['differences'][param] = {
                        'baseline_mean': baseline_mean,
                        'compared_mean': compared_mean,
                        'absolute_diff': abs_diff,
                        'percent_diff': percent_diff
                    }
            
            comparisons.append(comparison)
        
        differences_by_product[product] = {
            'baseline_lamp': baseline_lamp,
            'comparisons': comparisons
        }
    
    return differences_by_product

def generate_differences_section(differences_data):
    """
    Genera HTML para la sección de diferencias por producto.
    
    Args:
        differences_data: Salida de calculate_lamp_differences()
        
    Returns:
        str: HTML con visualización de diferencias
    """
    
    html = """
    <div class="info-box" id="differences-by-product">
        <h2>📊 Diferencias por Producto</h2>
        <p style='color: #6c757d; font-size: 0.95em; margin-bottom: 25px;'>
            <em>Análisis comparativo detallado entre lámparas para cada producto. 
            Se muestra la diferencia absoluta y porcentual de cada parámetro respecto 
            a la lámpara baseline (primera lámpara seleccionada).</em>
        </p>
    """
    
    for product, product_data in differences_data.items():
        baseline_lamp = product_data['baseline_lamp']
        comparisons = product_data['comparisons']
        
        html += f"""
        <div style="margin-bottom: 40px; padding: 20px; background-color: #f8f9fa; border-radius: 8px; border-left: 4px solid #64B445;">
            <h3 style="margin-top: 0; color: #093A34;">🔬 {product}</h3>
            <p style="color: #6c757d; font-size: 0.9em; margin-bottom: 20px;">
                <strong>Lámpara Baseline:</strong> {baseline_lamp} 
                (N = {comparisons[0]['n_baseline'] if comparisons else 'N/A'})
            </p>
        """
        
        for comparison in comparisons:
            comp_lamp = comparison['lamp']
            n_compared = comparison['n_compared']
            differences = comparison['differences']
            
            # Crear tabla de diferencias
            html += f"""
            <details open style="margin-bottom: 20px; border: 1px solid #dee2e6; border-radius: 5px; background-color: white;">
                <summary style="cursor: pointer; padding: 15px; background-color: #e9ecef; border-radius: 5px; user-select: none; font-weight: bold;">
                    📍 {comp_lamp} vs {baseline_lamp} (N = {n_compared})
                </summary>
                
                <div style="padding: 20px;">
                    <table style="width: 100%;">
                        <thead>
                            <tr>
                                <th style="text-align: left;">Parámetro</th>
                                <th style="text-align: center;">{baseline_lamp}<br/><span style="font-weight: normal; font-size: 0.85em;">(Baseline)</span></th>
                                <th style="text-align: center;">{comp_lamp}<br/><span style="font-weight: normal; font-size: 0.85em;">(Comparada)</span></th>
                                <th style="text-align: center;">Δ Absoluta</th>
                                <th style="text-align: center;">Δ Relativa (%)</th>
                                <th style="text-align: center;">Evaluación</th>
                            </tr>
                        </thead>
                        <tbody>
            """
            
            # Ordenar parámetros por diferencia absoluta (mayor a menor)
            sorted_params = sorted(
                differences.items(), 
                key=lambda x: abs(x[1]['absolute_diff']), 
                reverse=True
            )
            
            for param, diff_data in sorted_params:
                baseline_val = diff_data['baseline_mean']
                compared_val = diff_data['compared_mean']
                abs_diff = diff_data['absolute_diff']
                percent_diff = diff_data['percent_diff']
                
                # Clasificar magnitud de diferencia
                abs_percent = abs(percent_diff)
                if abs_percent < 2.0:
                    evaluation = '🟢 Excelente'
                    eval_color = '#4caf50'
                elif abs_percent < 5.0:
                    evaluation = '🟡 Aceptable'
                    eval_color = '#ffc107'
                elif abs_percent < 10.0:
                    evaluation = '🟠 Revisar'
                    eval_color = '#ff9800'
                else:
                    evaluation = '🔴 Significativo'
                    eval_color = '#f44336'
                
                # Color de fondo para diferencia
                if abs_percent < 2.0:
                    row_bg = '#e8f5e9'
                elif abs_percent < 5.0:
                    row_bg = '#fff3e0'
                else:
                    row_bg = '#ffebee'
                
                # Símbolo de dirección
                direction = '↑' if abs_diff > 0 else '↓' if abs_diff < 0 else '='
                
                html += f"""
                    <tr style="background-color: {row_bg};">
                        <td style="font-weight: bold;">{param}</td>
                        <td style="text-align: center;">{baseline_val:.3f}</td>
                        <td style="text-align: center;">{compared_val:.3f}</td>
                        <td style="text-align: center; font-weight: bold;">{direction} {abs(abs_diff):.3f}</td>
                        <td style="text-align: center; font-weight: bold; color: {eval_color};">
                            {abs_diff:+.3f} ({percent_diff:+.2f}%)
                        </td>
                        <td style="text-align: center; color: {eval_color}; font-weight: bold;">
                            {evaluation}
                        </td>
                    </tr>
                """
            
            html += """
                        </tbody>
                    </table>
                    
                    <div style="margin-top: 15px; padding: 10px; background-color: #f1f3f4; border-radius: 5px;">
                        <strong>📌 Leyenda de Evaluación:</strong>
                        <ul style="margin: 10px 0 0 20px; font-size: 0.9em;">
                            <li><strong>🟢 Excelente:</strong> Δ < 0.5% - Diferencia despreciable</li>
                            <li><strong>🟡 Aceptable:</strong> 0.5% ≤ Δ < 2% - Dentro del rango esperado</li>
                            <li><strong>🟠 Revisar:</strong> 2% ≤ Δ < 5% - Diferencia notable, revisar causas</li>
                            <li><strong>🔴 Significativo:</strong> Δ ≥ 5% - Diferencia importante, requiere investigación</li>
                        </ul>
                    </div>
                </div>
            </details>
            """
        
        html += """
        </div>
        """
    
    html += """
    </div>
    """
    
    return html

def generate_html_report(stats, analyzer, filename):
    """
    Generar reporte HTML completo con estilo corporativo BUCHI.
    """
    
    # Obtener información general
    products = list(stats.keys())
    all_lamps = set()
    for product_stats in stats.values():
        all_lamps.update(product_stats.keys())
    all_lamps = sorted(list(all_lamps))
    
    sensor_serial = analyzer.sensor_serial if analyzer.sensor_serial else "N/A"
    timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    
    # ============================================
    # HEADER CON SIDEBAR
    # ============================================
    html = generate_html_header()
    
    # ============================================
    # TÍTULO PRINCIPAL
    # ============================================
    html += f"""
        <h1>Reporte de Predicciones NIR</h1>
        
        <div class="info-box" id="info-general">
            <h2>Información General del Análisis</h2>
            <div class="info-grid">
                <div class="info-item">
                    <span class="info-label">🔬 Sensor NIR</span>
                    <span class="info-value">{sensor_serial}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">📅 Fecha del Reporte</span>
                    <span class="info-value">{timestamp}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">📦 Productos Analizados</span>
                    <span class="info-value">{len(products)}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">💡 Lámparas Comparadas</span>
                    <span class="info-value">{len(all_lamps)}</span>
                </div>
            </div>
            
            <table style="margin-top: 20px;">
                <tr>
                    <th>Productos</th>
                    <td>{', '.join(products)}</td>
                </tr>
                <tr>
                    <th>Lámparas</th>
                    <td>{', '.join(all_lamps)}</td>
                </tr>
            </table>
        </div>
    """
    
    # ============================================
    # SECCIÓN 1: ESTADÍSTICAS POR PRODUCTO
    # ============================================
    html += """
        <div class="info-box" id="statistics">
            <h2>Estadísticas por Producto y Lámpara</h2>
            <p style='color: #6c757d; font-size: 0.95em; margin-bottom: 25px;'>
                <em>Valores promedio y desviación estándar de cada parámetro analítico 
                para cada lámpara y producto.</em>
            </p>
    """
    
    for product in products:
        # Obtener parámetros en orden original
        if product in analyzer.data:
            df = analyzer.data[product]
            excluded_cols = ['No', 'ID', 'Note', 'Product', 'Method', 'Unit', 'Begin', 'End', 'Length']
            if len(df.columns) > 1:
                excluded_cols.append(df.columns[1])
            params = [col for col in df.columns if col not in excluded_cols]
        else:
            params = set()
            for lamp_stats in stats[product].values():
                params.update([k for k in lamp_stats.keys() if k not in ['n', 'note']])
            params = sorted(list(params))
        
        html += f"""
            <h3>{product}</h3>
            <div style="overflow-x: auto;">
                <table>
                    <thead>
                        <tr>
                            <th style="text-align: left;">Lámpara</th>
                            <th>N</th>
        """
        
        for param in params:
            html += f'<th>{param}<br/><span style="font-weight: normal; font-size: 0.85em;">(Media ± SD)</span></th>'
        
        html += """
                        </tr>
                    </thead>
                    <tbody>
        """
        
        for lamp, lamp_stats in stats[product].items():
            html += f"""
                        <tr>
                            <td style="font-weight: bold; background-color: #f8f9fa;">{lamp}</td>
                            <td>{lamp_stats['n']}</td>
            """
            
            for param in params:
                if param in lamp_stats:
                    mean = lamp_stats[param]['mean']
                    std = lamp_stats[param]['std']
                    html += f'<td>{mean:.3f} ± {std:.3f}</td>'
                else:
                    html += '<td>-</td>'
            
            html += """
                        </tr>
            """
        
        html += """
                    </tbody>
                </table>
            </div>
        """
    
    html += """
        </div>
    """
    
    # ============================================
    # SECCIÓN 2: GRÁFICOS COMPARATIVOS
    # ============================================
    html += """
        <div class="info-box" id="comparison-charts">
            <h2>Gráficos Comparativos</h2>
            <p style='color: #6c757d; font-size: 0.95em;'>
                <em>Análisis visual de las predicciones NIR entre diferentes lámparas.</em>
            </p>
    """
    
    # Obtener parámetros en orden original
    params_ordered = get_params_in_original_order(analyzer, products)
    
    for param in params_ordered:
        fig = create_detailed_comparison(stats, param)
        
        if fig:
            chart_html = fig.to_html(
                include_plotlyjs=False,
                div_id=f"graph_{param.replace(' ', '_')}"
            )
            
            html += wrap_chart_in_expandable(
                chart_html,
                f"Comparación detallada: {param}",
                f"chart_{param.replace(' ', '_')}",
                default_open=True
            )
    
    html += """
        </div>
    """
    
    # ============================================
    # ⭐ SECCIÓN 3: DIFERENCIAS POR PRODUCTO (NUEVO)
    # ============================================
    differences_data = calculate_lamp_differences(stats, analyzer)
    
    if differences_data:
        html += generate_differences_section(differences_data)
    
    # ============================================
    # SECCIÓN 4: REPORTE DE TEXTO
    # ============================================
    text_report = generate_text_report(stats, analyzer)
    
    html += f"""
        <div class="info-box" id="text-report">
            <h2>Informe Detallado en Texto</h2>
            <p style='color: #6c757d; font-size: 0.95em; margin-bottom: 20px;'>
                <em>Reporte completo en formato de texto con análisis estadístico 
                y comparaciones detalladas.</em>
            </p>
            <pre style="background-color: #f8f9fa; padding: 20px; border-radius: 5px; overflow-x: auto; line-height: 1.6;">{text_report}</pre>
        </div>
    """
    
    # ============================================
    # FOOTER
    # ============================================
    html += f"""
        <div class="footer">
            <p><strong>NIR Predictions Analyzer</strong> - Desarrollado para BUCHI</p>
            <p>Reporte generado automáticamente el {timestamp}</p>
            <p style="color: #093A34; font-weight: bold;">BUCHI Labortechnik AG</p>
        </div>
    </body>
    </html>
    """
    
    return html

def generate_text_report(stats, analyzer):
    """Generar reporte de texto completo con todos los parámetros"""
    
    report = []
    report.append("=" * 120)
    report.append("INFORME COMPARATIVO DE LÁMPARAS NIR")
    report.append("Análisis de Predicciones - Reporte Completo")
    report.append("=" * 120)
    report.append("")
    report.append(f"Fecha de generación: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    
    # Información del sensor
    if analyzer.sensor_serial:
        report.append(f"Sensor NIR: {analyzer.sensor_serial}")
    
    report.append("")
    
    # Listar lámparas comparadas
    lamps = set()
    for product_stats in stats.values():
        lamps.update(product_stats.keys())
    lamps = sorted(list(lamps))
    
    report.append("LÁMPARAS COMPARADAS:")
    for lamp in lamps:
        report.append(f"  • {lamp}")
    report.append("")
    
    # Información por producto
    for product, product_stats in stats.items():
        report.append("-" * 120)
        report.append(f"PRODUCTO: {product.upper()}")
        report.append("-" * 120)
        report.append("")
        
        # Obtener TODOS los parámetros en orden original
        if product in analyzer.data:
            df = analyzer.data[product]
            excluded_cols = ['No', 'ID', 'Note', 'Product', 'Method', 'Unit', 'Begin', 'End', 'Length']
            if len(df.columns) > 1:
                excluded_cols.append(df.columns[1])
            params = [col for col in df.columns if col not in excluded_cols]
        else:
            params = set()
            for lamp_stats in product_stats.values():
                params.update([k for k in lamp_stats.keys() if k not in ['n', 'note']])
            params = sorted(list(params))
        
        report.append("RESULTADOS DE PREDICCIÓN:")
        report.append("")
        
        # Tabla de resultados por lámpara
        for lamp, lamp_stats in product_stats.items():
            report.append(f"  Lámpara: {lamp} (N={lamp_stats['n']})")
            report.append("  " + "-" * 100)
            
            for param in params:
                if param in lamp_stats:
                    mean = lamp_stats[param]['mean']
                    std = lamp_stats[param]['std']
                    min_val = lamp_stats[param]['min']
                    max_val = lamp_stats[param]['max']
                    report.append(f"    {param:<25} {mean:>10.3f} ± {std:<8.3f}   (min: {min_val:>8.3f}, max: {max_val:>8.3f})")
            
            report.append("")
        
        # Análisis de diferencias entre lámparas
        if len(lamps) >= 2:
            report.append("  ANÁLISIS DE DIFERENCIAS:")
            report.append("")
            
            # Comparar primera lámpara con las demás
            base_lamp = sorted(list(product_stats.keys()))[0]
            
            for lamp in sorted(list(product_stats.keys()))[1:]:
                report.append(f"    {lamp} vs {base_lamp} (baseline):")
                
                for param in params:
                    if param in product_stats[base_lamp] and param in product_stats[lamp]:
                        base_mean = product_stats[base_lamp][param]['mean']
                        comp_mean = product_stats[lamp][param]['mean']
                        diff = comp_mean - base_mean
                        percent_diff = (diff / base_mean * 100) if base_mean != 0 else 0
                        
                        report.append(f"      {param:<25} Δ = {diff:+.3f}  ({percent_diff:+.2f}%)")
                
                report.append("")
        
        report.append("")
    
    # Resumen estadístico general
    report.append("=" * 120)
    report.append("RESUMEN ESTADÍSTICO GENERAL")
    report.append("=" * 120)
    report.append("")
    
    for product in stats.keys():
        report.append(f"Producto: {product}")
        
        # Obtener parámetros
        if product in analyzer.data:
            df = analyzer.data[product]
            excluded_cols = ['No', 'ID', 'Note', 'Product', 'Method', 'Unit', 'Begin', 'End', 'Length']
            if len(df.columns) > 1:
                excluded_cols.append(df.columns[1])
            params = [col for col in df.columns if col not in excluded_cols]
        else:
            params = list(stats[product][list(stats[product].keys())[0]].keys())
            params = [p for p in params if p not in ['n', 'note']]
        
        for param in params[:5]:  # Primeros 5 parámetros para resumen
            report.append(f"  {param}:")
            
            # Calcular estadísticas entre lámparas
            values = []
            for lamp_stats in stats[product].values():
                if param in lamp_stats:
                    values.append(lamp_stats[param]['mean'])
            
            if values:
                overall_mean = sum(values) / len(values)
                overall_std = (sum((x - overall_mean) ** 2 for x in values) / len(values)) ** 0.5
                overall_range = max(values) - min(values)
                
                report.append(f"    Media entre lámparas: {overall_mean:.3f} ± {overall_std:.3f}")
                report.append(f"    Rango: {overall_range:.3f}")
        
        report.append("")
    
    report.append("=" * 120)
    report.append("FIN DEL INFORME")
    report.append("=" * 120)
    
    return "\n".join(report)


def main():
    """Función principal de la aplicación Streamlit"""
    
    st.set_page_config(
        page_title="NIR Predictions Analyzer",
        page_icon="🔬",
        layout="wide"
    )
    
    # ⭐ NUEVO: Cargar estilos CSS corporativos
    st.markdown(f"""
    <style>
        {load_buchi_css()}
    </style>
    """, unsafe_allow_html=True)
    

    
    # ⭐ Aplicar estilos corporativos BUCHI
    apply_buchi_styles()

    # ⭐ Header simple y limpio (sin gradiente)
    st.markdown(f"""
    <div style="background-color: {BUCHI_COLORS['gris_claro']}; 
                padding: 2rem; 
                border-radius: 10px; 
                margin-bottom: 2rem; 
                text-align: center;">
        <h1 style="color: white !important; margin: 0; font-size: 2.5rem;">
            🔬 NIR Predictions Analyzer
        </h1>
        <p style="color: white !important; margin: 0.5rem 0 0 0; font-size: 1.1rem; opacity: 0.9;">
            Análisis Comparativo de Lámparas NIR
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Inicializar session state
    if 'analyzer' not in st.session_state:
        st.session_state.analyzer = None
    if 'filtered_data' not in st.session_state:
        st.session_state.filtered_data = None
    if 'stats' not in st.session_state:
        st.session_state.stats = None
    
    # Sidebar para configuración
    with st.sidebar:
        st.header("⚙️ Configuración")
        
        # Upload de archivo
        uploaded_file = st.file_uploader(
            "Cargar archivo XML de reporte NIR",
            type=['xml'],
            help="Archivo XML generado por el software NIR-Online"
        )
        
        if uploaded_file is not None:
            if st.button("📊 Cargar y Analizar"):
                with st.spinner("Procesando archivo XML..."):
                    analyzer = NIRAnalyzer()
                    if analyzer.parse_xml(uploaded_file):
                        st.session_state.analyzer = analyzer
                        st.success(f"✅ Archivo cargado correctamente!")
                        st.info(f"Productos encontrados: {len(analyzer.products)}")
        
        # Botón de descarga de reporte HTML (solo si hay estadísticas)
        if st.session_state.stats is not None and st.session_state.analyzer is not None:
            st.markdown("---")
            st.subheader("📥 Descargar Reporte")
            
            # Generar nombre del archivo
            analyzer = st.session_state.analyzer
            stats = st.session_state.stats
            
            # Obtener lámparas seleccionadas
            all_lamps = set()
            for product_stats in stats.values():
                all_lamps.update(product_stats.keys())
            lamps_str = "_".join(sorted(all_lamps))
            
            # Obtener número de serie
            sensor_serial = analyzer.sensor_serial if analyzer.sensor_serial else "sensor"
            
            # Timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Nombre del archivo
            filename = f"Predictions_Report_{sensor_serial}_{lamps_str}_{timestamp}.html"
            
            if st.button("💾 Generar y Descargar Reporte HTML"):
                with st.spinner("Generando reporte HTML..."):
                    # Generar HTML completo con todos los gráficos
                    html_content = generate_html_report(stats, analyzer, filename)
                    
                    st.download_button(
                        label="⬇️ Descargar Reporte HTML",
                        data=html_content,
                        file_name=filename,
                        mime="text/html"
                    )
    
    # Contenido principal
    if st.session_state.analyzer is not None:
        analyzer = st.session_state.analyzer
        
        # Mostrar número de serie del sensor
        if analyzer.sensor_serial:
            st.info(f"🔬 **Sensor NIR:** {analyzer.sensor_serial}")
        
        st.success(f"📦 Productos disponibles: {', '.join(analyzer.products)}")
        
        # Selección de productos
        st.subheader("1️⃣ Selección de Productos")
        selected_products = st.multiselect(
            "Selecciona los productos a analizar:",
            analyzer.products,
            default=analyzer.products
        )
        
        if selected_products:
            # Obtener IDs y Notes únicos
            all_ids = set()
            all_notes = set()
            
            for product in selected_products:
                if product in analyzer.data:
                    df = analyzer.data[product]
                    all_ids.update(df['ID'].dropna().unique())
                    all_notes.update(df['Note'].dropna().unique())
            
            all_ids = sorted(list(all_ids))
            all_notes = sorted(list(all_notes))
            
            st.subheader("2️⃣ Selección de IDs y Lámparas (Notes)")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.info(f"💡 {len(all_ids)} IDs disponibles")
                selected_ids = st.multiselect(
                    "Selecciona los IDs:",
                    all_ids,
                    default=all_ids
                )
            
            with col2:
                st.info(f"💡 {len(all_notes)} Lámparas (Notes) disponibles")
                selected_notes = st.multiselect(
                    "Selecciona las Lámparas (Notes):",
                    all_notes,
                    default=all_notes
                )
            
            # Crear combinaciones a partir de selecciones separadas
            selected_combinations = []
            for id_val in selected_ids:
                for note_val in selected_notes:
                    selected_combinations.append((id_val, note_val))
            
            if selected_combinations:
                # Botón para generar análisis
                if st.button("🚀 Generar Análisis y Gráficos", type="primary"):
                    with st.spinner("Generando análisis..."):
                        # Filtrar datos
                        filtered_data = analyzer.filter_data(selected_products, selected_combinations)
                        st.session_state.filtered_data = filtered_data
                        
                        # Calcular estadísticas
                        stats = analyzer.calculate_statistics(filtered_data)
                        st.session_state.stats = stats
                        
                        st.success("✅ Análisis completado!")
                
                # Mostrar resultados si existen
                if st.session_state.stats is not None:
                    stats = st.session_state.stats
                    
                    # Mostrar lámparas seleccionadas
                    all_lamps = set()
                    for product_stats in stats.values():
                        all_lamps.update(product_stats.keys())
                    all_lamps = sorted(list(all_lamps))
                    
                    if all_lamps:
                        st.info(f"🔬 **Lámparas seleccionadas:** {', '.join(all_lamps)}")
                    
                    st.markdown("---")
                    st.header("📊 Resultados del Análisis")
                    
                    # Tabs para diferentes visualizaciones
                    tab1, tab2, tab3, tab4 = st.tabs([
                        "📊 Comparación Detallada",
                        "📈 Diferencias entre Lámparas",
                        "📦 Box Plots",
                        "📄 Reporte de Texto"
                    ])
                    
                    with tab1:
                        st.subheader("Comparación Detallada por Producto")
                        
                        # Obtener parámetros en orden original
                        params = get_params_in_original_order(analyzer, list(stats.keys()))
                        
                        if params:
                            selected_param = st.selectbox(
                                "Selecciona el parámetro a visualizar:",
                                params,
                                key='detailed_param'
                            )
                            
                            fig_detailed = create_detailed_comparison(stats, selected_param)
                            if fig_detailed:
                                st.plotly_chart(fig_detailed, use_container_width=True)
                    
                    with tab2:
                        st.subheader("Diferencias Relativas entre Lámparas")
                        fig_diff = create_comparison_plots(stats)
                        if fig_diff:
                            st.plotly_chart(fig_diff, use_container_width=True)
                    
                    with tab3:
                        st.subheader("Distribución de Valores por Lámpara")
                        fig_box = create_box_plots(stats, analyzer)
                        if fig_box:
                            st.plotly_chart(fig_box, use_container_width=True)
                    
                    with tab4:
                        st.subheader("Informe Completo en Texto")
                        report_text = generate_text_report(stats, analyzer)
                        st.text_area("Reporte:", report_text, height=600)
                        
                        # Botón de descarga
                        st.download_button(
                            label="💾 Descargar Reporte",
                            data=report_text,
                            file_name=f"informe_nir_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                            mime="text/plain"
                        )
    
    else:
        st.info("👈 Por favor, carga un archivo XML desde la barra lateral para comenzar el análisis")
        
        # Mostrar información de ayuda
        with st.expander("ℹ️ Información de Uso"):
            st.markdown("""
            ### Cómo usar esta aplicación:
            
            1. **Cargar Archivo**: Sube un archivo XML de reporte NIR desde la barra lateral
            2. **Seleccionar Productos**: Elige los productos que quieres analizar
            3. **Seleccionar Lámparas**: Filtra las combinaciones de ID y Note (lámparas)
            4. **Generar Análisis**: Haz clic en el botón para generar los gráficos e informes
            5. **Explorar Resultados**: Navega por las diferentes pestañas para ver:
               - Diferencias relativas entre lámparas
               - Comparaciones detalladas
               - Distribuciones (box plots)
               - Relaciones entre parámetros (scatter plots)
               - Reporte completo en texto
            
            ### Formato del archivo:
            - Archivo XML generado por el software NIR-Online
            - Debe contener múltiples hojas (worksheets) con datos de productos
            - Cada hoja debe tener columnas: No, ID, Note, Product, Method, y parámetros numéricos
            """)


if __name__ == "__main__":
    main()