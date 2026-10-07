"""
Abstract syntax tree (AST) for WDL documents, containing tasks and workflows, which contain
declarations, calls, and scatter & if sections. The AST is typically constructed by
:func:`~WDL.load`.

The ``WDL.Tree.*`` classes are also exported by the base ``WDL`` module, i.e. ``WDL.Tree.Document``
can be abbreviated ``WDL.Document``.

.. inheritance-diagram:: WDL.Tree
"""

import os
import errno
import itertools
import asyncio
import hashlib
import base64
from typing import (
    Any,
    List,
    Optional,
    Dict,
    Tuple,
    Union,
    Iterable,
    Callable,
    Generator,
    Set,
    NamedTuple,
    Awaitable,
)
from abc import ABC, abstractmethod
from .Error import SourcePosition, SourceNode
from . import Type, Expr, Env, Error, StdLib, _parser, _util


class StructTypeDef(SourceNode):
    """WDL struct type definition"""

    name: str
    """
    :type: str

    Name of the struct type (in the current document)
    """

    members: Dict[str, Type.Base]
    """
    :type: Dict[str, WDL.Type.Base]

    Member names and types
    """

    imported: "Optional[Tuple[Document,StructTypeDef]]"
    """
    :type: Optional[Tuple[Document,StructTypeDef]]

    If this struct is imported from another document, references that document and its definition
    there. The referenced definition might itself be imported from yet another document.
    """

    def __init__(
        self,
        pos: SourcePosition,
        name: str,
        members: Dict[str, Type.Base],
        imported: "Optional[Tuple[Document,StructTypeDef]]" = None,
    ) -> None:
        super().__init__(pos)
        self.name = name
        self.members = members
        self.imported = imported

    @property
    def type_id(self) -> str:
        """
        :type: str

        A string canonically describing the member names and their types, excluding the struct type name; useful to
        unify aliased struct types.
        """
        return Type._struct_type_id(self.members)


class WorkflowNode(SourceNode, ABC):
    """
    Base class for workflow "nodes" including declarations, calls, and scatter/if sections and
    their bodies.

    Each node has a human-readable ID string which is unique within the workflow. It also exposes
    the set of workflow node IDs upon which it depends. Abstractly, workflow execution can proceed
    by "visiting" each node once all of its dependencies have been visited, performing some
    action(s) appropriate to the specific node type (such as evaluating a WDL expression and
    binding a name in the environment, or executing a task and binding its outputs).
    """

    workflow_node_id: str
    """
    :type: str

    Human-readable node ID unique within the current workflow
    """

    scatter_depth: int
    """
    :type: int

    How many nested scatter sections the node lies within. This information is useful for runtime
    dependency analysis in workflows with scatters. When scatter sections are nested within
    conditional sections or vice versa, this counts the scatters only.
    """

    _memo_workflow_node_dependencies: Optional[Set[str]] = None

    def __init__(self, workflow_node_id: str, pos: SourcePosition):
        super().__init__(pos)
        self.workflow_node_id = workflow_node_id
        self.scatter_depth = 0

    @property
    def workflow_node_dependencies(self) -> Set[str]:
        """
        :type: Set[str]

        Set of workflow node IDs on which this node depends. Available once workflow has been
        typechecked.
        """
        # in particular, requires all ident expressions have their referees resolved
        # memoize
        if self._memo_workflow_node_dependencies is None:
            self._memo_workflow_node_dependencies = set(self._workflow_node_dependencies())
        return self._memo_workflow_node_dependencies

    @abstractmethod
    def _workflow_node_dependencies(self) -> Iterable[str]:
        # to be supplied by subclasses
        raise NotImplementedError()

    @abstractmethod
    def add_to_type_env(
        self, struct_types: Env.Bindings[Dict[str, Type.Base]], type_env: Env.Bindings[Type.Base]
    ) -> Env.Bindings[Type.Base]:
        # typechecking helper -- add this node to the type environment; for sections, this includes
        # everything in the section body as visible outside of the section.
        raise NotImplementedError()

    def _increment_scatter_depth(self) -> None:
        for ch in self.children:
            if isinstance(ch, WorkflowNode):
                ch._increment_scatter_depth()
        self.scatter_depth += 1


class Decl(WorkflowNode):
    """
    A value declaration within a task or workflow.

    Within a task, the declarations can be viewed as "workflow nodes" insofar as they must be
    evaluated in an order consistent with their dependency structure, and ensured acyclic. The
    "workflow node IDs" of a task's declarations are unique within the task only, and unrelated to
    the top-level workflow, if any, in the WDL document.
    """

    type: Type.Base
    ":type: WDL.Type.Base"
    name: str
    """Declared value name

    :type: str"""
    expr: Optional[Expr.Base]
    """:type: Optional[WDL.Expr.Base]

    Bound expression, if any"""
    decor: Dict[str, Any]  # EXPERIMENTAL
    ""

    def __init__(
        self,
        pos: SourcePosition,
        type: Type.Base,
        name: str,
        expr: Optional[Expr.Base] = None,
        id_prefix="decl",
    ) -> None:
        super().__init__(id_prefix + "-" + name, pos)
        self.type = type
        self.name = name
        self.expr = expr
        self.decor = {}

    def __str__(self) -> str:
        if self.expr is None:
            return "{} {}".format(str(self.type), self.name)
        return "{} {} = {}".format(str(self.type), self.name, str(self.expr))

    __repr__ = __str__

    @property
    def children(self) -> Iterable[SourceNode]:
        """"""
        if self.expr:
            yield self.expr

    def add_to_type_env(
        self,
        struct_types: Env.Bindings[Dict[str, Type.Base]],
        type_env: Env.Bindings[Type.Base],
        collision_ok: bool = False,
    ) -> Env.Bindings[Type.Base]:
        # Add an appropriate binding in the type env, after checking for name
        # collision.
        if not collision_ok:
            if self.name in type_env:
                raise Error.MultipleDefinitions(self, "Multiple declarations of " + self.name)
            if type_env.has_namespace(self.name):
                raise Error.MultipleDefinitions(self, "Value/call name collision on " + self.name)
        _resolve_struct_types(self.pos, self.type, struct_types)
        if isinstance(self.type, Type.StructInstance):
            return _add_struct_instance_to_type_env(self.name, self.type, type_env, ctx=self)
        return type_env.bind(self.name, self.type, self)

    def typecheck(
        self,
        type_env: Env.Bindings[Type.Base],
        stdlib: StdLib.Base,
        struct_types: Env.Bindings[Dict[str, Type.Base]],
        check_quant: bool = True,
    ) -> None:
        # Infer the expression's type and ensure it checks against the declared
        # type. One time use!
        if self.expr:
            self.expr.infer_type(
                type_env, stdlib, check_quant=check_quant, struct_types=struct_types
            ).typecheck(self.type)

    def _workflow_node_dependencies(self) -> Iterable[str]:
        yield from _expr_workflow_node_dependencies(self.expr)


