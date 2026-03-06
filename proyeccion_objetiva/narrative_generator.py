"""
Generador de narrativa IA para análisis comparativo de proyecciones.
Usa OpenRouter (Claude) para generar un análisis de divergencias entre
PY Gerente y PY Estadística (Holt-Winters).
"""

import os
import logging
import requests
import pandas as pd
from typing import Optional, Dict
from datetime import datetime

logger = logging.getLogger(__name__)


class ProjectionNarrativeGenerator:
    """Genera narrativa IA comparando PY Gerente vs PY Estadística."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        from dotenv import load_dotenv
        load_dotenv()

        self.api_key = api_key or os.getenv('OPENROUTER_API_KEY')
        self.base_url = os.getenv('OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1')
        self.model = model or os.getenv('DEFAULT_MODEL', 'anthropic/claude-opus-4.6')
        self.fallback_model = os.getenv('FALLBACK_MODEL', 'anthropic/claude-sonnet-4')

    def generate_narrative(
        self,
        projection_data: Dict,
        marca_totales_df: pd.DataFrame,
        current_date: datetime
    ) -> str:
        """
        Genera narrativa HTML analizando divergencias entre proyecciones.

        Args:
            projection_data: Dict con 'by_marca' (comparativo triple pilar)
            marca_totales_df: DataFrame con marca_totales (incluye py_estadistica_bob)
            current_date: Fecha actual del reporte

        Returns:
            HTML string con la narrativa, o cadena vacía si falla
        """
        if not self.api_key:
            logger.info("Sin API key de OpenRouter, omitiendo narrativa de proyecciones")
            return ""

        try:
            by_marca = projection_data.get('by_marca', pd.DataFrame())
            if by_marca.empty:
                return ""

            # Construir tabla de datos para el prompt
            tabla_md = self._build_data_table(by_marca, marca_totales_df, current_date)
            prompt = self._build_prompt(tabla_md, current_date)

            # Llamar LLM
            response = self._call_llm(prompt)
            if not response:
                return ""

            # Envolver en HTML
            return self._wrap_html(response)

        except Exception as e:
            logger.warning(f"Error generando narrativa de proyecciones: {e}")
            return ""

    def _build_data_table(
        self,
        by_marca: pd.DataFrame,
        marca_totales_df: pd.DataFrame,
        current_date: datetime
    ) -> str:
        """Construye tabla markdown con los datos comparativos."""
        py_col = f'py_{current_date.year}_bob'

        lines = ["| Marca | PY Gerente | PY Estadística (HW) | Spread | Confianza |"]
        lines.append("|-------|-----------|---------------------|--------|-----------|")

        for _, row in by_marca.iterrows():
            marca = row.get('marcadir', '?')
            py_ger = row.get('py_gerente_bob', 0)
            py_est = row.get('py_estadistica_bob', 0)
            spread = row.get('spread', None)
            confidence = row.get('confidence', '-')

            py_ger_str = f"${py_ger:,.0f}" if pd.notna(py_ger) and py_ger else "-"
            py_est_str = f"${py_est:,.0f}" if pd.notna(py_est) and py_est else "-"
            spread_str = f"{spread:+.1%}" if pd.notna(spread) else "-"

            lines.append(f"| {marca} | {py_ger_str} | {py_est_str} | {spread_str} | {confidence or '-'} |")

        # Totales
        total_ger = by_marca['py_gerente_bob'].dropna().sum() if 'py_gerente_bob' in by_marca.columns else 0
        total_est = by_marca['py_estadistica_bob'].dropna().sum() if 'py_estadistica_bob' in by_marca.columns else 0
        total_spread = (total_ger / total_est - 1) if total_est > 0 else None
        total_spread_str = f"{total_spread:+.1%}" if total_spread is not None else "-"
        lines.append(f"| **TOTAL** | **${total_ger:,.0f}** | **${total_est:,.0f}** | **{total_spread_str}** | - |")

        return "\n".join(lines)

    def _build_prompt(self, tabla_md: str, current_date: datetime) -> str:
        """Construye el prompt para el LLM."""
        mes_nombre = [
            '', 'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
            'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'
        ][current_date.month]

        return f"""Eres un analista financiero senior de DYM, empresa boliviana líder en distribución de bebidas alcohólicas premium (marcas como Casa Real, Branca, Havana, Campos de Solana, Redbull, entre otras).
Audiencia: directores y gerentes comerciales en una reunión de revisión semanal.

DATOS COMPARATIVOS DE PROYECCIONES — {mes_nombre.upper()} {current_date.year}:

{tabla_md}

