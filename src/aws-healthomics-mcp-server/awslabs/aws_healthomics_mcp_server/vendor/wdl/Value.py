"""
WDL values instantiated at runtime

Each value is represented by an instance of a Python class inheriting from
``WDL.Value.Base``.

.. inheritance-diagram:: WDL.Value
   :top-classes: WDL.Value.Base
"""

import json
import copy
import base64
import hashlib
from abc import ABC
from typing import Any, List, Optional, Tuple, Dict, Iterable, Union, Callable, Set, TYPE_CHECKING
from contextlib import suppress
from . import Error, Type, Env

if TYPE_CHECKING:
    from . import Expr


class Base(ABC):
    """The abstract base class for WDL values"""

    type: Type.Base
    ":type: WDL.Type.Base"

    value: Any
    """The "raw" Python value"""

    _expr: "Optional[Expr.Base]"

    def __init__(self, type: Type.Base, value: Any, expr: "Optional[Expr.Base]" = None) -> None:
        assert isinstance(type, Type.Base)
        self.type = type
        if self.type.optional and not isinstance(self, Null):
            self.type = self.type.copy(optional=False)  # normalize runtime type
        self.value = value
        self._expr = None
        if expr:
            self.expr = expr

    def __eq__(self, other) -> bool:
        # nb: assumes static typechecking has ensured it's sensible to test these for equality
        assert isinstance(other, Base) and self.type.equatable(other.type), (
            f"cannot equate {self.type} {self} with {other.type} {other}"
        )
        return self.value == other.value

    def __str__(self) -> str:
        return json.dumps(self.json)

    @property
    def expr(self) -> "Optional[Expr.Base]":
        """
        Reference to the WDL expression that generated this value, if it originated
        from ``WDL.Expr.eval``
        """
        return self._expr

    @expr.setter
    def expr(self, rhs: "Expr.Base"):
        old_expr = self._expr  # possibly None
        if rhs is not old_expr:
            self._expr = rhs
            # recursively replace old_expr in children
            stack = [ch for ch in self.children]
            while stack:
                desc = stack.pop()
                if desc.expr is old_expr:
                    desc._expr = rhs
                    stack.extend(desc2 for desc2 in desc.children)

    def coerce(self, desired_type: Optional[Type.Base] = None) -> "Base":
        """
        Coerce the value to the desired type and return it. Types should be
        checked statically on ``WDL.Expr.Base`` prior to evaluation.

        :raises: ReferenceError for a null value and non-optional type
        """
        if isinstance(desired_type, Type.String):
            return String(str(self), self.expr)
        if isinstance(desired_type, Type.Array) and self.type.coerces(
            desired_type.item_type, check_quant=False
        ):
            # coercion of T to Array[T] (x to [x])
            # if self is an Array, then Array.coerce precludes this path
            return Array(desired_type, [self.coerce(desired_type.item_type)], self.expr)
        if desired_type and not self.type.coerces(desired_type):
            # owing to static type-checking, this path should arise only rarely e.g. read_json()
            raise Error.InputError(f"cannot coerce {str(self.type)} to {str(desired_type)}")
        return self

    def expect(self, desired_type: Optional[Type.Base] = None) -> "Base":
        """Alias for coerce"""
        return self.coerce(desired_type)

    @property
    def json(self) -> Any:
        """Return a value representation which can be serialized to JSON using ``json.dumps``"""
        """(str, int, float, list, dict, or null)"""
        return self.value

    @property
    def children(self) -> "Iterable[Base]":
        return []


class Boolean(Base):
    """``value`` has Python type ``bool``"""

    def __init__(self, value: bool, expr: "Optional[Expr.Base]" = None) -> None:
        super().__init__(Type.Boolean(), value, expr)


class Float(Base):
    """``value`` has Python type ``float``"""

    def __init__(self, value: float, expr: "Optional[Expr.Base]" = None) -> None:
        super().__init__(Type.Float(), value, expr)

    def __str__(self) -> str:
        return "{:.6f}".format(self.value)


