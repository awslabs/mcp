version 1.0

import "tasks/alignment.wdl" as alignment
import "tasks/variant_calling.wdl" as variant_calling

workflow GenomicsPipeline {
    input {
        File reference_genome
        Array[File] fastq_files
        String sample_name
    }
    
    call alignment.AlignReads {
        input:
            reference = reference_genome,
            reads = fastq_files,
            sample_id = sample_name
    }
    
    call variant_calling.CallVariants {
        input:
            aligned_bam = AlignReads.aligned_bam,
            reference = reference_genome,
            sample_id = sample_name
    }
    
    output {
        File aligned_bam = AlignReads.aligned_bam
        File variants_vcf = CallVariants.variants_vcf
        File alignment_stats = AlignReads.stats
    }
}