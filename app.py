import dash
from dash import dcc, html, dash_table
import pandas as pd
import plotly.express as px

# 1. CARGAR DATOS
df = pd.read_csv("data/Anexo1.NoFetal2019_CE_15-03-23.csv", encoding="latin-1", sep=",")

# Cargar Divipola
divipola = pd.read_excel("data/Divipola.xlsx", sheet_name="Hoja3", skiprows=1, header=None)
divipola = divipola[[0, 1, 2, 3, 5, 6]] # Agregamos las columnas 5 y 6 (Longitud y Latitud)
divipola.columns = ["COD_DEPARTAMENTO", "NOMBRE_DEPARTAMENTO", "COD_MUNICIPIO", "NOMBRE_MUNICIPIO", "Longitud", "Latitud"]

# Cargar Codigos de Muerte
codigos = pd.read_excel("data/Anexo2.CodigosDeMuerte_CE_15-03-23.xlsx", skiprows=8)
codigos.columns = codigos.columns.str.strip()

# 2. CRUZAR DATOS
# Limpiamos los códigos base
df["COD_DEPARTAMENTO"] = df["COD_DEPARTAMENTO"].astype(str).str.replace('.0', '', regex=False).str.zfill(2)
df["COD_MUNICIPIO"] = df["COD_MUNICIPIO"].astype(str).str.replace('.0', '', regex=False).str.zfill(3)
df["COD_MUERTE"] = df["COD_MUERTE"].astype(str).str.strip().str.upper()

# Unimos el código del depto (2 dígitos) + municipio (3 dígitos) para tener el código DANE de 5 dígitos (ej. 05001)
df["COD_DANE_MUNICIPIO"] = df["COD_DEPARTAMENTO"] + df["COD_MUNICIPIO"]

# Limpiamos Divipola
divipola["COD_DEPARTAMENTO"] = divipola["COD_DEPARTAMENTO"].astype(str).str.replace('.0', '', regex=False).str.zfill(2)
divipola["COD_MUNICIPIO"] = divipola["COD_MUNICIPIO"].astype(str).str.replace('.0', '', regex=False).str.zfill(5)

# Diccionarios
dict_deptos = dict(zip(divipola["COD_DEPARTAMENTO"], divipola["NOMBRE_DEPARTAMENTO"]))
dict_municipios = dict(zip(divipola["COD_MUNICIPIO"], divipola["NOMBRE_MUNICIPIO"]))

df["NOMBRE_DEPARTAMENTO"] = df["COD_DEPARTAMENTO"].map(dict_deptos)
df["NOMBRE_MUNICIPIO"] = df["COD_DANE_MUNICIPIO"].map(dict_municipios)

# Traducir Sexo
df["SEXO_TEXTO"] = df["SEXO"].map({1: "Masculino", 2: "Femenino", 3: "Indeterminado"})
df["SEXO_TEXTO"] = df["SEXO_TEXTO"].fillna("No especificado")

# --- DIAGNÓSTICO EN CONSOLA ---
print("--------------------------------------------------")
print("DIAGNÓSTICO DE DATOS:")
print(f"Total de registros en el CSV: {len(df)}")
print(f"Municipios sin nombre (NaN): {df['NOMBRE_MUNICIPIO'].isna().sum()}")
print(f"Homicidios X95 encontrados: {len(df[df['COD_MUERTE'].str.startswith('X95')])}")
print("--------------------------------------------------")


# 3. CREAR LAS GRÁFICAS

# 1. Mapa (Scatter con coordenadas de la Divipola)
muertes_depto = df.groupby("NOMBRE_DEPARTAMENTO").size().reset_index(name="Total")

coords_deptos = divipola[["NOMBRE_DEPARTAMENTO", "Latitud", "Longitud"]].drop_duplicates("NOMBRE_DEPARTAMENTO")
coords_deptos["Latitud"] = pd.to_numeric(coords_deptos["Latitud"].astype(str).str.replace(",", "."), errors="coerce")
coords_deptos["Longitud"] = pd.to_numeric(coords_deptos["Longitud"].astype(str).str.replace(",", "."), errors="coerce")

mapa_data = muertes_depto.merge(coords_deptos, on="NOMBRE_DEPARTAMENTO", how="inner")

fig_mapa = px.scatter_geo(
    mapa_data, lat="Latitud", lon="Longitud", size="Total", color="Total",
    hover_name="NOMBRE_DEPARTAMENTO", title="Distribución de muertes por departamento (2019)",
    color_continuous_scale="Reds", template="plotly_dark", size_max=50
)
fig_mapa.update_geos(
    scope="south america", center={"lat": 4.0, "lon": -74.0}, projection_scale=4,
    showcountries=True, countrycolor="#444444", showland=True, landcolor="#222222"
)

# 2. Líneas
muertes_mes = df.groupby("MES").size().reset_index(name="Total")
fig_lineas = px.line(
    muertes_mes, x="MES", y="Total", title="Total de muertes por mes en Colombia (2019)",
    markers=True, template="plotly_dark"
)

