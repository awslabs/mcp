from typing import Optional, Tuple, Set

# We share the following productions between the grammars for draft-2 and 1.0; this maximizes test
# coverage.
productions_common1 = r"""
///////////////////////////////////////////////////////////////////////////////////////////////////
// document
///////////////////////////////////////////////////////////////////////////////////////////////////

document: version? document_element*
        | version? document_element*

version: "version" /[^ \t\r\n]+/
import_alias: "alias" CNAME "as" CNAME
import_doc: "import" string_literal ["as" CNAME] import_alias*

///////////////////////////////////////////////////////////////////////////////////////////////////
// workflow
///////////////////////////////////////////////////////////////////////////////////////////////////

workflow: "workflow" CNAME "{" workflow_element* "}"
?workflow_element: input_decls | any_decl | call | scatter | conditional | workflow_outputs | meta_section

scatter: "scatter" "(" CNAME "in" expr ")" "{" inner_workflow_element* "}"
conditional: "if" "(" expr ")" "{" inner_workflow_element* "}"
?inner_workflow_element: any_decl | call | scatter | conditional

call: "call" namespaced_ident _call_body? -> call
    | "call" namespaced_ident "as" CNAME _call_body? -> call_as
namespaced_ident: CNAME ("." CNAME)*
call_inputs: "input" ":" [call_input ("," call_input)*] ","?
_call_body: "{" call_inputs? "}"
call_input: CNAME "=" expr

///////////////////////////////////////////////////////////////////////////////////////////////////
// task
///////////////////////////////////////////////////////////////////////////////////////////////////

task: "task" CNAME "{" task_section* command task_section* "}"
?task_section: input_decls
             | output_decls
             | meta_section
             | runtime_section
             | any_decl -> noninput_decl

tasks: task*

input_decls: "input" "{" any_decl* "}"
output_decls: "output" "{" bound_decl* "}"

// WDL task commands: with {} and <<< >>> command and ${} and ~{} placeholder styles
!?placeholder_key: "default" | "false" | "true" | "sep"
?placeholder_value: string_literal
                  | INT -> int
                  | FLOAT -> float
placeholder_option: placeholder_key "=" placeholder_value
placeholder: placeholder_option* expr

?command: command1 | command2

// meta/parameter_meta sections (effectively JSON)
meta_object: "{" [meta_kv (","? meta_kv)*] "}"
meta_kv: CNAME ":" meta_value
?meta_value: literal | string_literal
           | meta_object
           | "[" [meta_value ("," meta_value)*] "]" -> meta_array
!meta_section: ("meta" | "parameter_meta") meta_object

// task runtime section (key-expression pairs)
runtime_section: "runtime" "{" [runtime_kv (","? runtime_kv)*] "}"
runtime_kv: CNAME ":" expr

///////////////////////////////////////////////////////////////////////////////////////////////////
// decl
///////////////////////////////////////////////////////////////////////////////////////////////////

unbound_decl: type CNAME -> decl
bound_decl: type CNAME "=" expr -> decl
?any_decl: unbound_decl | bound_decl

///////////////////////////////////////////////////////////////////////////////////////////////////
// type
///////////////////////////////////////////////////////////////////////////////////////////////////

_quant: optional | nonempty | optional_nonempty
optional: "?"
nonempty: "+"
optional_nonempty: "+?"


CNAME: /[a-zA-Z][a-zA-Z0-9_]*/
COMMENT: /[ \t]*/ "#" /[^\r\n]*/
SPACE: /[ \t]+/

%import common.INT
%import common.SIGNED_INT
%import common.FLOAT
%import common.SIGNED_FLOAT
%import common.ESCAPED_STRING
%import common.NEWLINE
%ignore SPACE
%ignore NEWLINE
%ignore COMMENT

///////////////////////////////////////////////////////////////////////////////////////////////////
// expr
///////////////////////////////////////////////////////////////////////////////////////////////////

?expr: expr_infix

?expr_infix: expr_infix0

?expr_infix0: expr_infix0 "||" expr_infix1 -> lor
            | expr_infix1

?expr_infix1: expr_infix1 "&&" expr_infix2 -> land
            | expr_infix2

?expr_infix2: expr_infix2 "==" expr_infix3 -> eqeq
            | expr_infix2 "!=" expr_infix3 -> neq
            | expr_infix2 "<=" expr_infix3 -> lte
            | expr_infix2 ">=" expr_infix3 -> gte
            | expr_infix2 "<" expr_infix3 -> lt
            | expr_infix2 ">" expr_infix3 -> gt
            | expr_infix3

?expr_infix3: expr_infix3 "+" expr_infix4 -> add
            | expr_infix3 "-" expr_infix4 -> sub
            | expr_infix4

?expr_infix4: expr_infix4 "*" expr_infix5 -> mul
            | expr_infix4 "/" expr_infix5 -> div
            | expr_infix4 "%" expr_infix5 -> rem
            | expr_infix5

?expr_infix5: expr_core

?literal: "true"-> boolean_true
        | "false" -> boolean_false
        | INT -> int
        | SIGNED_INT -> int
        | FLOAT -> float
        | SIGNED_FLOAT -> float

?string: string1 | string2

_DOUBLE_BACKSLASH.2: "\\\\"
STRING_INNER1: (_DOUBLE_BACKSLASH|"\\'"|/[^']/)
ESCAPED_STRING1: "'" STRING_INNER1* "'"
string_literal: ESCAPED_STRING | ESCAPED_STRING1

?map_key: expr_core
map_kv: map_key ":" expr

// expression core (everything but infix)
// we stuck this last down here so that further language-version-specific
// productions can be added below
?expr_core: "(" expr ")"
          | literal
          | string
          | "!" expr_core -> negate

          | "[" [expr ("," expr)*] ","? "]" -> array
          | expr_core "[" expr "]" -> at

          | "(" expr "," expr ")" -> pair
          | "{" [map_kv ("," map_kv)*] ","? "}" -> map

          | "if" expr "then" expr "else" expr -> ifthenelse

          | CNAME "(" [expr ("," expr)*] ")" -> apply

          | CNAME -> left_name
          | expr_core "." CNAME -> get_name
"""

