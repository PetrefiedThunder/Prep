resource "aws_msk_configuration" "main" {
  name              = "prep-primary-config"
  kafka_versions    = ["3.6.0"]
  server_properties = <<-EOT
auto.create.topics.enable = false
log.retention.hours = 168
message.max.bytes = 262144
  EOT
}
