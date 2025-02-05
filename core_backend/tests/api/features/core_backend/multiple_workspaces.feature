Feature: Multiple workspaces
    Test admin and user permissions with multiple workspaces

    Background: Populate 3 workspaces with admin and read-only users
        Given I create Tony as the first user in Workspace_Tony
        And Tony adds Mark as a read-only user in Workspace_Tony
        And Tony creates Workspace_Carlos
        And Tony adds Carlos as the first user in Workspace_Carlos with an admin role
        And Carlos adds Zia as a read-only user in Workspace_Carlos
        And Tony creates Workspace_Amir
        And Tony adds Amir as the first user in Workspace_Amir with an admin role
        And Amir adds Poornima as an admin user in Workspace_Amir
        And Amir adds Sid as a read-only user in Workspace_Amir
        And Tony adds Poornima as an adin user in Workspace_Tony

    Scenario: Users can only log into their own workspaces

    Scenario: Any user can reset their own password

    Scenario: Any user can retrieve information about themselves

    Scenario: Admin users can only see details for users in their workspace

    Scenario: Admin users can add users to their own workspaces

    Scenario: Admin users can remove users from their own workspaces

    Scenario: Admin users can change user roles for their own users

    Scenario: Admin users can change user names for their own users

    Scenario: Admin users can change user default workspaces for their own users
