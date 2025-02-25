Feature: Updating workspaces
    Test operations involving updating workspaces

    Background: Populate 3 workspaces with admin and read-only users
        Given Multiple workspaces are setup

    Scenario: Admin users updating workspaces
        When Poornima updates the name and quotas for workspace Amir
        Then The name for workspace Amir should be updated but not the quotas

    Scenario: Non-admin users updating workspaces
        When Zia updates the name and quotas for workspace Carlos
        Then Zia should get an error
