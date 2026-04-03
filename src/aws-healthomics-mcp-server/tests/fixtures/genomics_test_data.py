# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Test fixtures and mock data for genomics file search integration tests."""

from datetime import datetime, timezone
from typing import Any, Dict, List


class GenomicsTestDataFixtures:
    """Comprehensive test data fixtures for genomics file search testing."""

    @staticmethod
    def get_comprehensive_s3_dataset() -> List[Dict[str, Any]]:
        """Get a comprehensive S3 dataset covering all genomics file types and scenarios."""
        return [
            # Cancer genomics study - complete BAM workflow
            {
                'Key': 'studies/cancer_genomics/samples/TCGA-001/tumor.bam',
                'Size': 15000000000,  # 15GB
                'LastModified': datetime(2023, 6, 15, 14, 30, 0, tzinfo=timezone.utc),
                'StorageClass': 'STANDARD',
                'TagSet': [
                    {'Key': 'study', 'Value': 'cancer_genomics'},
                    {'Key': 'sample_type', 'Value': 'tumor'},
                    {'Key': 'patient_id', 'Value': 'TCGA-001'},
                    {'Key': 'data_type', 'Value': 'alignment'},
                    {'Key': 'pipeline_version', 'Value': 'v2.1'},
                ],
            },
            {
                'Key': 'studies/cancer_genomics/samples/TCGA-001/tumor.bam.bai',
                'Size': 8000000,  # 8MB
                'LastModified': datetime(2023, 6, 15, 14, 35, 0, tzinfo=timezone.utc),
                'StorageClass': 'STANDARD',
                'TagSet': [
                    {'Key': 'study', 'Value': 'cancer_genomics'},
                    {'Key': 'sample_type', 'Value': 'tumor'},
                    {'Key': 'patient_id', 'Value': 'TCGA-001'},
                    {'Key': 'data_type', 'Value': 'index'},
                ],
            },
            {
                'Key': 'studies/cancer_genomics/samples/TCGA-001/normal.bam',
                'Size': 12000000000,  # 12GB
                'LastModified': datetime(2023, 6, 15, 16, 45, 0, tzinfo=timezone.utc),
                'StorageClass': 'STANDARD',
                'TagSet': [
                    {'Key': 'study', 'Value': 'cancer_genomics'},
                    {'Key': 'sample_type', 'Value': 'normal'},
                    {'Key': 'patient_id', 'Value': 'TCGA-001'},
                    {'Key': 'data_type', 'Value': 'alignment'},
                ],
            },
            {
                'Key': 'studies/cancer_genomics/samples/TCGA-001/normal.bam.bai',
                'Size': 6500000,  # 6.5MB
                'LastModified': datetime(2023, 6, 15, 16, 50, 0, tzinfo=timezone.utc),
                'StorageClass': 'STANDARD',
                'TagSet': [
                    {'Key': 'study', 'Value': 'cancer_genomics'},
                    {'Key': 'sample_type', 'Value': 'normal'},
                    {'Key': 'patient_id', 'Value': 'TCGA-001'},
                    {'Key': 'data_type', 'Value': 'index'},
                ],
            },
            # Raw sequencing data - FASTQ pairs
            {
                'Key': 'raw_sequencing/batch_2023_01/sample_WGS_001_R1.fastq.gz',
                'Size': 8500000000,  # 8.5GB
                'LastModified': datetime(2023, 1, 20, 10, 15, 0, tzinfo=timezone.utc),
                'StorageClass': 'STANDARD',
                'TagSet': [
                    {'Key': 'sequencing_batch', 'Value': 'batch_2023_01'},
                    {'Key': 'sample_id', 'Value': 'WGS_001'},
                    {'Key': 'read_pair', 'Value': 'R1'},
                    {'Key': 'sequencing_platform', 'Value': 'NovaSeq'},
                    {'Key': 'library_prep', 'Value': 'TruSeq'},
                ],
            },
            {
                'Key': 'raw_sequencing/batch_2023_01/sample_WGS_001_R2.fastq.gz',
                'Size': 8500000000,  # 8.5GB
                'LastModified': datetime(2023, 1, 20, 10, 20, 0, tzinfo=timezone.utc),
                'StorageClass': 'STANDARD',
                'TagSet': [
                    {'Key': 'sequencing_batch', 'Value': 'batch_2023_01'},
                    {'Key': 'sample_id', 'Value': 'WGS_001'},
                    {'Key': 'read_pair', 'Value': 'R2'},
                    {'Key': 'sequencing_platform', 'Value': 'NovaSeq'},
                    {'Key': 'library_prep', 'Value': 'TruSeq'},
                ],
            },
            # Single-end FASTQ
            {
                'Key': 'rna_seq/single_cell/experiment_001/cell_001.fastq.gz',
                'Size': 2100000000,  # 2.1GB
                'LastModified': datetime(2023, 4, 10, 9, 30, 0, tzinfo=timezone.utc),
                'StorageClass': 'STANDARD',
                'TagSet': [
                    {'Key': 'experiment', 'Value': 'single_cell_rna_seq'},
                    {'Key': 'cell_id', 'Value': 'cell_001'},
                    {'Key': 'protocol', 'Value': '10x_genomics'},
                ],
            },
            # Variant calling results
            {
                'Key': 'variant_calling/cohort_analysis/all_samples.vcf.gz',
                'Size': 2800000000,  # 2.8GB
                'LastModified': datetime(2023, 7, 5, 11, 20, 0, tzinfo=timezone.utc),
                'StorageClass': 'STANDARD_IA',
                'TagSet': [
                    {'Key': 'analysis_type', 'Value': 'joint_genotyping'},
                    {'Key': 'cohort_size', 'Value': '1000'},
                    {'Key': 'variant_caller', 'Value': 'GATK_HaplotypeCaller'},
                    {'Key': 'genome_build', 'Value': 'GRCh38'},
                ],
            },
            {
                'Key': 'variant_calling/cohort_analysis/all_samples.vcf.gz.tbi',
                'Size': 15000000,  # 15MB
                'LastModified': datetime(2023, 7, 5, 11, 25, 0, tzinfo=timezone.utc),
                'StorageClass': 'STANDARD_IA',
                'TagSet': [
                    {'Key': 'analysis_type', 'Value': 'joint_genotyping'},
                    {'Key': 'data_type', 'Value': 'index'},
                ],
            },
            # GVCF files
            {
                'Key': 'variant_calling/individual_gvcfs/TCGA-001.g.vcf.gz',
                'Size': 450000000,  # 450MB
                'LastModified': datetime(2023, 6, 20, 15, 10, 0, tzinfo=timezone.utc),
                'StorageClass': 'STANDARD',
                'TagSet': [
                    {'Key': 'patient_id', 'Value': 'TCGA-001'},
                    {'Key': 'variant_type', 'Value': 'gvcf'},
                    {'Key': 'caller', 'Value': 'GATK'},
                ],
            },
            {
                'Key': 'variant_calling/individual_gvcfs/TCGA-001.g.vcf.gz.tbi',
                'Size': 2500000,  # 2.5MB
                'LastModified': datetime(2023, 6, 20, 15, 15, 0, tzinfo=timezone.utc),
                'StorageClass': 'STANDARD',
                'TagSet': [
                    {'Key': 'patient_id', 'Value': 'TCGA-001'},
                    {'Key': 'data_type', 'Value': 'index'},
                ],
            },
            # Reference genomes and indexes
            {
                'Key': 'references/GRCh38/GRCh38.primary_assembly.genome.fasta',
                'Size': 3200000000,  # 3.2GB
                'LastModified': datetime(2023, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
                'StorageClass': 'STANDARD',
                'TagSet': [
                    {'Key': 'genome_build', 'Value': 'GRCh38'},
                    {'Key': 'assembly_type', 'Value': 'primary'},
                    {'Key': 'data_type', 'Value': 'reference'},
                ],
            },
            {
                'Key': 'references/GRCh38/GRCh38.primary_assembly.genome.fasta.fai',
                'Size': 3500,  # 3.5KB
                'LastModified': datetime(2023, 1, 1, 0, 5, 0, tzinfo=timezone.utc),
                'StorageClass': 'STANDARD',
                'TagSet': [
                    {'Key': 'genome_build', 'Value': 'GRCh38'},
                    {'Key': 'data_type', 'Value': 'index'},
                ],
            },
            {
                'Key': 'references/GRCh38/GRCh38.primary_assembly.genome.dict',
                'Size': 18000,  # 18KB
                'LastModified': datetime(2023, 1, 1, 0, 10, 0, tzinfo=timezone.utc),
                'StorageClass': 'STANDARD',
                'TagSet': [
                    {'Key': 'genome_build', 'Value': 'GRCh38'},
                    {'Key': 'data_type', 'Value': 'dictionary'},
                ],
            },
            # BWA index files
            {
                'Key': 'references/GRCh38/bwa_index/GRCh38.primary_assembly.genome.fasta.amb',
                'Size': 190,
                'LastModified': datetime(2023, 1, 1, 1, 0, 0, tzinfo=timezone.utc),
                'StorageClass': 'STANDARD',
                'TagSet': [
                    {'Key': 'genome_build', 'Value': 'GRCh38'},
                    {'Key': 'index_type', 'Value': 'bwa'},
                ],
            },
            {
                'Key': 'references/GRCh38/bwa_index/GRCh38.primary_assembly.genome.fasta.ann',
                'Size': 950,
                'LastModified': datetime(2023, 1, 1, 1, 5, 0, tzinfo=timezone.utc),
                'StorageClass': 'STANDARD',
                'TagSet': [
                    {'Key': 'genome_build', 'Value': 'GRCh38'},
                    {'Key': 'index_type', 'Value': 'bwa'},
                ],
            },
            {
                'Key': 'references/GRCh38/bwa_index/GRCh38.primary_assembly.genome.fasta.bwt',
                'Size': 800000000,  # 800MB
                'LastModified': datetime(2023, 1, 1, 1, 10, 0, tzinfo=timezone.utc),
                'StorageClass': 'STANDARD',
                'TagSet': [
                    {'Key': 'genome_build', 'Value': 'GRCh38'},
                    {'Key': 'index_type', 'Value': 'bwa'},
                ],
            },
            {
                'Key': 'references/GRCh38/bwa_index/GRCh38.primary_assembly.genome.fasta.pac',
                'Size': 800000000,  # 800MB
                'LastModified': datetime(2023, 1, 1, 1, 15, 0, tzinfo=timezone.utc),
                'StorageClass': 'STANDARD',
                'TagSet': [
                    {'Key': 'genome_build', 'Value': 'GRCh38'},
                    {'Key': 'index_type', 'Value': 'bwa'},
                ],
            },
            {
                'Key': 'references/GRCh38/bwa_index/GRCh38.primary_assembly.genome.fasta.sa',
                'Size': 1600000000,  # 1.6GB
                'LastModified': datetime(2023, 1, 1, 1, 20, 0, tzinfo=timezone.utc),
                'StorageClass': 'STANDARD',
                'TagSet': [
                    {'Key': 'genome_build', 'Value': 'GRCh38'},
                    {'Key': 'index_type', 'Value': 'bwa'},
                ],
            },
            # Annotation files
            {
                'Key': 'annotations/gencode/gencode.v44.primary_assembly.annotation.gff3.gz',
                'Size': 45000000,  # 45MB
                'LastModified': datetime(2023, 3, 15, 12, 0, 0, tzinfo=timezone.utc),
                'StorageClass': 'STANDARD',
                'TagSet': [
                    {'Key': 'annotation_source', 'Value': 'GENCODE'},
                    {'Key': 'version', 'Value': 'v44'},
                    {'Key': 'genome_build', 'Value': 'GRCh38'},
                ],
            },
            # BED files
            {
                'Key': 'intervals/exome_capture/SureSelect_Human_All_Exon_V7.bed',
                'Size': 12000000,  # 12MB
                'LastModified': datetime(2023, 2, 1, 8, 30, 0, tzinfo=timezone.utc),
                'StorageClass': 'STANDARD',
                'TagSet': [
                    {'Key': 'capture_kit', 'Value': 'SureSelect_V7'},
                    {'Key': 'target_type', 'Value': 'exome'},
                ],
            },
            # CRAM files
            {
                'Key': 'compressed_alignments/low_coverage/sample_LC_001.cram',
                'Size': 3200000000,  # 3.2GB (smaller than BAM due to compression)
                'LastModified': datetime(2023, 5, 10, 14, 20, 0, tzinfo=timezone.utc),
                'StorageClass': 'STANDARD_IA',
                'TagSet': [
                    {'Key': 'sample_id', 'Value': 'LC_001'},
                    {'Key': 'coverage', 'Value': 'low'},
                    {'Key': 'compression', 'Value': 'cram'},
                ],
            },
            {
                'Key': 'compressed_alignments/low_coverage/sample_LC_001.cram.crai',
                'Size': 1800000,  # 1.8MB
                'LastModified': datetime(2023, 5, 10, 14, 25, 0, tzinfo=timezone.utc),
                'StorageClass': 'STANDARD_IA',
                'TagSet': [
                    {'Key': 'sample_id', 'Value': 'LC_001'},
                    {'Key': 'data_type', 'Value': 'index'},
                ],
            },
            # Archived/Glacier files
            {
                'Key': 'archive/2022/old_study/legacy_sample.bam',
                'Size': 8000000000,  # 8GB
                'LastModified': datetime(2022, 12, 15, 10, 0, 0, tzinfo=timezone.utc),
                'StorageClass': 'GLACIER',
                'TagSet': [
                    {'Key': 'study', 'Value': 'legacy_study'},
                    {'Key': 'archived', 'Value': 'true'},
                    {'Key': 'archive_date', 'Value': '2023-01-01'},
                ],
            },
            # Deep archive files
            {
                'Key': 'deep_archive/historical/2020_cohort/batch_001.fastq.gz',
                'Size': 5000000000,  # 5GB
                'LastModified': datetime(2020, 8, 1, 0, 0, 0, tzinfo=timezone.utc),
                'StorageClass': 'DEEP_ARCHIVE',
                'TagSet': [
                    {'Key': 'cohort', 'Value': '2020_cohort'},
                    {'Key': 'deep_archived', 'Value': 'true'},
                ],
            },
        ]

    @staticmethod
    def get_healthomics_sequence_stores() -> List[Dict[str, Any]]:
        """Get comprehensive HealthOmics sequence store test data."""
        return [
            {
                'id': 'seq-store-cancer-001',
                'name': 'cancer-genomics-sequences',
                'description': 'Sequence data for cancer genomics research',
                'arn': 'arn:aws:omics:us-east-1:123456789012:sequenceStore/seq-store-cancer-001',
                'creationTime': datetime(2023, 1, 15, tzinfo=timezone.utc),
                'sseConfig': {'type': 'KMS'},
                'readSets': [
                    {
                        'id': 'readset-tumor-001',
                        'name': 'TCGA-001-tumor-WGS',
                        'description': 'Whole genome sequencing of tumor sample from patient TCGA-001',
                        'subjectId': 'TCGA-001',
                        'sampleId': 'tumor-sample-001',
                        'status': 'ACTIVE',
                        'sequenceInformation': {
                            'totalReadCount': 750000000,
                            'totalBaseCount': 112500000000,  # 112.5 billion bases
                            'generatedFrom': 'FASTQ',
                            'alignment': 'UNALIGNED',
                        },
                        'files': [
                            {
                                'contentType': 'FASTQ',
                                'partNumber': 1,
                                's3Access': {
                                    's3Uri': 's3://omics-123456789012-us-east-1/seq-store-cancer-001/readset-tumor-001/source1.fastq.gz'
                                },
                            },
                            {
                                'contentType': 'FASTQ',
                                'partNumber': 2,
                                's3Access': {
                                    's3Uri': 's3://omics-123456789012-us-east-1/seq-store-cancer-001/readset-tumor-001/source2.fastq.gz'
                                },
                            },
                        ],
                        'creationTime': datetime(2023, 6, 15, tzinfo=timezone.utc),
                    },
                    {
                        'id': 'readset-normal-001',
                        'name': 'TCGA-001-normal-WGS',
                        'description': 'Whole genome sequencing of normal sample from patient TCGA-001',
                        'subjectId': 'TCGA-001',
                        'sampleId': 'normal-sample-001',
                        'status': 'ACTIVE',
                        'sequenceInformation': {
                            'totalReadCount': 600000000,
                            'totalBaseCount': 90000000000,  # 90 billion bases
                            'generatedFrom': 'FASTQ',
                            'alignment': 'UNALIGNED',
                        },
                        'files': [
                            {
                                'contentType': 'FASTQ',
                                'partNumber': 1,
                                's3Access': {
                                    's3Uri': 's3://omics-123456789012-us-east-1/seq-store-cancer-001/readset-normal-001/source1.fastq.gz'
                                },
                            },
                            {
                                'contentType': 'FASTQ',
                                'partNumber': 2,
                                's3Access': {
                                    's3Uri': 's3://omics-123456789012-us-east-1/seq-store-cancer-001/readset-normal-001/source2.fastq.gz'
                                },
                            },
                        ],
                        'creationTime': datetime(2023, 6, 15, tzinfo=timezone.utc),
                    },
                    {
                        'id': 'readset-rna-001',
                        'name': 'TCGA-001-tumor-RNA-seq',
                        'description': 'RNA sequencing of tumor sample from patient TCGA-001',
                        'subjectId': 'TCGA-001',
                        'sampleId': 'rna-sample-001',
                        'status': 'ACTIVE',
                        'sequenceInformation': {
                            'totalReadCount': 100000000,
                            'totalBaseCount': 15000000000,  # 15 billion bases
                            'generatedFrom': 'FASTQ',
                            'alignment': 'UNALIGNED',
                        },
                        'files': [
                            {
                                'contentType': 'FASTQ',
                                'partNumber': 1,
                                's3Access': {
                                    's3Uri': 's3://omics-123456789012-us-east-1/seq-store-cancer-001/readset-rna-001/source1.fastq.gz'
                                },
                            },
                            {
                                'contentType': 'FASTQ',
                                'partNumber': 2,
                                's3Access': {
                                    's3Uri': 's3://omics-123456789012-us-east-1/seq-store-cancer-001/readset-rna-001/source2.fastq.gz'
                                },
                            },
                        ],
                        'creationTime': datetime(2023, 7, 1, tzinfo=timezone.utc),
                    },
                ],
            },
            {
                'id': 'seq-store-population-002',
                'name': 'population-genomics-sequences',
                'description': 'Large-scale population genomics study sequences',
                'arn': 'arn:aws:omics:us-east-1:123456789012:sequenceStore/seq-store-population-002',
                'creationTime': datetime(2023, 2, 1, tzinfo=timezone.utc),
                'sseConfig': {'type': 'KMS'},
                'readSets': [
                    {
                        'id': 'readset-pop-001',
                        'name': 'population-sample-001',
                        'description': 'Population study sample 001',
                        'subjectId': 'POP-001',
                        'sampleId': 'pop-sample-001',
                        'status': 'ACTIVE',
                        'sequenceInformation': {
                            'totalReadCount': 400000000,
                            'totalBaseCount': 60000000000,
                            'generatedFrom': 'FASTQ',
                            'alignment': 'UNALIGNED',
                        },
                        'files': [
                            {
                                'contentType': 'FASTQ',
                                'partNumber': 1,
                                's3Access': {
                                    's3Uri': 's3://omics-123456789012-us-east-1/seq-store-population-002/readset-pop-001/source1.fastq.gz'
                                },
                            },
                        ],
                        'creationTime': datetime(2023, 3, 1, tzinfo=timezone.utc),
                    },
                ],
            },
        ]

    @staticmethod
    def get_healthomics_reference_stores() -> List[Dict[str, Any]]:
        """Get comprehensive HealthOmics reference store test data."""
        return [
            {
                'id': 'ref-store-human-001',
                'name': 'human-reference-genomes',
                'description': 'Human reference genome assemblies',
                'arn': 'arn:aws:omics:us-east-1:123456789012:referenceStore/ref-store-human-001',
                'creationTime': datetime(2023, 1, 1, tzinfo=timezone.utc),
                'sseConfig': {'type': 'KMS'},
                'references': [
                    {
                        'id': 'ref-grch38-001',
                        'name': 'GRCh38-primary-assembly',
                        'description': 'Human reference genome GRCh38 primary assembly',
                        'md5': 'md5HashValue789',
                        'status': 'ACTIVE',
                        'files': [
                            {
                                'contentType': 'FASTA',
                                'partNumber': 1,
                                's3Access': {
                                    's3Uri': 's3://omics-123456789012-us-east-1/ref-store-human-001/ref-grch38-001/reference.fasta'
                                },
                            }
                        ],
                        'creationTime': datetime(2023, 1, 1, tzinfo=timezone.utc),
                    },
                    {
                        'id': 'ref-grch37-001',
                        'name': 'GRCh37-primary-assembly',
                        'description': 'Human reference genome GRCh37 primary assembly',
                        'md5': 'md5HashValueABC',
                        'status': 'ACTIVE',
                        'files': [
                            {
                                'contentType': 'FASTA',
                                'partNumber': 1,
                                's3Access': {
                                    's3Uri': 's3://omics-123456789012-us-east-1/ref-store-human-001/ref-grch37-001/reference.fasta'
                                },
                            }
                        ],
                        'creationTime': datetime(2023, 1, 1, tzinfo=timezone.utc),
                    },
                ],
            },
            {
                'id': 'ref-store-model-002',
                'name': 'model-organism-references',
                'description': 'Reference genomes for model organisms',
                'arn': 'arn:aws:omics:us-east-1:123456789012:referenceStore/ref-store-model-002',
                'creationTime': datetime(2023, 1, 15, tzinfo=timezone.utc),
                'sseConfig': {'type': 'KMS'},
                'references': [
                    {
                        'id': 'ref-mouse-001',
                        'name': 'GRCm39-mouse-reference',
                        'description': 'Mouse reference genome GRCm39',
                        'md5': 'md5HashValueDEF',
                        'status': 'ACTIVE',
                        'files': [
                            {
                                'contentType': 'FASTA',
                                'partNumber': 1,
                                's3Access': {
                                    's3Uri': 's3://omics-123456789012-us-east-1/ref-store-model-002/ref-mouse-001/reference.fasta'
                                },
                            }
                        ],
                        'creationTime': datetime(2023, 1, 15, tzinfo=timezone.utc),
                    },
                ],
            },
        ]

    @staticmethod
    def get_large_dataset_scenario(num_files: int = 10000) -> List[Dict[str, Any]]:
        """Generate a large dataset scenario for performance testing."""
        large_dataset = []

        # Generate diverse file types and patterns
        file_patterns = [
            ('samples/batch_{batch:03d}/sample_{sample:05d}.fastq.gz', 'STANDARD', 2000000000),
            ('alignments/batch_{batch:03d}/sample_{sample:05d}.bam', 'STANDARD', 8000000000),
            ('variants/batch_{batch:03d}/sample_{sample:05d}.vcf.gz', 'STANDARD_IA', 500000000),
            ('archive/old_batch_{batch:03d}/sample_{sample:05d}.bam', 'GLACIER', 6000000000),
        ]

        for i in range(num_files):
            batch_num = i // 100
            sample_num = i
            pattern_idx = i % len(file_patterns)

            pattern, storage_class, base_size = file_patterns[pattern_idx]
            key = pattern.format(batch=batch_num, sample=sample_num)

            # Add some size variation
            size_variation = (i % 1000) * 1000000  # Up to 1GB variation
            final_size = base_size + size_variation

            large_dataset.append(
                {
                    'Key': key,
                    'Size': final_size,
                    'LastModified': datetime(
                        2023, 1 + (i % 12), 1 + (i % 28), tzinfo=timezone.utc
                    ),
                    'StorageClass': storage_class,
                    'TagSet': [
                        {'Key': 'batch', 'Value': f'batch_{batch_num:03d}'},
                        {'Key': 'sample_id', 'Value': f'sample_{sample_num:05d}'},
                        {'Key': 'file_type', 'Value': key.split('.')[-1]},
                        {'Key': 'generated', 'Value': 'true'},
                    ],
                }
            )

        return large_dataset

    @staticmethod
    def get_pagination_test_scenarios() -> Dict[str, List[Dict[str, Any]]]:
        """Get various pagination test scenarios."""
        return {
            'small_dataset': GenomicsTestDataFixtures.get_comprehensive_s3_dataset()[:10],
            'medium_dataset': GenomicsTestDataFixtures.get_comprehensive_s3_dataset()
            * 5,  # 125 files
            'large_dataset': GenomicsTestDataFixtures.get_large_dataset_scenario(1000),
            'very_large_dataset': GenomicsTestDataFixtures.get_large_dataset_scenario(10000),
        }

    @staticmethod
    def get_cross_storage_scenarios() -> Dict[str, Any]:
        """Get test scenarios that span multiple storage systems."""
        return {
            's3_data': GenomicsTestDataFixtures.get_comprehensive_s3_dataset()[:15],
            'healthomics_sequences': GenomicsTestDataFixtures.get_healthomics_sequence_stores(),
            'healthomics_references': GenomicsTestDataFixtures.get_healthomics_reference_stores(),
            'mixed_search_terms': [
                'TCGA-001',  # Should match both S3 and HealthOmics
                'cancer_genomics',  # Should match S3 study
                'GRCh38',  # Should match references
                'tumor',  # Should match both systems
            ],
        }
