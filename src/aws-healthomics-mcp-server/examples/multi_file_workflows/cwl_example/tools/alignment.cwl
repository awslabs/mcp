cwlVersion: v1.2
class: CommandLineTool

requirements:
  - class: DockerRequirement
    dockerPull: "biocontainers/bwa:v0.7.17_cv1"
  - class: ResourceRequirement
    coresMin: 4
    ramMin: 8192

baseCommand: [bash, -c]

inputs:
  reference:
    type: File
    secondaryFiles:
      - .amb
      - .ann
      - .bwt
      - .pac
      - .sa
  reads:
    type: File[]
  sample_id:
    type: string

arguments:
  - |
    bwa mem -t $(nproc) $(inputs.reference.path) $(inputs.reads.map(function(f) { return f.path; }).join(' ')) | \
    samtools sort -@ $(nproc) -o $(inputs.sample_id).aligned.bam - && \
    samtools index $(inputs.sample_id).aligned.bam && \
    samtools flagstat $(inputs.sample_id).aligned.bam > $(inputs.sample_id).stats.txt

outputs:
  aligned_bam:
    type: File
    outputBinding:
      glob: "*.aligned.bam"
    secondaryFiles:
      - .bai
  stats:
    type: File
    outputBinding:
      glob: "*.stats.txt"