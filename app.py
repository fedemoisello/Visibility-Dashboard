import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import datetime
import io

# Configuración de la página
st.set_page_config(layout="wide", page_title="Dashboard Visibility", page_icon="📊")

# Estilos personalizados
st.markdown("""
<style>
    .main-header {
        font-size: 26px;
        font-weight: bold;
        color: #2c3e50;
        margin-bottom: 20px;
    }
    .sub-header {
        font-size: 20px;
        font-weight: bold;
        color: #34495e;
        margin-top: 30px;
        margin-bottom: 10px;
    }
    .metric-card {
        background-color: #f7f7f7;
        border-radius: 5px;
        padding: 15px;
        text-align: center;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    .metric-value {
        font-size: 24px;
        font-weight: bold;
        color: #3498db;
    }
    .metric-title {
        font-size: 14px;
        color: #7f8c8d;
    }
    .highlighted {
        background-color: #e8f4f8;
    }
    .st-emotion-cache-1wivap2 {
        max-height: 600px;
        overflow-y: auto;
    }
</style>
""", unsafe_allow_html=True)

# Título principal
st.markdown('<div class="main-header">Dashboard de Visibility</div>', unsafe_allow_html=True)

# Función para procesar el CSV con varios formatos posibles
@st.cache_data
def procesar_csv(file_content, delimiter=';'):
    try:
        df = pd.read_csv(io.StringIO(file_content.decode('utf-8')), delimiter=delimiter)
        
        # Intentar detectar la columna de fecha
        date_columns = [col for col in df.columns if 'date' in col.lower() or 'fecha' in col.lower()]
        date_col = date_columns[0] if date_columns else 'Date'
        
        # Intentar detectar la columna de cliente
        client_columns = [col for col in df.columns if 'client' in col.lower() or 'customer' in col.lower() or 'parent' in col.lower()]
        client_col = client_columns[0] if client_columns else 'Customer Parent'
        
        # Forzar la columna de monto a "Total USD" específicamente
        amount_col = 'Total USD'
        
        # Verificar si la columna existe
        if amount_col not in df.columns:
            # Buscar alternativas si no existe
            amount_columns = [col for col in df.columns if 'usd' in col.lower() or 'total' in col.lower() or 'amount' in col.lower()]
            amount_col = amount_columns[0] if amount_columns else 'Total'
        
        # Convertir fechas
        try:
            df[date_col] = pd.to_datetime(df[date_col], dayfirst=True, errors='coerce')
        except:
            try:
                df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
            except:
                pass
        
        # Convertir montos (considerando formato europeo con comas)
        if isinstance(df[amount_col].iloc[0], str):
            df[amount_col] = df[amount_col].str.replace('.', '').str.replace(',', '.').str.replace(' ', '')
        
        try:
            df[amount_col] = pd.to_numeric(df[amount_col], errors='coerce')
        except:
            pass
        
        # Crear columnas de fecha
        if pd.api.types.is_datetime64_dtype(df[date_col]):
            df['Año'] = df[date_col].dt.year
            df['Mes'] = df[date_col].dt.month
            df['Mes_Nombre'] = df[date_col].dt.month_name()
            df['Trimestre'] = 'Q' + df[date_col].dt.quarter.astype(str)
        
        return df, date_col, client_col, amount_col
    except Exception as e:
        st.error(f"Error al procesar el CSV: {e}")
        return None, None, None, None

# Función para generar la tabla de reporte estilo hoja de cálculo
def generar_tabla_reporte(df, client_col, date_col, amount_col):
    # Asegurarse de que las columnas de fecha estén correctas
    if 'Año' not in df.columns or 'Mes' not in df.columns or 'Trimestre' not in df.columns:
        if pd.api.types.is_datetime64_dtype(df[date_col]):
            df['Año'] = df[date_col].dt.year
            df['Mes'] = df[date_col].dt.month
            df['Mes_Nombre'] = df[date_col].dt.month_name()
            df['Trimestre'] = 'Q' + df[date_col].dt.quarter.astype(str)
    
    # Crear un pivot table
    table = pd.pivot_table(
        df,
        values=amount_col,
        index=client_col,
        columns=['Trimestre', 'Mes_Nombre'],
        aggfunc='sum',
        fill_value=0
    )
    
    # Definir el orden de los meses
    month_order = ['January', 'February', 'March', 'April', 'May', 'June', 
                   'July', 'August', 'September', 'October', 'November', 'December']
    
    # Calcular totales
    quarter_totals = {}
    for quarter in ['Q1', 'Q2', 'Q3', 'Q4']:
        if quarter in table.columns.levels[0]:  # Solo si hay datos para ese trimestre
            quarter_months = table[quarter].columns.tolist()
            if quarter_months:
                table[(quarter, 'Total')] = table[quarter].sum(axis=1)
                quarter_totals[quarter] = table[(quarter, 'Total')]
    
    # Total anual
    table[('Total', 'Anual')] = sum(quarter_totals.values())
    
    # Ordenar clientes por total anual (descendente)
    table = table.sort_values(('Total', 'Anual'), ascending=False)
    
    # Agregar fila de totales
    table.loc['Total'] = table.sum()
    
    return table