# 3. Barras X95 (Violencia)
homicidios = df[df["COD_MUERTE"].str.startswith("X95")]
top_ciudades = homicidios.groupby("NOMBRE_MUNICIPIO").size().nlargest(5).reset_index(name="Total")
fig_barras = px.bar(
    top_ciudades, x="NOMBRE_MUNICIPIO", y="Total", title="Top 5 ciudades más violentas (Homicidios X95)",
    color="Total", color_continuous_scale="OrRd", template="plotly_dark"
)

# 4. Circular
bottom_ciudades = df.groupby("NOMBRE_MUNICIPIO").size().nsmallest(10).reset_index(name="Total")
fig_pie = px.pie(
    bottom_ciudades, names="NOMBRE_MUNICIPIO", values="Total",
    title="10 ciudades con menor índice de mortalidad", template="plotly_dark"
)

# 5. Barras apiladas (Sexo)
sexo_depto = df.groupby(["NOMBRE_DEPARTAMENTO", "SEXO_TEXTO"]).size().reset_index(name="Total")
top_deptos = muertes_depto.nlargest(10, "Total")
sexo_depto = sexo_depto[sexo_depto["NOMBRE_DEPARTAMENTO"].isin(top_deptos["NOMBRE_DEPARTAMENTO"])]
fig_apiladas = px.bar(
    sexo_depto, x="NOMBRE_DEPARTAMENTO", y="Total", color="SEXO_TEXTO",
    title="Muertes por sexo en los Top 10 departamentos", barmode="stack", template="plotly_dark",
    labels={"SEXO_TEXTO": "Sexo", "NOMBRE_DEPARTAMENTO": "Departamento"}
)

# 6. Histograma
fig_hist = px.histogram(
    df, x="GRUPO_EDAD1", title="Distribución de muertes por grupo de edad (Ciclo de vida)", template="plotly_dark"
)

# 7. Tabla
top_causas = df.groupby("COD_MUERTE").size().nlargest(10).reset_index(name="Total Casos")
top_causas["COD_3"] = top_causas["COD_MUERTE"].str[:3]
top_causas = top_causas.merge(
    codigos[["Código de la CIE-10 tres caracteres", "Descripción  de códigos mortalidad a tres caracteres"]].drop_duplicates(),
    left_on="COD_3", right_on="Código de la CIE-10 tres caracteres", how="left"
)
top_causas = top_causas.drop_duplicates(subset=["COD_MUERTE"])
top_causas = top_causas[["COD_MUERTE", "Descripción  de códigos mortalidad a tres caracteres", "Total Casos"]]
top_causas.columns = ["Código CIE-10", "Nombre de la causa", "Total Casos"]


# 4. DISEÑO DE LA PÁGINA WEB
app = dash.Dash(__name__)
server = app.server 

app.layout = html.Div(style={'backgroundColor': '#121212', 'color': '#ffffff', 'fontFamily': 'Arial, sans-serif', 'padding': '20px'}, children=[
    html.Div([
        html.H1("Análisis de Mortalidad en Colombia - 2019", style={'textAlign': 'center', 'color': '#ffffff', 'marginBottom': '5px'}),
        html.H4("Autor: Andres Guzman", style={'textAlign': 'center', 'color': '#aaaaaa', 'margin': '0'}),
        html.H5("Universidad La Salle", style={'textAlign': 'center', 'color': '#aaaaaa', 'marginTop': '0'})
    ], style={'marginBottom': '20px'}),
    html.Hr(style={'borderColor': '#333333'}),
    
    html.H2("1. Mapa de muertes por departamento"),
    dcc.Graph(figure=fig_mapa),
    html.H2("2. Variación mensual de muertes"),
    dcc.Graph(figure=fig_lineas),
    html.H2("3. Ciudades más violentas (Códigos X95)"),
    dcc.Graph(figure=fig_barras),
    html.H2("4. Ciudades con menor mortalidad"),
    dcc.Graph(figure=fig_pie),
    html.H2("5. Comparación por sexo en los Top Departamentos"),
    dcc.Graph(figure=fig_apiladas),
    html.H2("6. Distribución por rangos de edad"),
    dcc.Graph(figure=fig_hist),
    html.H2("7. Tabla: 10 principales causas de muerte"),
    
    dash_table.DataTable(
        data=top_causas.to_dict('records'),
        columns=[{'name': i, 'id': i} for i in top_causas.columns],
        style_cell={'textAlign': 'left', 'padding': '10px', 'backgroundColor': '#1e1e1e', 'color': 'white', 'border': '1px solid #333333'},
        style_header={'backgroundColor': '#333333', 'fontWeight': 'bold', 'color': 'white', 'border': '1px solid #333333'}
    ),
    html.Hr(style={'borderColor': '#333333'}),
    html.P("Taller desarrollado para la materia de Análisis de Datos.", style={'textAlign': 'center', 'color': '#666666'})
])

if __name__ == "__main__":
    app.run(debug=True)