aws cloudformation create-stack --stack-name codepipeline-ecr-build-sf-execution --template-body file://cfn/pipeline-cfn.yaml  --parameters file://cfn/params.json --capabilities CAPABILITY_NAMED_IAM

# aws cloudformation update-stack --stack-name codepipeline-ecr-build-sf-execution --template-body file://cfn/pipeline-cfn.yaml  --parameters file://cfn/params.json --capabilities CAPABILITY_NAMED_IAM