Feature: Multiple workspaces
    Test admin and user permissions with multiple workspaces

    Background: Populate 3 workspaces with admin and read-only users
        Given Multiple workspaces are setup

    Scenario: Users can only switch to their own workspaces
        When Suzin switches to Workspace Carlos and Workspace Amir
        Then Suzin should be able to switch to both workspaces
        When Mark tries to switch to Workspace Carlos and Workspace Amir
        Then Mark should get an error
        When Carlos tries to switch to Workspace Suzin and Workspace Amir
        Then Carlos should get an error
        When Zia tries to switch to Workspace Suzin and Workspace Amir
        Then Zia should get an error
        When Amir tries to switch to Workspace Suzin and Workspace Carlos
        Then Amir should get an error
        When Sid tries to switch to Workspace Suzin and Workspace Carlos
        Then Sid should get an error
        When Poornima switches to Workspace Suzin
        Then Poornima should be able to switch to Workspace Suzin
