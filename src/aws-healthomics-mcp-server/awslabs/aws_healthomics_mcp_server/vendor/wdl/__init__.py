# Vendored from chanzuckerberg/miniwdl (https://github.com/chanzuckerberg/miniwdl) at tag
# v1.13.0, commit 7f3068ff31de3d16d398ab5693a8dd8f21c5c807. MIT licensed (see LICENSE in this
# directory). Only the WDL parsing and static-lint modules are included; the `WDL.runtime`
# task-execution package (and its GPL-licensed `pygtail` dependency) is deliberately excluded
# and is neither vendored nor imported here. See VENDORED.md for details.

"""
`miniwdl <https://github.com/chanzuckerberg/miniwdl/>`_ is a developer toolkit and local runner for
the bioinformatics-focused `Workflow Description Language (WDL) <http://openwdl.org/>`_. This
documentation covers the Python3 ``WDL`` package facilitating parsing & static analysis of WDL
documents. Simply ``import WDL`` once miniwdl has been installed.

* `GitHub repo <https://github.com/chanzuckerberg/miniwdl/>`_ for installation and further background
* `Codelabs <https://miniwdl.readthedocs.io/en/latest/WDL.html#python-codelabs>`_ on using this package
"""

import sys
import os
from typing import List, Optional, Callable, Dict, Any, Awaitable, Union
from . import _util, _parser, Error, Type, Value, Env, Expr, Tree, Walker
from .Tree import (  # noqa: F401
    Decl,
    StructTypeDef,
    Task,
    Call,
    Scatter,
    Conditional,
    Gather,
    Workflow,
    Document,
    WorkflowNode,
    WorkflowSection,
    SourceComment,
    ReadSourceResult,
)

SourcePosition = Error.SourcePosition
SourceNode = Error.SourceNode


def load(
    uri: str,
    path: Optional[List[str]] = None,
    check_quant: bool = True,
    read_source: Optional[
        Callable[[str, List[str], Optional[Document]], Awaitable["ReadSourceResult"]]
    ] = None,
    import_max_depth: int = 10,
) -> Document:
    """
    Parse a WDL document given filename/URI, recursively descend into imported documents, then typecheck the tasks and
    workflow.

    :param path: local filesystem directories to search for imports, in addition to the current working directory

    :param check_quant:
        set to ``False`` to relax static typechecking of the optional (?) and nonempty (+) type quantifiers. This is
        discouraged, but may be useful for older WDL workflows which assume less-rigorous static validation of these
        annotations.

    :param read_source:
        async routine to read the WDL source code from filename/URI; see :func:`read_source_default` below for details

    :param import_max_depth:
        to prevent recursive import infinite loops, fail when there are too many import nesting levels (default 10)

    :raises WDL.Error.SyntaxError: when the document is syntactically invalid under the WDL grammar
    :raises WDL.Error.ValidationError:
        when the document is syntactically OK, but fails typechecking or other static validity checks
    :raises WDL.Error.MultipleValidationErrors:
        when multiple validation errors are detected in one pass, listed in the ``exceptions`` attribute
    :raises WDL.Error.ImportError:
        when an imported sub-document can't be loaded; the ``__cause__`` attribute has the specific error
    """
    doc = Tree._load(
        uri,
        path=path,
        check_quant=check_quant,
        read_source=read_source,
        import_max_depth=import_max_depth,
    )
    Walker.SetParents()(doc)
    return doc


async def load_async(
    uri: str,
    path: Optional[List[str]] = None,
    check_quant: bool = True,
    read_source: Optional[
        Callable[[str, List[str], Optional[Document]], Awaitable["ReadSourceResult"]]
    ] = None,
    import_max_depth: int = 10,
) -> Document:
    """
    Async version of :func:`load`, with all the same arguments
    """
    doc = await Tree._load_async(
        uri,
        path=path,
        check_quant=check_quant,
        read_source=read_source,
        import_max_depth=import_max_depth,
    )
    Walker.SetParents()(doc)
    return doc


