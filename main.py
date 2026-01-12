import os
import sys
from dotenv import load_dotenv

# Asegurar que el módulo src3 esté en el path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.processor import extract_mining_data
from src.utils import save_to_json
import json

load_dotenv()

def validate_modular_extraction(data: dict) -> dict:
    """Valida la extracción modular con las 4 categorías."""
    validation = {
        "status": "OK",
        "warnings": [],
        "errors": [],
        "summary": {}
    }
    
    # 1. VALIDAR METADATA
    metadata = data.get("metadata", {})
    if not metadata:
        validation["errors"].append("❌ Metadata faltante")
    else:
        project_info = metadata.get("project_info", {})
        location = metadata.get("location", {})
        report_details = metadata.get("report_details", {})
        
        validation["summary"]["metadata"] = {
            "project": project_info.get("project_name", "N/A"),
            "company": project_info.get("company_name", "N/A"),
            "country": location.get("country", "N/A"),
            "region": location.get("region", "N/A"),
            "effective_date": report_details.get("effective_date", "N/A"),
            "qps": len(report_details.get("qualified_persons", []))
        }
        
        if not report_details.get("qualified_persons"):
            validation["warnings"].append("⚠️  Qualified Persons no extraídos")
    
    # 2. VALIDAR RECURSOS MINERALES
    mineral_resources = data.get("mineral_resources", {})
    resources_data = mineral_resources.get("data", [])
    
    if not resources_data:
        validation["errors"].append("❌ Recursos minerales vacíos")
    else:
        total_tonnes = sum(r.get("tonnes", 0) for r in resources_data)
        total_metal_koz = sum(r.get("contained_metal", 0) for r in resources_data)
        
        validation["summary"]["mineral_resources"] = {
            "count": len(resources_data),
            "total_tonnes": f"{total_tonnes:,.0f}",
            "total_metal_koz": f"{total_metal_koz:,.1f}",
            "categories": [r.get("category") for r in resources_data],
            "commodity": mineral_resources.get("summary", {}).get("commodity", "N/A")
        }
        
        # Validar que las toneladas sean realistas
        for resource in resources_data:
            if resource.get("tonnes", 0) < 500_000:
                validation["warnings"].append(
                    f"⚠️  Recurso '{resource['category']}' con tonelaje bajo: {resource['tonnes']:,.0f}"
                )
    
    # 3. VALIDAR RESERVAS MINERALES
    mineral_reserves = data.get("mineral_reserves", {})
    reserves_data = mineral_reserves.get("data", [])
    
    if not reserves_data:
        validation["errors"].append("❌ Reservas minerales vacías")
    else:
        total_tonnes = sum(r.get("tonnes", 0) for r in reserves_data)
        total_metal_koz = sum(r.get("contained_metal", 0) for r in reserves_data)
        
        validation["summary"]["mineral_reserves"] = {
            "count": len(reserves_data),
            "total_tonnes": f"{total_tonnes:,.0f}",
            "total_metal_koz": f"{total_metal_koz:,.1f}",
            "categories": [r.get("category") for r in reserves_data],
            "mining_method": mineral_reserves.get("summary", {}).get("mining_method", "N/A")
        }
        
        # Las reservas deben ser menores que los recursos
        resources_total = sum(r.get("tonnes", 0) for r in resources_data)
        if total_tonnes > resources_total:
            validation["errors"].append(
                f"❌ Reservas ({total_tonnes:,.0f} t) mayores que recursos ({resources_total:,.0f} t)"
            )
    
    # 4. VALIDAR INFORMACIÓN ECONÓMICA
    economics = data.get("economics", {})
    cost_structure = economics.get("cost_structure", {})
    valuation = economics.get("valuation", {})
    
    if not cost_structure:
        validation["warnings"].append("⚠️  Estructura de costos faltante")
    
    capex = cost_structure.get("capex", {})
    opex = cost_structure.get("opex", {})
    
    validation["summary"]["economics"] = {
        "capex_total": f"${capex.get('total', 0):,.0f}",
        "capex_sustaining": f"${capex.get('sustaining', 0):,.0f}",
        "capex_non_sustaining": f"${capex.get('non_sustaining', 0):,.0f}",
        "mining_cost_per_t": f"${opex.get('mining_cost_per_tonne', 0):.2f}",
        "processing_cost_per_t": f"${opex.get('processing_cost_per_tonne', 0):.2f}",
        "has_npv": valuation.get("npv") is not None,
        "has_irr": valuation.get("irr") is not None,
        "gold_price": f"${cost_structure.get('metal_prices', {}).get('gold_price_assumption', 0):,.0f}/oz"
    }
    
    # Determinar estado final
    if validation["errors"]:
        validation["status"] = "ERROR"
    elif validation["warnings"]:
        validation["status"] = "WARNING"
    
    return validation

