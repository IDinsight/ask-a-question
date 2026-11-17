Feature: Switching workspaces
    Test admin and user permissions when switching between workspaces

    Background: Populate 3 workspaces with admin and read-only users
        Given Multiple workspaces are setup

    Scenario: Users can only switch to their own workspaces
        When Suzin switches to workspace Carlos and workspace Amir
        Then Suzin should be able to switch to both workspaces
        When Mark tries to switch to workspace Carlos and workspace Amir
        Then Mark should get an error
        When Carlos tries to switch to workspace Suzin and workspace Amir
        Then Carlos should get an error
        When Zia tries to switch to workspace Suzin and workspace Amir
        Then Zia should get an error
        When Amir tries to switch to workspace Suzin and workspace Carlos
        Then Amir should get an error
        When Sid tries to switch to workspace Suzin and workspace Carlos
        Then Sid should get an error
        When Poornima switches to workspace Suzin
        Then Poornima should be able to switch to workspace Suzin
