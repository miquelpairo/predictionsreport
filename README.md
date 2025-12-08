# NIR Analyzer - Analizador de Predicciones NIR

Aplicación Streamlit para analizar y comparar predicciones de equipos NIR con diferentes lámparas.

## 📋 Requisitos Previos

- Python 3.8 o superior
- Windows (los scripts .bat son para Windows, pero puedes adaptar para Linux/Mac)

## 🚀 Instalación

### Opción 1: Instalación Automática (Windows)

1. Descarga todos los archivos en una carpeta
2. Haz doble clic en `install.bat`
3. Espera a que se instalen todas las dependencias
4. ¡Listo!

### Opción 2: Instalación Manual

```bash
# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
# En Windows:
venv\Scripts\activate
# En Linux/Mac:
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

## 🎯 Uso

### Ejecutar la Aplicación (Windows)

Haz doble clic en `run_nir_analyzer.bat`

### Ejecutar Manualmente

```bash
# Activar entorno virtual
venv\Scripts\activate  # Windows
# o
source venv/bin/activate  # Linux/Mac

# Ejecutar Streamlit
streamlit run nir_analyzer.py
```

La aplicación se abrirá automáticamente en tu navegador en `http://localhost:8501`

## 📖 Guía de Uso

### 1. Cargar Archivo XML

- Haz clic en "Browse files" en la barra lateral
- Selecciona tu archivo XML de reporte NIR
- Haz clic en "Cargar y Analizar"

### 2. Seleccionar Productos

- Marca los productos que quieres analizar
- Por defecto, se seleccionan todos

### 3. Seleccionar Lámparas

- Selecciona las combinaciones de ID y Note (lámparas) que quieres comparar
- Cada combinación representa una configuración de lámpara específica

### 4. Generar Análisis

- Haz clic en "Generar Análisis y Gráficos"
- Espera a que se procesen los datos

### 5. Explorar Resultados

Navega por las 5 pestañas disponibles:

#### 📈 Diferencias entre Lámparas
- Selecciona dos lámparas para comparar
- Visualiza las diferencias en Humedad y Proteína
- Gráfico de barras horizontales con colores verde/rojo

#### 📊 Comparación Detallada
- Selecciona el parámetro a visualizar
- Compara medias por producto y lámpara
- Gráfico de barras agrupadas

#### 📦 Box Plots
- Selecciona múltiples parámetros
- Visualiza la distribución completa de valores
- Identifica outliers y variabilidad

#### 🎯 Scatter Plots
- Visualiza la relación entre Humedad y Proteína
- Cada lámpara tiene un color diferente
- Scatter plot por producto

#### 📄 Reporte de Texto
- Informe completo en formato texto
- Incluye estadísticas detalladas
- Botón para descargar el reporte

## 📊 Formato de Archivo XML

El archivo XML debe:
- Ser generado por el software NIR-Online
- Contener múltiples hojas (worksheets) con datos de productos
- Cada hoja debe tener las columnas:
  - No: Número de medición
  - ID: Identificador de muestra
  - Note: Nota/configuración de lámpara
  - Product: Nombre del producto
  - Method: Método utilizado
  - Parámetros numéricos (H, PB, etc.)

## 🔧 Estructura de Archivos

```
nir_analyzer/
├── nir_analyzer.py       # Aplicación principal
├── requirements.txt      # Dependencias Python
├── install.bat          # Script de instalación (Windows)
├── run_nir_analyzer.bat # Script de ejecución (Windows)
├── README.md            # Este archivo
└── venv/                # Entorno virtual (creado al instalar)
```

## 🎨 Características

- ✅ Interfaz web intuitiva con Streamlit
- ✅ Carga de archivos XML desde NIR-Online
- ✅ Selección flexible de productos y lámparas
- ✅ Múltiples tipos de gráficos interactivos
- ✅ Estadísticas detalladas (media, std, min, max)
- ✅ Comparación automática entre lámparas
- ✅ Generación de reportes en texto
- ✅ Descarga de informes
- ✅ Gráficos interactivos con Plotly

## 🐛 Resolución de Problemas

### La aplicación no se inicia
- Verifica que Python esté instalado: `python --version`
- Asegúrate de haber ejecutado `install.bat` primero
- Revisa que todas las dependencias estén instaladas

### Error al cargar el archivo XML
- Verifica que el archivo sea XML válido de NIR-Online
- Comprueba que contenga datos de productos
- Asegúrate de que las columnas estén correctamente formateadas

### Los gráficos no se muestran
- Actualiza tu navegador
- Intenta con otro navegador (Chrome recomendado)
- Verifica la consola de Python por errores

## 📝 Notas

- La aplicación se ejecuta localmente en tu PC
- No se envía ningún dato a servidores externos
- Los archivos XML se procesan en memoria
- Puedes cerrar la aplicación con Ctrl+C en la terminal

## 👨‍💻 Autor

Desarrollado para análisis de equipos NIR BUCHI

## 📄 Licencia

Uso interno

---

Para soporte o preguntas, contacta al administrador del sistema.