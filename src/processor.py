from llama_index.core import SimpleDirectoryReader
from openai import OpenAI
import json
import os
import re
from typing import List, Dict, Set
from .models import (
    MiningReportComplete,
    ProjectMetadata,
    MineralResourcesSection,
    MineralResource,
    CutOffGrade,
    CutOffGradeReserves,
    MineralReservesSection,
    MineralReserve,
    Economics,
    OperatingCost,
    CapitalCost,
    MetallurgyHistory,
    ValidationSummary
)

class TableFinder:
    """Encuentra páginas específicas que contienen tablas o secciones relevantes."""
    
    def __init__(self, documents):
        self.documents = documents
        self.table_locations = self._map_all_tables()
    
    def _map_all_tables(self) -> Dict[str, List[int]]:
        """Mapea TODAS las tablas y secciones del documento."""
        locations = {
            # Tablas numeradas específicas
            "metadata_tables": [],
            "resource_tables": [],
            "reserve_tables": [],
            "economic_tables": [],
            "drilling_tables": [],
            "sampling_tables": [],
            
            # Secciones por keyword
            "qualified_persons": [],
            "project_description": [],
            "mineral_resources": [],
            "mineral_reserves": [],
            "costs": [],
            "budget": [],
            "metallurgy": [],
        }
        
        print("\n🔍 ESCANEANDO DOCUMENTO COMPLETO...")
        print(f"   Total de páginas: {len(self.documents)}")
        
        for i, doc in enumerate(self.documents):
            text = doc.text
            text_upper = text.upper()
            
            # Buscar tablas numeradas específicas
            tables_found = re.findall(r'TABLE\s+(\d+[-\.]\d+)', text, re.IGNORECASE)
            
            for table_num in set(tables_found):
                # Clasificar por número de tabla
                table_int = int(table_num.split('-')[0].split('.')[0])
                
                if table_int <= 4:  # Tablas 1-4: Metadata
                    locations["metadata_tables"].append(i)
                elif 10 <= table_int <= 13:  # Tablas 10-13: Drilling/Sampling
                    locations["drilling_tables"].append(i)
                    locations["sampling_tables"].append(i)
                elif table_int == 14:  # Tabla 14: Recursos
                    locations["resource_tables"].append(i)
                elif table_int == 15:  # Tabla 15: Reservas
                    locations["reserve_tables"].append(i)
                elif table_int >= 20:  # Tablas 20+: Economía
                    locations["economic_tables"].append(i)
            
            # Buscar por keywords (más robusto que tablas numeradas)
            if any(kw in text_upper for kw in ["QUALIFIED PERSON", "AUTHOR", "P.GEO", "P.ENG"]):
                locations["qualified_persons"].append(i)
            
            if any(kw in text_upper for kw in ["PROJECT DESCRIPTION", "LOCATION", "CLIMATE", "MINING TITLE", "CONCESSION"]):
                locations["project_description"].append(i)
            
            if any(kw in text_upper for kw in ["MINERAL RESOURCE", "RESOURCE ESTIMATE", "MEASURED", "INDICATED", "INFERRED"]):
                locations["mineral_resources"].append(i)
            
            if any(kw in text_upper for kw in ["MINERAL RESERVE", "RESERVE ESTIMATE", "PROVEN", "PROBABLE"]):
                locations["mineral_reserves"].append(i)
            
            if any(kw in text_upper for kw in ["CUT-OFF GRADE", "CUTOFF GRADE", "CUT OFF GRADE"]):
                locations["resource_tables"].append(i)
                locations["reserve_tables"].append(i)
            
            if any(kw in text_upper for kw in ["DRILL", "DRILLING", "DIAMOND DRILL", "CORE"]):
                locations["drilling_tables"].append(i)
            
            if any(kw in text_upper for kw in ["SAMPLING", "SAMPLE", "ASSAY", "CHANNEL"]):
                locations["sampling_tables"].append(i)
            
            if any(kw in text_upper for kw in ["CAPEX", "CAPITAL COST", "OPEX", "OPERATING COST"]):
                locations["costs"].append(i)
                locations["economic_tables"].append(i)
            
            if any(kw in text_upper for kw in ["BUDGET", "EXPLORATION BUDGET", "PROPOSED WORK"]):
                locations["budget"].append(i)
                locations["economic_tables"].append(i)
            
            if any(kw in text_upper for kw in ["METALLURG", "RECOVERY", "PROCESSING", "PLANT"]):
                locations["metallurgy"].append(i)
            
            if any(kw in text_upper for kw in ["NPV", "IRR", "ECONOMIC ANALYSIS", "PAYBACK"]):
                locations["economic_tables"].append(i)
        
        # Eliminar duplicados y ordenar
        for key in locations:
            locations[key] = sorted(set(locations[key]))
        
        # Imprimir reporte
        print("\n📊 MAPA DE TABLAS Y SECCIONES:")
        print(f"   {'='*60}")
        
        important_sections = {
            "Metadata (Tablas 1-4)": locations["metadata_tables"],
            "Qualified Persons": locations["qualified_persons"],
            "Project Description": locations["project_description"],
            "Drilling (Tablas 10-13)": locations["drilling_tables"],
            "Sampling": locations["sampling_tables"],
            "Resources (Tabla 14)": locations["resource_tables"],
            "Mineral Resources (sección)": locations["mineral_resources"],
            "Reserves (Tabla 15)": locations["reserve_tables"],
            "Mineral Reserves (sección)": locations["mineral_reserves"],
            "Economic Tables (20+)": locations["economic_tables"],
            "Costs": locations["costs"],
            "Budget": locations["budget"],
            "Metallurgy": locations["metallurgy"],
        }
        
        for section, pages in important_sections.items():
            if pages:
                status = "✅"
                page_str = f"{pages[:5]}{'...' if len(pages) > 5 else ''}"
                count = len(pages)
                print(f"   {status} {section:40} {count:3} páginas: {page_str}")
            else:
                print(f"   ❌ {section:40}   0 páginas")
        
        print(f"   {'='*60}\n")
        
        return locations
    
    def get_pages_for_extraction(self, category: str, max_pages: int = 30) -> List[int]:
        """Obtiene las páginas óptimas para una categoría de extracción."""
        pages = set()
        
        if category == "metadata":
            # Metadata: primeras 15 páginas + páginas con tablas + qualified persons
            pages.update(range(min(15, len(self.documents))))
            pages.update(self.table_locations.get("metadata_tables", []))
            pages.update(self.table_locations.get("qualified_persons", []))
            pages.update(self.table_locations.get("project_description", []))
        
        elif category == "resources":
            # Recursos: tablas específicas + secciones + drilling + sampling
            pages.update(self.table_locations.get("resource_tables", []))
            pages.update(self.table_locations.get("mineral_resources", []))
            pages.update(self.table_locations.get("drilling_tables", []))
            pages.update(self.table_locations.get("sampling_tables", []))
            
            # Si no hay páginas, buscar en rango típico
            if not pages:
                pages.update(range(20, min(50, len(self.documents))))
        
        elif category == "reserves":
            # Reservas: tablas específicas + secciones
            pages.update(self.table_locations.get("reserve_tables", []))
            pages.update(self.table_locations.get("mineral_reserves", []))
            
            # Si no hay páginas, buscar en rango típico
            if not pages:
                pages.update(range(30, min(60, len(self.documents))))
        
        elif category == "economics":
            # Economía: tablas + costos + presupuesto + metalurgia
            pages.update(self.table_locations.get("economic_tables", []))
            pages.update(self.table_locations.get("costs", []))
            pages.update(self.table_locations.get("budget", []))
            pages.update(self.table_locations.get("metallurgy", []))
            
            # Si no hay páginas, buscar en rango típico
            if not pages:
                pages.update(range(40, min(80, len(self.documents))))
        
        # Ordenar y limitar
        pages = sorted(pages)[:max_pages]
        
        return pages


