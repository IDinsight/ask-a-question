# Testing AlignScore

You may wish to check the performance of AlignScore against your task and context. You
can also use the performance on the tests to set the best threshold score(1).
{ .annotate }

1.   See [Deployment](./deployment.md#other-configuration) for what this is.

In this section we describe how to setup the data, the infrastructure, and run the tests.

## Setup the data

We provide tests and some data to get you started but it highly recommended that you
create some new test data that is realistics and appropriate to your context.

The test data can be found in:
```
tests/rails/data/llm_response_in_context.yaml
```
This shows you the format expected by the tests.

## Setup the infrastructure

In order to run these test, you need to setup the AlignScore service.
See instructions in [Dev setup](./deployment.md#dev-setup) on how to setup a local
container.

## Run the tests

Once you have data ready and the AlignScore container running, you are ready to run
the tests:

```
cd ../../core_backend
pytest -m rails -k "test_alignScore" -vv
```