class Int(Base):
    """``value`` has Python type ``int``"""

    def __init__(self, value: int, expr: "Optional[Expr.Base]" = None) -> None:
        super().__init__(Type.Int(), value, expr)

    def coerce(self, desired_type: Optional[Type.Base] = None) -> Base:
        """"""
        if isinstance(desired_type, Type.Float):
            return Float(float(self.value), self.expr)
        return super().coerce(desired_type)


class String(Base):
    """``value`` has Python type ``str``"""

    def __init__(
        self, value: str, expr: "Optional[Expr.Base]" = None, subtype: Optional[Type.Base] = None
    ) -> None:
        subtype = subtype or Type.String()
        super().__init__(subtype, value, expr)

    def coerce(self, desired_type: Optional[Type.Base] = None) -> Base:
        """"""
        if isinstance(desired_type, Type.String):
            return String(self.value, self.expr)
        if isinstance(desired_type, Type.File) and not isinstance(self, File):
            return File(self.value, self.expr)
        if isinstance(desired_type, Type.Directory) and not isinstance(self, Directory):
            return Directory(self.value, self.expr)
        try:
            if isinstance(desired_type, Type.Int):
                return Int(int(self.value), self.expr)
            if isinstance(desired_type, Type.Float):
                return Float(float(self.value), self.expr)
        except ValueError as exn:
            msg = f"coercing String to {desired_type}: {exn}"
            raise Error.EvalError(self.expr, msg) if self.expr else Error.RuntimeError(msg)
        return super().coerce(desired_type)


class File(String):
    """``value`` has Python type ``str``"""

    def __init__(self, value: str, expr: "Optional[Expr.Base]" = None) -> None:
        super().__init__(value, expr=expr, subtype=Type.File())
        if value != value.rstrip("/"):
            raise Error.InputError("WDL.Value.File invalid path: " + value)


class Directory(String):
    """``value`` has Python type ``str``"""

    def __init__(self, value: str, expr: "Optional[Expr.Base]" = None) -> None:
        super().__init__(value, expr=expr, subtype=Type.Directory())


class Array(Base):
    """``value`` is a Python ``list`` of other ``WDL.Value.Base`` instances"""

    value: List[Base]
    type: Type.Array

    def __init__(
        self, item_type: Type.Base, value: List[Base], expr: "Optional[Expr.Base]" = None
    ) -> None:
        self.value = []
        self.type = Type.Array(item_type, nonempty=(len(value) > 0))
        super().__init__(self.type, value, expr)

    @property
    def json(self) -> Any:
        """"""
        return [item.json for item in self.value]

    def __str__(self) -> Any:
        # nb: this is NOT json.dumps(self.json) because it applies item __str__ overrides
        return "[" + ", ".join(str(item) for item in self.value) + "]"

    @property
    def children(self) -> Iterable[Base]:
        return self.value

    def coerce(self, desired_type: Optional[Type.Base] = None) -> Base:
        """"""
        if isinstance(desired_type, Type.Array):
            if desired_type.nonempty and not self.value:
                if self.expr:
                    raise Error.EmptyArray(self.expr)
                else:
                    raise ValueError("Empty array for Array+ input/declaration")
            if desired_type.item_type == self.type.item_type or (
                isinstance(desired_type.item_type, Type.Any)
            ):
                return self
            return Array(
                desired_type.item_type,
                [v.coerce(desired_type.item_type) for v in self.value],
                self.expr,
            )
        return super().coerce(desired_type)