def print_comprehensive_report(data: dict):
    """Imprime un reporte COMPLETO con todos los datos."""
    validation = data.get("validation", {})
    
    print("\n" + "=" * 80)
    print("📊 REPORTE COMPLETO DE EXTRACCIÓN")
    print("=" * 80)
    
    # Estado de validación
    status_emoji = {"OK": "✅", "WARNING": "⚠️ ", "ERROR": "❌"}
    print(f"\nEstado: {status_emoji.get(validation.get('status'), '❓')} {validation.get('status')}")
    
    if validation.get("errors"):
        print("\n🚨 ERRORES:")
        for error in validation["errors"]:
            print(f"  {error}")
    
    if validation.get("warnings"):
        print("\n⚠️  ADVERTENCIAS:")
        for warning in validation["warnings"]:
            print(f"  {warning}")
    
    # METADATA
    print("\n" + "=" * 80)
    print("📋 CATEGORÍA 1: METADATA DEL PROYECTO")
    print("=" * 80)
    meta_sum = validation.get("metadata_summary", {})
    print(f"  Proyecto: {meta_sum.get('project')}")
    print(f"  Compañía: {meta_sum.get('company')}")
    print(f"  Ubicación: {meta_sum.get('region')}, {meta_sum.get('country')}")
    print(f"  Fecha efectiva: {meta_sum.get('effective_date')}")
    print(f"  Qualified Persons: {meta_sum.get('qps')}")
    print(f"  Títulos mineros: {meta_sum.get('mining_titles_count')}")
    print(f"  Vetas documentadas: {meta_sum.get('veins_count')}")
    
    # RECURSOS
    print("\n" + "=" * 80)
    print("💎 CATEGORÍA 2: RECURSOS MINERALES")
    print("=" * 80)
    res_sum = validation.get("resources_summary", {})
    print(f"  Commodity: {res_sum.get('commodity')}")
    print(f"  Áreas evaluadas: {res_sum.get('areas_count')}")
    print(f"  Categorías: {', '.join(res_sum.get('categories', []))}")
    print(f"  Registros de recursos: {res_sum.get('count')}")
    print(f"  Toneladas totales: {res_sum.get('total_tonnes')}")
    print(f"  Contenido metálico: {res_sum.get('total_metal_koz')} koz")
    print(f"\n  📊 Completitud de Tablas:")
    print(f"    - Tabla 10-1 (Perforación): {res_sum.get('drilling_campaigns')}/{res_sum.get('expected_drilling_campaigns')} registros ({res_sum.get('completeness_pct')}%)")
    print(f"    - Tabla 14-1 (Disponibilidad): {res_sum.get('data_availability_count')} registros")
    print(f"    - Tabla 14-4 (Cut-offs): {res_sum.get('cut_off_grades_count')} áreas")
    print(f"    - Tabla 14-2 (Block model): {res_sum.get('block_model_stats_count')} registros")
    print(f"    - Tabla 14-3 (Estadísticas): {res_sum.get('sample_statistics_count')} registros")
    
    # RESERVAS
    print("\n" + "=" * 80)
    print("🏆 CATEGORÍA 3: RESERVAS MINERALES")
    print("=" * 80)
    rev_sum = validation.get("reserves_summary", {})
    print(f"  Método de minería: {rev_sum.get('mining_method')}")
    print(f"  Vida útil (LOM): {rev_sum.get('lom_years')} años" if rev_sum.get('lom_years') else "  Vida útil: N/A")
    print(f"  Categorías: {', '.join(rev_sum.get('categories', []))}")
    print(f"  Registros de reservas: {rev_sum.get('count')}")
    print(f"  Toneladas totales: {rev_sum.get('total_tonnes')}")
    print(f"  Contenido metálico: {rev_sum.get('total_metal_koz')} koz")
    print(f"\n  📊 Completitud de Tablas:")
    print(f"    - Tabla 15-1 (Cut-offs a $1,700/oz): {'✅ Completa' if rev_sum.get('has_table_15_1') else '❌ Faltante'}")
    print(f"    - Variables de cut-off: {rev_sum.get('cut_off_grades_reserves_count')} áreas")
    
    # ECONOMÍA
    print("\n" + "=" * 80)
    print("💰 CATEGORÍA 4: INFORMACIÓN ECONÓMICA")
    print("=" * 80)
    econ_sum = validation.get("economics_summary", {})
    print(f"  CAPEX Total: {econ_sum.get('capex_total')}")
    print(f"    - Sustaining: {econ_sum.get('capex_sustaining')}")
    print(f"    - Non-sustaining: {econ_sum.get('capex_non_sustaining')}")
    print(f"  CAPEX líneas de detalle: {econ_sum.get('capex_detail_count')}")
    print(f"  OPEX por tonelada:")
    print(f"    - Mining: {econ_sum.get('mining_cost_per_t')}")
    print(f"    - Processing: {econ_sum.get('processing_cost_per_t')}")
    print(f"    - G&A: {econ_sum.get('ga_cost_per_t')}")
    print(f"  OPEX líneas de detalle: {econ_sum.get('opex_detail_count')}")
    print(f"  Histórico metalúrgico: {econ_sum.get('metallurgy_years')} años")
    print(f"  Créditos documentados: {econ_sum.get('credits_count')}")
    print(f"  Precio de oro asumido: {econ_sum.get('gold_price')}")
    print(f"  NPV disponible: {'✅' if econ_sum.get('has_npv') else '❌'}")
    print(f"  IRR disponible: {'✅' if econ_sum.get('has_irr') else '❌'}")
    
    print("\n" + "=" * 80)

