"""
Generador de narrativa IA para analisis de PY Sistema.
Usa OpenRouter (Claude) para generar un analisis estructurado
del Nowcast (blend HW + Run Rate) con detalle por marca.
"""

import os
import logging
import requests
import pandas as pd
import numpy as np
from typing import Optional, Dict
from datetime import datetime

logger = logging.getLogger(__name__)


class ProjectionNarrativeGenerator:
    """Genera narrativa IA explicando PY Sistema y comparando con PY Gerente."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        from dotenv import load_dotenv
        load_dotenv()

        self.api_key = api_key or os.getenv('OPENROUTER_API_KEY')
        self.base_url = os.getenv('OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1')
        self.model = model or os.getenv('DEFAULT_MODEL', 'anthropic/claude-opus-4.6')
        self.fallback_model = os.getenv('FALLBACK_MODEL', 'anthropic/claude-sonnet-4.6')

    def generate_narrative(
        self,
        projection_data: Dict,
        marca_totales_df: pd.DataFrame,
        current_date: datetime,
        nowcast_meta: Dict = None
    ) -> str:
        if not self.api_key:
            logger.info("Sin API key de OpenRouter, omitiendo narrativa de proyecciones")
            return ""

        try:
            if marca_totales_df.empty:
                return ""

            tabla_md = self._build_data_table(marca_totales_df, current_date)
            prompt = self._build_prompt(tabla_md, current_date, nowcast_meta or {})

            response = self._call_llm(prompt)
            if not response:
                return ""

            return self._build_structured_html(response, current_date, nowcast_meta or {}, marca_totales_df)

        except Exception as e:
            logger.warning(f"Error generando narrativa de proyecciones: {e}")
            return ""

    def _build_data_table(self, marca_totales_df: pd.DataFrame, current_date: datetime) -> str:
        """Construye tabla markdown con datos de PY Sistema por marca, incluyendo contexto historico."""
        py_col = f'py_{current_date.year}_bob'
        avance_col = f'avance_{current_date.year}_bob'
        vendido_col = f'vendido_{current_date.year - 1}_bob'

        mes_abrev = ['', 'Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'][current_date.month]
        lines = [f"| Marca | Vendido {mes_abrev} {current_date.year - 1} | Modelo Historico (HW) | Crec. Implicito HW | Ritmo Actual (extrap.) | PY Sistema | PY Gerente | Spread |"]
        lines.append("|-------|-------------------|----------------------|-------------------|----------------------|------------|------------|--------|")

        for _, row in marca_totales_df.iterrows():
            marca = row.get('marcadir', '?')
            vendido_prev = row.get(vendido_col, 0) or 0
            avance = row.get(avance_col, 0) or 0
            run_rate = row.get('run_rate_bob', 0) or 0
            hw = row.get('py_estadistica_bob', 0) or 0
            py_sist = row.get('py_sistema_bob', 0) or 0
            py_ger = row.get(py_col, 0) or 0
            spread = row.get('spread_sistema', None)

            vendido_str = f"${vendido_prev:,.0f}" if vendido_prev else "-"
            rr_str = f"${run_rate:,.0f}" if run_rate else "-"
            hw_str = f"${hw:,.0f}" if hw else "-"
            sist_str = f"${py_sist:,.0f}" if py_sist else "-"
            ger_str = f"${py_ger:,.0f}" if py_ger else "-"
            spread_str = f"{spread:+.1%}" if pd.notna(spread) else "-"

            # Crecimiento implicito: (HW / vendido_prev) - 1
            if hw > 0 and vendido_prev > 0:
                crec = (hw / vendido_prev) - 1
                crec_str = f"{crec:+.1%}"
            else:
                crec_str = "-"

            lines.append(f"| {marca} | {vendido_str} | {hw_str} | {crec_str} | {rr_str} | {sist_str} | {ger_str} | {spread_str} |")

        # Totales
        t_vend = marca_totales_df[vendido_col].sum() if vendido_col in marca_totales_df.columns else 0
        t_rr = marca_totales_df['run_rate_bob'].sum() if 'run_rate_bob' in marca_totales_df.columns else 0
        t_hw = marca_totales_df['py_estadistica_bob'].sum() if 'py_estadistica_bob' in marca_totales_df.columns else 0
        t_sist = marca_totales_df['py_sistema_bob'].sum() if 'py_sistema_bob' in marca_totales_df.columns else 0
        t_ger = marca_totales_df[py_col].sum() if py_col in marca_totales_df.columns else 0
        t_spread = (t_ger / t_sist - 1) if t_sist > 0 else None
        t_spread_str = f"{t_spread:+.1%}" if t_spread is not None else "-"
        t_crec = f"{(t_hw / t_vend - 1):+.1%}" if t_vend > 0 and t_hw > 0 else "-"

        lines.append(f"| **TOTAL** | **${t_vend:,.0f}** | **${t_hw:,.0f}** | **{t_crec}** | **${t_rr:,.0f}** | **${t_sist:,.0f}** | **${t_ger:,.0f}** | **{t_spread_str}** |")

        return "\n".join(lines)

    def _build_prompt(self, tabla_md: str, current_date: datetime, nowcast_meta: Dict) -> str:
        mes_nombre = [
            '', 'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
            'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'
        ][current_date.month]

        w = nowcast_meta.get('w', 0)
        dias_avance = nowcast_meta.get('dias_laborales_avance', 0)
        dias_mes = nowcast_meta.get('dias_laborales_mes', 0)
        w_pct = w * 100

        prev_year = current_date.year - 1

        return f"""Eres un analista financiero senior de DYM, empresa boliviana lider en distribucion de bebidas alcoholicas premium.
