"""
WDL data types

WDL has both atomic types such as ``Int``, ``Boolean``, and ``String``; and
parametric types like ``Array[String]`` and
``Map[String,Array[Array[Float]]]``. Here, each type is represented by an
immutable instance of a Python class inheriting from ``WDL.Type.Base``. Such
types are associated with expressions, statically prior to evaluation, as well
as with values and identifier bindings after evaluation.

An atomic type like ``Int`` is represented by ``WDL.Type.Int()``. Atomic types
can be checked either with ``isinstance(t,WDL.Type.Int)``, which ignores the
possible optional quantifier (thus satisfied by ``Int`` or ``Int?``), or with
``t == WDL.Type.Int(optional=True)`` to include the quantifier in the
comparison.

A parametric type like ``Array[String]`` is represented by
``WDL.Type.Array(WDL.Type.String())``. Any kind of array satisfies
``isinstance(t,WDL.Type.Array)``, and
``WDL.Type.Array(WDL.Type.String()) == WDL.Type.Array(WDL.Type.String())``, but
for example
``WDL.Type.Array(WDL.Type.String()) != WDL.Type.Array(WDL.Type.Float())``.

The type classes include a method indicating if a value of the type can be
coerced to some other desired type, according to the following rules:

1. ``Int`` coerces to ``Float``
2. ``Boolean``, ``Int``, ``Float``, and ``File`` coerce to ``String``
3. ``String`` coerces to ``File``, ``Int``, and ``Float``
4. ``Array[T]`` coerces to ``String`` provided ``T`` does as well
5. ``T`` coerces to ``T?`` but the reverse is not true in general*
6. ``Array[T]+`` coerces to ``Array[T]`` but the reverse is not true in general*

(*) The reverse coercions are statically permitted in expressions set up with
``Expr.infer_type(check_quant=False)`` although they may fail at runtime. This
also enables coercion of ``T`` to ``Array[T]+`` (an array of length 1).

.. inheritance-diagram:: WDL.Type
   :top-classes: WDL.Type.Base
"""

import copy
import typing
from abc import ABC
from typing import Optional, Tuple, Dict, Iterable, Set, List, TYPE_CHECKING

if TYPE_CHECKING:
    from .Error import SourcePosition


class Base(ABC):
    """The abstract base class for WDL types

    Each specific type inherits from this base, e.g.::

        assert issubclass(WDL.Type.Int, WDL.Type.Base)
        assert isinstance(WDL.Type.Array(WDL.Type.Int()), WDL.Type.Base)

    All instances are immutable.
    """

    _optional: bool = False  # immutable!!!

    # pos is set on Type objects instantiated by the WDL syntax parser (mainly in Decl). Other Type
    # objects are instantiated in other ways (e.g. Value describing itself), so will not have pos.
    pos: "Optional[SourcePosition]" = None

    def coerces(self, rhs: "Base", check_quant: bool = True) -> bool:
        """
        True if this is the same type as, or can be coerced to, ``rhs``.

        :param check_quant: when ``False``, disables static enforcement of the optional (?) type quantifier
        """
        try:
            self.check(rhs, check_quant)
        except TypeError:
            return False
        return True

    def check(self, rhs: "Base", check_quant: bool = True) -> None:
        """
        Verify this is the same type as, or can be coerced to ``rhs``. The ``TypeError`` exception
        raised otherwise MAY include a specific error message (but not if the obvious "cannot
        coerce self to rhs" suffices).

        :param check_quant: when ``False``, disables static enforcement of the optional (?) type quantifier
        """
        if not check_quant and isinstance(rhs, Array) and self.coerces(rhs.item_type, check_quant):
            # coerce T to Array[T]
            return
        if type(self).__name__ != type(rhs).__name__ and not isinstance(rhs, Any):
            raise TypeError()
        self._check_optional(rhs, check_quant)

    def _check_optional(self, rhs: "Base", check_quant: bool) -> None:
        if check_quant and (self.optional and not rhs.optional and not isinstance(rhs, Any)):
            raise TypeError()

    @property
    def optional(self) -> bool:
        """
        :type: bool

        True when the type has the optional quantifier, ``T?``"""
        return self._optional

    @property
    def parameters(self) -> Iterable["Base"]:
        """
        :type: Iterable[WDL.Type.Base]

        The type's parameters, if any (e.g. item type of Array; left & right
        types of Pair; etc.)
        """
        return []

    def copy(self, optional: Optional[bool] = None) -> "Base":
        """
        copy(self, optional : Optional[bool] = None) -> WDL.Type.Base

        Create a copy of the type, possibly with a different setting of the
        ``optional`` quantifier.
        """
        ans: "Base" = copy.copy(self)
        if optional is not None:
            ans._optional = optional
        return ans

    def __str__(self) -> str:
        return type(self).__name__ + ("?" if self.optional else "")

    def __eq__(self, rhs: typing.Any) -> bool:
        return isinstance(rhs, Base) and str(self) == str(rhs)

    def equatable(self, rhs: "Base", *, compound: bool = False) -> bool:
        """
        Check if values of the given types may be equated with the WDL == operator (and its
        negation). This mostly requires they have the same type, with quirks like ignoring
        quantifiers and Int/Float coercion (allowed at 'top level' but not within compound types).
        """
        return isinstance(rhs, (type(self), Any))  # intentionally ignores optional quantifier

    def comparable(self, rhs: "Base", *, check_quant: bool = True) -> bool:
        """
        Check if values of the given types may be compared with the WDL comparison operators (<, <=,
        >, >=).
        """
        # Since this is currently only allowed for primitive types, we can code all cases here
        # instead of fanning out to subclasses (still possible if we need to in the future).
        allowed = (Int, Float, String, Boolean)
        if not (isinstance(self, allowed) and isinstance(rhs, allowed)):
            return False
        if check_quant and (self.optional or rhs.optional):
            return False
        if isinstance(self, (Int, Float)) and isinstance(rhs, (Int, Float)):
            return True
        return isinstance(rhs, type(self))


