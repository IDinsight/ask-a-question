Feature: Resetting user passwords
    Ensure that users can only reset their own passwords

    Background: Populate 3 workspaces with admin and read-only users
        Given Multiple workspaces are setup

    Scenario: Users can only reset their own passwords
        When Suzin tries to reset her own password
        Then Suzin should be able to reset her own password
        When Suzin tries to reset Mark's password
        Then Suzin gets an error
        When Mark tries to reset Suzin's password
        Then Mark gets an error
        When Poornima tries to reset Suzin's password
        Then Poornima gets an error
