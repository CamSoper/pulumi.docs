import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";

const bucket = new aws.s3.BucketV2("content-bucket", {
    bucket: "pipeline-test-content-bucket",
});

const versioning = new aws.s3.BucketVersioningV2("content-bucket-versioning", {
    bucket: bucket.id,
    versioningConfiguration: {
        status: "Enabled",
    },
});

export const bucketName = bucket.id;
export const bucketArn = bucket.arn;