# draft-2 specific productions:
# - predefined types only
# - interpolated strings and { } and <<< >>> command styles all have placeholders delimited by ${ }
# - workflow outputs can be bare identifiers rather than complete decls
productions_pre_1_0 = r"""
// WDL types
type: BUILTIN_TYPE _quant?
      | BUILTIN_TYPE "[" type ["," type] "]" _quant?
BUILTIN_TYPE.2: "Int" | "Float" | "Boolean" | "String" | "File" | "Array" | "Map" | "Pair"

// string (single-quoted)
STRING1_CHAR: _DOUBLE_BACKSLASH | "\\'" | /[^'$]/ | /\$(?=[^{])/
STRING1_FRAGMENT: STRING1_CHAR+
string1: /'/ (STRING1_FRAGMENT? "${" expr "}")* STRING1_FRAGMENT? /'/ -> string

// string (double-quoted)
STRING2_CHAR: _DOUBLE_BACKSLASH | "\\\"" | /[^"$]/ |  /\$(?=[^{])/
STRING2_FRAGMENT: STRING2_CHAR+
string2: /"/ (STRING2_FRAGMENT? "${" expr "}")* STRING2_FRAGMENT? /"/ -> string

COMMAND1_CHAR: /[^$}]/ | /\$(?=[^{])/
COMMAND1_FRAGMENT: COMMAND1_CHAR+
command1: "command" "{" (COMMAND1_FRAGMENT? "${" placeholder "}")* COMMAND1_FRAGMENT? "}" -> command

COMMAND2_CHAR: /[^$>]/ | /\$(?=[^{])/ | />(?=[^>])/ | />>(?=[^>])/
COMMAND2_FRAGMENT: COMMAND2_CHAR+
command2: "command" "<<<" (COMMAND2_FRAGMENT? "${" placeholder "}")* COMMAND2_FRAGMENT? ">>>" -> command

?workflow_outputs: "output" "{" workflow_output_decls "}"
workflow_output_decls: workflow_output_decl*
?workflow_output_decl: bound_decl | namespaced_ident | workflow_wildcard_output
workflow_wildcard_output: namespaced_ident "." "*" | namespaced_ident ".*"

?document_element: import_doc | task | workflow
"""