Audiencia: directores y gerentes comerciales en una reunion semanal. Debes ser claro, concreto y financieramente solido.

DATOS DE PROYECCION PY SISTEMA — {mes_nombre.upper()} {current_date.year}:

{tabla_md}

COMO FUNCIONA PY SISTEMA:
- PY Sistema combina dos fuentes: (1) el Modelo Historico Holt-Winters (HW), que analiza 24-36 meses de ventas reales para identificar tendencias y estacionalidad, y (2) el Ritmo Actual de ventas del mes extrapolado al cierre.
- Hoy llevamos {dias_avance} de {dias_mes} dias laborales ({w_pct:.0f}% del mes):
  - {w_pct:.0f}% del PY Sistema viene del Ritmo Actual
  - {100-w_pct:.0f}% viene del Modelo Historico
- Al inicio de mes el modelo historico domina; conforme avanzan las ventas reales, el ritmo actual gana peso.
- "Crec. Implicito HW" = cuanto crecimiento o caida proyecta el modelo vs el mismo mes de {prev_year}. Es la senal mas importante: indica si el modelo ve una marca al alza, estable o en declive.

QUE CAPTURA EL MODELO HOLT-WINTERS (para que entiendas las proyecciones):
- **Tendencia**: Si la marca viene creciendo o declinando de forma sostenida en los ultimos 24-36 meses. Una marca con tendencia descendente tendra un HW por debajo del vendido del año anterior, incluso si el mes pasado fue bueno.
- **Estacionalidad**: Patrones ciclicos que se repiten cada año. Ejemplos tipicos en DYM: (a) marcas de singani/whisky suben en invierno y fiestas (jun-dic); (b) marcas de cerveza/vodka pican en verano (dic-mar); (c) marcas de eventos (espumantes) pican en dic y caen en ene-feb. Si el Crec. Implicito HW es negativo para una marca en un mes especifico, puede ser por estacionalidad desfavorable (ej: singani en verano) O por tendencia estructural a la baja.
- **Divergencia HW vs Ritmo Actual**: Cuando el Ritmo Actual (extrapolacion de ventas reales) difiere mucho del HW, hay una senal importante: (a) si el ritmo actual esta MUY por encima del HW, las primeras jornadas del mes arrancaron con traccion inusual — verificar si es sostenible o un evento puntual; (b) si esta MUY por debajo, la demanda real esta floja vs lo que el patron historico esperaba.
- IMPORTANTE: Para cada marca, INTERPRETA por que el modelo proyecta lo que proyecta. No solo digas "el modelo proyecta $X". Explica si es por tendencia descendente sostenida, por estacionalidad desfavorable de este mes, o ambos. Esto ayuda al director a entender si es algo ciclico (se recuperara) o estructural (requiere accion).

CONTEXTO:
- **PY Gerente**: Proyeccion de cierre ingresada por el gerente comercial. Incluye negociaciones, expectativas, informacion cualitativa.
- **Spread**: (PY Gerente / PY Sistema) - 1. Positivo = gerente mas optimista que el sistema; negativo = mas conservador.
- **Vendido {mes_nombre} {prev_year}**: Lo que realmente se vendio en el mismo mes del ano anterior. Es la referencia historica directa.
- IMPORTANTE: Los gerentes tipicamente ingresan sus proyecciones en la segunda semana del mes. Si PY Gerente es $0 o muy bajo, NO es conservadurismo — es que aun no la han cargado.

