variable "private_subnets" {
  description = "List of private subnet IDs used for MSK broker nodes"
  type        = list(string)
}
