Feature: Removing users from workspaces
    Test operations involving removing users from workspaces

    Background: Populate 3 workspaces with admin and read-only users
        Given Multiple workspaces are setup

    Scenario: Removing Suzin from workspace Carlos is OK, but then removing Carlos from workspace Carlos is not allowed
        When Carlos removes Suzin from workspace Carlos
        Then Suzin should only belong to workspace Suzin and workspace Amir
        When Carlos then tries to remove himself from workspace Carlos
        Then Carlos should get an error

    Scenario: Amir removes Sid from workspace Amir, then tries to remove Poornima from workspace Suzin
        When Amir removes Sid from workspace Amir
        Then Sid no longer belongs to workspace Amir
        And Sid can no longer authenticate
        When Amir tries to remove Poornima from workspace Suzin
        Then Amir should get an error

    Scenario: Poornima removes herself from workspace Amir
        When Poornima removes herself from workspace Amir
        Then Poornima is required to switch workspaces to workspace Suzin

    Scenario: Carlos removes himself from workspace Carlos
        When Carlos removes himself from workspace Carlos
        Then Carlos no longer belongs to workspace Carlos
        And Carlos can no longer authenticate
        And Reauthentication is required
