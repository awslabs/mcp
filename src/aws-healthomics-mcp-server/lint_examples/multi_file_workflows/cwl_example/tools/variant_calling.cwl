cwlVersion: v1.2
class: CommandLineTool

requirements:
  - class: DockerRequirement
    dockerPull: "broadinstitute/gatk:4.2.6.1"
  - class: ResourceRequirement
    coresMin: 2
    ramMin: 4096

baseCommand: [gatk, HaplotypeCaller]

inputs:
  aligned_bam:
    type: File
    inputBinding:
      prefix: -I
    secondaryFiles:
      - .bai
  reference:
    type: File
    inputBinding:
      prefix: -R
    secondaryFiles:
      - .fai
      - ^.dict
  sample_id:
    type: string

arguments:
  - prefix: -O
    valueFrom: $(inputs.sample_id).variants.vcf
  - prefix: --native-pair-hmm-threads
    valueFrom: $(runtime.cores)

outputs:
  variants_vcf:
    type: File
    outputBinding:
      glob: "*.variants.vcf"
