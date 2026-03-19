"""
Generador de narrativa IA para Drivers de Performance.
Usa OpenRouter (Claude Opus) para generar un diagnostico operativo
basado en las tendencias de Cobertura, Hit Rate y Drop Size.
"""

import os
import logging
import requests
import pandas as pd
import numpy as np
from typing import Optional, Dict
from datetime import datetime

from .drivers_engine import DriversEngine

logger = logging.getLogger(__name__)


class DriversNarrativeGenerator:
    """Genera narrativa IA diagnosticando los drivers operativos por marca."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        from dotenv import load_dotenv
        load_dotenv()

        self.api_key = api_key or os.getenv('OPENROUTER_API_KEY')
        self.base_url = os.getenv('OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1')
        self.model = model or os.getenv('DEFAULT_MODEL', 'anthropic/claude-opus-4.6')
        self.fallback_model = os.getenv('FALLBACK_MODEL', 'anthropic/claude-sonnet-4')

    def generate_diagnostic(
        self,
        drivers_df: pd.DataFrame,
        current_date: datetime,
        level: str = "marca",
        detail_df: pd.DataFrame = None,
    ) -> str:
        """
        Genera diagnostico IA en HTML basado en los drivers.

        Args:
            drivers_df: DataFrame con drivers (output de DriversEngine)
            current_date: Fecha actual del reporte
            level: "marca", "ciudad" o "canal"
            detail_df: DataFrame de detalle (ej: ciudad×marca, canal×subcanal para enriquecer analisis)

        Returns:
            HTML string con el diagnostico, o "" si falla
        """
        if not self.api_key:
            logger.info("[Drivers Narrative] Sin API key, omitiendo diagnostico IA")
            return ""

        try:
            if drivers_df.empty:
                return ""

            key_col_map = {'marca': 'marca', 'ciudad': 'ciudad', 'canal': 'canal'}
            key_col = key_col_map.get(level, 'marca')
            tabla_md = self._build_data_table(drivers_df, key_col=key_col)

            # Agregar detalle para enriquecer el analisis
            detail_md = ""
            if detail_df is not None and not detail_df.empty:
                if level == "ciudad":
                    detail_md = self._build_city_brand_detail(detail_df)
                elif level == "marca":
                    detail_md = self._build_marca_submarca_detail(detail_df)
                elif level == "canal":
                    detail_md = self._build_canal_subcanal_detail(detail_df)

            prompt = self._build_prompt(tabla_md, current_date, level=level, detail_md=detail_md)

            response = self._call_llm(prompt)
            if not response:
                return ""

            return self._format_html(response)

        except Exception as e:
            logger.warning(f"[Drivers Narrative] Error generando diagnostico {level}: {e}")
            return ""

    def _build_marca_submarca_detail(self, detail_df: pd.DataFrame) -> str:
        """Construye tabla markdown con submarcas/subfamilias por marca para enriquecer el analisis."""
        lines = ["\nDETALLE SUBMARCA/SUBFAMILIA POR MARCA (top subfamilias por venta en cada marca):"]
        lines.append("| Marca | Submarca | Cob (cli) | Δ VSLY Cob | Freq. | Δ VSLY Freq | DS (BOB) | Δ VSLY DS |")
        lines.append("|-------|----------|-----------|-----------|-------|------------|----------|----------|")

        for marca, marca_group in detail_df.groupby('marca'):
            top_subs = marca_group.nlargest(4, 'venta_total')
            for _, row in top_subs.iterrows():
                sub = row.get('submarca', '?')
                cob = int(row.get('cobertura', 0))
                hr = row.get('hit_rate', 0)
                ds = row.get('drop_size', 0)
                cob_t = row.get('cobertura_trend', None)
                hr_t = row.get('hitrate_trend', None)
                ds_t = row.get('dropsize_trend', None)
                cob_t_str = f"{cob_t:+.1%}" if cob_t is not None else "-"
                hr_t_str = f"{hr_t:+.1%}" if hr_t is not None else "-"
                ds_t_str = f"{ds_t:+.1%}" if ds_t is not None else "-"
                lines.append(
                    f"| {marca} | {sub} | {cob:,} | {cob_t_str} | {hr:.2f} | {hr_t_str} | ${ds:,.0f} | {ds_t_str} |"
                )

        return "\n".join(lines)

    def _build_city_brand_detail(self, detail_df: pd.DataFrame) -> str:
        """Construye tabla markdown con top 3 marcas por ciudad para enriquecer el analisis."""
        lines = ["\nDETALLE MARCA POR CIUDAD (top 3 marcas por venta en cada ciudad):"]
        lines.append("| Ciudad | Marca | Cob (cli) | Freq. | DS (BOB) | Venta |")
        lines.append("|--------|-------|-----------|-------|----------|-------|")

        for ciudad, city_group in detail_df.groupby('ciudad'):
            top3 = city_group.nlargest(3, 'venta_total')
            for _, row in top3.iterrows():
                marca = row.get('marca', '?')
                cob = int(row.get('cobertura', 0))
                hr = row.get('hit_rate', 0)
                ds = row.get('drop_size', 0)
                venta = row.get('venta_total', 0)
                lines.append(
                    f"| {ciudad} | {marca} | {cob:,} | {hr:.2f} | ${ds:,.0f} | ${venta:,.0f} |"
                )

        return "\n".join(lines)

    def _build_canal_subcanal_detail(self, detail_df: pd.DataFrame) -> str:
        """Construye tabla markdown con top subcanales por canal para enriquecer el analisis."""
        lines = ["\nDETALLE SUBCANAL POR CANAL (top subcanales por venta en cada canal):"]
        lines.append("| Canal | Subcanal | Cob (cli) | Δ VSLY Cob | Freq. | Δ VSLY Freq | DS (BOB) | Δ VSLY DS |")
        lines.append("|-------|----------|-----------|-----------|-------|------------|----------|----------|")

        for canal, canal_group in detail_df.groupby('canal'):
            top_subs = canal_group.nlargest(4, 'venta_total')
            for _, row in top_subs.iterrows():
                sub = row.get('subcanal', '?')
                cob = int(row.get('cobertura', 0))
                hr = row.get('hit_rate', 0)
                ds = row.get('drop_size', 0)
                cob_t = row.get('cobertura_trend', None)
                hr_t = row.get('hitrate_trend', None)
                ds_t = row.get('dropsize_trend', None)
                cob_t_str = f"{cob_t:+.1%}" if cob_t is not None else "-"
                hr_t_str = f"{hr_t:+.1%}" if hr_t is not None else "-"
                ds_t_str = f"{ds_t:+.1%}" if ds_t is not None else "-"
                lines.append(
                    f"| {canal} | {sub} | {cob:,} | {cob_t_str} | {hr:.2f} | {hr_t_str} | ${ds:,.0f} | {ds_t_str} |"
                )

        return "\n".join(lines)

    def _build_data_table(self, df: pd.DataFrame, key_col: str = 'marca') -> str:
        """Construye tabla markdown con drivers."""
        key_label = {'marca': 'Marca', 'ciudad': 'Ciudad', 'canal': 'Canal'}.get(key_col, key_col.title())
        lines = [
            f"| {key_label} | Cobertura (cli) | Δ VSLY Cob | Frecuencia (ped/cli) | Δ VSLY Freq | Drop Size (BOB/ped) | Δ VSLY DS | Diagnostico Auto |"
        ]
        lines.append("|-------|----------------|-----------|-------------------|---------|--------------------|---------|--------------------|")

        for _, row in df.iterrows():
            marca = row.get(key_col, '?')
            cob = row.get('cobertura', 0)
            cob_t = row.get('cobertura_trend', None)
            hr = row.get('hit_rate', 0)
            hr_t = row.get('hitrate_trend', None)
            ds = row.get('drop_size', 0)
            ds_t = row.get('dropsize_trend', None)

            cob_str = f"{int(cob):,}" if cob else "-"
            hr_str = f"{hr:.2f}" if hr else "-"
            ds_str = f"${ds:,.0f}" if ds else "-"

            cob_t_str = f"{cob_t:+.1%}" if cob_t is not None else "-"
            hr_t_str = f"{hr_t:+.1%}" if hr_t is not None else "-"
            ds_t_str = f"{ds_t:+.1%}" if ds_t is not None else "-"

            diag = DriversEngine.diagnose_trend(cob_t, hr_t, ds_t)

            lines.append(
                f"| {marca} | {cob_str} | {cob_t_str} | {hr_str} | {hr_t_str} | {ds_str} | {ds_t_str} | {diag} |"
            )

        return "\n".join(lines)

    def _build_prompt(self, tabla_md: str, current_date: datetime, level: str = "marca", detail_md: str = "") -> str:
        mes_nombre = [
            '', 'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
            'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'
        ][current_date.month]

        entity_map = {
            'marca': ('marca', 'MARCA', 'NOMBRE_MARCA'),
            'ciudad': ('ciudad', 'CIUDAD', 'NOMBRE_CIUDAD'),
            'canal': ('canal', 'CANAL', 'NOMBRE_CANAL'),
        }
        entity, entity_upper, entity_label = entity_map.get(level, ('marca', 'MARCA', 'NOMBRE_MARCA'))

        context_extra = ""
        if level == "marca":
            context_extra = """