class Map(Base):
    value: List[Tuple[Base, Base]]
    type: Type.Map

    def __init__(
        self,
        item_type: Tuple[Type.Base, Type.Base],
        value: List[Tuple[Base, Base]],
        expr: "Optional[Expr.Base]" = None,
    ) -> None:
        self.value = []
        self.type = Type.Map(item_type)
        super().__init__(self.type, value, expr)

    @property
    def json(self) -> Any:
        """"""
        ans = {}
        if not self.type.item_type[0].coerces(Type.String()):
            msg = f"cannot write {str(self.type)} to JSON"
            raise (Error.EvalError(self.expr, msg) if self.expr else Error.RuntimeError(msg))
        for k, v in self.value:
            kstr = k.coerce(Type.String()).value
            if kstr not in ans:
                ans[kstr] = v.json
        return ans

    def __str__(self) -> Any:
        items = {}
        for k, v in self.value:
            items[str(k)] = str(v)
        return "{" + ", ".join(f"{k}: {v}" for k, v in items.items()) + "}"

    @property
    def children(self) -> Iterable[Base]:
        for k, v in self.value:
            yield k
            yield v

    def coerce(self, desired_type: Optional[Type.Base] = None) -> Base:
        """"""
        if isinstance(desired_type, Type.Map) and desired_type != self.type:
            return Map(
                desired_type.item_type,
                [
                    (k.coerce(desired_type.item_type[0]), v.coerce(desired_type.item_type[1]))
                    for (k, v) in self.value
                ],
                self.expr,
            )
        if isinstance(desired_type, Type.StructInstance):
            # Runtime typecheck for initializing struct from read_{object,objects,map}
            # This couldn't have been checked statically because the map keys weren't known.
            assert self.type.item_type[0].coerces(Type.String())
            try:
                Type.Map(
                    self.type.item_type,
                    self.type.optional,
                    set(kv[0].coerce(Type.String()).value for kv in self.value),
                ).check(desired_type)
            except TypeError as exn:
                msg = "unusable runtime struct initializer"
                if exn.args:
                    msg += ", " + exn.args[0]
                raise (
                    Error.EvalError(
                        self.expr,
                        msg,
                    )
                    if self.expr
                    else Error.RuntimeError(msg)
                )
            assert desired_type.members
            # coerce to desired member types
            ans = {}
            for k, v in self.value:
                ks = k.coerce(Type.String()).value
                try:
                    ans[ks] = v.coerce(desired_type.members[ks])
                except Error.RuntimeError as exc:
                    # some coercions that typecheck could still fail, e.g. String to Int
                    msg = (
                        "runtime type mismatch initializing "
                        f"{desired_type.members[ks]} {ks} member of struct {desired_type.type_name}"
                    ) + ((": " + exc.args[0]) if exc.args else "")
                    raise (
                        Error.EvalError(
                            self.expr,
                            msg,
                        )
                        if self.expr
                        else Error.RuntimeError(msg)
                    )
            return Struct(desired_type, ans, self.expr)
        return super().coerce(desired_type)


class Pair(Base):
    value: Tuple[Base, Base]
    type: Type.Pair

    def __init__(
        self,
        left_type: Type.Base,
        right_type: Type.Base,
        value: Tuple[Base, Base],
        expr: "Optional[Expr.Base]" = None,
    ) -> None:
        self.value = value
        self.type = Type.Pair(left_type, right_type)
        super().__init__(self.type, value, expr)

    def __str__(self) -> str:
        assert isinstance(self.value, tuple)
        return "(" + str(self.value[0]) + "," + str(self.value[1]) + ")"

    @property
    def json(self) -> Any:
        """"""
        return {"left": self.value[0].json, "right": self.value[1].json}

    @property
    def children(self) -> Iterable[Base]:
        yield self.value[0]
        yield self.value[1]

    def coerce(self, desired_type: Optional[Type.Base] = None) -> Base:
        """"""
        if isinstance(desired_type, Type.Pair) and desired_type != self.type:
            return Pair(
                desired_type.left_type,
                desired_type.right_type,
                (
                    self.value[0].coerce(desired_type.left_type),
                    self.value[1].coerce(desired_type.right_type),
                ),
                self.expr,
            )
        return super().coerce(desired_type)