class Any(Base):
    """
    A symbolic type which coerces to any other type; used to represent e.g. the item type of an empty array literal, or
    the result of read_json().

    The ``optional`` attribute shall be true only for WDL ``None`` literals, which coerce to optional types only.
    """

    def __init__(self, optional: bool = False, null: bool = False) -> None:
        self._optional = null  # True only for None literals

    def check(self, rhs: Base, check_quant: bool = True) -> None:
        """"""
        self._check_optional(rhs, check_quant)

    def __str__(self) -> str:
        return "None" if self._optional else "Any"

    def equatable(self, rhs, *, compound: bool = False):
        return True


class Boolean(Base):
    def __init__(self, optional: bool = False) -> None:
        self._optional = optional

    def check(self, rhs: Base, check_quant: bool = True) -> None:
        """"""
        if isinstance(rhs, String):
            return self._check_optional(rhs, check_quant)
        super().check(rhs, check_quant)


class Float(Base):
    def __init__(self, optional: bool = False) -> None:
        self._optional = optional

    def check(self, rhs: Base, check_quant: bool = True) -> None:
        """"""
        if isinstance(rhs, String):
            return self._check_optional(rhs, check_quant)
        super().check(rhs, check_quant)

    def equatable(self, rhs, *, compound: bool = False):
        # per WDL spec, Int/Float can be equated directly, but not as part of a compound type
        return super().equatable(rhs, compound=compound) or (not compound and isinstance(rhs, Int))


class Int(Base):
    def __init__(self, optional: bool = False) -> None:
        self._optional = optional

    def check(self, rhs: Base, check_quant: bool = True) -> None:
        """"""
        if isinstance(rhs, Float):
            return self._check_optional(rhs, check_quant)
        if isinstance(rhs, String):
            return self._check_optional(rhs, check_quant)
        super().check(rhs, check_quant)

    def equatable(self, rhs, *, compound: bool = False):
        return super().equatable(rhs, compound=compound) or (
            not compound and isinstance(rhs, Float)
        )


class File(Base):
    def __init__(self, optional: bool = False) -> None:
        self._optional = optional

    def check(self, rhs: Base, check_quant: bool = True) -> None:
        """"""
        if isinstance(rhs, String):
            return self._check_optional(rhs, check_quant)
        super().check(rhs, check_quant)


class Directory(Base):
    def __init__(self, optional: bool = False) -> None:
        self._optional = optional

    def check(self, rhs: Base, check_quant: bool = True) -> None:
        """"""
        if isinstance(rhs, String):
            return self._check_optional(rhs, check_quant)
        super().check(rhs, check_quant)


class String(Base):
    def __init__(self, optional: bool = False) -> None:
        self._optional = optional

    def check(self, rhs: Base, check_quant: bool = True) -> None:
        """"""
        if isinstance(rhs, (File, Directory, Int, Float)):
            return self._check_optional(rhs, check_quant)
        super().check(rhs, check_quant)