class Task(SourceNode):
    """
    WDL Task
    """

    name: str
    """:type: str"""
    inputs: Optional[List[Decl]]
    """:type: Optional[List[WDL.Tree.Decl]]

    Declarations in the ``input{}`` task section, if it's present"""
    postinputs: List[Decl]
    """:type: List[WDL.Tree.Decl]

    Declarations outside of the ``input{}`` task section"""
    command: Expr.String
    ":type: WDL.Expr.String"
    outputs: List[Decl]
    """:type: List[WDL.Tree.Decl]

    Output declarations"""
    parameter_meta: Dict[str, Any]
    """:type: Dict[str,Any]

    ``parameter_meta{}`` section as a JSON-like dict"""
    runtime: Dict[str, Expr.Base]
    """:type: Dict[str,WDL.Expr.Base]

    ``runtime{}`` section, with keys and corresponding expressions to be evaluated"""
    meta: Dict[str, Any]
    """:type: Dict[str,Any]

    ``meta{}`` section as a JSON-like dict"""

    effective_wdl_version: str
    """:type: str

    Effective WDL version of the containing document
    """

    def __init__(
        self,
        pos: SourcePosition,
        name: str,
        inputs: Optional[List[Decl]],
        postinputs: List[Decl],
        command: Expr.String,
        outputs: List[Decl],
        parameter_meta: Dict[str, Any],
        runtime: Dict[str, Expr.Base],
        meta: Dict[str, Any],
    ) -> None:
        super().__init__(pos)
        self.name = name
        self.inputs = inputs
        self.postinputs = postinputs
        self.command = command
        self.outputs = outputs
        self.parameter_meta = parameter_meta
        self.runtime = runtime
        self.meta = meta
        self.effective_wdl_version = "1.0"  # overridden by Document.__init__
        # TODO: enforce validity constraints on parameter_meta and runtime
        # TODO: if the input section exists, then all postinputs decls must be
        #       bound

    @property
    def available_inputs(self) -> Env.Bindings[Decl]:
        """:type: WDL.Env.Bindings[WDL.Tree.Decl]

        Yields the task's input declarations. This is all declarations in the
        task's ``input{}`` section, if it's present. Otherwise, it's all
        declarations in the task, excluding outputs. (This dichotomy bridges
        pre-1.0 and 1.0+ WDL versions.)

        Each input is at the top level of the Env, with no namespace.
        """
        ans: Env.Bindings[Decl] = Env.Bindings()

        if self.effective_wdl_version not in ("draft-2", "1.0"):
            # synthetic placeholder to expose runtime overrides
            ans = ans.bind("_runtime", Decl(self.pos, Type.Any(), "_runtime"))

        for decl in reversed(self.inputs if self.inputs is not None else self.postinputs):
            ans = ans.bind(decl.name, decl)
        return ans

    @property
    def required_inputs(self) -> Env.Bindings[Decl]:
        """:type: WDL.Env.Bindings[WDL.Tree.Decl]

        Yields the input declarations which are required to call the task
        (available inputs that are unbound and non-optional).

        Each input is at the top level of the Env, with no namespace.
        """
        ans: Env.Bindings[Decl] = Env.Bindings()
        for b in reversed(list(self.available_inputs)):
            assert isinstance(b, Env.Binding)
            d: Decl = b.value
            if d.expr is None and d.type.optional is False and not d.name.startswith("_"):
                ans = Env.Bindings(b, ans)
        return ans

    @property
    def effective_outputs(self) -> Env.Bindings[Type.Base]:
        """:type: WDL.Env.Bindings[Type.Base]

        Yields each task output with its type, at the top level of the Env with
        no namespace. (Present for isomorphism with
        ``Workflow.effective_outputs``)
        """
        ans: Env.Bindings[Type.Base] = Env.Bindings()
        for decl in reversed(self.outputs):
            ans = ans.bind(decl.name, decl.type, decl)
        return ans

    @property
    def children(self) -> Iterable[SourceNode]:
        """"""
        for d in self.inputs or []:
            yield d
        for d in self.postinputs:
            yield d
        yield self.command
        for d in self.outputs:
            yield d
        for _, ex in self.runtime.items():
            yield ex

    def typecheck(
        self,
        struct_types: Optional[Env.Bindings[Dict[str, Type.Base]]] = None,
        check_quant: bool = True,
    ) -> None:
        struct_types = struct_types or Env.Bindings()
        # warm-up check: if input{} section exists then all postinput decls
        # must be bound
        if self.inputs is not None:
            for decl in self.postinputs:
                if not decl.type.optional and not decl.expr:
                    raise Error.StrayInputDeclaration(
                        self,
                        "unbound non-optional declaration {} {} outside task input{} section".format(
                            str(decl.type), decl.name, "{}"
                        ),
                    )
        # First collect a type environment for all the input & postinput
        # declarations, so that we're prepared for possible forward-references
        # in their right-hand side expressions.
        type_env: Env.Bindings[Type.Base] = Env.Bindings()
        for decl in (self.inputs or []) + self.postinputs:
            type_env = decl.add_to_type_env(struct_types, type_env)

        with Error.multi_context() as errors:
            stdlib = StdLib.Base(self.effective_wdl_version)
            # Pass through input & postinput declarations again, typecheck their
            # right-hand side expressions against the type environment.
            for decl in (self.inputs or []) + self.postinputs:
                errors.try1(
                    lambda: decl.typecheck(
                        type_env, stdlib, check_quant=check_quant, struct_types=struct_types
                    )
                )
            # Typecheck the command (string)
            errors.try1(
                lambda: self.command.infer_type(
                    type_env, stdlib, check_quant=check_quant, struct_types=struct_types
                ).typecheck(Type.String())
            )
            for b in self.available_inputs:
                errors.try1(lambda: _check_serializable_map_keys(b.value.type, b.name, b.value))
            # Typecheck runtime expressions
            for _, runtime_expr in self.runtime.items():
                errors.try1(
                    (
                        lambda runtime_expr: lambda: runtime_expr.infer_type(
                            type_env, stdlib, check_quant=check_quant, struct_types=struct_types
                        )
                    )(runtime_expr)
                )  # .typecheck()
                # (At this stage we don't care about the overall expression type, just that it
                #  typechecks internally.)
            # Add output declarations to type environment
            for decl in self.outputs:
                type_env2 = errors.try1(
                    (lambda decl: lambda: decl.add_to_type_env(struct_types, type_env))(decl)
                )
                if type_env2:
                    type_env = type_env2
            errors.maybe_raise()
            # Typecheck the output expressions
            stdlib = StdLib.TaskOutputs(self.effective_wdl_version)
            for decl in self.outputs:
                errors.try1(
                    lambda: decl.typecheck(type_env, stdlib, struct_types, check_quant=check_quant)
                )
                errors.try1(lambda: _check_serializable_map_keys(decl.type, decl.name, decl))

        # check for cyclic dependencies among decls
        _detect_cycles(
            _decl_dependency_matrix([ch for ch in self.children if isinstance(ch, Decl)])  # type: ignore
        )

    _digest: str = ""

    @property
    def digest(self) -> str:
        """
        Content digest of the task, for use e.g. as a cache key. The digest is an opaque string of
        a few dozen alphanumeric characters, sensitive to the task's source code (with best effort
        to exclude comments and whitespace).
        """
        if self._digest:
            return self._digest
        sha256 = hashlib.sha256(self._digest_source().encode("utf-8")).digest()
        self._digest = base64.b32encode(sha256[:20]).decode().lower()
        return self._digest

    def _digest_source(self) -> str:
        doc = getattr(self, "parent", None)
        assert isinstance(doc, Document)

        # For now we just excerpt the task's source code, minus comments and blank lines, plus
        # annotations for the WDL version and struct types.
        source_lines = []
        if doc.wdl_version:
            source_lines.append("version " + doc.wdl_version)

        # Insert comments describing struct types used in the task.
        structs = _describe_struct_types(self)
        for struct_name in sorted(structs.keys()):
            source_lines.append(f"# {struct_name} :: {structs[struct_name]}")

        # excerpt task{} from document
        # Possible future improvements:
        # excise the meta & parameter_meta sections
        # normalize order of declarations
        # normalize whitespace within lines (not leading/trailing)
        source_lines += _source_excerpt(doc, self.pos, [self.command.pos])
        return "\n".join(source_lines).strip()


