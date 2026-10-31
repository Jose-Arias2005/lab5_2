import os
import io
import time
import base64
import urllib.parse
import logging
import subprocess
import requests
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from PIL import Image, ImageDraw, ImageFont

from app.config import settings

logger = logging.getLogger("marketing_app.media_service")

class MediaService:
    VIDEO_WIDTH = 720
    VIDEO_HEIGHT = 1280
    FPS = 24
    SCENE_DURATION = 3.5  # segundos por imagen (total ~10.5 seg)
    IMAGEN_MODEL = "imagen-3.0-generate-002"

    @classmethod
    def generate_campaign_media(cls, campaign_id: int, script_data: Dict[str, Any], company_name: str) -> Tuple[List[str], str]:
        """
        Orquesta la generación multimedia completa:
        1. Genera 3 imágenes basadas en la descripción de cada escena con Google Imagen 3 (imagen-3.0-generate-002).
        2. Descarga los bytes generados y los guarda en /app/media/generated_images/.
        3. Superpone subtítulos/frases clave en cada imagen.
        4. Compila el video vertical MP4 (720x1280, 24fps) con MoviePy / FFmpeg.
        
        Retorna (lista_rutas_imagenes, ruta_video_final).
        """
        scene_prompts: List[str] = script_data.get("scene_prompts", [])
        scene_subtitles: List[str] = script_data.get("scene_subtitles", [])
        
        # Garantizar que existan al menos 3 descripciones
        while len(scene_prompts) < 3:
            scene_prompts.append(f"Commercial vertical 9:16 advertisement photography for {company_name}")
        while len(scene_subtitles) < 3:
            scene_subtitles.append(f"Descubre {company_name}")

        image_paths: List[str] = []
        annotated_image_paths: List[str] = []

        # 1. Generar y guardar las 3 imágenes con Imagen 3 / Google AI
        for idx in range(3):
            prompt = scene_prompts[idx]
            subtitle = scene_subtitles[idx]
            scene_num = idx + 1
            
            raw_img_path = str(settings.GENERATED_IMAGES_DIR / f"campaign_{campaign_id}_scene_{scene_num}_raw.jpg")
            annotated_img_path = str(settings.GENERATED_IMAGES_DIR / f"campaign_{campaign_id}_scene_{scene_num}.jpg")

            logger.info("Generando imagen %s/3 para campaña %s con Google Imagen 3 / IA...", scene_num, campaign_id)
            cls._generate_image(prompt, raw_img_path, scene_index=scene_num, company_name=company_name)
            
            # 2. Superponer subtítulos del guion seleccionado
            cls._overlay_text_on_image(raw_img_path, annotated_img_path, subtitle, company_name, scene_index=scene_num)
            
            image_paths.append(annotated_img_path)
            annotated_image_paths.append(annotated_img_path)

        # 3. Compilar video vertical MP4 (9:16, 720x1280, 24fps) con MoviePy / FFmpeg
        video_filename = f"campaign_{campaign_id}.mp4"
        final_video_path = str(settings.VIDEOS_DIR / video_filename)

        logger.info("Compilando video vertical 9:16 en: %s", final_video_path)
        cls._create_video_mp4(annotated_image_paths, final_video_path)

        return image_paths, final_video_path

    @classmethod
    def _generate_image(cls, prompt: str, output_path: str, scene_index: int, company_name: str) -> None:
        """
        Genera y descarga la imagen utilizando la API de Google con la clave GEMINI_API_KEY.
        Pipeline de generación:
        1. Google Imagen 3 (imagen-3.0-generate-002) vía SDK google-genai / REST.
        2. Google Multimodal Image Model (gemini-2.5-flash-image) en la Developer API.
        3. Fallback a Pollinations.ai / PIL para garantizar continuidad sin interrupciones.
        """
        api_key = settings.GEMINI_API_KEY.strip()

        if api_key and api_key != "tu_api_key_de_gemini":
            # Intento A: Google Imagen 3 (imagen-3.0-generate-002) con google-genai
            if cls._try_imagen_3_sdk(prompt, output_path, api_key):
                return

            # Intento B: Google Imagen 3 REST predict
            if cls._try_imagen_3_rest(prompt, output_path, api_key):
                return

            # Intento C: Google Gemini Flash Image (gemini-2.5-flash-image)
            if cls._try_gemini_flash_image(prompt, output_path, api_key):
                return

        # Fallback si no hay API key o si se superaron cuotas
        logger.warning("Recurriendo a generador de respaldo para la imagen de la escena %s.", scene_index)
        cls._download_pollinations_image(prompt, output_path, scene_index, company_name)

    @classmethod
    def _try_imagen_3_sdk(cls, prompt: str, output_path: str, api_key: str) -> bool:
        """Intenta generar la imagen usando el método oficial SDK de Imagen 3 (imagen-3.0-generate-002)."""
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=api_key)
            logger.info("Invocando client.models.generate_images con modelo '%s'...", cls.IMAGEN_MODEL)
            
            response = client.models.generate_images(
                model=cls.IMAGEN_MODEL,
                prompt=f"{prompt}, vertical 9:16 commercial advertisement photography, highly detailed, 8k",
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                    aspect_ratio="9:16",
                    output_mime_type="image/jpeg",
                )
            )

            if response and response.generated_images and len(response.generated_images) > 0:
                img_obj = response.generated_images[0].image
                img_bytes = img_obj.image_bytes
                if img_bytes and len(img_bytes) > 500:
                    with open(output_path, "wb") as f:
                        f.write(img_bytes)
                    logger.info("Imagen 3 generada y guardada con éxito desde SDK en: %s", output_path)
                    return True

        except Exception as e:
            logger.info("SDK Imagen 3 (imagen-3.0-generate-002) no disponible en este nivel de API (%s). Pasando a endpoint Gemini.", e)

        return False

    @classmethod
    def _try_imagen_3_rest(cls, prompt: str, output_path: str, api_key: str) -> bool:
        """Intenta generar la imagen invocando directamente el endpoint REST de Imagen 3."""
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{cls.IMAGEN_MODEL}:predict"
            headers = {
                "x-goog-api-key": api_key,
                "Content-Type": "application/json"
            }
            payload = {
                "instances": [
                    {"prompt": f"{prompt}, commercial 9:16 vertical photography"}
                ],
                "parameters": {
                    "sampleCount": 1,
                    "aspectRatio": "9:16",
                    "outputMimeType": "image/jpeg"
                }
            }
            resp = requests.post(url, headers=headers, json=payload, timeout=25)
            if resp.status_code == 200:
                data = resp.json()
                predictions = data.get("predictions", [])
                if predictions and "bytesBase64Encoded" in predictions[0]:
                    img_bytes = base64.b64decode(predictions[0]["bytesBase64Encoded"])
                    with open(output_path, "wb") as f:
                        f.write(img_bytes)
                    logger.info("Imagen 3 generada y guardada exitosamente vía REST en: %s", output_path)
                    return True
        except Exception as e:
            logger.debug("REST Imagen 3 endpoint info: %s", e)

        return False

    @classmethod
    def _try_gemini_flash_image(cls, prompt: str, output_path: str, api_key: str) -> bool:
        """Genera imagen con la API oficial de Google Gemini Image (gemini-2.5-flash-image)."""
        try:
            from google import genai

            client = genai.Client(api_key=api_key)
            model_name = "gemini-2.5-flash-image"
            logger.info("Generando imagen con Google Gemini API modelo '%s'...", model_name)

            prompt_full = (
                f"Generate a vertical 9:16 high-resolution commercial advertisement photo: {prompt}. "
                "Realistic, professional studio lighting, 8k, modern aesthetic."
            )
            response = client.models.generate_content(
                model=model_name,
                contents=prompt_full
            )

            if response and response.candidates and len(response.candidates) > 0:
                candidate = response.candidates[0]
                for part in candidate.content.parts:
                    if hasattr(part, "inline_data") and part.inline_data and part.inline_data.data:
                        img_bytes = part.inline_data.data
                        with open(output_path, "wb") as f:
                            f.write(img_bytes)
                        logger.info("Imagen generada exitosamente con Google AI y guardada en: %s (%s bytes)", output_path, len(img_bytes))
                        return True

        except Exception as e:
            logger.warning("Fallo al generar imagen con Google Gemini Image API: %s", e)

        return False

    @classmethod
    def _download_pollinations_image(cls, prompt: str, output_path: str, scene_index: int, company_name: str) -> None:
        """Descarga de imagen de respaldo desde Pollinations.ai o generador local con PIL."""
        clean_prompt = prompt.strip()
        enhanced_prompt = f"{clean_prompt}, vertical 9:16 aspect ratio, ultra-detailed commercial photography, high resolution, modern studio lighting"
        encoded_prompt = urllib.parse.quote_plus(enhanced_prompt[:400])
        seed = int(time.time() * 1000) % 1000000 + scene_index * 1337

        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={cls.VIDEO_WIDTH}&height={cls.VIDEO_HEIGHT}&nologo=true&seed={seed}&model=flux"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

        try:
            logger.info("Descargando imagen de respaldo de Pollinations.ai...")
            response = requests.get(url, headers=headers, timeout=25)
            if response.status_code == 200 and len(response.content) > 1000:
                with open(output_path, "wb") as f:
                    f.write(response.content)
                logger.info("Imagen de respaldo guardada en %s", output_path)
                return
        except Exception as e:
            logger.warning("Fallo al conectar con Pollinations.ai: %s", e)

        # Respaldo estético con PIL
        cls._create_fallback_image(output_path, scene_index, company_name)

    @classmethod
    def _create_fallback_image(cls, output_path: str, scene_index: int, company_name: str) -> None:
        """Crea una imagen estilizada 9:16 con degradado moderno con Pillow."""
        width, height = cls.VIDEO_WIDTH, cls.VIDEO_HEIGHT
        img = Image.new("RGB", (width, height), color=(15, 23, 42))
        draw = ImageDraw.Draw(img)

        palettes = [
            ((79, 70, 229), (147, 51, 234)),
            ((14, 165, 233), (59, 130, 246)),
            ((244, 63, 94), (249, 115, 22)),
        ]
        color_start, color_end = palettes[(scene_index - 1) % len(palettes)]

        for y in range(height):
            ratio = y / height
            r = int(color_start[0] * (1 - ratio) + color_end[0] * ratio)
            g = int(color_start[1] * (1 - ratio) + color_end[1] * ratio)
            b = int(color_start[2] * (1 - ratio) + color_end[2] * ratio)
            draw.line([(0, y), (width, y)], fill=(r, g, b))

        draw.ellipse([50, 150, 670, 770], outline=(255, 255, 255, 40), width=4)

        try:
            font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
        except Exception:
            font_title = ImageFont.load_default()

        draw.text((width // 2, 400), company_name.upper(), fill=(255, 255, 255), anchor="mm", font=font_title)
        draw.text((width // 2, 460), f"ESCENA {scene_index}", fill=(224, 231, 255), anchor="mm", font=font_title)

        img.save(output_path, "JPEG", quality=95)

    @classmethod
    def _overlay_text_on_image(cls, input_path: str, output_path: str, subtitle: str, company_name: str, scene_index: int) -> None:
        """
        Superpone un banner con subtítulo elegante en la imagen para el video vertical.
        Garantiza legibilidad y formato publicitario para TikTok.
        """
        try:
            img = Image.open(input_path).convert("RGBA")
        except Exception:
            cls._create_fallback_image(input_path, scene_index, company_name)
            img = Image.open(input_path).convert("RGBA")

        # Asegurar dimensiones exactas 720x1280 (vertical 9:16)
        if img.size != (cls.VIDEO_WIDTH, cls.VIDEO_HEIGHT):
            img = img.resize((cls.VIDEO_WIDTH, cls.VIDEO_HEIGHT), Image.Resampling.LANCZOS)

        overlay = Image.new("RGBA", img.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(overlay)

        font_large = None
        font_small = None
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/calibrib.ttf",
        ]
        for fp in font_paths:
            if os.path.exists(fp):
                try:
                    font_large = ImageFont.truetype(fp, 36)
                    font_small = ImageFont.truetype(fp, 22)
                    break
                except Exception:
                    pass

        if font_large is None:
            font_large = ImageFont.load_default()
            font_small = ImageFont.load_default()

        # 1. Badge superior de la Empresa
        badge_top = 80
        badge_text = f"● {company_name.upper()}"
        draw.rounded_rectangle([40, badge_top, 380, badge_top + 45], radius=15, fill=(0, 0, 0, 160))
        draw.text((55, badge_top + 10), badge_text, fill=(255, 255, 255, 240), font=font_small)

        # 2. Badge de escena / progreso TikTok
        draw.rounded_rectangle([cls.VIDEO_WIDTH - 140, badge_top, cls.VIDEO_WIDTH - 40, badge_top + 45], radius=15, fill=(0, 0, 0, 160))
        draw.text((cls.VIDEO_WIDTH - 115, badge_top + 10), f"{scene_index}/3", fill=(255, 255, 255, 240), font=font_small)

        # 3. Subtítulo / Frase clave en el tercio inferior
        words = subtitle.split()
        lines = []
        current_line = []
        for word in words:
            current_line.append(word)
            if len(" ".join(current_line)) > 24:
                lines.append(" ".join(current_line))
                current_line = []
        if current_line:
            lines.append(" ".join(current_line))
        if not lines:
            lines = [subtitle]

        box_height = 50 + len(lines) * 48
        box_y_start = cls.VIDEO_HEIGHT - box_height - 180
        box_padding_x = 35

        draw.rounded_rectangle(
            [box_padding_x, box_y_start, cls.VIDEO_WIDTH - box_padding_x, box_y_start + box_height],
            radius=20,
            fill=(0, 0, 0, 190),
            outline=(255, 255, 255, 80),
            width=2
        )

        y_text = box_y_start + 25
        for line in lines:
            draw.text(
                (cls.VIDEO_WIDTH // 2, y_text),
                line,
                fill=(254, 240, 138),  # Amarillo cálido
                anchor="mt",
                font=font_large
            )
            y_text += 46

        final_img = Image.alpha_composite(img, overlay).convert("RGB")
        final_img.save(output_path, "JPEG", quality=95)
        logger.info("Subtítulos superpuestos con éxito en %s", output_path)

    @classmethod
    def _create_video_mp4(cls, image_paths: List[str], output_video_path: str) -> None:
        """
        Compila el video vertical (9:16, 720x1280, 24fps) uniendo las 3 imágenes resultantes.
        Utiliza MoviePy como motor principal con fallback a FFmpeg CLI nativo.
        """
        try:
            from moviepy.editor import ImageClip, concatenate_videoclips

            clips = []
            for img_path in image_paths:
                clip = ImageClip(img_path).set_duration(cls.SCENE_DURATION)
                clips.append(clip)

            video = concatenate_videoclips(clips, method="compose")
            
            video.write_videofile(
                output_video_path,
                fps=cls.FPS,
                codec="libx264",
                audio=False,
                preset="medium",
                ffmpeg_params=["-pix_fmt", "yuv420p"]
            )
            logger.info("Video compilado exitosamente con MoviePy: %s", output_video_path)
            return

        except Exception as e:
            logger.warning("Fallo en MoviePy (%s). Ejecutando pipeline nativo FFmpeg...", e)

        cls._create_video_with_ffmpeg_cli(image_paths, output_video_path)

    @classmethod
    def _create_video_with_ffmpeg_cli(cls, image_paths: List[str], output_video_path: str) -> None:
        """Compilación directa con FFmpeg CLI nativo."""
        concat_file = Path(output_video_path).parent / f"concat_{int(time.time())}.txt"
        with open(concat_file, "w", encoding="utf-8") as f:
            for img in image_paths:
                clean_path = str(Path(img).resolve()).replace("\\", "/")
                f.write(f"file '{clean_path}'\n")
                f.write(f"duration {cls.SCENE_DURATION}\n")
            clean_last = str(Path(image_paths[-1]).resolve()).replace("\\", "/")
            f.write(f"file '{clean_last}'\n")

        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file).replace("\\", "/"),
            "-vf", f"scale={cls.VIDEO_WIDTH}:{cls.VIDEO_HEIGHT},fps={cls.FPS}",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            output_video_path
        ]

        logger.info("Ejecutando comando FFmpeg: %s", " ".join(cmd))
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if concat_file.exists():
            concat_file.unlink()

        if result.returncode != 0:
            logger.error("FFmpeg falló: %s", result.stderr)
            raise RuntimeError(f"Error al compilar video con FFmpeg: {result.stderr}")
        
        logger.info("Video compilado con éxito mediante FFmpeg CLI: %s", output_video_path)
