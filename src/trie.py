"""implementa radix trie/trie compacta"""

from dataclasses import dataclass, field
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(slots=True)
class _Node(Generic[T]):
    children: dict[str, tuple[str, "_Node[T]"]] = field(default_factory=dict)
    values: list[T] = field(default_factory=list)


class RadixTrie(Generic[T]):
    """guarda as chaves como arestas comprimidas e aceita busca em o(m+k)"""

    def __init__(self) -> None:
        self._root: _Node[T] = _Node()
        self._size = 0

    def __len__(self) -> int:
        return self._size

    def clear(self) -> None:
        self._root = _Node()
        self._size = 0

    def insert(self, key: str, value: T) -> None:
        if not key:
            raise ValueError("chave não pode ser vazia")

        node = self._root
        remaining = key
        while remaining:
            edge = node.children.get(remaining[0])
            if edge is None:
                terminal = _Node[T](values=[value])
                node.children[remaining[0]] = (remaining, terminal)
                self._size += 1
                return

            label, child = edge
            common = self._common_prefix_length(remaining, label)
            if common == len(label):
                remaining = remaining[common:]
                node = child
                continue

            middle = _Node[T]()
            old_suffix = label[common:]
            middle.children[old_suffix[0]] = (old_suffix, child)
            node.children[label[0]] = (label[:common], middle)
            remaining = remaining[common:]
            if remaining:
                terminal = _Node[T](values=[value])
                middle.children[remaining[0]] = (remaining, terminal)
            else:
                middle.values.append(value)
            self._size += 1
            return

        node.values.append(value)
        self._size += 1

    def search_prefix(self, prefix: str) -> list[T]:
        if not prefix:
            return self._collect(self._root)

        node = self._root
        remaining = prefix
        while remaining:
            edge = node.children.get(remaining[0])
            if edge is None:
                return []
            label, child = edge
            common = self._common_prefix_length(remaining, label)
            if common == len(remaining):
                return self._collect(child)
            if common != len(label):
                return []
            remaining = remaining[common:]
            node = child
        return self._collect(node)

    @staticmethod
    def _common_prefix_length(first: str, second: str) -> int:
        limit = min(len(first), len(second))
        index = 0
        while index < limit and first[index] == second[index]:
            index += 1
        return index

    @classmethod
    def _collect(cls, node: _Node[T]) -> list[T]:
        values = list(node.values)
        for _, child in node.children.values():
            values.extend(cls._collect(child))
        return values