class Array(Base):
    """
    Array type, parameterized by the type of the constituent items.
    """

    item_type: Base  # TODO: make immutable property
    """
    :type: WDL.Type.Base

    ``item_type`` may be ``Any`` when not known statically, such as in a literal empty array ``[]``.
    """
    _nonempty: bool

    def __init__(self, item_type: Base, optional: bool = False, nonempty: bool = False) -> None:
        assert item_type
        self.item_type = item_type
        assert isinstance(nonempty, bool)
        self._optional = optional
        self._nonempty = nonempty

    def __str__(self) -> str:
        ans = (
            "Array["
            + str(self.item_type)
            + "]"
            + ("+" if self.nonempty else "")
            + ("?" if self.optional else "")
        )
        return ans

    @property
    def nonempty(self) -> bool:
        """
        :type: bool

        True when the type has the nonempty quantifier, ``Array[T]+``
        """
        return self._nonempty

    @property
    def parameters(self) -> Iterable[Base]:
        yield self.item_type

    def check(self, rhs: Base, check_quant: bool = True) -> None:
        """"""
        if isinstance(rhs, Array):
            self.item_type.check(rhs.item_type, check_quant)
            return self._check_optional(rhs, check_quant)
        if isinstance(rhs, String):
            if self.item_type is not None:
                self.item_type.check(String())
            return self._check_optional(rhs, check_quant)
        super().check(rhs, check_quant)

    def copy(self, optional: Optional[bool] = None, nonempty: Optional[bool] = None) -> Base:
        ans = super().copy(optional)
        if nonempty is not None:
            setattr(ans, "_nonempty", nonempty)
        return ans

    def equatable(self, rhs, *, compound: bool = False):
        # intentionally ignores optional and nonempty quantifiers:
        return isinstance(rhs, Array) and self.item_type.equatable(rhs.item_type, compound=True)


class Map(Base):
    """
    Map type, parameterized by the (key,value) item type.
    """

    item_type: Tuple[Base, Base]
    """
    :type: Tuple[WDL.Type.Base,WDL.Type.Base]

    The key and value types may be ``Any`` when not known statically, such as in a literal empty map ``{}``.
    """

    literal_keys: Optional[Set[str]]
    ""
    # Special use: Map[String,_] literal stores the key names here for potential use in
    # struct coercions where we need them. (Normally the Map type would record the common
    # type of the keys but not the keys themselves.)

    def __init__(
        self,
        item_type: Tuple[Base, Base],
        optional: bool = False,
        literal_keys: Optional[Set[str]] = None,
    ) -> None:
        self._optional = optional
        if item_type is None:
            item_type = (Any(), Any())
        self.item_type = item_type
        self.literal_keys = literal_keys

    def __str__(self) -> str:
        return (
            "Map["
            + (
                str(self.item_type[0]) + "," + str(self.item_type[1])
                if self.item_type is not None
                else ""
            )
            + "]"
            + ("?" if self.optional else "")
        )

    @property
    def parameters(self) -> Iterable[Base]:
        yield self.item_type[0]
        yield self.item_type[1]

    def check(self, rhs: Base, check_quant: bool = True) -> None:
        """"""
        if isinstance(rhs, Map):
            self.item_type[0].check(rhs.item_type[0], check_quant)
            self.item_type[1].check(rhs.item_type[1], check_quant)
            return self._check_optional(rhs, check_quant)
        if isinstance(rhs, StructInstance) and self.literal_keys is not None:
            # struct assignment from map literal
            return _check_struct_members(
                {k: self.item_type[1] for k in self.literal_keys},
                rhs,
                check_quant,
            )
        if (
            isinstance(rhs, StructInstance)
            and self.literal_keys is None
            and self.item_type[0] == String()
        ):
            # Allow attempt to runtime-coerce a non-literal Map[String,_] to StructInstance.
            # Unlike a literal, we don't (during static validation) know what the keys will be, so
            # we can't typecheck it thoroughly (Lint warning will apply). This is used initializing
            # structs from read_map() or read_object[s]().
            return
        super().check(rhs, check_quant)

    def equatable(self, rhs, *, compound: bool = False):
        return (
            isinstance(rhs, Map)
            and self.item_type[0].equatable(rhs.item_type[0], compound=True)
            and self.item_type[1].equatable(rhs.item_type[1], compound=True)
        )