async def read_source_default(
    uri: str, path: List[str], importer: Optional[Document]
) -> "ReadSourceResult":
    """
    Default async routine for the ``read_source`` parameter to :func:`load` and :func:`load_async`,
    which they use to read the desired WDL document and its imports. This default routine handles
    local files only, supplying the search path logic to resolve relative filenames; it fails with
    network URIs.

    :param uri: Filename/URI to read, as provided to :func:`load` or the WDL import statement; may
                be relative
    :param path: Local directories to search for relative imports
    :param importer: The document importing the one here requested, if any; the
                     ``importer.pos.uri`` and ``importer.pos.abspath`` fields may be relevant to
                     resolve relative imports.
    :returns: ``WDL.ReadSourceResult(source_text="...", abspath="...")``

    The returned ``NamedTuple`` provides the WDL source code and the absolute filename/URI from
    which the source was read (e.g. after resolving a relative path).

    Callers may wish to override ``read_source`` with logic to download source code from network
    URIs, and for local filenames fall back to ``return await WDL.read_source_default(...)``.

    Note: the synchronous :func:`load` merely calls :func:`load_async` on the current
    ``asyncio.get_event_loop()`` and awaits the result.
    """
    return await Tree.read_source_default(uri, path, importer)


async def resolve_file_import(uri: str, path: List[str], importer: Optional[Document]) -> str:
    """
    Exposes the logic by which :func:`read_source_default` resolves ``uri`` to the absolute path of
    an extant file. If ``uri`` is already an absolute path, it's normalized and returned. A
    relative ``uri`` is resolved by first joining it to either, the directory of the importer
    document (if any), or the process current working directory (otherwise). Failing that, it's
    searched in the ``path`` directories (in reverse order).

    Security-focused applications may wish to override ``read_source`` with logic to restrict
    allowable results of ``resolve_file_import``, to prevent WDL source code from triggering access
    to arbitrary filesystem paths. No such restrictions are applied by default.
    """
    return await Tree.resolve_file_import(uri, path, importer)


def copy_source(doc: Document, dir: str) -> str:
    """"""
    """
    Copy the original WDL document source, and any imports, into the specified directory. Ignores
    any imports using absolute file paths or URIs.

    Returns the path to the copy of the given document, which possibly could be nested in a
    subdirectory if it uses .. relative imports.
    """
    # make list of all docs to save
    docs = []
    queue = [doc]
    while queue:
        a_doc = queue.pop()
        docs.append(a_doc)
        for imp in a_doc.imports:
            if (
                not imp.uri.startswith("http:")
                and not imp.uri.startswith("https:")
                and not os.path.isabs(imp.uri)
            ):
                assert imp.doc
                queue.append(imp.doc)
    # find longest common prefix (up to a '/') among docs' pos.abspath (note these could be URIs!)
    lcp = os.path.dirname(os.path.commonprefix([a_doc.pos.abspath for a_doc in docs]))
    # write each doc text out under dir, its abspath without lcp
    ans = None
    for a_doc in docs:
        assert a_doc.pos.abspath.startswith(lcp)
        rp = a_doc.pos.abspath[len(lcp) :].lstrip("/")
        fn = os.path.join(dir, rp)
        os.makedirs(os.path.dirname(fn), exist_ok=True)
        _util.write_atomic(a_doc.source_text, fn, end="")
        if a_doc is doc:
            assert not ans
            ans = fn
    assert ans
    return ans


def parse_document(txt: str, version: Optional[str] = None, uri: str = "") -> Document:
    """"""
    """
    Parse WDL document text into an abstract syntax tree. Doesn't descend into
    imported documents nor typecheck the AST.

    :param version:
        Override the WDL language version, such as "1.0" or "draft-2". (By default, detects from the "version" string
        at the beginning of the document, per the WDL spec.)

    :param uri: filename/URI for error reporting (not otherwise used)
    """
    doc = _parser.parse_document(txt, version, uri)
    Walker.SetParents()(doc)
    return doc


