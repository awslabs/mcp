## Example Usage

This walkthrough shows a complete happy-path workflow: searching for a dataset,
previewing its S3 bucket structure, and sampling a file — all using natural language.

---

### 1. Search for datasets

**Prompt:** "Find datasets for human genetics"

**Tool called:** `search_datasets(query="human genetics", limit=10)`

**Response (trimmed):**
```json
{
  "query": "human genetics",
  "total_count": 101,
  "returned_count": 10,
  "top_categories": ["aws-pds", "life sciences", "genomic", "genetic", "whole genome sequencing"],
  "results": [
    {
      "slug": "1000-genomes",
      "name": "1000 Genomes",
      "description": "The 1000 Genomes Project is the first project to sequence the genomes of a large number of people...",
      "managed_by": "[International Genome Sample Resource (IGSR)](https://www.internationalgenome.org/)",
      "license": "Data from the 1000 Genomes Project is now available without embargo..."
    }
  ]
}
```

---

### 2. Get dataset details

**Prompt:** "Tell me more about the 1000 Genomes dataset"

**Tool called:** `get_dataset_details(slug="1000-genomes")`

**Response (trimmed):**
```json
{
  "Name": "1000 Genomes",
  "Description": "The 1000 Genomes Project is an international collaboration which has established the most detailed catalogue of human genetic variation, including SNPs, structural variants, and their haplotype context. The final phase of the project sequenced more than 2500 individuals from 26 different populations...",
  "ManagedBy": "National Institutes of Health",
  "License": "Data from the 1000 Genomes Project is now available without embargo...",
  "Tags": ["aws-pds", "fastq", "genetic", "genomic", "life sciences", "whole genome sequencing"],
  "Resources": [
    {
      "Description": "http://www.internationalgenome.org/formats",
      "ARN": "arn:aws:s3:::1000genomes",
      "Region": "us-east-1",
      "Type": "S3 Bucket"
    }
  ],
  "Documentation": "https://github.com/awslabs/open-data-docs/tree/main/docs/1000genomes",
  "Contact": "http://www.internationalgenome.org/contact"
}
```

---

### 3. Preview the dataset

**Prompt:** "Preview the 1000 Genomes dataset"

**Tool called:** `preview_dataset(slug="1000-genomes")`

**Response (trimmed):**
```json
{
  "dataset": "1000 Genomes",
  "slug": "1000-genomes",
  "license": "Data from the 1000 Genomes Project is now available without embargo...",
  "bucket": "1000genomes",
  "region": "us-east-1",
  "truncated": true,
  "object_count": 10,
  "objects": [
    {
      "key": "1000G_2504_high_coverage/additional_698_related/20200526_1000G_2504plus698_high_cov_data_reuse_README.txt",
      "size_bytes": 2394,
      "last_modified": "2020-05-26T18:27:27+00:00"
    },
    {
      "key": "1000G_2504_high_coverage/additional_698_related/HG00418.final.cram.crai",
      "size_bytes": 1391941,
      "last_modified": "2021-12-07T18:59:12+00:00"
    }
  ],
  "cli_commands": {
    "list": "aws s3 ls s3://1000genomes/ --no-sign-request",
    "list_recursive": "aws s3 ls s3://1000genomes/ --recursive --no-sign-request"
  }
}
```

---

### 4. Sample a file

**Prompt:** "Read the README file"

**Tool called:** `sample_dataset(slug="1000-genomes", file_key="1000G_2504_high_coverage/additional_698_related/20200526_1000G_2504plus698_high_cov_data_reuse_README.txt")`

**Response (trimmed):**
```json
{
  "dataset": "1000 Genomes",
  "slug": "1000-genomes",
  "license": "Data from the 1000 Genomes Project is now available without embargo...",
  "bucket": "1000genomes",
  "file_key": "1000G_2504_high_coverage/additional_698_related/20200526_1000G_2504plus698_high_cov_data_reuse_README.txt",
  "file_size_bytes": 2394,
  "bytes_read": 2394,
  "is_partial": false,
  "encoding": "utf-8",
  "content": "This policy refers to 30x Illumina NovaSeq sequencing of 2504 samples from the 1000 Genomes project phase 3 sample set, along with 698 family members that complete trios in the phase 3 data. These data were generated at the New York Genome Center with funds provided by NHGRI Grant 3UM1HG008901...",
  "cli_command": "aws s3 cp s3://1000genomes/1000G_2504_high_coverage/additional_698_related/20200526_1000G_2504plus698_high_cov_data_reuse_README.txt . --no-sign-request"
}
```

---

### 5. Sample another file

**Prompt:** "Show me the population data file"

**Tool called:** `sample_dataset(slug="1000-genomes", file_key="1000G_2504_high_coverage/additional_698_related/20130606_g1k_3202_samples_ped_population.txt")`

**Response (trimmed):**
```json
{
  "dataset": "1000 Genomes",
  "slug": "1000-genomes",
  "license": "Data from the 1000 Genomes Project is now available without embargo...",
  "bucket": "1000genomes",
  "file_key": "1000G_2504_high_coverage/additional_698_related/20130606_g1k_3202_samples_ped_population.txt",
  "file_size_bytes": 97483,
  "bytes_read": 97483,
  "is_partial": false,
  "encoding": "utf-8",
  "content": "FamilyID SampleID FatherID MotherID Sex Population Superpopulation\nHG00096 HG00096 0 0 1 GBR EUR\nHG00097 HG00097 0 0 2 GBR EUR\nHG00099 HG00099 0 0 2 GBR EUR\nHG00100 HG00100 0 0 2 GBR EUR\n...",
  "cli_command": "aws s3 cp s3://1000genomes/1000G_2504_high_coverage/additional_698_related/20130606_g1k_3202_samples_ped_population.txt . --no-sign-request"
}
```

---

### 6. Find related datasets

**Prompt:** "Find datasets related to 1000 Genomes"

**Tool called:** `find_related_datasets(slug="1000-genomes", limit=5)`

**Response (trimmed):**
```json
{
  "source_dataset": "1000-genomes",
  "count": 5,
  "related_datasets": [
    {
      "slug": "ncbi-sra",
      "name": "NIH NCBI Sequence Read Archive (SRA) on AWS",
      "tags": ["aws-pds", "bam", "cram", "fastq", "genomic"],
      "managed_by": "[National Library of Medicine (NLM)](http://nlm.nih.gov/)",
      "license": "[NIH Genomic Data Sharing Policy](...)"
    },
    {
      "slug": "ncbi-covid-19",
      "name": "COVID-19 Genome Sequence Dataset",
      "tags": ["aws-pds", "bam", "bioinformatics", "biology", "coronavirus"],
      "managed_by": "[National Library of Medicine (NLM)](http://nlm.nih.gov/)",
      "license": "[NIH Genomic Data Sharing Policy](...)"
    }
  ]
}
```

---

### Notes

- `preview_dataset` lists files without downloading data. Use `sample_dataset` to read file content.
- If a dataset has multiple S3 buckets, `preview_dataset` will ask you to pick one.
- Text files are decoded and shown directly. Binary files (e.g., `.cram`, `.zip`) return a CLI command to download instead.
- Requester-pays and controlled-access datasets cannot be previewed anonymously — the response explains why and what to do.