class Call(WorkflowNode):
    """A call (within a workflow) to a task or sub-workflow"""

    callee_id: List[str]
    """
    :type: List[str]

    The called task; either one string naming a task in the current document, or an import
    namespace and task name.
    """
    name: str
    """:type: string

    Call name, defaults to task/workflow name"""
    after: List[str]
    """:type: string

    Call names on which this call depends (even if none of their outputs are used in this call's
    inputs)
    """
    _after_node_ids: Set[str]

    inputs: Dict[str, Expr.Base]
    """
    :type: Dict[str,WDL.Expr.Base]

    Call inputs provided"""

    callee: Optional[Union[Task, "Workflow"]]
    """
    :type: Union[WDL.Tree.Task, WDL.Tree.Workflow]

    Refers to the ``Task`` or imported ``Workflow`` object to be called (after AST typechecking)"""

    def __init__(
        self,
        pos: SourcePosition,
        callee_id: List[str],
        alias: Optional[str],
        inputs: Dict[str, Expr.Base],
        after: Optional[List[str]] = None,
    ) -> None:
        assert callee_id
        self.callee_id = callee_id
        self.name = alias if alias is not None else self.callee_id[-1]
        super().__init__("call-" + self.name, pos)
        self.inputs = inputs
        self.callee = None
        self.after = after if after is not None else list()
        self._after_node_ids = set()

    @property
    def children(self) -> Iterable[SourceNode]:
        """"""
        for _, ex in self.inputs.items():
            yield ex

    def resolve(self, doc: "Document") -> None:
        # Set self.callee to the Task/Workflow being called. Use exactly once
        # prior to add_to_type_env() or typecheck_input()
        if self.callee:
            return
        callee_doc = None
        if len(self.callee_id) == 1:
            callee_doc = doc
        elif len(self.callee_id) == 2:
            for imp in doc.imports:
                if imp.namespace == self.callee_id[0]:
                    callee_doc = imp.doc
        if callee_doc:
            assert isinstance(callee_doc, Document)
            wf = callee_doc.workflow
            if isinstance(wf, Workflow) and wf.name == self.callee_id[-1]:
                if callee_doc is doc:
                    raise Error.CircularDependencies(self)
                if not wf.complete_calls or (wf.outputs is None and wf.effective_outputs):
                    raise Error.UncallableWorkflow(self, ".".join(self.callee_id))
                self.callee = wf
            else:
                for task in callee_doc.tasks:
                    if task.name == self.callee_id[-1]:
                        self.callee = task
        if self.callee is None:
            raise Error.NoSuchTask(self, ".".join(self.callee_id))
        assert doc.workflow
        if self.name == doc.workflow.name:
            raise Error.MultipleDefinitions(
                self, "Call's name may not equal the containing workflow's"
            )
        assert isinstance(self.callee, (Task, Workflow))

    def add_to_type_env(
        self, struct_types: Env.Bindings[Dict[str, Type.Base]], type_env: Env.Bindings[Type.Base]
    ) -> Env.Bindings[Type.Base]:
        # Add the call's outputs to the type environment under the appropriate
        # namespace, after checking for namespace collisions.
        assert self.callee
        if self.name in type_env:
            raise Error.MultipleDefinitions(self, "Value/call name collision on " + self.name)
        if type_env.has_namespace(self.name):
            raise Error.MultipleDefinitions(
                self,
                "Workflow has multiple calls named {}; give calls distinct names using `call {} as NAME ...`".format(
                    self.name, self.callee.name
                ),
            )
        # add a dummy _present binding to ensure the namespace exists even if callee has no outputs
        return Env.merge(
            self.effective_outputs, type_env.bind(self.name + "." + "_present", Type.Any(), self)
        )

    def typecheck_input(
        self,
        struct_types: Env.Bindings[Dict[str, Type.Base]],
        type_env: Env.Bindings[Type.Base],
        stdlib: StdLib.Base,
        check_quant: bool,
    ) -> bool:
        # Check the input expressions against the callee's inputs. One-time use.
        # Returns True if the call supplies all required inputs, False otherwise.
        assert self.callee

        # first resolve each self.after to a node ID (possibly a Gather node)
        for call_after in self.after:
            try:
                self._after_node_ids.add(
                    type_env.resolve_binding(call_after + "._present").info.workflow_node_id
                )
            except KeyError:
                raise Error.NoSuchCall(self, call_after)

        # Make a set of the input names which are required for this call
        required_inputs = set(decl.name for decl in self.callee.required_inputs)

        # typecheck call inputs against task/workflow input declarations
        with Error.multi_context() as errors:
            for name, expr in self.inputs.items():
                try:
                    decl = self.callee.available_inputs[name]
                    # treat input with default as optional, with or without the ? type quantifier
                    decltype = decl.type.copy(optional=True) if decl.expr else decl.type
                    errors.try1(
                        (
                            lambda expr, decltype: lambda: expr.infer_type(
                                type_env, stdlib, check_quant=check_quant, struct_types=struct_types
                            ).typecheck(decltype)
                        )(expr, decltype)
                    )
                except KeyError:
                    errors.append(Error.NoSuchInput(expr, name))
                if name in required_inputs:
                    required_inputs.remove(name)
        assert (not required_inputs) == (not list(self.required_inputs))
        return not required_inputs

    @property
    def available_inputs(self) -> Env.Bindings[Decl]:
        """:type: WDL.Env.Bindings[WDL.Tree.Decl]

        Yields the task/workflow inputs which are *not* supplied in the call
        ``inputs:``, and thus may be supplied at workflow launch; in namespaces
        according to the call names.
        """
        assert self.callee

        supplied_inputs = set(self.inputs.keys())
        return self.callee.available_inputs.filter(
            lambda b: b.name not in supplied_inputs
        ).wrap_namespace(self.name)

    @property
    def required_inputs(self) -> Env.Bindings[Decl]:
        """:type: WDL.Env.Bindings[WDL.Tree.Decl]

        Yields the required task/workflow inputs which are *not* supplied in
        the call ``inputs:`` (incomplete calls), and thus must be supplied at
        workflow launch; in namespaces according to the call name.
        """
        assert self.callee

        supplied_inputs = set(self.inputs.keys())
        return self.callee.required_inputs.filter(
            lambda b: b.name not in supplied_inputs
        ).wrap_namespace(self.name)

    @property
    def effective_outputs(self) -> Env.Bindings[Type.Base]:
        """:type: WDL.Env.Bindings[WDL.Tree.Decl]

        Yields the effective outputs of the callee Task or Workflow, in a
        namespace according to the call name.
        """
        ans: Env.Bindings[Type.Base] = Env.Bindings()
        assert self.callee
        for outp in reversed(list(self.callee.effective_outputs)):
            ans = ans.bind(self.name + "." + outp.name, outp.value, self)
        return ans

    def _workflow_node_dependencies(self) -> Iterable[str]:
        assert (not self.after) == (not self._after_node_ids)
        yield from self._after_node_ids
        for expr in self.inputs.values():
            yield from _expr_workflow_node_dependencies(expr)


class Gather(WorkflowNode):
    """
    A ``Gather`` node symbolizes the operation to gather an array of declared values or call
    outputs in a scatter section, or optional values from a conditional section. These operations
    are implicit in the WDL syntax, but explicating them in the AST facilitates analysis of the
    workflow's data types and dependency structure.

    Each scatter/conditional section provides ``Gather`` nodes to expose the section body's
    products to the rest of the workflow. When a :class:`WDL.Expr.Ident` elsewhere identifies a
    node inside the section, its ``referee`` attribute is the corresponding ``Gather`` node, which
    in turn references the interior node. The interior node might itself be another ``Gather``
    node, from a nested scatter/conditional section.
    """

    section: "WorkflowSection"
    """
    :type: WorkflowSection

    The ``Scatter``/``Conditional`` section implying this Gather operation
    """

    referee: "Union[Decl, Call, Gather]"
    """
    :type: Union[Decl, Call, Gather]

    The ``Decl``, ``Call``, or sub-``Gather`` node from which this operation "gathers"
    """

    def __init__(self, section: "WorkflowSection", referee: "Union[Decl, Call, Gather]") -> None:
        super().__init__("gather-" + referee.workflow_node_id, referee.pos)
        self.section = section
        self.referee = referee

    def add_to_type_env(
        self, struct_types: Env.Bindings[Dict[str, Type.Base]], type_env: Env.Bindings[Type.Base]
    ) -> Env.Bindings[Type.Base]:
        raise NotImplementedError()

    def _workflow_node_dependencies(self) -> Iterable[str]:
        yield self.referee.workflow_node_id

    @property
    def children(self) -> Iterable[SourceNode]:
        """"""
        # section & referee are NOT 'children' of Gather
        return []

    @property
    def final_referee(self) -> Union[Decl, Call]:
        """
        The ``Decl`` or ``Call`` node found at the end of the referee chain through any nested
        ``Gather`` nodes
        """
        ans = self.referee
        while isinstance(ans, Gather):
            ans = ans.referee
        assert isinstance(ans, (Decl, Call))
        return ans