# 1.0 productions:
# - types can be any CNAME (structs)
# - within interpolated strings and { } task commands, placeholders may be delimited by ${ } or ~{ }
# - within <<< >>> commands, placeholders are delimited by ~{ } only
# - workflow outputs are complete decls
# - struct type definitions
# - struct literals (as object literals)
productions_1_0 = r"""
          | "object" "{" [object_kv ("," object_kv)* ","?] "}" -> obj // appends to expr_core

object_kv:  CNAME ":" expr
          | string_literal ":" expr

// WDL types
type: CNAME _quant?
      | CNAME "[" type ["," type] "]" _quant?

_EITHER_DELIM.2: "~{" | "${"

// string (single-quoted)
STRING1_CHAR: _DOUBLE_BACKSLASH | "\\'" | /[^'~$]/ | /\$(?=[^{])/ | /\~(?=[^{])/
STRING1_FRAGMENT: STRING1_CHAR+
string1: /'/ (STRING1_FRAGMENT? _EITHER_DELIM expr "}")* STRING1_FRAGMENT? /'/ -> string

// string (double-quoted)
STRING2_CHAR: _DOUBLE_BACKSLASH | "\\\"" | /[^"~$]/ | /\$(?=[^{])/ | /~(?=[^{])/
STRING2_FRAGMENT: STRING2_CHAR+
string2: /"/ (STRING2_FRAGMENT? _EITHER_DELIM expr "}")* STRING2_FRAGMENT? /"/ -> string

COMMAND1_CHAR: /[^~$}]/ | /\$(?=[^{])/ | /~(?=[^{])/
COMMAND1_FRAGMENT: COMMAND1_CHAR+
command1: "command" "{" (COMMAND1_FRAGMENT? _EITHER_DELIM placeholder "}")* COMMAND1_FRAGMENT? "}" -> command

COMMAND2_CHAR: /[^~>]/ | /~(?=[^{])/ | />(?=[^>])/ | />>(?=[^>])/
COMMAND2_FRAGMENT: COMMAND2_CHAR+
command2: "command" "<<<" (COMMAND2_FRAGMENT? "~{" placeholder "}")* COMMAND2_FRAGMENT? ">>>" -> command

?workflow_outputs: output_decls

// struct definitions
struct: "struct" CNAME "{" unbound_decl* "}"

?document_element: import_doc | task | workflow | struct
"""

versions = {}
versions["draft-2"] = productions_common1 + productions_pre_1_0
versions["1.0"] = productions_common1 + productions_1_0

keywords = {}
keywords["draft-2"] = set(
    "Array File Float Int Map None Pair String as call command else false if import input left meta object output parameter_meta right runtime scatter task then true workflow".split(
        " "
    )
)
keywords["1.0"] = keywords["draft-2"] | set(["alias", "struct"])