- DYM distribuye marcas premium: Casa Real (singani, dominante), Branca (amargo, alta penetracion), whiskies importados (Chivas, Johnnie Walker), vodkas, gins, vinos
- Cada marca tiene submarcas/subfamilias con dinamicas distintas (ej: Casa Real tiene Singani, Ron, Vodka — pueden ir en direcciones opuestas)
- Si hay detalle de submarca disponible, USALO para enriquecer: identifica que subfamilias impulsan o frenan la marca (ej: "arrastrada por caida en Singani" o "crecimiento liderado por Ron")"""
        elif level == "ciudad":
            context_extra = """
- DYM opera en las principales ciudades de Bolivia: Santa Cruz (sede), Cochabamba, La Paz, El Alto, Tarija, Sucre, Oruro, Potosi, Trinidad
- Cada ciudad tiene dinamicas de mercado distintas: Santa Cruz es el mercado mas grande, La Paz/El Alto tienen alta frecuencia pero menor ticket, ciudades intermedias tienen menor cobertura
- El analisis debe considerar el tamaño relativo de cada plaza
- Si hay detalle de marca por ciudad disponible, USALO para enriquecer: menciona las marcas que impulsan o frenan cada ciudad"""
        elif level == "canal":
            context_extra = """
- DYM opera a traves de multiples canales de distribucion, cada uno con dinamicas distintas:
  - **MAYORISTAS**: Distribuidores grandes que revenden. Alto volumen, frecuencia alta, ticket grande. El motor de volumen.
  - **NIGHT**: Bares, discotecas, karaokes, night clubs. Venta on-premise con alto ticket por pedido.
  - **LICORERIAS**: Puntos de venta tradicional (licorerias de barrio y modernas). Alta cobertura, frecuencia media.
  - **MODERNO**: Supermercados, micromercados. Canal formal con frecuencia estable pero margenes menores.
  - **HORECA**: Hoteles, restaurantes, cafeterias. On-premise con ticket medio-alto.
  - **TDB**: Tiendas de barrio. Masivo, alta cobertura, ticket bajo.
  - **TIENDAS PROPIAS**: Puntos de venta propios de DYM. Control total de experiencia.
  - **EVENTOS**: Ventas a eventos, ferias, salones. Estacional y volatil.
  - **INSTITUCIONAL**: Empresas, instituciones. Bajo volumen pero ticket alto.
  - **E-COMMERCE**: Canal digital (Shopify, WhatsApp). En crecimiento.