class WorkflowSection(WorkflowNode):
    """
    Base class for workflow nodes representing scatter and conditional sections
    """

    body: List[WorkflowNode]
    """
    :type: List[WorkflowNode]

    Section body, potentially including nested sections.
    """
    gathers: Dict[str, Gather]
    """
    :type: Dict[str, Gather]

    ``Gather`` nodes exposing the section body's products to the rest of the workflow. The dict is
    keyed by ``workflow_node_id`` of the interior node, to expedite looking up the corresponding
    gather node.

    The section's body and gather nodes do not explicitly include the section node among their
    dependencies. Such dependence is implicit because the body subgraph can be "instantiated" only
    upon visiting the section node at runtime.
    """

    _type_env: Optional[Env.Bindings[Type.Base]] = None
    """
    After typechecking: the type environment, INSIDE the section, consisting of
    - everything available outside of the section
    - declarations and call outputs in the scatter (singletons)
    - declarations & outputs gathered from sub-sections (arrays/optionals)
    - the scatter variable, if applicable
    """

    def __init__(self, body: List[WorkflowNode], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.body = body
        # TODO: add dependency on self to each body node?
        # populate gathers
        self.gathers = dict()
        for elt in self.body:
            if isinstance(elt, (Decl, Call)):
                # assert elt.workflow_node_id not in self.gathers
                # ^ won't hold if the section has internal name collisions, which will be checked
                # later upon building the type environment.
                self.gathers[elt.workflow_node_id] = Gather(self, elt)
            elif isinstance(elt, WorkflowSection):
                # gather gathers!
                for subgather in elt.gathers.values():
                    # assert subgather.workflow_node_id not in self.gathers
                    # id.
                    self.gathers[subgather.workflow_node_id] = Gather(self, subgather)

    @property
    def children(self) -> Iterable[SourceNode]:
        """"""
        for elt in self.body:
            yield elt
        for elt in self.gathers.values():
            yield elt

    @property
    @abstractmethod
    def effective_outputs(self) -> Env.Bindings[Type.Base]:
        raise NotImplementedError()


class Scatter(WorkflowSection):
    """Workflow scatter section"""

    variable: str
    """
    :type: string

    Scatter variable name"""
    expr: Expr.Base
    """
    :type: WDL.Expr.Base

    Expression for the array over which to scatter"""

    def __init__(
        self, pos: SourcePosition, variable: str, expr: Expr.Base, body: List[WorkflowNode]
    ) -> None:
        super().__init__(body, "scatter-L{}C{}-{}".format(pos.line, pos.column, variable), pos)
        self.variable = variable
        self.expr = expr

        for body_node in self.body:
            body_node._increment_scatter_depth()
            # excluded our gather nodes, which are not "within" the section

    @property
    def children(self) -> Iterable[SourceNode]:
        """"""
        yield self.expr
        yield from super().children

    def add_to_type_env(
        self, struct_types: Env.Bindings[Dict[str, Type.Base]], type_env: Env.Bindings[Type.Base]
    ) -> Env.Bindings[Type.Base]:
        # Add declarations and call outputs in this section as they'll be
        # available outside of the section (i.e. a declaration of type T is
        # seen as Array[T] outside)

        inner_type_env: Env.Bindings[Type.Base] = Env.Bindings()
        for elt in self.body:
            inner_type_env = elt.add_to_type_env(struct_types, inner_type_env)
        # Subtlety: if the scatter array is statically nonempty, then so too
        # are the arrayized values.
        nonempty = isinstance(self.expr._type, Type.Array) and self.expr._type.nonempty

        # array-ize each inner type binding and add gather nodes
        def arrayize(binding: Env.Binding[Type.Base]) -> Env.Binding[Type.Base]:
            return Env.Binding(
                binding.name,
                Type.Array(binding.value, nonempty=nonempty),
                self.gathers[binding.info.workflow_node_id],
            )

        return Env.merge(inner_type_env.map(arrayize), type_env)

    @property
    def effective_outputs(self) -> Env.Bindings[Type.Base]:
        # Yield the outputs of calls in this section and subsections, typed
        # and namespaced appropriately, as they'll be propagated if the
        # workflow lacks an explicit output{} section
        nonempty = isinstance(self.expr._type, Type.Array) and self.expr._type.nonempty
        inner_outputs: Env.Bindings[Type.Base] = Env.Bindings()
        for elt in self.body:
            if not isinstance(elt, Decl):
                assert isinstance(elt, (Call, Scatter, Conditional))
                inner_outputs = Env.merge(elt.effective_outputs, inner_outputs)

        def arrayize(binding: Env.Binding[Type.Base]) -> Env.Binding[Type.Base]:
            return Env.Binding(
                binding.name,
                Type.Array(binding.value, nonempty=nonempty),
                self.gathers[binding.info.workflow_node_id],
            )

        return inner_outputs.map(arrayize)

    def _workflow_node_dependencies(self) -> Iterable[str]:
        yield from _expr_workflow_node_dependencies(self.expr)


class Conditional(WorkflowSection):
    """Workflow conditional (if) section"""

    expr: Expr.Base
    """
    :tree: WDL.Expr.Base

    Boolean expression"""

    def __init__(self, pos: SourcePosition, expr: Expr.Base, body: List[WorkflowNode]) -> None:
        super().__init__(body, "if-L{}C{}".format(pos.line, pos.column), pos)
        # TODO: add to id the name of 'shallowest' (closest to root) ident in expr
        self.expr = expr

    @property
    def children(self) -> Iterable[SourceNode]:
        """"""
        yield self.expr
        yield from super().children

    def add_to_type_env(
        self, struct_types: Env.Bindings[Dict[str, Type.Base]], type_env: Env.Bindings[Type.Base]
    ) -> Env.Bindings[Type.Base]:
        # Add declarations and call outputs in this section as they'll be
        # available outside of the section (i.e. a declaration of type T is
        # seen as T? outside)

        inner_type_env: Env.Bindings[Type.Base] = Env.Bindings()
        for elt in self.body:
            inner_type_env = elt.add_to_type_env(struct_types, inner_type_env)

        # optional-ize each inner type binding and add gather nodes
        def optionalize(binding: Env.Binding[Type.Base]) -> Env.Binding[Type.Base]:
            return Env.Binding(
                binding.name,
                binding.value.copy(optional=True),
                self.gathers[binding.info.workflow_node_id],
            )

        return Env.merge(inner_type_env.map(optionalize), type_env)

    @property
    def effective_outputs(self) -> Env.Bindings[Type.Base]:
        # Yield the outputs of calls in this section and subsections, typed
        # and namespaced appropriately, as they'll be propagated if the
        # workflow lacks an explicit output{} section
        inner_outputs: Env.Bindings[Type.Base] = Env.Bindings()
        for elt in self.body:
            if isinstance(elt, (Call, WorkflowSection)):
                inner_outputs = Env.merge(elt.effective_outputs, inner_outputs)

        def optionalize(binding: Env.Binding[Type.Base]) -> Env.Binding[Type.Base]:
            return Env.Binding(
                binding.name,
                binding.value.copy(optional=True),
                self.gathers[binding.info.workflow_node_id],
            )

        return inner_outputs.map(optionalize)

    def _workflow_node_dependencies(self) -> Iterable[str]:
        yield from _expr_workflow_node_dependencies(self.expr)


class Workflow(SourceNode):
    name: str
    ":type: str"
    inputs: Optional[List[Decl]]
    """:type: List[WDL.Tree.Decl]

    Declarations in the ``input{}`` workflow section, if it's present"""
    body: List[WorkflowNode]
    """:type: List[Union[WDL.Tree.Decl,WDL.Tree.Call,WDL.Tree.Scatter,WDL.Tree.Conditional]]

    Workflow body in between ``input{}`` and ``output{}`` sections, if any
    """
    outputs: Optional[List[Decl]]
    """:type: Optional[List[WDL.Tree.Decl]]

    Workflow output declarations, if the ``output{}`` section is present"""
    # following two fields temporarily hold old-style (pre 1.0) outputs with
    # bare identifiers or namespace wildcards. We postprocess them into
    # full declarations as expected in WDL 1.0+.
    _output_idents: List[List[str]]
    _output_idents_pos: Optional[Error.SourcePosition]
    parameter_meta: Dict[str, Any]
    """
    :type: Dict[str,Any]

    ``parameter_meta{}`` section as a JSON-like dict"""
    meta: Dict[str, Any]
    """
    :type: Dict[str,Any]

    ``meta{}`` section as a JSON-like dict"""

    _type_env: Optional[Env.Bindings[Type.Base]] = None
    """
    After typechecking: the type environment in the main workflow body,
    - declarations at the top level of the workflow body
    - outputs of calls at the top level the workflow body
    - declarations & outputs inside scatter sections (as arrays)
    - declarations & outputs inside conditional sections (as optionals)
    """

    complete_calls: bool
    """
    After typechecking, False if the workflow has a call which does not supply
    all required inputs (and thus cannot be called from another workflow).
    """

    _nodes_by_id: Dict[str, WorkflowNode]  # memoizer

    effective_wdl_version: str
    """:type: str

    Effective WDL version of the containing document
    """

    def __init__(
        self,
        pos: SourcePosition,
        name: str,
        inputs: Optional[List[Decl]],
        body: List[WorkflowNode],
        outputs: Optional[List[Decl]],
        parameter_meta: Dict[str, Any],
        meta: Dict[str, Any],
        output_idents: Optional[List[List[str]]] = None,
        output_idents_pos: Optional[SourcePosition] = None,
    ) -> None:
        super().__init__(pos)
        self.name = name
        self.inputs = inputs
        self.body = body
        self.outputs = outputs
        self._output_idents = output_idents or []
        self._output_idents_pos = output_idents_pos
        self.parameter_meta = parameter_meta
        self.meta = meta
        self.complete_calls = True
        self._nodes_by_id = {}
        self.effective_wdl_version = ""  # overridden by Document.__init__

        # Hack: modify workflow node IDs for output decls since, in draft-2, they could reuse names
        # of earlier decls
        for output_decl in self.outputs or []:
            output_decl.workflow_node_id = output_decl.workflow_node_id.replace("decl-", "output-")

    @property
    def available_inputs(self) -> Env.Bindings[Decl]:
        """:type: WDL.Env.Bindings[WDL.Tree.Decl]

        The workflow's input declarations. This includes:

        1. If the ``input{}`` workflow section is present, all declarations within that section.
        Otherwise, all declarations in the top-level workflow body, excluding outputs. (This
        dichotomy bridges pre-1.0 and 1.0+ WDL versions.) These appear at the top level of the Env,
        with no namespace.

        2. Available inputs of all calls in the workflow, namespaced by the call names.
        """
        ans: Env.Bindings[Decl] = Env.Bindings()

        # order of operations here ensures that iterating the env yields decls in the source order
        for c in reversed(list(_calls(self))):
            ans = Env.merge(c.available_inputs, ans)

        if self.inputs is not None:
            for decl in reversed(self.inputs):
                ans = ans.bind(decl.name, decl)
        else:
            for elt in reversed(self.body):
                if isinstance(elt, Decl):
                    ans = ans.bind(elt.name, elt)

        return ans

    @property
    def required_inputs(self) -> Env.Bindings[Decl]:
        """:type: WDL.Env.Bindings[Decl]

        The subset of available inputs which are required to start the workflow.
        """
        ans: Env.Bindings[Decl] = Env.Bindings()

        for c in reversed(list(_calls(self))):
            ans = Env.merge(c.required_inputs, ans)

        for b in reversed(list(self.available_inputs)):
            if "." not in b.name:
                d = b.value
                assert isinstance(d, Decl)
                if not d.type.optional and not d.expr:
                    ans = ans.bind(b.name, b.value)

        return ans

    @property
    def effective_outputs(self) -> Env.Bindings[Type.Base]:
        """:type: WDL.Env.Bindings[Decl]

        If the ``output{}`` workflow section is present, yields the names and
        types therein, at the top level of the Env. Otherwise, yield all the
        call outputs, namespaced and typed appropriately.
        """
        ans: Env.Bindings[Type.Base] = Env.Bindings()

        if self.outputs is not None:
            for decl in reversed(self.outputs):
                ans = ans.bind(decl.name, decl.type, decl)
        else:
            for elt in reversed(self.body):
                if isinstance(elt, (Call, WorkflowSection)):
                    ans = Env.merge(elt.effective_outputs, ans)

        return ans

    @property
    def children(self) -> Iterable[SourceNode]:
        """"""
        for d in self.inputs or []:
            yield d
        for elt in self.body:
            yield elt
        for d in self.outputs or []:
            yield d

    def typecheck(self, doc: "Document", check_quant: bool) -> None:
        assert doc.workflow is self
        assert self._type_env is None
        # 1. resolve all calls and check for call name collisions
        _resolve_calls(doc)
        # 2. build type environments in the workflow and each scatter &
        #    conditional section therein
        stdlib = StdLib.Base(self.effective_wdl_version)
        _build_workflow_type_env(doc, stdlib, check_quant)
        assert self._type_env is not None
        with Error.multi_context() as errors:
            # 3. typecheck the right-hand side expressions of each declaration
            #    and the inputs to each call (descending into scatter & conditional
            #    sections)
            for decl in self.inputs or []:
                errors.try1(
                    (
                        lambda decl, type_env: lambda: decl.typecheck(
                            type_env,
                            stdlib,
                            check_quant=check_quant,
                            struct_types=doc._struct_types,
                        )
                    )(decl, self._type_env)
                )
            if errors.try1(lambda: _typecheck_workflow_body(doc, stdlib, check_quant)) is False:
                self.complete_calls = False
            for b in self.available_inputs:
                errors.try1(lambda: _check_serializable_map_keys(b.value.type, b.name, b.value))
            # 4. convert deprecated output_idents, if any, to output declarations
            if self._output_idents:
                self._rewrite_output_idents()
            # 5. typecheck the output expressions
            if self.outputs:
                output_names: Set[str] = set()
                output_type_env = self._type_env
                assert output_type_env is not None
                for output in self.outputs:
                    assert output.expr
                    if output.name in output_names:
                        errors.append(
                            Error.MultipleDefinitions(
                                output, "multiple workflow outputs named " + output.name
                            )
                        )
                    output_names.add(output.name)
                    # tricky sequence here: we need to call Decl.add_to_type_env to resolve
                    # potential struct type, but:
                    # 1. we may not want it to check for name collision in the usual way in order to
                    #    handle a quirk of draft-2 workflow output style, where an output may take
                    #    the name of another decl in the workflow. Instead we've tracked and
                    #    rejected any duplicate names among the workflow outputs.
                    # 2. we still want to typecheck the output expression againsnt the 'old' type
                    #    environment
                    output_type_env2 = output.add_to_type_env(
                        doc._struct_types,
                        output_type_env,
                        collision_ok=getattr(output, "_rewritten_ident", False),
                    )
                    errors.try1(
                        lambda output=output: output.typecheck(
                            output_type_env,
                            stdlib,
                            check_quant=check_quant,
                            struct_types=doc._struct_types,
                        )
                    )
                    output_type_env = output_type_env2
                    errors.try1(
                        lambda: _check_serializable_map_keys(output.type, output.name, output)
                    )
        # 6. check for cyclic dependencies
        _detect_cycles(_workflow_dependency_matrix(self))

    def _rewrite_output_idents(self) -> None:
        # for pre-1.0 workflow output sections with a list of namespaced
        # identifiers (instead of bound decls)
        assert self._type_env is not None

        # for each listed identifier, formulate a synthetic declaration
        output_ident_decls = []
        for output_ident in self._output_idents:
            assert self._output_idents_pos
            output_idents = [output_ident]

            if output_idents[0][-1] == "*":
                # wildcard: expand to each call output
                wildcard_namespace_parts = output_idents[0][:-1]
                wildcard_namespace = ".".join(wildcard_namespace_parts)
                output_idents = []
                if not self._type_env.has_namespace(wildcard_namespace):
                    raise Error.NoSuchTask(self._output_idents_pos, wildcard_namespace) from None
                for binding in self._type_env.enter_namespace(wildcard_namespace):
                    assert isinstance(binding, Env.Binding)
                    binding_name = binding.name
                    assert isinstance(binding_name, str)
                    if not binding_name.startswith("_"):
                        output_idents.append(wildcard_namespace_parts + [binding_name])

            for output_ident1 in output_idents:
                # the output name is supposed to be 'fully qualified'
                # including the call namespace. we're going to stick it
                # into the decl name with a ., which is a weird corner
                # case!
                synthetic_output_name = ".".join(output_ident1)
                ty = self._type_env.get(synthetic_output_name)
                if not ty:
                    raise Error.UnknownIdentifier(
                        Expr.Ident(self._output_idents_pos, synthetic_output_name)
                    ) from None
                output_ident_decls.append(
                    Decl(
                        self.pos,
                        ty,
                        synthetic_output_name,
                        Expr.Ident(self._output_idents_pos, synthetic_output_name),
                        id_prefix="output",
                    )
                )

        for decl in output_ident_decls:
            setattr(decl, "_rewritten_ident", True)

        # put the synthetic declarations into self.outputs
        self.outputs = output_ident_decls + (self.outputs or [])
        self._output_idents = []

    def get_node(self, workflow_node_id: str) -> WorkflowNode:
        """
        Look up ``WorkflowNode`` by ``workflow_node_id``
        """
        if not self._nodes_by_id:

            def visit(node: SourceNode) -> None:
                if isinstance(node, WorkflowNode):
                    self._nodes_by_id[node.workflow_node_id] = node
                    for ch in node.children:
                        visit(ch)

            for ch in self.children:
                visit(ch)
        return self._nodes_by_id[workflow_node_id]

    _digest: str = ""

    @property
    def digest(self) -> str:
        """
        Content digest of the workflow, for use e.g. as a cache key. The digest is an opaque string
        of a few dozen alphanumeric characters, sensitive to the workflow's source code (with best
        effort to exclude comments and whitespace) and the tasks and subworkflows it calls.
        """
        if self._digest:
            return self._digest
        sha256 = hashlib.sha256(self._digest_source().encode("utf-8")).digest()
        self._digest = base64.b32encode(sha256[:20]).decode().lower()
        return self._digest

    def _digest_source(self) -> str:
        doc = getattr(self, "parent", None)
        assert isinstance(doc, Document)

        # For now we just excerpt the workflow's source code, minus comments and blank lines, plus
        # annotations for the WDL version, struct types, and called tasks & subworkflows.
        source_lines = []
        if doc.wdl_version:
            source_lines.append("version " + doc.wdl_version)

        # Insert comments describing struct types used in the workflow
        structs = _describe_struct_types(self)
        for struct_name in sorted(structs.keys()):
            source_lines.append(f"# {struct_name} :: {structs[struct_name]}")

        # Insert comments with the digests of called tasks & subworkflows (to ensure the workflow
        # digest will be sensitive to changes in those).
        for call in _calls(self):
            callee = call.callee
            assert isinstance(call, Call) and isinstance(callee, (Task, Workflow))
            source_lines.append(f"# {'.'.join(call.callee_id)} :: {callee.digest}")

        # excerpt workflow{} from document
        source_lines += _source_excerpt(doc, self.pos)
        return "\n".join(source_lines).strip()


SourceComment = NamedTuple("SourceComment", [("pos", Error.SourcePosition), ("text", str)])
"""
Position and text of a comment. The text includes the ``#`` and any preceding or trailing
spaces/tabs.
"""

DocImport = NamedTuple(
    "DocImport",
    [
        ("pos", Error.SourcePosition),
        ("uri", str),
        ("namespace", str),
        ("aliases", List[Tuple[str, str]]),
        ("doc", "Optional[Document]"),
    ],
)
"""
Represents one imported document, with position of the import statement, import URI, namespace,
struct type aliases, and (after typechecking) the ``Document`` object.
"""


class Document(SourceNode):
    """
    Top-level document, with imports, tasks, and up to one workflow. Typically returned by
    :func:`~WDL.load`.
    """

    source_text: str
    """
    :type: str

    Original WDL source code text
    """

    source_lines: List[str]
    """
    :type: List[str]

    Original WDL source code text split by newlines. ``SourcePosition`` line numbers are
    one-based, so line number ``L`` corresponds to ``source_lines[L-1]``.
    """

    source_comments: List[Optional[SourceComment]]
    """
    :type: List[Optional[SourceComment]]

    Lookup table for source code comments. ``source_comments`` has the same length as
    ``source_lines``, and each entry is the :class:`WDL.Tree.SourceComment` found on the
    corresponding source line, or ``None`` if the line has no comment.
    """

    wdl_version: Optional[str]
    """
    :type: Optional[str]

    Declared WDL language version, if any
    """

    effective_wdl_version: str
    """
    :type"

    ``wdl_version if wdl_version is not None else "draft-2"``
    """

    imports: List[DocImport]
    """
    :type: List[DocImport]

    Imported documents"""
    struct_typedefs: Env.Bindings[StructTypeDef]
    """:type: Env.Bindings[WDL.Tree.StructTypeDef]"""

    _struct_types: Env.Bindings[Dict[str, Type.Base]]
    # simpler mapping of struct names to their members, used for typechecking ops

    tasks: List[Task]
    """:type: List[WDL.Tree.Task]"""
    workflow: Optional[Workflow]
    """:type: Optional[WDL.Tree.Workflow]"""

    def __init__(
        self,
        source_text: str,
        pos: SourcePosition,
        imports: List[DocImport],
        struct_typedefs: Dict[str, StructTypeDef],
        tasks: List[Task],
        workflow: Optional[Workflow],
        comments: List[SourceComment],
        wdl_version: Optional[str],
    ) -> None:
        super().__init__(pos)
        self.imports = imports
        self.struct_typedefs = Env.Bindings()
        for name, struct_typedef in struct_typedefs.items():
            self.struct_typedefs = self.struct_typedefs.bind(name, struct_typedef)
        self._struct_types = Env.Bindings()
        self.tasks = tasks
        self.workflow = workflow
        self.source_text = source_text
        self.source_lines = source_text.split("\n")
        self.source_comments = [None for _ in self.source_lines]
        self.wdl_version = wdl_version
        self.effective_wdl_version = wdl_version if wdl_version is not None else "draft-2"
        for task in self.tasks:
            task.effective_wdl_version = self.effective_wdl_version
        if self.workflow:
            self.workflow.effective_wdl_version = self.effective_wdl_version
        for comment in comments:
            assert self.source_comments[comment.pos.line - 1] is None
            assert self.source_lines[comment.pos.line - 1].endswith(comment.text)
            self.source_comments[comment.pos.line - 1] = comment

    @property
    def children(self) -> Iterable[SourceNode]:
        """"""
        for imp in self.imports:
            if imp.doc:
                yield imp.doc
        for stb in self.struct_typedefs:
            assert isinstance(stb, Env.Binding) and isinstance(stb.value, StructTypeDef)
            yield stb.value
        for task in self.tasks:
            yield task
        if self.workflow:
            yield self.workflow

    def typecheck(self, check_quant: bool = True) -> None:
        """Typecheck each task in the document, then the workflow, if any.

        Documents returned by :func:`~WDL.load` have already been typechecked."""
        names = set()
        for imp in self.imports:
            if imp.namespace in names:
                raise Error.MultipleDefinitions(
                    self, "Multiple imports with namespace " + imp.namespace
                )
            names.add(imp.namespace)
        _import_structs(self)
        for struct_binding in self.struct_typedefs:
            self._struct_types = self._struct_types.bind(
                struct_binding.name, struct_binding.value.members
            )
        _initialize_struct_typedefs(self.struct_typedefs, self._struct_types)
        names = set()
        # typecheck each task
        with Error.multi_context() as errors:
            for task in self.tasks:
                if task.name in names:
                    errors.append(
                        Error.MultipleDefinitions(task, "Multiple tasks named " + task.name)
                    )
                names.add(task.name)
                errors.try1(
                    (
                        lambda task: lambda: task.typecheck(
                            self._struct_types, check_quant=check_quant
                        )
                    )(task)
                )
        # typecheck the workflow
        if self.workflow:
            if self.workflow.name in names:
                raise Error.MultipleDefinitions(
                    self.workflow,
                    "Workflow name collides with a task also named " + self.workflow.name,
                )
            self.workflow.typecheck(self, check_quant=check_quant)


async def resolve_file_import(uri: str, path: List[str], importer: Optional[Document]) -> str:
    if uri.startswith("http://") or uri.startswith("https://"):
        # for now we do nothing with web URIs
        return uri
    if uri.startswith("file:///"):
        uri = uri[7:]
    if os.path.isabs(uri):
        # given an already-absolute filename, just normalize it
        ans: Optional[str] = os.path.abspath(uri)
    else:
        # resolving a relative import: before searching the user-provided path directories, try the
        # directory of the importing document (if any), or the current working directory
        # (otherwise)
        path = path + [os.path.dirname(importer.pos.abspath) if importer else os.getcwd()]
        ans = next(
            (
                fn
                for fn in (os.path.abspath(os.path.join(dn, uri)) for dn in reversed(path))
                if os.path.isfile(fn)
            ),
            None,
        )
    if ans and (os.path.isfile(ans) or ans.startswith("/dev/fd/")):
        return ans
    raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), uri)


