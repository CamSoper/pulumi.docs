import * as aws from "@pulumi/aws";

const bucket = new aws.s3.BucketV2("multi-domain-bucket");

export const id = bucket.id;
