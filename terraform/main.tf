terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.33.0"
    }
  }

  required_version = ">= 1.7.1"
}

provider "aws" {
  region = "us-east-1"
}

// log group for ec2
resource "aws_cloudwatch_log_group" "beans_bot_logs" {
  name              = "beans_bot_logs"
  retention_in_days = 14

  tags = {
    app = "beans_bot"
  }
}


// ec2 role
resource "aws_iam_instance_profile" "beans-bot-server-role" {
  name = "beans-bot-server-role"
  role = aws_iam_role.server-role.name
}

resource "aws_iam_role" "server-role" {
  name = "beans-bot-server-role"

  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [
      {
        Action    = "sts:AssumeRole"
        Effect    = "Allow"
        Sid       = ""
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      },
    ]
  })

  tags = {
    app = "beans_bot"
  }
}

resource "aws_iam_policy" "server-policy" {
  name        = "server-policy"
  path        = "/"
  description = "policy for interacting"

  policy = file("${path.module}/policy/ec2-policy.template.json")
}

resource "aws_iam_role_policy_attachment" "attach-cloud-watch-agent-needs" {
  role       = aws_iam_role.server-role.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy"
}

resource "aws_iam_role_policy_attachment" "attach-other-needs" {
  role       = aws_iam_role.server-role.name
  policy_arn = aws_iam_policy.server-policy.arn
}
