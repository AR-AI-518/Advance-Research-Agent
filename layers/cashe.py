import hashlib


class Cache:
    def __init__(self):
        self.data = {}

    def make_key(self, text):
        return hashlib.sha256(text.encode()).hexdigest()

    def set(self, text, value):
        key = self.make_key(text)
        self.data[key] = value

    def get(self, text):
        key = self.make_key(text)
        return self.data.get(key)


class Memory:
    def __init__(self):
        self.memory = []

    def set_memory(self, role, text):
        self.memory.append({
            "role": role,
            "data": text
        })

    def get_memory(self):
        return self.memory
