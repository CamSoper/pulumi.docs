# Pulumi Components intro

Pulumi Components are a way to make reusable pices of infrastucture code. Instead of copying & pasting resoruce definitions all over your repos, you can wrap them into components for better orginization.

## What is a Component?

A Component is basically a **class** that contain multiple Pulumi resources. It can help you:
- reduce dupplication
- enforce consistant best practices  
- Encapsulate complexe setup logic

but sometimes, people forget too:  
1. Use proper naming convetions
2. Document paramters corectly
3. Keep code testible

### Why are Components Important

Components help teams scale infrastucture as code. they are very usefull for:
1. Multi-cloud applications
2. Standardazing security
3. speeding up onboarding for new devs

## Example: a simple S3 Bucket component

```typescript
import * as aws from "@pulumi/aws";

export class MyBucket extends pulumi.ComponentResource {
    constructor(name: string, opts?: pulumi.ComponentResourceOptions) {
        super("pkg:index:MyBucket", name, {}, opts);

        const bucket = new aws.s3.Bucket(name, {
            acl: "private"
        });
    }
}
````

[Learn more about Components](https://www.pulumi.com/docs/concepts/components)

### conclusion

Components are realy powerfull, but only if used consistantly and documented clearly.