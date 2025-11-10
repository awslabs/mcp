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

"""Unit tests for pattern matching algorithms."""

from awslabs.aws_healthomics_mcp_server.search.pattern_matcher import PatternMatcher


class TestPatternMatcher:
    """Test cases for PatternMatcher class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.pattern_matcher = PatternMatcher()

    def test_exact_match_score(self):
        """Test exact matching algorithm."""
        # Test exact matches (case-insensitive)
        assert self.pattern_matcher._exact_match_score('test', 'test') == 1.0
        assert self.pattern_matcher._exact_match_score('TEST', 'test') == 1.0
        assert self.pattern_matcher._exact_match_score('Test', 'TEST') == 1.0

        # Test non-matches
        assert self.pattern_matcher._exact_match_score('test', 'testing') == 0.0
        assert self.pattern_matcher._exact_match_score('different', 'test') == 0.0

    def test_substring_match_score(self):
        """Test substring matching algorithm."""
        # Test substring matches
        score = self.pattern_matcher._substring_match_score('testing', 'test')
        assert score > 0.0
        assert score <= 0.8  # Max score for substring matches

        # Test coverage-based scoring
        score1 = self.pattern_matcher._substring_match_score('test', 'test')
        score2 = self.pattern_matcher._substring_match_score('testing', 'test')
        assert score1 > score2  # Better coverage should score higher

        # Test case insensitivity
        assert self.pattern_matcher._substring_match_score('TESTING', 'test') > 0.0

        # Test non-matches
        assert self.pattern_matcher._substring_match_score('different', 'test') == 0.0

    def test_fuzzy_match_score(self):
        """Test fuzzy matching algorithm."""
        # Test similar strings
        score = self.pattern_matcher._fuzzy_match_score('test', 'tset')
        assert score > 0.0
        assert score <= 0.6  # Max score for fuzzy matches

        # Test threshold behavior
        score_high = self.pattern_matcher._fuzzy_match_score('test', 'test')
        score_low = self.pattern_matcher._fuzzy_match_score('test', 'xyz')
        assert score_high > score_low

        # Test below threshold returns 0
        score = self.pattern_matcher._fuzzy_match_score('completely', 'different')
        assert score == 0.0

    def test_calculate_match_score_single_pattern(self):
        """Test match score calculation with single pattern."""
        # Test exact match gets highest score
        score, reasons = self.pattern_matcher.calculate_match_score('test', ['test'])
        assert score == 1.0
        assert 'Exact match' in reasons[0]

        # Test substring match
        score, reasons = self.pattern_matcher.calculate_match_score('testing', ['test'])
        assert 0.0 < score < 1.0
        assert 'Substring match' in reasons[0]

        # Test fuzzy match
        score, reasons = self.pattern_matcher.calculate_match_score('tset', ['test'])
        assert 0.0 < score < 1.0
        assert 'Fuzzy match' in reasons[0]

    def test_calculate_match_score_multiple_patterns(self):
        """Test match score calculation with multiple patterns."""
        # Test multiple patterns - should take best score
        score, reasons = self.pattern_matcher.calculate_match_score('testing', ['test', 'nomatch'])
        assert score > 0.0
        assert len(reasons) >= 1

        # Test multiple matching patterns get bonus
        score, reasons = self.pattern_matcher.calculate_match_score(
            'test_sample', ['test', 'sample']
        )
        assert score > 0.5  # Should get bonus for multiple matches (adjusted expectation)
        assert len(reasons) >= 2

    def test_calculate_match_score_edge_cases(self):
        """Test edge cases for match score calculation."""
        # Empty patterns
        score, reasons = self.pattern_matcher.calculate_match_score('test', [])
        assert score == 0.0
        assert reasons == []

        # Empty text
        score, reasons = self.pattern_matcher.calculate_match_score('', ['test'])
        assert score == 0.0
        assert reasons == []

        # Empty pattern in list
        score, reasons = self.pattern_matcher.calculate_match_score('test', ['', 'test'])
        assert score == 1.0  # Should ignore empty pattern

        # Whitespace-only pattern
        score, reasons = self.pattern_matcher.calculate_match_score('test', ['   ', 'test'])
        assert score == 1.0  # Should ignore whitespace-only pattern

    def test_match_file_path(self):
        """Test file path matching."""
        file_path = '/path/to/sample1_R1.fastq.gz'

        # Test matching against full path
        score, reasons = self.pattern_matcher.match_file_path(file_path, ['sample1'])
        assert score > 0.0
        assert len(reasons) > 0

        # Test matching against filename only
        score, reasons = self.pattern_matcher.match_file_path(file_path, ['fastq'])
        assert score > 0.0

        # Test matching against base name (without extension)
        score, reasons = self.pattern_matcher.match_file_path(file_path, ['sample1_R1'])
        assert score > 0.0

        # Test no match
        score, reasons = self.pattern_matcher.match_file_path(file_path, ['nomatch'])
        assert score == 0.0

    def test_match_file_path_edge_cases(self):
        """Test edge cases for file path matching."""
        # Empty file path
        score, reasons = self.pattern_matcher.match_file_path('', ['test'])
        assert score == 0.0
        assert reasons == []

        # Empty patterns
        score, reasons = self.pattern_matcher.match_file_path('/path/to/file.txt', [])
        assert score == 0.0
        assert reasons == []

    def test_match_tags(self):
        """Test tag matching."""
        tags = {'project': 'genomics', 'sample_type': 'tumor', 'environment': 'production'}

        # Test matching tag values
        score, reasons = self.pattern_matcher.match_tags(tags, ['genomics'])
        assert score > 0.0
        assert 'Tag' in reasons[0]

        # Test matching tag keys
        score, reasons = self.pattern_matcher.match_tags(tags, ['project'])
        assert score > 0.0

        # Test matching key:value format
        score, reasons = self.pattern_matcher.match_tags(tags, ['project:genomics'])
        assert score > 0.0

        # Test no match
        score, reasons = self.pattern_matcher.match_tags(tags, ['nomatch'])
        assert score == 0.0

        # Test tag penalty (should be slightly lower than path matches)
        tag_score, _ = self.pattern_matcher.match_tags(tags, ['genomics'])
        path_score, _ = self.pattern_matcher.match_file_path('genomics', ['genomics'])
        assert tag_score < path_score

    def test_match_tags_edge_cases(self):
        """Test edge cases for tag matching."""
        # Empty tags
        score, reasons = self.pattern_matcher.match_tags({}, ['test'])
        assert score == 0.0
        assert reasons == []

        # Empty patterns
        score, reasons = self.pattern_matcher.match_tags({'key': 'value'}, [])
        assert score == 0.0
        assert reasons == []

    def test_extract_filename_components(self):
        """Test filename component extraction."""
        # Test regular file
        components = self.pattern_matcher.extract_filename_components('/path/to/sample1.fastq')
        assert components['full_path'] == '/path/to/sample1.fastq'
        assert components['filename'] == 'sample1.fastq'
        assert components['base_filename'] == 'sample1.fastq'
        assert components['base_name'] == 'sample1'
        assert components['extension'] == 'fastq'
        assert components['compression'] is None
        assert components['directory'] == '/path/to'

        # Test compressed file
        components = self.pattern_matcher.extract_filename_components('/path/to/sample1.fastq.gz')
        assert components['filename'] == 'sample1.fastq.gz'
        assert components['base_filename'] == 'sample1.fastq'
        assert components['base_name'] == 'sample1'
        assert components['extension'] == 'fastq'
        assert components['compression'] == 'gz'

        # Test bz2 compression
        components = self.pattern_matcher.extract_filename_components('sample1.fastq.bz2')
        assert components['compression'] == 'bz2'
        assert components['base_filename'] == 'sample1.fastq'

        # Test multiple extensions
        components = self.pattern_matcher.extract_filename_components('reference.fasta.fai')
        assert components['base_name'] == 'reference'
        assert components['extension'] == 'fasta.fai'

        # Test no extension
        components = self.pattern_matcher.extract_filename_components('/path/to/filename')
        assert components['base_name'] == 'filename'
        assert components['extension'] == ''

        # Test no directory
        components = self.pattern_matcher.extract_filename_components('filename.txt')
        assert components['directory'] == ''

    def test_genomics_specific_patterns(self):
        """Test patterns specific to genomics files."""
        # Test FASTQ R1/R2 patterns
        score, _ = self.pattern_matcher.match_file_path('sample1_R1.fastq.gz', ['sample1'])
        assert score > 0.0

        # Test BAM/BAI patterns
        score, _ = self.pattern_matcher.match_file_path('aligned.bam', ['aligned'])
        assert score > 0.0

        # Test VCF patterns
        score, _ = self.pattern_matcher.match_file_path('variants.vcf.gz', ['variants'])
        assert score > 0.0

        # Test reference patterns
        score, _ = self.pattern_matcher.match_file_path('reference.fasta', ['reference'])
        assert score > 0.0

    def test_case_insensitive_matching(self):
        """Test that all matching is case-insensitive."""
        test_cases = [
            ('TEST', ['test']),
            ('Test', ['TEST']),
            ('tEsT', ['TeSt']),
        ]

        for text, patterns in test_cases:
            score, _ = self.pattern_matcher.calculate_match_score(text, patterns)
            assert score == 1.0, f'Case insensitive match failed for {text} vs {patterns}'

    def test_special_characters_in_patterns(self):
        """Test handling of special characters in patterns."""
        # Test patterns with underscores
        score, _ = self.pattern_matcher.match_file_path('sample_1_R1.fastq', ['sample_1'])
        assert score > 0.0

        # Test patterns with hyphens
        score, _ = self.pattern_matcher.match_file_path('sample-1-R1.fastq', ['sample-1'])
        assert score > 0.0

        # Test patterns with dots
        score, _ = self.pattern_matcher.match_file_path('sample.1.R1.fastq', ['sample.1'])
        assert score > 0.0

    def test_performance_with_long_patterns(self):
        """Test performance with long patterns and text."""
        long_text = 'a' * 1000
        long_pattern = 'a' * 500

        # Should not raise exception and should complete reasonably quickly
        score, reasons = self.pattern_matcher.calculate_match_score(long_text, [long_pattern])
        assert score > 0.0
        assert len(reasons) > 0

    def test_unicode_handling(self):
        """Test handling of unicode characters."""
        # Test unicode in patterns and text
        score, _ = self.pattern_matcher.calculate_match_score('tëst', ['tëst'])
        assert score == 1.0

        # Test mixed unicode and ascii
        score, _ = self.pattern_matcher.calculate_match_score('tëst_file', ['tëst'])
        assert score > 0.0
