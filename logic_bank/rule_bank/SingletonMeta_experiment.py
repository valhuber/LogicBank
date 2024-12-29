class SingletonMeta(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        # Check if an instance already exists
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]

    @classmethod
    def reset_instance(cls, singleton_class):
        """Reset the singleton for a specific class."""
        if singleton_class in cls._instances:
            del cls._instances[singleton_class]

# Singleton class
class Singleton(metaclass=SingletonMeta):
    def __init__(self, value):
        self.value = value

# Test the reset functionality
a = Singleton(10)
print(a.value)  # Output: 10

b = Singleton(20)
print(b.value)  # Output: 10 (same instance)

# Reset the singleton
SingletonMeta.reset_instance(Singleton)

c = Singleton(30)
print(c.value)  # Output: 30 (new instance)