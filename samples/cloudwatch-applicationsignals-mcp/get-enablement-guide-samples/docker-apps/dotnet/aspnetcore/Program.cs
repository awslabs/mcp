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

using Amazon.S3;
using Amazon.S3.Model;

var builder = WebApplication.CreateBuilder(args);

// Configure AWS S3 client
builder.Services.AddAWSService<IAmazonS3>();

var app = builder.Build();

var awsRegion = Environment.GetEnvironmentVariable("AWS_REGION") ?? "us-east-1";

app.MapGet("/health", (ILogger<Program> logger) =>
{
    logger.LogInformation("Health check endpoint called");
    return Results.Json(new { status = "healthy" });
});

app.MapGet("/api/buckets", async (IAmazonS3 s3Client, ILogger<Program> logger) =>
{
    try
    {
        var response = await s3Client.ListBucketsAsync();
        var buckets = response.Buckets.Select(b => b.BucketName).ToList();
        
        logger.LogInformation("Successfully listed {BucketCount} S3 buckets", buckets.Count);
        
        return Results.Json(new { bucket_count = buckets.Count, buckets });
    }
    catch (Exception ex)
    {
        logger.LogError(ex, "S3 client error: {ErrorMessage}", ex.Message);
        return Results.Json(new { error = "Failed to retrieve S3 buckets" }, statusCode: 500);
    }
});

app.Run();