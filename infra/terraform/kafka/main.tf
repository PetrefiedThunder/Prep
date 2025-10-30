module "msk" {
  source  = "terraform-aws-modules/msk/aws"
  version = "~> 4.0"

  cluster_name           = "prep-primary"
  number_of_broker_nodes = 6

  broker_node_group_info = {
    instance_type   = "kafka.m7g.large"
    ebs_volume_size = 1000
    client_subnets  = var.private_subnets
    security_groups = [aws_security_group.msk.id]
  }

  configuration_info = {
    arn      = aws_msk_configuration.main.arn
    revision = 1
  }
}

resource "aws_glue_schema" "pos_txn" {
  schema_name       = "prep.pos.PosTxn"
  data_format       = "AVRO"
  schema_definition = file("${path.module}/../contracts/avro/pos_txn.avsc")
}
