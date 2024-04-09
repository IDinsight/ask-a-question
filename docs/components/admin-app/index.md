# The Admin App



<div class="grid cards" markdown>

-   :material-database:{ .lg .middle .red} __Manage content__

    ---

    Allows you to view, create, edit, or delete content.

    [:octicons-arrow-right-24: More info](./manage-content.md)

-   :material-chat-question:{ .lg .middle } __Playground__

    ---

    Allows you to experiment with the Question-Answering Service. You can
    use this to simulate a question being asked by a user within a chat window

    [:octicons-arrow-right-24: More info](./playground.md)

-   :material-view-dashboard:{ .lg .middle } __Content Manager's Dashboard (Coming Soon)__

    ---

    Allows you to see statistices like which content is most frequently being
    used, or the feedback from users on responses provided by the service.

-   :material-monitor-dashboard: __Engineer's Dashboard (Coming Soon)__

    ---

    Shows you technical performance of the application like uptime, throughput,
    response time, and the number of responses by HTTP response codes


</div>

## Accessing the Admin app

If you have the [application running](../../deployment/quick-setup.md), you can access the admin app at:

    https://[DOMAIN]/

or if you are using the [dev](../../develop/setup.md) setup:

    http://localhost:3000/

### Access Levels

There are two logins - `readonly` and `fullaccess` with different access levels.
See [Access Level](./access-level.md) for more details.
