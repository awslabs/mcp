version 1.0

task AlignReads {
    input {
        File reference
        Array[File] reads
        String sample_id
        Int cpu_cores = 4
        String memory = "8 GB"
    }
    
    command <<<
        bwa mem -t ${cpu_cores} ${reference} ${sep=' ' reads} | \
        samtools sort -@ ${cpu_cores} -o ${sample_id}.aligned.bam -
        
        samtools index ${sample_id}.aligned.bam
        samtools flagstat ${sample_id}.aligned.bam > ${sample_id}.stats.txt
    >>>
    
    runtime {
        docker: "biocontainers/bwa:v0.7.17_cv1"
        memory: memory
        cpu: cpu_cores
    }
    
    output {
        File aligned_bam = "${sample_id}.aligned.bam"
        File bam_index = "${sample_id}.aligned.bam.bai"
        File stats = "${sample_id}.stats.txt"
    }
}