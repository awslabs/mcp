# pylint: disable=protected-access,exec-used
import math
import os
import json
import tempfile
from typing import List, Tuple, Dict, Callable, IO, Optional
from abc import ABC, abstractmethod
from contextlib import suppress
import regex
from . import Type, Value, Expr, Env, Error
from ._util import byte_size_units, chmod_R_plus, round_half_up


class Base:
    """
    Base class for standard library implementations. An instance has an
    attribute with the name of each available function and a ``Function``
    object providing the type-checking logic and implementation.

    Subclasses may replace these objects with custom context-dependent logic,
    or add new ones. For example, ``stdout()`` is only meaningful in task
    output sections.
    """

    wdl_version: str
    _write_dir: str  # directory in which write_* functions create files

    def __init__(self, wdl_version: str, write_dir: str = ""):
        self.wdl_version = wdl_version
        self._write_dir = write_dir if write_dir else tempfile.gettempdir()

        # language built-ins
        self._at = _At()
        self._land = _And()
        self._lor = _Or()
        self._negate = StaticFunction(
            "_negate", [Type.Boolean()], Type.Boolean(), lambda x: Value.Boolean(not x.value)
        )
        self._add = _AddOperator()
        self._interpolation_add = _InterpolationAddOperator()
        self._sub = _ArithmeticOperator("-", lambda l, r: l - r)
        self._mul = _ArithmeticOperator("*", lambda l, r: l * r)
        self._div = _ArithmeticOperator("/", lambda l, r: l // r)
        self._rem = StaticFunction(
            "_rem", [Type.Int(), Type.Int()], Type.Int(), lambda l, r: Value.Int(l.value % r.value)
        )
        self._eqeq = _EqualityOperator()
        self._neq = _EqualityOperator(negate=True)
        self._lt = _ComparisonOperator("<", lambda l, r: l < r)
        self._lte = _ComparisonOperator("<=", lambda l, r: l <= r)
        self._gt = _ComparisonOperator(">", lambda l, r: l > r)
        self._gte = _ComparisonOperator(">=", lambda l, r: l >= r)

        # static stdlib functions
        def static(
            argument_types: List[Type.Base], return_type: Type.Base, name: Optional[str] = None
        ):
            """
            helper/decorator to create a static function from type signature and a lambda
            """
            return lambda F: setattr(
                self,
                name or F.__name__,
                StaticFunction(name or F.__name__, argument_types, return_type, F),
            )

        static([Type.Float()], Type.Int(), "floor")(lambda v: Value.Int(math.floor(v.value)))
        static([Type.Float()], Type.Int(), "ceil")(lambda v: Value.Int(math.ceil(v.value)))
        static([Type.Float()], Type.Int(), "round")(lambda v: Value.Int(round_half_up(v.value)))
        static([Type.Array(Type.Any())], Type.Int(), "length")(lambda v: Value.Int(len(v.value)))

        @static([Type.String(), Type.String(), Type.String()], Type.String())
        def sub(input: Value.String, pattern: Value.String, replace: Value.String) -> Value.String:
            pattern_re = regex.compile(pattern.value, flags=regex.POSIX)  # pylint: disable=E1101
            return Value.String(pattern_re.sub(replace.value, input.value))

        static([Type.String(), Type.String(optional=True)], Type.String())(basename)

        @static([Type.Any(optional=True)], Type.Boolean())
        def defined(v: Value.Base):
            return Value.Boolean(not isinstance(v, Value.Null))

        @static([Type.String(), Type.Array(Type.String())], Type.String())
        def sep(sep: Value.String, iterable: Value.Array) -> Value.String:
            return Value.String(sep.value.join(v.value for v in iterable.value))

        # write_*
        static([Type.Array(Type.String())], Type.File(), "write_lines")(
            self._write(_serialize_lines)
        )
        static([Type.Array(Type.Array(Type.String()))], Type.File(), "write_tsv")(
            self._write(_serialize_tsv)
        )
        static([Type.Map((Type.Any(), Type.Any()))], Type.File(), "write_map")(
            self._write(_serialize_map)
        )
        static([Type.Any()], Type.File(), "write_json")(
            self._write(
                lambda v, outfile: (outfile.write(json.dumps(v.json).encode("utf-8")), None)[1]
            )
        )

        # read_*
        static([Type.File()], Type.Int(), "read_int")(self._read(lambda s: Value.Int(int(s))))
        static([Type.File()], Type.Boolean(), "read_boolean")(self._read(_parse_boolean))
        static([Type.File()], Type.String(), "read_string")(
            self._read(lambda s: Value.String(s[:-1] if s.endswith("\n") else s))
        )
        static([Type.File()], Type.Float(), "read_float")(
            self._read(lambda s: Value.Float(float(s)))
        )
        static([Type.File()], Type.Map((Type.String(), Type.String())), "read_map")(
            self._read(_parse_map)
        )
        static([Type.File()], Type.Array(Type.String()), "read_lines")(self._read(_parse_lines))
        static([Type.File()], Type.Array(Type.Array(Type.String())), "read_tsv")(
            self._read(_parse_tsv)
        )
        static([Type.File()], Type.Any(), "read_json")(self._read(_parse_json))
        static([Type.File()], Type.Map((Type.String(), Type.String())), "read_object")(
            self._read(_parse_object)
        )
        static([Type.File()], Type.Array(Type.Map((Type.String(), Type.String()))), "read_objects")(
            self._read(_parse_objects)
        )

        # polymorphically typed stdlib functions which require specialized
        # infer_type logic
        self.range = _Range()
        self.prefix = _Prefix()
        self.suffix = _Suffix()
        self.size = _Size(self)
        self.select_first = _SelectFirst()
        self.select_all = _SelectAll()
        self.zip = _Zip()
        self.unzip = _Unzip()
        self.cross = _Cross()
        self.flatten = _Flatten()
        self.transpose = _Transpose()

        if self.wdl_version not in ["draft-2", "1.0"]:
            self.min = _ArithmeticOperator("min", lambda l, r: min(l, r))
            self.max = _ArithmeticOperator("max", lambda l, r: max(l, r))
            self.quote = _Quote()
            self.squote = _Quote(squote=True)
            self.keys = _Keys()
            self.as_map = _AsMap()
            self.as_pairs = _AsPairs()
            self.collect_by_key = _CollectByKey()

    def _read(self, parse: Callable[[str], Value.Base]) -> Callable[[Value.File], Value.Base]:
        "generate read_* function implementation based on parse"

        def f(file: Value.File) -> Value.Base:
            with open(self._devirtualize_filename(file.value), "r") as infile:
                return parse(infile.read())

        return f

    def _devirtualize_filename(self, filename: str) -> str:
        """
        'devirtualize' filename passed to a read_* function: return a filename that can be open()ed
        on the local host. Subclasses may further wish to forbid access to files outside of a
        designated directory or allowlist (by raising an exception)
        """
        # TODO: add directory: bool argument when we have stdlib functions that take Directory
        raise NotImplementedError()

    def _write(
        self, serialize: Callable[[Value.Base, IO[bytes]], None]
    ) -> Callable[[Value.Base], Value.File]:
        "generate write_* function implementation based on serialize"

        def _f(
            v: Value.Base,
        ) -> Value.File:
            os.makedirs(self._write_dir, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=self._write_dir, delete=False) as outfile:
                serialize(v, outfile)
                filename = outfile.name
            chmod_R_plus(filename, file_bits=0o660)
            vfn = self._virtualize_filename(filename)
            return Value.File(vfn)

        return _f

    def _virtualize_filename(self, filename: str) -> str:
        """
        from a local path in write_dir, 'virtualize' into the filename as it should present in a
        File value
        """
        # TODO: add directory: bool argument when we have stdlib functions that take Directory
        raise NotImplementedError()

    def _override_static(self, name: str, f: Callable) -> None:
        # replace the implementation lambda of a StaticFunction (keeping its
        # types etc. the same)
        sf = getattr(self, name)
        assert isinstance(sf, StaticFunction)
        setattr(sf, "F", f)


class Function(ABC):
    # Abstract interface to a standard library function implementation

    @abstractmethod
    def infer_type(self, expr: "Expr.Apply") -> Type.Base:
        # Typecheck the Apply expression (including the argument expressions);
        # raise an exception or return the function's return type, which may
        # depend on the argument types.
        pass

    @abstractmethod
    def __call__(
        self, expr: "Expr.Apply", env: Env.Bindings[Value.Base], stdlib: Base
    ) -> Value.Base:
        # Invoke the function, evaluating the arguments as needed
        pass


class EagerFunction(Function):
    # Function helper providing boilerplate for eager argument evaluation.
    # Implementation is responsible for any appropriate type coercion of
    # argument and return values.

    @abstractmethod
    def _call_eager(self, expr: "Expr.Apply", arguments: List[Value.Base]) -> Value.Base:
        pass

    def __call__(
        self, expr: "Expr.Apply", env: Env.Bindings[Value.Base], stdlib: Base
    ) -> Value.Base:
        return self._call_eager(expr, [arg.eval(env, stdlib=stdlib) for arg in expr.arguments])


class StaticFunction(EagerFunction):
    # Function helper for static argument and return types.
    # In this case the boilerplate can handle the coercions.

    name: str
    argument_types: List[Type.Base]
    return_type: Type.Base
    F: Callable

    def __init__(
        self, name: str, argument_types: List[Type.Base], return_type: Type.Base, F: Callable
    ) -> None:
        self.name = name
        self.argument_types = argument_types
        self.return_type = return_type
        self.F = F

    def infer_type(self, expr: "Expr.Apply") -> Type.Base:
        min_args = len(self.argument_types)
        for ty in reversed(self.argument_types):
            if ty.optional:
                min_args = min_args - 1
            else:
                break
        if len(expr.arguments) > len(self.argument_types) or len(expr.arguments) < min_args:
            raise Error.WrongArity(expr, len(self.argument_types))
        for i in range(len(expr.arguments)):
            try:
                expr.arguments[i].typecheck(self.argument_types[i])
            except Error.StaticTypeMismatch:
                raise Error.StaticTypeMismatch(
                    expr.arguments[i],
                    self.argument_types[i],
                    expr.arguments[i].type,
                    "for {} argument #{}".format(self.name, i + 1),
                ) from None
        return self.return_type

    def _call_eager(self, expr: "Expr.Apply", arguments: List[Value.Base]) -> Value.Base:
        argument_values = [arg.coerce(ty) for arg, ty in zip(arguments, self.argument_types)]
        try:
            ans: Value.Base = self.F(*argument_values)
        except Exception as exn:
            msg = "function evaluation failed"
            if str(exn):
                msg += ", " + str(exn)
            raise Error.EvalError(expr, msg) from exn
        return ans.coerce(self.return_type)


def _notimpl(*args, **kwargs) -> None:
    exec("raise NotImplementedError('function not available in this context')")


class TaskOutputs(Base):
    """
    Defines type signatures for functions only available in task output sections.
    (Implementations left to by overridden by the task runtime)
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, argument_types, return_type, F in [
            ("stdout", [], Type.File(), _notimpl),
            ("stderr", [], Type.File(), _notimpl),
            ("glob", [Type.String()], Type.Array(Type.File()), _notimpl),
        ]:
            setattr(self, name, StaticFunction(name, argument_types, return_type, F))


def basename(*args) -> Value.String:
    assert len(args) in (1, 2)
    assert isinstance(args[0], Value.String)
    path = args[0].value
    if len(args) > 1:
        assert isinstance(args[1], Value.String)
        suffix = args[1].value
        if path.endswith(suffix):
            path = path[: -len(suffix)]
    return Value.String(os.path.basename(path))


def _parse_lines(s: str) -> Value.Array:
    ans: List[Value.Base] = []
    if s:
        ans = [Value.String(line) for line in (s[:-1] if s.endswith("\n") else s).split("\n")]
    return Value.Array(Type.String(), ans)


def _parse_boolean(s: str) -> Value.Boolean:
    s = s.strip().lower()
    if s == "true":
        return Value.Boolean(True)
    if s == "false":
        return Value.Boolean(False)
    raise Error.InputError('read_boolean(): file content is not "true" or "false"')


def _parse_tsv(s: str) -> Value.Array:
    ans: List[Value.Base] = [
        Value.Array(
            Type.Array(Type.String()), [Value.String(field) for field in line.value.split("\t")]
        )
        for line in _parse_lines(s).value
        if line
    ]
    return Value.Array(Type.Array(Type.String()), ans)


def _parse_objects(s: str) -> Value.Array:
    strmat = _parse_tsv(s)
    if len(strmat.value) < 1 or len(strmat.value[0].value) < 1:
        return Value.Array(Type.Map((Type.String(), Type.String())), [])
    keys = strmat.value[0].value
    literal_keys = set(key.value for key in strmat.value[0].value if key.value)
    if len(literal_keys) < len(keys):
        raise Error.InputError("read_objects(): file has empty or duplicate column names")
    maps: List[Value.Base] = []
    for row in strmat.value[1:]:
        if len(row.value) != len(keys):
            raise Error.InputError("read_objects(): file's tab-separated lines are ragged")
        maps.append(Value.Map((Type.String(), Type.String()), list(zip(keys, row.value))))
    return Value.Array(Type.Map((Type.String(), Type.String())), maps)


def _parse_object(s: str) -> Value.Map:
    maps = _parse_objects(s)
    if len(maps.value) != 1:
        raise Error.InputError("read_object(): file must have exactly one object")
    map0 = maps.value[0]
    assert isinstance(map0, Value.Map)
    return map0


def _parse_map(s: str) -> Value.Map:
    keys = set()
    ans = []
    for line in _parse_tsv(s).value:
        assert isinstance(line, Value.Array)
        if len(line.value) != 2:
            raise Error.InputError("read_map(): each line must have two fields")
        if line.value[0].value in keys:
            raise Error.InputError("read_map(): duplicate key")
        keys.add(line.value[0].value)
        ans.append((line.value[0], line.value[1]))
    return Value.Map((Type.String(), Type.String()), ans)


def _parse_json(s: str) -> Value.Base:
    return Value.from_json(Type.Any(), json.loads(s))


def _serialize_lines(array: Value.Base, outfile: IO[bytes]) -> None:
    assert isinstance(array, Value.Array)
    for item in array.value:
        outfile.write(item.coerce(Type.String()).value.encode("utf-8"))
        outfile.write(b"\n")


def _serialize_tsv(v: Value.Base, outfile: IO[bytes]) -> None:
    assert isinstance(v, Value.Array)
    return _serialize_lines(
        Value.Array(
            Type.String(),
            [
                Value.String("\t".join([part.coerce(Type.String()).value for part in parts.value]))
                for parts in v.value
            ],
        ),
        outfile,
    )


def _serialize_map(map: Value.Base, outfile: IO[bytes]) -> None:
    assert isinstance(map, Value.Map)
    lines: List[Value.Base] = []
    for k, v in map.value:
        ks = k.coerce(Type.String()).value
        vs = v.coerce(Type.String()).value
        if "\n" in ks or "\t" in ks or "\n" in vs or "\t" in vs:
            raise ValueError(
                "write_map(): keys & values must not contain tab or newline characters"
            )
        lines.append(Value.String(ks + "\t" + vs))
    _serialize_lines(Value.Array(Type.String(), lines), outfile)


class _At(EagerFunction):
    # Special function for array access arr[index], returning the element type
    #                   or map access map[key], returning the value type

    def infer_type(self, expr: "Expr.Apply") -> Type.Base:
        assert len(expr.arguments) == 2
        lhs = expr.arguments[0]
        rhs = expr.arguments[1]
        if isinstance(lhs.type, Type.Array):
            if isinstance(lhs, Expr.Array) and not lhs.items:
                # the user wrote: [][idx]
                raise Error.OutOfBounds(expr, "Cannot acess empty array")
            try:
                rhs.typecheck(Type.Int())
            except Error.StaticTypeMismatch:
                raise Error.StaticTypeMismatch(rhs, Type.Int(), rhs.type, "Array index") from None
            return lhs.type.item_type
        if isinstance(lhs.type, Type.Map):
            if lhs.type.item_type is None:
                raise Error.OutOfBounds(expr, "Cannot access empty map")
            try:
                rhs.typecheck(lhs.type.item_type[0])
            except Error.StaticTypeMismatch:
                raise Error.StaticTypeMismatch(
                    rhs, lhs.type.item_type[0], rhs.type, "Map key"
                ) from None
            return lhs.type.item_type[1]
        if isinstance(lhs.type, Type.Any) and not lhs.type.optional:
            # e.g. read_json(): assume lhs is Array[Any] or Struct
            return Type.Any()
        raise Error.NotAnArray(lhs)

    def _call_eager(self, expr: "Expr.Apply", arguments: List[Value.Base]) -> Value.Base:
        assert len(expr.arguments) == 2 and len(arguments) == 2
        lhs = arguments[0]
        rhs = arguments[1]
        if isinstance(lhs, Value.Map):
            mty = expr.arguments[0].type
            mkey = rhs
            if isinstance(mty, Type.Map):
                mkey = mkey.coerce(mty.item_type[0])
            ans = None
            for k, v in lhs.value:
                if mkey == k:
                    ans = v
            if ans is None:
                raise Error.OutOfBounds(expr.arguments[1], "Map key not found")
            return ans
        elif isinstance(lhs, Value.Struct):
            # allow member access from read_json() (issue #320)
            skey = None
            if rhs.type.coerces(Type.String()):
                with suppress(Error.RuntimeError):
                    skey = rhs.coerce(Type.String()).value
            if skey is None or skey not in lhs.value:
                raise Error.OutOfBounds(expr.arguments[1], "struct member not found")
            return lhs.value[skey]
        else:
            lhs = lhs.coerce(Type.Array(Type.Any()))
            rhs = rhs.coerce(Type.Int())
            if (
                not isinstance(lhs, Value.Array)
                or not isinstance(rhs, Value.Int)
                or rhs.value < 0
                or rhs.value >= len(lhs.value)
            ):
                raise Error.OutOfBounds(expr.arguments[1], "Array index out of bounds")
            return lhs.value[rhs.value]


class _And(Function):
    # logical && with short-circuit evaluation
    def infer_type(self, expr: "Expr.Apply") -> Type.Base:
        assert len(expr.arguments) == 2
        for arg in expr.arguments:
            if not isinstance(arg.type, Type.Boolean):
                raise Error.IncompatibleOperand(arg, "non-Boolean operand to &&")
            if expr._check_quant and arg.type.optional:
                raise Error.IncompatibleOperand(arg, "optional Boolean? operand to &&")
        return Type.Boolean()

    def __call__(
        self, expr: "Expr.Apply", env: Env.Bindings[Value.Base], stdlib: Base
    ) -> Value.Base:
        lhs = expr.arguments[0].eval(env, stdlib=stdlib).expect(Type.Boolean()).value
        if not lhs:
            return Value.Boolean(False)
        return expr.arguments[1].eval(env, stdlib=stdlib).expect(Type.Boolean())


class _Or(Function):
    # logical || with short-circuit evaluation
    def infer_type(self, expr: "Expr.Apply") -> Type.Base:
        assert len(expr.arguments) == 2
        for arg in expr.arguments:
            if not isinstance(arg.type, Type.Boolean):
                raise Error.IncompatibleOperand(arg, "non-Boolean operand to ||")
            if expr._check_quant and arg.type.optional:
                raise Error.IncompatibleOperand(arg, "optional Boolean? operand to ||")
        return Type.Boolean()

    def __call__(
        self, expr: "Expr.Apply", env: Env.Bindings[Value.Base], stdlib: Base
    ) -> Value.Base:
        lhs = expr.arguments[0].eval(env, stdlib=stdlib).expect(Type.Boolean()).value
        if lhs:
            return Value.Boolean(True)
        return expr.arguments[1].eval(env, stdlib=stdlib).expect(Type.Boolean())


class _ArithmeticOperator(EagerFunction):
    # arithmetic infix operators
    # operands may be Int or Float; return Float iff either operand is Float

    name: str
    op: Callable

    def __init__(self, name: str, op: Callable) -> None:
        self.name = name
        self.op = op

    def infer_type(self, expr: "Expr.Apply") -> Type.Base:
        assert len(expr.arguments) == 2
        rt: Type.Base = Type.Int()
        if isinstance(expr.arguments[0].type, Type.Float) or isinstance(
            expr.arguments[1].type, Type.Float
        ):
            rt = Type.Float()
        try:
            expr.arguments[0].typecheck(rt)
            expr.arguments[1].typecheck(rt)
        except Error.StaticTypeMismatch:
            raise Error.IncompatibleOperand(
                expr, "Non-numeric operand to " + self.name + " operator"
            ) from None
        return rt

    def _call_eager(self, expr: "Expr.Apply", arguments: List[Value.Base]) -> Value.Base:
        ans_type = self.infer_type(expr)
        ans = self.op(arguments[0].coerce(ans_type).value, arguments[1].coerce(ans_type).value)
        if ans_type == Type.Int():
            assert isinstance(ans, int)
            return Value.Int(ans)
        assert isinstance(ans, float)
        return Value.Float(ans)


class _AddOperator(_ArithmeticOperator):
    # + operator can also serve as concatenation for String.
    def __init__(self) -> None:
        super().__init__("+", lambda l, r: l + r)

    def infer_type(self, expr: "Expr.Apply") -> Type.Base:
        assert len(expr.arguments) == 2
        t2 = None
        if isinstance(expr.arguments[0].type, Type.String):
            t2 = expr.arguments[1].type
        elif isinstance(expr.arguments[1].type, Type.String):
            t2 = expr.arguments[0].type
        if t2 is None:
            # neither operand is a string; defer to _ArithmeticOperator
            return super().infer_type(expr)
        if not t2.coerces(Type.String(), check_quant=expr._check_quant):
            raise Error.IncompatibleOperand(
                expr,
                "Cannot add/concatenate {} and {}".format(
                    str(expr.arguments[0].type), str(expr.arguments[1].type)
                ),
            )
        return Type.String()

    def _call_eager(self, expr: "Expr.Apply", arguments: List[Value.Base]) -> Value.Base:
        ans_type = self.infer_type(expr)
        if not isinstance(ans_type, Type.String):
            return super()._call_eager(expr, arguments)
        ans = self.op(
            str(arguments[0].coerce(Type.String()).value),
            str(arguments[1].coerce(Type.String()).value),
        )
        assert isinstance(ans, str)
        return Value.String(ans)


class _InterpolationAddOperator(_AddOperator):
    # + operator within an interpolation; accepts String? operands, evaluating to None if either
    # operand is None.

    def infer_type(self, expr: "Expr.Apply") -> Type.Base:
        either_string = sum(1 for arg in expr.arguments if isinstance(arg.type, Type.String)) > 0
        either_optional = sum(1 for arg in expr.arguments if arg.type.optional) > 0
        both_stringifiable = (
            sum(1 for arg in expr.arguments if arg.type.coerces(Type.String(optional=True))) > 1
        )
        return (
            Type.String(optional=True)
            if either_string and either_optional and both_stringifiable
            else super().infer_type(expr)
        )

    def _call_eager(self, expr: "Expr.Apply", arguments: List[Value.Base]) -> Value.Base:
        if sum(1 for arg in arguments if isinstance(arg, Value.Null)):
            return Value.Null()
        return super()._call_eager(expr, arguments)


class _EqualityOperator(EagerFunction):
    # Test for [in]equality of two values of suitable types

    negate: bool
    name: str

    def __init__(self, negate: bool = False) -> None:
        self.negate = negate
        self.name = "!=" if negate else "=="

    def infer_type(self, expr: "Expr.Apply") -> Type.Base:
        assert len(expr.arguments) == 2
        if not expr.arguments[0].type.equatable(expr.arguments[1].type):
            raise Error.IncompatibleOperand(
                expr,
                "Cannot test equality of {} and {}".format(
                    str(expr.arguments[0].type), str(expr.arguments[1].type)
                ),
            )
        return Type.Boolean()

    def _call_eager(self, expr: "Expr.Apply", arguments: List[Value.Base]) -> Value.Base:
        assert len(arguments) == 2
        ans = arguments[0] == arguments[1]  # Value.Base.__eq__()
        return Value.Boolean(self.negate ^ ans)


class _ComparisonOperator(EagerFunction):
    # < > <= >= operators

    name: str
    op: Callable

    def __init__(self, name: str, op: Callable) -> None:
        self.name = name
        self.op = op

    def infer_type(self, expr: "Expr.Apply") -> Type.Base:
        assert len(expr.arguments) == 2
        if not expr.arguments[0].type.comparable(
            expr.arguments[1].type, check_quant=expr._check_quant
        ):
            raise Error.IncompatibleOperand(
                expr,
                "Cannot compare {} and {}".format(
                    str(expr.arguments[0].type), str(expr.arguments[1].type)
                ),
            )
        return Type.Boolean()

    def _call_eager(self, expr: "Expr.Apply", arguments: List[Value.Base]) -> Value.Base:
        assert len(arguments) == 2
        return Value.Boolean(self.op(arguments[0].value, arguments[1].value))


class _Size(EagerFunction):
    # size(): first argument can be File? or Array[File?]
    stdlib: Base

    def __init__(self, stdlib: Base) -> None:
        self.stdlib = stdlib

    def infer_type(self, expr: "Expr.Apply") -> Type.Base:
        if not expr.arguments:
            raise Error.WrongArity(expr, 1)
        arg0ty = expr.arguments[0].type
        if not arg0ty.coerces(Type.File(optional=True)):
            if isinstance(arg0ty, Type.Array):
                if arg0ty.optional or not arg0ty.item_type.coerces(Type.File(optional=True)):
                    raise Error.StaticTypeMismatch(
                        expr.arguments[0], Type.Array(Type.File(optional=True)), arg0ty
                    )
            else:
                raise Error.StaticTypeMismatch(expr.arguments[0], Type.File(optional=True), arg0ty)
        if len(expr.arguments) == 2:
            if expr.arguments[1].type != Type.String():
                raise Error.StaticTypeMismatch(
                    expr.arguments[1], Type.String(), expr.arguments[1].type
                )
        elif len(expr.arguments) > 2:
            raise Error.WrongArity(expr, 2)
        return Type.Float()

    def _call_eager(self, expr: "Expr.Apply", arguments: List[Value.Base]) -> Value.Base:
        # this default implementation attempts os.path.getsize() on the argument(s)
        files = arguments[0].coerce(Type.Array(Type.File(optional=True)))
        unit = arguments[1].coerce(Type.String()) if len(arguments) > 1 else None

        ans = []
        for file in files.value:
            if isinstance(file, Value.File):
                ans.append(os.path.getsize(self.stdlib._devirtualize_filename(file.value)))
            elif isinstance(file, Value.Null):
                ans.append(0)
            else:
                assert False
        fans = float(sum(ans))

        if unit:
            try:
                fans /= float(byte_size_units[unit.value])
            except KeyError:
                raise Error.EvalError(expr, "size(): invalid unit " + unit.value)
        return Value.Float(fans)


class _SelectFirst(EagerFunction):
    def infer_type(self, expr: "Expr.Apply") -> Type.Base:
        if len(expr.arguments) != 1:
            raise Error.WrongArity(expr, 1)
        arg0ty = expr.arguments[0].type
        if not isinstance(arg0ty, Type.Array) or (
            expr.arguments[0]._check_quant and arg0ty.optional
        ):
            raise Error.StaticTypeMismatch(expr.arguments[0], Type.Array(Type.Any()), arg0ty)
        if isinstance(arg0ty.item_type, Type.Any):
            raise Error.IndeterminateType(expr.arguments[0], "can't infer item type of empty array")
        return arg0ty.item_type.copy(optional=False)

    def _call_eager(self, expr: "Expr.Apply", arguments: List[Value.Base]) -> Value.Base:
        arr = arguments[0].coerce(Type.Array(Type.Any()))
        assert isinstance(arr, Value.Array)
        for arg in arr.value:
            if not isinstance(arg, Value.Null):
                return arg
        raise Error.EvalError(
            expr,
            "select_first() given empty or all-null array; prevent this or append a default value",
        )


class _SelectAll(EagerFunction):
    def infer_type(self, expr: "Expr.Apply") -> Type.Base:
        if len(expr.arguments) != 1:
            raise Error.WrongArity(expr, 1)
        arg0ty = expr.arguments[0].type
        if not isinstance(arg0ty, Type.Array) or (
            expr.arguments[0]._check_quant and arg0ty.optional
        ):
            raise Error.StaticTypeMismatch(expr.arguments[0], Type.Array(Type.Any()), arg0ty)
        if isinstance(arg0ty.item_type, Type.Any):
            raise Error.IndeterminateType(expr.arguments[0], "can't infer item type of empty array")
        return Type.Array(arg0ty.item_type.copy(optional=False))

    def _call_eager(self, expr: "Expr.Apply", arguments: List[Value.Base]) -> Value.Base:
        arr = arguments[0].coerce(Type.Array(Type.Any()))
        assert isinstance(arr, Value.Array)
        arrty = arr.type
        assert isinstance(arrty, Type.Array)
        return Value.Array(
            arrty.item_type.copy(optional=False),
            [arg for arg in arr.value if not isinstance(arg, Value.Null)],
        )


class _ZipOrCross(EagerFunction):
    # 'a array -> 'b array -> ('a,'b) array
    def infer_type(self, expr: "Expr.Apply") -> Type.Base:
        if len(expr.arguments) != 2:
            raise Error.WrongArity(expr, 2)
        arg0ty: Type.Base = expr.arguments[0].type
        if not isinstance(arg0ty, Type.Array) or (expr._check_quant and arg0ty.optional):
            raise Error.StaticTypeMismatch(expr.arguments[0], Type.Array(Type.Any()), arg0ty)
        if isinstance(arg0ty.item_type, Type.Any):
            raise Error.IndeterminateType(expr.arguments[0], "can't infer item type of empty array")
        arg1ty: Type.Base = expr.arguments[1].type
        if not isinstance(arg1ty, Type.Array) or (expr._check_quant and arg1ty.optional):
            raise Error.StaticTypeMismatch(expr.arguments[1], Type.Array(Type.Any()), arg1ty)
        if isinstance(arg1ty.item_type, Type.Any):
            raise Error.IndeterminateType(expr.arguments[1], "can't infer item type of empty array")
        return Type.Array(
            Type.Pair(arg0ty.item_type, arg1ty.item_type),
            nonempty=(arg0ty.nonempty or arg1ty.nonempty),
        )

    def _coerce_args(
        self, expr: "Expr.Apply", arguments: List[Value.Base]
    ) -> Tuple[Type.Array, Value.Array, Value.Array]:
        ty = self.infer_type(expr)
        assert isinstance(ty, Type.Array) and isinstance(ty.item_type, Type.Pair)
        lhs = arguments[0].coerce(Type.Array(ty.item_type.left_type))
        rhs = arguments[1].coerce(Type.Array(ty.item_type.right_type))
        assert isinstance(lhs, Value.Array) and isinstance(rhs, Value.Array)
        return (ty, lhs, rhs)


class _Zip(_ZipOrCross):
    def _call_eager(self, expr: "Expr.Apply", arguments: List[Value.Base]) -> Value.Array:
        ty, lhs, rhs = self._coerce_args(expr, arguments)
        assert isinstance(ty, Type.Array) and isinstance(ty.item_type, Type.Pair)
        if len(lhs.value) != len(rhs.value):
            raise Error.EvalError(expr, "zip(): input arrays must have equal length")
        return Value.Array(
            ty.item_type,
            [
                Value.Pair(
                    ty.item_type.left_type, ty.item_type.right_type, (lhs.value[i], rhs.value[i])
                )
                for i in range(len(lhs.value))
            ],
        )


class _Cross(_ZipOrCross):
    def _call_eager(self, expr: "Expr.Apply", arguments: List[Value.Base]) -> Value.Array:
        ty, lhs, rhs = self._coerce_args(expr, arguments)
        assert isinstance(ty, Type.Array) and isinstance(ty.item_type, Type.Pair)
        return Value.Array(
            ty.item_type,
            [
                Value.Pair(ty.item_type.left_type, ty.item_type.right_type, (lhs_item, rhs_item))
                for lhs_item in lhs.value
                for rhs_item in rhs.value
            ],
        )


class _Unzip(EagerFunction):
    # Array[Pair[X,Y]] -> Pair[Array[X],Array[Y]]
    def infer_type(self, expr: "Expr.Apply") -> Type.Base:
        if len(expr.arguments) != 1:
            raise Error.WrongArity(expr, 1)
        arg0ty: Type.Base = expr.arguments[0].type
        if (
            not isinstance(arg0ty, Type.Array)
            or (expr._check_quant and arg0ty.optional)
            or not isinstance(arg0ty.item_type, Type.Pair)
            or (expr._check_quant and arg0ty.item_type.optional)
        ):
            raise Error.StaticTypeMismatch(
                expr.arguments[0], Type.Array(Type.Pair(Type.Any(), Type.Any())), arg0ty
            )
        return Type.Pair(
            Type.Array(arg0ty.item_type.left_type, nonempty=arg0ty.nonempty),
            Type.Array(arg0ty.item_type.right_type, nonempty=arg0ty.nonempty),
        )

    def _call_eager(self, expr: "Expr.Apply", arguments: List[Value.Base]) -> Value.Pair:
        pty = self.infer_type(expr)
        assert isinstance(pty, Type.Pair)
        lty = pty.left_type
        assert isinstance(lty, Type.Array)
        rty = pty.right_type
        assert isinstance(rty, Type.Array)
        arr = arguments[0]
        assert isinstance(arr, Value.Array)
        return Value.Pair(
            lty,
            rty,
            (
                Value.Array(lty.item_type, [p.value[0] for p in arr.value]),
                Value.Array(rty.item_type, [p.value[1] for p in arr.value]),
            ),
        )


class _Flatten(EagerFunction):
    # t array array -> t array
    # TODO: if any of the input arrays are statically nonempty then so is output
    def infer_type(self, expr: "Expr.Apply") -> Type.Base:
        if len(expr.arguments) != 1:
            raise Error.WrongArity(expr, 1)
        expr.arguments[0].typecheck(Type.Array(Type.Any()))
        # TODO: won't handle implicit coercion from T to Array[T]
        arg0ty = expr.arguments[0].type
        assert isinstance(arg0ty, Type.Array)
        if isinstance(arg0ty.item_type, Type.Any):
            return Type.Array(Type.Any())
        if not isinstance(arg0ty.item_type, Type.Array) or (
            expr._check_quant and arg0ty.item_type.optional
        ):
            raise Error.StaticTypeMismatch(
                expr.arguments[0], Type.Array(Type.Array(Type.Any())), arg0ty
            )
        return Type.Array(arg0ty.item_type.item_type)

    def _call_eager(self, expr: "Expr.Apply", arguments: List[Value.Base]) -> Value.Base:
        ty = self.infer_type(expr)
        assert isinstance(ty, Type.Array)
        ans = []
        for row in arguments[0].coerce(Type.Array(ty)).value:
            ans.extend(row.value)
        return Value.Array(ty.item_type, ans)


class _Transpose(EagerFunction):
    # t array array -> t array array
    # TODO: if any of the input arrays are statically nonempty then so is output
    def infer_type(self, expr: "Expr.Apply") -> Type.Base:
        if len(expr.arguments) != 1:
            raise Error.WrongArity(expr, 1)
        expr.arguments[0].typecheck(Type.Array(Type.Any()))
        # TODO: won't handle implicit coercion from T to Array[T]
        arg0ty = expr.arguments[0].type
        assert isinstance(arg0ty, Type.Array)
        if isinstance(arg0ty.item_type, Type.Any):
            return Type.Array(Type.Any())
        if not isinstance(arg0ty.item_type, Type.Array) or (
            expr._check_quant and arg0ty.item_type.optional
        ):
            raise Error.StaticTypeMismatch(
                expr.arguments[0], Type.Array(Type.Array(Type.Any())), arg0ty
            )
        return Type.Array(Type.Array(arg0ty.item_type.item_type))

    def _call_eager(self, expr: "Expr.Apply", arguments: List[Value.Base]) -> Value.Base:
        ty = self.infer_type(expr)
        assert isinstance(ty, Type.Array) and isinstance(ty.item_type, Type.Array)
        mat = arguments[0].coerce(ty)
        assert isinstance(mat, Value.Array)
        n = None
        ans: List[Value.Base] = []
        for row in mat.value:
            assert isinstance(row, Value.Array)
            if n is None:
                n = len(row.value)
                ans = [Value.Array(ty.item_type.item_type, []) for _ in row.value]
            if len(row.value) != n:
                raise Error.EvalError(expr, "transpose(): ragged input matrix")
            for i in range(len(row.value)):
                ans[i].value.append(row.value[i])
        return Value.Array(ty.item_type, ans)


class _Range(EagerFunction):
    # int -> int array
    # with special case: if the argument is a positive integer literal or
    # length(a_nonempty_array), then we can say the returned array is nonempty.

    def infer_type(self, expr: "Expr.Apply") -> Type.Base:
        if len(expr.arguments) != 1:
            raise Error.WrongArity(expr, 1)
        expr.arguments[0].typecheck(Type.Int())
        nonempty = False
        arg0 = expr.arguments[0]
        if isinstance(arg0, Expr.Int) and arg0.value > 0:
            nonempty = True
        if isinstance(arg0, Expr.Apply) and arg0.function_name == "length":
            arg00ty = arg0.arguments[0].type
            if isinstance(arg00ty, Type.Array) and arg00ty.nonempty:
                nonempty = True
        return Type.Array(Type.Int(), nonempty=nonempty)

    def _call_eager(self, expr: "Expr.Apply", arguments: List[Value.Base]) -> Value.Base:
        arg0 = arguments[0].coerce(Type.Int())
        assert isinstance(arg0, Value.Int)
        if arg0.value < 0:
            raise Error.EvalError(expr, "range() got negative argument")
        return Value.Array(Type.Int(), [Value.Int(x) for x in range(arg0.value)])


class _Prefix(EagerFunction):
    # string -> t array -> string array
    # if input array is nonempty then so is output

    def infer_type(self, expr: "Expr.Apply") -> Type.Base:
        if len(expr.arguments) != 2:
            raise Error.WrongArity(expr, 2)
        expr.arguments[0].typecheck(Type.String())
        expr.arguments[1].typecheck(Type.Array(Type.String()))
        arg1ty = expr.arguments[1].type
        return Type.Array(
            Type.String(), nonempty=(isinstance(arg1ty, Type.Array) and arg1ty.nonempty)
        )

    def _call_eager(self, expr: "Expr.Apply", arguments: List[Value.Base]) -> Value.Base:
        pfx = arguments[0].coerce(Type.String()).value
        return Value.Array(
            Type.String(),
            [Value.String(pfx + s.coerce(Type.String()).value) for s in arguments[1].value],
        )


class _Suffix(EagerFunction):
    # string -> t array -> string array
    # if input array is nonempty then so is output
    # Append a suffix to every element within the array

    def infer_type(self, expr: "Expr.Apply") -> Type.Base:
        if len(expr.arguments) != 2:
            raise Error.WrongArity(expr, 2)
        expr.arguments[0].typecheck(Type.String())
        expr.arguments[1].typecheck(Type.Array(Type.String()))
        arg1ty = expr.arguments[1].type
        return Type.Array(
            Type.String(), nonempty=(isinstance(arg1ty, Type.Array) and arg1ty.nonempty)
        )

    def _call_eager(self, expr: "Expr.Apply", arguments: List[Value.Base]) -> Value.Base:
        sfx = arguments[0].coerce(Type.String()).value
        return Value.Array(
            Type.String(),
            [Value.String(s.coerce(Type.String()).value + sfx) for s in arguments[1].value],
        )


class _Quote(EagerFunction):
    # t array -> string array
    # if input array is nonempty then so is output
    # Append a suffix to every element within the array

    def __init__(self, squote: bool = False) -> None:
        if squote:
            self.quote = "'"
        else:
            self.quote = '"'

    def infer_type(self, expr: "Expr.Apply") -> Type.Base:
        if len(expr.arguments) != 1:
            raise Error.WrongArity(expr, 1)
        expr.arguments[0].typecheck(Type.Array(Type.String()))
        arg0ty = expr.arguments[0].type
        nonempty = isinstance(arg0ty, Type.Array) and arg0ty.nonempty
        return Type.Array(Type.String(), nonempty=nonempty)

    def _call_eager(self, expr: "Expr.Apply", arguments: List[Value.Base]) -> Value.Base:
        return Value.Array(
            Type.String(),
            [
                Value.String("{0}{1}{0}".format(self.quote, s.coerce(Type.String()).value))
                for s in arguments[0].value
            ],
        )


class _Keys(EagerFunction):
    def infer_type(self, expr: "Expr.Apply") -> Type.Base:
        if len(expr.arguments) != 1:
            raise Error.WrongArity(expr, 1)
        arg0ty = expr.arguments[0].type
        if not isinstance(arg0ty, Type.Map) or (expr._check_quant and arg0ty.optional):
            raise Error.StaticTypeMismatch(
                expr.arguments[0], Type.Map((Type.Any(), Type.Any())), arg0ty
            )
        return Type.Array(arg0ty.item_type[0].copy())

    def _call_eager(self, expr: "Expr.Apply", arguments: List[Value.Base]) -> Value.Base:
        assert isinstance(arguments[0], Value.Map)
        mapty = arguments[0].type
        assert isinstance(mapty, Type.Map)
        return Value.Array(
            mapty.item_type[0], [p[0].coerce(mapty.item_type[0]) for p in arguments[0].value], expr
        )


class _AsPairs(EagerFunction):
    def infer_type(self, expr: "Expr.Apply") -> Type.Base:
        if len(expr.arguments) != 1:
            raise Error.WrongArity(expr, 1)
        arg0ty = expr.arguments[0].type
        if not isinstance(arg0ty, Type.Map) or (expr._check_quant and arg0ty.optional):
            raise Error.StaticTypeMismatch(
                expr.arguments[0], Type.Map((Type.Any(), Type.Any())), arg0ty
            )
        return Type.Array(Type.Pair(arg0ty.item_type[0], arg0ty.item_type[1]))

    def _call_eager(self, expr: "Expr.Apply", arguments: List[Value.Base]) -> Value.Base:
        assert isinstance(arguments[0], Value.Map)
        mapty = arguments[0].type
        assert isinstance(mapty, Type.Map)
        pairty = Type.Pair(mapty.item_type[0], mapty.item_type[1])
        return Value.Array(
            pairty,
            [Value.Pair(mapty.item_type[0], mapty.item_type[1], p) for p in arguments[0].value],
            expr,
        ).coerce(self.infer_type(expr))


class _CollectByKey(EagerFunction):
    def infer_type(self, expr: "Expr.Apply") -> Type.Base:
        if len(expr.arguments) != 1:
            raise Error.WrongArity(expr, 1)
        arg0ty = expr.arguments[0].type
        if (
            not isinstance(arg0ty, Type.Array)
            or not isinstance(arg0ty.item_type, Type.Pair)
            or (expr._check_quant and (arg0ty.optional or arg0ty.item_type.optional))
        ):
            raise Error.StaticTypeMismatch(
                expr.arguments[0], Type.Array(Type.Pair(Type.Any(), Type.Any())), arg0ty
            )
        return Type.Map((arg0ty.item_type.left_type, Type.Array(arg0ty.item_type.right_type)))

    def _call_eager(self, expr: "Expr.Apply", arguments: List[Value.Base]) -> Value.Base:
        assert isinstance(arguments[0], Value.Array)
        arg0ty = arguments[0].type
        assert isinstance(arg0ty, Type.Array)
        pairty = arg0ty.item_type
        assert isinstance(pairty, Type.Pair)

        items: Dict[str, Tuple[Value.Base, List[Value.Base]]] = {}
        for p in arguments[0].value:
            assert isinstance(p, Value.Pair)
            ek = p.value[0].coerce(pairty.left_type)
            ev = p.value[1].coerce(pairty.right_type)
            sk = str(ek)
            if sk in items:
                items[sk][1].append(ev)
            else:
                items[sk] = (ek, [ev])

        return Value.Map(
            (pairty.left_type, Type.Array(pairty.right_type)),
            [(ek, Value.Array(pairty.right_type, evs)) for ek, evs in items.values()],
            expr,
        )


class _AsMap(_CollectByKey):
    # as_map(): run collect_by_key() and pluck the values out of the length-1 arrays

    def infer_type(self, expr: "Expr.Apply") -> Type.Base:
        collectedty = super().infer_type(expr)
        assert isinstance(collectedty, Type.Map)
        arrayty = collectedty.item_type[1]
        assert isinstance(arrayty, Type.Array)
        return Type.Map((collectedty.item_type[0], arrayty.item_type))

    def _call_eager(self, expr: "Expr.Apply", arguments: List[Value.Base]) -> Value.Base:
        collected = super()._call_eager(expr, arguments)
        assert isinstance(collected, Value.Map)
        collectedty = collected.type
        assert isinstance(collectedty, Type.Map)
        arrayty = collectedty.item_type[1]
        assert isinstance(arrayty, Type.Array)
        singletons = []
        for k, vs in collected.value:
            assert isinstance(vs, Value.Array)
            assert len(vs.value) > 0
            if len(vs.value) > 1:
                raise Error.EvalError(expr, "duplicate keys supplied to as_map(): " + str(k))
            singletons.append((k, vs.value[0]))
        return Value.Map((collectedty.item_type[0], arrayty.item_type), singletons, expr)