INSTRUCCIONES — Genera contenido para 2 secciones usando estas etiquetas exactas:

[MARCAS_CLAVE]
Para las 5-6 marcas con mayor PY Sistema (por volumen absoluto BOB), genera un analisis financiero con este enfoque:
- **Nombre Marca** — PY Sistema: $X. En {mes_nombre} {prev_year} se vendieron $Y. El modelo historico proyecta $HW para este mes, lo que implica un crecimiento/caida de Z% interanual. [2-3 oraciones interpretando: (1) Explica QUE PATRON CAPTURA el modelo — ¿la tendencia de los ultimos 24-36 meses es ascendente, estable o descendente? ¿Este mes tiene estacionalidad favorable o desfavorable para esta marca? (2) Si el ritmo actual difiere significativamente del HW, mencionarlo y explicar que implica — ¿las primeras jornadas arrancaron con mayor/menor traccion de la esperada? (3) Si el crecimiento implicito HW es negativo, distinguir si es por estacionalidad del mes o por tendencia estructural a la baja.]
- Si PY Gerente es $0 o cercano a $0, mencionar que el gerente aun no ha cargado una proyeccion representativa (monto actual = extrapolacion del avance, no una carga manual).
- Solo incluye marcas con PY Sistema > $100,000.
- El foco es que el director entienda POR QUE el sistema proyecta ese numero para cada marca: que patrones historicos (tendencia y/o estacionalidad) respaldan la proyeccion, y si las ventas reales del mes la confirman o la desafian.

[SPREAD_ANALYSIS]
Genera 3-4 bullet points analizando el spread:
- Bullet 1: Spread total nacional y que significa en terminos practicos
- Bullet 2: Las marcas con mayor divergencia positiva (gerente optimista vs sistema) — solo si existen
- Bullet 3: Las marcas con mayor divergencia negativa (gerente conservador vs sistema) — solo si existen
- Bullet 4: Conclusion o accion requerida (si los gerentes no han cargado PY, mencionarlo como la accion principal)

