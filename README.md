# aws-attach-secondary-eni-lambda
Persist Private IP in AWS Auto Scaling Group (https://hassanmurtaza.com/persist-private-ip-in-aws-auto-scaling-group)

Thanks to (https://aws.amazon.com/premiumsupport/knowledge-center/attach-second-eni-auto-scaling/) for making work easier for me. 

I extended the solution to detach the secondary eni if it's already attached to EC2 instance plus some exceptional handling and retry logic.

Don't forget to increase Lambda time out to at least 2-3 minutes and attach appropriate role.

```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "VisualEditor0",
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "arn:aws:logs:*:*:*"
        },
        {
            "Sid": "VisualEditor1",
            "Effect": "Allow",
            "Action": [
                "ec2:CreateNetworkInterface",
                "ec2:DescribeInstances",
                "ec2:DetachNetworkInterface",
                "autoscaling:CompleteLifecycleAction",
                "ec2:DescribeNetworkInterfaces",
                "ec2:DeleteNetworkInterface",
                "ec2:AttachNetworkInterface"
            ],
            "Resource": "*"
        },
        {
            "Sid": "VisualEditor2",
            "Effect": "Allow",
            "Action": "logs:CreateLogGroup",
            "Resource": "arn:aws:logs:*:*:*"
        }
    ]
}
```
