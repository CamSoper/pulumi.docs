import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/pulumi-aws";

const bucket = new aws.s3.Bucket("my-bucket", {
    bucket_name: "pipeline-test-demo",
    versioning: true,
});

const file = new aws.s3.BucketObject("greeting", {
    bucket: bucket.id,
    key: "hello.txt",
    content: "Hello from the pipeline test.",
});

export const url: pulumi.Output<string> = pulumi.interpolate`s3://${bucket.bucket}/${file.key}`;
