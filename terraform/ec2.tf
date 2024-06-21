data "aws_ami" "latest_amazonlinux" {
  most_recent = true

  filter {
    name   = "name"
    values = ["amzn2-ami-kernel-5.10-hvm-*-gp2"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }

  filter {
    name   = "root-device-type"
    values = ["ebs"]
  }

  filter {
    name   = "architecture"
    values = ["x86_64"]
  }

  owners = ["amazon"]
}
resource "aws_instance" "web" {
  ami = data.aws_ami.latest_amazonlinux.id

  iam_instance_profile = aws_iam_instance_profile.studier-server-role.name

  associate_public_ip_address = true
  availability_zone           = "us-east-2a"
  instance_type               = "t2.micro"
  key_name                    = "studier-instance-0"


  source_dest_check = true
  subnet_id         = "subnet-09a8aed2d8e727e84"

  tags = {
    app = "studier"
  }

  user_data = file("${path.module}/ec2/user_data.sh")
  user_data_replace_on_change = true
  vpc_security_group_ids = [aws_security_group.studier_server_rules.id]

  root_block_device {
    delete_on_termination = true
    encrypted             = false
    volume_size           = 8
    volume_type           = "gp2"
  }

  timeouts {}
}

// security group for me ssh AND https
data "external" "my_ip_address" {
  program = ["sh", "-c", <<EOF
echo { \"ip\": \"$(wget -qO- ifconfig.co)\"}
EOF
]
}

resource "aws_security_group" "studier_server_rules" {
  name        = "studier-server-rules"
  description = "allow https and ssh from my computer"
  vpc_id      = var.vpc_id
  tags        = {
    app = "studier"
  }
}
resource "aws_security_group_rule" "public_out" {
  type              = "egress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.studier_server_rules.id
}

// TODO: for now we remove this after each deployment
resource "aws_security_group_rule" "my_computer_ssh" {
  depends_on        = [data.external.my_ip_address]
  type              = "ingress"
  from_port         = 22
  to_port           = 22
  protocol          = "tcp"
  cidr_blocks       = ["${data.external.my_ip_address.result.ip}/32"]
  security_group_id = aws_security_group.studier_server_rules.id
}

resource "aws_security_group_rule" "public_in_https" {
  type              = "ingress"
  from_port         = 443
  to_port           = 443
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.studier_server_rules.id
}