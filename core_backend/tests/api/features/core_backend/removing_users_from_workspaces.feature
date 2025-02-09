Feature: Removing users from workspaces
    Test operations involving removing users from workspaces

    Background: Populate 3 workspaces with admin and read-only users
        Given Multiple workspaces are setup

    Scenario: Each workspace must have at least one (admin) user
        When Carlos removes Suzin from workspace Carlos
        Then Suzin should only belong to workspace Suzin and workspace Amir
        When Carlos then tries to remove himself from workspace Carlos
        Then Carlos should get an error

    Scenario: Admin can remove user from their own workspace but not a user in a workspace that the admin is not a member of
        When Amir removes Sid from workspace Amir
        Then Sid no longer belongs to workspace Amir
        And Sid can no longer authenticate
        When Amir tries to remove Poornima from workspace Suzin
        Then Amir should get an error

    Scenario: An admin can remove themselves from a workspace if the workspace has multiple admins
        When Poornima removes herself from workspace Amir
        Then Poornima is required to switch workspaces to workspace Suzin

    Scenario: If a (admin) user removes themselves from the only workspace they belong to and they are signed into that workspace, then the user is deleted and reauthentication is required
        When Carlos removes himself from workspace Carlos
        Then Carlos no longer belongs to workspace Carlos
        And Carlos can no longer authenticate
        And Reauthentication is required
