"""
Módulo de procesamiento de comentarios con LLM vía OpenRouter
Mejora los comentarios de gerentes usando IA para análisis profesional
"""

import os
import json
import logging
import requests
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class CommentProcessor:
    """Procesador de comentarios usando LLM"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Inicializar el procesador de comentarios

        Args:
            api_key: API key de OpenRouter (opcional, se puede usar variable de entorno)
        """
        # Cargar variables de entorno del archivo .env
        from dotenv import load_dotenv
        load_dotenv()

        self.api_key = api_key or os.getenv('OPENROUTER_API_KEY')
        self.base_url = os.getenv('OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1')

        # Usar el modelo por defecto o el modelo fallback si está configurado
        self.model = os.getenv('DEFAULT_MODEL', 'anthropic/claude-opus-4.1')
        self.fallback_model = os.getenv('FALLBACK_MODEL', 'anthropic/claude-sonnet-4')

        if not self.api_key:
            logger.warning("No se encontró API key de OpenRouter. Usando procesamiento básico.")

    def process_comments(self, raw_comments: str, data_context: Dict = None) -> str:
        """
        Procesar comentarios crudos y generar análisis profesional

        Args:
            raw_comments: Comentarios sin procesar de los gerentes
            data_context: Contexto adicional (KPIs, marcas problemáticas, etc.)

        Returns:
            Análisis profesional formateado
        """
        if not self.api_key:
            return self._basic_processing(raw_comments)

        try:
            # Construir el prompt para el LLM
            prompt = self._build_prompt(raw_comments, data_context)

            # Llamar a la API de OpenRouter
            response = self._call_llm(prompt)

            if response:
                return response
            else:
                return self._basic_processing(raw_comments)

        except Exception as e:
            logger.error(f"Error procesando comentarios con LLM: {e}")
            return self._basic_processing(raw_comments)

    def _build_prompt(self, raw_comments: str, data_context: Dict = None) -> str:
        """Construir prompt para el LLM"""

        context_info = ""
        if data_context:
            if 'marcas_criticas' in data_context:
                context_info += f"\nMarcas con desempeño crítico: {', '.join(data_context['marcas_criticas'])}"
            if 'kpis_principales' in data_context:
                context_info += f"\nKPIs principales: {data_context['kpis_principales']}"

        prompt = f"""Eres un analista especializado en DYM (empresa boliviana de bebidas alcohólicas). Analiza estos comentarios de gerentes regionales y genera un resumen ejecutivo preciso y contextualizado.

COMENTARIOS ORIGINALES:
{raw_comments}

CONTEXTO OPERATIVO DE DYM:
- DYM maneja aproximadamente 17 marcas principales con presupuesto activo
- Santa Cruz es el centro logístico principal de DYM con el almacén más grande
- Las operaciones regionales siguen planificación mensual basada en presupuestos SOP
- Marcas principales: Casa Real, Havana, Gran Reserva, Singani Mezclador, Solana, etc.
- Regiones principales: Santa Cruz, Cochabamba, La Paz, Potosí, Tarija{context_info}

INSTRUCCIONES ESPECÍFICAS:
1. Menciona SOLO las marcas específicas que aparecen nombradas en los comentarios
2. NUNCA inventes o especules números de marcas afectadas (ej: "7 marcas", "11 marcas")
3. Para Santa Cruz: reconoce su rol como centro logístico, no asumas ineficiencias
4. Distingue entre situaciones normales del negocio y problemas reales
5. Usa lenguaje directo y factual, evita jerga consultora
6. Enfócate en lo que REALMENTE dicen los gerentes, palabra por palabra
7. Si mencionan "cupeo", "quiebres" o "stock", repórtalos como situaciones específicas
8. Evita términos alarmistas como "crítico", "sistemático", "ineficiencias" sin evidencia clara
9. NO agregues números que no están explícitamente en los comentarios originales

FORMATO DESEADO:
- Párrafo 1: Resumen directo de la situación reportada por los gerentes
- Párrafo 2-3: Situaciones específicas por región (solo las mencionadas explícitamente)
- Párrafo final: Acciones puntuales basadas en comentarios reales

REGLAS IMPORTANTES:
- Si un gerente reporta "cupeo en Havana 7", di eso exactamente, no especules sobre toda la línea Havana
- Si hay problemas de stock, reporta la situación, no asumas fallas de planificación
- Mantén el contexto: DYM es una empresa establecida con operaciones maduras
- PROHIBIDO inventar números de marcas afectadas que no estén en los comentarios
- Si no mencionan marcas específicas, usa frases como "reporta situaciones de..." sin especificar cantidad

Genera SOLO el análisis, máximo 3 párrafos, lenguaje directo y profesional."""

        return prompt

    def _call_llm(self, prompt: str, use_fallback: bool = False) -> Optional[str]:
        """Llamar a la API de OpenRouter"""

        # Construir URL completa
        url = f"{self.base_url}/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://dym-wsr-generator.com",
            "X-Title": "DYM WSR Generator"
        }

        # Seleccionar modelo
        model_to_use = self.fallback_model if use_fallback else self.model

        data = {
            "model": model_to_use,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.3,  # Baja temperatura para respuestas más consistentes
            "max_tokens": 1000
        }

        try:
            logger.info(f"Llamando a OpenRouter con modelo: {model_to_use}")
            response = requests.post(
                url,
                headers=headers,
                json=data,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content']
            elif response.status_code == 429 and not use_fallback:
                # Rate limit - intentar con modelo fallback
                logger.warning("Rate limit detectado, intentando con modelo fallback")
                return self._call_llm(prompt, use_fallback=True)
            else:
                logger.error(f"Error en API de OpenRouter: {response.status_code} - {response.text}")
                return None

        except requests.exceptions.Timeout:
            logger.error("Timeout al llamar a OpenRouter")
            return None
        except Exception as e:
            logger.error(f"Error llamando a OpenRouter: {e}")
            return None

    def _basic_processing(self, raw_comments: str) -> str:
        """Procesamiento básico sin LLM"""

        if not raw_comments or raw_comments.strip() == "":
            return "No hay comentarios disponibles para este período."

        # Limpiar y formatear básicamente
        lines = raw_comments.split('.')
        processed_lines = []

        # Agrupar por gerente/región
        comments_by_region = {}
        current_region = "General"

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Detectar región/gerente
            if any(region in line.upper() for region in ['SANTA CRUZ', 'COCHABAMBA', 'LA PAZ', 'POTOSI', 'TARIJA']):
                for region in ['SANTA CRUZ', 'COCHABAMBA', 'LA PAZ', 'POTOSI', 'TARIJA']:
                    if region in line.upper():
                        current_region = region.title()
                        break

            if current_region not in comments_by_region:
                comments_by_region[current_region] = []

            comments_by_region[current_region].append(line)

        # Construir texto formateado
        result = "Los gerentes regionales han reportado las siguientes situaciones:\n\n"

        for region, comments in comments_by_region.items():
            if comments:
                result += f"En {region}: "
                # Consolidar comentarios similares
                unique_comments = list(set([c for c in comments if c]))
                result += ". ".join(unique_comments[:3]) + ".\n\n"

        return result.strip()

    def extract_key_insights(self, processed_comments: str, df_marca) -> Dict:
        """
        Extraer insights clave del análisis procesado

        Args:
            processed_comments: Comentarios ya procesados
            df_marca: DataFrame con datos de marcas

        Returns:
            Diccionario con insights estructurados
        """
        insights = {
            'alertas_criticas': [],
            'oportunidades': [],
            'acciones_recomendadas': []
        }

        # Identificar marcas con problemas basándose en KPIs
        if df_marca is not None and not df_marca.empty:
            # Marcas con bajo desempeño
            marcas_criticas = df_marca[df_marca['AV_SOP'] < -0.3]['marcadir'].tolist()[:5]
            if marcas_criticas:
                insights['alertas_criticas'].append(
                    f"Marcas críticas con desempeño bajo: {', '.join(marcas_criticas)}"
                )

            # Marcas con buen desempeño
            marcas_estrella = df_marca[df_marca['AV_SOP'] > 0.1]['marcadir'].tolist()[:3]
            if marcas_estrella:
                insights['oportunidades'].append(
                    f"Marcas con desempeño destacado: {', '.join(marcas_estrella)}"
                )

        # Extraer patrones del texto procesado
        if 'quiebre' in processed_comments.lower() or 'stock' in processed_comments.lower():
            insights['alertas_criticas'].append("Problemas de inventario detectados en múltiples regiones")
            insights['acciones_recomendadas'].append("Revisar urgentemente la cadena de suministro")

        if 'cupeo' in processed_comments.lower() or 'cupos' in processed_comments.lower():
            insights['alertas_criticas'].append("Restricciones de cupos limitando el crecimiento")
            insights['acciones_recomendadas'].append("Negociar ampliación de cupos con marcas afectadas")

        if 'feria' in processed_comments.lower() or 'evento' in processed_comments.lower():
            insights['oportunidades'].append("Eventos comerciales generando oportunidades de venta")
            insights['acciones_recomendadas'].append("Maximizar participación en eventos próximos")

        return insights


class CommentFormatter:
    """Formateador visual de comentarios para HTML"""

    @staticmethod
    def format_html_comments(processed_comments: str, insights: Dict = None) -> str:
        """
        Formatear comentarios procesados para el reporte HTML

        Args:
            processed_comments: Comentarios ya procesados
            insights: Insights extraídos (opcional)

        Returns:
            HTML formateado
        """
        html = '<div class="comments-analysis">'

        # Sección principal de comentarios
        html += f'''
        <div class="comments-main">
            <h4 style="color: #1e3a8a; margin-bottom: 15px;">
                <span style="font-size: 18px;">💬</span> ANÁLISIS DE COMENTARIOS REGIONALES
            </h4>
            <div class="comments-text" style="line-height: 1.6; color: #374151;">
                {processed_comments.replace('\n\n', '</p><p>').replace('\n', '<br>')}
            </div>
        </div>
        '''

        # Agregar insights si están disponibles
        if insights:
            html += '<div class="insights-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; margin-top: 20px;">'

            # Alertas críticas
            if insights.get('alertas_criticas'):
                html += '''
                <div class="insight-card" style="background: #fef2f2; border-left: 4px solid #ef4444; padding: 12px; border-radius: 4px;">
                    <h5 style="color: #991b1b; margin: 0 0 8px 0; font-size: 13px;">
                        ⚠️ ALERTAS CRÍTICAS
                    </h5>
                    <ul style="margin: 0; padding-left: 20px; font-size: 12px; color: #7f1d1d;">
                '''
                for alerta in insights['alertas_criticas']:
                    html += f'<li>{alerta}</li>'
                html += '</ul></div>'

            # Oportunidades
            if insights.get('oportunidades'):
                html += '''
                <div class="insight-card" style="background: #f0fdf4; border-left: 4px solid #22c55e; padding: 12px; border-radius: 4px;">
                    <h5 style="color: #166534; margin: 0 0 8px 0; font-size: 13px;">
                        ✨ OPORTUNIDADES
                    </h5>
                    <ul style="margin: 0; padding-left: 20px; font-size: 12px; color: #14532d;">
                '''
                for oportunidad in insights['oportunidades']:
                    html += f'<li>{oportunidad}</li>'
                html += '</ul></div>'

            # Acciones recomendadas
            if insights.get('acciones_recomendadas'):
                html += '''
                <div class="insight-card" style="background: #eff6ff; border-left: 4px solid #3b82f6; padding: 12px; border-radius: 4px;">
                    <h5 style="color: #1e3a8a; margin: 0 0 8px 0; font-size: 13px;">
                        🎯 ACCIONES RECOMENDADAS
                    </h5>
                    <ul style="margin: 0; padding-left: 20px; font-size: 12px; color: #1e293b;">
                '''
                for accion in insights['acciones_recomendadas']:
                    html += f'<li>{accion}</li>'
                html += '</ul></div>'

            html += '</div>'

        html += '</div>'

        return html