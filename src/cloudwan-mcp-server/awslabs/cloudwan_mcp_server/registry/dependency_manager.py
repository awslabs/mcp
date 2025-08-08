from typing import Dict, List, Set


class DependencyManager:
    def __init__(self, tool_registry: Any):
        self._registry = tool_registry
        self._dependency_graph: Dict[str, Set[str]] = {}

    def add_dependency(self, tool_name: str, depends_on: str):
        if tool_name not in self._dependency_graph:
            self._dependency_graph[tool_name] = set()
        self._dependency_graph[tool_name].add(depends_on)

    def get_initialization_order(self) -> List[str]:
        visited = set()
        result = []

        def visit(node):
            if node in visited:
                return
            visited.add(node)
            for dep in self._dependency_graph.get(node, []):
                visit(dep)
            result.append(node)

        for tool in self._registry._metadata.keys():
            visit(tool)

        return result[::-1]  # Reverse for proper order
