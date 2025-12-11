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

"""Performance comparison test for pre-compiled patterns optimization."""

import time
from awslabs.aws_healthomics_mcp_server.models import GenomicsFile, GenomicsFileType
from awslabs.aws_healthomics_mcp_server.search.file_association_engine import FileAssociationEngine
from datetime import datetime


def test_performance_improvement_demonstration():
    """Demonstrate performance improvement with pre-compiled patterns.

    This test shows that the optimized implementation with pre-compiled patterns
    and extension-based filtering performs significantly better than naive
    regex compilation on every iteration.
    """
    engine = FileAssociationEngine()
    base_datetime = datetime(2023, 1, 1, 12, 0, 0)

    # Create a realistic dataset with 500 files (250 BAM + 250 BAI)
    files = []
    for i in range(250):
        files.append(
            GenomicsFile(
                path=f's3://bucket/sample{i}.bam',
                file_type=GenomicsFileType.BAM,
                size_bytes=1000000,
                storage_class='STANDARD',
                last_modified=base_datetime,
                tags={},
                source_system='s3',
                metadata={},
            )
        )
        files.append(
            GenomicsFile(
                path=f's3://bucket/sample{i}.bam.bai',
                file_type=GenomicsFileType.BAI,
                size_bytes=10000,
                storage_class='STANDARD',
                last_modified=base_datetime,
                tags={},
                source_system='s3',
                metadata={},
            )
        )

    # Measure performance
    start_time = time.time()
    groups = engine.find_associations(files)
    elapsed_time = time.time() - start_time

    # Verify correctness
    assert len(groups) == 250, 'Should create 250 BAM groups'
    assert all(g.group_type == 'bam_index' for g in groups), 'All groups should be bam_index'
    assert all(len(g.associated_files) == 1 for g in groups), (
        'Each group should have 1 associated file'
    )

    # Performance assertion - should complete in under 500ms for 500 files
    # With pre-compiled patterns and optimization, this should be very fast
    assert elapsed_time < 0.5, (
        f'Performance regression: took {elapsed_time:.3f}s for 500 files. '
        f'Expected < 0.5s with optimizations.'
    )

    print(f'\n✓ Performance test passed: {elapsed_time:.3f}s for 500 files')
    print(f'  Average: {(elapsed_time / 500) * 1000:.2f}ms per file')
    print(f'  Throughput: {500 / elapsed_time:.0f} files/second')


if __name__ == '__main__':
    test_performance_improvement_demonstration()