class Null(Base):
    """Represents the missing value which optional inputs may take.
    ``type`` and ``value`` are both None."""

    def __init__(self, expr: "Optional[Expr.Base]" = None) -> None:
        super().__init__(Type.Any(null=True), None, expr)

    def coerce(self, desired_type: Optional[Type.Base] = None) -> Base:
        """"""
        if desired_type and not desired_type.optional and not isinstance(desired_type, Type.Any):
            if isinstance(desired_type, (Type.File, Type.Directory)):
                # This case arises processing task outputs; we convert nonexistent paths to Null
                # before coercing to the declared output type (+ checking whether it's optional).
                raise FileNotFoundError()
            # normally the typechecker should prevent the following cases, but it might have had
            # check_quant=False
            if isinstance(desired_type, Type.String):
                return String("", self.expr)
            if isinstance(desired_type, Type.Array) and desired_type.item_type.optional:
                return Array(desired_type, [self.coerce(desired_type.item_type)], self.expr)
            if self.expr:
                raise Error.NullValue(self.expr)
            raise Error.InputError("'None' for non-optional input/declaration")
        return self

    def __str__(self) -> str:
        return "None"

    @property
    def json(self) -> Any:
        """"""
        return None


class Struct(Base):
    value: Dict[str, Base]

    # records the names of any extraneous keys that were present in the JSON/Map/Object from which
    # this struct was initialized
    extra: Set[str]

    def __init__(
        self,
        type: Union[Type.Object, Type.StructInstance],
        value: Dict[str, Base],
        expr: "Optional[Expr.Base]" = None,
        extra: Optional[Set[str]] = None,
    ) -> None:
        # type may be Object for the transient evaluation of an object literal or read_json(); we
        # expect it to be coerced to a StructInstance in short order.
        value = dict(value)
        if isinstance(type, Type.StructInstance):
            # fill in null for any omitted optional members
            assert type.members
            for k in type.members:
                if k not in value:
                    assert type.members[k].optional
                    value[k] = Null()
        self.value = value
        self.extra = extra or set()
        super().__init__(type, value, expr)

    def coerce(self, desired_type: Optional[Type.Base] = None) -> Base:
        """"""
        if isinstance(desired_type, Type.StructInstance):
            return self._coerce_to_struct(desired_type)
        if isinstance(desired_type, Type.Map):
            return self._coerce_to_map(desired_type)
        if not isinstance(desired_type, (Type.Any, Type.Object)):
            self._eval_error(f"cannot coerce struct to {desired_type}")
        # Object coercion is a no-op because we expect a further coercion to StructInstance to
        # follow in short order, providing the expected member types.
        return self

    def _coerce_to_struct(self, desired_type: Type.StructInstance) -> Base:
        assert desired_type.members
        if isinstance(self.type, Type.StructInstance) and self.type.type_id == desired_type.type_id:
            return self
        try:
            # Runtime typecheck for initializing StructInstance from read_json(), where the
            # Object type isn't known until runtime
            self.type.check(desired_type)
        except TypeError as exn:
            msg = "unusable runtime struct initializer"
            if exn.args:
                msg += ", " + exn.args[0]
            self._eval_error(msg)
        # coerce to desired member types
        members = {}
        extra = set()
        for k in self.value:
            if k not in desired_type.members:
                extra.add(k)
            else:
                try:
                    members[k] = self.value[k].coerce(desired_type.members[k])
                except Error.RuntimeError as exc:
                    # some coercions that typecheck could still fail, e.g. String to Int; note the
                    # offending member, taking care not to obscure it if the struct is nested
                    msg = ""
                    if exc.args:
                        if "member of struct" in exc.args[0]:
                            raise
                        msg = ": " + exc.args[0]
                    msg = (
                        "runtime type mismatch initializing "
                        f"{desired_type.members[k]} {k} member of struct {desired_type.type_name}"
                    ) + msg
                    self._eval_error(msg)
        return Struct(desired_type, members, expr=self.expr, extra=extra)

    def _coerce_to_map(self, desired_type: Type.Map) -> Map:
        # runtime coercion e.g. Map[String,String] foo = read_json("foo.txt")
        assert isinstance(self.type, Type.Object)
        key_type = desired_type.item_type[0]
        if not Type.String().coerces(key_type):
            self._eval_error(f"cannot coerce struct member names to {desired_type} keys")
        value_type = desired_type.item_type[1]
        entries = []
        for k, v in self.value.items():
            if not isinstance(v, Null) or value_type.optional:
                map_key = None
                map_value = None
                try:
                    map_key = String(k).coerce(key_type)
                except Error.RuntimeError:
                    self._eval_error(f"cannot coerce struct member name {k} to {desired_type} key")
                if self.type.members[k].coerces(value_type):
                    with suppress(Error.RuntimeError):
                        map_value = v.coerce(value_type)
                if map_value is None:
                    self._eval_error(
                        "cannot coerce struct member"
                        f" {self.type.members[k]} {k} to {value_type} map value"
                    )
                assert map_key and map_value
                entries.append((map_key, map_value))
        return Map(desired_type.item_type, entries)

    def _eval_error(self, msg: str) -> None:
        raise (
            Error.EvalError(
                self.expr,
                msg,
            )
            if self.expr
            else Error.RuntimeError(msg)
        ) from None

    def __str__(self) -> Any:
        return "{" + ", ".join(f"{k}: {str(v)}" for k, v in self.value.items()) + "}"

    @property
    def json(self) -> Any:
        """"""
        ans = {}
        for k, v in self.value.items():
            ans[k] = v.json
        return ans

    @property
    def children(self) -> Iterable[Base]:
        return self.value.values()


