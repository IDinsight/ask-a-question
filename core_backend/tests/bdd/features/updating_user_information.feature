Feature: Updating user information
    Test operations involving updating user information

    Background: Populate 3 workspaces with admin and read-only users
        Given Multiple workspaces are setup

    Scenario: Admin updates admin's information
        When Suzin updates Poornima's name to Poornima_Updated
        Then Poornima's name should be Poornima_Updated
        When Suzin updates Poornima's default workspace to workspace Suzin
        Then Poornima's default workspace should be changed to workspace Suzin
        When Suzin updates Poornima's role to read-only in workspace Suzin
        Then Poornima's role should be read-only in workspace Suzin

    Scenario: Admin updates user's default workspace to a workspace that admin is not a member of
        When Amir updates Poornima's default workspace to workspace Suzin
        Then Amir should get an error

    Scenario: Admin updates read-only user's information
        When Poornima updates Sid's role to admin in workspace Amir
        Then Sid's role should be admin in workspace Amir

    Scenario: Admin updates information for a user not in admin's workspaces
        When Carlos updates Mark's information
        Then Carlos should get an error

    Scenario: Admin changes their user's workspace information to a workspace that the user is not a member of
        When Suzin updates Mark's workspace information to workspace Carlos
        Then Suzin should get an error

    Scenario: Read-only user tries to update their own information
        When Zia tries to update his own role to admin in workspace Carlos
        Then Zia should get an error