ReadSourceResult = NamedTuple("ReadSourceResult", [("source_text", str), ("abspath", str)])


async def read_source_default(
    uri: str, path: List[str], importer: Optional[Document]
) -> ReadSourceResult:
    abspath = await resolve_file_import(uri, path, importer)
    # TODO: actual async read
    with open(abspath, "r") as infile:
        return ReadSourceResult(source_text=infile.read(), abspath=abspath)


async def _load_async(
    uri: str,
    path: Optional[List[str]] = None,
    check_quant: bool = True,
    read_source: Optional[
        Callable[[str, List[str], Optional[Document]], Awaitable[ReadSourceResult]]
    ] = None,
    import_max_depth: int = 10,
    importer: Optional[Document] = None,
) -> Document:
    path = list(path) if path is not None else []
    read_source = read_source or read_source_default
    uri = uri if uri != "-" else "/dev/stdin"
    read_rslt = await read_source(uri, path, importer)
    # parse the document
    try:
        doc = _parser.parse_document(read_rslt.source_text, uri=uri, abspath=read_rslt.abspath)
    except Exception as exn:
        setattr(exn, "source_text", read_rslt.source_text)
        raise
    assert doc.pos.uri == uri and doc.pos.abspath.endswith(os.path.basename(doc.pos.uri))
    # recursively descend into document's imports, and store the imported
    # documents into doc.imports
    # TODO: are we supposed to do something smart for relative imports
    #       within a document loaded by URI?
    # TODO: concurrent imports
    for i in range(len(doc.imports)):
        imp = doc.imports[i]
        if import_max_depth <= 1:
            raise Error.ImportError(
                imp.pos, imp.uri, "exceeded import_max_depth; circular imports?"
            )
        try:
            subdoc = await _load_async(
                imp.uri,
                path=path,
                check_quant=check_quant,
                read_source=read_source,
                importer=doc,
                import_max_depth=(import_max_depth - 1),
            )
        except Exception as exn:
            raise Error.ImportError(imp.pos, imp.uri) from exn
        doc.imports[i] = DocImport(
            pos=imp.pos, uri=imp.uri, namespace=imp.namespace, aliases=imp.aliases, doc=subdoc
        )
    try:
        doc.typecheck(check_quant=check_quant)
    except Error.ValidationError as exn:
        exn.source_text = read_rslt.source_text
        exn.declared_wdl_version = doc.wdl_version
        raise
    except Error.MultipleValidationErrors as multi:
        for exn1 in multi.exceptions:
            if not exn1.source_text:
                exn1.source_text = read_rslt.source_text
                exn1.declared_wdl_version = doc.wdl_version
        multi.source_text = read_rslt.source_text
        multi.declared_wdl_version = doc.wdl_version
        raise multi
    return doc


