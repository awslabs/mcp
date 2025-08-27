version 1.0

workflow HelloWorld {
    input {
        String name = "World"
    }

    call SayHello { input: name = name }

    output {
        String greeting = SayHello.greeting
    }
}

task SayHello {
    input {
        String name
    }

    command <<<
        echo "Hello, ${name}!"
    >>>

    runtime {
        docker: "ubuntu:20.04"
        memory: "1 GB"
        cpu: 1
    }

    output {
        String greeting = stdout()
    }
}