REGLAS:
- Tono: ejecutivo, directo, con datos concretos. Como si presentaras en un comite comercial.
- Idioma: espanol
- NO inventes datos — usa exclusivamente los valores de la tabla
- Cuando cites un monto, usa formato $X,XXX (sin decimales para montos grandes)
- No uses emojis
- Cada bullet de marca debe ser 3-4 oraciones, con sustancia financiera y explicacion de los patrones HW
- Cada bullet de spread debe ser 2-3 oraciones maximo
- Usa "productos" en lugar de "SKUs" y "referencias" o "presentaciones" en lugar de "lenguas" — la audiencia es comercial, no tecnica"""

    def _call_llm(self, prompt: str, use_fallback: bool = False) -> Optional[str]:
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
            "max_tokens": 3000
        }

        try:
            logger.info(f"Generando narrativa de proyecciones con {model_to_use}...")
            response = requests.post(url, headers=headers, json=data, timeout=60)

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

    def _parse_sections(self, response_text: str) -> Dict[str, str]:
        sections = {'marcas_clave': '', 'spread_analysis': ''}
        current_section = None
        current_lines = []

        for line in response_text.split('\n'):
            stripped = line.strip()
            if '[MARCAS_CLAVE]' in stripped:
                if current_section:
                    sections[current_section] = '\n'.join(current_lines).strip()
                current_section = 'marcas_clave'
                current_lines = []
            elif '[SPREAD_ANALYSIS]' in stripped:
                if current_section:
                    sections[current_section] = '\n'.join(current_lines).strip()
                current_section = 'spread_analysis'
                current_lines = []
            elif current_section:
                current_lines.append(line)

        if current_section:
            sections[current_section] = '\n'.join(current_lines).strip()

        # Fallback
        if not any(sections.values()):
            sections['spread_analysis'] = response_text.strip()

        return sections

    def _format_bullets_html(self, text: str) -> str:
        """Convierte bullets markdown a HTML con estilo."""
        lines = text.strip().split('\n')
        html_items = []

        for line in lines:
            line = line.strip()
            if not line or line == '---':
                continue
            if line.startswith('- '):
                line = line[2:]
            # Convert markdown bold
            while '**' in line:
                line = line.replace('**', '<strong>', 1).replace('**', '</strong>', 1)
            html_items.append(
                f'<li style="margin-bottom: 8px; line-height: 1.55; padding-left: 4px; font-size: 11.5px;">{line}</li>'
            )

        if html_items:
            return (
                '<ul style="margin: 6px 0; padding-left: 18px; '
                'list-style-type: disc; color: #374151; font-size: 11.5px;">'
                + ''.join(html_items) + '</ul>'
            )
        # Fallback: paragraph
        text_html = text.replace('\n\n', '</p><p>').replace('\n', ' ')
        return f'<p style="color: #374151; line-height: 1.65;">{text_html}</p>'

    def _build_structured_html(self, response_text: str, current_date: datetime,
                                nowcast_meta: Dict, marca_totales_df: pd.DataFrame = None) -> str:
        sections = self._parse_sections(response_text)
        w = nowcast_meta.get('w', 0)
        dias_avance = nowcast_meta.get('dias_laborales_avance', 0)
        dias_mes = nowcast_meta.get('dias_laborales_mes', 0)

        mes_nombre = [
            '', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
            'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
        ][current_date.month]

        bar_ritmo = min(w * 100, 100)
        bar_hw = 100 - bar_ritmo

        marcas_html = self._format_bullets_html(sections['marcas_clave']) if sections['marcas_clave'] else ''
        spread_html = self._format_bullets_html(sections['spread_analysis']) if sections['spread_analysis'] else ''

        return f"""
        <div style="margin: 25px 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">

            <!-- Header sutil -->
            <div style="
                background: #f8fafc;
                border: 1px solid #e2e8f0;
                border-left: 4px solid #3B82F6;
                border-radius: 8px 8px 0 0;
                padding: 14px 20px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            ">
                <div>
                    <span style="font-size: 14px; font-weight: 700; color: #1e3a5f; letter-spacing: 0.3px;">
                        PY Sistema
                    </span>
                    <span style="font-size: 13px; color: #64748b; margin-left: 8px;">
                        {mes_nombre} {current_date.year}
                    </span>
                </div>
                <div style="
                    background: #EBF5FF;
                    padding: 4px 12px;
                    border-radius: 12px;
                    font-size: 12px;
                    color: #2563eb;
                    font-weight: 600;
                ">
                    Dia {dias_avance} de {dias_mes} laborales ({bar_ritmo:.0f}% del mes)
                </div>
            </div>

            <!-- Explicacion del modelo -->
            <div style="
                background: #f0f7ff;
                padding: 10px 18px;
                border-left: 4px solid #3B82F6;
                border-right: 1px solid #e2e8f0;
                font-size: 11px;
                line-height: 1.5;
                color: #475569;
            ">
                <strong style="color: #1e3a5f;">Que es PY Sistema:</strong>
                Proyeccion hibrida que combina dos fuentes &mdash;
                el <strong>Modelo Historico (Holt-Winters)</strong>, que analiza 24-36 meses de ventas reales
                para capturar tendencias y estacionalidad de cada marca, y el
                <strong>Ritmo Actual</strong> de ventas del mes extrapolado al cierre.
                Hoy, con {bar_ritmo:.0f}% del mes transcurrido, el modelo historico aporta el {bar_hw:.0f}%
                del calculo y el ritmo actual el {bar_ritmo:.0f}%. Conforme avance el mes, las ventas reales
                tomaran mayor protagonismo.
            </div>

            <!-- Marcas Clave -->
            <div style="
                background: white;
                padding: 10px 18px;
                border-left: 4px solid #3B82F6;
                border-right: 1px solid #e2e8f0;
                border-top: 1px solid #f1f5f9;
            ">
                <h5 style="margin: 0 0 4px 0; color: #1e3a5f; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 700;">
                    Detalle por marca
                </h5>
                {marcas_html}
            </div>

            <!-- Spread Analysis -->
            <div style="
                background: #fffbeb;
                padding: 10px 18px;
                border-left: 4px solid #EA580C;
                border-right: 1px solid #e2e8f0;
                border-bottom: 1px solid #e2e8f0;
                border-radius: 0 0 8px 8px;
            ">
                <h5 style="margin: 0 0 4px 0; color: #92400e; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 700;">
                    Spread: PY Gerente vs PY Sistema
                </h5>
                {spread_html}
            </div>

            <!-- Footer -->
            <p style="
                margin: 6px 0 0 0;
                font-size: 10px;
                color: #94a3b8;
                font-style: italic;
                text-align: right;
            ">Generado por IA (Claude) | PY Sistema = {bar_ritmo:.0f}% Ritmo Actual + {bar_hw:.0f}% Modelo Historico</p>
        </div>
        """