def _load(
    uri: str,
    path: Optional[List[str]] = None,
    check_quant: bool = True,
    read_source: Optional[
        Callable[[str, List[str], Optional[Document]], Awaitable[ReadSourceResult]]
    ] = None,
    import_max_depth: int = 10,
    importer: Optional[Document] = None,
) -> Document:
    return asyncio.get_event_loop().run_until_complete(
        _load_async(
            uri,
            path=path,
            importer=importer,
            check_quant=check_quant,
            read_source=read_source,
            import_max_depth=import_max_depth,
        )
    )


#
# Typechecking helper functions
#


def _calls(element: Union[Workflow, WorkflowSection]) -> Generator[Call, None, None]:
    # Yield each Call in the workflow, including those nested within scatter/conditional sections
    for ch in element.children:
        if isinstance(ch, Call):
            yield ch
        elif isinstance(ch, WorkflowSection):
            yield from _calls(ch)


def _resolve_calls(doc: Document) -> None:
    # Resolve all calls in the workflow (descending into scatter & conditional
    # sections).
    if doc.workflow:
        with Error.multi_context() as errors:
            for c in _calls(doc.workflow):
                errors.try1((lambda c: lambda: c.resolve(doc))(c))


def _build_workflow_type_env(
    doc: Document,
    stdlib: StdLib.Base,
    check_quant: bool,
    self: Optional[Union[Workflow, WorkflowSection]] = None,
    outer_type_env: Optional[Env.Bindings[Type.Base]] = None,
) -> None:
    # Populate each Workflow, Scatter, and Conditional object with its
    # _type_env attribute containing the type environment available in the body
    # of the respective section. This is tricky because:
    # - forward-references to any declaration or call output in the workflow
    #   are valid, except
    #   - circular dependencies, direct or indirect
    #   - (corollary) scatter and conditional expressions can't refer to
    #     anything within the respective section
    # - a scatter variable is visible only inside the scatter
    # - declarations & call outputs of type T within a scatter have type
    #   Array[T] outside of the scatter
    # - declarations & call outputs of type T within a conditional have type T?
    #   outside of the conditional
    #
    # preconditions:
    # - _resolve_calls()
    #
    # postconditions:
    # - typechecks scatter and conditional expressions (recursively)
    # - sets _type_env attributes on each Workflow/Scatter/Conditional
    assert doc.workflow
    self = self or doc.workflow
    if not self:
        return
    assert isinstance(self, WorkflowSection) or self is doc.workflow
    assert self._type_env is None

    # When we've been called recursively on a scatter or conditional section,
    # the 'outer' type environment has everything available in the workflow
    # -except- the body of self.
    type_env = outer_type_env or Env.Bindings()

    if isinstance(self, Workflow):
        # start with workflow inputs
        for decl in self.inputs or []:
            type_env = decl.add_to_type_env(doc._struct_types, type_env)
    elif isinstance(self, Scatter):
        # typecheck scatter array
        self.expr.infer_type(
            type_env, stdlib, check_quant=check_quant, struct_types=doc._struct_types
        )
        if not isinstance(self.expr.type, Type.Array):
            raise Error.NotAnArray(self.expr)
        if isinstance(self.expr.type.item_type, Type.Any):
            raise Error.IndeterminateType(self.expr, "can't infer item type of empty array")
        # bind the scatter variable to the array item type within the body
        if self.variable in type_env:
            raise Error.MultipleDefinitions(
                self, "Name collision for scatter variable " + self.variable
            )
        if type_env.has_namespace(self.variable):
            raise Error.MultipleDefinitions(
                self, "Call name collision for scatter variable " + self.variable
            )
        type_env = type_env.bind(self.variable, self.expr.type.item_type, self)
    elif isinstance(self, Conditional):
        # typecheck the condition
        self.expr.infer_type(
            type_env, stdlib, check_quant=check_quant, struct_types=doc._struct_types
        )
        if not self.expr.type.coerces(Type.Boolean()):
            raise Error.StaticTypeMismatch(self.expr, Type.Boolean(), self.expr.type)
    else:
        assert False

    # descend into child scatter & conditional elements, if any.
    for child in self.body:
        if isinstance(child, WorkflowSection):
            # prepare the 'outer' type environment for the child element, by
            # adding all its sibling declarations and call outputs
            child_outer_type_env = type_env
            for sibling in self.body:
                if sibling is not child:
                    child_outer_type_env = sibling.add_to_type_env(
                        doc._struct_types, child_outer_type_env
                    )
            _build_workflow_type_env(doc, stdlib, check_quant, child, child_outer_type_env)
        elif isinstance(child, Decl) and not child.type.optional and not child.expr:
            if doc.workflow.inputs is not None:
                raise Error.StrayInputDeclaration(
                    self,
                    "unbound non-optional declaration {} {} outside workflow input{} section".format(
                        str(child.type), child.name, "{}"
                    ),
                )
            elif not isinstance(self, Workflow):
                raise Error.StrayInputDeclaration(
                    self,
                    "unbound non-optional declaration {} {} inside scatter/conditional section".format(
                        str(child.type), child.name
                    ),
                )

    # finally, populate self._type_env with all our children
    for child in self.body:
        type_env = child.add_to_type_env(doc._struct_types, type_env)
    self._type_env = type_env


