Feature: Google user sign in
    Testing Google user sign in

  Background: Populate 3 workspaces with admin and read-only users
      Given Multiple workspaces are setup

  Scenario: Wamuyu authenticates using her gmail
      When Wamuyu signs in using her gmail
      Then Wamuyu should be added to Wamuyu's Workspace
      Then Wamuyu should be able to sign into her workspace again
      When Zia creates to create a workspace called wamuyu@gmail.com's Workspace
      Then Zia should receive an empty list as a response

  Scenario: Zia creates wamuyu@gmail.com's Workspace
      When Zia creates wamuyu@gmail.com's Workspace first
      Then Zia should be able to create Wamuyu's gmail workspace
      When Wamuyu tries to sign in using her gmail
      Then Wamuyu should get an error
