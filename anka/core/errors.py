class AnkaError(Exception):
    """Uygulamanin kullaniciya guvenli bir hata mesaji verebilecegi taban hata."""


class PermissionDeniedError(AnkaError):
    pass


class SecurityViolationError(AnkaError):
    pass


class FileProcessingError(AnkaError):
    pass


class ModelServiceError(AnkaError):
    pass


class WebResearchError(AnkaError):
    pass
