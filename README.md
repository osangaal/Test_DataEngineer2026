# 🚀 Extracción Modular de Reportes Mineros (NI 43-101)

Este proyecto implementa un pipeline de ingeniería de datos diseñado para la extracción estructurada, validación y normalización de información técnica desde reportes mineros en formato PDF (NI 43-101). Utiliza Modelos de Lenguaje Grande (LLMs) orquestados mediante LlamaIndex para transformar datos no estructurados en esquemas JSON rigurosamente tipados.

## 📋 Tabla de Contenidos
- [Arquitectura y Funcionamiento](#arquitectura-y-funcionamiento)
- [Instalación y Uso](#instalación-y-uso)
- [Estructura del Proyecto](#estructura-del-proyecto)
- [Stack Tecnológico](#stack-tecnológico)
- [Costos Operativos](#costos-operativos)
- [Desafíos y Limitaciones](#desafíos-y-limitaciones)
- [Propuesta de Escalabilidad (Producción)](#propuesta-de-escalabilidad-producción)

## 🏗 Arquitectura y Funcionamiento

El sistema opera bajo un enfoque modular de "Divide y Vencerás", procesando el documento en cuatro etapas secuenciales para maximizar la precisión y mitigar las limitaciones de ventana de contexto de los LLMs.

1.  **Ingesta Inteligente**: Escaneo preliminar del PDF para mapear índices, tablas y secciones clave.
2.  **Extracción Modular**:
    *   **Metadata**: Identificación de proyecto, ubicación y propietarios.
    *   **Recursos Minerales**: Extracción de tablas de recursos, leyes de corte y estadísticas de sondajes.
    *   **Reservas Minerales**: Identificación de reservas probadas/probables y metalurgia.
    *   **Economía**: Análisis de CAPEX, OPEX, NPV e IRR.
3.  **Validación Cruzada**: Verificación lógica de datos (ej. Reservas < Recursos) y normalización de unidades.
4.  **Persistencia**: Generación de reportes JSON y logs de validación.

## 💻 Instalación y Uso

### Prerrequisitos
*   Linux/MacOS (Probado en Ubuntu 22.04)
*   Python 3.10+
*   Clave de API de OpenAI

### Ejecución
1.  **Configurar entorno**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

2.  **Variables de Entorno**:
    Crear un archivo `.env` en la raíz:
    ```env
    OPENAI_API_KEY=sk-proj-xxxx
    ```

3.  **Ejecutar Pipeline**:
    Coloque los archivos PDF en la carpeta `data/` y ejecute:
    ```bash
    python main.py
    ```
    Los reportes se generarán en la carpeta `output/`.

## 📂 Estructura del Proyecto

```text
.
├── data/                  # Directorio de entrada (PDFs)
├── output/                # Directorio de salida (JSONs)
├── src/
│   ├── processor.py       # Lógica core de extracción y procesamiento (LlamaIndex)
│   ├── models.py          # Definiciones de esquemas Pydantic
│   └── utils.py           # Utilidades de I/O y normalización
├── main.py                # Entrypoint y orquestador del batch processing
└── requirements.txt       # Dependencias del proyecto
```

## 🛠 Stack Tecnológico

La elección del stack prioriza la **precisión semántica** sobre la velocidad pura, dado la naturaleza crítica de los datos financieros mineros.

*   **LlamaIndex**: Framework de orquestación para RAG (Retrieval-Augmented Generation). Seleccionado por su capacidad superior para manejar contextos largos y estructuras de documentos complejos comparado con LangChain crudo.
*   **OpenAI GPT-4o-mini**: Motor de inferencia.
    *   *Por qué*: Ofrece un balance óptimo entre capacidad de razonamiento y costo-eficiencia para tareas de extracción estructurada.
*   **Pydantic**: Validación de datos y definición de contratos de interfaz. Asegura que el JSON de salida cumpla estrictamente con el esquema esperado.

## 💰 Costos Operativos

El modelo subyacente es **gpt-4o-mini**. La estimación de costos basada en el pricing actual es:

| Concepto | Precio / 1M Tokens |
| :--- | :--- |
| **Input (Entrada)** | $0.150 |
| **Cached Input** | $0.075 |
| **Output (Salida)** | $0.600 |

*Nota: Un reporte NI 43-101 típico consume entre 15k y 40k tokens dependiendo de la densidad tablas.*

## 🚧 Desafíos y Limitaciones

### Desafíos Encontrados
1.  **Heterogeneidad de Documentos**: Los reportes no siguen un estándar visual único; tablas de recursos pueden ser imágenes, texto mal formateado o tablas nativas.
2.  **Alucinación en Celdas Vacías**: Los LLMs tienden a "inferir" valores nulos (0 vs null). Se implementaron validadores en `models.py` para mitigar esto.
3.  **Hardware Limitado**: La extracción de PDF (OCR + Parsing) es intensiva en CPU.
4.  **Tiempo de Ejecución**: El procesamiento secuencial de secciones grandes es lento (1-3 min por archivo).

### Limitaciones Actuales
*   **OCR**: Actualmente depende de la capa de texto del PDF. PDFs escaneados (imágenes) requieren integración con Tesseract o Azure Document Intelligence.
*   **Tablas Complejas**: Tablas anidadas o con headers verticales rotados pueden perder alineación en la extracción de texto plano.

### Alternativas Consideradas (Mejoras Potenciales)
*   **MinerU / Marker**: Herramientas especializadas en conversión de PDF a Markdown que superan a `PyMuPDF` en layout analysis, pero requieren GPU para inferencia eficiente.
*   **Unstructured.io**: Potente para ingesta, pero costoso en versión cloud o complejo de desplegar on-premise.

## 🚀 Propuesta de Escalabilidad (Producción) - Arquitectura AWS

Para llevar esta solución a un nivel productivo y procesar miles de documentos (10,000+), proponemos una arquitectura **Serverless / Event-Driven** totalmente nativa en AWS para optimizar costos y reducir la carga operativa.

### Diagrama de Flujo

1.  **Ingesta (S3 + SQS)**:
    *   Los PDFs se cargan en **Amazon S3** (`raw-bucket`).
    *   S3 Event Notifications envían mensajes a una cola **Amazon SQS**, desacoplando la ingesta del procesamiento.

2.  **Cómputo (AWS Batch / Lambda)**:
    *   **Paso 1 (GPU - AWS Batch)**: Se utiliza **AWS Batch** con instancias EC2 GPU (ej. g4dn) para ejecutar trabajos pesados de conversión PDF a Markdown (usando herramientas como MinerU o Marker) de manera efímera.
    *   **Paso 2 (Orquestación - AWS Lambda)**: Funciones Lambda consumen los Markdowns limpios y ejecutan la lógica de `LlamaIndex`.
        *   *Integración LLM*: La Lambda invoca a la API de OpenAI (o **Amazon Bedrock** si se desea seguridad privada total).

3.  **Almacenamiento y Consultas**:
    *   **Amazon DynamoDB**: Almacenamiento NoSQL para los JSONs resultantes (baja latencia y esquema flexible).
    *   **Amazon S3 (Results)**: Archivo de backups de los JSONs generados.
    *   **Amazon Athena**: Para realizar consultas SQL analíticas directamente sobre los resultados en S3 sin necesidad de cargar un Data Warehouse complejo.

4.  **Observabilidad y Monitoreo**:
    *   **Amazon CloudWatch**: Centralización de logs de aplicación y métricas de infraestructura.
    *   **AWS X-Ray**: Trazabilidad distribuida para detectar cuellos de botella entre servicios.


![Arquitectura AWS](flujo_datos.drawio.svg)

---
*Desarrollado para el Test Técnico de Data Engineer - 2026*