# Función para formatear valores en miles
def format_miles(x):
    if pd.isna(x) or x == 0:
        return ""
    return f"{int(round(x/1000))}K"

# Sección de carga de archivo
st.markdown('<div class="sub-header">Carga de datos</div>', unsafe_allow_html=True)

uploaded_file = st.file_uploader("Carga tu archivo CSV de Visibility", type=['csv'])

if uploaded_file is not None:
    # Determinar delimitador
    delimiter_options = [';', ',', '\t', '|']
    selected_delimiter = st.selectbox("Selecciona el delimitador", delimiter_options, index=0)
    
    file_content = uploaded_file.read()
    df, date_col, client_col, amount_col = procesar_csv(file_content, delimiter=selected_delimiter)
    
    if df is not None:
        st.success(f"Archivo cargado correctamente: {uploaded_file.name}")
        
        # Visualizar datos básicos
        st.markdown('<div class="sub-header">Vista previa de datos</div>', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f'<div class="metric-card"><div class="metric-value">{len(df)}</div><div class="metric-title">Registros totales</div></div>', unsafe_allow_html=True)
        with col2:
            st.markdown(f'<div class="metric-card"><div class="metric-value">{df[client_col].nunique()}</div><div class="metric-title">Clientes únicos</div></div>', unsafe_allow_html=True)
        with col3:
            total_amount = df[amount_col].sum()
            formatted_amount = f"${total_amount/1000000:.2f}M"
            st.markdown(f'<div class="metric-card"><div class="metric-value">{formatted_amount}</div><div class="metric-title">Total USD</div></div>', unsafe_allow_html=True)
        
        # Mostrar los primeros 5 registros
        st.dataframe(df.head())
        
        # Mostrar columnas detectadas
        st.markdown("**Columnas detectadas:**")
        st.markdown(f"- Fecha: `{date_col}`")
        st.markdown(f"- Cliente: `{client_col}`")
        st.markdown(f"- Monto: `{amount_col}`")
        
        # Filtros interactivos
        st.markdown('<div class="sub-header">Filtros</div>', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            year_options = ["Todos"] + sorted(df['Año'].dropna().unique().astype(int).astype(str).tolist())
            selected_year = st.selectbox("Año", year_options)
        
        with col2:
            quarter_options = ["Todos", "Q1", "Q2", "Q3", "Q4"]
            selected_quarter = st.selectbox("Trimestre", quarter_options)
        
        with col3:
            client_options = ["Todos"] + sorted(df[client_col].dropna().unique().tolist())
            selected_client = st.selectbox("Cliente", client_options)
        
        # Aplicar filtros
        filtered_df = df.copy()
        
        if selected_year != "Todos":
            filtered_df = filtered_df[filtered_df['Año'] == int(selected_year)]
        
        if selected_quarter != "Todos":
            filtered_df = filtered_df[filtered_df['Trimestre'] == selected_quarter]
        
        if selected_client != "Todos":
            filtered_df = filtered_df[filtered_df[client_col] == selected_client]
        
        # Generar tabla de reporte
        try:
            report_table = generar_tabla_reporte(filtered_df, client_col, date_col, amount_col)
            
            # Mostrar tabla formateada
            st.markdown('<div class="sub-header">Reporte de Visibility</div>', unsafe_allow_html=True)
            
            # Formatear tabla para mostrar en miles (K)
            formatted_table = report_table.applymap(format_miles)
            
            # Mostrar la tabla
            st.dataframe(formatted_table, use_container_width=True)
            
            # Opción para descargar la tabla
            csv_buffer = io.StringIO()
            report_table.to_csv(csv_buffer)
            csv_string = csv_buffer.getvalue()
            
            st.download_button(
                label="Descargar reporte como CSV",
                data=csv_string,
                file_name=f"reporte_visibility_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv"
            )
            
            # Visualizaciones
            st.markdown('<div class="sub-header">Visualizaciones</div>', unsafe_allow_html=True)
            
            # Gráfico 1: Distribución por cliente (Top 20 en lugar de 10)
            fig1 = px.pie(
                filtered_df.groupby(client_col)[amount_col].sum().reset_index().sort_values(amount_col, ascending=False).head(20),
                values=amount_col,
                names=client_col,
                title=f"Distribución de ingresos por cliente (Top 20)",
                hole=0.4
            )
            st.plotly_chart(fig1, use_container_width=True)
            
            # Gráfico 2: Tendencia mensual
            monthly_data = filtered_df.groupby(['Año', 'Mes', 'Mes_Nombre'])[amount_col].sum().reset_index()
            monthly_data['Fecha'] = pd.to_datetime(monthly_data['Año'].astype(str) + '-' + monthly_data['Mes'].astype(str) + '-01')
            monthly_data = monthly_data.sort_values('Fecha')
            
            fig2 = px.bar(
                monthly_data,
                x='Mes_Nombre',
                y=amount_col,
                text=monthly_data[amount_col].apply(lambda x: f"${x/1000:.0f}K"),
                title="Tendencia mensual de ingresos",
                labels={'Mes_Nombre': 'Mes', amount_col: 'Total USD'}
            )
            
            # Definimos un orden personalizado para los meses
            month_order = ['January', 'February', 'March', 'April', 'May', 'June', 
                          'July', 'August', 'September', 'October', 'November', 'December']
            
            # Aplicamos el orden a la gráfica de tendencia mensual
            fig2.update_xaxes(categoryorder='array', categoryarray=month_order)
            
            st.plotly_chart(fig2, use_container_width=True)
            
            # Gráfico 3: Comparativo trimestral
            quarterly_data = filtered_df.groupby('Trimestre')[amount_col].sum().reset_index()
            
            fig3 = px.bar(
                quarterly_data,
                x='Trimestre',
                y=amount_col,
                text=quarterly_data[amount_col].apply(lambda x: f"${x/1000:.0f}K"),
                title="Comparativo trimestral",
                color='Trimestre',
                color_discrete_map={'Q1': '#3498db', 'Q2': '#2ecc71', 'Q3': '#f1c40f', 'Q4': '#e74c3c'}
            )
            st.plotly_chart(fig3, use_container_width=True)
            
        except Exception as e:
            st.error(f"Error al generar el reporte: {e}")
            st.text("Detalles técnicos para solucionar el problema:")
            st.exception(e)
    
else:
    # Mensaje cuando no hay archivo cargado
    st.info("Sube tu archivo CSV para comenzar el análisis.")
    
    # Demo data placeholder
    st.markdown('<div class="sub-header">Vista previa de la aplicación</div>', unsafe_allow_html=True)
    st.markdown("""
    Esta aplicación te permitirá:
    
    1. **Cargar** un archivo CSV con datos de Visibility
    2. **Visualizar** una tabla similar a la que generaste anteriormente
    3. **Filtrar** por año, trimestre y cliente
    4. **Analizar** tendencias con gráficos interactivos
    5. **Exportar** los resultados en formato CSV
    
    Sube tu archivo para comenzar.
    """)

# Información adicional al final
with st.expander("Información adicional"):
    st.markdown("""
    ### Instrucciones de uso
    
    1. **Carga el archivo CSV**: Asegúrate de que tu archivo tenga las columnas de fecha, cliente y monto.
    2. **Selecciona el delimitador correcto**: Normalmente es punto y coma (;) o coma (,).
    3. **Usa los filtros** para explorar los datos por año, trimestre o cliente.
    4. **Descarga el reporte** en formato CSV para utilizarlo en Excel u otras herramientas.
    
    ### Requisitos del formato CSV
    
    El dashboard funciona mejor con archivos que contengan estas columnas (o similares):
    - Una columna de fecha (formato DD/MM/YYYY)
    - Una columna de cliente o cuenta
    - Una columna de monto en USD llamada "Total USD"
    
    ### Instalación local
    
    Para ejecutar esta aplicación en tu equipo:
    
    ```bash
    pip install streamlit pandas plotly
    streamlit run app.py
    ```
    """)

# Footer
st.markdown("---")
st.markdown("Dashboard de Visibility v1.0 | Desarrollado con Streamlit")