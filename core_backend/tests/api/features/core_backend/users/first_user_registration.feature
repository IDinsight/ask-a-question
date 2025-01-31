Feature: First user registration
    Testing registration process for very first user

  Background: Ensure that the database is empty for first user registration
      Given there are no current users or workspaces
      And a username and password for registration

  Scenario: Successful first user created
      When I call the endpoint to create the first user
      Then the returned response should contain the expected values
      And I am able to authenticate as the first user
      And the first user belongs to the correct workspace with the correct role
