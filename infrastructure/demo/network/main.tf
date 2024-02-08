data "aws_availability_zones" "available" {
  # This is a data source, which means it will not create any resources
  # It will fetch the data from AWS and make it available to use in the code
  # This data source will fetch the list of availability zones for the region specified
  state = "available"
}
