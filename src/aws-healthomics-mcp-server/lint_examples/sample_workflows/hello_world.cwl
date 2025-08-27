cwlVersion: v1.2
class: Workflow

inputs:
  name:
    type: string
    default: "World"

outputs:
  greeting:
    type: string
    outputSource: say_hello/greeting

steps:
  say_hello:
    run:
      class: CommandLineTool
      baseCommand: echo
      inputs:
        name:
          type: string
          inputBinding:
            prefix: "Hello,"
      outputs:
        greeting:
          type: stdout
      stdout: greeting.txt
    in:
      name: name
    out: [greeting]