def from_json(type: Type.Base, value: Any) -> Base:
    """
    Instantiate a WDL value of the specified type from a parsed JSON value (str, int, float, list,
    dict, or null).

    If type is :class:`WDL.Type.Any()`, attempts to infer a WDL type & value from the JSON's
    intrinsic types. This isn't ideal; for example, Files can't be distinguished from Strings, and
    JSON lists and dicts with heterogeneous item types may give undefined results.

    :raise WDL.Error.InputError: if the given value isn't coercible to the specified type
    """
    if isinstance(type, Type.Any):
        return _infer_from_json(value)
    if isinstance(type, (Type.Boolean, Type.Any)) and value in [True, False]:
        return Boolean(value)
    if isinstance(type, (Type.Int, Type.Any)) and isinstance(value, int):
        return Int(value)
    if isinstance(type, (Type.Float, Type.Any)) and isinstance(value, (float, int)):
        return Float(float(value))
    if isinstance(type, Type.File) and isinstance(value, str):
        return File(value)
    if isinstance(type, Type.Directory) and isinstance(value, str):
        return Directory(value)
    if isinstance(type, (Type.String, Type.Any)) and isinstance(value, str):
        return String(value)
    if isinstance(type, Type.Array) and isinstance(value, list):
        return Array(type.item_type, [from_json(type.item_type, item) for item in value])
    if isinstance(type, Type.Pair) and isinstance(value, dict) and set(value) == {"left", "right"}:
        return Pair(
            type.left_type,
            type.right_type,
            (from_json(type.left_type, value["left"]), from_json(type.right_type, value["right"])),
        )
    if (
        isinstance(type, Type.Map)
        and Type.String().coerces(type.item_type[0])
        and isinstance(value, dict)
    ):
        items = []
        for k, v in value.items():
            assert isinstance(k, str)
            items.append((String(k).coerce(type.item_type[0]), from_json(type.item_type[1], v)))
        return Map(type.item_type, items)
    if isinstance(type, Type.StructInstance) and isinstance(value, dict) and type.members:
        for k, ty in type.members.items():
            if k not in value and not ty.optional:
                raise Error.InputError(
                    f"initializer for struct {str(type)} omits required field(s)"
                )
        members = {}
        extra = set()
        for k, v in value.items():
            assert isinstance(k, str)
            if k not in type.members:
                extra.add(k)
            else:
                try:
                    members[k] = from_json(type.members[k], v)
                except Error.InputError:
                    raise Error.InputError(
                        f"couldn't initialize struct {str(type)} {type.members[k]} {k} from {json.dumps(v)}"
                    ) from None
        # Struct.__init__ will populate null for any omitted optional members
        return Struct(type, members, extra=extra)
    if type.optional and value is None:
        return Null()
    raise Error.InputError(f"couldn't construct {str(type)} from {json.dumps(value)}")


