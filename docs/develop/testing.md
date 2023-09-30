# Writing and running tests
!!! note "You need to have installed [Docker](https://docs.docker.com/get-docker/)"

??? warning "Don't run `pytest` directly"
    Unless you have updated your environment variables and started a testing instance
    of postrges and qdrant, the tests will end up writing to your dev environment :weary_cat:

Run tests using

    make tests

This target starts up new postgres and qdrant container for testing. It also sets the
correct environment variables, runs `pytest`, and then destroys the containers.
