Feature: Retrieving workspace information
    Test different user roles retrieving workspace information

    Background: Populate 3 workspaces with admin and read-only users
        Given Multiple workspaces are setup

    Scenario: Admin retrieving information using workspace ID
        When Suzin retrieves information for workspace Suzin
        Then Suzin should be able to see information regarding workspace Suzin only
        When Carlos retrieves information for workspace Suzin
        Then Carlos should get an error

    Scenario: Non-admins retrieving information using workspace ID
        When Sid retrieves information for workspace Amir
        Then Sid should get an error

    Scenario: Admins retrieving workspaces using user ID
        When Suzin retrieves workspace information for Poornima
        Then Suzin should be able to see information for all workspaces that Poornima belongs to
        When Amir retrieves workspace information for Poornima
        Then Amir should only see information for Poornima in workspace Amir
        When Carlos retrieves workspace information for Poornima
        Then Carlos should get an error again

    Scenario: Non-admins retrieving workspaces using user ID
        When Mark retrieves information for workspace Suzin
        Then Mark should get an error
