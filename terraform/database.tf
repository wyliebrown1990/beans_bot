// rds postgres free tier
resource "aws_db_instance" "studier_database" {
  allocated_storage = 20
  engine            = "postgres"
  engine_version    = "16.3"
  instance_class    = "db.t3.micro"
  username          = "postgres"
  password          = var.database_password

  skip_final_snapshot = true

  identifier = "beans-db"

  storage_encrypted = true # you should always do this

  vpc_security_group_ids  = [aws_security_group.studier_database_security_group.id]
  backup_retention_period = 7   # in days
}


resource "aws_security_group" "studier_database_security_group" {
  name = "mydb1"

  description = "RDS postgres servers (terraform-managed)"
  vpc_id      = var.vpc_id

  # Only postgres in
  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Allow all outbound traffic.
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}