def _typecheck_workflow_body(
    doc: Document,
    stdlib: StdLib.Base,
    check_quant: bool,
    self: Optional[Union[Workflow, WorkflowSection]] = None,
) -> bool:
    # following _resolve_calls() and _build_workflow_type_env(), typecheck all
    # the declaration expressions and call inputs
    self = self or doc.workflow
    assert self and (self._type_env is not None)
    complete_calls = True
    with Error.multi_context() as errors:
        for child in self.body:
            if isinstance(child, Decl):
                errors.try1(
                    _translate_struct_mismatch(
                        doc,
                        (
                            lambda child, type_env: lambda: child.typecheck(
                                type_env,
                                stdlib,
                                check_quant=check_quant,
                                struct_types=doc._struct_types,
                            )
                        )(child, self._type_env),
                    )
                )
            elif isinstance(child, Call):
                if (
                    errors.try1(
                        _translate_struct_mismatch(
                            doc,
                            (
                                lambda child, type_env: lambda: child.typecheck_input(
                                    doc._struct_types, type_env, stdlib, check_quant=check_quant
                                )
                            )(child, self._type_env),
                        )
                    )
                    is False
                ):
                    complete_calls = False
            elif isinstance(child, WorkflowSection):
                if (
                    errors.try1(
                        _translate_struct_mismatch(
                            doc,
                            (
                                lambda child: lambda: _typecheck_workflow_body(
                                    doc, stdlib, check_quant, child
                                )
                            )(child),
                        )
                    )
                    is False
                ):
                    complete_calls = False
            else:
                assert False
    return complete_calls


def _translate_struct_mismatch(doc: Document, stmt: Callable[[], Any]) -> Callable[[], Any]:
    # When we get a StaticTypeMismatch error during workflow typechecking,
    # which involves a struct type imported from another document, the error
    # message may require translation from the struct type's original name
    # within in the imported document to its aliased name in the current
    # document.
    def f(doc=doc, stmt=stmt):
        try:
            return stmt()
        except Error.StaticTypeMismatch as exc:
            expected = exc.expected
            if isinstance(expected, Type.StructInstance):
                for stb in doc.struct_typedefs:
                    assert isinstance(stb, Env.Binding) and isinstance(stb.value, StructTypeDef)
                    if id(stb.value.members) == id(expected.members):
                        expected = Type.StructInstance(stb.name, optional=expected.optional)
                        expected.members = stb.value.members
            actual = exc.actual
            if isinstance(actual, Type.StructInstance):
                for stb in doc.struct_typedefs:
                    assert isinstance(stb, Env.Binding) and isinstance(stb.value, StructTypeDef)
                    if id(stb.value.members) == id(actual.members):
                        actual = Type.StructInstance(stb.name, optional=actual.optional)
                        actual.members = stb.value.members
            raise Error.StaticTypeMismatch(exc.node or exc.pos, expected, actual, exc.message)

    return f


def _expr_workflow_node_dependencies(expr: Optional[Expr.Base]) -> Iterable[str]:
    # Given some Expr within a workflow, yield the workflow node IDs of the referees of each
    # Expr.Ident subexpression. These referees can include
    #   - Decl: reference to a named value
    #   - Call: reference to a call output
    #   - Gather: reference to values(s) (array/optional) gathered from a scatter or conditional
    #             section
    if isinstance(expr, Expr.Ident):
        assert isinstance(expr.referee, WorkflowNode)
        # omit dependence on containing scatter sections (when scatter variable is used), which we
        # handle implicitly
        if not isinstance(expr.referee, WorkflowSection):
            yield expr.referee.workflow_node_id
    for ch in expr.children if expr else []:
        assert isinstance(ch, Expr.Base)
        yield from _expr_workflow_node_dependencies(ch)


def _decl_dependency_matrix(decls: List[Decl]) -> Tuple[Dict[str, Decl], _util.AdjM[str]]:
    # Given decls (e.g. in a task), produce mapping of workflow node id to the objects, and the
    # AdjM of their dependencies (edge from o1 to o2 = o2 depends on o1)
    # IGNORES dependencies that aren't among decls to begin with (the task runtime omits decls that
    # are supplied/overriden by runtime inputs)
    objs_by_id = dict((decl.workflow_node_id, decl) for decl in decls)
    assert len(objs_by_id) == len(decls)
    adj: _util.AdjM = _util.AdjM()

    for obj in decls:
        oid = obj.workflow_node_id
        adj.add_node(oid)
        for dep_id in obj.workflow_node_dependencies:
            if dep_id in objs_by_id:
                adj.add_edge(dep_id, oid)

    assert set(objs_by_id.keys()) == set(adj.nodes)
    return (objs_by_id, adj)


