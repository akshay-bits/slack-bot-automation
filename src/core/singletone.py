class Singleton:
    """Singleton class for the application"""
    _instance = None
    _initialized = False
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(Singleton, cls).__new__(cls)
        return cls._instance
    
    def __init__(self, *args, **kwargs):
        # Only initialize once - subclasses should override __init__ and check _initialized
        if not self._initialized:
            self._initialized = True