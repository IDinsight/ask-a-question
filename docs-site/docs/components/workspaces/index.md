# Workspaces

![Swagger UD](./swagger-user-and-workspace-screenshot.png)

A workspace is a dedicated virtual environment that contains its own set of data and
users. Workspaces allow you to create isolated environments for different projects or
teams, and assign users with different roles to each workspace. This is useful for
managing access to sensitive data, or for creating separate environments for
development, testing, and production.

## Background

Previous implementation of AAQ assigns every user as an admin user with read/write
privileges. Each user is assigned to their own environment and can only access the
contents (along with feedback, urgency rules, etc.) in their environment. In order for
User 1 to share their contents with User 2, User 1 must give User 2 their credentials
and, as a result, User 2 would have the same read/write privileges with User 1’s
content.

The scenario above is undesirable for the following reasons:

1. **Security risks**: Sharing content requires sharing credentials. User 1 must share
their credentials with every single user that they want to share their content with.

2. **Data risks**: Sharing content with other users means that those users have admin
privileges with the data. Each user can freely add, modify, and delete content without
limitation.

3. **Resource sharing**: When User 1 shares their environment with User 2, User 2 will
use the same API daily quota and content quota as User 1. In addition, User 2 is free
to make calls that uses LLMs without any constraints.

An ideal solution is one which addresses all of the issues above. That is, the solution
should distinguish between different types of users, isolate content to its own
dedicated environment, and better manage resource sharing. To accomplish this, our
solution is as follows.

## Workspace Solution

A workspace is an isolated virtual environment that contains contents that can be
accessed and modified by users assigned to that workspace. Workspaces must be unique
but can contain duplicated content. Users can be assigned to one or more workspaces,
with different roles in each workspace. In other words, there is a **many-to-many
relationship** between users and workspaces.

Users do not have assigned quotas or API keys; rather, a user's API keys and quotas are
tied to those of the workspaces they belong to. Furthermore, users must be unique
across all workspaces.

There are currently 2 different types of users:

1. **Read-Only**: These users are assigned to workspaces and can only read the contents
within their assigned workspaces. They cannot modify existing contents or add new
contents to their workspaces, add or delete users from their workspaces, or delete
workspaces. However, read-only users can create new workspaces.

2. **Admin**: These users are assigned to workspaces and can read and modify the
contents within their assigned workspaces. They can also add or delete users from their
assigned workspaces and can also add new workspaces or delete their own workspaces
(assuming that there is at least one admin user left in that workspace). Admin users
have no control over workspaces that they are not assigned to.

Other user types are possible (e.g., a `Content-Only` user or `Dashboard-Only` user).
Adding a new user type is relatively straightforward. However, it is advised to only
add new user types when absolutely necessary as each new type requires additional
backend logic.

The workspace solution addresses:

1. **Security risks**
    2. Admins only have privileges in their assigned workspaces. An admin in Workspace
       1 has no access to users or contents in Workspace 2.
    3. An admin of a workspace can add new users to their workspace without having to
       share their own credentials.
    4. An admin can change the role of any user in their own workspaces.
    5. Each user is allowed to set up their own username and password, which are
       universal across workspaces.
    6. The password of a user can only be changed by that user. This means that admins
       cannot change the passwords of users in their workspaces. An admin is allowed to
       change their own password.
    7. A user’s name and default workspace (more details below) can be changed by the
       admins of any workspaces that a user belongs to.
8. **Data risks**
    9. An admin of a workspace can choose the user's role when adding users to their
       workspace.
    10. An admin can also remove a user (including other admin users) from their
        workspace.
    11. Each workspace must have at least 1 admin user. Removing the last admin user
        from a workspace poses a data risk since an existing workspace with no users
        means that ANY admin can add users to that workspace---this is essentially the
        scenario when an admin creates a new workspace and then proceeds to add users
        to that newly created workspace. However, existing workspaces can have content;
        thus, we disable the ability to remove the last admin user from a workspace.
     12. **A workspace cannot be deleted**. Deleting a workspace is currently not
        allowed since the process involves removing users from the workspace, possibly
        reassigning those users to other default workspaces, and deleting/archiving
        artifacts such as content, tags, urgency rules, and feedback.
13. **Resource sharing**
     14. When a new workspace is created, the user that creates the workspace is
         automatically assigned as an admin user in that workspace. They can then add
         other users to the workspace, including other admin users.
     15. Admins set the API daily quota and content quota of a workspace when the
         workspace is created. These quotas can only be updated by the workspace admins.
     16. The API key is now tied to workspaces rather than individual users. Only
         admins can generate a new API key.
     17. Costly resources (such as making calls to LLM providers) can be limited to
         certain user types (e.g., `LLM` users).

## Major Changes (10,000 Foot View)

The old AAQ design uses the user's ID as the unique key for authentication, creating
access tokens, and filtering users, content, tags, etc. In other words, each user was
assigned to their own “workspace” with their user ID as the unique identifier for that
workspace.

The new design effectively replaces every use of user ID with workspace ID and takes
the user's role in the current workspace into account when accessing certain endpoints.
In effect, operations that modify artifacts can only be done by admin users. Read-only
users can only view existing artifacts.

There are 2 new tables:

1. `WorkspaceDB`: This table manages workspace information, such as API and content
quotas
2. `UserWorkspaceDB`: This table manages the relationship between users and workspaces,
including the user's role in each workspace and a user's default workspace.
