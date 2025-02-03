Feature: First user registration
    Testing registration process for very first user

  Background: Ensure that the database is empty for first user registration
      Given An empty database

  Scenario: Only one user can be registered as the first user
      When I create Tony as the first user
      Then The returned response should contain the expected values
      And I am able to authenticate as Tony
      And Tony belongs to the correct workspace with the correct role
      When Tony tries to register Mark as a first user
      Then Tony should not be allowed to register Mark as the first user
      When Tony adds Mark as the second user with a read-only role
      Then The returned response from adding Mark should contain the expected values
      And Mark is able to authenticate himself
