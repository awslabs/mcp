import inspect
import threading
import regex
from typing import List, Optional, Set, Tuple, Any, Union
import lark
from .Error import SourcePosition
from . import Error, Tree, Type, Expr, _grammar

# memoize Lark parsers constructed for version & start symbol
_lark_cache = {}
_lark_comments_buffer: List[lark.Token] = []
_lark_lock = threading.Lock()


def parse(grammar: str, txt: str, start: str) -> Tuple[lark.Tree, List[lark.Token]]:
    with _lark_lock:
        assert not _lark_comments_buffer
        try:
            if (grammar, start) not in _lark_cache:
                _lark_cache[(grammar, start)] = lark.Lark(
                    grammar,
                    start=start,
                    parser="lalr",
                    maybe_placeholders=False,
                    propagate_positions=True,
                    lexer_callbacks={"COMMENT": _lark_comments_buffer.append},
                )
            tree = _lark_cache[(grammar, start)].parse(
                txt + ("\n" if not txt.endswith("\n") else "")
            )
            comments = _lark_comments_buffer.copy()
            return (tree, comments)
        finally:
            # Wipe temp state (success or fail). It receives the side-effects of lark's
            # lexer_callbacks, which we have to bind before memoizing the parser object.
            _lark_comments_buffer.clear()


def to_int(x):
    return int(x)


def to_float(x):
    return float(x)