# Development grammar version; any bugfixes to the draft-2/1.0 grammar may need to be forward-
# ported into this.
versions["development"] = r"""
///////////////////////////////////////////////////////////////////////////////////////////////////
// document
///////////////////////////////////////////////////////////////////////////////////////////////////

document: version? document_element*
        | version? document_element*

version: "version" /[^ \t\r\n]+/
?document_element: import_doc | task | workflow | struct

import_doc: "import" string_literal ["as" CNAME] import_alias*
import_alias: "alias" CNAME "as" CNAME

///////////////////////////////////////////////////////////////////////////////////////////////////
// workflow
///////////////////////////////////////////////////////////////////////////////////////////////////

workflow: "workflow" CNAME "{" workflow_element* "}"
?workflow_element: input_decls | any_decl | call | scatter | conditional | workflow_outputs | meta_section

scatter: "scatter" "(" CNAME "in" expr ")" "{" inner_workflow_element* "}"
conditional: "if" "(" expr ")" "{" inner_workflow_element* "}"
?inner_workflow_element: any_decl | call | scatter | conditional

call: "call" namespaced_ident ("after" CNAME)* _call_body? -> call
    | "call" namespaced_ident "as" CNAME ("after" CNAME)* _call_body? -> call_as
namespaced_ident: CNAME ("." CNAME)*
call_inputs: input_colon? [call_input ("," call_input)*] ","?
input_colon: "input" ":"
_call_body: "{" call_inputs? "}"
call_input: CNAME ["=" expr]

?workflow_outputs: output_decls

///////////////////////////////////////////////////////////////////////////////////////////////////
// task
///////////////////////////////////////////////////////////////////////////////////////////////////

task: "task" CNAME "{" task_section* command task_section* "}"
?task_section: task_input_decls
             | output_decls
             | meta_section
             | runtime_section
             | task_env_decl -> noninput_decl

tasks: task*

input_decls: "input" "{" any_decl* "}"
task_input_decls: "input" "{" task_env_decl* "}" -> input_decls
ENV.2: "env"
task_env_decl: ENV? any_decl
output_decls: "output" "{" bound_decl* "}"

// WDL task commands: with {} and <<< >>> command and ${} and ~{} placeholder styles
?command: "command" (command1 | command2)

// meta/parameter_meta sections (effectively JSON)
meta_object: "{" [meta_kv (","? meta_kv)*] ","? "}"
meta_kv: CNAME ":" meta_value
?meta_value: literal | string_literal
           | meta_object
           | "[" [meta_value ("," meta_value)*] ","? "]" -> meta_array
!meta_section: ("meta" | "parameter_meta") meta_object

// task runtime section (key-expression pairs)
runtime_section: "runtime" "{" [runtime_kv (","? runtime_kv)*] "}"
runtime_kv: CNAME ":" expr

///////////////////////////////////////////////////////////////////////////////////////////////////
// decl
///////////////////////////////////////////////////////////////////////////////////////////////////

unbound_decl: type CNAME -> decl
bound_decl: type CNAME "=" expr -> decl
?any_decl: unbound_decl | bound_decl

struct: "struct" CNAME "{" unbound_decl* "}"

///////////////////////////////////////////////////////////////////////////////////////////////////
// type
///////////////////////////////////////////////////////////////////////////////////////////////////

// WDL types
type: CNAME _quant?
      | CNAME "[" type ["," type] "]" _quant?

_quant: optional | nonempty | optional_nonempty
optional: "?"
nonempty: "+"
optional_nonempty: "+?"

///////////////////////////////////////////////////////////////////////////////////////////////////
// expr
///////////////////////////////////////////////////////////////////////////////////////////////////

?expr: expr_infix

?expr_infix: expr_infix0

?expr_infix0: expr_infix0 "||" expr_infix1 -> lor
            | expr_infix1

?expr_infix1: expr_infix1 "&&" expr_infix2 -> land
            | expr_infix2

?expr_infix2: expr_infix2 "==" expr_infix3 -> eqeq
            | expr_infix2 "!=" expr_infix3 -> neq
            | expr_infix2 "<=" expr_infix3 -> lte
            | expr_infix2 ">=" expr_infix3 -> gte
            | expr_infix2 "<" expr_infix3 -> lt
            | expr_infix2 ">" expr_infix3 -> gt
            | expr_infix3

?expr_infix3: expr_infix3 "+" expr_infix4 -> add
            | expr_infix3 "-" expr_infix4 -> sub
            | expr_infix4

?expr_infix4: expr_infix4 "*" expr_infix5 -> mul
            | expr_infix4 "/" expr_infix5 -> div
            | expr_infix4 "%" expr_infix5 -> rem
            | expr_infix5

?expr_infix5: expr_core

// expression core (everything but infix)
?expr_core: "(" expr ")"
          | literal
          | string
          | "!" expr_core -> negate

          | "[" [expr ("," expr)*] ","? "]" -> array
          | expr_core "[" expr "]" -> at

          | "(" expr "," expr ")" -> pair
          | "{" [map_kv ("," map_kv)*] ","? "}" -> map

          | "if" expr "then" expr "else" expr -> ifthenelse

          | CNAME "(" [expr ("," expr)*] ")" -> apply

          | CNAME "{" [object_kv ("," object_kv)* ","?] "}" -> obj

          | CNAME -> left_name
          | expr_core "." CNAME -> get_name

?map_key: expr_core
map_kv: map_key ":" expr

object_kv:  CNAME ":" expr
          | string_literal ":" expr

///////////////////////////////////////////////////////////////////////////////////////////////////
// literals & string interpolations
///////////////////////////////////////////////////////////////////////////////////////////////////

?literal: "true"-> boolean_true
        | "false" -> boolean_false
        | "None" -> null
        | INT -> int
        | SIGNED_INT -> int
        | FLOAT -> float
        | SIGNED_FLOAT -> float

?string: string1 | string2 | multistring

_DOUBLE_BACKSLASH.2: "\\\\"
STRING_INNER1: (_DOUBLE_BACKSLASH|"\\'"|/[^']/)
ESCAPED_STRING1: "'" STRING_INNER1* "'"
string_literal: ESCAPED_STRING | ESCAPED_STRING1

_EITHER_DELIM.2: "~{" | "${"

// string (single-quoted)
STRING1_CHAR: _DOUBLE_BACKSLASH | "\\'" | /[^'~$]/ | /\$(?=[^{])/ | /\~(?=[^{])/
STRING1_FRAGMENT: STRING1_CHAR+
string1: /'/ (STRING1_FRAGMENT? _EITHER_DELIM placeholder "}")* STRING1_FRAGMENT? /'/ -> string

// string (double-quoted)
STRING2_CHAR: _DOUBLE_BACKSLASH | "\\\"" | /[^"~$]/ | /\$(?=[^{])/ | /~(?=[^{])/
STRING2_FRAGMENT: STRING2_CHAR+
string2: /"/ (STRING2_FRAGMENT? _EITHER_DELIM placeholder "}")* STRING2_FRAGMENT? /"/ -> string

COMMAND1_CHAR: /[^~$}]/ | /\$(?=[^{])/ | /~(?=[^{])/
COMMAND1_FRAGMENT: COMMAND1_CHAR+
command1: "{" (COMMAND1_FRAGMENT? _EITHER_DELIM placeholder "}")* COMMAND1_FRAGMENT? "}" -> command

COMMAND2_CHAR: /[^~>]/ | /~(?=[^{])/ | />(?=[^>])/ | />>(?=[^>])/
COMMAND2_FRAGMENT: COMMAND2_CHAR+
command2: "<<<" (COMMAND2_FRAGMENT? "~{" placeholder "}")* COMMAND2_FRAGMENT? ">>>" -> command

// multi-line string (very similar to command2, but processed slightly differently)
multistring: /<<</ (COMMAND2_FRAGMENT? "~{" placeholder "}")* COMMAND2_FRAGMENT? />>>/ -> string

?placeholder_value: string_literal
                  | INT -> int
                  | FLOAT -> float
!?placeholder_name: CNAME | "true" | "false"  // extra hints needed here to overcome literal
placeholder_option: placeholder_name "=" placeholder_value
placeholder: placeholder_option* expr

CNAME: /[a-zA-Z][a-zA-Z0-9_]*/

%import common.INT
%import common.SIGNED_INT
%import common.FLOAT
%import common.SIGNED_FLOAT
%import common.ESCAPED_STRING

///////////////////////////////////////////////////////////////////////////////////////////////////
// whitespace/comments
///////////////////////////////////////////////////////////////////////////////////////////////////

%import common.NEWLINE
SPACE: /[ \t]+/
COMMENT: /[ \t]*/ "#" /[^\r\n]*/

%ignore SPACE
%ignore NEWLINE
%ignore COMMENT
"""
keywords["development"] = set(
    (
        "Array Directory File Float Int Map None Pair String"
        " alias as call command else env false if import input left meta"
        " object output parameter_meta right runtime scatter struct task then true workflow"
    ).split(" ")
)

# For now we're defining 1.1 as 'development minus Directory and multi-line strings' (the
# subtractions enforced in _parser.py).
# We'll need to fork them when the development grammar diverges further.
versions["1.1"] = versions["development"]
keywords["1.1"] = keywords["development"]

assert set(versions.keys()) == set(keywords.keys())


def get(version: Optional[str] = None) -> Tuple[str, Set[str]]:
    version = version or "1.0"
    return (versions[version], keywords[version])
