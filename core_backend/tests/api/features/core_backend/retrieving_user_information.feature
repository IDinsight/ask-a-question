Feature: Retrieving user information
    Test different user roles retrieving user information

    Background: Populate 3 workspaces with admin and read-only users
        Given Multiple workspaces are setup

    Scenario: Retrieved user information should be limited by role and workspace
        When Suzin retrieves information from all workspaces
        Then Suzin should be able to see all users from all workspaces
        When Mark retrieves information from all workspaces
        Then Mark should only see his own information
        When Carlos retrieves information from all workspaces
        Then Carlos should only see users in his workspaces
        When Poornima retrieves information from her workspaces
        Then Poornima should be able to see all users in her workspaces
