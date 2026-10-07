"""
Environments, for identifier resolution during WDL typechecking and evaluation.
"""

from typing import Optional, TypeVar, Generic, Any, Callable, Set, Iterator

T = TypeVar("T")
S = TypeVar("S")


class Binding(Generic[T]):
    """
    An individual, immutable binding of a possibly-namespaced name to a right-hand-side value of
    type ``T``. ``T`` is typically ``Value.Base`` (value environments) or ``Type.Base`` (type
    environments). The binding may also reference an additional informational value of arbitrary
    type.
    """

    _name: str
    _value: T
    _info: Any

    def __init__(self, name: str, value: T, info: Any = None) -> None:
        self._name = name
        self._value = value
        self._info = info

    @property
    def name(self) -> str:
        """:type: str

        Namedspaced names are flat, dot-separated strings.
        """
        return self._name

    @property
    def value(self) -> T:
        ":type: T"
        return self._value

    @property
    def info(self) -> Any:
        ":type: Any"
        return self._info


class Bindings(Generic[T]):
    """WDL.Env.Bindings(binding: Optional[WDL.Env.Binding[T]] = None, next: Optional[WDL.Env.Bindings[T]] = None)

    An environment consisting of an immutable linked-list of :class:`WDL.Env.Binding` objects.
    ``WDL.Env.Bindings()`` is the empty environment. ``Bindings[T]`` is iterable for the individual
    ``Binding[T]`` objects::

        env = WDL.Env.Bindings()
        env = env.bind("x", 1).bind("y", 42)
        print(env["x"])                             # 1
        print(",".join(str(b.value) for b in env))  # 1,42

    """

    _binding: Optional[Binding[T]]
    _next: "Optional[Bindings[T]]"
    _namespaces: Optional[Set[str]] = None

    def __init__(
        self,
        binding: Optional[Binding[T]] = None,
        next: "Optional[Bindings[T]]" = None,
    ) -> None:
        assert binding or not next
        self._binding = binding
        self._next = next

    def __bool__(self) -> bool:
        return next(self.__iter__(), None) is not None

    def __iter__(self) -> Iterator[Binding[T]]:
        mask = set()
        pos: Optional[Bindings[T]] = self
        while pos is not None:
            if isinstance(pos._binding, Binding) and pos._binding.name not in mask:
                mask.add(pos._binding.name)
                yield pos._binding
            pos = pos._next

    def __len__(self) -> int:
        return sum(1 for _ in self)

    def bind(self, name: str, value: T, info: Any = None) -> "Bindings[T]":
        """
        Return an environment with a new binding prepended. Any existing binding for the same name
        is shadowed by the new one. (This should not usually arise in view of the immutability of
        WDL values.)
        """
        assert name and not (name.startswith(".") or name.endswith("."))
        return Bindings(Binding(name, value, info), self)

    def resolve_binding(self, name: str) -> Binding[T]:
        """Look up a :class:`WDL.Env.Binding` object by name

        :raise KeyError: no such binding
        """
        for b in self:
            if b.name == name:
                return b
        raise KeyError()

    def resolve(self, name: str) -> T:
        """
        Look up a bound value by name. Equivalently, ``env[name]``

        :raise KeyError: no such binding
        """
        return self.resolve_binding(name).value

    def get(self, name: str, default: Optional[T] = None) -> Optional[T]:
        """
        Look up a bound value by name, returning the default value or ``None`` if there's no such
        binding.
        """
        try:
            return self.resolve(name)
        except KeyError:
            return default

    def __getitem__(self, name: str) -> T:
        return self.resolve(name)

    def has_binding(self, name: str) -> bool:
        """
        Determine existence of a binding for the name. Equivalently, ``name in env``
        """
        try:
            self.resolve(name)
            return True
        except KeyError:
            return False

    def __contains__(self, name: str) -> bool:
        if isinstance(name, str):
            return self.has_binding(name)
        return False

    def map(self, f: Callable[[Binding[T]], Optional[Binding[S]]]) -> "Bindings[S]":
        """
        Copy the environment with each binding transformed by the given function. If the function
        returns ``None`` then the binding is excluded.
        """
        ans: Bindings[S] = Bindings()
        for b in self:
            fb = f(b)
            if isinstance(fb, Binding):
                ans = Bindings(fb, ans)
        return _rev(ans)

    def filter(self, pred: Callable[[Binding[T]], bool]) -> "Bindings[T]":
        "Copy the environment with only those bindings for which ``pred`` returns True"
        return self.map(lambda b: b if pred(b) else None)

    def subtract(self, rhs: "Bindings[S]") -> "Bindings[T]":
        "Copy the environment excluding any binding for which ``rhs`` has a binding with the same name"

        def flt(b: Binding[T]) -> bool:
            try:
                rhs.resolve(b.name)
                return False
            except KeyError:
                return True

        return self.filter(flt)

    @property
    def namespaces(self) -> Set[str]:
        """:type: Set[str]

        Return the environment's namespaces, all the distinct dot-separated prefixes of the binding
        names. Each element ends with a dot.
        """
        if self._namespaces is None:
            self._namespaces = self._next.namespaces if self._next is not None else set()
            if isinstance(self._binding, Binding):
                names = self._binding.name.split(".")
                if len(names) > 1:
                    for i in range(len(names) - 1):
                        ns = ".".join(names[: i + 1]) + "."
                        self._namespaces.add(ns)
        return self._namespaces.copy()

    def has_namespace(self, namespace: str) -> bool:
        "Determine existence of a namespace in the environment"
        assert namespace
        if not namespace.endswith("."):
            namespace += "."
        return namespace in (self._namespaces if self._namespaces else self.namespaces)

    def enter_namespace(self, namespace: str) -> "Bindings[T]":
        """
        Generate an environment with only those bindings in the given namespace, with the namespace
        prefix removed from each binding's name.
        """
        assert namespace
        if not namespace.endswith("."):
            namespace += "."

        def enter(b: Binding[T]) -> Optional[Binding[T]]:
            if b.name.startswith(namespace):
                return Binding(b.name[len(namespace) :], b.value, b.info)
            return None

        return self.map(enter)

    def wrap_namespace(self, namespace: str) -> "Bindings[T]":
        "Copy the environment with the given namespace prefixed to each binding name"
        assert namespace
        if not namespace.endswith("."):
            namespace += "."
        ans: Bindings[T] = Bindings()
        for b in self:
            ans = Bindings(Binding(namespace + b.name, b.value, b.info), ans)
        return _rev(ans)


def _rev(env: Bindings[T]) -> Bindings[T]:
    ans: Bindings[T] = Bindings()
    for b in env:
        ans = Bindings(b, ans)
    return ans


def merge(*args: Bindings[T]) -> Bindings[T]:
    """
    Merge several ``Bindings[T]`` environments into one. Should the same name appear in multiple
    arguments, the first (leftmost) occurrence takes precedence. Otherwise, for efficiency, the
    largest environment should be supplied last.
    """
    ans = args[-1] if args else Bindings()
    for env in reversed(args[:-1]):
        assert isinstance(env, Bindings)
        for b in _rev(env):
            ans = Bindings(b, ans)
    return ans
