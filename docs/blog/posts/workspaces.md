---
authors:
  - Sid
category:
  - Admin App
  - Workspaces
date: 2024-09-02
---

# Introducing Workspaces

Need a better way to organize your projects, data, and user roles?
Meet **Workspaces**—isolated virtual environments designed to simplify access management across multiple projects or teams. With the Workspaces feature, you get a cleaner, more secure, and more flexible approach to data sharing.

<!-- more -->

![Workspace screenshot](./swagger-user-and-workspace-screenshot.png){: .blog-img }

## Why Workspaces?

Previously, every user was a de facto admin with unlimited read/write privileges in their environment. To share data with someone else, you had to reveal your personal credentials, granting them the same authority you had. This setup made it hard to manage sensitive data and user permissions effectively.

### Old Model Concerns

1. **Security Risks** – Sharing credentials was the only way to grant access.
2. **Data Risks** – Shared credentials meant unrestricted read/write privileges.
3. **Resource Sharing** – Users tapped into the same daily API and content quotas, with no clear controls in place.

## The Workspace Approach

Workspaces completely overhaul this system:

1. **Isolated Virtual Environments**
   Each workspace contains its own set of content, quotas, and users, meaning no accidental overlaps or data spills.

2. **Many-to-Many Relationship**
   Users can belong to multiple workspaces, and each workspace can have multiple users. Permissions are specific to each workspace.

3. **Role-based Access**
   There are two main user types out of the box:

   - **Admin**: Full access to create, read, update, and delete data in their assigned workspace(s). They can add or remove users (including other admins), plus create new workspaces or remove their own.
   - **Read-Only**: Can only read existing data in their assigned workspace(s). They can create new workspaces but cannot modify data or user assignments within their current workspace(s).

4. **Finer Control Over Credentials**
   Each user now has a unique username and password. You never need to share personal credentials again—just assign the necessary role in the relevant workspace.

5. **Enforced Security**

   - An admin in one workspace has zero visibility into a different workspace they don’t belong to.
   - Admins must keep at least one admin user in a workspace at all times, preventing orphaned data.
   - Admins can’t change another user’s password, maintaining personal credential integrity.

6. **Managed Resource Sharing**
   - **API Quotas**: Assigned at the workspace level, so usage stays strictly within each workspace.
   - **API Keys**: Linked to workspaces, not individuals. Only admins can generate or update API keys.
   - **Costly Operations**: Potentially restricted to specific roles, ensuring more predictable usage of LLM or other costly operations.

## Major Changes at a Glance

1. **Workspace IDs vs. User IDs**
   We replaced the idea of each user being their own environment with a **workspace-centric** design. Artifacts (like content and tags) now hinge on the workspace ID, not the user ID.

2. **New Database Tables**

   - **WorkspaceDB**: Stores key workspace details like quotas and API keys.
   - **UserWorkspaceDB**: Defines the relationship between users and workspaces, including each user’s role and default workspace.

3. **Easier Role Extensions**
   Though only “Admin” and “Read-Only” roles are standard, you can add additional roles if needed (e.g., `Content-Only`, `Dashboard-Only`). Each new role type may involve extra backend logic, so it’s best to add them sparingly.

## Wrapping Up

By putting Workspaces at the heart of user and data management, we’ve elevated security, streamlined resource usage, and created a flexible foundation for future enhancements. Whether you’re dealing with strictly siloed data, multiple projects, or sensitive information, Workspaces empower you to keep everything organized and under control.

## Doc References

- [Workspaces Overview](../../components/workspaces/index.md)
- [User and Role Management](../../components/workspaces/users/index.md)
- [API Key Management](../../components/admin-app/apikeys/index.md)