def main():
    data_dir = "data"
    output_dir = "output"
    
    # Asegurar que el directorio de salida existe
    os.makedirs(output_dir, exist_ok=True)
    
    # Obtener lista de archivos PDF
    pdf_files = [f for f in os.listdir(data_dir) if f.lower().endswith(".pdf")]
    
    if not pdf_files:
        print(f"⚠️  No se encontraron archivos PDF en '{data_dir}'")
        return

    print("=" * 80)
    print("🚀 EXTRACCIÓN MODULAR DE REPORTE MINERO NI 43-101")
    print("=" * 80)
    print(f"� Directorio: {data_dir}")
    print(f"� Archivos encontrados: {len(pdf_files)}")
    print("=" * 80)

    for i, filename in enumerate(pdf_files, 1):
        pdf_path = os.path.join(data_dir, filename)
        file_basename = os.path.splitext(filename)[0]
        output_file = os.path.join(output_dir, f"mining_report_{file_basename}.json")
        
        print(f"\n🔄 Procesando archivo {i}/{len(pdf_files)}: {filename}")
        print(f"   📄 Ruta: {pdf_path}")
        print(f"   💾 Salida esperada: {output_file}")
        
        try:
            # Extraer datos con el nuevo método modular
            result = extract_mining_data(pdf_path)
            data_dict = result.dict()
            
            # Guardar JSON principal
            save_to_json(data_dict, output_file)
            
            # Imprimir reporte completo
            print_comprehensive_report(data_dict)
            
            # Resumen del archivo actual
            print(f"\n✅ Archivo {i} completado: {data_dict['validation']['status']}")
            
        except Exception as e:
            print(f"\n❌ Error procesando {filename}: {str(e)}")
            continue

    # Resumen final del proceso
    print("\n" + "=" * 80)
    print("🏁 PROCESO COMPLETADO")
    print("=" * 80)

if __name__ == "__main__":
    main()