def _workflow_dependency_matrix(
    workflow: Workflow,
) -> Tuple[Dict[str, WorkflowNode], _util.AdjM[str]]:
    # Given workflow, produce mapping of workflow node id to each node, and the AdjM of their
    # dependencies (edge from o1 to o2 = o2 depends on o1). Considers each Scatter and Conditional
    # node a dependency of each of its body nodes.
    objs_by_id = {}
    adj: _util.AdjM = _util.AdjM()

    def visit(obj: WorkflowNode) -> None:
        oid = obj.workflow_node_id
        objs_by_id[oid] = obj
        adj.add_node(oid)
        if isinstance(obj, WorkflowSection):
            for ch in itertools.chain(obj.body, obj.gathers.values()):
                visit(ch)
                # TODO: should body nodes explicitly report their section as a dependency?
                adj.add_edge(oid, ch.workflow_node_id)
        for dep_id in obj.workflow_node_dependencies:
            adj.add_edge(dep_id, oid)

    for inp in workflow.inputs or []:
        visit(inp)
    for obj in workflow.body:
        visit(obj)
    for outp in workflow.outputs or []:
        visit(outp)

    assert set(objs_by_id.keys()) == set(adj.nodes)
    return (objs_by_id, adj)


def _detect_cycles(p: Tuple[Dict[str, WorkflowNode], _util.AdjM[str]]) -> None:
    # given the result of _dependency_matrix, detect if there exists a cycle
    # and if so, then raise WDL.Error.CircularDependencies with a relevant
    # SourceNode.
    nodes, adj = p
    try:
        _util.topsort(adj)
    except StopIteration as err:
        raise Error.CircularDependencies(nodes[getattr(err, "node")]) from None


def _import_structs(doc: Document):
    # Add imported structs to doc.struct_typedefs, with collision checks
    for imp in [
        imp for imp in doc.imports if imp.doc
    ]:  # imp.doc should be None only for certain legacy unit tests
        assert imp.doc
        imported_structs = {}
        for stb in imp.doc.struct_typedefs:
            assert isinstance(stb, Env.Binding) and isinstance(stb.value, StructTypeDef)
            imported_structs[stb.name] = stb.value
        for name, alias in imp.aliases:
            if name not in imported_structs:
                raise Error.NoSuchMember(imp.pos, name)
            if alias in imported_structs:
                raise Error.MultipleDefinitions(
                    imp.pos,
                    "struct type alias {} collides with another struct type in the imported document".format(
                        alias
                    ),
                )
            try:
                collider = doc.struct_typedefs[alias]
                raise Error.MultipleDefinitions(
                    imp.pos,
                    "struct type alias {} collides with a struct {} document".format(
                        alias,
                        (
                            "type/alias from another imported"
                            if collider.imported
                            else "type in this"
                        ),
                    ),
                )
            except KeyError:
                pass
            if alias != name:
                imported_structs[alias] = imported_structs[name]
                del imported_structs[name]
        for name, st in imported_structs.items():
            existing = None
            try:
                existing = doc.struct_typedefs[name]
                if existing.type_id != st.type_id:
                    raise Error.MultipleDefinitions(
                        imp.pos,
                        "imported struct {} must be aliased because it collides with a struct {} document".format(
                            name,
                            (
                                "type/alias from another imported"
                                if existing.imported
                                else "type in this"
                            ),
                        ),
                    )
            except KeyError:
                pass
            if not existing:
                st2 = StructTypeDef(imp.pos, name, st.members, imported=(imp.doc, st))
                doc.struct_typedefs = doc.struct_typedefs.bind(name, st2)


def _resolve_struct_type(
    pos: Error.SourcePosition,
    ty: Type.StructInstance,
    struct_types: Env.Bindings[Dict[str, Type.Base]],
):
    # On initial document construction, WDL.Type.StructInstance is not yet resolved to the struct
    # type definition. Here, we populate 'members' with the dict of member types and names given
    # the document-wide Env.Bindings[StructTypeDef].
    #
    # 'members' may already be populated in WDL.Type.StructInstance imported from another, already-
    # typechecked document. In that case it's important to leave them be, as the struct type name
    # could refer to something else in the current document. (issue #635)
    if ty.members is None:
        try:
            ty.members = struct_types[ty.type_name]
            assert isinstance(ty.members, dict)
        except KeyError:
            raise Error.InvalidType(pos, "Unknown type " + ty.type_name) from None


def _resolve_struct_types(
    pos: Error.SourcePosition,
    ty: Type.Base,
    struct_types: Env.Bindings[Dict[str, Type.Base]],
    members_dict_ids: Optional[List[int]] = None,
):
    members_dict_ids = members_dict_ids or []
    # resolve all StructInstance within a potentially compound type
    if isinstance(ty, Type.StructInstance):
        _resolve_struct_type(pos, ty, struct_types)
        if id(ty.members) in members_dict_ids:
            # circular struct types!
            raise StopIteration
        members_dict_ids = [id(ty.members)] + (members_dict_ids or [])
    for p in ty.parameters:
        _resolve_struct_types(pos, p, struct_types, members_dict_ids=members_dict_ids)


def _initialize_struct_typedefs(
    struct_typedefs: Env.Bindings[StructTypeDef], struct_types: Env.Bindings[Dict[str, Type.Base]]
):
    # bootstrap struct typechecking: resolve all StructInstance members of the
    # struct types; also detect & error circular struct definitions
    for b in struct_typedefs:
        assert isinstance(b, Env.Binding)
        for member_ty in b.value.members.values():
            try:
                _resolve_struct_types(b.value.pos, member_ty, struct_types)
            except StopIteration:
                raise Error.CircularDependencies(b.value) from None


def _add_struct_instance_to_type_env(
    namespace: str, ty: Type.StructInstance, type_env: Env.Bindings[Type.Base], ctx: Any
):
    # populate the type env with a binding for the struct instance and a
    # namespace containing its members (recursing if any members are themselves
    # struct instances)
    assert isinstance(ty.members, dict)
    ans = type_env.bind(namespace, ty, ctx)
    for member_name, member_type in ty.members.items():
        if isinstance(member_type, Type.StructInstance):
            ans = _add_struct_instance_to_type_env(
                namespace + "." + member_name, member_type, ans, ctx
            )
        else:
            ans = ans.bind(namespace + "." + member_name, member_type, ctx)
    return ans


def _check_serializable_map_keys(t: Type.Base, name: str, node: SourceNode) -> None:
    # For any Map[K,V] in an input or output declaration, K must be coercible to & from String, so
    # that it can be de/serialized as JSON.
    if isinstance(t, Type.Map):
        kt = t.item_type[0]
        if not kt.coerces(Type.String()) or not Type.String().coerces(kt):
            raise Error.ValidationError(
                node,
                f"{str(t)} may not be used in input/output {name} because the keys cannot be written to/from JSON",
            )
    for p in t.parameters:
        _check_serializable_map_keys(p, name, node)


def _describe_struct_types(exe: Union[Task, Workflow]) -> Dict[str, str]:
    """
    Traverse the task/workflow AST to find all struct types used; produce a mapping from struct
    name to its type_id (a string describing the struct's members, independent of the struct name,
    as the latter can differ across documents).
    """
    structs = {}
    items: List[Any] = list(exe.children)
    while items:
        item = items.pop()
        if isinstance(item, Type.StructInstance):
            structs[item.type_name] = item.type_id
        elif isinstance(item, Type.Base):
            # descent into compound types so we'll cover e.g. Array[MyStructType]
            for par_ty in item.parameters:
                items.append(par_ty)
        elif isinstance(item, Expr.Base):
            # descent into expressions to find struct literals
            if isinstance(item, Expr.Struct):
                items.append(item.type)
            items.extend(item.children)
        elif isinstance(item, Decl):
            items.append(item.type)
            items.append(item.expr)
        elif isinstance(item, WorkflowSection):
            items.extend(item.children)
        elif isinstance(item, Call):
            items.extend(item.available_inputs)
            for b in item.effective_outputs:
                items.append(b.value)
    return structs


def _source_excerpt(
    doc: Document, pos: SourcePosition, literals: Optional[List[SourcePosition]] = None
) -> List[str]:
    """
    Excerpt the document's source lines indicated by pos : WDL.SourcePosition. Delete comments,
    blank lines, and leading/trailing whitespace from each line -- except those indicated by
    literals.
    """
    literals = literals if literals else []

    def clean(line: int, column: int = 1, end_column: Optional[int] = None) -> List[str]:
        literal = next(
            (True for lit in literals if line >= lit.line and line <= lit.end_line), False
        )
        comment = doc.source_comments[line - 1]
        if comment and not literal:
            assert comment.pos.line == line
            if end_column is None:
                end_column = comment.pos.column - 1
            else:
                end_column = min(end_column, comment.pos.column - 1)
        txt = doc.source_lines[line - 1][(column - 1) : end_column]
        if literal:
            return [txt]
        txt = txt.strip()
        return [txt] if txt else []

    if pos.end_line == pos.line:
        return clean(pos.line, pos.column, pos.end_column)
    return list(
        itertools.chain(
            clean(pos.line, pos.column),
            *(clean(line_nr) for line_nr in range(pos.line + 1, pos.end_line)),
            clean(pos.end_line, 1, pos.end_column),
        )
    )
