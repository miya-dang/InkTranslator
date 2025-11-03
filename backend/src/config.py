from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List

class HealthSettings(BaseSettings):
    # System thresholds
    max_memory_percent: int = 90
    max_disk_percent: int = 90
    max_cpu_percent: int = 90
    min_memory_gb: int = 1
    min_disk_gb: int = 1

    # Translation test values
    test_text: str = "Hello world"
    test_source_lang: str = "en"
    test_target_lang: str = "ja"


class Settings(BaseSettings):
    # Application settings
    app_name: str = Field(default="Ink Translator API", env="APP_NAME")
    app_version: str = Field(default="0.0.0", env="APP_VERSION")
    app_description: str = Field(
        default="API for MTL of text in manga/manhwa/manhua images", env="APP_DESCRIPTION"
    )
    debug: bool = Field(default=False, env="DEBUG")
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")

    # CORS settings
    enable_cors: bool = Field(default=True, env="ENABLE_CORS")
    allowed_origins: List[str] = Field(default=[], env="ALLOWED_ORIGINS")

    # Rate limiting
    enable_rate_limiting: bool = Field(default=True, env="ENABLE_RATE_LIMITING")
    translation_rate_limit_requests: int = Field(default=10, env="TRANSLATION_RATE_LIMIT_REQUESTS")
    translation_rate_limit_window: int = Field(default=5, env="TRANSLATION_RATE_LIMIT_WINDOW")
    preview_rate_limit_requests: int = Field(default=20, env="PREVIEW_RATE_LIMIT_REQUESTS")
    preview_rate_limit_window: int = Field(default=5, env="PREVIEW_RATE_LIMIT_WINDOW")
    batch_rate_limit_requests: int = Field(default=2, env="BATCH_RATE_LIMIT_REQUESTS")
    batch_rate_limit_window: int = Field(default=10, env="BATCH_RATE_LIMIT_WINDOW")

    # File upload settings
    max_file_size_mb: int = Field(default=10, env="MAX_FILE_SIZE_MB")
    allowed_mime_types: List[str] = ["image/jpeg", "image/jpg", "image/png"]
    allowed_extensions: List[str] = [".jpeg", ".jpg", ".png"]

    # OCR settings
    ocr_confidence_threshold: float = 0.3
    manga_ocr_enabled: bool = Field(default=True, env="MANGA_OCR_ENABLED")
    easyocr_gpu: bool = Field(default=False, env="EASYOCR_GPU")
    merge_nearby_textboxes: bool = True

    # Translation service settings
    google_translate_enabled: bool = Field(default=True, env="GOOGLE_TRANSLATE_ENABLED")
    deepl_enabled: bool = Field(default=False, env="DEEPL_ENABLED")

    # Translation API Keys
    google_translate_api_key: str = Field(default="", env="GOOGLE_TRANSLATE_API_KEY")
    deepl_api_key: str = Field(default="", env="DEEPL_API_KEY")
    deepl_api_url: str = Field(default="", env="DEEPL_API_URL")

    # Translation settings
    translation_timeout: int = Field(default=30, env="TRANSLATION_TIMEOUT")
    translation_max_retries: int = Field(default=2, env="TRANSLATION_MAX_RETRIES")
    translation_retry_delay: float = Field(default=1.0, env="TRANSLATION_RETRY_DELAY")

    # Inpainting settings (constants)
    inpaint_radius: int = 3
    inpaint_method: str = "telea"
    mask_padding: int = 3

    # Text rendering settings (constants)
    font_size_min: int = 6
    font_size_max: int = 30
    font_size_multiplier: float = 1.0
    font_size_multiplier_min: float = 0.5
    font_size_multiplier_max: float = 2.0
    text_outline_width: int = 1
    text_outline_color: str = "white"
    text_color: str = "black"

    # Font paths (constants)
    fonts_dir: str = "fonts/"
    english_font: str = "fonts/CCMonologousTeddyBear.ttf"
    japanese_font: str = "fonts/GenEiAntique.ttf"
    sim_chinese_font: str = "fonts/SCNotoSerifCJK.otf"
    korean_font: str = "fonts/KRNotoSerifCJK.otf"
    trad_chinese_font: str = "fonts/TCNotoSerifCJK.otf"
    vietnamese_font: str = "fonts/CCMonologousTeddyBear.ttf"
    default_font: str = "fonts/CCMonologousTeddyBear.ttf"

    @property
    def font_mappings(self) -> dict:
        return {
            "english": self.english_font,
            "japanese": self.japanese_font,
            "sim_chinese": self.sim_chinese_font,  # simplified
            "korean": self.korean_font,
            "trad_chinese": self.trad_chinese_font,
            "vietnamese": self.vietnamese_font,
            "default": self.default_font,
        }

    @property
    def text_directions(self) -> dict:
        return {
            "english": "ltr",
            "japanese": "ttb",
            "sim_chinese": "ttb",
            "trad_chinese": "ttb",
            "korean": "ltr",
            "vietnamese": "ltr",
            "default": "ltr",
        }

    # Logging settings
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_to_file: bool = Field(default=True, env="LOG_TO_FILE")
    log_file_path: str = Field(default="ink_translator.log", env="LOG_FILE_PATH")
    log_max_size_mb: int = Field(default=100, env="LOG_MAX_SIZE_MB")
    log_backup_count: int = Field(default=5, env="LOG_BACKUP_COUNT")

    # Performance settings
    max_workers: int = Field(default=4, env="MAX_WORKERS")
    async_timeout: int = Field(default=300, env="ASYNC_TIMEOUT")

    # Health check settings
    health: HealthSettings = HealthSettings()

    # API documentation
    enable_docs: bool = Field(default=True, env="ENABLE_DOCS")

    # Development
    reload: bool = Field(default=False, env="RELOAD")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

# Constants
TRANSLATION_SERVICE_PRIORITY = ["google", "deepl"]
OCR_SERVICES = ["easyocr", "mangaocr"]

