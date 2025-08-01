version 1.0

task CallVariants {
    input {
        File aligned_bam
        File reference
        String sample_id
        Int cpu_cores = 2
        String memory = "4 GB"
    }
    
    command <<<
        gatk HaplotypeCaller \
            -R ${reference} \
            -I ${aligned_bam} \
            -O ${sample_id}.variants.vcf \
            --native-pair-hmm-threads ${cpu_cores}
    >>>
    
    runtime {
        docker: "broadinstitute/gatk:4.2.6.1"
        memory: memory
        cpu: cpu_cores
    }
    
    output {
        File variants_vcf = "${sample_id}.variants.vcf"
    }
}