- El analisis debe considerar el ROL de cada canal: Mayoristas es volumen puro, Night/Horeca son rentabilidad, TDB/Licorerias son cobertura de mercado
- Si hay detalle de SUBCANAL disponible, USALO para enriquecer: identifica que subcanales impulsan o frenan el canal (ej: "Licorerias arrastrada por caida en Licoreria Tradicional" o "Night impulsado por crecimiento en Discotecas")"""

        return f"""Eres un analista de operaciones comerciales de DYM, empresa boliviana lider en distribucion de bebidas alcoholicas premium.
Audiencia: directores y gerentes comerciales.

DRIVERS DE PERFORMANCE POR {entity_upper} — Same-to-Date (STD): {mes_nombre} {current_date.year} (al dia {current_date.day}) vs {mes_nombre} {current_date.year - 1} (mismos dias):

{tabla_md}
{detail_md}

DEFINICIONES:
- **Cobertura (cli)**: COUNT(DISTINCT clientes) que compraron en el periodo. Mide el ALCANCE de la fuerza de ventas.
- **Frecuencia (ped/cli)**: Pedidos / clientes — cuantas veces compra cada cliente. Mide la FRECUENCIA de compra.
- **Drop Size (BOB/ped)**: SUM(venta) / pedidos — venta promedio por pedido. Mide el TICKET PROMEDIO.
- **Formula**: Venta = Cobertura x Frecuencia x Drop Size (multiplicacion exacta).
- **Δ VSLY** (Versus Last Year): Variacion porcentual vs mismo periodo del año anterior. Positivo = mejorando, negativo = deteriorando.
- Si una {entity} no tiene Δ VSLY (muestra "-"), analiza su perfil absoluto: tamaño de cobertura, frecuencia vs promedio, ticket vs promedio.{context_extra}

