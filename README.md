# aws-attach-secondary-eni-lambda
Persist Private IP in AWS Auto Scaling Group (https://hassanmurtaza.com/persist-private-ip-in-aws-auto-scaling-group)

Thanks to (https://aws.amazon.com/premiumsupport/knowledge-center/attach-second-eni-auto-scaling/) for making work easier for me. 

I extended the solution to detach the secondary eni if it's already attached plus some exceptional handling and retry logic. Don't forget to increase Lambda time out to at least 2-3 minutes. 
