import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from streamlit_gsheets import GSheetsConnection

# Configuración de página
st.set_page_config(page_title="My Budget", layout="wide")

st.title("My Budget")

# ------------------
# CONEXIÓN A GOOGLE SHEETS
# ------------------
# Establecer la conexión
conn = st.connection("gsheets", type=GSheetsConnection)

# Leer los datos de la hoja
# ttl=0 asegura que siempre lea la versión más reciente al recargar
df = conn.read(ttl=0)

# ------------------
# FORMULARIO LATERAL
# ------------------
st.sidebar.header("➕ Registrar Nuevo Movimiento")

with st.sidebar.form("registro_form", clear_on_submit=True):
    tipo = st.selectbox("Tipo de Movimiento", ["Gasto", "Ingreso"])
    mes = st.selectbox("Mes", ['Ene', 'Feb', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Ago', 'Sept', 'Oct', 'Nov', 'Dic'])
    
    categorias_opciones = [
        "Casa", "Vida Diaria", "Transporte", "Entretenimiento", 
        "Salud", "Vacaciones", "Ocio", "Cuotas y Suscripciones", 
        "Personal", "Obligaciones Financieras", "Pagos Varios", 
        "Ingresos", "Otro"
    ]
    categoria = st.selectbox("Categoría General", categorias_opciones)
    subcategoria = st.text_input("Detalle (Ej. Arriendo, Spotify, Salario)")
    monto = st.number_input("Monto ($)", min_value=0.00, format="%.2f")
    submit = st.form_submit_button("Guardar Registro")
    
    if submit:
        if subcategoria:
            # Crear el nuevo registro
            nuevo_registro = pd.DataFrame([{
                "Mes": mes, "Tipo": tipo, "Categoria": categoria, 
                "Subcategoria": subcategoria, "Monto": monto
            }])
            
            # Unir los datos existentes con el nuevo
            df_actualizado = pd.concat([df, nuevo_registro], ignore_index=True)
            
            # Actualizar el Google Sheet
            conn.update(data=df_actualizado)
            
            st.success("¡Registro guardado exitosamente en la nube!")
            # Limpiar caché y recargar
            st.cache_data.clear()
            st.rerun()
        else:
            st.error("Por favor, ingresa un detalle para el movimiento.")

# ------------------
# LECTURA DE DATOS Y GRÁFICOS
# ------------------
if not df.empty and 'Monto' in df.columns:
    # Asegurarnos de que Monto sea numérico
    df['Monto'] = pd.to_numeric(df['Monto'], errors='coerce').fillna(0)
    
    # 1. TARJETAS RESUMEN
    st.subheader("📊 Balance General")
    total_ingresos = df[df['Tipo'] == 'Ingreso']['Monto'].sum()
    total_gastos = df[df['Tipo'] == 'Gasto']['Monto'].sum()
    balance = total_ingresos - total_gastos
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Ingresos Totales", f"${total_ingresos:,.2f}")
    col2.metric("Gastos Totales", f"${total_gastos:,.2f}")
    col3.metric("Balance Disponible", f"${balance:,.2f}")
    
    st.markdown("---")
    col_izq, col_der = st.columns(2)
    
    # 2. GRÁFICO DE ANILLO
    with col_izq:
        st.subheader("🍩 Distribución de Gastos Reales")
        df_gastos = df[(df['Tipo'] == 'Gasto') & (df['Monto'] > 0)]
        if not df_gastos.empty:
            gastos_por_categoria = df_gastos.groupby('Categoria')['Monto'].sum().reset_index()
            fig_pie = px.pie(gastos_por_categoria, values='Monto', names='Categoria', hole=0.5, color_discrete_sequence=px.colors.sequential.RdBu)
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("No hay gastos registrados mayores a $0 para graficar.")

    # 3. GRÁFICO DE LÍNEAS
    with col_der:
        st.subheader("📈 Flujo de Caja por Mes")
        meses_orden = ['Ene', 'Feb', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Ago', 'Sept', 'Oct', 'Nov', 'Dic']
        df['Mes'] = pd.Categorical(df['Mes'], categories=meses_orden, ordered=True)
        
        flujo = df.groupby(['Mes', 'Tipo'], observed=False)['Monto'].sum().reset_index()
        flujo_pivot = flujo.pivot(index='Mes', columns='Tipo', values='Monto').fillna(0).reset_index()
        
        if 'Ingreso' not in flujo_pivot.columns: flujo_pivot['Ingreso'] = 0
        if 'Gasto' not in flujo_pivot.columns: flujo_pivot['Gasto'] = 0
        
        flujo_pivot['Balance Mensual'] = flujo_pivot['Ingreso'] - flujo_pivot['Gasto']
        
        fig_line = go.Figure()
        fig_line.add_trace(go.Scatter(x=flujo_pivot['Mes'], y=flujo_pivot['Ingreso'], mode='lines+markers', name='Ingresos', line=dict(color='green')))
        fig_line.add_trace(go.Scatter(x=flujo_pivot['Mes'], y=flujo_pivot['Gasto'], mode='lines+markers', name='Gastos', line=dict(color='red')))
        fig_line.add_trace(go.Scatter(x=flujo_pivot['Mes'], y=flujo_pivot['Balance Mensual'], mode='lines+markers', name='Balance', line=dict(color='blue', dash='dot')))
        
        st.plotly_chart(fig_line, use_container_width=True)

    # 4. TABLA DE DETALLES
    st.markdown("---")
    st.subheader("📋 Detalle de Movimientos")
    
    col_filtro1, col_filtro2 = st.columns([2, 1])
    with col_filtro1:
        cat_filtro = st.multiselect("Filtrar por Categoría:", options=df['Categoria'].dropna().unique(), default=list(df['Categoria'].dropna().unique()))
    with col_filtro2:
        mostrar_ceros = st.checkbox("Mostrar registros en $0.00", value=True)
    
    df_filtrado = df[df['Categoria'].isin(cat_filtro)]
    if not mostrar_ceros:
        df_filtrado = df_filtrado[df_filtrado['Monto'] > 0]
        
    st.dataframe(df_filtrado, use_container_width=True)
else:
    st.warning("No hay datos en el Google Sheet o se están cargando...")
