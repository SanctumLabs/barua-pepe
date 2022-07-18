def singleton(cls, *args, **kw):
    """
    Decorator used to check if an instance of a class already exists.
    """
    instances = {}

    def _singleton(*args, **kw):
        if cls not in instances:
            instances[cls] = cls(*args, **kw)
        return instances[cls]

    return _singleton
