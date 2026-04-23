import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";

const certCertificate = new aws.acm.Certificate("cert", {
    domainName: "example.com",
    validationMethod: "DNS",
    tags: {
        Environment: "pipeline-test",
        ManagedBy: "pulumi",
    },
});

export const certificateArn = certCertificate.arn;