LOGICA DE DIAGNOSTICO:
| Cobertura | Frecuencia | Drop Size | Diagnostico |
|-----------|------------|-----------|-------------|
| baja | estable | estable | Problema de ruta/cobertura — menos clientes en cartera |
| estable | baja | estable | Problema de conversion — clientes compran menos seguido |
| estable | estable | baja | Problema de mix/precio — menor ticket por pedido |
| baja | baja | baja | Problema sistemico — todas las palancas deteriorandose |

INSTRUCCIONES:
Genera un diagnostico ejecutivo para CADA {entity} de la tabla. Debe haber exactamente un bullet point por {entity}, en el mismo orden de la tabla.

Para cada {entity}, el formato OBLIGATORIO es:
- **{entity_label} — [Titular breve de 3-5 palabras].** [Analisis de 2-3 oraciones explicando que palancas estan mejorando o deteriorandose, que significa operativamente, y cual es la prioridad de accion.]

Despues de todos los bullets, incluye 1 parrafo de conclusion general con la implicacion operativa para el equipo comercial.

REGLAS:
- Tono: ejecutivo, directo, orientado a accion
- Idioma: espanol
- NO inventes datos — usa exclusivamente los valores de la tabla
- Cada {entity} DEBE tener su propio bullet point con analisis sustantivo (no solo repetir numeros)
- Cuando cites un numero, usa el formato exacto de la tabla
- No uses emojis
- Si una {entity} tiene todas las palancas estables o en crecimiento, igualmente analiza su dinamica positiva
- Si no hay Δ VSLY disponible, analiza el perfil absoluto comparando contra las otras {entity}s de la tabla
- Si hay tabla de DETALLE disponible (submarcas o marcas por ciudad), INCORPORALA en tu analisis para dar insights mas profundos"""

    def _call_llm(self, prompt: str, use_fallback: bool = False) -> Optional[str]:
        url = f"{self.base_url}/chat/completions"
        model_to_use = self.fallback_model if use_fallback else self.model

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://dym-wsr-generator.com",
            "X-Title": "DYM WSR Generator - Drivers Diagnostic"
        }

        data = {
            "model": model_to_use,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": 4000
        }

        try:
            logger.info(f"[Drivers Narrative] Generando diagnostico con {model_to_use}...")
            response = requests.post(url, headers=headers, json=data, timeout=60)

            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content']
            elif response.status_code == 429 and not use_fallback:
                logger.warning("[Drivers Narrative] Rate limit, intentando fallback")
                return self._call_llm(prompt, use_fallback=True)
            else:
                logger.error(f"[Drivers Narrative] Error OpenRouter: {response.status_code}")
                return None

        except requests.exceptions.Timeout:
            logger.error("[Drivers Narrative] Timeout")
            return None
        except Exception as e:
            logger.error(f"[Drivers Narrative] Error: {e}")
            return None

    def _format_html(self, response_text: str) -> str:
        """Convierte la respuesta del LLM en HTML con estilo."""
        lines = response_text.strip().split('\n')
        html_items = []
        closing_paragraph = []
        in_closing = False

        for line in lines:
            line = line.strip()
            if not line:
                if html_items:
                    in_closing = True
                continue

            if line.startswith('- ') or line.startswith('* '):
                line = line[2:]
                in_closing = False
            elif line.startswith('**') and not in_closing:
                pass  # Bold line as bullet

            # Convert markdown bold
            processed = line
            while '**' in processed:
                processed = processed.replace('**', '<strong>', 1).replace('**', '</strong>', 1)

            if in_closing:
                closing_paragraph.append(processed)
            else:
                html_items.append(
                    f'<li style="margin-bottom: 8px; line-height: 1.6; padding-left: 4px;">{processed}</li>'
                )

        html = ""
        if html_items:
            html += (
                '<ul style="margin: 8px 0; padding-left: 18px; '
                'list-style-type: disc; color: #374151;">'
                + ''.join(html_items) + '</ul>'
            )
        if closing_paragraph:
            html += (
                '<p style="margin: 12px 0 0 0; color: #475569; '
                'font-size: 12.5px; line-height: 1.6; '
                'border-top: 1px solid #e2e8f0; padding-top: 10px;">'
                + ' '.join(closing_paragraph) + '</p>'
            )

        return html
