cwlVersion: v1.2
class: Workflow

requirements:
  - class: SubworkflowFeatureRequirement

inputs:
  reference_genome:
    type: File
  fastq_files:
    type: File[]
  sample_name:
    type: string

outputs:
  aligned_bam:
    type: File
    outputSource: alignment/aligned_bam
  variants_vcf:
    type: File
    outputSource: variant_calling/variants_vcf
  alignment_stats:
    type: File
    outputSource: alignment/stats

steps:
  alignment:
    run: tools/alignment.cwl
    in:
      reference: reference_genome
      reads: fastq_files
      sample_id: sample_name
    out: [aligned_bam, stats]

  variant_calling:
    run: tools/variant_calling.cwl
    in:
      aligned_bam: alignment/aligned_bam
      reference: reference_genome
      sample_id: sample_name
    out: [variants_vcf]