def parse_expr(txt: str, version: Optional[str] = None) -> Expr.Base:
    """"""
    """
    Parse an isolated WDL expression text into an abstract syntax tree
    """
    return _parser.parse_expr(txt, version)


def parse_tasks(txt: str, version: Optional[str] = None) -> List[Task]:
    return _parser.parse_tasks(txt, version)


def values_from_json(
    values_json: Dict[str, Any],
    available: Union[Env.Bindings[Tree.Decl], Env.Bindings[Type.Base]],
    required: Optional[Union[Env.Bindings[Tree.Decl], Env.Bindings[Type.Base]]] = None,
    namespace: str = "",
) -> Env.Bindings[Value.Base]:
    """
    Given a dict parsed from Cromwell-style JSON and the available input (or
    output) declarations of a task or workflow, create a
    ``WDL.Env.Bindings[Value.Base]``.

    :param required: raise an error if any of these required inputs aren't
                     present
    :param namespace: expect each key to start with this namespace prefixed to
                      the input/output names (e.g. the workflow name)
    """
    if namespace and not namespace.endswith("."):
        namespace += "."
    ans: Env.Bindings[Value.Base] = Env.Bindings()
    for key in values_json:
        if not key.startswith("#"):  # ignore "comments"
            key2 = key
            if namespace and key.startswith(namespace):
                key2 = key[len(namespace) :]

            ty = None
            if key2 in available:
                ty = available[key2]
            else:
                key2parts = key2.split(".")

                runtime_idx = next(
                    (i for i, term in enumerate(key2parts) if term in ("runtime",)), -1
                )
                if (
                    runtime_idx >= 0
                    and len(key2parts) > (runtime_idx + 1)
                    and ".".join(key2parts[:runtime_idx] + ["_runtime"]) in available
                ):
                    # allow arbitrary keys for runtime
                    ty = Type.Any()
                elif len(key2parts) == 3 and key2parts[0] and key2parts[1] and key2parts[2]:
                    # attempt to simplify <call>.<subworkflow>.<input> from old Cromwell JSON
                    key2 = ".".join([key2parts[0], key2parts[2]])
                    if key2 in available:
                        ty = available[key2]
            if not ty:
                raise Error.InputError("unknown input/output: " + key) from None
            if isinstance(ty, Tree.Decl):
                # treat input with default as optional, with or without the ? type quantifier
                ty = ty.type.copy(optional=True) if ty.expr else ty.type

            assert isinstance(ty, Type.Base)
            try:
                v = Value.from_json(ty, values_json[key])
                try:
                    v.type.check(ty)
                except Exception:
                    assert False  # just a sanity test of Value.from_json
                ans = ans.bind(key2, v)
            except Error.InputError as exn:
                raise Error.InputError(exn.args[0] + f" (in {key})").with_traceback(
                    sys.exc_info()[2]
                )
    if required:
        missing = required.subtract(ans)
        if missing:
            raise Error.InputError(
                "missing required inputs/outputs: " + ", ".join(values_to_json(missing))  # type: ignore
            )
    return ans


def values_to_json(
    values_env: Union[Env.Bindings[Value.Base], Env.Bindings[Tree.Decl], Env.Bindings[Type.Base]],
    namespace: str = "",
) -> Dict[str, Any]:
    """
    Convert a ``WDL.Env.Bindings[WDL.Value.Base]`` to a dict which ``json.dumps`` to
    Cromwell-style JSON.

    :param namespace: prefix this namespace to each key (e.g. workflow name)
    """
    # also can be used on Env.Bindings[Tree.Decl] or Env.Types, then the right-hand side of
    # each entry will be the type string.
    if namespace and not namespace.endswith("."):
        namespace += "."
    ans = {}
    for item in values_env:
        v = item.value
        if isinstance(v, Value.Base):
            j = v.json
        elif isinstance(item.value, Tree.Decl):
            j = str(item.value.type)
        else:
            assert isinstance(item.value, Type.Base)
            j = str(item.value)
        ans[(namespace if not item.name.startswith("_") else "") + item.name] = j
    return ans
