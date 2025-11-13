// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

package com.application.springboot;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;
import software.amazon.awssdk.services.s3.S3Client;
import software.amazon.awssdk.services.s3.model.ListBucketsResponse;

import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@RestController
public class Controller {
    private static final Logger logger = LoggerFactory.getLogger(Controller.class);
    private final S3Client s3Client;
    private final ObjectMapper objectMapper;

    public Controller() {
        this.s3Client = S3Client.builder().build();
        this.objectMapper = new ObjectMapper();
    }

    @GetMapping(value = "/", produces = MediaType.APPLICATION_JSON_VALUE)
    public String index() throws Exception {
        return healthCheck();
    }

    @GetMapping(value = "/health", produces = MediaType.APPLICATION_JSON_VALUE)
    public String healthCheck() throws Exception {
        logger.info("Health check endpoint called");
        Map<String, String> response = Map.of("status", "healthy");
        return objectMapper.writeValueAsString(response) + "\n";
    }

    @GetMapping(value = "/api/buckets", produces = MediaType.APPLICATION_JSON_VALUE)
    public String listBuckets() throws Exception {
        try {
            ListBucketsResponse response = s3Client.listBuckets();
            List<String> buckets = response.buckets().stream()
                    .map(bucket -> bucket.name())
                    .collect(Collectors.toList());
            logger.info("Successfully listed " + buckets.size() + " S3 buckets");
            Map<String, Object> responseMap = Map.of(
                "bucket_count", buckets.size(),
                "buckets", buckets
            );
            return objectMapper.writeValueAsString(responseMap) + "\n";
        } catch (Exception e) {
            logger.error("Exception thrown when Listing Buckets: " + e.getMessage());
            Map<String, String> errorResponse = Map.of("error", "Failed to retrieve S3 buckets");
            return objectMapper.writeValueAsString(errorResponse) + "\n";
        }
    }
}