CONTEXTO DE LAS PROYECCIONES:
- **PY Gerente**: Proyección de cierre mensual ingresada por el gerente comercial de cada marca. Refleja su lectura del mercado, negociaciones en curso, y expectativas de sell-in.
- **PY Estadística (Holt-Winters)**: Modelo de series temporales que usa 24-36 meses de historia real para capturar tendencia secular y patrones estacionales. Es una referencia objetiva y cuantitativa — no un reemplazo del criterio gerencial, sino un espejo estadístico.
- **PY Operativa (Cobertura × Hit Rate × Drop Size)**: Modelo bottom-up actualmente en desarrollo. Se integrará próximamente para completar el triángulo de validación.
- **Spread**: Divergencia entre PY Gerente y PY Estadística. Positivo = gerente más optimista que la historia; negativo = gerente más conservador.

INSTRUCCIONES — Redacta un análisis financiero ejecutivo:

1. **Apertura (1-2 oraciones)**: Panorama general del spread total nacional. ¿Hay consenso o divergencia sistémica entre lo que proyectan los gerentes y lo que sugiere la data histórica?

2. **Análisis de gaps críticos (2-3 párrafos)**: Este es el corazón del análisis.
   - Identifica las marcas con mayor divergencia absoluta en BOB (no solo porcentual — una marca pequeña con +50% puede ser menos relevante que una marca grande con +15%)
   - Para cada gap relevante, plantea hipótesis posibles: ¿el gerente tiene información que la historia no captura (lanzamiento, promoción, pérdida de cliente)? ¿O el optimismo/conservadurismo no está respaldado?
   - Agrupa si hay patrones: ¿las marcas premium divergen en una dirección y las masivas en otra?
   - Menciona las marcas con spread cercano a 0 (consenso) como referencia positiva

3. **Implicación para el cierre de {mes_nombre} (1 párrafo)**: Si los gerentes están sistemáticamente por encima o debajo del modelo estadístico, ¿qué riesgo implica para el cumplimiento del presupuesto? ¿Hay marcas donde el gap requiere atención inmediata?

REGLAS:
- Tono: ejecutivo, directo, datos concretos. Como si presentaras en un comité comercial.
- Máximo 5 párrafos totales
- Idioma: español
- NO inventes datos — usa exclusivamente los valores de la tabla
- Cuando cites un valor, usa el formato exacto de la tabla
- No uses emojis ni viñetas — párrafos fluidos
- Si el spread total es cercano a 0 (±5%), destaca el consenso como señal positiva"""

    def _call_llm(self, prompt: str, use_fallback: bool = False) -> Optional[str]:
        """Llama a OpenRouter API."""
        url = f"{self.base_url}/chat/completions"
        model_to_use = self.fallback_model if use_fallback else self.model

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://dym-wsr-generator.com",
            "X-Title": "DYM WSR Generator - Projection Narrative"
        }

        data = {
            "model": model_to_use,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": 1500
        }

        try:
            logger.info(f"Generando narrativa de proyecciones con {model_to_use}...")
            response = requests.post(url, headers=headers, json=data, timeout=45)

            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content']
            elif response.status_code == 429 and not use_fallback:
                logger.warning("Rate limit, intentando con modelo fallback")
                return self._call_llm(prompt, use_fallback=True)
            else:
                logger.error(f"Error OpenRouter: {response.status_code} - {response.text[:200]}")
                return None

        except requests.exceptions.Timeout:
            logger.error("Timeout generando narrativa de proyecciones")
            return None
        except Exception as e:
            logger.error(f"Error llamando OpenRouter para narrativa: {e}")
            return None

    def _wrap_html(self, narrative_text: str) -> str:
        """Envuelve la narrativa en HTML con estilo."""
        # Convertir saltos de línea a <p> tags
        paragraphs = narrative_text.strip().split('\n\n')
        html_paragraphs = ''.join(f'<p>{p.strip()}</p>' for p in paragraphs if p.strip())

        return f"""
        <div class="projection-narrative" style="
            margin: 25px 0;
            padding: 20px 25px;
            background: linear-gradient(135deg, #f0f7ff 0%, #e8f0fe 100%);
            border-left: 4px solid #3B82F6;
            border-radius: 8px;
            font-size: 14px;
            line-height: 1.7;
            color: #1e293b;
        ">
            <h4 style="
                margin: 0 0 15px 0;
                color: #1e3a8a;
                font-size: 16px;
            ">ANALISIS COMPARATIVO DE PROYECCIONES</h4>
            <div class="narrative-text" style="color: #374151;">
                {html_paragraphs}
            </div>
            <p style="
                margin: 15px 0 0 0;
                font-size: 11px;
                color: #94a3b8;
                font-style: italic;
            ">Generado por IA (Claude) - Referencia analitica, no reemplaza el juicio del equipo comercial.</p>
        </div>
        """
