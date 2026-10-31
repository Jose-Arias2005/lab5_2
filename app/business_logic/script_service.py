import json
import logging
import re
from typing import List, Dict, Any
from app.config import settings

logger = logging.getLogger("marketing_app.script_service")

class ScriptService:
    @classmethod
    def generate_scripts(cls, company_name: str, industry: str) -> List[Dict[str, Any]]:
        """
        Genera 3 propuestas de guiones publicitarios para TikTok:
        - Opción A: Enfoque dinámico / viral (humor o gancho rápido).
        - Opción B: Enfoque profesional / valor diferencial y beneficios.
        - Opción C: Enfoque promocional / llamada a la acción con urgencia.
        
        Optimizado para mínimo consumo de tokens en Gemini (gemini-1.5-flash)
        con fallback local en caso de ausencia de API Key o error de cuota.
        """
        api_key = settings.GEMINI_API_KEY.strip()
        if not api_key or api_key == "tu_api_key_de_gemini":
            logger.warning("GEMINI_API_KEY no configurada o por defecto. Activando fallback local inmediato.")
            return cls._get_local_fallback_scripts(company_name, industry)

        try:
            return cls._call_gemini_api(company_name, industry)
        except Exception as e:
            logger.error("Error al invocar la API de Gemini (%s). Activando fallback local seguro: %s", settings.GEMINI_MODEL, e)
            return cls._get_local_fallback_scripts(company_name, industry)

    @classmethod
    def _call_gemini_api(cls, company_name: str, industry: str) -> List[Dict[str, Any]]:
        # Prompt conciso para minimizar tokens de entrada y salida
        prompt = f"""Genera 3 guiones de video vertical TikTok (9:16) para '{company_name}' del rubro '{industry}'.
Devuelve SOLO un JSON válido con esta lista de 3 objetos:
[
  {{
    "option_type": "A",
    "title": "Título corto y llamativo",
    "approach": "Enfoque dinámico / viral (humor o gancho rápido)",
    "hook": "Gancho inicial de 3 segundos",
    "narration": "Voz en off breve (máx 25 palabras)",
    "cta": "Llamada a la acción final",
    "scene_prompts": ["Prompt 1 en inglés para foto publicitaria", "Prompt 2 en inglés", "Prompt 3 en inglés"],
    "scene_subtitles": ["Subtítulo 1 para escena 1", "Subtítulo 2 para escena 2", "Subtítulo 3 para escena 3"]
  }},
  {{
    "option_type": "B",
    "title": "Título",
    "approach": "Enfoque profesional / valor diferencial y beneficios",
    "hook": "Gancho inicial",
    "narration": "Voz en off (máx 25 palabras)",
    "cta": "Llamada a la acción",
    "scene_prompts": ["Prompt 1 en inglés", "Prompt 2 en inglés", "Prompt 3 en inglés"],
    "scene_subtitles": ["Subtítulo 1", "Subtítulo 2", "Subtítulo 3"]
  }},
  {{
    "option_type": "C",
    "title": "Título",
    "approach": "Enfoque promocional / llamada a la acción con urgencia",
    "hook": "Gancho inicial",
    "narration": "Voz en off (máx 25 palabras)",
    "cta": "Llamada a la acción",
    "scene_prompts": ["Prompt 1 en inglés", "Prompt 2 en inglés", "Prompt 3 en inglés"],
    "scene_subtitles": ["Subtítulo 1", "Subtítulo 2", "Subtítulo 3"]
  }}
]
Notas: scene_prompts deben ser en inglés descriptivo fotorrealista para generar imágenes publicitarias verticales 9:16 sin texto."""

        raw_text = None
        models_to_try = [settings.GEMINI_MODEL, "gemini-3.8-flash", "gemini-2.5-flash"]

        # Intento con SDK oficial moderno google-genai
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=settings.GEMINI_API_KEY)
            for m in models_to_try:
                try:
                    response = client.models.generate_content(
                        model=m,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            temperature=0.7,
                            max_output_tokens=2048,
                            response_mime_type="application/json"
                        )
                    )
                    raw_text = response.text
                    if raw_text:
                        logger.info("Guiones generados exitosamente con modelo Gemini: %s", m)
                        break
                except Exception as model_err:
                    logger.warning("Intento con modelo '%s' no disponible (%s). Probando siguiente...", m, model_err)

        except ImportError:
            # Fallback a SDK google-generativeai
            import google.generativeai as genai_legacy
            genai_legacy.configure(api_key=settings.GEMINI_API_KEY)
            for m in models_to_try:
                try:
                    model = genai_legacy.GenerativeModel(
                        model_name=m,
                        generation_config={"temperature": 0.7, "max_output_tokens": 900, "response_mime_type": "application/json"}
                    )
                    response = model.generate_content(prompt)
                    raw_text = response.text
                    if raw_text:
                        break
                except Exception:
                    pass

        if not raw_text:
            raise ValueError("Respuesta vacía desde Gemini API")

        # Limpieza de bloques de código markdown
        cleaned_text = re.sub(r"^```(?:json)?\s*", "", raw_text.strip(), flags=re.MULTILINE)
        cleaned_text = re.sub(r"```$", "", cleaned_text.strip(), flags=re.MULTILINE)

        parsed = json.loads(cleaned_text)
        if isinstance(parsed, list) and len(parsed) >= 3:
            return parsed[:3]
        raise ValueError("El JSON retornado no contiene los 3 guiones requeridos")

    @classmethod
    def _get_local_fallback_scripts(cls, company_name: str, industry: str) -> List[Dict[str, Any]]:
        """
        Fallback local garantizado. Genera 3 guiones de alta calidad para cualquier negocio
        asegurando que la aplicación nunca se congele ni lance error 500.
        """
        logger.info("Generando guiones con motor de fallback local para '%s' (%s)", company_name, industry)

        return [
            {
                "option_type": "A",
                "title": f"¡Lo que nadie te dijo de {company_name}!",
                "approach": "Enfoque dinámico / viral (humor o gancho rápido)",
                "hook": f"¿Pensabas que todos en {industry} eran iguales? ¡Mira esto!",
                "narration": f"Deja de perder el tiempo buscando alternativas. En {company_name} revolucionamos {industry} con resultados reales desde el primer segundo.",
                "cta": "¡Síguenos y comenta 'INFO' para una sorpresa exclusiva!",
                "scene_prompts": [
                    f"Surprised expressive person looking at smartphone with amazement, modern urban background, neon lighting, dynamic commercial photo, vertical 9:16 aspect ratio, 8k",
                    f"Vibrant aesthetic presentation of innovative {industry} product or service, modern aesthetic composition, studio lighting, vertical 9:16 aspect ratio, ultra realistic",
                    f"Happy energetic customer celebrating success with {company_name}, bright energetic atmosphere, vertical 9:16, high quality commercial cinematography"
                ],
                "scene_subtitles": [
                    f"¿Aún no conoces {company_name}?",
                    f"La evolución en {industry} llegó",
                    "¡Comenta INFO y pruébalo hoy!"
                ]
            },
            {
                "option_type": "B",
                "title": f"{company_name}: Excelencia en {industry}",
                "approach": "Enfoque profesional / valor diferencial y beneficios",
                "hook": f"La calidad no se improvisa: conoce el estándar de {company_name}.",
                "narration": f"Diseñado para quienes buscan excelencia. Cada detalle en {company_name} está pensado para optimizar tu experiencia en {industry}.",
                "cta": "Descubre la diferencia visitando nuestro perfil o enlace en bio.",
                "scene_prompts": [
                    f"Elegant professional workspace showcasing premium {industry} solutions, minimalist luxury interior, soft ambient daylight, vertical 9:16 aspect ratio, cinematic depth of field",
                    f"Close up detailed macro shot of craftsmanship and premium quality related to {industry}, modern aesthetic, 8k, vertical 9:16",
                    f"Satisfied confident professional smiling in modern office, sleek corporate backdrop, vertical 9:16 aspect ratio, hyperrealistic"
                ],
                "scene_subtitles": [
                    f"Calidad que marca la diferencia",
                    f"Diseñado para expertos en {industry}",
                    "Conoce más en nuestro enlace"
                ]
            },
            {
                "option_type": "C",
                "title": f"¡Oferta Flash en {company_name}!",
                "approach": "Enfoque promocional / llamada a la acción con urgencia",
                "hook": f"¡Solo por hoy! La oportunidad que esperabas en {industry}.",
                "narration": f"Aprovecha esta promoción de tiempo limitado en {company_name}. Cupos exclusivos para las primeras 20 personas que den clic.",
                "cta": "¡Toca el botón ahora antes de que se agoten los cupos!",
                "scene_prompts": [
                    f"Bold eye-catching commercial scene featuring modern promotional badge and vibrant display for {industry}, neon accent lighting, vertical 9:16, 8k",
                    f"Excited group of customers enjoying {company_name} special offer, bright vibrant colors, high-end commercial photo, vertical 9:16 aspect ratio",
                    f"Dramatic countdown and special gift box opening with glowing light, vertical 9:16 aspect ratio, cinematic lighting, ultra-detailed"
                ],
                "scene_subtitles": [
                    "¡OFERTA POR TIEMPO LIMITADO!",
                    f"Accede al beneficio de {company_name}",
                    "¡Haz clic en el enlace AHORA!"
                ]
            }
        ]