class MiningReportExtractor:
    """Extractor modular con búsqueda inteligente de tablas."""
    
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.documents = SimpleDirectoryReader(input_files=[pdf_path]).load_data()
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Inicializar buscador de tablas
        self.table_finder = TableFinder(self.documents)
    
    def _get_pages_text(self, page_indices: List[int]) -> str:
        """Obtiene el texto de páginas específicas con marcadores."""
        if not page_indices:
            return ""
        
        return "\n\n".join([
            f"=== PÁGINA {i} ===\n{self.documents[i].text}" 
            for i in page_indices 
            if i < len(self.documents)
        ])
    
    def _call_llm(self, prompt: str, content: str) -> dict:
        """Llama al LLM con manejo de errores."""
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": content}
                ],
                temperature=0.0,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
        except Exception as e:
            print(f"    ❌ Error en llamada LLM: {e}")
            return {}
    
    def extract_metadata(self) -> ProjectMetadata:
        """LLAMADA 1: Extrae metadata COMPLETA del proyecto."""
        pages = self.table_finder.get_pages_for_extraction("metadata", max_pages=25)
        content = self._get_pages_text(pages)
        
        print(f"    📄 Buscando en {len(pages)} páginas: {pages[:8]}{'...' if len(pages) > 8 else ''}")
        
        prompt = """Eres un experto en extracción exhaustiva de datos de reportes NI 43-101.

Extrae TODA la metadata del proyecto en formato JSON:

{
  "project_info": {
    "project_name": "nombre del proyecto",
    "company_name": "nombre de la compañía",
    "status": "Producing/Development/Exploration"
  },
  "location": {
    "country": "país",
    "region": "región",
    "coordinates": "descripción de ubicación",
    "municipalities": ["lista de municipios"]
  },
  "report_details": {
    "report_type": "NI 43-101",
    "report_date": "fecha de publicación",
    "effective_date": "fecha efectiva",
    "qualified_persons": ["todos los nombres completos con credenciales"]
  },
  "mining_titles": [
    {
      "number": "número de título",
      "area_name": "nombre del área",
      "type": "tipo de concesión",
      "area_ha": 123.45,
      "expiry": "fecha de expiración"
    }
  ],
  "vein_dimensions": [
    {
      "vein": "nombre de la veta",
      "average_dip": "ángulo de inclinación",
      "strike_length_km": 2.8,
      "down_dip_length_km": 2.7,
      "average_vein_width_m": 1.3
    }
  ]
}

TABLAS A BUSCAR:
- Tabla 4-1 o similar: Mining titles (títulos mineros)
- Tabla 7-1 o similar: Vein dimensions (dimensiones de vetas)
- Sección 2.3 o similar: Qualified Persons

IMPORTANTE:
- Si no encuentras una tabla específica, busca la información en el texto
- Extrae TODOS los registros de cada tabla
- Si un campo no existe, usa null o array vacío []
"""

        result = self._call_llm(prompt, content)
        return ProjectMetadata(**result) if result else ProjectMetadata()
    
    def extract_resources(self) -> MineralResourcesSection:
        """LLAMADA 2: Extrae recursos minerales COMPLETOS."""
        pages = self.table_finder.get_pages_for_extraction("resources", max_pages=30)
        content = self._get_pages_text(pages)
        
        print(f"    📄 Buscando en {len(pages)} páginas: {pages[:8]}{'...' if len(pages) > 8 else ''}")
        
        prompt = """Eres un experto en extracción exhaustiva de recursos minerales de reportes NI 43-101.

**INSTRUCCIÓN CRÍTICA DE BÚSQUEDA:**
El texto contiene páginas marcadas como "=== PÁGINA X ===".
ESCANEA TODAS las páginas buscando:
1. Tablas numeradas: "TABLE 14-X", "TABLE 10-X", "TABLE 13-X"
2. Títulos de secciones: "MINERAL RESOURCES", "RESOURCE ESTIMATE"
3. Palabras clave: "Measured", "Indicated", "Inferred", "Cut-off Grade", "Drilling"

Si el proyecto está en EXPLORACIÓN TEMPRANA (no tiene recursos NI 43-101):
- Busca "HISTORIC ESTIMATES" o "HISTORICAL RESOURCES"
- Busca tablas de SAMPLING (TABLE 14-1, TABLE 10-1)
- Si NO hay recursos definidos, retorna arrays vacíos []

Extrae TODA la información de recursos en formato JSON:

{
  "summary": {
    "commodity": "Gold/Copper/Silver",
    "unit": "g/t Au",
    "contained_unit": "koz Au"
  },
  "data": [
    {
      "area": "nombre del área/depósito",
      "category": "Measured/Indicated/Inferred",
      "tonnes": 4100000.0,
      "grade": 14.31,
      "contained_metal": 1893.0
    }
  ],
  "cut_off_grades": [
    {
      "area": "nombre del área",
      "gold_price": 1850.0,
      "smelting_and_refining": 9.25,
      "royalties": 3.52,
      "gold_processing_recovery_pct": 95.2,
      "mining_cost": 114.0,
      "processing_cost": 34.0,
      "ga_cost": 25.0,
      "tailings_sustaining_cost": 1.5,
      "credits": 23.0,
      "final_cut_off_grade": 2.8
    }
  ],
  "drilling_summary": [
    {
      "target": "nombre del target",
      "number_of_holes": 790,
      "total_metres": 163547.0
    }
  ],
  "data_availability": [
    {
      "area": "nombre del área",
      "channel_count": 94416,
      "channel_metres": 96380.0,
      "drillhole_count": 790,
      "drillhole_metres": 163547.0
    }
  ],
  "block_model_stats": [
    {
      "vein": "nombre de veta",
      "fault_blocks": 61,
      "notes": "información adicional"
    }
  ],
  "sample_statistics": [
    {
      "vein": "nombre de veta",
      "coefficient_of_variation": 1.2,
      "mean_grade": 14.5,
      "notes": "estadísticas"
    }
  ],
  "totals": {
    "measured_tonnes": 0.0,
    "indicated_tonnes": 0.0,
    "inferred_tonnes": 0.0,
    "measured_indicated_tonnes": 0.0,
    "measured_metal_koz": 0.0,
    "indicated_metal_koz": 0.0,
    "inferred_metal_koz": 0.0,
    "measured_indicated_metal_koz": 0.0,
    "total_drilling_holes": 0,
    "total_drilling_metres": 0.0,
    "total_channel_samples": 0,
    "total_channel_metres": 0.0
  }
}

CONVERSIÓN DE UNIDADES:
- "4.1 Mt" → 4100000.0 toneladas
- "1,893 koz" → 1893.0 (mantén en koz)
- "500 kt" → 500000.0 toneladas

IMPORTANTE: 
- Extrae CADA fila de CADA tabla encontrada
- Si NO hay recursos NI 43-101, pero hay datos de muestreo, extrae esos datos
- NO inventes datos que no estén en el texto
"""

        result = self._call_llm(prompt, content)
        
        if result:
            resources = []
            for r in result.get("data", []):
                resources.append(MineralResource(**r))
            
            cut_offs = []
            for c in result.get("cut_off_grades", []):
                cut_offs.append(CutOffGrade(**c))
            
            return MineralResourcesSection(
                summary=result.get("summary", {}),
                data=resources,
                cut_off_grades=cut_offs,
                drilling_summary=result.get("drilling_summary", []),
                data_availability=result.get("data_availability", []),
                block_model_stats=result.get("block_model_stats", []),
                sample_statistics=result.get("sample_statistics", []),
                totals=result.get("totals", {})
            )
        
        return MineralResourcesSection()
    
    def extract_reserves(self) -> MineralReservesSection:
        """LLAMADA 3: Extrae reservas minerales COMPLETAS."""
        pages = self.table_finder.get_pages_for_extraction("reserves", max_pages=20)
        content = self._get_pages_text(pages)
        
        print(f"    📄 Buscando en {len(pages)} páginas: {pages[:8]}{'...' if len(pages) > 8 else ''}")
        
        prompt = """Eres un experto en extracción exhaustiva de reservas minerales de reportes NI 43-101.

**INSTRUCCIÓN CRÍTICA:**
ESCANEA todas las páginas buscando:
- Tablas "TABLE 15-X"
- Títulos "MINERAL RESERVES", "RESERVE ESTIMATE"
- Palabras "Proven", "Probable"

Si el proyecto NO tiene reservas (exploración/pre-feasibility), retorna arrays vacíos [].

Extrae TODA la información de reservas en formato JSON:

{
  "summary": {
    "mining_method": "Underground/Open Pit",
    "life_of_mine_years": 7.0,
    "mining_rate_tpd": 2000.0,
    "dilution_pct": 15.0,
    "mining_recovery_pct": 85.0
  },
  "data": [
    {
      "area": "nombre del área",
      "category": "Proven/Probable",
      "tonnes": 1515000.0,
      "grade": 12.25,
      "contained_metal": 597.0
    }
  ],
  "cut_off_grades_reserves": [
    {
      "area": "nombre del área",
      "gold_price": 1700.0,
      "smelting_and_refining": 9.25,
      "royalties": 3.52,
      "gold_processing_recovery_pct": 95.2,
      "mining_cost": 114.0,
      "processing_cost": 34.0,
      "ga_cost": 25.0,
      "tailings_sustaining_cost": 1.5,
      "credits": 23.0,
      "final_cut_off_grade": 2.8
    }
  ],
  "totals": {
    "proven_tonnes": 0.0,
    "probable_tonnes": 0.0,
    "proven_probable_tonnes": 0.0,
    "proven_metal_koz": 0.0,
    "probable_metal_koz": 0.0,
    "proven_probable_metal_koz": 0.0,
    "average_grade": 0.0
  }
}

CONVERSIÓN DE UNIDADES:
- "1,515 kt" → 1515000.0 toneladas
- "597 koz" → 597.0 (mantén en koz)

IMPORTANTE:
- Tabla 15-1 puede usar precio diferente a Tabla 14-4
- Si NO hay reservas, retorna arrays vacíos (no es un error)
"""

        result = self._call_llm(prompt, content)
        
        if result:
            reserves = []
            for r in result.get("data", []):
                reserves.append(MineralReserve(**r))
            
            cut_offs_reserves = []
            for c in result.get("cut_off_grades_reserves", []):
                cut_offs_reserves.append(CutOffGradeReserves(**c))
            
            return MineralReservesSection(
                summary=result.get("summary", {}),
                data=reserves,
                cut_off_grades_reserves=cut_offs_reserves,
                totals=result.get("totals", {})
            )
        
        return MineralReservesSection()
    
    def extract_economics(self) -> Economics:
        """LLAMADA 4: Extrae información económica COMPLETA."""
        pages = self.table_finder.get_pages_for_extraction("economics", max_pages=30)
        content = self._get_pages_text(pages)
        
        print(f"    📄 Buscando en {len(pages)} páginas: {pages[:8]}{'...' if len(pages) > 8 else ''}")
        
        prompt = """Eres un experto en extracción exhaustiva de información económica de reportes NI 43-101.

**INSTRUCCIÓN CRÍTICA:**
ESCANEA todas las páginas buscando:
- Tablas "TABLE 20-X", "TABLE 21-X", "TABLE 22-X"
- Títulos: "ECONOMIC ANALYSIS", "BUDGET", "COSTS", "CAPEX", "OPEX"
- Palabras: "NPV", "IRR", "Payback", "Operating Cost", "Capital Cost"

PROYECTOS EN EXPLORACIÓN pueden tener:
- Presupuestos de exploración (TABLE 20-X) en lugar de CAPEX/OPEX de producción
- NO tener NPV/IRR

Extrae TODA la información económica en formato JSON:

{
  "valuation": {
    "npv": null,
    "irr": null,
    "discount_rate": 0.05,
    "currency": "USD",
    "payback_period_years": null
  },
  "cost_structure": {
    "capex": {
      "sustaining": 0.0,
      "non_sustaining": 0.0,
      "total": 0.0
    },
    "opex": {
      "mining_cost_per_tonne": 0.0,
      "processing_cost_per_tonne": 0.0,
      "ga_cost_per_tonne": 0.0,
      "total_cost_per_tonne": 0.0
    },
    "metal_prices": {
      "gold_price_assumption": 0.0,
      "silver_price_assumption": null
    }
  },
  "operating_costs_detail": [
    {
      "description": "descripción del costo",
      "amount": 36758000.0,
      "unit": "USD"
    }
  ],
  "capital_costs_detail": [
    {
      "category": "Sustaining/Non-sustaining/Exploration",
      "description": "descripción",
      "amount": 8774000.0
    }
  ],
  "metallurgy_history": [
    {
      "year": "2019",
      "tonnes_processed": 451450.0,
      "head_grade_au": 15.48,
      "recovery_pct": 95.2,
      "gold_produced_oz": 214036.0
    }
  ],
  "credits": [
    {
      "description": "descripción del crédito",
      "amount": 7682000.0,
      "unit": "USD"
    }
  ],
  "processing_info": {
    "plant_name": "nombre de planta",
    "nominal_capacity_tpd": 2000.0,
    "process_type": "tipo de proceso",
    "recovery_rate_pct": 95.2
  }
}

CONVERSIÓN CRÍTICA:
- Valores en tablas pueden estar en miles (US$ 000s)
- Ejemplo: "$555" en tabla con encabezado "US$ 000" → 555000.0
- Ejemplo: "$36,758" en "US$ 000" → 36758000.0

IMPORTANTE:
- Para proyectos en exploración, extrae "exploration_budget" de TABLE 20-X
- Si NO hay CAPEX/OPEX de producción, usa 0.0 o null
- Extrae CADA línea de cada tabla
"""

        result = self._call_llm(prompt, content)
        
        if result:
            opex_detail = []
            for oc in result.get("operating_costs_detail", []):
                opex_detail.append(OperatingCost(**oc))
            
            capex_detail = []
            for cc in result.get("capital_costs_detail", []):
                capex_detail.append(CapitalCost(**cc))
            
            metall_history = []
            for mh in result.get("metallurgy_history", []):
                metall_history.append(MetallurgyHistory(**mh))
            
            return Economics(
                valuation=result.get("valuation", {}),
                cost_structure=result.get("cost_structure", {}),
                operating_costs_detail=opex_detail,
                capital_costs_detail=capex_detail,
                metallurgy_history=metall_history,
                credits=result.get("credits", []),
                processing_info=result.get("processing_info", {})
            )
        
        return Economics()
    
    def _calculate_validation(self, metadata: ProjectMetadata, 
                             resources: MineralResourcesSection,
                             reserves: MineralReservesSection,
                             economics: Economics) -> ValidationSummary:
        """Calcula el resumen de validación integrado."""
        validation = ValidationSummary()
        
        # Metadata summary
        validation.metadata_summary = {
            "project": metadata.project_info.get("project_name", "N/A"),
            "company": metadata.project_info.get("company_name", "N/A"),
            "country": metadata.location.get("country", "N/A"),
            "region": metadata.location.get("region", "N/A"),
            "effective_date": metadata.report_details.get("effective_date", "N/A"),
            "qps": len(metadata.report_details.get("qualified_persons", [])),
            "mining_titles_count": len(metadata.mining_titles),
            "veins_count": len(metadata.vein_dimensions)
        }
        
        # Resources summary
        if resources.data:
            total_tonnes = sum(r.tonnes for r in resources.data)
            total_metal = sum(r.contained_metal for r in resources.data)
            
            drilling_count = len(resources.drilling_summary)
            
            validation.resources_summary = {
                "count": len(resources.data),
                "total_tonnes": f"{total_tonnes:,.0f}",
                "total_metal_koz": f"{total_metal:,.1f}",
                "categories": list(set(r.category for r in resources.data)),
                "commodity": resources.summary.get("commodity", "Gold"),
                "areas_count": len(set(r.area for r in resources.data if r.area)),
                "drilling_campaigns": drilling_count,
                "expected_drilling_campaigns": 13,
                "cut_off_grades_count": len(resources.cut_off_grades),
                "data_availability_count": len(resources.data_availability),
                "block_model_stats_count": len(resources.block_model_stats),
                "sample_statistics_count": len(resources.sample_statistics),
                "completeness_pct": 100.0 if drilling_count > 0 else 0.0
            }
        else:
            validation.resources_summary = {}
        
        # Reserves summary
        if reserves.data:
            total_tonnes = sum(r.tonnes for r in reserves.data)
            total_metal = sum(r.contained_metal for r in reserves.data)
            
            validation.reserves_summary = {
                "count": len(reserves.data),
                "total_tonnes": f"{total_tonnes:,.0f}",
                "total_metal_koz": f"{total_metal:,.1f}",
                "categories": list(set(r.category for r in reserves.data)),
                "mining_method": reserves.summary.get("mining_method", "N/A"),
                "lom_years": reserves.summary.get("life_of_mine_years"),
                "cut_off_grades_reserves_count": len(reserves.cut_off_grades_reserves),
                "has_table_15_1": len(reserves.cut_off_grades_reserves) > 0
            }
        else:
            validation.reserves_summary = {}
        
        # Economics summary
        capex = economics.cost_structure.get("capex", {}) if economics.cost_structure else {}
        opex = economics.cost_structure.get("opex", {}) if economics.cost_structure else {}
        metal_prices = economics.cost_structure.get("metal_prices", {}) if economics.cost_structure else {}
        
        validation.economics_summary = {
            "capex_total": f"${capex.get('total', 0) or 0:,.0f}",
            "capex_sustaining": f"${capex.get('sustaining', 0) or 0:,.0f}",
            "capex_non_sustaining": f"${capex.get('non_sustaining', 0) or 0:,.0f}",
            "mining_cost_per_t": f"${opex.get('mining_cost_per_tonne', 0) or 0:.2f}",
            "processing_cost_per_t": f"${opex.get('processing_cost_per_tonne', 0) or 0:.2f}",
            "ga_cost_per_t": f"${opex.get('ga_cost_per_tonne', 0) or 0:.2f}",
            "has_npv": economics.valuation.get("npv") is not None if economics.valuation else False,
            "has_irr": economics.valuation.get("irr") is not None if economics.valuation else False,
            "gold_price": f"${metal_prices.get('gold_price_assumption', 0) or 0:,.0f}/oz",
            "opex_detail_count": len(economics.operating_costs_detail) if economics.operating_costs_detail else 0,
            "capex_detail_count": len(economics.capital_costs_detail) if economics.capital_costs_detail else 0,
            "metallurgy_years": len(economics.metallurgy_history) if economics.metallurgy_history else 0,
            "credits_count": len(economics.credits) if economics.credits else 0
        }
        
        # Validaciones adaptadas
        if not metadata.report_details.get("qualified_persons"):
            validation.warnings.append("⚠️  Qualified Persons no extraídos")
        
        # Para proyectos en exploración, no es error no tener recursos/reservas
        project_status = metadata.project_info.get("status", "").lower()
        is_exploration = "exploration" in project_status or "early" in project_status
        
        if not resources.data and not is_exploration:
            validation.errors.append("❌ Recursos minerales vacíos (proyecto no es exploración temprana)")
        elif not resources.data and is_exploration:
            validation.warnings.append("⚠️  Sin recursos NI 43-101 definidos (proyecto en exploración)")
        
        if not reserves.data and not is_exploration:
            validation.warnings.append("⚠️  Reservas minerales vacías")
        
        # Status
        if validation.errors:
            validation.status = "ERROR"
        elif validation.warnings:
            validation.status = "WARNING"
        else:
            validation.status = "OK"
        
        return validation
    
    def extract_all(self) -> MiningReportComplete:
        """Ejecuta las 4 llamadas y consolida TODO."""
        print("🔍 Iniciando extracción EXHAUSTIVA con búsqueda inteligente...")
        print("-" * 80)
        
        # LLAMADA 1
        print("\n📋 [1/4] Extrayendo METADATA COMPLETA...")
        metadata = self.extract_metadata()
        print(f"    ✅ Proyecto: {metadata.project_info.get('project_name', 'N/A')}")
        print(f"    ✅ Títulos mineros: {len(metadata.mining_titles)}")
        print(f"    ✅ Vetas: {len(metadata.vein_dimensions)}")
        
        # LLAMADA 2
        print("\n💎 [2/4] Extrayendo RECURSOS COMPLETOS...")
        resources = self.extract_resources()
        print(f"    ✅ Recursos: {len(resources.data)} registros")
        print(f"    ✅ Cut-off grades: {len(resources.cut_off_grades)}")
        print(f"    ✅ Campañas de perforación: {len(resources.drilling_summary)}")
        
        # LLAMADA 3
        print("\n🏆 [3/4] Extrayendo RESERVAS COMPLETAS...")
        reserves = self.extract_reserves()
        print(f"    ✅ Reservas: {len(reserves.data)} registros")
        
        # LLAMADA 4
        print("\n💰 [4/4] Extrayendo ECONOMÍA COMPLETA...")
        economics = self.extract_economics()
        print(f"    ✅ OPEX detalle: {len(economics.operating_costs_detail)} líneas")
        print(f"    ✅ CAPEX detalle: {len(economics.capital_costs_detail)} líneas")
        print(f"    ✅ Histórico metalúrgico: {len(economics.metallurgy_history)} años")
        
        # VALIDACIÓN
        print("\n✅ Calculando validación...")
        validation = self._calculate_validation(metadata, resources, reserves, economics)
        
        complete_report = MiningReportComplete(
            validation=validation,
            metadata=metadata,
            mineral_resources=resources,
            mineral_reserves=reserves,
            economics=economics
        )
        
        return complete_report


def extract_mining_data(pdf_path: str) -> MiningReportComplete:
    """Función principal."""
    extractor = MiningReportExtractor(pdf_path)
    return extractor.extract_all()