class Pair(Base):
    """
    Pair type, parameterized by the left and right item types.
    """

    left_type: Base
    """
    :type: WDL.Type.Base
    """
    right_type: Base
    """
    :type: WDL.Type.Base
    """

    def __init__(self, left_type: Base, right_type: Base, optional: bool = False) -> None:
        self._optional = optional
        self.left_type = left_type
        self.right_type = right_type

    def __str__(self) -> str:
        return (
            "Pair["
            + (str(self.left_type) + "," + str(self.right_type))
            + "]"
            + ("?" if self.optional else "")
        )

    @property
    def parameters(self) -> Iterable[Base]:
        yield self.left_type
        yield self.right_type

    def check(self, rhs: Base, check_quant: bool = True) -> None:
        """"""
        if isinstance(rhs, Pair):
            self.left_type.check(rhs.left_type, check_quant)
            self.right_type.check(rhs.right_type, check_quant)
            return self._check_optional(rhs, check_quant)
        super().check(rhs, check_quant)

    def equatable(self, rhs, *, compound: bool = True):
        return (
            isinstance(rhs, Pair)
            and self.left_type.equatable(rhs.left_type, compound=True)
            and self.right_type.equatable(rhs.right_type, compound=True)
        )


class StructInstance(Base):
    """
    Type of an instance of a struct

    Not to be confused with struct type definition, :class:`WDL.Tree.StructTypeDef`. To find the
    ``WDL.Tree.StructTypeDef`` in the current ``doc: WDL.Tree.Document`` corresponding to
    ``ty: WDL.Type.StructInstance``, use ``doc.struct_typedefs[ty.type_name]``.
    """

    type_name: str
    """
    :type: str

    The struct type name with which the instance is declared; note that the
    same struct type can go by different names.
    """

    members: Optional[Dict[str, Base]]
    """
    :type: Dict[str,WDL.Type.Base]

    Names and types of the struct members, from the struct type definition
    (available after typechecking)
    """

    def __init__(self, type_name: str, optional: bool = False) -> None:
        self._optional = optional
        self.type_name = type_name
        self.members = None

    def __str__(self) -> str:
        return self.type_name + ("?" if self.optional else "")

    def check(self, rhs: Base, check_quant: bool = True) -> None:
        """"""
        if isinstance(rhs, StructInstance):
            if self.type_id != rhs.type_id:
                raise TypeError()
            return self._check_optional(rhs, check_quant)
        super().check(rhs, check_quant)

    @property
    def type_id(self) -> str:
        """
        :type: str

        A string canonically describing the member names and their types, excluding the struct type name; useful to
        unify aliased struct types.
        """
        assert isinstance(self.members, dict)
        return _struct_type_id(self.members)

    @property
    def parameters(self) -> Iterable[Base]:
        assert self.members is not None
        return self.members.values()

    def equatable(self, rhs, *, compound: bool = False):
        return isinstance(rhs, StructInstance) and self.type_id == rhs.type_id


def _struct_type_id(members: Dict[str, Base]) -> str:
    # generates a content hash of the struct type definition, used to recognize
    # equivalent struct types going by different aliases
    ans = []
    for name, ty in sorted(members.items()):
        if isinstance(ty, StructInstance):
            assert ty.members
            sty = _struct_type_id(ty.members) + ("?" if ty.optional else "")
        else:
            sty = str(ty)
        ans.append(name + " : " + sty)
    return "struct(" + ", ".join(ans) + ")"


class Object(Base):
    """"""

    # Represents the type of object{} literals and the known-only-at-runtime return value of
    # read_json(). We expect this to exist only transiently, just before attempting coercion to
    # a StructInstance with known member types. We hide this from docs to avoid confusion with
    # general (pre-WDL1.0) Object support, since it's only to support struct initialization.

    members: Dict[str, Base]

    def __init__(self, members: Dict[str, Base]) -> None:
        self.members = members

    def __str__(self) -> str:
        ans = []
        for name, ty in sorted(self.members.items()):
            ans.append(name + " : " + str(ty))
        return "object(" + ", ".join(ans) + ")"

    @property
    def parameters(self) -> Iterable[Base]:
        return self.members.values()

    def check(self, rhs: Base, check_quant: bool = True) -> None:
        if isinstance(rhs, StructInstance):
            return _check_struct_members(self.members, rhs, check_quant)
        if isinstance(rhs, Map):
            # Member names must coerce to the map key type, and each member type must coerce to the
            # map value type.
            String().check(rhs.item_type[0])
            for vt in self.members.values():
                vt.check(rhs.item_type[1], check_quant=check_quant)
            return
        if isinstance(rhs, (Any, Object)):
            # Don't worry about Object coercion because we expect a further coercion to
            # StructInstance to follow in short order, constraining the expected member types.
            return
        raise TypeError()

    def equatable(self, rhs, *, compound: bool = False):
        return False


