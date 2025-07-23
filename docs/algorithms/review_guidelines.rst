.. _algorithm-review-guidelines:

Production-ready algorithm guidelines
====================================

To safeguard data privacy and ensure that individual-level data does not leave the data
stations, it is important to restrict the set of algorithms that can be run by
researchers to a set of well-validated algorithms. This page describes the guidelines
for reviewing algorithms to ensure that they are of high quality.

In order to create a basic vantage6 algorithm, an algorithm developer should
first follow the :ref:`algo-dev-guide`. This will allow them to create a basic
algorithm. However, to create a production-ready algorithm, the algorithm developer
should extend the basic algorithm with e.g. documentation, (unit) tests and
privacy-enhancing measures. This page provides a checklist for algorithm
developers so that they may produce algorithms of high quality.

The best place to review vantage6 algorithms is in the :ref:`algorithm store <algorithm-store>`.
The store can have appropriate :ref:`policies <algorithm-store-policies>` in place
to ensure that the algorithms are of high quality.
The checklist below also provides pointers to algorithm reviewers:
the questions that the developer should ask themselves, should be repeated by
the reviewers. Independent reviewers (i.e. not the same person(s) as who wrote
the algorithm) should be assigned during the review process in the vantage6 algorithm
store, as described in :ref:`algorithm-store-review-process`.

Below are questions that algorithm developers and reviewers should address to
produce a high-quality, trustworthy algorithm. Note that this list is rather
general so that it is valid for all algorithms, and can therefore not be fully
exhaustive: for a particular algorithm, there may be additional points to
address that are specific to that algorithm.

.. _algorithm_review_checklist:

Reviewing code and documentation
--------------------------------

Questions to ask yourself when developing or reviewing the algorithm may include,
but are not limited to:

- Completeness

  - Which use cases are supported?
  - Can all the research question(s) be answered that should be answered with
    this algorithm? If not, would extending the algorithm suffice to answer the
    remaining questions, or should that be part of another algorithm?

- Availability and security:

  - Does the code fulfill the project's requirements in being either closed
    source or open source?
  - Is the algorithm image available from a Docker registry? Is the image
    available to anyone or only to authenticated clients, and is this in line
    with the project requirements?
  - Is the algorithm image digitally signed (if required by your project)?
  - Is the algorithm build process transparent? Is the image produced by a pipeline (or
    similar) or is it built locally? Can you verify that the image contains the proper
    algorithm code?

- Code quality:

  - Is the code understandable? For example:

    - Are code standards used? E.g. PEP8 or black for Python
    - Are clear variable and function names used?
    - Does the code contain comments to explain the code (if necessary)?
    - Is the code properly structured in functions and modules that are short
      enough to easily comprehend?
  - Is there a README that explains the contents of the repository?
  - Is the algorithm implementation structured properly?

    - Are all the subtasks that are created actually necessary for the
      execution of the algorithm?
    - Are all of the function arguments required to properly execute the algorithm?
    - Does the algorithm properly output the results? Is a part of the desired
      result missing or are data shared that are not necessary to share?
    - Could the compute time be reduced by a more efficient implementation of
      the algorithm? This is especially relevant if the algorithm is
      computationally heavy. Note that (unit) tests can help evaluate
      potential bottlenecks.

- Correctness and testing:

  - Are sample datasets provided to test the algorithm?

    - Ideally, sample datasets resemble the real data to some extent, so that
      the algorithm produces sensible results. Synthetic data is recommended.
  - Are proper (unit) tests provided so that the algorithm can be tested
    locally?
  - Does the algorithm work on the sample dataset?

    - This may be tested both within vantage6 as well as running mock tests
      using the vantage6 mock algorithm client.
  - Does the algorithm support all types of datasets (e.g. CSV, SQL, RDF) that
    are supposed to be supported?
  - Are the tests extensive enough? Are there any cases you can find when the
    algorithm will not work (while it should)?

    - In case of insufficient testing, reviewers should independently test
      scenarios that the developers have not tested.
  - Is the result obtained from the sample dataset mathematically/scientifically
    correct and reproducible?

- Is the algorithm documented properly?

  - Is there a clear explanation of the analysis that has been implemented?
  - Is there a clear explanation of which use cases are supported? And, if
    relevant, which are not?
  - Is there a clear explanation of how the algorithm has been implemented?
  - Is there a clear explanation of how to run the algorithm?
  - Is there a clear explanation of how to test the algorithm (preferably
    locally)?
  - Has an analysis of the potential privacy risks (as described in
    :ref:`prevent-common-federated-learning-exploits`) been included in the
    documentation? If there are specific risks associated with the algorithm,
    is it understandably explained how can they be mitigated?

- Privacy risks:

  - Is the (non-personal) data that is being shared with the central server the
    minimum of what is necessary to answer the research question? Is this the
    case for both the final results and the results of subtasks?
  - Is there a risk that sensitive data are printed in the algorithm logs?
  - Even if it is the absolute minimum, is the data that is being sent back to
    the central server acceptable?

    - Does it (potentially) disclose detailed information of individual
      patients/records?
    - Is there a risk of identification of individual patients/records?
    - Are there mitigations possible that would reduce the risk of disclosing
      record-level information without making the algorithm wrong or unusable?
  - Checks on database size. This is e.g. relevant when calculating the average
    on a single record, which would normally not be allowed because it leaks the
    individual value. Also, depending on the algorithm, proper
    :ref:`cell suppression <https://nces.ed.gov/fcsm/dpt/content/3-2-2-1>`_ may be
    necessary.

    - Are there checks on data size where necessary?
    - If the algorithm creates some data subgroups, are analyses rejected if the
      subgroup is so small that individual records may be exposed?
    - If the sample size is too small to share the results, is the data station
      properly excluded from the analysis? Does the algorithm properly report
      that the data station was excluded for this reason?

  - Is the algorithm at risk for one or more of the federate learning exploits
    described in :ref:`prevent-common-federated-learning-exploits`?
  - If a server administrator, node administrator or researcher tries to gain
    access to your data, does the algorithm properly protect the data from them?

.. _prevent-common-federated-learning-exploits:

Prevent common federated learning exploits
-----------------------------------------

As both algorithm developer and reviewer, it is important to be aware of common
exploits, and to analyze if the algorithm could be impacted by them. If the
answer is yes, a plan should be put in place to avoid the attacks.

Note that the table below contains attacks in federated learning that are aimed
at reconstructing record-level data. This list could be extended in the future
if new attacks are found. Note that most of the attacks below are only relevant for
machine-learning (ML) algorithms.

.. list-table:: Common federated learning attacks
   :name: federated-learning-attacks
   :widths: 30 70
   :header-rows: 1

   * - Attack name
     - Explanation
   * - Reconstruction
     - Attacker tries to reconstruct the original data from model parameters.
   * - Differencing
     - Running the same analysis multiple times, before and after the data has
       been updated. For instance, if average is computed again after a single
       patient is added, the value for that patient may be deduced.
   * - Deep Leakage from Gradients (DLG)
     - Using gradients in a deep learning model to reconstruct the original data
       bit by bit.
   * - Generative Adversarial Networks (GAN)
     - Reconstruction attack specifically aimed at machine learning model
       parameters.
   * - Model Inversion
     - Attacker builds a machine learning model known as the inversion model,
       that tries to predict the input of the FL machine learning model.
   * - Watermark attacks
     - An attacker includes a unique pattern into their partial ML model, which
       can later be used to derive information about the training data of others.





