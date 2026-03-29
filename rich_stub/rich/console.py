class Console:
    """Drop-in stub for rich.Console that prints to stdout."""
    def log(self, *args, **kwargs):
        print(*args)
    def print(self, *args, **kwargs):
        print(*args)