def _check_struct_members(
    self_members: Dict[str, Base], rhs: StructInstance, check_quant: bool
) -> None:
    # shared routine for checking Map or Object type coercion, with useful error messages
    rhs_members = rhs.members
    assert rhs_members
    rhs_keys = set(rhs_members.keys())
    self_keys = set(self_members.keys())

    missing_keys = list(k for k in rhs_keys - self_keys if not rhs_members[k].optional)
    if missing_keys:
        raise TypeError(
            "missing non-optional member(s) in struct "
            f"{rhs.type_name}: {' '.join(sorted(missing_keys))}"
        )
    for k in self_keys.intersection(rhs_keys):
        try:
            self_members[k].check(rhs_members[k], check_quant)
        except TypeError as exn:
            if len(exn.args):
                raise
            raise TypeError(
                f"type mismatch using {self_members[k]} to initialize "
                f"{rhs_members[k]} {k} member of struct {rhs.type_name}"
            )


def unify(types: List[Base], check_quant: bool = True, force_string: bool = False) -> Base:
    """
    Given a list of types, compute a type to which they're all coercible, or :class:`WDL.Type.Any`
    if no more-specific inference is possible.

    :param force_string: permit last-resort unification to ``String`` even if no item is currently
                         a ``String``, but all can be coerced
    """
    if not types:
        return Any()

    # begin with first non-String type (as almost everything is coercible to string); or if
    # --no-quant-check, the first array type (as we can try to promote other T to Array[T])
    t = next((t for t in types if not isinstance(t, (String, Any))), types[0])
    if not check_quant:
        t = next((a for a in types if isinstance(a, Array) and not isinstance(a.item_type, Any)), t)
    t = t.copy()

    # potentially promote/generalize t to other types seen
    optional = False
    all_nonempty = True
    all_stringifiable = True
    for t2 in types:
        # recurse on parameters of compound types
        t_was_array_any = isinstance(t, Array) and isinstance(t.item_type, Any)
        if isinstance(t, Array) and isinstance(t2, Array) and not isinstance(t2.item_type, Any):
            t.item_type = unify([t.item_type, t2.item_type], check_quant, force_string)
        if isinstance(t, Pair) and isinstance(t2, Pair):
            t.left_type = unify([t.left_type, t2.left_type], check_quant, force_string)
            t.right_type = unify([t.right_type, t2.right_type], check_quant, force_string)
        if isinstance(t, Map) and isinstance(t2, Map):
            t.item_type = (
                unify([t.item_type[0], t2.item_type[0]], check_quant, force_string),
                unify([t.item_type[1], t2.item_type[1]], check_quant, force_string),
            )
        if (
            not t_was_array_any
            and next((pt for pt in t.parameters if isinstance(pt, Any)), None) is not None
        ):
            return Any()
        if isinstance(t, Object) and isinstance(t2, Object):
            # unifying Object types (generally transient, pending coercion to a StructInstance)
            for k in t2.members:
                if k in t.members:
                    t.members[k] = unify([t.members[k], t2.members[k]])
                else:
                    # infer optionality of fields present only in some types
                    t.members[k] = t2.members[k].copy(optional=True)

        # Int/Float, String/File
        if isinstance(t, Int) and isinstance(t2, Float):
            t = Float()

        # String
        if (
            isinstance(t2, String)
            and (not check_quant or not isinstance(t, Array))
            and (not isinstance(t, (Pair, Map)))
        ):
            t = String()
        if not t2.coerces(String(optional=True), check_quant=check_quant):
            all_stringifiable = False

        # optional/nonempty
        if t.optional or t2.optional:
            optional = True
        if isinstance(t, Array) and not t.nonempty or isinstance(t2, Array) and not t2.nonempty:
            all_nonempty = False

    if isinstance(t, Array):
        t = t.copy(nonempty=all_nonempty)
    t = t.copy(optional=optional)

    # check all types are coercible to t
    for t2 in types:
        if not t2.coerces(t, check_quant=check_quant):
            if all_stringifiable and force_string:
                return String(optional=optional)
            return Any()

    return t
