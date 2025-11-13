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

package com.example;

import com.amazonaws.services.lambda.runtime.Context;
import com.amazonaws.services.lambda.runtime.RequestHandler;
import software.amazon.awssdk.services.s3.S3Client;
import software.amazon.awssdk.services.s3.model.ListBucketsResponse;
import java.time.LocalTime;
import java.time.format.DateTimeFormatter;
import java.util.Map;
import java.util.HashMap;

public class LambdaHandler implements RequestHandler<Map<String, Object>, Map<String, Object>> {
    
    private final S3Client s3Client = S3Client.create();
    
    @Override
    public Map<String, Object> handleRequest(Map<String, Object> event, Context context) {
        /**
         * Self-contained Lambda function that generates internal traffic.
         * 
         * Runs for ~10 minutes, calling application functions in a loop.
         */
        System.out.println("Starting self-contained traffic generation");
        
        int duration = 600; // Run for 10 minutes (600 seconds)
        int interval = 2; // Call every 2 seconds
        
        long startTime = System.currentTimeMillis();
        int iteration = 0;
        
        while ((System.currentTimeMillis() - startTime) / 1000 < duration) {
            iteration++;
            String timestamp = LocalTime.now().format(DateTimeFormatter.ofPattern("HH:mm:ss"));
            
            System.out.println(String.format("[%s] Iteration %d: Generating traffic...", timestamp, iteration));
            
            // Call buckets logic
            Map<String, Object> bucketsResult = listBuckets();
            System.out.println(String.format("[%s] Buckets check: %s buckets found", timestamp, bucketsResult.get("bucket_count")));
            
            // Sleep between requests
            try {
                Thread.sleep(interval * 1000);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                break;
            }
        }
        
        double elapsed = (System.currentTimeMillis() - startTime) / 1000.0;
        System.out.println(String.format("Traffic generation completed. Total iterations: %d, Elapsed time: %.2fs", iteration, elapsed));
        
        Map<String, Object> response = new HashMap<>();
        response.put("statusCode", 200);
        
        Map<String, Object> body = new HashMap<>();
        body.put("message", "Traffic generation completed");
        body.put("iterations", iteration);
        body.put("elapsed_seconds", elapsed);
        response.put("body", body);
        
        return response;
    }
    
    private Map<String, Object> listBuckets() {
        /**
         * List S3 buckets logic.
         */
        Map<String, Object> result = new HashMap<>();
        try {
            ListBucketsResponse response = s3Client.listBuckets();
            int bucketCount = response.buckets().size();
            
            result.put("bucket_count", bucketCount);
            result.put("message", String.format("Found %d buckets", bucketCount));
        } catch (Exception e) {
            System.err.println("Error listing buckets: " + e.getMessage());
            result.put("bucket_count", 0);
            result.put("message", "Error listing buckets");
        }
        return result;
    }
}