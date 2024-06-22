output "ec2_ip_address" {
  value = aws_instance.beans_bot_server.public_ip
}