# What is Align Score?

_"AlignScore, a metric for automatic_ __factual consistency evaluation of text pairs__" is
introduced in [AlignScore: Evaluating Factual Consistency with a Unified Alignment Function](https://arxiv.org/abs/2305.16739)
by Yuheng Zha, Yichi Yang, Ruichen Li and Zhiting Hu

AlignScore returns a score between `0` (Not consistent)
and `1` (Perfectly consistent) for if the given _claims_ are consistent with the
provided _contexts_.


<div class="grid cards" markdown>

-   :octicons-gear-16:{ .lg .middle } __Deployment__

    ---

    Deploying the AlignScore service. Configuring AAQ to use AlignScore.

    [:octicons-arrow-right-24: More info](./deployment.md)

-   :material-test-tube:{ .lg .middle } __Testing__

    ---

    Testing how well AlignScore works for your context

    [:octicons-arrow-right-24: More info](./testing.md)
