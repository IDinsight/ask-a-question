Feature: Creating workspaces
    Test operations involving creating workspaces

    Background: Populate 3 workspaces with admin and read-only users
        Given Multiple workspaces are setup

    Scenario: If users create workspaces, they are added to those workspaces as admins iff the workspaces did not exist before
        When Zia creates workspace Zia
        Then Zia should be added as an admin to workspace Zia with the expected quotas
        And Zia's default workspace should still be workspace Carlos
        When Sid tries to create workspace Amir
        Then No new workspaces should be created by Sid
        And Sid should still be a read-only user in workspace Amir
