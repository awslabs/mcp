"""
WDL expressions composing literal values, arithmetic, comparison, conditionals,
string interpolation, arrays & maps, and function applications. These appear on
the right-hand side of value declarations and in task command substitutions,
task runtime sections, and workflow scatter and conditional sections.

The abstract syntax tree (AST) for any expression is represented by an instance
of a Python class deriving from ``WDL.Expr.Base``. Any such node may have other
nodes attached "beneath" it. An expression can be evaluated to a ``Value``
given a suitable ``WDL.Env.Bindings[Value.Base]``.

.. inheritance-diagram:: WDL.Expr
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Tuple, Union, Iterable, Set, TYPE_CHECKING
import codecs
import regex
from .Error import SourcePosition, SourceNode
from . import Type, Value, Env, Error, StdLib, Any

if TYPE_CHECKING:
    from . import Tree


class Base(SourceNode, ABC):
    """Superclass of all expression AST nodes"""

    _type: Optional[Type.Base] = None
    _check_quant: bool = True
    _stdlib: "Optional[StdLib.Base]" = None
    _struct_types: Optional[Env.Bindings[Dict[str, Type.Base]]] = None

    @property
    def type(self) -> Type.Base:
        """
        :type: WDL.Type.Base

        WDL type of this expression. Undefined on construction; populated by one
        invocation of ``infer_type``.
        """
        # Failure of this assertion indicates use of an Expr object without
        # first calling _infer_type
        assert self._type is not None
        return self._type

    @abstractmethod
    def _infer_type(self, type_env: Env.Bindings[Type.Base]) -> Type.Base:
        # Abstract protected method called by infer_type(): return the inferred
        # type with no side-effects, obeying self._check_quant.
        pass

    def infer_type(
        self,
        type_env: Env.Bindings[Type.Base],
        stdlib: StdLib.Base,
        check_quant: bool = True,
        struct_types: Optional[Env.Bindings[Dict[str, Type.Base]]] = None,
    ) -> "Base":
        """infer_type(self, type_env : Env.Bindings[Type.Base], stdlib : StdLib.Base) -> WDL.Expr.Base

        Infer the expression's type within the given type environment. Must be
        invoked exactly once prior to use of other methods.

        :param stdlib: a context-specific standard function library for typechecking
        :param check_quant:
            when ``False``, disables static validation of the optional (?) type quantifier when `typecheck()` is called
            on this expression, so for example type ``T?`` can satisfy an expected type ``T``. Applies recursively to
            the type inference and checking of any sub-expressions.
        :raise WDL.Error.StaticTypeMismatch: when the expression fails to type-check
        :return: `self`
        """
        # Failure of this assertion indicates multiple invocations of
        # infer_type
        assert self._type is None
        # recursive descent into child expressions
        with Error.multi_context() as errors:
            for child in self.children:
                assert isinstance(child, Base)
                errors.try1(
                    (
                        lambda child: lambda: child.infer_type(
                            type_env, stdlib, check_quant, struct_types
                        )
                    )(child)
                )
        # invoke derived-class logic. we pass check_quant, stdlib, and struct_types hackily through
        # instance variables since only some subclasses use them.
        self._check_quant = check_quant
        self._stdlib = stdlib
        self._struct_types = struct_types
        try:
            self._type = self._infer_type(type_env)
        finally:
            self._stdlib = None
            self._struct_types = None
        assert self._type and isinstance(self.type, Type.Base)
        return self

    def typecheck(self, expected: Type.Base) -> "Base":
        """typecheck(self, expected : Type.Base) -> WDL.Expr.Base

        Check that this expression's type is, or can be coerced to,
        ``expected``.

        :raise WDL.Error.StaticTypeMismatch:
        :return: `self`
        """
        try:
            self.type.check(expected, self._check_quant)
        except TypeError as exn:
            raise Error.StaticTypeMismatch(
                self, expected, self.type, exn.args[0] if exn.args else ""
            )
        return self

    @abstractmethod
    def _eval(self, env: Env.Bindings[Value.Base], stdlib: StdLib.Base) -> Value.Base:
        # to be overridden by subclasses. eval() calls this and deals with any
        # exceptions raised
        pass

    def eval(self, env: Env.Bindings[Value.Base], stdlib: StdLib.Base, **kwargs) -> Value.Base:
        """
        Evaluate the expression in the given environment

        :param stdlib: a context-specific standard function library implementation
        """
        try:
            ans = self._eval(env, stdlib, **kwargs)
            ans.expr = self
            return ans
        except Error.RuntimeError:
            raise
        except Exception as exn:
            raise Error.EvalError(self, str(exn)) from exn

    @property
    def literal(self) -> Optional[Value.Base]:
        """
        If the expression is a literal constant, return its value; otherwise return None. The
        result can be an instance of ``WDL.Value.Null`` which is distinct from None.
        """
        if isinstance(self, (Boolean, Int, Float)):
            return self._eval(Env.Bindings(), None)  # type: ignore
        return None


class Boolean(Base):
    """
    Boolean literal
    """

    value: bool
    """
    :type: bool

    Literal value
    """

    def __init__(self, pos: SourcePosition, literal: bool) -> None:
        super().__init__(pos)
        self.value = literal

    def __str__(self):
        return str(self.value).lower()

    def _infer_type(self, type_env: Env.Bindings[Type.Base]) -> Type.Base:
        return Type.Boolean()

    def _eval(self, env: Env.Bindings[Value.Base], stdlib: StdLib.Base) -> Value.Boolean:
        """"""
        return Value.Boolean(self.value)


class Int(Base):
    """
    Integer literal
    """

    value: int
    """
    :type: int

    Literal value
    """

    def __init__(self, pos: SourcePosition, literal: int) -> None:
        super().__init__(pos)
        self.value = literal

    def __str__(self):
        return str(self.value)

    def _infer_type(self, type_env: Env.Bindings[Type.Base]) -> Type.Base:
        return Type.Int()

    def _eval(self, env: Env.Bindings[Value.Base], stdlib: StdLib.Base) -> Value.Int:
        """"""
        return Value.Int(self.value)


# Float literal


class Float(Base):
    """
    Numeric literal
    """

    value: float
    """
    :type: float

    Literal value
    """

    def __init__(self, pos: SourcePosition, literal: float) -> None:
        super().__init__(pos)
        self.value = literal

    def __str__(self):
        return str(self.value)

    def _infer_type(self, type_env: Env.Bindings[Type.Base]) -> Type.Base:
        return Type.Float()

    def _eval(self, env: Env.Bindings[Value.Base], stdlib: StdLib.Base) -> Value.Float:
        """"""
        return Value.Float(self.value)


class Null(Base):
    """
    WDL ``None`` literal

    (called ``Null`` to avoid conflict with Python ``None``)
    """

    value: None
    """
    :type: None
    """

    def __init__(self, pos: SourcePosition) -> None:
        super().__init__(pos)
        self.value = None

    def __str__(self):
        return "None"

    def _infer_type(self, type_env: Env.Bindings[Type.Base]) -> Type.Base:
        return Type.Any(null=True)

    def _eval(self, env: Env.Bindings[Value.Base], stdlib: StdLib.Base) -> Value.Null:
        """"""
        return Value.Null()


class Placeholder(Base):
    """Holds an expression interpolated within a string or command"""

    options: Dict[str, str]
    """
    :type: Dict[str,str]

    Placeholder options (sep, true, false, default)"""

    expr: Base
    """
    :type: WDL.Expr.Base

    Expression to be evaluated and substituted
    """

    def __init__(self, pos: SourcePosition, options: Dict[str, str], expr: Base) -> None:
        super().__init__(pos)
        self.options = options
        self.expr = expr

        # preprocess expr to rewrite any Apply("_add") to Apply("_interpolation_add") for the
        # special interpolation-only behavior of + for String? operands.
        def rewrite_adds(ch: Base):
            if isinstance(ch, Apply) and ch.function_name == "_add":
                ch.function_name = "_interpolation_add"
            for ch2 in ch.children:
                assert isinstance(ch2, Base)
                rewrite_adds(ch2)

        rewrite_adds(self.expr)

    def __str__(self):
        options = []
        for option in self.options:
            options.append('{}="{}"'.format(option, self.options[option]))
        options.append(str(self.expr))
        return "~{{{}}}".format(" ".join(options))

    @property
    def children(self) -> Iterable[SourceNode]:
        yield self.expr

    def _infer_type(self, type_env: Env.Bindings[Type.Base]) -> Type.Base:
        if isinstance(self.expr.type, Type.Array):
            if "sep" not in self.options:
                raise Error.IncompatibleOperand(
                    self, "provide `sep'arator string to interpolate array items"
                )
            # if sum(1 for t in [Type.Int, Type.Float, Type.Boolean, Type.String, Type.File] if isinstance(self.expr.type.item_type, t)) == 0:  # noqa
            #    raise Error.StaticTypeMismatch(self, Type.Array(Type.Any()), self.expr.type, "cannot use array of complex types for command placeholder")  # noqa
        elif "sep" in self.options:
            raise Error.StaticTypeMismatch(
                self,
                Type.Array(Type.Any()),
                self.expr.type,
                "command placeholder has 'sep' option for non-Array expression",
            )
        if "true" in self.options or "false" in self.options:
            if not isinstance(self.expr.type, Type.Boolean):
                raise Error.StaticTypeMismatch(
                    self,
                    Type.Boolean(),
                    self.expr.type,
                    "command placeholder 'true' and 'false' options used with non-Boolean expression",
                )
            if not ("true" in self.options and "false" in self.options):
                raise Error.StaticTypeMismatch(
                    self,
                    Type.Boolean(),
                    self.expr.type,
                    "command placeholder with only one of 'true' and 'false' options",
                )
        return Type.String()

    def _eval_impl(self, env: Env.Bindings[Value.Base], stdlib: StdLib.Base) -> Value.String:
        """"""
        v = self.expr.eval(env, stdlib)
        if isinstance(v, Value.Null):
            if "default" in self.options:
                return Value.String(self.options["default"])
            return Value.String("")
        if isinstance(v, Value.String):
            return v
        if isinstance(v, Value.Array):
            return Value.String(
                self.options["sep"].join(item.coerce(Type.String()).value for item in v.value)
            )
        if isinstance(v, Value.Boolean) and v.value and "true" in self.options:
            return Value.String(self.options["true"])
        if isinstance(v, Value.Boolean) and not v.value and "false" in self.options:
            return Value.String(self.options["false"])
        return Value.String(str(v))

    def _eval(self, env: Env.Bindings[Value.Base], stdlib: StdLib.Base) -> Value.String:
        ans = self._eval_impl(env, stdlib)
        placeholder_regex: Optional[regex.Pattern] = getattr(stdlib, "_placeholder_regex", None)
        if placeholder_regex and not placeholder_regex.fullmatch(ans.value):
            raise Error.InputError(
                "Task command placeholder value forbidden by configuration [task_runtime] placeholder_regex"
            )
        return ans


class String(Base):
    """String literal, possibly interleaved with expression placeholders for interpolation"""

    parts: List[Union[str, Placeholder]]
    """
    :type: List[Union[str,WDL.Expr.Placeholder]]

    The parts list begins and ends with the original delimiters (quote marks, braces, or triple
    angle brackets). Between these is a sequence of literal strings and/or interleaved placeholder
    expressions. Escape sequences in the literals are NOT decoded until the string literal is
    evaluated (although the parser will have checked they're valid).
    """

    def __init__(
        self, pos: SourcePosition, parts: List[Union[str, Placeholder]], command: bool = False
    ) -> None:
        super().__init__(pos)
        self.parts = parts
        # self.command: legacy attribute predating the TaskCommand subclass
        assert not command or isinstance(self, TaskCommand)
        self.command = command

    def __str__(self):
        parts = []
        for part in self.parts:
            if isinstance(part, Placeholder):
                parts.append(str(part))
            else:
                parts.append(part)
        return "".join(parts)

    @property
    def children(self) -> Iterable[SourceNode]:
        for p in self.parts:
            if isinstance(p, Base):
                yield p

    def _infer_type(self, type_env: Env.Bindings[Type.Base]) -> Type.Base:
        return Type.String()

    def typecheck(self, expected: Type.Base) -> Base:
        """"""
        return super().typecheck(expected)

    def _eval(self, env: Env.Bindings[Value.Base], stdlib: StdLib.Base) -> Value.String:
        """"""
        # eval placeholders & decode escape sequences
        parts = [
            part.eval(env, stdlib).value
            if isinstance(part, Placeholder)
            else String._decode_escapes(self.pos, part)
            for part in self.parts
        ]
        # concatenate the stringified parts and trim the surrounding delimiters
        assert len(parts) >= 2 and parts[0] in ("'", '"') and parts[-1] == parts[0]
        return Value.String("".join(parts)[1:-1])

    @property
    def literal(self) -> Optional[Value.Base]:
        if next((p for p in self.parts if not isinstance(p, str)), None):
            return None
        return self._eval(Env.Bindings(), None)  # type: ignore

    _ASCII_PARTS_RE = regex.compile(r"[\x01-\x7f]+", regex.UNICODE)

    @staticmethod
    def _decode_escapes(pos: SourcePosition, s: str) -> str:
        """"""
        # Helper: decode backslash-escaped sequences in a str that may also contain unescaped,
        # non-ASCII unicode characters. codecs.decode gets tripped up by the latter, so we use
        # ASCII_PARTS_RE to apply it only to the ASCII parts of the string.
        # more info: https://stackoverflow.com/a/24519338/13393076

        # FIXME (issue #661): reject unicode-escape sequences that aren't allowed by the WDL spec
        try:
            return String._ASCII_PARTS_RE.sub(
                lambda match: codecs.decode(match.group(0), "unicode-escape"), s
            )
        except (SyntaxError, ValueError, UnicodeError):
            raise Error._BadCharacterEncoding(pos)

    @staticmethod
    def _dedent(parts: List[Any]) -> List[Any]:
        """"""
        # Helper for dedenting task commands and multi-line strings: given a list of parts (strs or
        # placeholders [anything but str]), remove common leading whitespace from non-blank lines,
        # passing placeholders through.

        # Detect common leading whitespace on the non-blank lines. For this purpose, use a
        # pseudo-string with dummy "~{}" substituted for placeholders, which is simpler than tracking
        # how newlines intersperse with the placeholders.
        common_ws = None
        pseudo = "".join((part if isinstance(part, str) else "~{}") for part in parts)
        for line in pseudo.split("\n"):
            line_ws = len(line) - len(line.lstrip())
            if line_ws < len(line):
                if common_ws is not None:
                    common_ws = min(line_ws, common_ws)
                else:
                    common_ws = line_ws
        # Remove the common leading whitespace, passing through placeholders (which don't
        # necessarily break the line they start on).
        if common_ws in (None, 0):
            return [part for part in parts]
        parts2 = []
        at_new_line = True
        for part in parts:
            if not isinstance(part, str):  # placeholder
                at_new_line = False
                parts2.append(part)
            else:
                lines2 = []
                for line in part.split("\n"):
                    if at_new_line:
                        assert not line[:common_ws].strip()
                        lines2.append(line[common_ws:])
                    else:
                        lines2.append(line)
                    at_new_line = True
                parts2.append("\n".join(lines2))
                at_new_line = parts2[-1].endswith("\n")
        return parts2


class TaskCommand(String):
    """
    Specialization of ``String`` for task commands, with slightly different evaluation rules:
    common leading whitespace is removed (dedentation) and escape sequences are passed through for
    shell interpretation. Also, for historical reasons, the ``parts`` does not include the
    beginning & ending delimiters.
    """

    def __init__(self, pos: SourcePosition, parts: List[Union[str, Placeholder]]) -> None:
        super().__init__(pos, parts, command=True)

    def _eval(
        self, env: Env.Bindings[Value.Base], stdlib: StdLib.Base, dedent: bool = True
    ) -> Value.String:
        """"""
        # in contrast to Expr.String._eval:
        # 1. dedents
        # 2. doesn't decode escape sequences
        # 3. doesn't assume the first and last parts are delimiters
        return Value.String(
            "".join(
                part.eval(env, stdlib).value if isinstance(part, Placeholder) else part
                for part in (String._dedent(self.parts) if dedent else self.parts)
            )
        )


class MultiLineString(String):
    """
    Specialization of ``String`` for WDL 1.2 multi-line string literals, with special evaluation
    rules: trim whitespace following the ``<<<`` and preceding the ``>>>`` delimiters and dedent
    the remaining non-blank lines, while allowing newlines to be escaped.
    """

    def _eval(self, env: Env.Bindings[Value.Base], stdlib: StdLib.Base) -> Value.String:
        """"""
        # From each str part, remove escaped newlines and any whitespace following them. Escaped
        # newlines are preceded by an odd number of backslashes.
        parts: List[Union[str, Placeholder]] = []
        for part in self.parts:
            if isinstance(part, str):
                part_lines = part.split("\n")
                for j in range(len(part_lines) - 1):
                    part_line = part_lines[j]
                    if (len(part_line) - len(part_line.rstrip("\\"))) % 2 == 1:
                        part_lines[j] = part_line[:-1]
                        if j < len(part_lines) - 1:
                            part_lines[j + 1] = part_lines[j + 1].lstrip(" \t")
                    else:
                        part_lines[j] += "\n"
                parts.append("".join(part_lines))
            else:
                parts.append(part)

        # Trim whitespace from the left of the first line and the right of the last line (including
        # the first/last newline, if any).
        assert parts[0] == "<<<" and parts[-1] == ">>>"
        if len(parts) > 2 and isinstance(parts[1], str):
            parts[1] = parts[1].lstrip(" \t")
            if parts[1] and parts[1][0] == "\n":
                parts[1] = parts[1][1:]
        if len(parts) > 2 and isinstance(parts[-2], str):
            parts[-2] = parts[-2].rstrip(" \t")
            if parts[-2] and parts[-2][-1] == "\n":
                parts[-2] = parts[-2][:-1]

        # dedent (without delimiters), eval placeholders, decode escape sequences, concatenate
        return Value.String(
            "".join(
                part.eval(env, stdlib).value
                if isinstance(part, Placeholder)
                else String._decode_escapes(self.pos, part)
                for part in String._dedent(parts[1:-1])
            )
        )


class Array(Base):
    """
    Array literal
    """

    items: List[Base]
    """
    :type: List[WDL.Expr.Base]

    Expression for each item in the array literal
    """

    def __init__(self, pos: SourcePosition, items: List[Base]) -> None:
        super(Array, self).__init__(pos)
        self.items = items

    def __str__(self):
        items = []
        for item in self.items:
            items.append(str(item))
        return "[{}]".format(", ".join(items))

    @property
    def children(self) -> Iterable[SourceNode]:
        for it in self.items:
            yield it

    def _infer_type(self, type_env: Env.Bindings[Type.Base]) -> Type.Base:
        if not self.items:
            return Type.Array(Type.Any())
        if any((isinstance(item.type, Type.Any) and not item.type.optional) for item in self.items):
            # an item is read_json() or something like that
            return Type.Array(Type.Any(), nonempty=True)
        if all((isinstance(item.type, Type.Any) for item in self.items)):
            # all items are literally None...
            return Type.Array(Type.Any(null=True), nonempty=True)
        item_type = Type.unify(
            [item.type for item in self.items], check_quant=self._check_quant, force_string=True
        )
        if isinstance(item_type, Type.Any) and not item_type.optional:
            raise Error.IndeterminateType(self, "unable to unify array item types")
        return Type.Array(item_type, optional=False, nonempty=True)

    def typecheck(self, expected: Type.Base) -> Base:
        """"""
        if not self.items and isinstance(expected, Type.Array):
            # the literal empty array satisfies any array type
            return self
        return super().typecheck(expected)

    def _eval(self, env: Env.Bindings[Value.Base], stdlib: StdLib.Base) -> Value.Array:
        """"""
        assert isinstance(self.type, Type.Array)
        return Value.Array(
            self.type.item_type,
            [item.eval(env, stdlib).coerce(self.type.item_type) for item in self.items],
        )

    @property
    def literal(self) -> Optional[Value.Base]:
        assert isinstance(self.type, Type.Array)
        ans = []
        for item in self.items:
            item_literal = item.literal
            if item_literal:
                ans.append(item_literal.coerce(self.type.item_type))
            else:
                return None
        return Value.Array(self.type.item_type, ans)


class Pair(Base):
    """
    Pair literal
    """

    left: Base
    """
    :type: WDL.Expr.Base

    Left-hand expression in the pair literal
    """
    right: Base
    """
    :type: WDL.Expr.Base

    Right-hand expression in the pair literal
    """

    def __init__(self, pos: SourcePosition, left: Base, right: Base) -> None:
        super().__init__(pos)
        self.left = left
        self.right = right

    def __str__(self):
        return "({}, {})".format(str(self.left), str(self.right))

    @property
    def children(self) -> Iterable[SourceNode]:
        yield self.left
        yield self.right

    def _infer_type(self, type_env: Env.Bindings[Type.Base]) -> Type.Base:
        return Type.Pair(self.left.type, self.right.type)

    def _eval(self, env: Env.Bindings[Value.Base], stdlib: StdLib.Base) -> Value.Base:
        """"""
        assert isinstance(self.type, Type.Pair)
        lv = self.left.eval(env, stdlib)
        rv = self.right.eval(env, stdlib)
        return Value.Pair(self.left.type, self.right.type, (lv, rv))

    @property
    def literal(self) -> Optional[Value.Base]:
        assert isinstance(self.type, Type.Pair)
        lv = self.left.literal
        rv = self.right.literal
        if lv and rv:
            return Value.Pair(self.left.type, self.right.type, (lv, rv))
        return None


class Map(Base):
    """
    Map literal
    """

    items: List[Tuple[Base, Base]]
    """
    :type: List[Tuple[WDL.Expr.Base,WDL.Expr.Base]]

    Expressions for the map literal keys and values
    """

    def __init__(self, pos: SourcePosition, items: List[Tuple[Base, Base]]) -> None:
        super().__init__(pos)
        self.items = items

    def __str__(self):
        items = []
        for item in self.items:
            items.append("{}: {}".format(str(item[0]), str(item[1])))
        return "{{{}}}".format(", ".join(items))

    @property
    def children(self) -> Iterable[SourceNode]:
        for k, v in self.items:
            yield k
            yield v

    def _infer_type(self, type_env: Env.Bindings[Type.Base]) -> Type.Base:
        if not self.items:
            return Type.Map((Type.Any(), Type.Any()), literal_keys=set())
        kty = Type.unify([k.type for (k, _) in self.items], check_quant=self._check_quant)
        if isinstance(kty, Type.Any):
            raise Error.IndeterminateType(self, "unable to unify map key types")
        vty = Type.unify(
            [v.type for (_, v) in self.items], check_quant=self._check_quant, force_string=True
        )
        if isinstance(vty, Type.Any):
            raise Error.IndeterminateType(self, "unable to unify map value types")
        literal_keys: Optional[Set[str]] = None
        if kty == Type.String():
            # If the keys are string constants, record them in the Type object
            # for potential later use in struct coercion. (Normally the Type
            # encodes the common type of the keys, but not the keys themselves)
            literal_keys = set()
            for k, _ in self.items:
                if (
                    literal_keys is not None
                    and isinstance(k, String)
                    and len(k.parts) == 3
                    and isinstance(k.parts[1], str)
                ):
                    literal_keys.add(k.parts[1])
                else:
                    literal_keys = None
        return Type.Map((kty, vty), literal_keys=literal_keys)

    def _eval(self, env: Env.Bindings[Value.Base], stdlib: StdLib.Base) -> Value.Base:
        """"""
        assert isinstance(self.type, Type.Map)
        keystrs = set()
        eitems = []
        for k, v in self.items:
            ek = k.eval(env, stdlib)
            sk = str(ek)
            if sk in keystrs:
                raise Error.EvalError(self, "duplicate keys in Map literal")
            eitems.append((ek, v.eval(env, stdlib)))
            keystrs.add(sk)
        return Value.Map(self.type.item_type, eitems)

    @property
    def literal(self) -> Optional[Value.Base]:
        assert isinstance(self.type, Type.Map)
        items = []
        for k, v in self.items:
            kl = k.literal
            vl = v.literal
            if kl and vl:
                items.append((kl, vl))
            else:
                return None
        return Value.Map(self.type.item_type, items)


class Struct(Base):
    """
    Struct literal
    """

    members: Dict[str, Base]
    """
    :type: Dict[str,WDL.Expr.Base]

    The struct literal is modelled initially as a bag of keys and values, which
    can be coerced to a specific struct type during typechecking.
    """

    struct_type_name: Optional[str]
    """
    :type: Optional[str]

    In WDL 2.0+ each struct literal may specify the intended struct type name.
    """

    def __init__(
        self,
        pos: SourcePosition,
        members: List[Tuple[str, Base]],
        struct_type_name: Optional[str] = None,
    ):
        super().__init__(pos)
        self.members = {}
        for k, v in members:
            if k in self.members:
                raise Error.MultipleDefinitions(self.pos, "duplicate keys " + k)
            self.members[k] = v
        self.struct_type_name = struct_type_name
        assert struct_type_name is None or isinstance(struct_type_name, str), str(struct_type_name)

    def __str__(self):
        members = []
        for member in self.members:
            members.append('"{}": {}'.format(member, str(self.members[member])))
        # Returns a Map literal instead of a struct literal as these are version dependant
        return "{{{}}}".format(", ".join(members))

    @property
    def children(self) -> Iterable[SourceNode]:
        return self.members.values()

    def _infer_type(self, type_env: Env.Bindings[Type.Base]) -> Type.Base:
        object_type = Type.Object({k: v.type for k, v in self.members.items()})
        if not self.struct_type_name:
            # pre-WDL 2.0: object literal with deferred typechecking
            return object_type

        # resolve struct type
        struct_type_members = None
        if self._struct_types and self.struct_type_name in self._struct_types:
            struct_type_members = self._struct_types[self.struct_type_name]
        if struct_type_members is None:
            raise Error.InvalidType(self, "Unknown type " + self.struct_type_name)

        struct_type = Type.StructInstance(self.struct_type_name)
        struct_type.members = struct_type_members

        # typecheck members vs struct declaration
        try:
            object_type.check(struct_type, self._check_quant)
        except TypeError as exn:
            raise Error.StaticTypeMismatch(
                self, struct_type, object_type, exn.args[0] if exn.args else ""
            )

        return struct_type

    def _eval(self, env: Env.Bindings[Value.Base], stdlib: StdLib.Base) -> Value.Base:
        assert isinstance(self.type, (Type.Object, Type.StructInstance))
        ans = {}
        for k, v in self.members.items():
            ans[k] = v.eval(env, stdlib)
            if isinstance(self.type, Type.StructInstance):
                assert self.type.members
                ans[k] = ans[k].coerce(self.type.members[k])
        return Value.Struct(self.type, ans)  # type: ignore

    @property
    def literal(self) -> Optional[Value.Base]:
        ans = {}
        for k, v in self.members.items():
            vl = v.literal
            if vl:
                ans[k] = vl
            else:
                return None
        assert isinstance(self.type, (Type.Object, Type.StructInstance))
        return Value.Struct(self.type, ans)


class IfThenElse(Base):
    """
    Ternary conditional expression
    """

    condition: Base
    """
    :type: WDL.Expr.Base

    A Boolean expression for the condition
    """

    consequent: Base
    """
    :type: WDL.Expr.Base

    Expression evaluated when the condition is true
    """

    alternative: Base
    """
    :type: WDL.Expr.Base

    Expression evaluated when the condition is false
    """

    def __init__(
        self, pos: SourcePosition, condition: Base, consequent: Base, alternative: Base
    ) -> None:
        super().__init__(pos)
        self.condition = condition
        self.consequent = consequent
        self.alternative = alternative

    def __str__(self):
        return "if {} then {} else {}".format(
            str(self.condition), str(self.consequent), str(self.alternative)
        )

    @property
    def children(self) -> Iterable[SourceNode]:
        yield self.condition
        yield self.consequent
        yield self.alternative

    def _infer_type(self, type_env: Env.Bindings[Type.Base]) -> Type.Base:
        # check for Boolean condition
        if self.condition.type != Type.Boolean():
            raise Error.StaticTypeMismatch(
                self, Type.Boolean(), self.condition.type, "in if condition"
            )
        branch_types = [self.consequent.type, self.alternative.type]
        if any((isinstance(ty, Type.Any) and not ty.optional) for ty in branch_types):
            # a branch is read_json() or something like that
            return Type.Any()
        if all(isinstance(ty, Type.Any) for ty in branch_types):
            # both branches are literally None...
            return Type.Any(null=True)
        ty = Type.unify(branch_types, check_quant=self._check_quant)
        if isinstance(ty, Type.Any):
            raise Error.StaticTypeMismatch(
                self,
                self.consequent.type,
                self.alternative.type,
                "(unable to unify consequent & alternative types)",
            )
        return ty

    def _eval(self, env: Env.Bindings[Value.Base], stdlib: StdLib.Base) -> Value.Base:
        """"""
        if self.condition.eval(env, stdlib).expect(Type.Boolean()).value:
            ans = self.consequent.eval(env, stdlib)
        else:
            ans = self.alternative.eval(env, stdlib)
        return ans


class Ident(Base):
    """
    An identifier referencing a named value or call output.

    ``Ident`` nodes are wrapped in ``Get`` nodes, as discussed below.
    """

    name: str
    """:type: str

    Name, possibly including a dot-separated namespace
    """

    referee: "Union[None, Tree.Decl, Tree.Call, Tree.Scatter, Tree.Gather]"
    """
    After typechecking within a task or workflow, stores the AST node to which the identifier
    refers: a ``WDL.Tree.Decl`` for value references; a ``WDL.Tree.Call`` for call outputs; a
    ``WDL.Tree.Scatter`` for scatter variables; or a ``WDL.Tree.Gather`` object representing a
    value or call output that resides within a scatter or conditional section.
    """

    def __init__(self, pos: SourcePosition, name: str) -> None:
        super().__init__(pos)
        assert name and not name.endswith(".") and not name.startswith(".") and ".." not in name
        self.name = name
        self.referee = None

    def __str__(self):
        return self.name

    @property
    def children(self) -> Iterable[SourceNode]:
        return []

    def _infer_type(self, type_env: Env.Bindings[Type.Base]) -> Type.Base:
        # The following Env.resolve will never fail, as Get._infer_type does
        # the heavy lifting for us.
        b = type_env.resolve_binding(self.name)
        ans = b.value
        # referee comes from the type environment's info value
        referee = b.info
        if referee:
            assert referee.__class__.__name__ in [
                "Decl",
                "Call",
                "Scatter",
                "Gather",
            ], referee.__class__.__name__
            self.referee = referee
        return ans

    def _eval(self, env: Env.Bindings[Value.Base], stdlib: StdLib.Base) -> Value.Base:
        """"""
        return env[self.name]

    @property
    def _ident(self) -> str:
        return self.name


class _LeftName(Base):
    # This AST node is a placeholder involved in disambiguating dot-separated
    # identifiers (e.g. "leftname.midname.rightname") as elaborated in the Get
    # docstring below. The parser, lacking the context to resolve this syntax,
    # creates this node simply to represent the leftmost (sometimes only) name,
    # as the innard of a Get node, potentially (not necessarily) with a
    # member name. Later during typechecking, Get._infer_type folds _LeftName
    # into an `Ident` expression; the library user should never have to work
    # with _LeftName.
    name: str

    def __init__(self, pos: SourcePosition, name: str) -> None:
        super().__init__(pos)
        assert name
        self.name = name

    def __str__(self):
        return self.name

    def _infer_type(self, type_env: Env.Bindings[Type.Base]) -> Type.Base:
        raise NotImplementedError()

    def _eval(self, env: Env.Bindings[Value.Base], stdlib: StdLib.Base) -> Value.Base:
        raise NotImplementedError()

    @property
    def _ident(self) -> str:
        return self.name


class Get(Base):
    """
    AST node representing access to a value by identifier (including namespaced
    ones), or accessing a member of a pair or struct as ``.member``.

    The entaglement of these two cases is inherent in WDL. Consider the syntax
    ``leftname.midname.rightname``. One interpretation is that ``leftname`` is
    an identifier for a struct value, and ``.midname.rightname`` represents a
    chain of struct member accesses. But another possibility is that
    ``leftname`` is a call, ``midname`` is a struct output of that call, and
    ``rightname`` is a member of that struct. These cases can't be
    distinguished by the syntax parser alone, but must be resolved during
    typechecking with reference to the calls and identifiers available in the
    environment.

    The typechecker does conveniently resolve such cases, and to minimize the
    extent to which it has to restructure the AST in doing so, all identifiers
    (with or without a namespace) are represented as a ``Get`` node wrapping an
    ``Ident`` node. The ``Get`` node may specify a member name to access, but
    may not if the identifier is to be accessed directly. On the other hand,
    the expression inside a ``Get`` node need not be a simple identifier, e.g.
    ``arr[1].memb.left`` is be represented as:
    ``Get(Get(Apply("_at", Get(Ident("arr")), 1),"memb"),"left")``
    """

    expr: Base
    """
    :type: WDL.Expr.Base

    The expression whose value is accessed
    """
    member: Optional[str]
    """
    :type: Optional[str]

    If the expression is accessing a pair/struct member, then ``expr.type`` is
    ``WDL.Type.Pair`` or ``WDL.Type.StructInstance`` and this field gives the
    desired member name (``left`` or ``right`` for pairs).

    Otherwise the expression accesses ``expr`` directly, and ``member`` is
    ``None``.
    """

    def __init__(self, pos: SourcePosition, expr: Base, member: Optional[str]) -> None:
        super().__init__(pos)
        assert isinstance(expr, Base)
        assert isinstance(member, (str, type(None)))
        self.expr = expr
        self.member = member

    def __str__(self):
        if self.member is not None:
            return "{}.{}".format(str(self.expr), self.member)
        return str(self.expr)

    @property
    def children(self) -> Iterable[SourceNode]:
        if self._type:
            # suppress children until resolution/typechecking is complete
            yield self.expr

    def _infer_type(self, type_env: Env.Bindings[Type.Base]) -> Type.Base:
        if isinstance(self.expr, _LeftName):
            # expr is a lone "name" -- try to resolve it as an identifier,
            # and if that works, transform it to Ident("name")
            if self.expr.name in type_env:
                self.expr = Ident(self.expr.pos, self.expr.name)
            elif not self.member:
                raise Error.UnknownIdentifier(self)
        # attempt to typecheck expr, disambiguating whether it's an
        # intermediate value, a resolvable identifier, or neither
        assert self._stdlib is not None
        try:
            self.expr.infer_type(type_env, self._stdlib, self._check_quant)
        except Error.UnknownIdentifier:
            # Fail...there's one case we may be able to rescue, where expr is a
            # _LeftName inside zero or more Gets representing an incomplete
            # namespaced identifier, and our member completes the path to an
            # available named value.
            if not (isinstance(self.expr, (_LeftName, Get)) and self.expr._ident and self.member):
                raise
            # attempt to resolve "expr.member" and if that works, transform
            # expr to Ident("expr.member")
            if self.expr._ident + "." + self.member not in type_env:
                message = None
                if type_env.has_namespace(self.expr._ident):
                    # specific error message when namespace exists but member doesn't
                    message = f"No {self.member} in namespace {self.expr._ident}"
                raise Error.UnknownIdentifier(self, message=message) from None
            self.expr = Ident(self.pos, self._ident)
            self.expr.infer_type(type_env, self._stdlib, self._check_quant)
            self.member = None
        # now we've typechecked expr
        ety = self.expr.type
        assert ety
        if not self.member:
            # no member to access; just propagate expr type
            assert isinstance(self.expr, Ident)
            return ety
        # now we expect expr to be a pair or struct, whose member we're
        # accessing
        if not isinstance(ety, (Type.Pair, Type.StructInstance)):
            raise Error.NoSuchMember(self, self.member)
        if self._check_quant and ety.optional:
            raise Error.StaticTypeMismatch(self.expr, ety.copy(optional=False), ety)
        if self.member in ["left", "right"]:
            if isinstance(ety, Type.Pair):
                return ety.left_type if self.member == "left" else ety.right_type
            raise Error.NoSuchMember(self, self.member)
        if isinstance(ety, Type.StructInstance):
            try:
                assert ety.members is not None
                return ety.members[self.member]
            except KeyError:
                pass
        raise Error.NoSuchMember(self, self.member)

    def _eval(self, env: Env.Bindings[Value.Base], stdlib: StdLib.Base) -> Value.Base:
        innard_value = self.expr.eval(env, stdlib)
        if not self.member:
            return innard_value
        if isinstance(innard_value, Value.Pair):
            assert self.member in ["left", "right"]
            return innard_value.value[0 if self.member == "left" else 1]
        if isinstance(innard_value, Value.Struct):
            return innard_value.value[self.member]
        raise NotImplementedError()

    @property
    def _ident(self) -> str:
        # helper for the resolution logic above -- get the partial identifier
        # recursing into nested Gets, if there's a _LeftName at the bottom.
        if isinstance(self.expr, (_LeftName, Get)) and self.expr._ident:
            return self.expr._ident + (("." + self.member) if self.member else "")
        return ""


def _add_parentheses(arguments, parent_operator):
    """
    Add parentheses around arguments if necessary.

    Adds parentheses around if-then-else clauses if on the left side of the
    parent operator (otherwise it is ambiguous whether 'if true
    then 1 else 100 + 1' should return 1 or 2).

    Adds parentheses around expression with a lower precedence than the parent operator
    """
    arguments_out = []
    precedence = {
        "_mul": 7,
        "_div": 7,
        "_rem": 7,
        "_add": 6,
        "_interpolation_add": 6,
        "_sub": 6,
        "_lt": 5,
        "_lte": 5,
        "_gt": 5,
        "_gte": 5,
        "_eqeq": 4,
        "_neq": 4,
        "_land": 3,
        "_lor": 3,
    }

    for i, argument in enumerate(arguments):
        if isinstance(argument, IfThenElse) and (parent_operator in precedence and i == 0):
            arguments_out.append("({})".format(str(argument)))
        elif isinstance(argument, Apply):
            if precedence.get(parent_operator, 100) > precedence.get(argument.function_name, 100):
                arguments_out.append("({})".format(str(argument)))
            else:
                arguments_out.append(str(argument))
        else:
            arguments_out.append(str(argument))
    return arguments_out


class Apply(Base):
    """Application of a built-in or standard library function"""

    function_name: str
    """Name of the function applied

    :type: str"""
    arguments: List[Base]
    """
    :type: List[WDL.Expr.Base]

    Expressions for each function argument
    """

    def __init__(self, pos: SourcePosition, function: str, arguments: List[Base]) -> None:
        super().__init__(pos)
        self.function_name = function
        self.arguments = arguments

    def __str__(self):
        arguments = _add_parentheses(self.arguments, self.function_name)
        infix = {
            "_mul": "*",
            "_div": "/",
            "_rem": "%",
            "_add": "+",
            "_interpolation_add": "+",
            "_sub": "-",
            "_lt": "<",
            "_lte": "<=",
            "_gt": ">",
            "_gte": ">=",
            "_eqeq": "==",
            "_neq": "!=",
            "_land": "&&",
            "_lor": "||",
        }
        if self.function_name in infix:
            return "{} {} {}".format(arguments[0], infix[self.function_name], arguments[1])
        elif self.function_name == "_at":
            return "{}[{}]".format(arguments[0], arguments[1])
        elif self.function_name == "_negate":
            return "!{}".format(arguments[0])
        else:
            return "{}({})".format(self.function_name, ",".join(arguments))

    @property
    def children(self) -> Iterable[SourceNode]:
        for arg in self.arguments:
            yield arg

    def _infer_type(self, type_env: Env.Bindings[Type.Base]) -> Type.Base:
        f = getattr(self._stdlib, self.function_name, None)
        if not f:
            raise Error.NoSuchFunction(self, self.function_name) from None
        assert isinstance(f, StdLib.Function)
        return f.infer_type(self)

    def _eval(self, env: Env.Bindings[Value.Base], stdlib: StdLib.Base) -> Value.Base:
        """"""

        f = getattr(stdlib, self.function_name, None)
        assert isinstance(f, StdLib.Function)
        return f(self, env, stdlib)
