Feature: Creating new users and adding existing users to workspaces
    Testing adding new users to workspaces and existing users to other workspaces

  Background: Populate 3 workspaces with admin and read-only users
      Given Multiple workspaces are setup

  Scenario: Creating a new user in an existing workspace
      When Carlos adds Tanmay to workspace Carlos
      Then Tanmay should be added to workspace Carlos

  Scenario: Creating a new user in a workspace that does not exist
      When Carlos adds Jahnavi to workspace Jahnavi
      Then Carlos should get an error

  Scenario: Adding an existing user to a workspace that does not exist
      When Suzin adds Mark to workspace Mark
      Then Suzin should get an error

  Scenario: Adding an existing user to an existing workspace
      When Suzin adds Mark to workspace Amir
      Then Mark should be added to workspace Amir