def _infer_from_json(j: Any) -> Base:
    if isinstance(j, str):
        return String(j)
    if isinstance(j, bool):
        return Boolean(j)
    if isinstance(j, int):
        return Int(j)
    if isinstance(j, float):
        return Float(j)
    if j is None:
        return Null()
    # compound: don't yet try to infer unified types for nested values, since we expect a coercion
    # to a StructInstance type to follow in short order, providing the expected item/member types
    if isinstance(j, list):
        return Array(Type.Any(), [_infer_from_json(v) for v in j])
    if isinstance(j, dict):
        members = {}
        member_types = {}
        for k in j:
            assert isinstance(k, str)
            members[k] = _infer_from_json(j[k])
            member_types[k] = members[k].type
        return Struct(Type.Object(member_types), members)
    raise Error.InputError(f"couldn't construct value from: {json.dumps(j)}")


def rewrite_paths(v: Base, f: Callable[[Union[File, Directory]], Optional[str]]) -> Base:
    """
    Produce a deep copy of the given Value with all File & Directory paths (including those nested
    inside compound Values) rewritten by the given function. The function may return None to
    replace the File/Directory value with None/Null.
    """

    def map_paths(w: Base) -> Base:
        w = copy.copy(w)
        if isinstance(w, (File, Directory)):
            fw = f(w)
            if fw is None:
                return Null(expr=w.expr)
            w.value = fw
        # recursive descent into compound Values
        elif isinstance(w.value, list):
            value2: List[Any] = []
            for elt in w.value:
                if isinstance(elt, tuple):
                    assert len(elt) == 2 and all(isinstance(x, Base) for x in elt)
                    value2.append((map_paths(elt[0]), map_paths(elt[1])))
                else:
                    assert isinstance(elt, Base)
                    value2.append(map_paths(elt))
            w.value = value2
        elif isinstance(w.value, tuple):
            assert len(w.value) == 2 and sum(1 for x in w.value if not isinstance(x, Base)) == 0
            w.value = (map_paths(w.value[0]), map_paths(w.value[1]))
        elif isinstance(w.value, dict):
            value3 = {}
            for key in w.value:
                assert isinstance(key, str) and isinstance(w.value[key], Base)
                value3[key] = map_paths(w.value[key])
            w.value = value3
        else:
            assert w.value is None or isinstance(w.value, (int, float, bool, str))
        return w

    return map_paths(v)


def rewrite_env_paths(
    env: Env.Bindings[Base], f: Callable[[Union[File, Directory]], Optional[str]]
) -> Env.Bindings[Base]:
    """
    Produce a deep copy of the given Value Env with all File & Directory paths rewritten by the
    given function.
    """
    return env.map(lambda binding: Env.Binding(binding.name, rewrite_paths(binding.value, f)))


def rewrite_files(v: Base, f: Callable[[str], Optional[str]]) -> Base:
    """
    Produce a deep copy of the given Value with all File names rewritten by the given function
    (including Files nested inside compound Values).

    (deprecated: use ``rewrite_paths`` to handle Directory values as well)
    """

    return rewrite_paths(v, lambda fd: f(fd.value) if isinstance(fd, File) else fd.value)


def rewrite_env_files(
    env: Env.Bindings[Base], f: Callable[[str], Optional[str]]
) -> Env.Bindings[Base]:
    """
    Produce a deep copy of the given Value Env with all File names rewritten by the given function.

    (deprecated: use ``rewrite_env_paths`` to handle Directory values as well)
    """
    return env.map(lambda binding: Env.Binding(binding.name, rewrite_files(binding.value, f)))


def digest_env(env: Env.Bindings[Base]) -> str:
    """
    Digest the Value Env, for use e.g. as a cache key. The digest is an opaque string of a few
    dozen alphanumeric characters.
    """
    from . import values_to_json

    env_json = json.dumps(values_to_json(env), separators=(",", ":"), sort_keys=True)
    sha256 = hashlib.sha256(env_json.encode("utf-8")).digest()
    return base64.b32encode(sha256[:20]).decode().lower()
