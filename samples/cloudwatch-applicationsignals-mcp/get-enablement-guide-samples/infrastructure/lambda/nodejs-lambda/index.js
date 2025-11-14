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

const { S3Client, ListBucketsCommand } = require('@aws-sdk/client-s3');

const s3 = new S3Client({});

exports.handler = async (event, context) => {
    /**
     * Self-contained Lambda function that generates internal traffic.
     * 
     * Runs for ~10 minutes, calling application functions in a loop.
     */
    console.log('Starting self-contained traffic generation');

    const duration = 600; // Run for 10 minutes (600 seconds)
    const interval = 2; // Call every 2 seconds

    const startTime = Date.now();
    let iteration = 0;

    while ((Date.now() - startTime) / 1000 < duration) {
        iteration++;
        const timestamp = new Date().toLocaleTimeString();

        console.log(`[${timestamp}] Iteration ${iteration}: Generating traffic...`);

        // Call buckets logic
        const bucketsResult = await listBuckets();
        console.log(`[${timestamp}] Buckets check: ${bucketsResult.bucket_count} buckets found`);

        // Sleep between requests
        await new Promise(resolve => setTimeout(resolve, interval * 1000));
    }

    const elapsed = (Date.now() - startTime) / 1000;
    console.log(`Traffic generation completed. Total iterations: ${iteration}, Elapsed time: ${elapsed.toFixed(2)}s`);

    return {
        statusCode: 200,
        body: JSON.stringify({
            message: 'Traffic generation completed',
            iterations: iteration,
            elapsed_seconds: elapsed
        })
    };
};

async function listBuckets() {
    /**
     * List S3 buckets logic.
     */
    try {
        const result = await s3.send(new ListBucketsCommand({}));
        const bucketCount = result.Buckets ? result.Buckets.length : 0;

        return { bucket_count: bucketCount, message: `Found ${bucketCount} buckets` };
    } catch (error) {
        console.error('Error listing buckets:', error);
        return { bucket_count: 0, message: 'Error listing buckets' };
    }
}