class _SourcePositionTransformerMixin:
    def __init__(self, uri: str = "(buffer)", abspath: str = "(buffer)", *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.uri = uri
        self.abspath = abspath

    def _sp(self, meta):
        return SourcePosition(
            uri=self.uri,
            abspath=self.abspath,
            line=meta.line,
            column=meta.column,
            end_line=meta.end_line,
            end_column=meta.end_column,
        )


# Transformer from lark.Tree to WDL.Expr
class _ExprTransformer(_SourcePositionTransformerMixin, lark.Transformer):
    # pylint: disable=no-self-use,unused-argument

    def boolean_true(self, meta, items) -> Expr.Base:
        assert not items
        return Expr.Boolean(self._sp(meta), True)

    def boolean_false(self, meta, items) -> Expr.Base:
        assert not items
        return Expr.Boolean(self._sp(meta), False)

    def null(self, meta, items) -> Expr.Base:
        assert not items
        return Expr.Null(self._sp(meta))

    def int(self, meta, items) -> Expr.Base:
        assert len(items) == 1
        return Expr.Int(self._sp(meta), to_int(items[0]))

    def float(self, meta, items) -> Expr.Base:
        assert len(items) == 1
        return Expr.Float(self._sp(meta), to_float(items[0]))

    def string(self, meta, items) -> Expr.Base:
        parts: List[Union[str, Expr.Placeholder]] = []
        for item in items:
            if isinstance(item, Expr.Placeholder):
                parts.append(item)
            elif isinstance(item, Expr.Base):
                parts.append(Expr.Placeholder(item.pos, {}, item))
            else:
                # validate escape sequences...
                Expr.String._decode_escapes(self._sp(meta), item.value)
                # ...but preserve originals in AST.
                parts.append(item.value)
        assert len(parts) >= 2
        assert parts[0] in ['"', "'", "<<<"], parts[0]
        assert parts[-1] in ['"', "'", ">>>"], parts[-1]
        if parts[0] == "<<<":
            wdl_version = getattr(self, "_version", None)
            if wdl_version and wdl_version != "development":
                raise Error.SyntaxError(
                    self._sp(meta),
                    "<<< multi-line strings >>> are not supported in this WDL version",
                    wdl_version,
                    None,
                ) from None
            return Expr.MultiLineString(self._sp(meta), parts)
        return Expr.String(self._sp(meta), parts)

    def placeholder_option(self, meta, items):
        assert len(items) == 2
        if items[0].value not in ("default", "false", "true", "sep"):
            raise Error.ValidationError(self._sp(meta), "unknown placeholder option")
        return (items[0].value, items[1])

    def placeholder(self, meta, items):
        options = dict(items[:-1])
        if len(options.items()) < len(items) - 1:
            raise Error.MultipleDefinitions(
                self._sp(meta), "duplicate options in expression placeholder"
            )
        return Expr.Placeholder(self._sp(meta), options, items[-1])

    def string_literal(self, meta, items):
        assert len(items) == 1
        assert items[0].value.startswith('"') or items[0].value.startswith("'")
        return Expr.String._decode_escapes(self._sp(meta), items[0].value[1:-1])

    def array(self, meta, items) -> Expr.Base:
        return Expr.Array(self._sp(meta), items)

    def apply(self, meta, items) -> Expr.Base:
        assert len(items) >= 1
        assert not items[0].startswith("_")  # TODO enforce in grammar
        return Expr.Apply(self._sp(meta), items[0], items[1:])

    def negate(self, meta, items) -> Expr.Base:
        return Expr.Apply(self._sp(meta), "_negate", items)

    def at(self, meta, items) -> Expr.Base:
        return Expr.Apply(self._sp(meta), "_at", items)

    def pair(self, meta, items) -> Expr.Base:
        assert len(items) == 2
        return Expr.Pair(self._sp(meta), items[0], items[1])

    def map_kv(self, meta, items):
        assert len(items) == 2
        return (items[0], items[1])

    def map(self, meta, items) -> Expr.Base:
        return Expr.Map(self._sp(meta), items)

    def object_kv(self, meta, items):
        assert len(items) == 2
        k = items[0]
        if isinstance(k, lark.Token):
            k = k.value
        assert isinstance(k, str), k
        assert isinstance(items[1], Expr.Base)
        return (k, items[1])

    def obj(self, meta, items) -> Expr.Base:
        if not items or isinstance(items[0], tuple):  # old-style "object" literal
            return Expr.Struct(self._sp(meta), items)
        return Expr.Struct(self._sp(meta), items[1:], (items[0] if items[0] != "object" else None))

    def ifthenelse(self, meta, items) -> Expr.Base:
        assert len(items) == 3
        return Expr.IfThenElse(self._sp(meta), *items)

    def left_name(self, meta, items) -> Expr.Base:
        assert len(items) == 1 and isinstance(items[0], str)
        return Expr.Get(self._sp(meta), Expr._LeftName(self._sp(meta), items[0]), None)

    def get_name(self, meta, items) -> Expr.Base:
        assert (
            len(items) == 2 and isinstance(items[0], Expr.Base) and isinstance(items[1].value, str)
        )
        return Expr.Get(self._sp(meta), items[0], items[1].value)


# _ExprTransformer infix operators
for op in [
    "land",
    "lor",
    "add",
    "sub",
    "mul",
    "div",
    "rem",
    "eqeq",
    "neq",
    "lt",
    "lte",
    "gt",
    "gte",
]:

    def fn(self, meta, items, op=op):
        assert len(items) == 2
        return Expr.Apply(self._sp(meta), "_" + op, items)

    setattr(_ExprTransformer, op, lark.v_args(meta=True)(fn))


class _DocTransformer(_ExprTransformer):
    # pylint: disable=no-self-use,unused-argument

    _keywords: Set[str]
    _source_text: str
    _comments: List[lark.Token]
    _version: Optional[str]
    _declared_version: Optional[str]

    def __init__(
        self,
        source_text: str,
        keywords: Set[str],
        comments: List[lark.Token],
        version: str,
        declared_version: Optional[str],
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self._source_text = source_text
        self._keywords = keywords
        self._comments = comments
        self._version = version
        self._declared_version = declared_version

    def _check_keyword(self, pos, name):
        if name in self._keywords:
            raise Error.SyntaxError(
                pos, "unexpected keyword {}".format(name), self._version, self._declared_version
            )

    def object_kv(self, meta, items):
        ans = super().object_kv(meta, items)
        self._check_keyword(self._sp(meta), ans[0])
        return ans

    def obj(self, meta, items) -> Expr.Base:
        if items and isinstance(items[0], str) and items[0] != "object":
            self._check_keyword(self._sp(meta), items[0])
        return super().obj(meta, items)

    def left_name(self, meta, items) -> Expr.Base:
        ans = super().left_name(meta, items)
        self._check_keyword(ans.pos, items[0])
        return ans

    def get_name(self, meta, items) -> Expr.Base:
        ans = super().get_name(meta, items)
        if items[1] not in ("left", "right"):
            self._check_keyword(ans.pos, items[1])
        return ans

    def optional(self, meta, items):
        return set(["optional"])

    def nonempty(self, meta, items):
        return set(["nonempty"])

    def optional_nonempty(self, meta, items):
        return set(["optional", "nonempty"])

    def type(self, meta, items):
        quantifiers = set()
        if len(items) > 1 and isinstance(items[-1], set):
            quantifiers = items.pop()
        param = items[1] if len(items) > 1 else None
        param2 = items[2] if len(items) > 2 else None

        if items[0].value == "Array":
            if not param or param2:
                raise Error.InvalidType(self._sp(meta), "Array must have one type parameter")
            if quantifiers - set(["optional", "nonempty"]):
                raise Error.ValidationError(self._sp(meta), "invalid type quantifier(s) for Array")
            ans = Type.Array(param, "optional" in quantifiers, "nonempty" in quantifiers)
            ans.pos = self._sp(meta)
            return ans
        if "nonempty" in quantifiers:
            raise Error.InvalidType(
                self._sp(meta), "invalid type quantifier(s) for " + items[0].value
            )

        atomic_types = {
            "Int": Type.Int,
            "Float": Type.Float,
            "Boolean": Type.Boolean,
            "String": Type.String,
            "File": Type.File,
        }
        if self._version not in ("draft-2", "1.0", "1.1"):
            atomic_types["Directory"] = Type.Directory
        if items[0].value in atomic_types:
            if param or param2:
                raise Error.InvalidType(
                    self._sp(meta), items[0] + " type doesn't accept parameters"
                )
            ans = atomic_types[items[0].value]("optional" in quantifiers)
            ans.pos = self._sp(meta)
            return ans

        if items[0].value == "Map":
            if not (param and param2):
                raise Error.InvalidType(self._sp(meta), "Map must have two type parameters")
            ans = Type.Map((param, param2), "optional" in quantifiers)
            ans.pos = self._sp(meta)
            return ans

        if items[0].value == "Pair":
            if not (param and param2):
                raise Error.InvalidType(self._sp(meta), "Pair must have two type parameters")
            ans = Type.Pair(param, param2, "optional" in quantifiers)
            ans.pos = self._sp(meta)
            return ans

        if param or param2:
            raise Error.InvalidType(self._sp(meta), "Unexpected type parameter(s)")

        ans = Type.StructInstance(items[0].value, "optional" in quantifiers)
        ans.pos = self._sp(meta)
        return ans

    def decl(self, meta, items):
        self._check_keyword(self._sp(meta), items[1].value)
        return Tree.Decl(
            self._sp(meta), items[0], items[1].value, (items[2] if len(items) > 2 else None)
        )

    def task_env_decl(self, meta, items):
        if len(items) == 2:
            assert items[0].value == "env"
            assert isinstance(items[1], Tree.Decl)
            items[1].decor["env"] = True
            return items[1]
        assert len(items) == 1 and isinstance(items[0], Tree.Decl)
        return items[0]

    def input_decls(self, meta, items):
        return {"inputs": items}

    def noninput_decl(self, meta, items):
        return {"noninput_decl": items[0]}

    def command(self, meta, items):
        parts = []
        for item in items:
            if isinstance(item, Expr.Placeholder):
                parts.append(item)
            else:
                parts.append(item.value)
        return {"command": Expr.TaskCommand(self._sp(meta), parts)}

    def output_decls(self, meta, items):
        return {"outputs": items}

    def meta_kv(self, meta, items):
        return (items[0].value, items[1])

    def meta_object(self, meta, items):
        d = dict()
        for k, v in items:
            if k in d:
                raise Error.MultipleDefinitions(self._sp(meta), "duplicate keys in meta object")
            d[k] = v
        return d

    def meta_array(self, meta, items):
        return items

    def meta_section(self, meta, items):
        kind = items[0].value
        assert kind in ["meta", "parameter_meta"]
        d = dict()
        d[kind] = items[1]
        return d

    def runtime_kv(self, meta, items):
        return (items[0].value, items[1])

    def runtime_section(self, meta, items):
        d = dict()
        for k, v in items:
            # TODO: restore duplicate check, cf. https://github.com/gatk-workflows/five-dollar-genome-analysis-pipeline/blob/89f11befc13abae97ab8fb1b457731f390c8728d/tasks_pipelines/qc.wdl#L288  # noqa
            # if k in d:
            #    raise Error.MultipleDefinitions(self._sp(meta), "duplicate keys in runtime section")
            d[k] = v
        return {"runtime": d}

    def task(self, meta, items):
        d = {"noninput_decls": []}
        for item in items:
            if isinstance(item, dict):
                for k, v in item.items():
                    if k == "noninput_decl":
                        d["noninput_decls"].append(v)
                    elif k in d:
                        raise Error.MultipleDefinitions(
                            self._sp(meta), "redundant sections in task"
                        )
                    else:
                        d[k] = v
            else:
                assert isinstance(item, str)
                assert "name" not in d
                d["name"] = item.value
        self._check_keyword(self._sp(meta), d["name"])
        return Tree.Task(
            self._sp(meta),
            d["name"],
            d.get("inputs", None),
            d["noninput_decls"],
            d["command"],
            d.get("outputs", []),
            d.get("parameter_meta", {}),
            d.get("runtime", {}),
            d.get("meta", {}),
        )

    def tasks(self, meta, items):
        return items

    def namespaced_ident(self, meta, items) -> List[str]:
        assert items
        return [item.value for item in items]

    def call_input(self, meta, items):
        if len(items) > 1:
            return (items[0].value, items[1])
        return (items[0].value, Expr.Ident(self._sp(meta), items[0].value))

    def input_colon(self, meta, items):
        return "input:"

    def call_inputs(self, meta, items):
        d = dict()
        if items:
            input_colon = False
            if isinstance(items[0], str) and items[0] == "input:":
                input_colon = True
                items = items[1:]
            if self._version == "1.1" and not input_colon:
                raise Error.SyntaxError(
                    self._sp(meta),
                    "WDL 1.1 calls require input: keyword",
                    self._version,
                    self._declared_version,
                )
        for k, v in items:
            if k in d:
                raise Error.MultipleDefinitions(self._sp(meta), f"duplicate call input '{k}'")
            d[k] = v
        return d

    def call(self, meta, items):
        after = []
        i = 1
        while i < len(items):
            if isinstance(items[i], lark.Token):
                after.append(items[i].value)
            else:
                break
            i += 1
        assert i == len(items) or isinstance(items[i], dict)
        return Tree.Call(
            self._sp(meta), items[0], None, items[i] if i < len(items) else dict(), after=after
        )

    def call_as(self, meta, items):
        self._check_keyword(self._sp(meta), items[1].value)
        after = list()
        i = 2
        while i < len(items):
            if isinstance(items[i], lark.Token):
                after.append(items[i].value)
            else:
                break
            i += 1
        assert i == len(items) or isinstance(items[i], dict)
        return Tree.Call(
            self._sp(meta),
            items[0],
            items[1].value,
            items[i] if i < len(items) else dict(),
            after=after,
        )

    def scatter(self, meta, items):
        self._check_keyword(self._sp(meta), items[0].value)
        return Tree.Scatter(self._sp(meta), items[0].value, items[1], items[2:])

    def conditional(self, meta, items):
        return Tree.Conditional(self._sp(meta), items[0], items[1:])

    def workflow_wildcard_output(self, meta, items):
        return items[0] + ["*"]
        # return Expr.Ident(items[0].pos, items[0].namespace + [items[0].name, "*"])

    def workflow_output_decls(self, meta, items):
        decls = [elt for elt in items if isinstance(elt, Tree.Decl)]
        idents = [elt for elt in items if isinstance(elt, list)]
        assert len(decls) + len(idents) == len(items)
        return {"outputs": decls, "output_idents": idents, "pos": self._sp(meta)}

    def workflow(self, meta, items):
        elements = []
        inputs = None
        outputs = None
        output_idents = None
        output_idents_pos = None
        parameter_meta = None
        meta_section = None
        for item in items[1:]:
            if isinstance(item, dict):
                if "inputs" in item:
                    if inputs is not None:
                        raise Error.MultipleDefinitions(
                            self._sp(meta), "redundant workflow input sections"
                        )
                    inputs = item["inputs"]
                elif "outputs" in item:
                    if outputs is not None:
                        raise Error.MultipleDefinitions(
                            self._sp(meta), "redundant workflow output sections"
                        )
                    outputs = item["outputs"]
                    if "output_idents" in item:
                        assert output_idents is None
                        output_idents = item["output_idents"]
                        output_idents_pos = item["pos"]
                elif "meta" in item:
                    if meta_section is not None:
                        raise Error.MultipleDefinitions(
                            self._sp(meta), "redundant workflow meta sections"
                        )
                    meta_section = item["meta"]
                elif "parameter_meta" in item:
                    if parameter_meta is not None:
                        raise Error.MultipleDefinitions(
                            self._sp(meta), "redundant workflow parameter_meta sections"
                        )
                    parameter_meta = item["parameter_meta"]
                else:
                    assert False
            elif isinstance(item, (Tree.Call, Tree.Conditional, Tree.Decl, Tree.Scatter)):
                elements.append(item)
            else:
                assert False
        self._check_keyword(self._sp(meta), items[0].value)
        return Tree.Workflow(
            self._sp(meta),
            items[0].value,
            inputs,
            elements,
            outputs,
            parameter_meta or dict(),
            meta_section or dict(),
            output_idents,
            output_idents_pos,
        )

    def struct(self, meta, items):
        assert len(items) >= 1
        name = items[0]
        self._check_keyword(self._sp(meta), name)
        members = {}
        for d in items[1:]:
            assert not d.expr
            if d.name in members:
                raise Error.MultipleDefinitions(
                    self._sp(meta), f"duplicate struct member '{d.name}'"
                )
            members[d.name] = d.type
        return Tree.StructTypeDef(self._sp(meta), name, members)

    def import_alias(self, meta, items):
        assert len(items) == 2
        self._check_keyword(self._sp(meta), items[1].value)
        return (items[0].value, items[1].value)

    def import_doc(self, meta, items):
        pos = self._sp(meta)
        uri = items[0]
        if len(items) > 1 and isinstance(items[1], str):
            namespace = items[1].value
        else:
            # infer namespace from filename/URI
            namespace = uri
            try:
                namespace = namespace[namespace.rindex("/") + 1 :]
            except ValueError:
                pass
            namespace = namespace.split("?")[0].split(".")[0]
        if not regex.fullmatch("[a-zA-Z][a-zA-Z0-9_]*", namespace) or namespace in self._keywords:
            raise Error.SyntaxError(
                pos,
                """declare an import namespace that follows WDL name rules and isn't a language keyword """
                """(import "filename" as some_namespace)""",
                self._version,
                self._declared_version,
            )
        aliases = [p for p in items[1:] if isinstance(p, tuple)]
        return Tree.DocImport(pos=pos, uri=uri, namespace=namespace, aliases=aliases, doc=None)

    def document(self, meta, items):
        imports = []
        structs = {}
        tasks = []
        workflow = None
        for item in items:
            if isinstance(item, Tree.Task):
                tasks.append(item)
            elif isinstance(item, Tree.Workflow):
                if workflow is not None:
                    raise Error.MultipleDefinitions(
                        self._sp(meta), "Document has multiple workflows"
                    )
                workflow = item
            elif isinstance(item, Tree.StructTypeDef):
                if item.name in structs:
                    raise Error.MultipleDefinitions(
                        self._sp(meta), "multiple structs named " + item.name
                    )
                structs[item.name] = item
            elif isinstance(item, lark.Tree) and item.data == "version":
                pass
            elif isinstance(item, Tree.DocImport):
                imports.append(item)
            else:
                assert False
        comments = [
            Tree.SourceComment(
                SourcePosition(
                    uri=self.uri,
                    abspath=self.abspath,
                    line=comment.line,
                    column=comment.column,
                    end_line=comment.end_line or comment.line,
                    end_column=comment.end_column or (comment.column + len(comment.value)),
                ),
                text=comment.value,
            )
            for comment in self._comments
        ]

        return Tree.Document(
            self._source_text,
            self._sp(meta),
            imports,
            structs,
            tasks,
            workflow,
            comments,
            self._declared_version,
        )


# have lark pass the 'meta' with line/column numbers to each transformer method
for _klass in [_ExprTransformer, _DocTransformer]:
    for name, method in inspect.getmembers(_klass, inspect.isfunction):
        if not name.startswith("_"):
            setattr(_klass, name, lark.v_args(meta=True)(method))


def parse_expr(txt: str, version: Optional[str] = None) -> Expr.Base:
    version = version or "1.0"
    try:
        xformer = _ExprTransformer()
        setattr(xformer, "_version", version)
        return xformer.transform(parse(_grammar.get(version)[0], txt, "expr")[0])
    except lark.exceptions.UnexpectedInput as exn:
        pos = SourcePosition(
            uri="(buffer)",
            abspath="(buffer)",
            line=getattr(exn, "line", 0),
            column=getattr(exn, "column", 0),
            end_line=getattr(exn, "line", 0),
            end_column=getattr(exn, "column", 0),
        )
        raise Error.SyntaxError(pos, str(exn), version, None) from None
    except lark.exceptions.VisitError as exn:
        exn2 = exn.__context__ or exn
        if isinstance(exn2, Error._BadCharacterEncoding):
            raise Error.SyntaxError(
                exn2.pos,
                "Bad escape sequence in string literal",
                version,
                None,
            ) from None
        # attach WDL version info to all parser exceptions (not just SyntaxError)
        setattr(exn2, "wdl_version", version)
        setattr(exn2, "declared_wdl_version", None)
        raise exn2 from None


def _parse_doctransformer(
    terminal: str,
    txt: str,
    version: str,
    declared_version: Optional[str] = None,
    uri: str = "",
    abspath: str = "",
) -> Any:
    npos = SourcePosition(uri=uri, abspath=abspath, line=0, column=0, end_line=0, end_column=0)
    try:
        (grammar, keywords) = _grammar.get(version)
    except KeyError:
        raise Error.SyntaxError(
            npos,
            f"unknown WDL version {version}; choices: " + ", ".join(_grammar.versions.keys()),
            version,
            declared_version,
        ) from None
    try:
        raw_ast, comments = parse(grammar, txt, terminal)
        return _DocTransformer(
            source_text=txt,
            uri=uri,
            abspath=abspath,
            keywords=keywords,
            comments=comments,
            version=version,
            declared_version=declared_version,
        ).transform(raw_ast)
    except lark.exceptions.UnexpectedInput as exn:
        pos = SourcePosition(
            uri=(uri if uri else "(buffer)"),
            abspath=(abspath if abspath else "(buffer)"),
            line=getattr(exn, "line", 0),
            column=getattr(exn, "column", 0),
            end_line=getattr(exn, "line", 0),
            end_column=getattr(exn, "column", 0),
        )
        raise Error.SyntaxError(pos, str(exn), version, declared_version) from None
    except lark.exceptions.VisitError as exn:
        exn2 = exn.__context__ or exn
        if isinstance(exn2, Error._BadCharacterEncoding):
            raise Error.SyntaxError(
                exn2.pos,
                "Bad escape sequence in string literal",
                version,
                declared_version,
            ) from None
        # attach WDL version info to all parser exceptions (not just SyntaxError)
        setattr(exn2, "wdl_version", version)
        setattr(exn2, "declared_wdl_version", declared_version)
        raise exn2 from None


def parse_tasks(txt: str, version: Optional[str] = None) -> List[Tree.Task]:
    return _parse_doctransformer("tasks", txt, version or "draft-2")


def parse_bound_decl(txt: str, version: Optional[str] = None) -> Tree.Decl:
    return _parse_doctransformer("bound_decl", txt, version or "draft-2")


def parse_document(
    txt: str, version: Optional[str] = None, uri: str = "", abspath: str = ""
) -> Tree.Document:
    npos = SourcePosition(uri=uri, abspath=abspath, line=0, column=0, end_line=0, end_column=0)
    if not txt.strip():
        return Tree.Document(txt, npos, [], {}, [], None, [], None)
    declared_version = None
    for line in txt.split("\n"):
        line = line.strip()
        if line and line[0] != "#":
            if line.startswith("version "):
                declared_version = line[8:]
            break
    version = version or declared_version or "draft-2"
    assert isinstance(version, str)
    return _parse_doctransformer(
        "document", txt, version, declared_version=declared_version, uri=uri, abspath=abspath
    )
