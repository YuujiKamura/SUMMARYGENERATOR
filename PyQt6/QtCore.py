class QObject:
    pass

def pyqtSignal(*args, **kwargs):
    def decorator(func=None):
        return func
    return decorator
