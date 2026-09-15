from typing import (
    List,
    Optional,
    Union,
    Iterable,
    Generator,
    Callable,
    Any,
    Dict,
    NamedTuple,
)
from functools import total_ordering
from contextlib import contextmanager

from . import Type


class SourcePosition(
    NamedTuple(
        "SourcePosition",
        [
            ("uri", str),
            ("abspath", str),
            ("line", int),
            ("column", int),
            ("end_line", int),
            ("end_column", int),
        ],
    )
):
    """
    Source position attached to AST nodes and exceptions; NamedTuple of ``uri`` the filename/URI
    passed to :func:`WDL.load` or a WDL import statement, which may be relative; ``abspath`` the
    absolute filename/URI; and one-based int positions ``line`` ``end_line`` ``column``
    ``end_column``
    """


class SyntaxError(Exception):
    """Failure to lex/parse a WDL document"""

    pos: SourcePosition
    wdl_version: str
    declared_wdl_version: Optional[str]

    def __init__(
        self, pos: SourcePosition, msg: str, wdl_version: str, declared_wdl_version: Optional[str]
    ) -> None:
        super().__init__(msg)
        self.pos = pos
        self.wdl_version = wdl_version
        self.declared_wdl_version = declared_wdl_version


class _BadCharacterEncoding(Exception):
    """"""

    # Invalid escape sequence in a string literal; this is used internally, eventually resurfaced
    # as a SyntaxError.
    pos: SourcePosition

    def __init__(self, pos: SourcePosition):
        self.pos = pos


class ImportError(Exception):
    """Failure to open/retrieve an imported WDL document

    The ``__cause__`` attribute may hold the inner error object."""

    pos: SourcePosition

    def __init__(self, pos: SourcePosition, import_uri: str, message: Optional[str] = None) -> None:
        msg = "Failed to import " + import_uri
        if message:
            msg = msg + ", " + message
        super().__init__(msg)
        self.pos = pos


@total_ordering
class SourceNode:
    """Base class for an AST node, recording the source position"""

    pos: SourcePosition
    """
    :type: SourcePosition

    Source position for this AST node
    """

    parent: Optional["SourceNode"] = None
    """
    :type: Optional[SourceNode]

    Parent node in the AST, if any
    """

    def __init__(self, pos: SourcePosition) -> None:
        self.pos = pos

    def __lt__(self, rhs: "SourceNode") -> bool:
        return isinstance(rhs, SourceNode) and (
            self.pos.abspath,
            self.pos.line,
            self.pos.column,
            self.pos.end_line,
            self.pos.end_column,
        ) < (
            rhs.pos.abspath,
            rhs.pos.line,
            rhs.pos.column,
            rhs.pos.end_line,
            rhs.pos.end_column,
        )

    def __eq__(self, rhs: Any) -> bool:
        return isinstance(rhs, SourceNode) and self.pos == rhs.pos

    @property
    def children(self) -> Iterable["SourceNode"]:
        """
        :type: Iterable[SourceNode]

        Yield all child nodes
        """
        return []


class ValidationError(Exception):
    """
    Base class for a WDL validation error (when the document loads and parses, but fails typechecking or other static
    validity tests)
    """

    pos: SourcePosition
    """:type: SourcePosition"""

    node: Optional[SourceNode] = None
    """:type: Optional[SourceNode]"""

    source_text: Optional[str] = None
    """:type: Optional[str]

    The complete source text of the WDL document (if available)"""

    declared_wdl_version: Optional[str] = None

    def __init__(self, node: Union[SourceNode, SourcePosition], message: str) -> None:
        if isinstance(node, SourceNode):
            self.node = node
            self.pos = node.pos
        else:
            self.pos = node
        super().__init__(message)


class InvalidType(ValidationError):
    pass


class IndeterminateType(ValidationError):
    pass


class NoSuchTask(ValidationError):
    def __init__(self, node: Union[SourceNode, SourcePosition], name: str) -> None:
        super().__init__(node, "No such task/workflow: " + name)


class NoSuchCall(ValidationError):
    def __init__(self, node: Union[SourceNode, SourcePosition], name: str) -> None:
        super().__init__(node, "No such call in this workflow: " + name)


class NoSuchFunction(ValidationError):
    def __init__(self, node: Union[SourceNode, SourcePosition], name: str) -> None:
        super().__init__(node, "No such function: " + name)


class WrongArity(ValidationError):
    def __init__(self, node: Union[SourceNode, SourcePosition], expected: int) -> None:
        # avoiding circular dep:
        # assert isinstance(node, WDL.Expr.Apply)
        msg = "{} expects {} argument(s)".format(getattr(node, "function_name"), expected)
        super().__init__(node, msg)


class NotAnArray(ValidationError):
    def __init__(self, node: Union[SourceNode, SourcePosition]) -> None:
        super().__init__(node, "Not an array")


class NoSuchMember(ValidationError):
    def __init__(self, node: Union[SourceNode, SourcePosition], member: str) -> None:
        super().__init__(node, "No such member '{}'".format(member))


class StaticTypeMismatch(ValidationError):
    message: str

    def __init__(
        self, node: SourceNode, expected: Type.Base, actual: Type.Base, message: str = ""
    ) -> None:
        self.expected = expected
        self.actual = actual
        self.message = message
        super().__init__(node, message)

    def __str__(self) -> str:
        msg = f"Expected {self.expected} instead of {self.actual}"
        if self.message:
            msg += "; " + self.message
        elif isinstance(self.expected, Type.Int) and isinstance(self.actual, Type.Float):
            msg += "; perhaps try floor() or round()"
        elif str(self.actual).replace("?", "") == str(self.expected):
            msg += (
                " -- to coerce T? X into T, try select_first([X,defaultValue])"
                " or select_first([X]) (which might fail at runtime);"
                " to coerce Array[T?] X into Array[T], try select_all(X)"
            )
        return msg


