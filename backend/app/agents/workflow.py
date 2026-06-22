class Workflow:
    def __init__(self, nodes=None):
        self.nodes = nodes or []

    def run(self, data):
        for n in self.nodes:
            data = n.process(data)
        return data
