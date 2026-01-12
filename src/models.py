from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

# ============================================================================
# CATEGORÍA 1: METADATA DEL PROYECTO (EXPANDIDA)
# ============================================================================

class ProjectMetadata(BaseModel):
    """Categoría 1: Metadata completa del proyecto."""
    project_info: Dict[str, Any] = Field(default_factory=dict)
    location: Dict[str, Any] = Field(default_factory=dict)
    report_details: Dict[str, Any] = Field(default_factory=dict)
    mining_titles: List[Dict[str, Any]] = Field(default_factory=list)  # Tabla 4-1
    vein_dimensions: List[Dict[str, Any]] = Field(default_factory=list)  # Tabla 7-1

# ============================================================================
# CATEGORÍA 2: RECURSOS MINERALES (EXPANDIDA)
# ============================================================================

class MineralResource(BaseModel):
    """Recurso mineral individual con área específica."""
    area: Optional[str] = None  # El Silencio, Providencia, Sandra K, etc.
    category: str
    tonnes: float
    grade: float
    contained_metal: float

class CutOffGrade(BaseModel):
    """Cut-off grade para recursos (Tabla 14-4)."""
    area: str = Field(description="Nombre del área")
    gold_price: Optional[float] = Field(default=None, description="Precio del oro asumido (USD/oz)")
    smelting_and_refining: Optional[float] = Field(default=None, description="Costos de fundición y refinación")
    royalties: Optional[float] = Field(default=None, description="Regalías")
    gold_processing_recovery_pct: Optional[float] = Field(default=None, description="Recuperación en procesamiento (%)")
    mining_cost: Optional[float] = Field(default=None, description="Costo de minería")
    processing_cost: Optional[float] = Field(default=None, description="Costo de procesamiento")
    ga_cost: Optional[float] = Field(default=None, description="Costos G&A")
    tailings_sustaining_cost: Optional[float] = Field(default=None, description="Costos de relaves")
    credits: Optional[float] = Field(default=None, description="Créditos")
    final_cut_off_grade: Optional[float] = Field(default=None, description="Cut-off grade final")

class CutOffGradeReserves(BaseModel):
    """Cut-off grade para reservas (Tabla 15-1)."""
    area: str = Field(description="Nombre del área")
    gold_price: Optional[float] = Field(default=None, description="Precio del oro asumido (USD/oz)")
    smelting_and_refining: Optional[float] = Field(default=None, description="Costos de fundición y refinación")
    royalties: Optional[float] = Field(default=None, description="Regalías")
    gold_processing_recovery_pct: Optional[float] = Field(default=None, description="Recuperación en procesamiento (%)")
    mining_cost: Optional[float] = Field(default=None, description="Costo de minería")
    processing_cost: Optional[float] = Field(default=None, description="Costo de procesamiento")
    ga_cost: Optional[float] = Field(default=None, description="Costos G&A")
    tailings_sustaining_cost: Optional[float] = Field(default=None, description="Costos de relaves")
    credits: Optional[float] = Field(default=None, description="Créditos")
    final_cut_off_grade: Optional[float] = Field(default=None, description="Cut-off grade final")

class MineralResourcesSection(BaseModel):
    """Sección completa de recursos minerales con detalles."""
    summary: Dict[str, Any] = Field(default_factory=dict)
    data: List[MineralResource] = Field(default_factory=list)
    cut_off_grades: List[CutOffGrade] = Field(default_factory=list)  # Tabla 14-4
    drilling_summary: List[Dict[str, Any]] = Field(default_factory=list)  # Tabla 10-1 COMPLETA
    data_availability: List[Dict[str, Any]] = Field(default_factory=list)  # Tabla 14-1 COMPLETA
    block_model_stats: List[Dict[str, Any]] = Field(default_factory=list)  # Tabla 14-2
    sample_statistics: List[Dict[str, Any]] = Field(default_factory=list)  # Tabla 14-3
    totals: Dict[str, Any] = Field(default_factory=dict)  # Totales calculados

# ============================================================================
# CATEGORÍA 3: RESERVAS MINERALES (EXPANDIDA)
# ============================================================================

class MineralReserve(BaseModel):
    """Reserva mineral individual con área específica."""
    area: Optional[str] = None
    category: str
    tonnes: float
    grade: float
    contained_metal: float

class MineralReservesSection(BaseModel):
    """Sección completa de reservas minerales con detalles."""
    summary: Dict[str, Any] = Field(default_factory=dict)
    data: List[MineralReserve] = Field(default_factory=list)
    cut_off_grades_reserves: List[CutOffGradeReserves] = Field(default_factory=list)  # Tabla 15-1
    totals: Dict[str, Any] = Field(default_factory=dict)  # Totales calculados

# ============================================================================
# CATEGORÍA 4: INFORMACIÓN ECONÓMICA (EXPANDIDA)
# ============================================================================

class OperatingCost(BaseModel):
    """Costo operativo detallado."""
    description: str
    amount: float
    unit: str = "USD"

class CapitalCost(BaseModel):
    """Costo de capital detallado."""
    category: str  # Sustaining / Non-sustaining
    description: str
    amount: float

class MetallurgyHistory(BaseModel):
    """Histórico de operación de planta."""
    year: str
    tonnes_processed: float
    head_grade_au: float
    recovery_pct: float
    gold_produced_oz: float

class Economics(BaseModel):
    """Información económica completa y detallada."""
    valuation: Dict[str, Any] = Field(default_factory=dict)
    cost_structure: Dict[str, Any] = Field(default_factory=dict)
    operating_costs_detail: List[OperatingCost] = Field(default_factory=list)  # Tabla 21-1
    capital_costs_detail: List[CapitalCost] = Field(default_factory=list)  # Tabla 21-4
    metallurgy_history: List[MetallurgyHistory] = Field(default_factory=list)  # Tabla 13-1
    credits: List[Dict[str, Any]] = Field(default_factory=list)  # Tabla 21-5
    processing_info: Dict[str, Any] = Field(default_factory=dict)  # Sección 13/17

# ============================================================================
# MODELO FINAL CONSOLIDADO CON VALIDACIÓN
# ============================================================================

class ValidationSummary(BaseModel):
    """Resumen de validación integrado."""
    status: str = "OK"
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    metadata_summary: Dict[str, Any] = Field(default_factory=dict)
    resources_summary: Dict[str, Any] = Field(default_factory=dict)
    reserves_summary: Dict[str, Any] = Field(default_factory=dict)
    economics_summary: Dict[str, Any] = Field(default_factory=dict)

class MiningReportComplete(BaseModel):
    """Modelo completo del reporte minero NI 43-101 con validación."""
    validation: ValidationSummary = Field(default_factory=ValidationSummary)
    metadata: ProjectMetadata
    mineral_resources: MineralResourcesSection
    mineral_reserves: MineralReservesSection
    economics: Economics