class IncompatibleOperand(ValidationError):
    def __init__(self, node: SourceNode, message: str) -> None:
        super().__init__(node, message)


class UnknownIdentifier(ValidationError):
    def __init__(self, node: SourceNode, message: Optional[str] = None) -> None:
        # avoiding circular dep:
        # assert isinstance(node, WDL.Expr.Ident)
        if not message:
            message = "Unknown identifier " + str(node)
        super().__init__(node, message)


class NoSuchInput(ValidationError):
    def __init__(self, node: SourceNode, name: str) -> None:
        super().__init__(node, "No such input " + name)


class UncallableWorkflow(ValidationError):
    def __init__(self, node: SourceNode, name: str) -> None:
        super().__init__(
            node,
            (
                "Cannot call subworkflow {} because its own calls have missing required inputs, "
                "and/or it lacks an output section"
            ).format(name),
        )


class MultipleDefinitions(ValidationError):
    pass


class StrayInputDeclaration(ValidationError):
    pass


class CircularDependencies(ValidationError):
    def __init__(self, node: SourceNode) -> None:
        msg = "circular dependencies"
        nm = next(
            (getattr(node, attr) for attr in ("name", "workflow_node_id") if hasattr(node, attr)),
            None,
        )
        if nm:
            nm += " involving " + nm
        super().__init__(node, msg)


class MultipleValidationErrors(Exception):
    """Propagates several validation/typechecking errors"""

    exceptions: List[ValidationError]
    """:type: List[ValidationError]"""

    source_text: Optional[str] = None

    declared_wdl_version: Optional[str] = None

    def __init__(
        self, *exceptions: List[Union[ValidationError, "MultipleValidationErrors"]]
    ) -> None:
        super().__init__()
        self.exceptions = []
        for exn in exceptions:
            if isinstance(exn, ValidationError):
                self.exceptions.append(exn)
            elif isinstance(exn, MultipleValidationErrors):
                self.exceptions.extend(exn.exceptions)
            else:
                assert False
        assert self.exceptions
        self.exceptions = sorted(self.exceptions, key=lambda exn: getattr(exn, "pos"))


class _MultiContext:
    """"""

    _exceptions: List[Union[ValidationError, MultipleValidationErrors]]

    def __init__(self) -> None:
        self._exceptions = []

    def try1(self, fn: Callable[[], Any]) -> Optional[Any]:
        try:
            return fn()
        except (ValidationError, MultipleValidationErrors) as exn:
            self._exceptions.append(exn)
            return None

    def append(self, exn: Union[ValidationError, MultipleValidationErrors]) -> None:
        self._exceptions.append(exn)

    def maybe_raise(self) -> None:
        if len(self._exceptions) == 1:
            raise self._exceptions[0]
        if self._exceptions:
            raise MultipleValidationErrors(*self._exceptions) from self._exceptions[0]  # type: ignore


@contextmanager
def multi_context() -> Generator[_MultiContext, None, None]:
    """"""
    # Context manager to assist with catching and propagating multiple
    # validation/typechecking errors
    #
    # with WDL.Error.multi_context() as errors:
    #
    #    result = errors.try1(lambda: perform_validation())
    #    # Returns the result of invoking the lambda. If the lambda invocation
    #    # raises WDL.Error.ValidationError or
    #    # WDL.Error.MultipleValidationErrors, records the error and returns
    #    # None. (Other exceptions would halt execution and propagate
    #    # normally.)
    #
    #    errors.append(WDL.Error.NullValue())
    #    # errors.append() manually records one error.
    #
    # When the context closes, any exceptions recorded with errors.try1() or
    # errors.append() are raised at that point. Note that any exception raised
    # outside of errors.try1() will exit the context immediately and discard
    # any previously-recorded errors.
    #
    # Lastly, you can call errors.maybe_raise() to immediately propagate any
    # exceptions recorded so far, or if none, proceed with the remainder of
    # the context body.
    ctx = _MultiContext()
    yield ctx
    ctx.maybe_raise()


class RuntimeError(Exception):
    more_info: Dict[str, Any]
    """
    Backend-specific information about an error (for example, pointer to a centralized log system)
    """

    def __init__(self, *args, more_info: Optional[Dict[str, Any]] = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.more_info = more_info if more_info else {}


class EvalError(RuntimeError):
    """Error evaluating a WDL expression or declaration"""

    pos: SourcePosition
    """:type: SourcePosition"""

    node: Optional[SourceNode] = None
    """:type: Optional[SourceNode]"""

    def __init__(self, node: Union[SourceNode, SourcePosition], message: str) -> None:
        if isinstance(node, SourceNode):
            self.node = node
            self.pos = node.pos
        else:
            self.pos = node
        super().__init__(message)


class OutOfBounds(EvalError):
    pass


class EmptyArray(EvalError):
    def __init__(self, node: SourceNode) -> None:
        super().__init__(node, "Empty array for Array+ input/declaration")


class NullValue(EvalError):
    def __init__(self, node: Union[SourceNode, SourcePosition]) -> None:
        super().__init__(node, "Null value")


class InputError(RuntimeError):
    """Error reading an input value/file"""

    pass
