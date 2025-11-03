# # routes/routers/health.py


# @router.get("/health/detailed", response_model=TranslationStatusResponse)
# async def detailed_health_check():
#     """
#     Detailed health check that tests all services
#     """
#     service_status = {}
#     overall_healthy = True
    
#     try:
#         # Test OCR services
#         ocr_status = await _check_ocr_services()
#         service_status["ocr"] = ocr_status
#         if not ocr_status["healthy"]:
#             overall_healthy = False
        
#         # Test translation services
#         translation_status = await _check_translation_services()
#         service_status["translation"] = translation_status
#         if not translation_status["healthy"]:
#             overall_healthy = False
        
#         # Test system resources
#         system_status = _check_system_resources()
#         service_status["system"] = system_status
#         if not system_status["healthy"]:
#             overall_healthy = False
        
#         return TranslationStatusResponse(
#             status="healthy" if overall_healthy else "unhealthy",
#             timestamp=datetime.utcnow(),
#             services=service_status,
#             message="Detailed health check completed"
#         )
        
#     except Exception as e:
#         logger.error(f"Health check failed: {str(e)}")
#         return TranslationStatusResponse(
#             status="unhealthy",
#             timestamp=datetime.utcnow(),
#             services={"error": {"healthy": False, "message": str(e)}},
#             message="Health check failed"
#         )


# async def _check_ocr_services() -> Dict[str, Any]:
#     """Check OCR services health"""
#     try:
#         ocr_manager = OCRManager()
        
#         # Test different OCR services
#         services_to_test = ["japanese", "chinese", "korean", "english"]
#         service_results = {}
        
#         for lang in services_to_test:
#             try:
#                 ocr_service = ocr_manager.get_ocr_service(lang)
#                 # We can't easily test without an actual image, so just check if service loads
#                 service_results[lang] = {"available": True, "error": None}
#             except Exception as e:
#                 service_results[lang] = {"available": False, "error": str(e)}
        
#         healthy = all(result["available"] for result in service_results.values())
        
#         return {
#             "healthy": healthy,
#             "services": service_results,
#             "message": "OCR services check completed"
#         }
        
#     except Exception as e:
#         return {
#             "healthy": False,
#             "error": str(e),
#             "message": "OCR services check failed"
#         }


# async def _check_translation_services() -> Dict[str, Any]:
#     """Check translation services health"""
#     try:
#         translation_manager = TranslationManager()
        
#         # Test with a simple translation
#         test_text = "Hello"
#         try:
#             result = await translation_manager.translate_text(
#                 text=test_text,
#                 source_lang="english",
#                 target_lang="japanese"
#             )
            
#             translation_healthy = result and result != test_text
            
#             return {
#                 "healthy": translation_healthy,
#                 "test_translation": result,
#                 "message": "Translation services are working"
#             }
            
#         except Exception as e:
#             return {
#                 "healthy": False,
#                 "error": str(e),
#                 "message": "Translation test failed"
#             }
        
#     except Exception as e:
#         return {
#             "healthy": False,
#             "error": str(e),
#             "message": "Translation services check failed"
#         }


# @router.get("/health/readiness")
# async def readiness_check():
#     """
#     Kubernetes readiness probe endpoint
#     """
#     try:
#         # Quick check that essential services can be initialized
#         ocr_manager = OCRManager()
#         translation_manager = TranslationManager()
        
#         return {"status": "ready", "timestamp": datetime.utcnow()}
        
#     except Exception as e:
#         logger.error(f"Readiness check failed: {str(e)}")
#         raise HTTPException(
#             status_code=503,
#             detail={"status": "not ready", "error": str(e)}
#         )


# @router.get("/health/liveness")
# async def liveness_check():
#     """
#     Kubernetes liveness probe endpoint
#     """
#     # Simple check that the application is alive
#     return {"status": "alive", "timestamp": datetime.utcnow()}


# @router.get("/version")
# async def get_version():
#     """
#     Get API version information
#     """
#     return {
#         "api_version": "1.0.0",
#         "build_date": "2024-01-01",  # You can set this dynamically
#         "python_version": "3.11+",
#         "supported_formats": ["PNG", "JPEG", "JPG", "WEBP"],
#         "max_file_size_mb": 10,
#         "max_batch_size": 10
#     }


##### NEW #####
import logging
import platform
import time
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from config import settings
from services.ocr.ocr_manager import OCRManager
from services.translate.translation_manager import TranslationManager
from models.responses import HealthResponse, ErrorResponse

logger = logging.getLogger(__name__)
router = APIRouter()

# Track uptime
START_TIME = time.time()

def _check_system_resources():
    """Check system resources utilization."""
    try:
        import psutil

        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        cpu = psutil.cpu_percent(interval=1)

        healthy = True
        messages = []

        if memory.percent > settings.health.max_memory_percent:
            healthy = False
            messages.append(f"Memory usage too high: {memory.percent}%.")
        if disk.percent > settings.health.max_disk_percent:
            healthy = False
            messages.append(f"Disk usage too high: {disk.percent}%.")
        if cpu > settings.health.max_cpu_percent:
            healthy = False
            messages.append(f"CPU usage too high: {cpu}%.")
        if (memory.available / (1024 ** 3)) < settings.health.min_memory_gb:
            healthy = False
            messages.append("Insufficient available memory.")
        if (disk.free / (1024 ** 3)) < settings.health.min_disk_gb:
            healthy = False
            messages.append("Insufficient disk space.")

        return healthy, " ".join(messages) if messages else "OK."
    
    except ImportError:
        return False, "System resource check unavailable (psutil not installed)."


async def _check_ocr_services():
    """Check OCR service health."""
    try:
        ocr_manager = OCRManager()
        available = ocr_manager.is_available()
        if not available:
            return False, "OCR manager not available"
        
        services = ocr_manager.get_service_status()
        if not services:
            return False, "No OCR services available"
        
        return True, services
    except Exception as e:
        return False, str(e)

async def _check_translation_services():
    """Check translation service health."""
    try:
        translation_manager = TranslationManager()
        services = translation_manager.get_available_services()
        if not services:
            return False, "No translation services available"
        return True, services
    except Exception as e:
        return False, str(e)


@router.get("/health", response_model=HealthResponse, responses={500: {"model": ErrorResponse}})
async def health_check():
    """
    Full API health check.
    Returns API version, OCR/translation availability, uptime, and system status.
    """
    try:
        uptime = time.time() - START_TIME

        system_ok, sys_msg = _check_system_resources()
        ocr_ok, ocr_info = await _check_ocr_services()
        trans_ok, trans_info = await _check_translation_services()

        if not (system_ok and ocr_ok and trans_ok):
            raise HTTPException(
                status_code=500,
                detail=f"Unhealthy: {sys_msg}, OCR: {ocr_info}, Translation: {trans_info}"
            )

        return HealthResponse(
            status="healthy",
            version=settings.app_version,
            ocr_models_loaded=ocr_info if isinstance(ocr_info, int) else 0,
            translation_services_available=trans_info if isinstance(trans_info, list) else [],
            uptime_seconds=uptime,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Health check failure", exc_info=True)
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error="health_check_failed",
                details=str(e),
                timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            ).model_dump(),
        )